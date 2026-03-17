"""
Site discovery: build a complete URL inventory for a domain.

Strategy:
  1. Try sitemap.xml — fast and authoritative if up to date
  2. Validate sitemap: if >50% of URLs return 404, the sitemap is stale.
     Fall back to BFS link crawl.
  3. BFS fallback — no content extraction, just follows internal links
     to enumerate all live URLs.

Output: emory_sitemap.json — flat list of {"url", "type", "lastmod"} dicts.
This file is a cached artifact. Re-run only with --rediscover flag.
"""
import asyncio
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
_EXCLUDE_PATTERNS = ["/404/", "/do-not-trash/", "/search.html"]
# If more than this fraction of sitemap URLs are 404, treat sitemap as stale
_STALE_THRESHOLD = 0.2
# How many URLs to probe when validating the sitemap (sampled evenly across the full list)
_VALIDATION_SAMPLE = 15


def _fetch_sitemap_xml(base_url: str) -> list[dict] | None:
    """Fetch and parse sitemap.xml. Returns URL list or None if unavailable."""
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    print(f"[discovery] Fetching {sitemap_url}")
    try:
        resp = requests.get(sitemap_url, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[discovery] sitemap.xml unavailable: {exc}")
        return None

    root = ET.fromstring(resp.content)
    urls = []
    for url_el in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = url_el.findtext(f"{{{SITEMAP_NS}}}loc", "").strip()
        lastmod = url_el.findtext(f"{{{SITEMAP_NS}}}lastmod", "").strip()
        if not loc or any(pat in loc for pat in _EXCLUDE_PATTERNS):
            continue
        urls.append({"url": loc, "type": "html", "lastmod": lastmod})
    return urls


def _validate_sitemap(urls: list[dict], sample_size: int = _VALIDATION_SAMPLE) -> bool:
    """
    Probe an evenly-spaced sample of URLs across the full list.
    Returns True if sitemap looks valid, False if it appears stale.
    """
    # Sample evenly across the full list to avoid bias toward recently-modified URLs at the top
    step = max(1, len(urls) // sample_size)
    sample = urls[::step][:sample_size]
    not_found = 0
    for entry in sample:
        try:
            r = requests.head(entry["url"], timeout=10, allow_redirects=True)
            if r.status_code == 404:
                not_found += 1
        except Exception:
            pass
    stale_ratio = not_found / len(sample)
    print(f"[discovery] Sitemap validation: {not_found}/{len(sample)} URLs returned 404 ({stale_ratio:.0%})")
    return stale_ratio < _STALE_THRESHOLD


async def _bfs_discover(base_url: str, domain: str, politeness_delay: float) -> list[dict]:
    """
    BFS crawl from base_url, following only internal links.
    No content extraction — only collects URLs.
    Returns list of URL dicts with type "html" or "pdf".
    """
    print(f"[discovery] Sitemap stale — running BFS discovery from {base_url}")
    visited: set[str] = set()
    queue: list[str] = [base_url]
    found: list[dict] = []

    run_conf = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=0)
    browser_conf = BrowserConfig(headless=True)

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        while queue:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                result = await crawler.arun(url=url, config=run_conf)
            except Exception as exc:
                print(f"[discovery] BFS error on {url}: {exc}")
                continue

            if not result.success:
                continue

            found.append({"url": url, "type": "html", "lastmod": ""})

            all_links = (
                result.links.get("internal", [])
                + result.links.get("external", [])
            )
            for link in all_links:
                href = link.get("href", "")
                if not href:
                    continue
                full_url = urljoin(url, href).split("#")[0]  # strip fragments
                parsed = urlparse(full_url)

                if parsed.netloc != domain:
                    continue
                if full_url in visited or full_url in queue:
                    continue
                if any(pat in full_url for pat in _EXCLUDE_PATTERNS):
                    continue

                if full_url.lower().endswith(".pdf"):
                    if full_url not in visited:
                        found.append({"url": full_url, "type": "pdf", "lastmod": ""})
                        visited.add(full_url)
                elif full_url.lower().endswith((".html", "/")):
                    queue.append(full_url)

            await asyncio.sleep(politeness_delay)

    print(f"[discovery] BFS complete — {len(found)} URLs found")
    return found


def save_sitemap(urls: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)


def load_sitemap(output_path: Path) -> list[dict]:
    with open(output_path, encoding="utf-8") as f:
        return json.load(f)


async def discover(base_url: str, domain: str, output_path: Path, politeness_delay: float = 2.0) -> list[dict]:
    """
    Main entry point. Tries sitemap.xml, validates it, falls back to BFS if stale.
    Saves result to output_path and returns URL list.
    """
    urls = _fetch_sitemap_xml(base_url)

    if urls and _validate_sitemap(urls):
        print(f"[discovery] Sitemap valid — {len(urls)} URLs")
    else:
        urls = await _bfs_discover(base_url, domain, politeness_delay)

    # Filter any residual 404-pattern entries
    urls = [u for u in urls if not any(pat in u["url"] for pat in _EXCLUDE_PATTERNS)]

    save_sitemap(urls, output_path)
    print(f"[discovery] {len(urls)} URLs saved → {output_path}")
    return urls
