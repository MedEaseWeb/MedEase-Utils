"""
MedEase-Utils — Emory DAS Corpus Scraper (V2)

Pipeline:
  1. Load site config
  2. Load sitemap cache (or discover if missing / --rediscover)
  3. Phase A — scrape HTML pages changed since last run (via sitemap lastmod)
  4. Phase B — extract PDFs discovered as links during Phase A
  5. Write versioned output + run log

Usage:
    python main.py
    python main.py --config config/emory_das.json
    python main.py --rediscover          # force re-fetch sitemap.xml
"""
import argparse
import asyncio
import dataclasses
import json
import logging
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig

from core.config_loader import load_config, CONFIG_DIR
from core.schema import CorpusEnvelope, Page
from discovery.sitemap import discover, load_sitemap
from scrapers.html_scraper import scrape_html
from scrapers.pdf_extractor import extract_pdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"
RUNS_DIR = Path(__file__).parent / "runs"
SITEMAP_PATH = OUTPUT_DIR / "emory_sitemap.json"


def parse_args():
    parser = argparse.ArgumentParser(description="MedEase DAS corpus scraper")
    parser.add_argument(
        "--config",
        default=str(CONFIG_DIR / "emory_das.json"),
        help="Path to site config JSON",
    )
    parser.add_argument(
        "--rediscover",
        action="store_true",
        help="Force re-fetch sitemap.xml even if cache exists",
    )
    return parser.parse_args()


def load_existing_corpus(source_id: str) -> dict[str, dict]:
    """Load existing corpus records keyed by URL for incremental diff."""
    latest = OUTPUT_DIR / f"{source_id}_data_latest.json"
    if not latest.exists():
        return {}
    with open(latest, encoding="utf-8") as f:
        data = json.load(f)
    return {r["url"]: r for r in data.get("records", [])}


def needs_update(entry: dict, existing: dict[str, dict]) -> bool:
    """
    Return True if the page should be re-scraped.
    Compares sitemap lastmod (YYYY-MM-DD) against stored last_scraped.
    New URLs always return True.
    """
    url = entry["url"]
    if url not in existing:
        return True
    lastmod = entry.get("lastmod", "")
    if not lastmod:
        return True
    return lastmod[:10] > existing[url].get("last_scraped", "")


def write_output(envelope: CorpusEnvelope, source_id: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    payload = json.dumps(dataclasses.asdict(envelope), indent=2, ensure_ascii=False)

    dated = OUTPUT_DIR / f"{source_id}_data_{today}.json"
    latest = OUTPUT_DIR / f"{source_id}_data_latest.json"
    dated.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    log.info(f"Output written → {dated}")


def append_run_log(source_id: str, stats: dict) -> None:
    RUNS_DIR.mkdir(exist_ok=True)
    with open(RUNS_DIR / "run_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"source": source_id, **stats}) + "\n")


def log_failed(url: str, reason: str) -> None:
    RUNS_DIR.mkdir(exist_ok=True)
    with open(RUNS_DIR / "failed_urls.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {url} | {reason}\n")


async def run(config: dict, rediscover: bool) -> None:
    source_id = config["source_id"]
    start = datetime.now()

    # --- Site Discovery (cached) ---
    if not SITEMAP_PATH.exists() or rediscover:
        log.info("Running site discovery...")
        sitemap = discover(config["base_url"], SITEMAP_PATH)
    else:
        log.info(f"Using cached sitemap: {SITEMAP_PATH}")
        sitemap = load_sitemap(SITEMAP_PATH)
    log.info(f"Sitemap: {len(sitemap)} URLs")

    # --- Load existing corpus ---
    existing = load_existing_corpus(source_id)
    log.info(f"Existing corpus: {len(existing)} records")

    # Seed new corpus with all existing records; updates will overwrite in-place
    records: dict[str, dict] = dict(existing)
    pdf_urls: set[str] = set()
    stats = {"new": 0, "updated": 0, "unchanged": 0, "failed_html": 0, "failed_pdf": 0}

    # --- Phase A: HTML pages ---
    browser_conf = BrowserConfig(headless=True)
    async with AsyncWebCrawler(config=browser_conf) as crawler:
        for entry in sitemap:
            url = entry["url"]

            if not needs_update(entry, existing):
                stats["unchanged"] += 1
                continue

            is_new = url not in existing
            log.info(f"{'NEW    ' if is_new else 'UPDATE '} {url}")

            page, discovered_pdfs = await scrape_html(
                crawler,
                url,
                css_selector=config["css_selector"],
                word_count_threshold=config["word_count_threshold"],
                max_retries=config["max_retries"],
            )

            if page:
                records[url] = dataclasses.asdict(page)
                stats["new" if is_new else "updated"] += 1
                pdf_urls.update(discovered_pdfs)
            else:
                stats["failed_html"] += 1
                log_failed(url, "html scrape failed after retries")

            await asyncio.sleep(config["politeness_delay_seconds"])

    # --- Phase B: PDFs ---
    new_pdf_urls = [u for u in pdf_urls if u not in records]
    log.info(f"PDFs: {len(pdf_urls)} discovered, {len(new_pdf_urls)} new")

    for pdf_url in new_pdf_urls:
        log.info(f"PDF    {pdf_url}")
        page = extract_pdf(pdf_url, max_retries=config["max_retries"])
        if page:
            records[pdf_url] = dataclasses.asdict(page)
            stats["new"] += 1
        else:
            stats["failed_pdf"] += 1
            log_failed(pdf_url, "pdf extraction failed after retries")

    # --- Write output ---
    envelope = CorpusEnvelope(
        source=config["domain"],
        last_updated=datetime.now().isoformat(timespec="seconds"),
        total_pages=len(records),
        records=list(records.values()),
    )
    write_output(envelope, source_id)

    duration = round((datetime.now() - start).total_seconds(), 1)
    run_stats = {"run_at": start.isoformat(timespec="seconds"), "duration_seconds": duration, **stats}
    append_run_log(source_id, run_stats)

    log.info(
        f"Done in {duration}s — "
        f"{stats['new']} new, {stats['updated']} updated, "
        f"{stats['unchanged']} unchanged, "
        f"{stats['failed_html'] + stats['failed_pdf']} failed"
    )


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
    asyncio.run(run(config, args.rediscover))
