"""
HTML scraper using crawl4ai.
Scrapes a single URL, returns a Page and any PDF links found on the page.
"""
import asyncio
import hashlib
from datetime import date, datetime

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

from core.schema import Page


def _extract_metadata(html: str) -> tuple[str, str]:
    """
    Parse raw HTML to extract title and description.

    Title fallback chain:
      1. <title> tag (full document title, most reliable)
      2. First <h1> in the page
      3. Empty string (caller will fall back to URL slug)

    Description: <meta name="description"> content, or "".
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        # Emory titles are like "Page Name | Emory University | Atlanta GA"
        # Keep only the first segment
        title = title_tag.string.split("|")[0].strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    # Description
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()

    return title, description


async def scrape_html(
    crawler: AsyncWebCrawler,
    url: str,
    css_selector: str = "main",
    word_count_threshold: int = 10,
    max_retries: int = 3,
) -> tuple[Page | None, list[str]]:
    """
    Scrape a single HTML page.
    Returns (Page or None, list of PDF URLs discovered on the page).
    On permanent failure returns (None, []).
    """
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector=css_selector,
        word_count_threshold=word_count_threshold,
    )

    delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            result = await crawler.arun(url=url, config=run_conf)

            if result.success:
                # Extract title and description from raw HTML (most reliable source)
                title, description = _extract_metadata(result.html or "")
                if not title:
                    slug = url.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").replace(".html", "").title() or url

                # result.markdown is a MarkdownGenerationResult object in crawl4ai 0.8+
                markdown = (result.markdown.raw_markdown if result.markdown else "") or ""
                content_hash = hashlib.md5(markdown.encode()).hexdigest()

                page = Page(
                    url=url,
                    title=title,
                    description=description,
                    content_type="html",
                    markdown=markdown,
                    last_scraped=date.today().isoformat(),
                    scraped_at=datetime.now().isoformat(timespec="seconds"),
                    word_count=len(markdown.split()),
                    content_hash=content_hash,
                )

                # Collect PDF hrefs from all links on the page
                all_links = (
                    result.links.get("internal", [])
                    + result.links.get("external", [])
                )
                pdf_urls = [
                    link["href"]
                    for link in all_links
                    if link.get("href", "").lower().endswith(".pdf")
                ]

                return page, pdf_urls

            print(f"[html] Attempt {attempt}/{max_retries} failed — {url}: {result.error_message}")

        except Exception as exc:
            print(f"[html] Attempt {attempt}/{max_retries} error — {url}: {exc}")

        if attempt < max_retries:
            await asyncio.sleep(delay)
            delay *= 2

    return None, []
