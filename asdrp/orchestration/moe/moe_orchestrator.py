"""
MoE (Mixture of Experts) Orchestrator Agent

This module provides a factory function for creating MoE orchestrator agents
that can be used in the agent configuration system.
"""

from typing import Any, Dict, Optional
from asdrp.agents.config_loader import ModelConfig
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.orchestration.moe.config_loader import load_moe_config


def create_moe_orchestrator(
    instructions: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
) -> MoEOrchestrator:
    """
    Factory function for creating MoE orchestrator instances.

    Args:
        instructions: System instructions (not used by MoE, as it coordinates agents)
        model_config: Model configuration for the orchestrator

    Returns:
        MoEOrchestrator instance configured with moe.yaml settings
    """
    # Load MoE configuration from moe.yaml
    config = load_moe_config()

    # Get the agent factory instance
    from asdrp.agents.agent_factory import AgentFactory
    agent_factory = AgentFactory.instance()

    # Create orchestrator with default components
    orchestrator = MoEOrchestrator.create_default(agent_factory, config)

    # Set name and instructions for protocol compatibility
    orchestrator.name = "MoE Orchestrator"
    orchestrator.instructions = instructions or (
        "I am an intelligent Mixture of Experts orchestrator that coordinates "
        "specialized agents to answer your queries comprehensively."
    )

    return orchestrator
