# philippines_search_tool.py

"""
This tool implements global per-tool rate limiting for all network requests using the `ratelimit` package.
- The rate limit is configurable via the TOOLS_RATE_LIMIT environment variable (default: 5 requests/sec).
- If the rate limit is exceeded, the tool will wait until the next available slot.
- All requests are routed through a rate-limited internal method.
"""

import os
from typing import Optional

import requests
from agno.tools.toolkit import Toolkit
from agno.utils.log import logger
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry

# Get rate limit from environment or default to 5/sec
RATE_LIMIT = int(os.getenv("TOOLS_RATE_LIMIT", 5))
PER_SECONDS = 1

# Load environment variables from a .env file if present
load_dotenv()

# Configure the maximum number of links to collect per site
_limit_str = os.getenv("MIN_LINKS", "5")
try:
    LINKS_LIMIT = int(_limit_str)
except (TypeError, ValueError):
    LINKS_LIMIT = 5


class PhilippinesSearchTool(Toolkit):
    def __init__(self):
        super().__init__(name="philippines_search_tool")
        self.register(self.search_government_and_news_sites)

    @sleep_and_retry
    @limits(calls=RATE_LIMIT, period=PER_SECONDS)
    def _rate_limited_request(self, *args, **kwargs):
        """Internal method for rate-limited requests."""
        return requests.get(*args, **kwargs)

    def search_government_and_news_sites(self, query: str) -> str:
        """
        Searches Philippine government and news websites for the given query
        and returns a summary of findings. Rate limited to 5 requests/sec (configurable).

        Args:
            query (str): The search query to look for.

        Returns:
            str: A formatted string containing the search results.
        """
        logger.info(f"Searching Philippine government and news sites for: '{query}'")

        # List of sites to search
        search_sites = [
            "site:gov.ph",
            "site:inquirer.net",
            "site:rappler.com",
            "site:philstar.com",
            "site:mb.com.ph",
            "site:inquirer.net",
            "site:manilatimes.net",
        ]

        # Format DuckDuckGo or Bing query (replace with better API later)
        headers = {"User-Agent": "Mozilla/5.0"}
        search_results = []

        for site in search_sites:
            try:
                q = f"{query} {site}"
                logger.info(f"Searching: {q}")
                res = self._rate_limited_request(
                    f"https://html.duckduckgo.com/html/?q={q}", headers=headers
                )
                soup = BeautifulSoup(res.text, "html.parser")
                links = soup.find_all("a", class_="result__a", limit=LINKS_LIMIT)

                for link in links:
                    if isinstance(link, Tag):
                        href = link.get("href")
                        snippet = link.get_text(strip=True)
                        if href and snippet:
                            search_results.append(f"🔗 [{snippet}]({href})")
            except Exception as e:
                error_msg = f"❌ Error searching {site}: {e}"
                search_results.append(error_msg)
                logger.error(error_msg)

        if not search_results:
            return "No results found from Philippine government or news sites."

        logger.info(f"Found {len(search_results)} results from Philippine sites")
        return "\n\n".join(search_results)

    @staticmethod
    def _safe_find(element: Tag, *args, **kwargs) -> Optional[Tag]:
        """
        Safely finds an element and ensures the result is of type Tag or None.

        Args:
            element (Tag): The parent element to search within.
            *args, **kwargs: Arguments passed to BeautifulSoup's find method.

        Returns:
            Optional[Tag]: The found element as a Tag, or None if not found.
        """
        result = element.find(*args, **kwargs)
        return result if isinstance(result, Tag) else None
