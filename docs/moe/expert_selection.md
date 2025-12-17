# Semantic Expert Selection Tutorial

**Table of Contents**

- [Introduction](#introduction)
- [How It Works](#how-it-works)
- [The Semantic Approach](#the-semantic-approach)
- [Architecture & Performance](#architecture--performance)
- [Step-by-Step Walkthrough](#step-by-step-walkthrough)
- [Real-World Examples](#real-world-examples)
- [Configuration](#configuration)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

---

## Introduction

### What is Expert Selection?

When you ask the MoE orchestrator a question like "Show me Greek restaurants on a map in San Francisco", the system needs to decide **which specialist agents** should handle your request. This decision-making process is called **expert selection**.

Think of it like a hospital triage system:
- Your query is the patient's symptoms
- Expert agents are specialist doctors (cardiologist, neurologist, etc.)
- The selector is the triage nurse who routes you to the right specialists

### Why Semantic Selection?

Traditional routing uses **keyword matching** (if query contains "restaurant" → use Yelp agent). But this approach is fragile:

❌ Misses synonyms: "eatery", "dining", "food places"
❌ Misses context: "Where can I eat?" (no keyword "restaurant")
❌ False positives: "I don't want restaurant recommendations" (contains keyword but opposite intent)

**Semantic selection** uses AI embeddings to understand **meaning**, not just keywords:

✅ Handles synonyms naturally
✅ Understands context and intent
✅ Works with unseen phrasing
✅ More robust to variations

---

## How It Works

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│ User Query: "Show me Greek restaurants on a map"            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Convert query to embedding vector                   │
│ "Show me Greek restaurants on a map"                        │
│ → [0.23, -0.45, 0.67, ..., 0.12] (1536 numbers)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Compare with pre-computed expert embeddings         │
│                                                             │
│ business_expert: [0.21, -0.43, 0.69, ...] → similarity: 0.89│
│ location_expert: [0.24, -0.46, 0.65, ...] → similarity: 0.85│
│ finance_expert:  [0.01, -0.92, 0.11, ...] → similarity: 0.12│
│ ...                                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Select top experts above threshold                  │
│                                                             │
│ ✅ business_expert (0.89) → yelp_mcp, yelp                  │
│ ✅ location_expert (0.85) → map, geo                        │
│ ❌ finance_expert (0.12) - below threshold                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Apply smart filtering (gap analysis)                │
│                                                             │
│ business_expert: 0.89                                       │
│ location_expert: 0.85  (gap: 0.04 < 0.15) ✅ Include        │
│ knowledge_expert: 0.45 (gap: 0.40 > 0.15) ❌ Stop here      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Final Selection: [yelp_mcp, map]                            │
│                                                             │
│ • yelp_mcp: Fetch Greek restaurants from Yelp               │
│ • map: Generate interactive map with markers                │
└─────────────────────────────────────────────────────────────┘
```

---

## The Semantic Approach

### What Are Embeddings?

An **embedding** is a high-dimensional vector (list of numbers) that represents the **meaning** of text. Similar meanings have similar vectors.

**Visual Analogy:**

Imagine a 3D space where each point represents a word or phrase:

```
         map
          ↗
    directions  →  navigation
       ↓
     route


         restaurants
              ↗
    dining  →  food
       ↓
     cafes
```

In reality, embeddings have **1536 dimensions** (not 3), allowing much more nuanced meaning representation.

### Example: Query Embedding

**Query:** "Show me pizza places nearby"

**Embedding (simplified to 8 dimensions for illustration):**
```python
[
  0.82,  # food-related
  0.91,  # local/location
  0.15,  # urgency
  -0.45, # formality (negative = casual)
  0.67,  # visual/display
  0.23,  # social context
  -0.12, # technical
  0.55   # discovery/search
]
```

### Example: Expert Embeddings

Each expert has an embedding based on its **capabilities** (skills it can handle).

#### Business Expert

**Capabilities:** `local_business, reviews, restaurants, food, dining, bars, cafes, shops, ratings`

**Embedding:**
```python
[
  0.87,  # food-related (HIGH - matches pizza)
  0.72,  # local/location (HIGH - matches nearby)
  0.05,  # urgency
  -0.32, # formality
  0.12,  # visual/display
  0.68,  # social context (HIGH - reviews)
  -0.45, # technical
  0.81   # discovery/search (HIGH - matches places)
]
```

**Similarity to query:** `0.89` ✅ (Very high - good match!)

#### Location Expert

**Capabilities:** `geocoding, directions, places, maps, navigation, location, coordinates`

**Embedding:**
```python
[
  0.15,  # food-related (LOW - not food focused)
  0.95,  # local/location (VERY HIGH - perfect match)
  0.08,  # urgency
  -0.21, # formality
  0.88,  # visual/display (HIGH - maps are visual)
  0.11,  # social context
  -0.22, # technical
  0.44   # discovery/search
]
```

**Similarity to query:** `0.82` ✅ (High - also relevant for "nearby")

#### Finance Expert

**Capabilities:** `stocks, market_data, financial, trading, investment, ticker, price`

**Embedding:**
```python
[
  -0.12, # food-related (NEGATIVE - opposite domain)
  0.05,  # local/location (LOW)
  0.67,  # urgency (markets are time-sensitive)
  0.72,  # formality (HIGH - professional domain)
  0.23,  # visual/display
  0.08,  # social context
  0.89,  # technical (HIGH - numbers, data)
  0.44   # discovery/search
]
```

**Similarity to query:** `0.21` ❌ (Low - poor match, filtered out)

### Computing Similarity: Cosine Similarity

**Formula:**
```
similarity = (query · expert) / (||query|| × ||expert||)
```

Where:
- `·` = dot product (multiply corresponding numbers and sum)
- `||x||` = length/magnitude of vector

**Intuition:** How much do the vectors point in the same direction?

- `1.0` = Identical meaning (perfect match)
- `0.8-0.9` = Very similar (high relevance)
- `0.5-0.7` = Somewhat similar (moderate relevance)
- `0.0-0.3` = Unrelated (different topics)

---

## Architecture & Performance

### Component Structure

```
┌──────────────────────────────────────────────────────────────┐
│                    SemanticSelector                          │
│  • Orchestrates the selection process                        │
│  • Uses dependency injection for flexibility                 │
└────────────────────┬─────────────────────────────────────────┘
                     │ depends on
┌────────────────────▼─────────────────────────────────────────┐
│                 IEmbeddingProvider                           │
│  • Interface for generating embeddings                       │
│  • Allows swapping implementations                           │
└────────────────────┬─────────────────────────────────────────┘
                     │ implemented by
┌────────────────────▼─────────────────────────────────────────┐
│            CachedEmbeddingProvider                           │
│  • Decorator pattern wrapping another provider               │
│  • LRU cache: 10,000 entries                                 │
│  • Content-addressed: SHA256(query) → embedding              │
│  • Hit rate: >90% after warmup                               │
└────────────────────┬─────────────────────────────────────────┘
                     │ wraps
┌────────────────────▼─────────────────────────────────────────┐
│            OpenAIEmbeddingProvider                           │
│  • Uses text-embedding-3-small model                         │
│  • Generates 1536-dimensional embeddings                     │
│  • Batch support: up to 2048 texts per API call              │
└──────────────────────────────────────────────────────────────┘
```

### Performance Characteristics

#### Cold Start (First Query)

```
User Query
   │
   ├─ Check cache → MISS
   ├─ Call OpenAI API → 1500-2000ms
   ├─ Store in cache → <1ms
   ├─ Compute similarities (6 experts) → 1-2ms
   ├─ Apply relevance filtering → <1ms
   │
   └─ Total: ~2000ms
```

#### Warm Cache (Subsequent Identical Query)

```
User Query
   │
   ├─ Check cache → HIT (<1ms)
   ├─ Compute similarities (6 experts) → 1-2ms
   ├─ Apply relevance filtering → <1ms
   │
   └─ Total: ~5ms (400x faster!)
```

#### Warm Cache (Similar Query)

```
User Query: "pizza restaurants in SF"  (never seen before)
   │
   ├─ Check cache → MISS (different query)
   ├─ Call OpenAI API → 1500-2000ms
   ├─ Store in cache → <1ms
   ├─ Compute similarities → 1-2ms
   ├─ Apply relevance filtering → <1ms
   │
   └─ Total: ~2000ms (but now cached for next time)
```

**Key Insight:** After 20-30 diverse queries, most new queries are similar enough to cached ones that the system maintains <50ms average latency.

### Memory Usage

```
Expert Embeddings (6 experts × 1536 dims × 4 bytes):  ~37 KB
Cache (10,000 entries × 1536 dims × 4 bytes):        ~58 MB
Overhead (dict structure, keys):                      ~5 MB
────────────────────────────────────────────────────────────
Total:                                               ~63 MB
```

**Trade-off:** 63 MB of RAM for 400x speedup on common queries.

---

## Step-by-Step Walkthrough

Let's walk through a complete example with detailed explanations.

### Example Query: "Find vegan restaurants near me and show them on a map"

#### Step 1: Expert Initialization (One-Time, During Startup)

**Code:**
```python
selector = SemanticSelector(config)
await selector._initialize_embeddings()
```

**What Happens:**

1. **Load expert definitions from config:**

```yaml
# config/moe.yaml
experts:
  business_expert:
    agents: ["yelp", "yelp_mcp"]
    capabilities:
      - local_business
      - reviews
      - restaurants
      - food
      - dining
      - bars
      - cafes
      - shops
      - businesses
      - ratings
    weight: 1.0

  location_expert:
    agents: ["map", "geo"]
    capabilities:
      - geocoding
      - directions
      - places
      - maps
      - navigation
      - location
      - coordinates
      - show
      - display
      - visualization
    weight: 1.0

  # ... other experts
```

2. **Generate descriptions from capabilities:**

```python
business_expert_description = "Expert for: local_business, reviews, restaurants, food, dining, bars, cafes, shops, businesses, ratings"
location_expert_description = "Expert for: geocoding, directions, places, maps, navigation, location, coordinates, show, display, visualization"
# ... etc
```

3. **Generate embeddings using OpenAI API (batched):**

```python
descriptions = [
    "Expert for: local_business, reviews, restaurants, ...",
    "Expert for: geocoding, directions, places, maps, ...",
    "Expert for: wikipedia, encyclopedia, history, ...",
    # ... all 6 experts
]

# Single API call for all experts
embeddings = await openai.embeddings.create(
    model="text-embedding-3-small",
    input=descriptions  # Batch request
)

# Store for later use
expert_embeddings = {
    "business_expert": [0.87, 0.72, ...],  # 1536 numbers
    "location_expert": [0.15, 0.95, ...],  # 1536 numbers
    # ... etc
}
```

**Performance:** ~1000ms (much faster than 6 sequential API calls = ~12000ms)

**Output:**
```
[SemanticSelector] Initializing expert embeddings (batched)...
[SemanticSelector] Initialized embeddings for 6 experts in 1023ms
```

---

#### Step 2: Query Arrives

**User sends:** "Find vegan restaurants near me and show them on a map"

**System receives:** `query = "Find vegan restaurants near me and show them on a map"`

---

#### Step 3: Generate Query Embedding

**Code:**
```python
query_embedding = await provider.generate_embedding(query)
```

**What Happens:**

1. **Check cache (content-addressed):**

```python
cache_key = sha256("Find vegan restaurants near me and show them on a map").hexdigest()
# → "a7f3e9c2b4d8f1a6..."

if cache_key in cache:
    return cache[cache_key]  # <1ms
else:
    # Cache miss - call OpenAI API
```

2. **First time seeing this query? Call OpenAI API:**

```python
response = await openai.embeddings.create(
    model="text-embedding-3-small",
    input="Find vegan restaurants near me and show them on a map"
)

query_embedding = response.data[0].embedding
# → [0.82, 0.91, 0.67, ..., 0.44]  (1536 numbers)
```

3. **Store in cache for next time:**

```python
cache[cache_key] = query_embedding
```

**Performance:**
- First time: ~1800ms (API call)
- Subsequent: <1ms (cache hit)

**Output:**
```
[EmbeddingCache] Cache miss for: Find vegan restaurants near me and show them on a...
[SemanticSelector] Query embedding generated in 1847.3ms
```

---

#### Step 4: Compute Similarities

**Code:**
```python
similarities = {}
for expert_name, expert_embedding in expert_embeddings.items():
    similarity = cosine_similarity(query_embedding, expert_embedding)
    similarities[expert_name] = similarity
```

**What Happens:**

For each expert, compute how similar its embedding is to the query:

```python
# Business Expert
business_sim = cosine_similarity(
    [0.82, 0.91, 0.67, ...],  # query: "vegan restaurants near me..."
    [0.87, 0.72, 0.12, ...]   # expert: "local_business, restaurants, food..."
)
# Result: 0.89 (very similar!)

# Location Expert
location_sim = cosine_similarity(
    [0.82, 0.91, 0.67, ...],  # query: "...show them on a map"
    [0.15, 0.95, 0.88, ...]   # expert: "maps, navigation, show, display..."
)
# Result: 0.85 (very similar!)

# Finance Expert
finance_sim = cosine_similarity(
    [0.82, 0.91, 0.67, ...],  # query: "vegan restaurants..."
    [-0.12, 0.05, 0.89, ...]  # expert: "stocks, market_data, trading..."
)
# Result: 0.18 (not similar)

# Knowledge Expert (Wikipedia)
knowledge_sim = cosine_similarity(
    [0.82, 0.91, 0.67, ...],  # query
    [0.32, 0.11, 0.76, ...]   # expert: "wikipedia, encyclopedia, history..."
)
# Result: 0.52 (somewhat similar - "vegan" is informational)
```

**Results Table:**

| Expert | Similarity | Status |
|--------|-----------|--------|
| business_expert | 0.89 | ✅ Above threshold (0.5) |
| location_expert | 0.85 | ✅ Above threshold |
| knowledge_expert | 0.52 | ✅ Above threshold |
| search_expert | 0.41 | ❌ Below threshold |
| finance_expert | 0.18 | ❌ Below threshold |
| chitchat_expert | 0.09 | ❌ Below threshold |

**Performance:** ~1-2ms (simple numpy dot products)

**Output:**
```
[SemanticSelector] Expert similarities: {
    'business_expert': 0.89,
    'location_expert': 0.85,
    'knowledge_expert': 0.52,
    'search_expert': 0.41,
    'finance_expert': 0.18,
    'chitchat_expert': 0.09
}
```

---

#### Step 5: Apply Relevance Gap Filter

**Why?** We don't want to select weakly matched experts just because they meet the threshold. The **gap filter** stops selection when there's a big drop in relevance.

**Algorithm:**

```python
def apply_relevance_gap_filter(experts, max_k=3, gap_threshold=0.15):
    """
    Select experts until:
    1. We hit max_k agents, OR
    2. The relevance gap between consecutive experts exceeds threshold
    """

    # Sort by similarity (highest first)
    sorted_experts = sorted(experts, key=lambda x: x[1], reverse=True)
    # → [('business_expert', 0.89),
    #    ('location_expert', 0.85),
    #    ('knowledge_expert', 0.52),
    #    ...]

    # Always include the top expert
    selected = [sorted_experts[0]]

    # Add more experts if gap is small
    for i in range(1, min(len(sorted_experts), max_k)):
        prev_score = sorted_experts[i-1][1]
        curr_score = sorted_experts[i][1]
        gap = prev_score - curr_score

        if gap <= gap_threshold:
            selected.append(sorted_experts[i])
            print(f"Adding {sorted_experts[i][0]} (gap={gap:.3f} < {gap_threshold})")
        else:
            print(f"Stopping: gap={gap:.3f} > {gap_threshold}")
            break

    return selected
```

**Execution:**

```
Sorted experts:
1. business_expert: 0.89
2. location_expert: 0.85
3. knowledge_expert: 0.52
4. search_expert: 0.41
5. finance_expert: 0.18
6. chitchat_expert: 0.09

Selection process:
✅ business_expert (0.89) - Always include top expert
✅ location_expert (0.85) - Gap: 0.04 < 0.15 → Include
❌ knowledge_expert (0.52) - Gap: 0.33 > 0.15 → STOP HERE

Final selection: [business_expert, location_expert]
```

**Why stop at knowledge_expert?**

The big gap (0.33) indicates that **knowledge_expert** is significantly less relevant than the top two. Including it would dilute the response quality.

**Output:**
```
[SemanticSelector] Adding expert location_expert (gap=0.040 < 0.15)
[SemanticSelector] Stopping selection: gap=0.330 > 0.15
[SemanticSelector] Dynamic selection: 2 experts from 3 candidates
```

---

#### Step 6: Map Experts to Agents

**Each expert group contains multiple agents:**

```python
# business_expert → multiple agents
business_expert.agents = ["yelp", "yelp_mcp"]

# location_expert → multiple agents
location_expert.agents = ["map", "geo"]
```

**Flattening:**

```python
selected_agents = []
for expert_name in ["business_expert", "location_expert"]:
    agents = expert_to_agents[expert_name]
    selected_agents.extend(agents)

# Result: ["yelp", "yelp_mcp", "map", "geo"]
```

**Apply max_k limit (top_k_experts = 3):**

```python
selected_agents = selected_agents[:3]
# Result: ["yelp", "yelp_mcp", "map"]
```

**Map intent prioritization (ensures map agent isn't dropped):**

```python
# Query contains "show them on a map" → map intent detected
# Ensure "map" agent is in the final list
if "map" in query and "map" not in selected_agents:
    # Replace less relevant agent with "map"
    selected_agents[-1] = "map"

# Result: ["yelp_mcp", "map"] (geo dropped, yelp consolidated)
```

**Final Selection:** `["yelp_mcp", "map"]`

**Output:**
```
[SemanticSelector] Selected 2 agents: ['yelp_mcp', 'map']
[MoE] Final selected agents: ['yelp_mcp', 'map']
```

---

#### Step 7: Total Performance

**First query (cold cache):**
```
Embedding generation: 1847ms
Similarity computation: 2ms
Gap filtering: <1ms
Agent mapping: <1ms
───────────────────────────
Total: 1850ms
```

**Second identical query (warm cache):**
```
Embedding generation: <1ms (cache hit!)
Similarity computation: 2ms
Gap filtering: <1ms
Agent mapping: <1ms
───────────────────────────
Total: 5ms (370x faster!)
```

---

## Real-World Examples

### Example 1: Simple Chitchat

**Query:** "Hello, how are you today?"

**Step 1: Generate Embedding**
```python
query_embedding = [0.12, -0.34, 0.89, ..., 0.23]
# Encodes: greeting, social, casual, friendly
```

**Step 2: Compute Similarities**
```
chitchat_expert:  0.92  (greeting words are in capabilities)
search_expert:    0.21
business_expert:  0.18
location_expert:  0.15
knowledge_expert: 0.12
finance_expert:   0.08
```

**Step 3: Apply Gap Filter**
```
1. chitchat_expert: 0.92 ✅
2. search_expert: 0.21 - Gap: 0.71 > 0.15 ❌ STOP

Final: [chitchat_expert] → ["chitchat"]
```

**Result:** Single agent for simple query (efficient!)

**Output:**
```
[SemanticSelector] Selected 1 agents in 3.8ms: ['chitchat']
```

---

### Example 2: Multi-Domain Query

**Query:** "What's the history of pizza and where can I find authentic Italian restaurants in SF?"

**Step 1: Generate Embedding**
```python
query_embedding = [0.78, 0.61, 0.87, ..., 0.92]
# Encodes: food + history + location + discovery
```

**Step 2: Compute Similarities**
```
knowledge_expert: 0.87  (history, encyclopedia)
business_expert:  0.84  (restaurants, food)
location_expert:  0.81  (where, find, SF)
search_expert:    0.45
finance_expert:   0.11
chitchat_expert:  0.08
```

**Step 3: Apply Gap Filter**
```
1. knowledge_expert: 0.87 ✅
2. business_expert: 0.84 - Gap: 0.03 < 0.15 ✅
3. location_expert: 0.81 - Gap: 0.03 < 0.15 ✅
4. search_expert: 0.45 - Gap: 0.36 > 0.15 ❌ STOP

Final: [knowledge_expert, business_expert, location_expert]
     → ["wiki", "yelp_mcp", "map"]
```

**Result:** Three agents for complex multi-domain query.

**What Each Agent Does:**
- `wiki`: Explains the history of pizza
- `yelp_mcp`: Finds authentic Italian restaurants in SF
- `map`: Shows restaurant locations on interactive map

**Output:**
```
[SemanticSelector] Selected 3 agents in 4.2ms: ['wiki', 'yelp_mcp', 'map']
```

---

### Example 3: Financial Query

**Query:** "What's the current price of TSLA stock?"

**Step 1: Generate Embedding**
```python
query_embedding = [-0.15, 0.92, 0.87, ..., 0.76]
# Encodes: finance, stock market, ticker, data
```

**Step 2: Compute Similarities**
```
finance_expert:   0.94  (stocks, market_data, price)
search_expert:    0.32  (could search for price)
knowledge_expert: 0.28
business_expert:  0.19
location_expert:  0.11
chitchat_expert:  0.07
```

**Step 3: Apply Gap Filter**
```
1. finance_expert: 0.94 ✅
2. search_expert: 0.32 - Gap: 0.62 > 0.15 ❌ STOP

Final: [finance_expert] → ["finance"]
```

**Result:** Single specialized agent (efficient and accurate!)

**Output:**
```
[SemanticSelector] Selected 1 agents in 2.1ms: ['finance']
```

---

### Example 4: Ambiguous Query

**Query:** "Apple"

**Analysis:** This is ambiguous - could mean:
- Apple Inc. stock (finance)
- Apple fruit (food/knowledge)
- Apple Store locations (business/location)

**Step 1: Generate Embedding**
```python
query_embedding = [0.45, 0.38, 0.41, ..., 0.37]
# Encodes: generic, ambiguous, multiple interpretations
```

**Step 2: Compute Similarities**
```
finance_expert:   0.58  (companies, ticker)
knowledge_expert: 0.56  (encyclopedia, facts)
business_expert:  0.54  (stores, shops)
search_expert:    0.52
location_expert:  0.48
chitchat_expert:  0.11
```

**Step 3: Apply Gap Filter**
```
1. finance_expert: 0.58 ✅
2. knowledge_expert: 0.56 - Gap: 0.02 < 0.15 ✅
3. business_expert: 0.54 - Gap: 0.02 < 0.15 ✅
4. search_expert: 0.52 - Max k=3 reached ❌ STOP

Final: [finance_expert, knowledge_expert, business_expert]
     → ["finance", "wiki", "yelp"]
```

**Result:** Multiple agents for ambiguous query (covers all interpretations!)

**What Happens:**
- System runs all 3 agents in parallel
- Result mixer synthesizes responses
- User gets comprehensive answer covering all meanings

**Output:**
```
[SemanticSelector] Selected 3 agents in 3.5ms: ['finance', 'wiki', 'yelp']
```

---

### Example 5: Negation (Tricky!)

**Query:** "I don't want restaurant recommendations, show me parks instead"

**Why This Works:**

Even though the query contains "restaurant", the embedding captures the **negation** and **intent shift**:

```python
query_embedding = [0.23, 0.88, -0.12, ..., 0.67]
# Notice the negative value and high location/outdoor signal
```

**Step 2: Compute Similarities**
```
location_expert:  0.82  (parks, places, show)
search_expert:    0.51  (find information about parks)
knowledge_expert: 0.44
business_expert:  0.38  (LOW despite "restaurant" keyword!)
finance_expert:   0.09
chitchat_expert:  0.06
```

**Result:** `["map", "one"]` - Correctly avoids restaurant agents!

This demonstrates why semantic understanding beats keyword matching.

---

## Configuration

### MoE Configuration File

**Location:** `config/moe.yaml`

#### Selection Strategy

```yaml
moe:
  # Choose selection approach
  selection_strategy: "semantic"  # or "capability_match"

  # Max agents to select (upper bound, not fixed)
  top_k_experts: 3

  # Minimum similarity score to consider expert
  confidence_threshold: 0.5

  # Maximum gap between consecutive experts before stopping
  relevance_gap_threshold: 0.15
```

**Parameters Explained:**

**`confidence_threshold` (default: 0.5)**
- **Too low (0.3):** Selects too many weakly relevant experts, slower execution
- **Too high (0.7):** May miss relevant experts, incomplete responses
- **Recommended:** 0.5 balances precision and recall

**`relevance_gap_threshold` (default: 0.15)**
- **Too low (0.05):** Very strict, often selects only 1-2 agents
- **Too high (0.30):** Less discriminating, may select marginally relevant agents
- **Recommended:** 0.15 provides good balance

**`top_k_experts` (default: 3)**
- **Hard upper limit** on selected agents (cost/latency control)
- Dynamic selection can select fewer than k
- **Recommended:** 3 for most use cases (allows multi-domain queries)

---

#### Expert Definitions

```yaml
experts:
  business_expert:
    agents: ["yelp", "yelp_mcp"]
    capabilities:
      - local_business
      - reviews
      - restaurants
      - food
      - dining
      - bars
      - cafes
      - shops
      - businesses
      - ratings
    weight: 1.0

  location_expert:
    agents: ["map", "geo"]
    capabilities:
      - geocoding
      - directions
      - places
      - maps
      - navigation
      - location
      - coordinates
      - show
      - display
      - visualization
    weight: 1.0
```

**How to Add Capabilities:**

When adding new capabilities, think about:

1. **Synonyms:** Add all common ways to express the concept
   - "restaurant" → also add "eatery", "dining", "food"

2. **Related Terms:** Add contextually related words
   - "map" → also add "navigation", "directions", "route"

3. **Action Verbs:** Add common verbs for this domain
   - "show", "display", "visualize", "find"

4. **Domain Jargon:** Add technical terms if relevant
   - Finance: "ticker", "portfolio", "dividend"

**Example: Enhancing location_expert**

```yaml
location_expert:
  capabilities:
    # Core concepts
    - geocoding
    - maps
    - location
    - geography

    # Synonyms
    - directions
    - navigation
    - route
    - routing
    - way
    - path

    # Visualization
    - show
    - display
    - visualize
    - visualization
    - pin
    - marker

    # Spatial terms
    - near
    - nearby
    - around
    - distance
    - coordinates

    # Actions
    - drive
    - walk
    - travel
    - navigate
    - go
```

---

### Cache Configuration

The embedding cache is configured in the code (not YAML):

```python
# asdrp/orchestration/moe/semantic_selector.py

CachedEmbeddingProvider(
    provider=base_provider,
    max_size=10000,      # Max cache entries (LRU eviction)
    enable_logging=True  # Log cache hits/misses
)
```

**Tuning Guidelines:**

**`max_size`:**
- **Default: 10,000** entries
- **Memory:** ~60 MB (10K × 1536 dims × 4 bytes)
- **Increase if:** You have high query diversity (>10K unique queries)
- **Decrease if:** Memory constrained (<100 MB available)

**Formula:** `memory_mb = max_size × 1536 × 4 / 1024 / 1024`

---

## Advanced Topics

### Understanding the Gap Filter

The **relevance gap filter** is what enables dynamic agent selection (1-3 agents, not always 3).

#### Why It Matters

Without gap filtering:

```
Query: "Hello"

Selected: [chitchat, search, knowledge]  ← Wasteful!
          0.95     0.12      0.08

Result: 3 agents run, but only chitchat is relevant
        → Slower execution, no quality improvement
```

With gap filtering:

```
Query: "Hello"

Candidates: chitchat (0.95), search (0.12), knowledge (0.08)
Gap analysis: 0.95 → 0.12 = 0.83 gap > 0.15 threshold
              STOP after chitchat

Selected: [chitchat]  ← Efficient!

Result: 1 agent runs, perfect for simple query
        → Faster execution, same quality
```

#### Gap Threshold Tuning

**Test different thresholds on real queries:**

```python
def evaluate_gap_threshold(queries, ground_truth, thresholds):
    """
    Find optimal threshold by testing on labeled data.

    Args:
        queries: List of test queries
        ground_truth: Expected number of agents for each query
        thresholds: List of gap values to test [0.05, 0.10, 0.15, 0.20, 0.25]
    """

    results = []

    for threshold in thresholds:
        config.moe.relevance_gap_threshold = threshold
        selector = SemanticSelector(config)

        correct = 0
        for query, expected_count in zip(queries, ground_truth):
            agents = await selector.select(query)
            if len(agents) == expected_count:
                correct += 1

        accuracy = correct / len(queries)
        results.append((threshold, accuracy))
        print(f"Threshold {threshold}: {accuracy:.1%} accuracy")

    return results

# Example output:
# Threshold 0.05: 62% accuracy (too strict, under-selects)
# Threshold 0.10: 78% accuracy
# Threshold 0.15: 89% accuracy ← Recommended
# Threshold 0.20: 84% accuracy (too lenient, over-selects)
# Threshold 0.25: 71% accuracy
```

---

### Embedding Provider Architecture

The system uses **dependency injection** for flexibility:

```python
# Default: Cached OpenAI provider
selector = SemanticSelector(config)

# Custom: Inject your own provider
custom_provider = MyCustomProvider()
selector = SemanticSelector(config, embedding_provider=custom_provider)
```

#### Creating Custom Providers

**Example: Mock Provider for Testing**

```python
from asdrp.orchestration.moe.embedding_providers import IEmbeddingProvider
import numpy as np

class MockEmbeddingProvider(IEmbeddingProvider):
    """Deterministic embeddings for unit tests."""

    def __init__(self):
        self._dimension = 1536
        self._cache = {}

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate deterministic embedding based on text hash."""
        # Use hash for reproducibility
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        return np.random.rand(self._dimension)

    async def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Batch generate embeddings."""
        return [await self.generate_embedding(text) for text in texts]

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

# Use in tests
selector = SemanticSelector(config, embedding_provider=MockEmbeddingProvider())
```

**Example: Local Model Provider (Fast, No API Cost)**

```python
class LocalEmbeddingProvider(IEmbeddingProvider):
    """Uses sentence-transformers for local inference."""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding locally (no API call)."""
        # Run in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self._model.encode,
            text
        )
        return np.array(embedding)

    async def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Batch encode efficiently."""
        import asyncio
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._model.encode,
            texts
        )
        return [np.array(emb) for emb in embeddings]

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

# Use for ultra-low latency (5-20ms)
local_provider = LocalEmbeddingProvider()
cached_local = CachedEmbeddingProvider(local_provider)
selector = SemanticSelector(config, embedding_provider=cached_local)
```

**Performance Comparison:**

| Provider | First Query | Cached Query | Quality | Cost |
|----------|------------|--------------|---------|------|
| **OpenAI** | 1500-2000ms | <1ms | Excellent | $0.00002/1K tokens |
| **Local (CPU)** | 20-50ms | <1ms | Very Good | Free |
| **Local (GPU)** | 5-10ms | <1ms | Very Good | Free |
| **Mock** | <1ms | <1ms | N/A (testing) | Free |

---

### Monitoring & Observability

#### Cache Statistics

```python
if isinstance(selector._provider, CachedEmbeddingProvider):
    stats = selector._provider.get_cache_stats()

    print(f"Hit rate: {stats['hit_rate']:.1%}")
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Total requests: {stats['total_requests']}")
    print(f"Cache size: {stats['cache_size']}/{stats['max_size']}")
```

**Example Output:**
```
Hit rate: 94.2%
Hits: 452
Misses: 28
Total requests: 480
Cache size: 387/10000
```

**Interpreting Results:**

- **Hit rate >90%:** Excellent, cache is working well
- **Hit rate 70-90%:** Good, but may benefit from larger cache
- **Hit rate <70%:** High query diversity, consider local model provider
- **Cache size near max_size:** May need to increase cache size

#### Performance Logging

The system automatically logs performance metrics:

```
[SemanticSelector] Query embedding generated in 1.2ms
[SemanticSelector] Selected 2 agents in 4.8ms: ['yelp_mcp', 'map']
[EmbeddingCache] Stats: 92.5% hit rate (185/200 requests, 167 entries)
```

**Set up alerting for slow queries:**

```python
import time
from loguru import logger

# Wrapper to track slow selections
original_select = selector.select

async def select_with_alerting(query, *args, **kwargs):
    start = time.time()
    result = await original_select(query, *args, **kwargs)
    elapsed_ms = (time.time() - start) * 1000

    if elapsed_ms > 100:  # Alert threshold
        logger.warning(
            f"Slow expert selection: {elapsed_ms:.0f}ms for query: {query[:50]}..."
        )

    return result

selector.select = select_with_alerting
```

---

## Troubleshooting

### Issue 1: High Latency (>500ms per query)

**Symptoms:**
```
[SemanticSelector] Query embedding generated in 1847.3ms
[SemanticSelector] Selected 2 agents in 1850.5ms
```

**Possible Causes:**

1. **Cache not working**

Check cache stats:
```python
stats = selector._provider.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

If hit rate is 0%, cache isn't being used:
- Verify `CachedEmbeddingProvider` is wrapping the base provider
- Check logs for `[SemanticSelector] Using cached OpenAI embedding provider`

2. **OpenAI API slow/rate limited**

Check OpenAI status: https://status.openai.com

Temporary workaround:
```python
# Increase timeout
base_provider = OpenAIEmbeddingProvider(
    api_key=api_key,
    timeout=30.0  # Increase from default
)
```

3. **Network issues**

Test direct API call:
```python
import asyncio
from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI()
    start = time.time()
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input="test"
    )
    print(f"API latency: {(time.time() - start)*1000:.0f}ms")

asyncio.run(test())
```

---

### Issue 2: Wrong Agents Selected

**Symptoms:**
```
Query: "Show me pizza places on a map"
Selected: ['wiki', 'chitchat']  ← Wrong!
```

**Possible Causes:**

1. **Expert capabilities need tuning**

Check which expert should have been selected:
```python
# Manually compute similarities for debugging
query_emb = await selector._provider.generate_embedding(
    "Show me pizza places on a map"
)

for expert_name, expert_emb in selector._expert_embeddings.items():
    sim = cosine_similarity(query_emb, expert_emb)
    print(f"{expert_name}: {sim:.3f}")
```

If `business_expert` and `location_expert` have low scores, add capabilities:

```yaml
business_expert:
  capabilities:
    - pizza  # Add specific term
    - places  # Add synonym

location_expert:
  capabilities:
    - show  # Add action verb
    - visualize  # Add synonym
```

2. **Threshold too high**

Lower the confidence threshold:
```yaml
moe:
  confidence_threshold: 0.4  # Down from 0.5
```

3. **Embeddings not initialized**

Check for initialization logs:
```
[SemanticSelector] Initialized embeddings for 6 experts in 1023ms
```

If missing, expert embeddings weren't pre-computed.

---

### Issue 3: Too Many Agents Selected

**Symptoms:**
```
Query: "Hello"
Selected: ['chitchat', 'one', 'wiki']  ← Too many for simple query
```

**Possible Causes:**

1. **Gap threshold too high**

Lower the relevance gap threshold:
```yaml
moe:
  relevance_gap_threshold: 0.10  # Down from 0.15
```

This makes selection more strict.

2. **Capabilities too broad**

Review expert capabilities for overlap:
```yaml
# BAD: Too much overlap
chitchat_expert:
  capabilities: [conversation, hello, hi, ...]
search_expert:
  capabilities: [search, find, hello, ...]  ← "hello" in both!

# GOOD: Clear separation
chitchat_expert:
  capabilities: [conversation, greeting, hello, hi, ...]
search_expert:
  capabilities: [search, find, lookup, information, ...]
```

---

### Issue 4: Memory Usage Too High

**Symptoms:**
```
Process memory: 850 MB (expected ~100 MB)
```

**Possible Causes:**

1. **Cache too large**

Reduce cache size:
```python
CachedEmbeddingProvider(
    provider=base_provider,
    max_size=5000,  # Down from 10000
    enable_logging=True
)
```

Memory formula: `5000 × 1536 × 4 / 1024 / 1024 = ~29 MB`

2. **Memory leak in custom provider**

Check if you're accumulating embeddings elsewhere:
```python
# BAD: Leaks memory
class BadProvider(IEmbeddingProvider):
    def __init__(self):
        self._all_embeddings = []  # Never cleared!

    async def generate_embedding(self, text):
        emb = ...
        self._all_embeddings.append(emb)  # Leak!
        return emb
```

---

## Summary

### Key Takeaways

1. **Semantic selection uses AI embeddings** to understand query meaning, not just keywords

2. **Performance is fast after warmup**:
   - First query: ~2000ms (API call)
   - Cached queries: <5ms (in-memory lookup)

3. **Dynamic agent selection** adapts to query complexity:
   - Simple queries → 1 agent
   - Complex queries → 2-3 agents

4. **Configuration is flexible**:
   - Tune thresholds for your use case
   - Add capabilities to improve matching
   - Inject custom providers for testing

5. **Architecture is extensible**:
   - Interface-based design (SOLID principles)
   - Easy to add new providers (local models, etc.)
   - Decorator pattern for composable features

### Quick Reference

**Configuration File:** `config/moe.yaml`

**Key Classes:**
- `SemanticSelector` - Main selection logic
- `IEmbeddingProvider` - Interface for embedding generation
- `CachedEmbeddingProvider` - Adds caching to any provider
- `OpenAIEmbeddingProvider` - Uses OpenAI API

**Key Parameters:**
- `confidence_threshold: 0.5` - Minimum similarity to select expert
- `relevance_gap_threshold: 0.15` - Stop selection when gap exceeds this
- `top_k_experts: 3` - Maximum agents to select

**Performance Targets:**
- Cold query: <2000ms
- Warm query: <50ms
- Cache hit rate: >90%

---

## Further Reading

- [MoE Architecture Overview](./architecture.md)
- [Result Mixing Strategies](./result_mixing.md)
- [Performance Optimization Guide](./performance.md)
- [Testing Guide](./testing.md)

---

**Last Updated:** December 15, 2024
**Authors:** OpenAgents Team
**Version:** 1.0
