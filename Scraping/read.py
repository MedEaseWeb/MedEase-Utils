"""
MedEase-Utils — Corpus Inspection CLI

Loads emory_data_latest.json and prints a summary table.

Usage:
    python read.py
    python read.py --file output/emory_data_2026-03-16.json
    python read.py --export csv
"""
import argparse
import json
from pathlib import Path


OUTPUT_DIR = Path(__file__).parent / "output"
LATEST = OUTPUT_DIR / "emory_data_latest.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect MedEase corpus")
    parser.add_argument("--file", default=str(LATEST), help="Path to corpus JSON file")
    parser.add_argument("--export", choices=["csv"], help="Export format")
    return parser.parse_args()


def main():
    # TODO: implement
    #   - load corpus JSON
    #   - print run metadata (source, last_updated, total_pages)
    #   - print summary table: url | title | content_type | word_count | last_scraped
    #   - flag duplicate URLs
    #   - optional CSV export via pandas
    raise NotImplementedError


if __name__ == "__main__":
    main()
