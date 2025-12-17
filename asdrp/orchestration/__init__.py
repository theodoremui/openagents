"""
OpenAgents Orchestration Layer.

This package contains orchestration strategies for coordinating multiple agents:
- MoE (Mixture of Experts): Dynamic expert selection and parallel execution
- SmartRouter: Multi-phase query decomposition and routing

All orchestration code has been consolidated here from the legacy asdrp.agents.router
and asdrp.agents.orchestration packages.
"""

__version__ = "1.0.0"

__all__ = ["moe", "smartrouter"]
