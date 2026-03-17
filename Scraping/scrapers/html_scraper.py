"""
HTML scraper using crawl4ai.
Extracts main-content markdown from a single URL.
Returns a Page record or None on permanent failure.
"""
import asyncio
import hashlib
from datetime import date, datetime

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from core.schema import Page


# TODO: implement with retry logic (up to max_retries, exponential backoff)
async def scrape_html(
    crawler: AsyncWebCrawler,
    url: str,
    css_selector: str,
    word_count_threshold: int,
    max_retries: int = 3,
) -> Page | None:
    """Scrape a single HTML page. Returns Page or None after exhausting retries."""
    raise NotImplementedError
