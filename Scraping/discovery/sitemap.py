"""
Site discovery: parse sitemap.xml and produce the URL inventory.

Output: emory_sitemap.json — flat list of {"url", "type", "lastmod"} dicts.
This file is a cached artifact. Re-run only with --rediscover flag.
"""
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

# URLs matching these patterns are excluded from the corpus
_EXCLUDE_PATTERNS = ["/404/"]


def fetch_sitemap(base_url: str) -> list[dict]:
    """Fetch and parse sitemap.xml. Returns list of URL dicts."""
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    print(f"[discovery] Fetching {sitemap_url}")

    with urllib.request.urlopen(sitemap_url, timeout=15) as resp:
        content = resp.read()

    root = ET.fromstring(content)
    urls = []

    for url_el in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = url_el.findtext(f"{{{SITEMAP_NS}}}loc", "").strip()
        lastmod = url_el.findtext(f"{{{SITEMAP_NS}}}lastmod", "").strip()

        if not loc:
            continue
        if any(pat in loc for pat in _EXCLUDE_PATTERNS):
            continue

        urls.append({
            "url": loc,
            "type": "html",
            "lastmod": lastmod,
        })

    return urls


def save_sitemap(urls: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)


def load_sitemap(output_path: Path) -> list[dict]:
    with open(output_path, encoding="utf-8") as f:
        return json.load(f)


def discover(base_url: str, output_path: Path) -> list[dict]:
    """
    Fetch sitemap.xml, save to output_path, return URL list.
    Call only when the cache doesn't exist or --rediscover is passed.
    """
    urls = fetch_sitemap(base_url)
    save_sitemap(urls, output_path)
    print(f"[discovery] {len(urls)} URLs saved → {output_path}")
    return urls
