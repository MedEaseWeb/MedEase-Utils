# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

MedEase-Utils harvests structured content from educational websites to build a natural language corpus for the MedEase RAG pipeline. Phase 1 targets `accessibility.emory.edu` (Emory Disability Access Services). Downstream consumer is ChromaDB — but embedding and indexing are out of scope here; this project delivers raw corpus only.

## System Dependencies

Before `pip install`, install these system binaries:

```bash
# macOS
brew install poppler tesseract

# Ubuntu/Debian
apt-get install poppler-utils tesseract-ocr
```

## Running the Scraper

```bash
pip install -r requirements.txt

cd Scraping/
python main.py                                          # Full pipeline (uses cached sitemap if present)
python main.py --rediscover                             # Force re-fetch sitemap.xml before scraping
python main.py --config config/emory_das.json          # Explicit config (same as default)
python read.py                                          # Inspect latest corpus
python read.py --file output/emory_das_data_2026-03-16.json
python read.py --export csv
```

## Architecture

```
Scraping/
├── config/
│   └── emory_das.json        # Site config: base_url, domain, css_selector, politeness, etc.
├── core/
│   ├── schema.py             # Page dataclass + CorpusEnvelope
│   └── config_loader.py      # Loads config/ JSON files
├── discovery/
│   └── sitemap.py            # Step 1: enumerate all URLs (sitemap.xml → BFS fallback)
├── scrapers/
│   ├── html_scraper.py       # crawl4ai-based HTML scraper with retry logic
│   └── pdf_extractor.py      # pdfplumber PDF downloader + text extractor
├── output/                   # Generated corpus files (gitignored, except .gitkeep)
├── runs/                     # run_log.jsonl + failed_urls.log (gitignored)
├── legacy/                   # V1 reference code (scraper_v1.py, emory_data_v1.json)
├── main.py                   # Entry point — orchestrates full pipeline
└── read.py                   # Corpus inspection CLI
```

## Corpus Output Schema

```json
{
  "source": "accessibility.emory.edu",
  "last_updated": "2026-03-16T14:32:01",
  "total_pages": 47,
  "records": [
    {
      "url": "https://accessibility.emory.edu/students/register/",
      "title": "Register for Accommodations",
      "content_type": "html",
      "markdown": "...",
      "last_scraped": "2026-03-16",
      "scraped_at": "2026-03-16T14:32:01",
      "word_count": 412,
      "content_hash": "a3f5c..."
    }
  ]
}
```

## Key Design Decisions

- **Site discovery first** — `main.py` always runs `discovery/sitemap.py` before scraping; this produces a complete URL inventory rather than relying on BFS crawl depth
- **PDFs included** — V1 filtered PDFs unintentionally; V2 extracts them via `pdf_extractor.py`
- **Incremental by default** — re-runs skip pages whose `content_hash` hasn't changed; designed for weekly refresh cadence
- **Config-driven** — all site-specific values live in `config/emory_das.json`, not in code

## Logs & Planning

- `log/v1_assessment.md` — V1 post-mortem
- `log/scraping-meta-plan.md` — V1→V2 planning document with resolved decisions
