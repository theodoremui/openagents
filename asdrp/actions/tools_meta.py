#############################################################################
# tools_meta.py
#
# General metaclass for automatically discovering class methods and creating
# tool lists for agent frameworks.
#
#############################################################################

import inspect
from typing import Any, List, Set
from agents import function_tool        


class ToolsMeta(type):
    """
    Metaclass that automatically discovers public class methods and creates
    a `spec_functions` list and `tool_list` for use with agent frameworks.
    
    The metaclass automatically:
    1. Discovers all public class methods (methods decorated with @classmethod)
    2. Creates a `spec_functions` list containing method names (sorted alphabetically)
    3. Creates a `tool_list` containing wrapped function tools ready for agent frameworks
    
    Customization Hooks:
    --------------------
    Classes using this metaclass can customize behavior by implementing optional hooks:
    
    - `_setup_class()`: A @classmethod called during class creation to perform 
      class-level initialization (e.g., setting API keys, headers, etc.)
    
    - `_get_excluded_methods()`: A @classmethod that returns a set of method/attribute 
      names to exclude from tool discovery (in addition to default exclusions)
    
    Default Exclusions:
    -------------------
    The following are automatically excluded from tool discovery:
    - Methods starting with '_' (private methods)
    - Special methods: '__init__', '__new__', '__init_subclass__', '__class__'
    - Metaclass-generated attributes: 'spec_functions', 'tool_list'
    
    Example Usage:
    --------------
    ```python
    from asdrp.actions.tools_meta import ToolsMeta
    
    class MyActionTools(metaclass=ToolsMeta):
        # Optional: Set up class-level configuration
        @classmethod
        def _setup_class(cls) -> None:
            cls.api_key = os.getenv("MY_API_KEY")
            cls.headers = {"Authorization": f"Bearer {cls.api_key}"}
        
        # Optional: Exclude additional methods/attributes
        @classmethod
        def _get_excluded_methods(cls) -> set[str]:
            return {'api_key', 'headers', 'BASE_URL'}
        
        # Public class methods are automatically discovered as tools
        @classmethod
        def search_something(cls, query: str) -> dict:
            \"\"\"Search for something.\"\"\"
            # Implementation here
            return {}
    
    # After class creation:
    # - MyActionTools.spec_functions contains ['search_something']
    # - MyActionTools.tool_list contains wrapped function tools
    ```
    """
    
    # Default methods/attributes to exclude from tool discovery
    DEFAULT_EXCLUDED: Set[str] = {
        '__init__', '__new__', '__init_subclass__', '__class__',
        'spec_functions', 'tool_list'
    }
    
    def __new__(mcs: type, name: str, bases: tuple[type, ...], 
                namespace: dict[str, Any], **kwargs: Any) -> type:
        """Create the class and set up spec_functions and tool_list."""
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        
        # Allow the class itself to perform custom setup via _setup_class classmethod
        # This is called after class creation but before method discovery
        if hasattr(cls, '_setup_class'):
            cls._setup_class()
        
        # Discover public class methods
        cls.spec_functions = mcs._discover_class_methods(mcs, cls)
        
        # Create tool_list from discovered methods
        cls.tool_list = mcs._create_tool_list(cls)
        
        return cls
    
    @staticmethod
    def _discover_class_methods(mcs: type, cls: type) -> List[str]:
        """
        Discover all public class methods in the class.
        
        Only includes methods (decorated with @classmethod), not variables.
        Excludes: class variables, instance variables, properties, descriptors.
        
        Args:
            mcs: The metaclass being used
            cls: The class to inspect
            
        Returns:
            Sorted list of public class method names
        """
        public_methods = []
        excluded = ToolsMeta._get_excluded_methods(mcs, cls)
        
        for name in dir(cls):
            if name.startswith('_') or name in excluded:
                continue
            
            attr = getattr(cls, name)
            # Only include methods, not variables (class or instance)
            # Check if it's a bound method bound to the class (classmethod)
            # This excludes: class variables, instance variables, properties, descriptors
            if inspect.ismethod(attr) and attr.__self__ is cls:
                public_methods.append(name)
        
        return sorted(public_methods)
    
    @staticmethod
    def _get_excluded_methods(mcs: type, cls: type) -> Set[str]:
        """
        Get the set of method names to exclude from tool discovery.
        
        Classes can define `_get_excluded_methods` as a classmethod to add custom exclusions.
        
        Args:
            mcs: The metaclass being used
            cls: The class being processed
            
        Returns:
            Set of method names to exclude
        """
        excluded = set(ToolsMeta.DEFAULT_EXCLUDED)
        
        # Allow the class itself to add custom exclusions via _get_excluded_methods classmethod
        # Check if the class defines its own _get_excluded_methods (not inherited from metaclass)
        # We need to check if it's actually defined on the class and is a classmethod
        if '_get_excluded_methods' in cls.__dict__:
            method_descriptor = cls.__dict__['_get_excluded_methods']
            # Check if it's a classmethod descriptor (not the staticmethod from ToolsMeta)
            if isinstance(method_descriptor, classmethod):
                # Get the bound method and call it
                bound_method = method_descriptor.__get__(cls, cls)
                excluded.update(bound_method())
            # Also handle if it's already a bound method (shouldn't happen, but be safe)
            elif inspect.ismethod(method_descriptor) and method_descriptor.__self__ is cls:
                excluded.update(method_descriptor())
        
        return excluded
    
    @staticmethod
    def _create_tool_list(cls: type) -> List[Any]:
        """
        Create a list of wrapped function tools from the class methods.
        
        Args:
            cls: The class containing the methods
            
        Returns:
            List of wrapped function tools
            
        Notes:
            Uses strict_mode=False to allow flexible return types like Dict[str, Any].
            This is necessary because many API wrapper methods return dynamic dictionaries.
        """
        return [function_tool(getattr(cls, tool), strict_mode=False) for tool in cls.spec_functions]

