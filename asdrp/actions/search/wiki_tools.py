#############################################################################
# wiki_tools.py
#
# Wikipedia tools using the wikipedia package
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import asyncio
from typing import Any, Dict, List, Optional

import wikipedia
from wikipedia.exceptions import (
    DisambiguationError,
    PageError,
    WikipediaException
)

from asdrp.actions.tools_meta import ToolsMeta

# Timeout for Wikipedia operations (in seconds)
TIMEOUT_SECONDS = 30

# Default number of sentences to return in summaries
DEFAULT_SENTENCES = 3


class WikiTools(metaclass=ToolsMeta):
    """
    Tools for searching and querying Wikipedia content.

    This class uses the ToolsMeta metaclass which automatically:
    - Discovers all public @classmethod decorated methods
    - Creates `spec_functions` list containing method names
    - Creates `tool_list` containing wrapped function tools ready for agent frameworks

    The wikipedia package is configured via the `_setup_class()` hook method.

    Usage:
    ------
    ```python
    from asdrp.actions.search.wiki_tools import WikiTools

    # Use the automatically generated tool_list
    from agents import Agent
    agent = Agent(tools=WikiTools.tool_list)

    # Or call methods directly
    summary = await WikiTools.get_page_summary("Python (programming language)")
    results = await WikiTools.search("artificial intelligence")
    ```

    Notes:
    ------
    - All methods are async to support concurrent execution
    - Methods handle common Wikipedia exceptions (disambiguation, page not found)
    - The wikipedia package uses the MediaWiki API under the hood
    """

    # ------------- Automatically populated by ToolsMeta -------------
    # List of method names & wrapped function tools to expose as tools
    spec_functions: List[str]
    tool_list: List[Any]

    @classmethod
    def _setup_class(cls) -> None:
        """
        Set up Wikipedia client configuration.

        This method is called automatically by ToolsMeta during class creation.
        It configures the wikipedia package with appropriate timeout and language settings.
        """
        # Set default language (can be overridden by set_language method)
        wikipedia.set_lang("en")

        # Set rate limiting with minimum wait time
        wikipedia.set_rate_limiting(rate_limit=True, min_wait=TIMEOUT_SECONDS)

    @classmethod
    async def search(
        cls,
        query: str,
        results: int = 10,
        suggestion: bool = False
    ) -> Dict[str, Any]:
        """
        Search Wikipedia for pages matching the query.

        Args:
            query (str): Search query string. Cannot be empty.
            results (int): Maximum number of results to return. Default is 10.
            suggestion (bool): If True, return a suggested search query if available.
                Default is False.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'results' (List[str]): List of page titles matching the query
                - 'suggestion' (Optional[str]): Suggested search query if requested
                - 'count' (int): Number of results returned

        Raises:
            ValueError: If query is empty or None.
            WikipediaException: If the Wikipedia API encounters an error.

        Example:
            >>> results = await WikiTools.search("machine learning", results=5)
            >>> print(results['results'])
            ['Machine learning', 'Deep learning', 'Supervised learning', ...]
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty or None.")

        try:
            # Use run_in_executor to run synchronous search in a thread pool
            loop = asyncio.get_running_loop()
            search_results = await loop.run_in_executor(
                None,
                lambda: wikipedia.search(query, results=results, suggestion=suggestion)
            )

            # wikipedia.search returns a tuple (results, suggestion) if suggestion=True
            if suggestion:
                result_list, suggested = search_results
                return {
                    "results": result_list,
                    "suggestion": suggested,
                    "count": len(result_list)
                }
            else:
                return {
                    "results": search_results,
                    "suggestion": None,
                    "count": len(search_results)
                }

        except WikipediaException as e:
            raise WikipediaException(f"Wikipedia search failed for query '{query}': {e}")

    @classmethod
    async def get_page_summary(
        cls,
        title: str,
        sentences: int = DEFAULT_SENTENCES,
        auto_suggest: bool = True,
        redirect: bool = True
    ) -> Dict[str, Any]:
        """
        Get a summary of a Wikipedia page.

        Args:
            title (str): Title of the Wikipedia page. Cannot be empty.
            sentences (int): Number of sentences to return in the summary.
                Default is 3. Use 0 for the full summary.
            auto_suggest (bool): If True, automatically use Wikipedia's suggestion
                for misspelled titles. Default is True.
            redirect (bool): If True, follow page redirects. Default is True.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'title' (str): Actual page title (may differ from input if redirected)
                - 'summary' (str): Summary text
                - 'url' (str): URL to the full Wikipedia page
                - 'sentences' (int): Number of sentences returned

        Raises:
            ValueError: If title is empty or None.
            PageError: If the page does not exist.
            DisambiguationError: If the title is ambiguous (multiple pages match).
                The exception contains a list of possible pages.

        Example:
            >>> result = await WikiTools.get_page_summary("Python (programming language)")
            >>> print(result['summary'])
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty or None.")

        try:
            loop = asyncio.get_running_loop()

            # Get the summary
            summary_text = await loop.run_in_executor(
                None,
                lambda: wikipedia.summary(
                    title.strip(),
                    sentences=sentences,
                    auto_suggest=auto_suggest,
                    redirect=redirect
                )
            )

            # Get the page object to retrieve the actual title and URL
            page = await loop.run_in_executor(
                None,
                lambda: wikipedia.page(title.strip(), auto_suggest=auto_suggest, redirect=redirect)
            )

            return {
                "title": page.title,
                "summary": summary_text,
                "url": page.url,
                "sentences": sentences if sentences > 0 else len(summary_text.split('. '))
            }

        except PageError as e:
            raise PageError(f"Wikipedia page not found for title '{title}': {e}")
        except DisambiguationError as e:
            # Include the options in the error message
            options = e.options[:10]  # Limit to first 10 options
            error_msg = f"Title '{title}' is ambiguous. Possible matches: {', '.join(options)}"
            new_error = DisambiguationError(title, e.options)
            new_error.args = (error_msg,)
            raise new_error
        except WikipediaException as e:
            raise WikipediaException(f"Failed to get summary for '{title}': {e}")

    @classmethod
    async def get_page_content(
        cls,
        title: str,
        auto_suggest: bool = True,
        redirect: bool = True
    ) -> Dict[str, Any]:
        """
        Get the full content of a Wikipedia page.

        Args:
            title (str): Title of the Wikipedia page. Cannot be empty.
            auto_suggest (bool): If True, automatically use Wikipedia's suggestion
                for misspelled titles. Default is True.
            redirect (bool): If True, follow page redirects. Default is True.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'title' (str): Actual page title (may differ from input if redirected)
                - 'content' (str): Full page content (plain text)
                - 'url' (str): URL to the Wikipedia page
                - 'length' (int): Length of content in characters
                - 'sections' (List[str]): List of section titles in the page

        Raises:
            ValueError: If title is empty or None.
            PageError: If the page does not exist.
            DisambiguationError: If the title is ambiguous (multiple pages match).

        Example:
            >>> result = await WikiTools.get_page_content("Artificial intelligence")
            >>> print(f"Content length: {result['length']} characters")
            >>> print(f"Sections: {result['sections']}")
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty or None.")

        try:
            loop = asyncio.get_running_loop()

            # Get the page object
            page = await loop.run_in_executor(
                None,
                lambda: wikipedia.page(title.strip(), auto_suggest=auto_suggest, redirect=redirect)
            )

            return {
                "title": page.title,
                "content": page.content,
                "url": page.url,
                "length": len(page.content),
                "sections": page.sections
            }

        except PageError as e:
            raise PageError(f"Wikipedia page not found for title '{title}': {e}")
        except DisambiguationError as e:
            options = e.options[:10]
            error = DisambiguationError(title, e.options)
            error.args = (f"Title '{title}' is ambiguous. Possible matches: {', '.join(options)}",)
            raise error
        except WikipediaException as e:
            raise WikipediaException(f"Failed to get content for '{title}': {e}")

    @classmethod
    async def get_page_section(
        cls,
        title: str,
        section_title: str,
        auto_suggest: bool = True,
        redirect: bool = True
    ) -> Dict[str, Any]:
        """
        Get a specific section from a Wikipedia page.

        Args:
            title (str): Title of the Wikipedia page. Cannot be empty.
            section_title (str): Title of the section to retrieve. Cannot be empty.
            auto_suggest (bool): If True, automatically use Wikipedia's suggestion
                for misspelled titles. Default is True.
            redirect (bool): If True, follow page redirects. Default is True.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'title' (str): Actual page title
                - 'section_title' (str): Section title
                - 'content' (str): Content of the section, or empty string if not found
                - 'url' (str): URL to the Wikipedia page
                - 'available_sections' (List[str]): List of all section titles (for reference)

        Raises:
            ValueError: If title or section_title is empty or None.
            PageError: If the page does not exist.
            DisambiguationError: If the title is ambiguous (multiple pages match).

        Example:
            >>> result = await WikiTools.get_page_section(
            ...     "Python (programming language)",
            ...     "History"
            ... )
            >>> print(result['content'])
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty or None.")
        if not section_title or not section_title.strip():
            raise ValueError("Section title cannot be empty or None.")

        try:
            loop = asyncio.get_running_loop()

            # Get the page object
            page = await loop.run_in_executor(
                None,
                lambda: wikipedia.page(title.strip(), auto_suggest=auto_suggest, redirect=redirect)
            )

            # Get section content
            section_content = await loop.run_in_executor(
                None,
                lambda: page.section(section_title.strip())
            )

            return {
                "title": page.title,
                "section_title": section_title.strip(),
                "content": section_content if section_content else "",
                "url": page.url,
                "available_sections": page.sections
            }

        except PageError as e:
            raise PageError(f"Wikipedia page not found for title '{title}': {e}")
        except DisambiguationError as e:
            options = e.options[:10]
            error = DisambiguationError(title, e.options)
            error.args = (f"Title '{title}' is ambiguous. Possible matches: {', '.join(options)}",)
            raise error
        except WikipediaException as e:
            raise WikipediaException(f"Failed to get section '{section_title}' for '{title}': {e}")

    @classmethod
    async def get_page_images(
        cls,
        title: str,
        auto_suggest: bool = True,
        redirect: bool = True
    ) -> Dict[str, Any]:
        """
        Get URLs of images from a Wikipedia page.

        Args:
            title (str): Title of the Wikipedia page. Cannot be empty.
            auto_suggest (bool): If True, automatically use Wikipedia's suggestion
                for misspelled titles. Default is True.
            redirect (bool): If True, follow page redirects. Default is True.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'title' (str): Actual page title
                - 'images' (List[str]): List of image URLs
                - 'count' (int): Number of images found
                - 'url' (str): URL to the Wikipedia page

        Raises:
            ValueError: If title is empty or None.
            PageError: If the page does not exist.
            DisambiguationError: If the title is ambiguous (multiple pages match).

        Example:
            >>> result = await WikiTools.get_page_images("Eiffel Tower")
            >>> print(f"Found {result['count']} images")
            >>> print(result['images'][:3])  # First 3 image URLs
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty or None.")

        try:
            loop = asyncio.get_running_loop()

            # Get the page object
            page = await loop.run_in_executor(
                None,
                lambda: wikipedia.page(title.strip(), auto_suggest=auto_suggest, redirect=redirect)
            )

            return {
                "title": page.title,
                "images": page.images,
                "count": len(page.images),
                "url": page.url
            }

        except PageError as e:
            raise PageError(f"Wikipedia page not found for title '{title}': {e}")
        except DisambiguationError as e:
            options = e.options[:10]
            error = DisambiguationError(title, e.options)
            error.args = (f"Title '{title}' is ambiguous. Possible matches: {', '.join(options)}",)
            raise error
        except WikipediaException as e:
            raise WikipediaException(f"Failed to get images for '{title}': {e}")

    @classmethod
    async def get_page_links(
        cls,
        title: str,
        auto_suggest: bool = True,
        redirect: bool = True
    ) -> Dict[str, Any]:
        """
        Get links to other Wikipedia pages from a given page.

        Args:
            title (str): Title of the Wikipedia page. Cannot be empty.
            auto_suggest (bool): If True, automatically use Wikipedia's suggestion
                for misspelled titles. Default is True.
            redirect (bool): If True, follow page redirects. Default is True.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'title' (str): Actual page title
                - 'links' (List[str]): List of linked page titles
                - 'count' (int): Number of links found
                - 'url' (str): URL to the Wikipedia page

        Raises:
            ValueError: If title is empty or None.
            PageError: If the page does not exist.
            DisambiguationError: If the title is ambiguous (multiple pages match).

        Example:
            >>> result = await WikiTools.get_page_links("Machine learning")
            >>> print(f"Found {result['count']} links")
            >>> print(result['links'][:10])  # First 10 linked pages
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty or None.")

        try:
            loop = asyncio.get_running_loop()

            # Get the page object
            page = await loop.run_in_executor(
                None,
                lambda: wikipedia.page(title.strip(), auto_suggest=auto_suggest, redirect=redirect)
            )

            return {
                "title": page.title,
                "links": page.links,
                "count": len(page.links),
                "url": page.url
            }

        except PageError as e:
            raise PageError(f"Wikipedia page not found for title '{title}': {e}")
        except DisambiguationError as e:
            options = e.options[:10]
            error = DisambiguationError(title, e.options)
            error.args = (f"Title '{title}' is ambiguous. Possible matches: {', '.join(options)}",)
            raise error
        except WikipediaException as e:
            raise WikipediaException(f"Failed to get links for '{title}': {e}")

    @classmethod
    async def set_language(cls, language_code: str) -> Dict[str, str]:
        """
        Set the language for Wikipedia queries.

        Args:
            language_code (str): Two-letter language code (e.g., 'en', 'es', 'fr', 'de').
                Cannot be empty.

        Returns:
            Dict[str, str]: Dictionary containing:
                - 'language' (str): The language code that was set
                - 'message' (str): Confirmation message

        Raises:
            ValueError: If language_code is empty or None.

        Example:
            >>> result = await WikiTools.set_language("es")
            >>> print(result['message'])
            'Wikipedia language set to: es'

        Note:
            The language setting persists across all subsequent calls until changed.
            Supported languages: https://en.wikipedia.org/wiki/List_of_Wikipedias
        """
        if not language_code or not language_code.strip():
            raise ValueError("Language code cannot be empty or None.")

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: wikipedia.set_lang(language_code.strip())
            )

            return {
                "language": language_code.strip(),
                "message": f"Wikipedia language set to: {language_code.strip()}"
            }

        except Exception as e:
            raise WikipediaException(f"Failed to set language to '{language_code}': {e}")

    @classmethod
    async def get_random_page(cls, pages: int = 1) -> Dict[str, Any]:
        """
        Get random Wikipedia page titles.

        Args:
            pages (int): Number of random pages to retrieve. Default is 1.
                Must be positive.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'pages' (List[str]): List of random page titles
                - 'count' (int): Number of pages returned

        Raises:
            ValueError: If pages is not positive.
            WikipediaException: If the Wikipedia API encounters an error.

        Example:
            >>> result = await WikiTools.get_random_page(pages=5)
            >>> print(result['pages'])
            ['Ancient Rome', 'Quantum mechanics', 'Jazz', ...]
        """
        if pages < 1:
            raise ValueError("Number of pages must be positive.")

        try:
            loop = asyncio.get_running_loop()
            random_pages = await loop.run_in_executor(
                None,
                lambda: wikipedia.random(pages=pages)
            )

            # wikipedia.random returns a string if pages=1, list otherwise
            if isinstance(random_pages, str):
                random_pages = [random_pages]

            return {
                "pages": random_pages,
                "count": len(random_pages)
            }

        except WikipediaException as e:
            raise WikipediaException(f"Failed to get random pages: {e}")


#---------------------------------------------
# main tests
#---------------------------------------------

async def test_wiki_tools():
    """Simple smoke test for WikiTools methods."""

    print("Testing search:")
    try:
        result = await WikiTools.search("Python programming", results=5)
        print(f"Found {result['count']} results: {result['results']}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting get_page_summary:")
    try:
        result = await WikiTools.get_page_summary("Python (programming language)", sentences=2)
        print(f"Title: {result['title']}")
        print(f"Summary: {result['summary'][:200]}...")
        print(f"URL: {result['url']}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting get_page_content:")
    try:
        result = await WikiTools.get_page_content("Artificial intelligence")
        print(f"Title: {result['title']}")
        print(f"Content length: {result['length']} characters")
        print(f"Number of sections: {len(result['sections'])}")
        print(f"Sections: {result['sections'][:5]}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting get_random_page:")
    try:
        result = await WikiTools.get_random_page(pages=3)
        print(f"Random pages: {result['pages']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_wiki_tools())
