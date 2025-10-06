import os
from typing import Optional

import requests
from agno.tools.toolkit import Toolkit
from agno.utils.log import logger
from bs4 import BeautifulSoup, Tag
from ratelimit import limits, sleep_and_retry

# === Rate Limit Config ===
RATE_LIMIT = int(os.getenv("TOOLS_RATE_LIMIT", 5))  # requests per period
PER_SECONDS = 1  # period length in seconds

# === Link Collection Config ===
_limit_str = os.getenv("SCI_LINKS_LIMIT", "15")
try:
    LINKS_LIMIT = int(_limit_str)
except (TypeError, ValueError):
    LINKS_LIMIT = 15


class SciResTool(Toolkit):
    def __init__(self):
        super().__init__(name="sci_research_tool")
        self.register(self.search_journal_sites)

    @sleep_and_retry
    @limits(calls=RATE_LIMIT, period=PER_SECONDS)
    def _rate_limited_request(self, url, headers):
        """Internal method for rate-limited requests."""
        logger.info(f"[RateLimiter] Making request: {url}")
        return requests.get(url, headers=headers)

    def search_journal_sites(self, query: str) -> str:
        """
        Searches research journals and scientific articles.
        Rate limited to TOOLS_RATE_LIMIT (default: 5 requests/sec).

        Args:
            query (str): The search query for scientific papers and research.

        Returns:
            str: A formatted string containing the search results from scientific sources.
        """
        logger.info(f"Searching scientific journals for: '{query}'")

        # List of sites to search
        search_sites = [
            "site:arxiv.org",
            "site:biorxiv.org",
            "site:medrxiv.org",
            "site:nature.com",
            "site:sciencedirect.com",
            "site:pubmed.ncbi.nlm.nih.gov",
            "site:plos.org",
            "site:springer.com",
            "site:wiley.com",
            "site:researchgate.net",
            "site:semanticscholar.org",
            "site:ieeexplore.ieee.org",
            "site:dl.acm.org",
            "site:openaccessbutton.org",
        ]

        headers = {"User-Agent": "Mozilla/5.0"}
        search_results = []

        for site in search_sites:
            try:
                q = f"{query} {site}"
                logger.info(f"🔍 Searching: {q}")
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
            return "No results found from scientific sources."

        logger.info(f"Found {len(search_results)} results from scientific sources")
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
