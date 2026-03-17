"""
MedEase-Utils — Emory DAS Corpus Scraper (V2)

Entry point. Runs the full pipeline:
  1. Load site config
  2. Discover all URLs (sitemap.xml or BFS fallback)
  3. Scrape HTML pages and extract PDFs
  4. Merge with existing corpus (incremental update)
  5. Write versioned output to output/

Usage:
    python main.py
    python main.py --config config/emory_das.json
"""
import argparse
import asyncio
from pathlib import Path

from core.config_loader import load_config, CONFIG_DIR


def parse_args():
    parser = argparse.ArgumentParser(description="MedEase DAS corpus scraper")
    parser.add_argument(
        "--config",
        default=str(CONFIG_DIR / "emory_das.json"),
        help="Path to site config JSON (default: config/emory_das.json)",
    )
    return parser.parse_args()


async def run(config: dict):
    # TODO: implement full pipeline
    #   1. discovery.sitemap.discover(...)
    #   2. load existing corpus for incremental diff
    #   3. scrape new/changed pages (html_scraper + pdf_extractor)
    #   4. write output/emory_data_YYYY-MM-DD.json + emory_data_latest.json
    #   5. append to runs/run_log.jsonl
    raise NotImplementedError


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
    asyncio.run(run(config))
