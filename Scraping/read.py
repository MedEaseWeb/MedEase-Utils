"""
MedEase-Utils — Corpus Inspection CLI

Usage:
    python read.py
    python read.py --file output/emory_das_data_2026-03-16.json
    python read.py --export csv
"""
import argparse
import json
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(__file__).parent / "output"
LATEST = OUTPUT_DIR / "emory_das_data_latest.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect MedEase corpus")
    parser.add_argument("--file", default=str(LATEST), help="Path to corpus JSON file")
    parser.add_argument("--export", choices=["csv"], help="Export format")
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.file)

    if not path.exists():
        print(f"No corpus file found at {path}")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"\nSource:       {data.get('source')}")
    print(f"Last updated: {data.get('last_updated')}")
    print(f"Total pages:  {data.get('total_pages')}")

    records = data.get("records", [])
    if not records:
        print("No records.")
        return

    df = pd.DataFrame(records)
    display_cols = [c for c in ["url", "title", "description", "content_type", "word_count", "last_scraped"] if c in df.columns]
    summary = df[display_cols]

    dupes = df[df.duplicated("url", keep=False)]
    if not dupes.empty:
        print(f"\nWARNING: {len(dupes)} duplicate URL(s) detected")

    print(f"\n{summary.to_string(index=False)}")
    print(f"\n{len(df)} records  |  avg word count: {df['word_count'].mean():.0f}  |  "
          f"html: {(df['content_type'] == 'html').sum()}  pdf: {(df['content_type'] == 'pdf').sum()}")

    if args.export == "csv":
        out = path.with_suffix(".csv")
        summary.to_csv(out, index=False)
        print(f"\nExported → {out}")


if __name__ == "__main__":
    main()
