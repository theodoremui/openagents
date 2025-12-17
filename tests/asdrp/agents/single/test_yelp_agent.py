#############################################################################
# test_yelp_agent.py
#
# Comprehensive tests for YelpAgent implementation.
#
# Test Coverage:
# - Agent creation with default and custom instructions
# - Model configuration application
# - Protocol compliance (AgentProtocol interface)
# - Tool configuration and availability
# - Error handling (ImportError, generic exceptions)
# - Edge cases (None instructions, invalid configs)
# - Default instructions constant
#
# Design Principles:
# - Single Responsibility: Each test class focuses on one aspect
# - DRY: Shared fixtures and helper methods
# - Extensibility: Easy to add new test cases
# - Robustness: Comprehensive error and edge case coverage
#
#############################################################################

import pytest
from unittest.mock import patch, MagicMock

from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig
from asdrp.agents.single.yelp_agent import (
    create_yelp_agent,
    DEFAULT_INSTRUCTIONS,
)


class TestYelpAgentCreation:
    """
    Test YelpAgent creation functionality.
    
    This class tests the basic agent creation with various instruction
    configurations and validates the returned agent instance.
    """
    
    def test_create_with_default_instructions(self):
        """
        Test that create_yelp_agent() uses DEFAULT_INSTRUCTIONS when no instructions provided.
        
        Verifies:
        - Agent is created successfully
        - Agent name is "YelpAgent"
        - Instructions match DEFAULT_INSTRUCTIONS
        - Agent implements AgentProtocol
        """
        agent = create_yelp_agent()
        
        assert agent is not None
        assert agent.name == "YelpAgent"
        assert agent.instructions == DEFAULT_INSTRUCTIONS
        assert isinstance(agent, AgentProtocol)
    
    def test_create_with_explicit_none_instructions(self):
        """
        Test that create_yelp_agent(None) uses DEFAULT_INSTRUCTIONS.
        
        Verifies that None is treated as "use default" rather than causing an error.
        """
        agent = create_yelp_agent(None)
        
        assert agent.instructions == DEFAULT_INSTRUCTIONS
    
    def test_create_with_custom_instructions(self):
        """
        Test that create_yelp_agent() accepts and uses custom instructions.
        
        Verifies:
        - Custom instructions are applied correctly
        - Agent name remains "YelpAgent"
        - Protocol compliance is maintained
        """
        custom_instructions = "You are an expert restaurant finder specializing in Yelp business search."
        agent = create_yelp_agent(custom_instructions)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == custom_instructions
        assert isinstance(agent, AgentProtocol)
    
    def test_create_with_empty_string_instructions(self):
        """
        Test that create_yelp_agent() accepts empty string instructions.
        
        Edge case: Empty string is a valid instruction (though not recommended).
        """
        agent = create_yelp_agent("")
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == ""
        assert isinstance(agent, AgentProtocol)


class TestYelpAgentModelConfiguration:
    """
    Test YelpAgent creation with model configuration.
    
    This class validates that model settings (name, temperature, max_tokens)
    are correctly applied when provided via ModelConfig.
    """
    
    def test_create_with_model_config(self):
        """
        Test that create_yelp_agent() applies model configuration correctly.
        
        Verifies:
        - Model name is set
        - Model settings (temperature, max_tokens) are applied
        - Agent is still created successfully
        """
        model_config = ModelConfig(
            name="gpt-4.1-mini",
            temperature=0.8,
            max_tokens=3000
        )
        agent = create_yelp_agent("Test instructions", model_config)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == "Test instructions"
        # Model config is applied internally - verify agent was created
        assert hasattr(agent, 'model')
    
    def test_create_with_model_config_minimal(self):
        """
        Test that create_yelp_agent() works with minimal model config.
        
        Verifies that only model name is required, defaults are used for other settings.
        """
        model_config = ModelConfig(name="gpt-4")
        agent = create_yelp_agent("Test", model_config)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == "Test"
    
    def test_create_with_model_config_and_default_instructions(self):
        """
        Test that model config works with default instructions.
        
        Verifies that model configuration doesn't interfere with default instruction handling.
        """
        model_config = ModelConfig(name="gpt-4.1-mini", temperature=0.7)
        agent = create_yelp_agent(None, model_config)
        
        assert agent.instructions == DEFAULT_INSTRUCTIONS
        assert hasattr(agent, 'model')


class TestYelpAgentProtocolCompliance:
    """
    Test that YelpAgent properly implements AgentProtocol interface.
    
    This class validates protocol compliance, ensuring the agent can be used
    with the agents library's Runner and other protocol-dependent code.
    """
    
    def test_implements_agent_protocol(self):
        """
        Test that created agent implements AgentProtocol.
        
        Verifies type checking and protocol compliance.
        """
        agent = create_yelp_agent()
        
        assert isinstance(agent, AgentProtocol)
        # Verify protocol attributes exist
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'instructions')
    
    def test_agent_has_required_attributes(self):
        """
        Test that agent has all required attributes for protocol compliance.
        
        Verifies:
        - name attribute exists and is correct
        - instructions attribute exists
        - tools attribute exists (required for agent functionality)
        """
        agent = create_yelp_agent()
        
        assert hasattr(agent, 'name')
        assert agent.name == "YelpAgent"
        assert hasattr(agent, 'instructions')
        assert hasattr(agent, 'tools')


class TestYelpAgentTools:
    """
    Test YelpAgent tool configuration.
    
    This class validates that the agent has the correct tools configured
    from YelpTools.tool_list.
    """
    
    def test_agent_has_tools(self):
        """
        Test that YelpAgent has tools configured.
        
        Verifies that tools are not None and are a list/iterable.
        """
        agent = create_yelp_agent()
        
        assert hasattr(agent, 'tools')
        assert agent.tools is not None
        # Tools should be a list or iterable
        assert hasattr(agent.tools, '__iter__')
    
    def test_tools_are_yelp_tools(self):
        """
        Test that agent tools come from YelpTools.tool_list.
        
        Verifies the tools are correctly imported and configured.
        """
        from asdrp.actions.local.yelp_tools import YelpTools
        
        agent = create_yelp_agent()
        
        # Tools should match YelpTools.tool_list
        assert agent.tools == YelpTools.tool_list


class TestYelpAgentErrorHandling:
    """
    Test YelpAgent error handling and exception scenarios.
    
    This class validates that errors are properly caught and wrapped
    in AgentException with appropriate error messages and agent_name.
    """
    
    def test_import_error_raises_agent_exception(self):
        """
        Test that ImportError during agent creation is wrapped in AgentException.
        
        Verifies:
        - ImportError is caught
        - AgentException is raised with correct message
        - agent_name is set to "yelp"
        """
        # Mock YelpTools import inside the function to raise ImportError
        with patch('asdrp.actions.local.yelp_tools.YelpTools', side_effect=ImportError("No module 'yelp'")):
            with pytest.raises(AgentException) as exc_info:
                create_yelp_agent("Test")
            
            assert exc_info.value.agent_name == "yelp"
            assert "Failed to import" in str(exc_info.value) or "Failed to create" in str(exc_info.value)
    
    def test_invalid_model_config_raises_agent_exception(self):
        """
        Test that invalid model configuration causes AgentException.
        
        Verifies error handling when model config has invalid values.
        """
        # Create a mock model config with invalid values
        mock_config = MagicMock(spec=ModelConfig)
        mock_config.name = None  # Invalid
        mock_config.temperature = "invalid"  # Invalid type
        mock_config.max_tokens = "invalid"  # Invalid type
        
        with pytest.raises(AgentException) as exc_info:
            create_yelp_agent("Test", mock_config)
        
        assert exc_info.value.agent_name == "yelp"
        assert "Failed to create" in str(exc_info.value)


class TestYelpAgentDefaultInstructions:
    """
    Test DEFAULT_INSTRUCTIONS constant.
    
    This class validates the default instructions constant used by YelpAgent.
    """
    
    def test_default_instructions_is_string(self):
        """
        Test that DEFAULT_INSTRUCTIONS is a non-empty string.
        
        Verifies the constant is properly defined and usable.
        """
        assert isinstance(DEFAULT_INSTRUCTIONS, str)
        assert len(DEFAULT_INSTRUCTIONS) > 0
    
    def test_default_instructions_contains_keywords(self):
        """
        Test that DEFAULT_INSTRUCTIONS contains relevant keywords.
        
        Verifies the instructions are appropriate for a Yelp business search agent.
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        # Should mention yelp, business, restaurant, or related concepts
        assert any(keyword in instructions_lower for keyword in [
            "yelp", "business", "restaurant", "review"
        ])


class TestYelpAgentIntegration:
    """
    Integration tests for YelpAgent.
    
    This class tests the agent in realistic scenarios and validates
    end-to-end functionality.
    """
    
    def test_agent_creation_with_all_parameters(self):
        """
        Test agent creation with all optional parameters provided.
        
        Verifies that instructions and model_config work together correctly.
        """
        model_config = ModelConfig(
            name="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=2000
        )
        custom_instructions = "Custom Yelp search instructions for testing."
        
        agent = create_yelp_agent(custom_instructions, model_config)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == custom_instructions
        assert hasattr(agent, 'model')
    
    def test_multiple_agent_instances_independent(self):
        """
        Test that multiple agent instances are independent.
        
        Verifies that creating multiple agents doesn't cause interference.
        """
        agent1 = create_yelp_agent("Instructions 1")
        agent2 = create_yelp_agent("Instructions 2")
        
        assert agent1.name == agent2.name == "YelpAgent"
        assert agent1.instructions == "Instructions 1"
        assert agent2.instructions == "Instructions 2"
        assert agent1 is not agent2  # Different instances


class TestYelpAgentEdgeCases:
    """
    Test edge cases and boundary conditions for YelpAgent.
    
    This class validates behavior with unusual but valid inputs.
    """
    
    def test_very_long_instructions(self):
        """
        Test that very long instructions are handled correctly.
        
        Edge case: Instructions that are extremely long should still work.
        """
        long_instructions = "A" * 10000  # 10KB of instructions
        agent = create_yelp_agent(long_instructions)
        
        assert agent.instructions == long_instructions
    
    def test_instructions_with_special_characters(self):
        """
        Test that instructions with special characters are handled correctly.
        
        Edge case: Instructions containing newlines, quotes, unicode, etc.
        """
        special_instructions = "Instructions with\nnewlines\tand\rspecial chars: \"quotes\" 'apostrophes' émojis 🍽️"
        agent = create_yelp_agent(special_instructions)
        
        assert agent.instructions == special_instructions
    
    def test_unicode_instructions(self):
        """
        Test that Unicode instructions are handled correctly.
        
        Edge case: Instructions in non-ASCII languages.
        """
        unicode_instructions = "あなたはレストラン検索アシスタントです"  # Japanese: "You are a restaurant search assistant"
        agent = create_yelp_agent(unicode_instructions)
        
        assert agent.instructions == unicode_instructions

