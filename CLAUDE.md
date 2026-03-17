# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

MedEase-Utils harvests structured content from educational websites to build a natural language corpus for the MedEase RAG pipeline. Phase 1 targets `accessibility.emory.edu` (Emory Disability Access Services). Downstream consumer is ChromaDB — but embedding and indexing are out of scope here; this project delivers raw corpus only.

## Checkpoint — 2026-03-17

V2 is complete. PR #2 is open against `main`.

**Corpus:** 51 records (42 HTML + 9 PDFs), avg 293 words, 0 failed scrapes.
**Next:** Merge PR #2 → validate corpus in MedEase RAG pipeline → Phase 2 (multi-site).

---

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
python read.py --file output/emory_das_data_2026-03-17.json
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
│   └── sitemap.py            # Enumerate all URLs: sitemap.xml (with staleness check) → BFS fallback
├── scrapers/
│   ├── html_scraper.py       # crawl4ai HTML scraper; BeautifulSoup title/description extraction
│   └── pdf_extractor.py      # pdfplumber + pytesseract OCR fallback for scanned PDFs
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
  "last_updated": "2026-03-17T14:32:01",
  "total_pages": 51,
  "records": [
    {
      "url": "https://accessibility.emory.edu/students-accommodations/registration.html",
      "title": "Register for Accommodations",
      "description": "...",
      "content_type": "html",
      "markdown": "# Register for Accommodations\n...",
      "last_scraped": "2026-03-17",
      "scraped_at": "2026-03-17T14:32:01",
      "word_count": 368,
      "content_hash": "a3f5c..."
    }
  ]
}
```

## Key Design Decisions

- **Sitemap with staleness validation** — `discovery/sitemap.py` fetches `sitemap.xml` then probes an evenly-spaced sample; if >20% return 404, it falls back to BFS. The DAS site was restructured (old sitemap had 86% dead URLs) — this detection was essential.
- **BeautifulSoup for titles** — `crawl4ai 0.8`'s `result.metadata.title` is unreliable; BS4 parses raw HTML directly. Fallback chain: `<title>` (first segment before `|`) → `<h1>` → URL slug.
- **`description` field** — captures `<meta name="description">` per page. Added to support no-vector RAG benchmarking (passing corpus metadata directly to Claude without embeddings).
- **PDFs included** — V1 filtered PDFs unintentionally; V2 extracts them via `pdf_extractor.py` with OCR fallback for scanned documents.
- **Incremental by default** — re-runs compare sitemap `lastmod` against stored `last_scraped`; only changed/new pages are re-scraped. Orphaned records (URLs no longer in sitemap) are pruned on each run.
- **Config-driven** — all site-specific values live in `config/emory_das.json`, not in code.

## Known Gaps (Post-V2)

- Atomic write (temp+rename) not implemented — direct file write used.
- Per-record validation before write not implemented.
- PDF `description` always `""` — no equivalent of meta description for PDFs.

## Logs & Planning

- `log/v1_assessment.md` — V1 post-mortem
- `log/scraping-meta-plan.md` — full V1→V2 planning doc with crossed-out completed items and open gaps
