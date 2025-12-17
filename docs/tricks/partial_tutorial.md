# Understanding `functools.partial` - A Tutorial

## The Problem: Keyword Arguments vs Positional Arguments

In the [`map_tools.py`](../asdrp/actions/geo/map_tools.py) file, we are using `functools.partial` to solve a common problem when working with `asyncio.run_in_executor()`.

### The Challenge

`run_in_executor()` has this signature:
```python
run_in_executor(executor, func, *args)  # Only accepts positional arguments!
```

But `places_nearby()` needs keyword arguments:
```python
client.places_nearby(location=(lat, lon), radius=1000, keyword="restaurant")
```

**You can't do this directly:**
```python
# ❌ This doesn't work!
await loop.run_in_executor(
    None,
    cls.client.places_nearby,
    location=(latitude, longitude),  # Error: keyword args not allowed!
    radius=radius
)
```

## What is `functools.partial`?

`partial` is a function that **creates a new function with some arguments pre-filled**. Think of it as "baking in" some arguments to create a simpler function.

### Simple Example

```python
from functools import partial

# Original function
def multiply(x, y, z):
    return x * y * z

# Create a new function with x=2 pre-filled
multiply_by_2 = partial(multiply, 2)

# Now you can call it with just 2 arguments
result = multiply_by_2(3, 4)  # Same as multiply(2, 3, 4) = 24
```

### With Keyword Arguments

```python
from functools import partial

def greet(greeting, name, punctuation="!"):
    return f"{greeting}, {name}{punctuation}"

# Pre-fill some keyword arguments
say_hello = partial(greet, greeting="Hello", punctuation=".")

# Now call with just the remaining argument
message = say_hello(name="Alice")  # "Hello, Alice."
```

## How It Works in `map_tools.py`

Let's trace through our specific code:

```python
# Step 1: Build a dictionary of parameters
places_params = {
    'location': (latitude, longitude),
    'radius': radius,
}
if keyword:
    places_params['keyword'] = keyword
if place_type:
    places_params['type'] = place_type

# Step 2: Use partial to "bake in" these keyword arguments
bound_function = partial(cls.client.places_nearby, **places_params)

# Step 3: Now bound_function can be called with NO arguments
# because all arguments are already filled in!
result = bound_function()  # This calls places_nearby with all the params

# Step 4: Pass the bound function to run_in_executor
places_result = await loop.run_in_executor(None, bound_function)
```

### What `partial` Actually Does

When you write:
```python
partial(cls.client.places_nearby, **places_params)
```

Python internally does something like this:
```python
def bound_function():
    return cls.client.places_nearby(
        location=(latitude, longitude),
        radius=radius,
        keyword=keyword,  # if provided
        type=place_type   # if provided
    )
```

## Understanding `[Any]` Type Annotation

The `[Any]` you might see in type hints refers to **generic type parameters** in Python's type system.

### What is `Any`?

`Any` is a special type from the `typing` module that means "any type is acceptable here." It's Python's way of saying "I don't care what type this is."

### `partial[Any]` Explained

When type checkers analyze `partial`, they see it as a generic function:

```python
from typing import Any
from functools import partial

# Type checker sees:
# partial[Any] means "partial that returns Any type"
bound_func: partial[Any] = partial(some_function, arg1, arg2)
```

In your case:
```python
# The type checker infers:
places_nearby_func: partial[Any] = partial(cls.client.places_nearby, **places_params)
```

This means:
- `partial` is a generic type
- `[Any]` specifies the return type of the partial function
- Since `places_nearby()` returns a dictionary (which could be typed as `Dict[str, Any]`), the type checker uses `Any` as a placeholder

### In Practice

You don't need to write `partial[Any]` yourself - it's what type checkers (like mypy or your IDE) infer. Your code is just:

```python
partial(cls.client.places_nearby, **places_params)
```

The `[Any]` is just type annotation metadata that helps IDEs and type checkers understand what type the resulting function returns.

## Visual Analogy

Think of `partial` like a **function factory**:

```
Original Function: places_nearby(location, radius, keyword, type)
         ↓
    [partial factory]
         ↓
New Function: bound_function()  ← All arguments already filled in!
```

It's like pre-ordering a pizza with all your toppings, so when you call the function, you just say "make it!" instead of listing all the toppings again.

## Why This Pattern is Common

This pattern appears throughout your codebase:

1. **`get_travel_time_distance`** (line ~396): Uses `partial` for `directions()`
2. **`get_distance_matrix`** (line ~473): Uses `partial` for `distance_matrix()`
3. **`places_autocomplete`** (line ~543): Uses `partial` for `places_autocomplete()`
4. **`search_places_nearby`** (line ~260): Uses `partial` for `places_nearby()`
5. **`get_place_details`** (line ~285): Uses `partial` for `place()`

All of these need keyword arguments, but `run_in_executor()` only accepts positional arguments, so `partial` bridges that gap!

## Understanding `asyncio.get_running_loop()`

At line 537 (and throughout `map_tools.py`), you'll see:

```python
loop = asyncio.get_running_loop()
```

### What Does It Do?

`asyncio.get_running_loop()` **gets a reference to the currently running event loop** in the current async context.

### Why Do We Need It?

The `googlemaps` library is **synchronous** (blocking) - when you call `client.geocode()`, it blocks the entire thread until the API responds. But your code is **asynchronous** - you want to handle multiple requests concurrently without blocking.

### The Solution: `run_in_executor()`

To run blocking synchronous code in an async function, you need to:

1. **Get the event loop** - `asyncio.get_running_loop()`
2. **Run blocking code in a thread pool** - `loop.run_in_executor()`

### Step-by-Step Breakdown

```python
# Line 537: Get the currently running event loop
loop = asyncio.get_running_loop()

# Line 553: Run the blocking function in a thread pool
autocomplete_result = await loop.run_in_executor(
    None,  # None = use default ThreadPoolExecutor
    partial(cls.client.places_autocomplete, **autocomplete_params)
)
```

### What Happens Internally?

```
┌─────────────────────────────────────┐
│  Async Function (your code)         │
│  ┌───────────────────────────────┐  │
│  │ loop = get_running_loop()     │  │ ← Gets current event loop
│  │                               │  │
│  │ await run_in_executor(...)    │  │ ← Runs blocking code in thread
│  │   ┌────────────────────────┐  │  │
│  │   │ Thread Pool            │  │  │
│  │   │ ┌───────────────────┐  │  │  │
│  │   │ │ client.geocode()  │  │  │  │ ← Blocking API call
│  │   │ │ (synchronous)     │  │  │  │
│  │   │ └───────────────────┘  │  │  │
│  │   └────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│  Event loop continues handling      │
│  other async tasks while waiting    │
└─────────────────────────────────────┘
```

### Key Points

1. **`get_running_loop()`** - Must be called from within an async function (that's why it's inside `async def` methods)
2. **Returns the active loop** - The event loop that's currently running your async code
3. **Used with `run_in_executor()`** - The loop needs to schedule the blocking work in a thread pool
4. **Non-blocking** - While the blocking code runs in a thread, the event loop can handle other async tasks

### Alternative: `asyncio.get_event_loop()`

You might see `asyncio.get_event_loop()` in older code, but `get_running_loop()` is preferred because:
- ✅ **Safer**: Raises an error if no loop is running (prevents bugs)
- ✅ **Clearer intent**: Explicitly says "get the loop that's running right now"
- ✅ **Python 3.7+**: Recommended approach

### Real-World Analogy

Think of it like a restaurant:

- **Event Loop** = The restaurant manager coordinating everything
- **`get_running_loop()`** = Finding the manager who's currently on duty
- **`run_in_executor()`** = Sending a slow task (like cooking) to the kitchen (thread pool) so the manager can keep taking orders (handling other async tasks)

### Where It's Used in `map_tools.py`

This pattern appears in every method that calls the Google Maps API:

1. **`get_coordinates_by_address`** (line 154)
2. **`get_address_by_coordinates`** (line 193)
3. **`search_places_nearby`** (line 244)
4. **`get_place_details`** (line 284)
5. **`get_travel_time_distance`** (line 379)
6. **`get_distance_matrix`** (line 460)
7. **`places_autocomplete`** (line 537)

All of them need to run blocking synchronous API calls without blocking the async event loop!

## Summary

- **`partial(func, **kwargs)`** creates a new function with keyword arguments pre-filled
- **`[Any]`** is a type annotation meaning "returns any type" (used by type checkers)
- **`asyncio.get_running_loop()`** gets the currently running event loop (must be in async context)
- **`loop.run_in_executor()`** runs blocking code in a thread pool without blocking the event loop
- **Why use it?** To convert functions that need keyword arguments into functions that can be called positionally (or with no arguments)
- **When to use it?** When you need to pass a function with keyword arguments to something that only accepts positional arguments (like `run_in_executor()`)

