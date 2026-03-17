"""
Site discovery: build a complete URL inventory for a domain.

Strategy (in priority order):
  1. Fetch sitemap.xml / sitemap_index.xml — fast and authoritative
  2. BFS link crawl fallback — no page cap, no content extraction,
     just follows internal links to enumerate all URLs

Output: list of dicts with keys: url (str), type ("html" | "pdf")
"""
import asyncio
from urllib.parse import urlparse, urljoin


# TODO: implement sitemap.xml fetch + parse
async def fetch_sitemap(base_url: str, domain: str) -> list[dict] | None:
    """Try sitemap.xml and sitemap_index.xml. Returns URL list or None if unavailable."""
    raise NotImplementedError


# TODO: implement BFS link-only crawl (no content extraction)
async def bfs_discover(base_url: str, domain: str, politeness_delay: float) -> list[dict]:
    """Full BFS crawl to enumerate all URLs. Used when no sitemap is available."""
    raise NotImplementedError


async def discover(base_url: str, domain: str, politeness_delay: float = 2.0) -> list[dict]:
    """
    Main entry point. Returns a flat list of discovered URLs:
      [{"url": "https://...", "type": "html"}, ...]
    """
    urls = await fetch_sitemap(base_url, domain)
    if urls is None:
        urls = await bfs_discover(base_url, domain, politeness_delay)
    return urls
