"""
HTML scraper using crawl4ai.
Scrapes a single URL, returns a Page and any PDF links found on the page.
"""
import asyncio
import hashlib
from datetime import date, datetime

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

from core.schema import Page


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
                # Title: prefer metadata, fall back to URL slug
                title = ""
                if result.metadata:
                    title = result.metadata.get("title") or ""
                if not title:
                    slug = url.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").replace(".html", "").title() or url

                markdown = result.markdown or ""
                content_hash = hashlib.md5(markdown.encode()).hexdigest()

                page = Page(
                    url=url,
                    title=title.strip(),
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
