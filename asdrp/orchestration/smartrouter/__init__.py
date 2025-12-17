"""
SmartRouter - Advanced Multi-Agent Orchestration System

This package implements a sophisticated orchestrator that uses LLMs to interpret,
decompose, route, and synthesize complex queries across multiple specialist agents.

Components:
-----------
- QueryInterpreter: Parses and classifies user queries
- QueryDecomposer: Breaks queries into independent subqueries
- CapabilityRouter: Selects agents based on capability maps
- AsyncSubqueryDispatcher: Dispatches subqueries asynchronously
- ResponseAggregator: Collects and organizes agent responses
- ResultSynthesizer: Merges responses into coherent answers
- LLMJudge: Evaluates answer quality and triggers fallbacks

Design Principles:
-----------------
- SOLID: Single Responsibility, Open/Closed, Liskov Substitution,
  Interface Segregation, Dependency Inversion
- DRY: Reusable logic in well-named methods
- Dependency Injection: Model clients, agent registries injected
- Extensibility: Easy to add new routing strategies
- Robustness: Domain-specific exceptions with meaningful messages

Usage:
------
>>> from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
>>> from asdrp.orchestration.smartrouter.config_loader import SmartRouterConfigLoader
>>>
>>> config = SmartRouterConfigLoader()
>>> router = SmartRouter(config)
>>> result = await router.route_query("Complex query here")
"""

from asdrp.orchestration.smartrouter.exceptions import (
    SmartRouterException,
    QueryDecompositionException,
    RoutingException,
    DispatchException,
    SynthesisException,
    EvaluationException,
)

__all__ = [
    "SmartRouterException",
    "QueryDecompositionException",
    "RoutingException",
    "DispatchException",
    "SynthesisException",
    "EvaluationException",
]
