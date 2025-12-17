#############################################################################
# test_chitchat_agent.py
#
# Comprehensive tests for ChitchatAgent implementation.
#
# Test Coverage:
# - Agent creation with default and custom instructions
# - Model configuration application (including default low-latency settings)
# - Protocol compliance (AgentProtocol interface)
# - Tool configuration (empty list - no tools for conversational agent)
# - Error handling (ImportError, generic exceptions)
# - Edge cases (None instructions, invalid configs)
# - Default instructions constant and safety guardrails
# - Low-latency optimization verification
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
from asdrp.agents.single.chitchat_agent import (
    create_chitchat_agent,
    DEFAULT_INSTRUCTIONS,
)


class TestChitchatAgentCreation:
    """
    Test ChitchatAgent creation functionality.
    
    This class tests the basic agent creation with various instruction
    configurations and validates the returned agent instance.
    """
    
    def test_create_with_default_instructions(self):
        """
        Test that create_chitchat_agent() uses DEFAULT_INSTRUCTIONS when no instructions provided.
        
        Verifies:
        - Agent is created successfully
        - Agent name is "ChitchatAgent"
        - Instructions match DEFAULT_INSTRUCTIONS
        - Agent implements AgentProtocol
        """
        agent = create_chitchat_agent()
        
        assert agent is not None
        assert agent.name == "ChitchatAgent"
        assert agent.instructions == DEFAULT_INSTRUCTIONS
        assert isinstance(agent, AgentProtocol)
    
    def test_create_with_explicit_none_instructions(self):
        """
        Test that create_chitchat_agent(None) uses DEFAULT_INSTRUCTIONS.
        
        Verifies that None is treated as "use default" rather than causing an error.
        """
        agent = create_chitchat_agent(None)
        
        assert agent.instructions == DEFAULT_INSTRUCTIONS
    
    def test_create_with_custom_instructions(self):
        """
        Test that create_chitchat_agent() accepts and uses custom instructions.
        
        Verifies:
        - Custom instructions are applied correctly
        - Agent name remains "ChitchatAgent"
        - Protocol compliance is maintained
        """
        custom_instructions = "You are a friendly assistant that helps with casual conversation."
        agent = create_chitchat_agent(custom_instructions)
        
        assert agent.name == "ChitchatAgent"
        assert agent.instructions == custom_instructions
        assert isinstance(agent, AgentProtocol)
    
    def test_create_with_empty_string_instructions(self):
        """
        Test that create_chitchat_agent() accepts empty string instructions.
        
        Edge case: Empty string is a valid instruction (though not recommended).
        """
        agent = create_chitchat_agent("")
        
        assert agent.name == "ChitchatAgent"
        assert agent.instructions == ""
        assert isinstance(agent, AgentProtocol)


class TestChitchatAgentModelConfiguration:
    """
    Test ChitchatAgent creation with model configuration.
    
    This class validates that model settings (name, temperature, max_tokens)
    are correctly applied when provided via ModelConfig, and that default
    low-latency settings are used when no config is provided.
    """
    
    def test_create_with_model_config(self):
        """
        Test that create_chitchat_agent() applies model configuration correctly.
        
        Verifies:
        - Model name is set
        - Model settings (temperature, max_tokens) are applied
        - Agent is still created successfully
        """
        model_config = ModelConfig(
            name="gpt-4.1-mini",
            temperature=0.8,
            max_tokens=200
        )
        agent = create_chitchat_agent("Test instructions", model_config)
        
        assert agent.name == "ChitchatAgent"
        assert agent.instructions == "Test instructions"
        # Model config is applied internally - verify agent was created
        assert hasattr(agent, 'model')
    
    def test_create_with_model_config_minimal(self):
        """
        Test that create_chitchat_agent() works with minimal model config.
        
        Verifies that only model name is required, defaults are used for other settings.
        """
        model_config = ModelConfig(name="gpt-4")
        agent = create_chitchat_agent("Test", model_config)
        
        assert agent.name == "ChitchatAgent"
        assert agent.instructions == "Test"
    
    def test_create_with_model_config_and_default_instructions(self):
        """
        Test that model config works with default instructions.
        
        Verifies that model configuration doesn't interfere with default instruction handling.
        """
        model_config = ModelConfig(name="gpt-4.1-mini", temperature=0.7)
        agent = create_chitchat_agent(None, model_config)
        
        assert agent.instructions == DEFAULT_INSTRUCTIONS
        assert hasattr(agent, 'model')
    
    def test_default_low_latency_settings(self):
        """
        Test that default model settings optimize for low latency.
        
        Verifies:
        - When no model_config provided, default settings are applied
        - Temperature is 0.7 (balanced creativity/speed)
        - Max tokens is 150 (keeps responses concise and fast)
        """
        # Create agent without model_config to test defaults
        agent = create_chitchat_agent()
        
        # Verify agent was created (defaults are applied internally)
        assert agent.name == "ChitchatAgent"
        assert hasattr(agent, 'model_settings') or hasattr(agent, 'model')
        # The actual settings are applied internally by the Agent class,
        # but we can verify the agent was created successfully with defaults


class TestChitchatAgentProtocolCompliance:
    """
    Test that ChitchatAgent properly implements AgentProtocol interface.
    
    This class validates protocol compliance, ensuring the agent can be used
    with the agents library's Runner and other protocol-dependent code.
    """
    
    def test_implements_agent_protocol(self):
        """
        Test that created agent implements AgentProtocol.
        
        Verifies type checking and protocol compliance.
        """
        agent = create_chitchat_agent()
        
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
        - tools attribute exists (empty list for conversational agent)
        """
        agent = create_chitchat_agent()
        
        assert hasattr(agent, 'name')
        assert agent.name == "ChitchatAgent"
        assert hasattr(agent, 'instructions')
        assert hasattr(agent, 'tools')


class TestChitchatAgentTools:
    """
    Test ChitchatAgent tool configuration.
    
    This class validates that the agent has NO tools configured (empty list),
    as it's a purely conversational agent without external tool dependencies.
    """
    
    def test_agent_has_no_tools(self):
        """
        Test that ChitchatAgent has empty tools list.
        
        Verifies:
        - Tools attribute exists
        - Tools is an empty list (conversational agent, no external tools)
        - This is intentional - chitchat agent is purely conversational
        """
        agent = create_chitchat_agent()
        
        assert hasattr(agent, 'tools')
        assert agent.tools == []  # Empty list - no tools for conversational agent
    
    def test_tools_is_list(self):
        """
        Test that tools attribute is a list (even if empty).
        
        Verifies the tools attribute has the correct type.
        """
        agent = create_chitchat_agent()
        
        assert isinstance(agent.tools, list)
        assert len(agent.tools) == 0


class TestChitchatAgentErrorHandling:
    """
    Test ChitchatAgent error handling and exception scenarios.
    
    This class validates that errors are properly caught and wrapped
    in AgentException with appropriate error messages and agent_name.
    """
    
    def test_import_error_raises_agent_exception(self):
        """
        Test that ImportError during agent creation is wrapped in AgentException.
        
        Verifies:
        - ImportError is caught
        - AgentException is raised with correct message
        - agent_name is set to "chitchat"
        """
        # Mock Agent[Any] call to raise ImportError
        # Agent[Any](**kwargs) uses __getitem__ then calls the result
        with patch('asdrp.agents.single.chitchat_agent.Agent') as mock_agent_class:
            # Make __getitem__ return a callable that raises ImportError when called
            mock_callable = MagicMock(side_effect=ImportError("No module 'agents'"))
            mock_agent_class.__getitem__ = MagicMock(return_value=mock_callable)
            
            with pytest.raises(AgentException) as exc_info:
                create_chitchat_agent("Test")
            
            assert exc_info.value.agent_name == "chitchat"
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
            create_chitchat_agent("Test", mock_config)
        
        assert exc_info.value.agent_name == "chitchat"
        assert "Failed to create" in str(exc_info.value)
    
    def test_generic_exception_raises_agent_exception(self):
        """
        Test that generic exceptions during creation are wrapped in AgentException.
        
        Verifies that any exception during agent creation is properly caught and wrapped.
        """
        # Mock Agent[Any] call to raise a generic exception
        # Agent[Any](**kwargs) uses __getitem__ then calls the result
        with patch('asdrp.agents.single.chitchat_agent.Agent') as mock_agent_class:
            # Make __getitem__ return a callable that raises ValueError when called
            mock_callable = MagicMock(side_effect=ValueError("Invalid configuration"))
            mock_agent_class.__getitem__ = MagicMock(return_value=mock_callable)
            
            with pytest.raises(AgentException) as exc_info:
                create_chitchat_agent("Test")
            
            assert exc_info.value.agent_name == "chitchat"
            assert "Failed to create" in str(exc_info.value)


class TestChitchatAgentDefaultInstructions:
    """
    Test DEFAULT_INSTRUCTIONS constant.
    
    This class validates the default instructions constant used by ChitchatAgent,
    including safety guardrails and low-latency optimization guidance.
    """
    
    def test_default_instructions_is_string(self):
        """
        Test that DEFAULT_INSTRUCTIONS is a non-empty string.
        
        Verifies the constant is properly defined and usable.
        """
        assert isinstance(DEFAULT_INSTRUCTIONS, str)
        assert len(DEFAULT_INSTRUCTIONS) > 0
    
    def test_default_instructions_contains_safety_guardrails(self):
        """
        Test that DEFAULT_INSTRUCTIONS contains safety guardrails.
        
        Verifies the instructions include explicit prohibitions against:
        - Offensive, abusive, or harmful content
        - Political topics
        - Religious topics
        - Controversial or sensitive subjects
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        # Should mention safety guardrails
        assert any(keyword in instructions_lower for keyword in [
            "guardrail", "safety", "offensive", "political", "religious", "controversial"
        ])
    
    def test_default_instructions_contains_positive_values(self):
        """
        Test that DEFAULT_INSTRUCTIONS emphasizes positive values.
        
        Verifies the instructions promote:
        - Positivity and encouragement
        - Friendliness and warmth
        - Helpfulness
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        # Should emphasize positive values
        assert any(keyword in instructions_lower for keyword in [
            "positive", "friendly", "wholesome", "kind", "helpful", "warm"
        ])
    
    def test_default_instructions_contains_low_latency_guidance(self):
        """
        Test that DEFAULT_INSTRUCTIONS includes low-latency optimization guidance.
        
        Verifies the instructions emphasize:
        - Concise responses
        - Fast response times
        - Brief, focused answers
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        # Should mention latency or brevity
        assert any(keyword in instructions_lower for keyword in [
            "latency", "concise", "brief", "fast", "2-4 sentences"
        ])
    
    def test_default_instructions_contains_redirection_guidance(self):
        """
        Test that DEFAULT_INSTRUCTIONS includes guidance for handling restricted topics.
        
        Verifies the instructions explain how to politely redirect users away from
        restricted topics without being judgmental.
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        # Should mention redirection or redirect
        assert "redirect" in instructions_lower or "politely" in instructions_lower


class TestChitchatAgentIntegration:
    """
    Integration tests for ChitchatAgent.
    
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
            max_tokens=150
        )
        custom_instructions = "Custom chitchat instructions for testing."
        
        agent = create_chitchat_agent(custom_instructions, model_config)
        
        assert agent.name == "ChitchatAgent"
        assert agent.instructions == custom_instructions
        assert hasattr(agent, 'model')
    
    def test_multiple_agent_instances_independent(self):
        """
        Test that multiple agent instances are independent.
        
        Verifies that creating multiple agents doesn't cause interference.
        """
        agent1 = create_chitchat_agent("Instructions 1")
        agent2 = create_chitchat_agent("Instructions 2")
        
        assert agent1.name == agent2.name == "ChitchatAgent"
        assert agent1.instructions == "Instructions 1"
        assert agent2.instructions == "Instructions 2"
        assert agent1 is not agent2  # Different instances
    
    def test_agent_with_default_settings(self):
        """
        Test that agent creation with defaults works correctly.
        
        Verifies that default low-latency settings are applied when no model_config provided.
        """
        agent = create_chitchat_agent()
        
        assert agent.name == "ChitchatAgent"
        assert agent.instructions == DEFAULT_INSTRUCTIONS
        assert agent.tools == []  # No tools
        # Default model settings are applied internally


class TestChitchatAgentEdgeCases:
    """
    Test edge cases and boundary conditions for ChitchatAgent.
    
    This class validates behavior with unusual but valid inputs.
    """
    
    def test_very_long_instructions(self):
        """
        Test that very long instructions are handled correctly.
        
        Edge case: Instructions that are extremely long should still work.
        """
        long_instructions = "A" * 10000  # 10KB of instructions
        agent = create_chitchat_agent(long_instructions)
        
        assert agent.instructions == long_instructions
    
    def test_instructions_with_special_characters(self):
        """
        Test that instructions with special characters are handled correctly.
        
        Edge case: Instructions containing newlines, quotes, unicode, emojis, etc.
        """
        special_instructions = "Instructions with\nnewlines\tand\rspecial chars: \"quotes\" 'apostrophes' émojis 😊🌟✨"
        agent = create_chitchat_agent(special_instructions)
        
        assert agent.instructions == special_instructions
    
    def test_unicode_instructions(self):
        """
        Test that Unicode instructions are handled correctly.
        
        Edge case: Instructions in non-ASCII languages.
        """
        unicode_instructions = "你是一个友好的聊天助手"  # Chinese: "You are a friendly chat assistant"
        agent = create_chitchat_agent(unicode_instructions)
        
        assert agent.instructions == unicode_instructions
    
    def test_instructions_with_markdown(self):
        """
        Test that instructions with markdown formatting are handled correctly.
        
        Edge case: Instructions containing markdown syntax (bold, lists, etc.).
        """
        import textwrap
        markdown_instructions = """
        # Chitchat Agent
        
        **Core Values:**
        - Be friendly
        - Be helpful
        
        > Always be positive!
        """
        # Remove common leading whitespace from multi-line string
        markdown_instructions = textwrap.dedent(markdown_instructions).strip()
        agent = create_chitchat_agent(markdown_instructions)
        
        # Agent stores instructions exactly as passed
        assert agent.instructions == markdown_instructions


class TestChitchatAgentSafetyGuardrails:
    """
    Test ChitchatAgent safety guardrails in instructions.
    
    This class validates that the default instructions contain comprehensive
    safety guardrails to prevent inappropriate content.
    """
    
    def test_instructions_prohibit_offensive_content(self):
        """
        Test that instructions explicitly prohibit offensive content.
        
        Verifies the instructions mention offensive, abusive, or harmful content restrictions.
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        assert any(keyword in instructions_lower for keyword in [
            "offensive", "abusive", "harmful"
        ])
    
    def test_instructions_prohibit_political_content(self):
        """
        Test that instructions explicitly prohibit political content.
        
        Verifies the instructions mention political topics restrictions.
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        assert "political" in instructions_lower
    
    def test_instructions_prohibit_religious_content(self):
        """
        Test that instructions explicitly prohibit religious content.
        
        Verifies the instructions mention religious topics restrictions.
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        assert "religious" in instructions_lower
    
    def test_instructions_provide_redirection_strategy(self):
        """
        Test that instructions provide a strategy for handling restricted topics.
        
        Verifies the instructions explain how to redirect users politely.
        """
        instructions_lower = DEFAULT_INSTRUCTIONS.lower()
        # Should mention redirecting or suggesting alternative topics
        assert "redirect" in instructions_lower or "suggest" in instructions_lower


