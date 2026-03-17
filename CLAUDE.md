# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Checkpoint — 2026-03-17**
> V2 delivered and merged (PR #2). Corpus: 51 records (42 HTML + 9 PDF), avg 293 words, 0 failed internal URLs.
> V3 (gap-closure) is planned in `log/scraping-meta-plan.md`. No V3 code has been written yet.

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

Also install the Playwright Chromium browser (required by `crawl4ai`):

```bash
playwright install chromium
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
  "total_pages": 51,
  "records": [
    {
      "url": "https://accessibility.emory.edu/students/register/",
      "title": "Register for Accommodations",
      "description": "Learn how to register with Emory DAS.",
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

Note: `description` was added in V2. It comes from `<meta name="description">` for HTML pages and is `""` for PDFs (PDF metadata extraction is a V3 goal).

## Key Design Decisions

- **Site discovery first** — `main.py` always runs `discovery/sitemap.py` before scraping; this produces a complete URL inventory rather than relying on BFS crawl depth.
- **Staleness detection** — `sitemap.py` validates the sitemap by sampling URLs evenly (every N-th entry) and checking HTTP status. If >20% return 404, the sitemap is considered stale and BFS discovery runs instead. This was necessary because `accessibility.emory.edu` restructured its URL paths after the sitemap was last generated (~80% of sitemap URLs were dead).
- **BS4 title extraction** — `crawl4ai 0.8`'s `result.metadata.title` is unreliable. `html_scraper.py` uses BeautifulSoup to parse `result.html` directly: `<title>` (first segment before `|`) → `<h1>` → URL slug fallback.
- **`.raw_markdown`** — `crawl4ai 0.8` returns `result.markdown` as a `MarkdownGenerationResult` object, not a string. Always use `result.markdown.raw_markdown`.
- **PDFs included** — V1 filtered PDFs unintentionally; V2 extracts them via `pdf_extractor.py` (pdfplumber + pytesseract/pdf2image OCR fallback for scanned PDFs).
- **Incremental by default** — re-runs skip pages whose `content_hash` hasn't changed; designed for weekly refresh cadence.
- **Orphan pruning** — records whose URLs are no longer in the current sitemap are removed on each run.
- **Config-driven** — all site-specific values live in `config/emory_das.json`, not in code.

## Known Gaps (V3 targets)

- **No atomic write** — `main.py` writes directly to the output file; a crash mid-write corrupts it. V3: write to temp file, then `os.replace()`.
- **No per-record validation gate** — records with empty markdown are currently logged but still written. V3: reject before write.
- **PDF metadata not extracted** — `description` is always `""` for PDFs. V3: read embedded title/subject from pdfplumber.
- **No `--validate` flag in `read.py`** — no CLI quality gate. V3: add `--validate` that fails with non-zero exit if records fail quality thresholds.

## Logs & Planning

- `log/v1_assessment.md` — V1 post-mortem
- `log/v2_assessment.md` — V2 delivery summary + V3 rationale
- `log/scraping-meta-plan.md` — V1→V2→V3 planning document
