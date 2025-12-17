"""
MoE (Mixture of Experts) Orchestrator.

A three-tier orchestration system that:
1. Selects relevant expert agents based on query analysis
2. Executes selected experts in parallel
3. Synthesizes expert outputs into coherent response
"""

"""
NOTE on imports:

This package is imported by many modules (including tests and config loaders).
Importing heavyweight modules here (e.g. orchestrator → fast_path → optional deps)
can cause unnecessary hard dependency failures at import-time.

We therefore expose the public API via *lazy imports* using __getattr__ so that:
- `import asdrp.orchestration.moe` is cheap and side-effect free
- consumers can still do `from asdrp.orchestration.moe import MoEOrchestrator`
"""

from typing import Any

_LAZY_EXPORTS = {
    # Orchestrator / results
    "MoEOrchestrator": ("asdrp.orchestration.moe.orchestrator", "MoEOrchestrator"),
    "MoEResult": ("asdrp.orchestration.moe.orchestrator", "MoEResult"),
    "MoETrace": ("asdrp.orchestration.moe.orchestrator", "MoETrace"),
    # Config
    "MoEConfigLoader": ("asdrp.orchestration.moe.config_loader", "MoEConfigLoader"),
    "MoEConfig": ("asdrp.orchestration.moe.config_loader", "MoEConfig"),
    "load_moe_config": ("asdrp.orchestration.moe.config_loader", "load_moe_config"),
    # Exceptions
    "MoEException": ("asdrp.orchestration.moe.exceptions", "MoEException"),
    "ConfigException": ("asdrp.orchestration.moe.exceptions", "ConfigException"),
    "ExpertSelectionException": ("asdrp.orchestration.moe.exceptions", "ExpertSelectionException"),
    "ExecutionException": ("asdrp.orchestration.moe.exceptions", "ExecutionException"),
    "MixingException": ("asdrp.orchestration.moe.exceptions", "MixingException"),
    "CacheException": ("asdrp.orchestration.moe.exceptions", "CacheException"),
}

__all__ = [
    "MoEOrchestrator",
    "MoEResult",
    "MoETrace",
    "MoEConfigLoader",
    "MoEConfig",
    "load_moe_config",
    "MoEException",
    "ConfigException",
    "ExpertSelectionException",
    "ExecutionException",
    "MixingException",
    "CacheException",
]

__version__ = "1.0.0"


def __getattr__(name: str) -> Any:
    """
    Lazy attribute access for public exports.

    This is the recommended pattern for optional/heavy dependencies in a package __init__.
    """
    if name in _LAZY_EXPORTS:
        import importlib

        module_name, attr = _LAZY_EXPORTS[name]
        mod = importlib.import_module(module_name)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
