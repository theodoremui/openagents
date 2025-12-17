"""Shared fixtures for MoE tests."""

import sys
import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path

# Ensure repo root is on sys.path so `import asdrp` works when running pytest
# without installing the package.
_p = Path(__file__).resolve()
_PROJECT_ROOT = None
for parent in [_p.parent, *_p.parents]:
    # Prefer the repo root (contains both runtime package `asdrp/` and `config/open_agents.yaml`)
    if (parent / "asdrp").is_dir() and (parent / "config" / "open_agents.yaml").exists():
        _PROJECT_ROOT = parent
        break
if _PROJECT_ROOT and str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from asdrp.orchestration.moe.config_loader import (
    MoEConfig,
    MoEConfigLoader,
    ExpertGroupConfig,
    MoECacheConfig,
)
from asdrp.agents.config_loader import ModelConfig


@pytest.fixture
def mock_model_config():
    """Mock model configuration."""
    return ModelConfig(
        name="gpt-4.1-mini",
        temperature=0.7,
        max_tokens=2000
    )


@pytest.fixture
def mock_expert_group_config():
    """Mock expert group configuration."""
    return ExpertGroupConfig(
        agents=["one", "perplexity"],
        capabilities=["web_search", "realtime", "search"],
        weight=1.0
    )


@pytest.fixture
def mock_moe_config(mock_model_config):
    """Mock MoE configuration."""
    return MoEConfig(
        enabled=True,
        moe={
            "selection_strategy": "capability_match",
            "top_k_experts": 3,
            "confidence_threshold": 0.3,
            "mixing_strategy": "synthesis",
            "parallel_execution": True,
            "max_concurrent": 10,
            "timeout_per_expert": 10.0,
            "overall_timeout": 30.0,
        },
        models={
            "selection": mock_model_config,
            "mixing": mock_model_config,
        },
        experts={
            "search_expert": ExpertGroupConfig(
                agents=["one", "perplexity"],
                capabilities=["web_search", "realtime", "search"],
                weight=1.0
            ),
            "location_expert": ExpertGroupConfig(
                agents=["geo", "map"],
                capabilities=["geocoding", "directions", "places"],
                weight=1.0
            ),
            "business_expert": ExpertGroupConfig(
                agents=["yelp"],
                capabilities=["local_business", "reviews", "restaurants"],
                weight=1.0
            ),
        },
        cache=MoECacheConfig(
            enabled=True,
            type="semantic",
            storage={"backend": "sqlite", "path": "test.db"},
            policy={"similarity_threshold": 0.9, "ttl": 3600, "max_entries": 1000}
        ),
        error_handling={
            "timeout": 30.0,
            "retries": 2,
            "fallback_agent": "one",
            "fallback_message": "I apologize, but I encountered an issue."
        },
        tracing={
            "enabled": True,
            "storage": {"backend": "sqlite", "path": "traces.db"},
            "exporters": []
        }
    )


@pytest.fixture
def mock_agent_factory():
    """Mock AgentFactory."""
    factory = Mock()

    # Mock agent
    mock_agent = Mock()
    mock_agent.name = "TestAgent"
    mock_agent.instructions = "Test instructions"

    # Mock session
    mock_session = Mock()

    # Setup async mock for both methods
    factory.get_agent_with_session = AsyncMock(
        return_value=(mock_agent, mock_session)
    )
    factory.get_agent_with_persistent_session = AsyncMock(
        return_value=(mock_agent, mock_session)
    )

    return factory


@pytest.fixture
def sample_query():
    """Sample query for testing."""
    return "Find pizza restaurants near San Francisco"


@pytest.fixture
def sample_context():
    """Sample context for testing."""
    return {
        "location": {"latitude": 37.7749, "longitude": -122.4194},
        "user_preferences": {"cuisine": "italian"}
    }
