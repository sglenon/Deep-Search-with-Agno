# download_team.py

"""
This tool implements global per-tool rate limiting for all network requests using the `ratelimit` package.
- The rate limit is configurable via the TOOLS_RATE_LIMIT environment variable (default: 5 requests/sec).
- If the rate limit is exceeded, the tool will wait until the next available slot.
- All requests are routed through a rate-limited internal method.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from agno.tools.toolkit import Toolkit
from agno.utils.log import logger
from bs4 import BeautifulSoup, Tag
from ratelimit import limits, sleep_and_retry

# Get rate limit from environment or default to 5/sec
RATE_LIMIT = int(os.getenv("TOOLS_RATE_LIMIT", 5))
PER_SECONDS = 1
MIN_LINKS = int(os.getenv("MIN_LINKS", "1"))


# === FILE DOWNLOADER ===
class FileDownloaderTool(Toolkit):
    def __init__(
        self, download_dir: str = "downloaded_files", default_prefix: str = "download"
    ):
        super().__init__(name="file_downloader_tool")
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.default_prefix = default_prefix
        self.register(self.download_files)
        self.register(self.download_custom)

    @sleep_and_retry
    @limits(calls=RATE_LIMIT, period=PER_SECONDS)
    def _rate_limited_request(self, *args, **kwargs):
        """Internal method for rate-limited requests."""
        return requests.get(*args, **kwargs)

    def download_files(self, urls: list[str]) -> str:
        """Download supported files from a list of URLs. Rate limited to 5 requests/sec (configurable)."""
        logger.info(f"Starting download of {len(urls)} files")
        log = []
        for url in urls:
            try:
                filename = url.split("/")[-1].split("?")[0]
                if not any(
                    filename.endswith(ext) for ext in [".csv", ".pdf", ".txt", ".md"]
                ):
                    log.append(f"⚠️ Skipped (unsupported file type): {filename}")
                    continue

                response = self._rate_limited_request(
                    url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
                file_path = self.download_dir / filename
                with open(file_path, "wb") as f:
                    f.write(response.content)

                log.append(f"✅ Downloaded: {filename}")
                logger.info(f"Successfully downloaded {filename}")
            except Exception as e:
                log.append(f"❌ Failed to download {url}: {e}")
                logger.error(f"Failed to download {url}: {e}")
        return "\n".join(log)

    def _generate_filename(self, url: str) -> str:
        """Generate filename from URL pattern or fallback to timestamp."""
        match = re.search(r"report[-_]?([\d.]+)[-_]([\d.]+)", url)
        if match:
            lat, lon = match.groups()
            return f"report_{lat}_{lon}.pdf"

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{self.default_prefix}_{timestamp}.pdf"

    def download_custom(
        self, url_filename: dict[str, str], verify_ssl: bool = True
    ) -> str:
        """Download PDF using a custom filename or auto-generated name."""
        try:
            url = url_filename["url"]
            filename = url_filename.get("filename") or self._generate_filename(url)

            save_path = self.download_dir / filename
            logger.info(f"Downloading custom file from {url} to {save_path}")
            response = self._rate_limited_request(
                url,
                verify=verify_ssl,
                stream=True,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Successfully downloaded custom file to {save_path}")
            return f"✅ PDF saved successfully to {save_path}"
        except Exception as e:
            logger.error(f"Failed to retrieve and download PDF: {e}")
            return f"❌ Failed to retrieve and download PDF: {e}"


# === WEB SCRAPER ===
class WebScraperTool(Toolkit):
    """
    WebScraperTool uses the same global rate-limited request method as FileDownloaderTool.
    All network requests are subject to the same rate limit.
    """

    def __init__(self):
        super().__init__(name="web_scraper_tool")
        self.register(self.scrape_urls)

    @sleep_and_retry
    @limits(calls=RATE_LIMIT, period=PER_SECONDS)
    def _rate_limited_request(self, *args, **kwargs):
        """Internal method for rate-limited requests."""
        return requests.get(*args, **kwargs)

    def scrape_urls(self, urls: list[str]) -> str:
        """Extract paragraph text from each URL. Rate limited to 5 requests/sec (configurable)."""
        logger.info(f"Starting scraping of {len(urls)} URLs")
        log = []
        for url in urls:
            try:
                response = self._rate_limited_request(url, timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")
                paragraphs = soup.find_all("p")
                text = "\n".join(
                    p.get_text(strip=True)
                    for p in paragraphs
                    if len(p.get_text(strip=True)) > 40
                )
                if not text:
                    log.append(f"❌ No usable content at {url}")
                else:
                    log.append(f"✅ Extracted from: {url}\n{text[:500]}...")
                    logger.info(f"Successfully scraped content from {url}")
            except Exception as e:
                log.append(f"❌ Failed to scrape {url}: {e}")
                logger.error(f"Failed to scrape {url}: {e}")
        return "\n".join(log)

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


# === MARKDOWN FORMATTER ===
class MarkdownFormatterTool(Toolkit):
    def __init__(self, output_dir: str = "scraped_markdown"):
        super().__init__(name="markdown_formatter_tool")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.register(self.format_documents)

    def format_documents(self, documents: list[dict[str, str]]) -> str:
        """Format scraped documents into Markdown files using custom titles."""
        logger.info(f"Formatting {len(documents)} documents to markdown")
        log = []
        for doc in documents:
            try:
                if not isinstance(doc, dict):
                    raise ValueError("Document is not a dictionary")

                # Get title from the document, fallback to 'untitled'
                title = doc.get("title", "untitled")
                content = doc.get("content", "")
                source = doc.get("source", "")

                # Sanitize title for filename
                safe_title = re.sub(r"[^a-zA-Z0-9\-_]", "_", title.lower())[:80]
                filename = self.output_dir / f"{safe_title}.md"

                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n")
                    if source:
                        f.write(f"**Source:** {source}\n\n")
                    f.write(content.strip())

                log.append(f"✅ Saved markdown: {filename.name}")
                logger.info(f"Successfully saved markdown: {filename.name}")
            except Exception as e:
                log.append(f"❌ Failed to save markdown: {e}")
                logger.error(f"Failed to save markdown: {e}")
        return "\n".join(log)
