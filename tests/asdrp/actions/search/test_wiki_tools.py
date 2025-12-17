#############################################################################
# test_wiki_tools.py
#
# Comprehensive tests for WikiTools class
#
# Test Coverage:
# - ToolsMeta integration (spec_functions, tool_list)
# - Async Wikipedia methods with mocked responses
# - Error handling (disambiguation, page not found, invalid inputs)
# - Edge cases (empty results, malformed data)
# - Input validation (empty strings, None values)
#
#############################################################################

import pytest
import asyncio
import importlib
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock

from wikipedia.exceptions import (
    DisambiguationError,
    PageError,
    WikipediaException
)

from asdrp.actions.search.wiki_tools import WikiTools
from asdrp.actions.tools_meta import ToolsMeta


class TestWikiToolsMetaIntegration:
    """Test WikiTools integration with ToolsMeta metaclass."""

    def test_tools_meta_integration(self):
        """Test that WikiTools properly integrates with ToolsMeta."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        # Verify ToolsMeta attributes exist
        assert hasattr(WikiTools, 'spec_functions')
        assert hasattr(WikiTools, 'tool_list')
        assert isinstance(WikiTools.spec_functions, list)
        assert isinstance(WikiTools.tool_list, list)
        assert len(WikiTools.tool_list) == len(WikiTools.spec_functions)

    def test_all_methods_discovered(self):
        """Test that all public WikiTools methods are discovered."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        expected_methods = [
            'get_page_content',
            'get_page_images',
            'get_page_links',
            'get_page_section',
            'get_page_summary',
            'get_random_page',
            'search',
            'set_language',
        ]

        for method in expected_methods:
            assert method in WikiTools.spec_functions, \
                f"{method} should be in spec_functions"

    def test_excluded_methods_not_discovered(self):
        """Test that internal methods are excluded from discovery."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        excluded = ['_setup_class', '_get_excluded_methods']
        for attr in excluded:
            assert attr not in WikiTools.spec_functions, \
                f"{attr} should not be in spec_functions"


class TestWikiToolsInitialization:
    """Test WikiTools class initialization and setup."""

    @patch('asdrp.actions.search.wiki_tools.wikipedia.set_lang')
    @patch('asdrp.actions.search.wiki_tools.wikipedia.set_rate_limiting')
    def test_setup_class_configures_wikipedia(self, mock_rate_limit, mock_set_lang):
        """Test that _setup_class configures Wikipedia properly."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)

        # Verify configuration methods were called
        mock_set_lang.assert_called_once_with("en")
        mock_rate_limit.assert_called_once()


class TestWikiToolsSearch:
    """Test WikiTools.search method."""

    @pytest.mark.asyncio
    async def test_search_success_without_suggestion(self):
        """Test successful Wikipedia search without suggestion."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_results = ['Machine learning', 'Deep learning', 'Supervised learning']

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_results)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.search("machine learning", results=3)

            assert result['results'] == mock_results
            assert result['suggestion'] is None
            assert result['count'] == 3

    @pytest.mark.asyncio
    async def test_search_success_with_suggestion(self):
        """Test successful Wikipedia search with suggestion."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_results = ['Artificial intelligence']
        mock_suggestion = 'artificial intelligence'
        mock_return = (mock_results, mock_suggestion)

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_return)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.search("artifical inteligence", results=5, suggestion=True)

            assert result['results'] == mock_results
            assert result['suggestion'] == mock_suggestion
            assert result['count'] == 1

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """Test that empty query raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Query cannot be empty or None"):
            await WikiTools.search("")

    @pytest.mark.asyncio
    async def test_search_whitespace_query(self):
        """Test that whitespace-only query raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Query cannot be empty or None"):
            await WikiTools.search("   ")

    @pytest.mark.asyncio
    async def test_search_none_query(self):
        """Test that None query raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Query cannot be empty or None"):
            await WikiTools.search(None)

    @pytest.mark.asyncio
    async def test_search_wikipedia_exception(self):
        """Test handling of WikipediaException."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=WikipediaException("API error")
        )

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(WikipediaException, match="Wikipedia search failed"):
                await WikiTools.search("test query")


class TestWikiToolsGetPageSummary:
    """Test WikiTools.get_page_summary method."""

    @pytest.mark.asyncio
    async def test_get_page_summary_success(self):
        """Test successful retrieval of page summary."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_summary = "Python is a high-level programming language. It supports multiple programming paradigms. It has a comprehensive standard library."
        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_summary, mock_page])

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_page_summary("Python", sentences=3)

            assert result['title'] == "Python (programming language)"
            assert result['summary'] == mock_summary
            assert result['url'] == "https://en.wikipedia.org/wiki/Python_(programming_language)"
            assert result['sentences'] == 3

    @pytest.mark.asyncio
    async def test_get_page_summary_empty_title(self):
        """Test that empty title raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Title cannot be empty or None"):
            await WikiTools.get_page_summary("")

    @pytest.mark.asyncio
    async def test_get_page_summary_page_not_found(self):
        """Test handling when page doesn't exist."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=PageError("Page not found")
        )

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(PageError, match="Wikipedia page not found"):
                await WikiTools.get_page_summary("NonexistentPage123456")

    @pytest.mark.asyncio
    async def test_get_page_summary_disambiguation(self):
        """Test handling of disambiguation error."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_options = ['Python (programming language)', 'Python (genus)', 'Python (missile)']
        mock_error = DisambiguationError('Python', mock_options)

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=mock_error)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(DisambiguationError):
                await WikiTools.get_page_summary("Python")


class TestWikiToolsGetPageContent:
    """Test WikiTools.get_page_content method."""

    @pytest.mark.asyncio
    async def test_get_page_content_success(self):
        """Test successful retrieval of full page content."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_content = "Full page content..." * 100
        mock_sections = ['History', 'Features', 'Syntax', 'Libraries']

        mock_page = MagicMock()
        mock_page.title = "Artificial intelligence"
        mock_page.content = mock_content
        mock_page.url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
        mock_page.sections = mock_sections

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_page)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_page_content("Artificial intelligence")

            assert result['title'] == "Artificial intelligence"
            assert result['content'] == mock_content
            assert result['url'] == "https://en.wikipedia.org/wiki/Artificial_intelligence"
            assert result['length'] == len(mock_content)
            assert result['sections'] == mock_sections

    @pytest.mark.asyncio
    async def test_get_page_content_empty_title(self):
        """Test that empty title raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Title cannot be empty or None"):
            await WikiTools.get_page_content("")

    @pytest.mark.asyncio
    async def test_get_page_content_page_not_found(self):
        """Test handling when page doesn't exist."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=PageError("Page not found")
        )

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(PageError, match="Wikipedia page not found"):
                await WikiTools.get_page_content("NonexistentPage123456")


class TestWikiToolsGetPageSection:
    """Test WikiTools.get_page_section method."""

    @pytest.mark.asyncio
    async def test_get_page_section_success(self):
        """Test successful retrieval of specific page section."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_section_content = "History section content..."
        mock_sections = ['History', 'Features', 'Syntax']

        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        mock_page.sections = mock_sections
        mock_page.section = MagicMock(return_value=mock_section_content)

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_page, mock_section_content])

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_page_section("Python", "History")

            assert result['title'] == "Python (programming language)"
            assert result['section_title'] == "History"
            assert result['content'] == mock_section_content
            assert result['url'] == "https://en.wikipedia.org/wiki/Python_(programming_language)"
            assert result['available_sections'] == mock_sections

    @pytest.mark.asyncio
    async def test_get_page_section_section_not_found(self):
        """Test when section doesn't exist on page."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_sections = ['History', 'Features', 'Syntax']

        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        mock_page.sections = mock_sections

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_page, None])

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_page_section("Python", "Nonexistent")

            assert result['content'] == ""
            assert result['available_sections'] == mock_sections

    @pytest.mark.asyncio
    async def test_get_page_section_empty_title(self):
        """Test that empty title raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Title cannot be empty or None"):
            await WikiTools.get_page_section("", "History")

    @pytest.mark.asyncio
    async def test_get_page_section_empty_section_title(self):
        """Test that empty section title raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Section title cannot be empty or None"):
            await WikiTools.get_page_section("Python", "")


class TestWikiToolsGetPageImages:
    """Test WikiTools.get_page_images method."""

    @pytest.mark.asyncio
    async def test_get_page_images_success(self):
        """Test successful retrieval of page images."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_images = [
            'https://upload.wikimedia.org/wikipedia/commons/image1.jpg',
            'https://upload.wikimedia.org/wikipedia/commons/image2.png',
            'https://upload.wikimedia.org/wikipedia/commons/image3.svg'
        ]

        mock_page = MagicMock()
        mock_page.title = "Eiffel Tower"
        mock_page.url = "https://en.wikipedia.org/wiki/Eiffel_Tower"
        mock_page.images = mock_images

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_page)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_page_images("Eiffel Tower")

            assert result['title'] == "Eiffel Tower"
            assert result['images'] == mock_images
            assert result['count'] == 3
            assert result['url'] == "https://en.wikipedia.org/wiki/Eiffel_Tower"

    @pytest.mark.asyncio
    async def test_get_page_images_empty_title(self):
        """Test that empty title raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Title cannot be empty or None"):
            await WikiTools.get_page_images("")


class TestWikiToolsGetPageLinks:
    """Test WikiTools.get_page_links method."""

    @pytest.mark.asyncio
    async def test_get_page_links_success(self):
        """Test successful retrieval of page links."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_links = [
            'Deep learning',
            'Neural network',
            'Artificial intelligence',
            'Supervised learning'
        ]

        mock_page = MagicMock()
        mock_page.title = "Machine learning"
        mock_page.url = "https://en.wikipedia.org/wiki/Machine_learning"
        mock_page.links = mock_links

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_page)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_page_links("Machine learning")

            assert result['title'] == "Machine learning"
            assert result['links'] == mock_links
            assert result['count'] == 4
            assert result['url'] == "https://en.wikipedia.org/wiki/Machine_learning"

    @pytest.mark.asyncio
    async def test_get_page_links_empty_title(self):
        """Test that empty title raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Title cannot be empty or None"):
            await WikiTools.get_page_links("")


class TestWikiToolsSetLanguage:
    """Test WikiTools.set_language method."""

    @pytest.mark.asyncio
    async def test_set_language_success(self):
        """Test successful language setting."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.set_language("es")

            assert result['language'] == "es"
            assert "es" in result['message']

    @pytest.mark.asyncio
    async def test_set_language_empty_code(self):
        """Test that empty language code raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Language code cannot be empty or None"):
            await WikiTools.set_language("")

    @pytest.mark.asyncio
    async def test_set_language_exception(self):
        """Test handling of language setting exception."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=Exception("Invalid language code")
        )

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(WikipediaException, match="Failed to set language"):
                await WikiTools.set_language("invalid")


class TestWikiToolsGetRandomPage:
    """Test WikiTools.get_random_page method."""

    @pytest.mark.asyncio
    async def test_get_random_page_single(self):
        """Test getting single random page."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_page = "Ancient Rome"

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_page)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_random_page(pages=1)

            assert result['pages'] == ["Ancient Rome"]
            assert result['count'] == 1

    @pytest.mark.asyncio
    async def test_get_random_page_multiple(self):
        """Test getting multiple random pages."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_pages = ["Ancient Rome", "Quantum mechanics", "Jazz"]

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_pages)

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await WikiTools.get_random_page(pages=3)

            assert result['pages'] == mock_pages
            assert result['count'] == 3

    @pytest.mark.asyncio
    async def test_get_random_page_invalid_count(self):
        """Test that invalid page count raises ValueError."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        with pytest.raises(ValueError, match="Number of pages must be positive"):
            await WikiTools.get_random_page(pages=0)

        with pytest.raises(ValueError, match="Number of pages must be positive"):
            await WikiTools.get_random_page(pages=-1)

    @pytest.mark.asyncio
    async def test_get_random_page_exception(self):
        """Test handling of WikipediaException."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=WikipediaException("API error")
        )

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(WikipediaException, match="Failed to get random pages"):
                await WikiTools.get_random_page()


class TestWikiToolsIntegration:
    """Integration tests for WikiTools combined operations."""

    @pytest.mark.asyncio
    async def test_search_then_get_summary(self):
        """Test search followed by getting page summary."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        # Mock search results
        mock_search_results = ['Python (programming language)', 'Python (genus)']

        # Mock page summary
        mock_summary = "Python is a high-level programming language."
        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[
            mock_search_results,
            mock_summary,
            mock_page
        ])

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            # Search
            search_result = await WikiTools.search("Python", results=2)
            assert search_result['count'] == 2

            # Get summary of first result
            summary_result = await WikiTools.get_page_summary(search_result['results'][0])
            assert summary_result['title'] == "Python (programming language)"
            assert summary_result['summary'] == mock_summary

    @pytest.mark.asyncio
    async def test_get_content_and_section(self):
        """Test getting full content then specific section."""
        import importlib
        import asdrp.actions.search.wiki_tools
        importlib.reload(asdrp.actions.search.wiki_tools)
        from asdrp.actions.search.wiki_tools import WikiTools

        mock_content = "Full page content..."
        mock_sections = ['History', 'Features', 'Syntax']
        mock_section_content = "History section content..."

        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.content = mock_content
        mock_page.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        mock_page.sections = mock_sections

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[
            mock_page,  # get_page_content
            mock_page,  # get_page_section
            mock_section_content
        ])

        with patch('asdrp.actions.search.wiki_tools.asyncio.get_running_loop', return_value=mock_loop):
            # Get full content
            content_result = await WikiTools.get_page_content("Python")
            assert content_result['sections'] == mock_sections

            # Get specific section
            section_result = await WikiTools.get_page_section("Python", "History")
            assert section_result['content'] == mock_section_content
