# MedEase-Utils

Async web scraper that harvests structured content from educational websites to build a natural language corpus for the [MedEase](https://github.com/MedEaseWeb) RAG pipeline.

**Phase 1 target:** `accessibility.emory.edu` (Emory Disability Access Services)
**Downstream consumer:** ChromaDB (embedding and indexing are handled separately)
**Current corpus:** 51 records — 42 HTML pages + 9 PDF documents, avg 293 words

---

## Setup

### System dependencies

```bash
# macOS
brew install poppler tesseract

# Ubuntu/Debian
apt-get install poppler-utils tesseract-ocr
```

### Python dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
cd Scraping/

# Full pipeline — discovers URLs, scrapes new/changed pages, extracts PDFs
python main.py

# Force re-run site discovery (use when site structure may have changed)
python main.py --rediscover

# Inspect the latest corpus
python read.py
python read.py --export csv
```

---

## How It Works

```
sitemap.xml ──► staleness check ──► BFS fallback (if stale)
                                          │
                                    emory_sitemap.json
                                          │
                    ┌─────────────────────┴──────────────────────┐
                  HTML                                          PDF
                    │                                            │
             crawl4ai scrape                            pdfplumber extract
          BeautifulSoup metadata                      pytesseract OCR fallback
                    │                                            │
                    └─────────────────────┬──────────────────────┘
                                   corpus records
                                          │
                             incremental merge (lastmod diff)
                                          │
                          emory_das_data_YYYY-MM-DD.json
```

Each run compares sitemap `lastmod` dates against stored `last_scraped` values and only re-scrapes changed or new pages. Orphaned records (pages removed from the site) are pruned automatically.

---

## Output Schema

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

`content_type` is `"html"` or `"pdf"`. The `description` field captures `<meta name="description">` for HTML pages and is used for no-vector RAG benchmarking.

---

## Project Structure

```
MedEase-Utils/
├── Scraping/
│   ├── config/
│   │   └── emory_das.json            # Site config (URL, domain, selectors, politeness)
│   ├── core/
│   │   ├── schema.py                 # Page + CorpusEnvelope dataclasses
│   │   └── config_loader.py
│   ├── discovery/
│   │   └── sitemap.py                # URL inventory: sitemap.xml → validation → BFS
│   ├── scrapers/
│   │   ├── html_scraper.py           # crawl4ai + BeautifulSoup
│   │   └── pdf_extractor.py          # pdfplumber + OCR
│   ├── output/                       # Generated corpus (gitignored)
│   ├── runs/                         # run_log.jsonl, failed_urls.log (gitignored)
│   ├── legacy/                       # V1 reference
│   ├── main.py                       # Entry point
│   └── read.py                       # Inspection CLI
├── log/
│   ├── v1_assessment.md
│   ├── v2_assessment.md
│   └── scraping-meta-plan.md         # Planning doc with V1→V2→V3 roadmap
└── requirements.txt
```

---

## Logs & Planning

| File | Purpose |
|---|---|
| `log/v1_assessment.md` | V1 post-mortem |
| `log/v2_assessment.md` | V2 post-implementation review |
| `log/scraping-meta-plan.md` | Full planning doc — V1→V2 (completed) + V3 roadmap |
