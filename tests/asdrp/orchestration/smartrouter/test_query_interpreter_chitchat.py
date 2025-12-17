"""
Tests for QueryInterpreter chitchat/social query detection.

This module tests the QueryInterpreter's ability to detect and classify
chitchat/social queries like greetings, farewells, gratitude, etc.
"""

import pytest
from asdrp.orchestration.smartrouter.query_interpreter import QueryInterpreter
from asdrp.orchestration.smartrouter.interfaces import QueryComplexity
from asdrp.orchestration.smartrouter.config_loader import ModelConfig


@pytest.fixture
def interpreter():
    """Create a QueryInterpreter instance for testing."""
    model_config = ModelConfig(
        name="gpt-4.1-mini",
        temperature=0.3,
        max_tokens=500
    )
    return QueryInterpreter(model_config=model_config)


class TestChitchatDetectionGreetings:
    """Test detection of greeting patterns."""

    @pytest.mark.asyncio
    async def test_simple_hi(self, interpreter):
        """Test detection of 'hi' as chitchat."""
        intent = interpreter._fallback_interpretation("hi")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains
        assert "social" in intent.domains
        assert intent.requires_synthesis is False
        assert intent.metadata.get("is_chitchat") is True

    @pytest.mark.asyncio
    async def test_hello_with_punctuation(self, interpreter):
        """Test detection of 'hello!' as chitchat."""
        intent = interpreter._fallback_interpretation("hello!")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains
        assert "social" in intent.domains

    @pytest.mark.asyncio
    async def test_hey_there(self, interpreter):
        """Test detection of 'hey there' as chitchat."""
        intent = interpreter._fallback_interpretation("hey there")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_good_morning(self, interpreter):
        """Test detection of 'good morning' as chitchat."""
        intent = interpreter._fallback_interpretation("good morning")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains
        assert "social" in intent.domains

    @pytest.mark.asyncio
    async def test_good_afternoon(self, interpreter):
        """Test detection of 'good afternoon' as chitchat."""
        intent = interpreter._fallback_interpretation("good afternoon")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_good_evening(self, interpreter):
        """Test detection of 'good evening' as chitchat."""
        intent = interpreter._fallback_interpretation("good evening")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_greetings(self, interpreter):
        """Test detection of 'greetings' as chitchat."""
        intent = interpreter._fallback_interpretation("greetings")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains


class TestChitchatDetectionFarewells:
    """Test detection of farewell patterns."""

    @pytest.mark.asyncio
    async def test_bye(self, interpreter):
        """Test detection of 'bye' as chitchat."""
        intent = interpreter._fallback_interpretation("bye")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains
        assert "social" in intent.domains

    @pytest.mark.asyncio
    async def test_goodbye(self, interpreter):
        """Test detection of 'goodbye' as chitchat."""
        intent = interpreter._fallback_interpretation("goodbye")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_see_you_later(self, interpreter):
        """Test detection of 'see you later' as chitchat."""
        intent = interpreter._fallback_interpretation("see you later")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_farewell(self, interpreter):
        """Test detection of 'farewell' as chitchat."""
        intent = interpreter._fallback_interpretation("farewell")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_take_care(self, interpreter):
        """Test detection of 'take care' as chitchat."""
        intent = interpreter._fallback_interpretation("take care")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains


class TestChitchatDetectionGratitude:
    """Test detection of gratitude patterns."""

    @pytest.mark.asyncio
    async def test_thank_you(self, interpreter):
        """Test detection of 'thank you' as chitchat."""
        intent = interpreter._fallback_interpretation("thank you")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains
        assert "social" in intent.domains

    @pytest.mark.asyncio
    async def test_thanks(self, interpreter):
        """Test detection of 'thanks' as chitchat."""
        intent = interpreter._fallback_interpretation("thanks")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_thank_you_so_much(self, interpreter):
        """Test detection of 'thank you so much' as chitchat."""
        intent = interpreter._fallback_interpretation("thank you so much")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_appreciate(self, interpreter):
        """Test detection of 'appreciate' as chitchat."""
        intent = interpreter._fallback_interpretation("appreciate")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains


class TestChitchatDetectionSocial:
    """Test detection of social conversation patterns."""

    @pytest.mark.asyncio
    async def test_how_are_you(self, interpreter):
        """Test detection of 'how are you' as chitchat."""
        intent = interpreter._fallback_interpretation("how are you")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains
        assert "social" in intent.domains

    @pytest.mark.asyncio
    async def test_whats_up(self, interpreter):
        """Test detection of 'what's up' as chitchat."""
        intent = interpreter._fallback_interpretation("what's up")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_hows_it_going(self, interpreter):
        """Test detection of 'how's it going' as chitchat."""
        intent = interpreter._fallback_interpretation("how's it going")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_how_are_things(self, interpreter):
        """Test detection of 'how are things' as chitchat."""
        intent = interpreter._fallback_interpretation("how are things")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains


class TestChitchatDetectionSmallTalk:
    """Test detection of small talk patterns."""

    @pytest.mark.asyncio
    async def test_nice_weather(self, interpreter):
        """Test detection of 'nice weather' as chitchat."""
        intent = interpreter._fallback_interpretation("nice weather")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_have_a_nice_day(self, interpreter):
        """Test detection of 'have a nice day' as chitchat."""
        intent = interpreter._fallback_interpretation("have a nice day")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_have_a_great_day(self, interpreter):
        """Test detection of 'have a great day' as chitchat."""
        intent = interpreter._fallback_interpretation("have a great day")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_good_luck(self, interpreter):
        """Test detection of 'good luck' as chitchat."""
        intent = interpreter._fallback_interpretation("good luck")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains


class TestNonChitchatQueries:
    """Test that non-chitchat queries are NOT classified as chitchat."""

    @pytest.mark.asyncio
    async def test_stock_query(self, interpreter):
        """Test that stock queries are not classified as chitchat."""
        intent = interpreter._fallback_interpretation("What's the stock price of AAPL?")
        assert "conversation" not in intent.domains
        assert "social" not in intent.domains
        assert "finance" in intent.domains

    @pytest.mark.asyncio
    async def test_location_query(self, interpreter):
        """Test that location queries are not classified as chitchat."""
        intent = interpreter._fallback_interpretation("Where is the nearest restaurant?")
        assert "conversation" not in intent.domains
        assert "geography" in intent.domains

    @pytest.mark.asyncio
    async def test_search_query(self, interpreter):
        """Test that search queries are not classified as chitchat."""
        intent = interpreter._fallback_interpretation("Tell me about quantum physics")
        assert "conversation" not in intent.domains
        # Should default to "search" domain

    @pytest.mark.asyncio
    async def test_wikipedia_query(self, interpreter):
        """Test that Wikipedia queries are not classified as chitchat."""
        intent = interpreter._fallback_interpretation("Wikipedia article about Einstein")
        assert "conversation" not in intent.domains
        assert "wikipedia" in intent.domains


class TestChitchatWithContext:
    """Test chitchat detection with additional context."""

    @pytest.mark.asyncio
    async def test_hi_with_question(self, interpreter):
        """Test that 'hi' at start of query with question is still detected."""
        # "hi" should trigger chitchat detection even with following text
        intent = interpreter._fallback_interpretation("hi there")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_hello_with_name(self, interpreter):
        """Test 'hello' with a name."""
        intent = interpreter._fallback_interpretation("hello John")
        assert intent.complexity == QueryComplexity.SIMPLE
        assert "conversation" in intent.domains

    @pytest.mark.asyncio
    async def test_case_insensitive(self, interpreter):
        """Test that detection is case-insensitive."""
        intent1 = interpreter._fallback_interpretation("HELLO")
        intent2 = interpreter._fallback_interpretation("Hello")
        intent3 = interpreter._fallback_interpretation("hello")

        assert "conversation" in intent1.domains
        assert "conversation" in intent2.domains
        assert "conversation" in intent3.domains


class TestChitchatMetadata:
    """Test that chitchat queries have proper metadata."""

    @pytest.mark.asyncio
    async def test_chitchat_metadata_present(self, interpreter):
        """Test that chitchat metadata is present."""
        intent = interpreter._fallback_interpretation("hi")
        assert "is_chitchat" in intent.metadata
        assert intent.metadata["is_chitchat"] is True
        assert "reasoning" in intent.metadata

    @pytest.mark.asyncio
    async def test_non_chitchat_no_metadata(self, interpreter):
        """Test that non-chitchat queries don't have chitchat metadata."""
        intent = interpreter._fallback_interpretation("What's the weather?")
        # Should not have is_chitchat in metadata, or it should be False/None
        is_chitchat = intent.metadata.get("is_chitchat", False)
        assert is_chitchat is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
