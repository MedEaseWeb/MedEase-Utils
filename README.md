# MedEase-Utils

Async web scraper that harvests structured content from educational websites to build a raw text corpus for the [MedEase](https://github.com/MedEaseWeb) RAG pipeline.

**Phase 1 target:** `accessibility.emory.edu` (Emory Disability Access Services)

---

## Setup

**System dependencies (required before pip install):**

```bash
# macOS
brew install poppler tesseract

# Ubuntu/Debian
apt-get install poppler-utils tesseract-ocr
```

**Python dependencies:**

```bash
pip install -r requirements.txt
playwright install chromium   # required by crawl4ai
```

---

## Usage

```bash
cd Scraping/

python main.py                                    # Full pipeline run
python main.py --rediscover                       # Force re-fetch sitemap before scraping
python main.py --config config/emory_das.json     # Explicit config (same as default)

python read.py                                    # Inspect latest corpus
python read.py --file output/emory_das_data_2026-03-17.json
python read.py --export csv
```

---

## Pipeline

```
config/emory_das.json
        │
        ▼
┌───────────────────┐
│  discovery/       │   sitemap.xml → validate → BFS fallback if stale
│  sitemap.py       │   output: Scraping/emory_sitemap.json
└────────┬──────────┘
         │  URL inventory (html + pdf entries)
         ▼
┌───────────────────┐
│  Phase A: HTML    │   crawl4ai + BeautifulSoup metadata extraction
│  html_scraper.py  │   exponential backoff retry (2s → 4s → 8s)
└────────┬──────────┘
         │  Page records + discovered PDF links
         ▼
┌───────────────────┐
│  Phase B: PDF     │   pdfplumber text extraction + OCR fallback
│  pdf_extractor.py │   (pytesseract + pdf2image for scanned PDFs)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  main.py          │   incremental merge, orphan pruning, atomic write
│  orchestrator     │   output: Scraping/output/emory_das_data_YYYY-MM-DD.json
└───────────────────┘        + Scraping/output/emory_das_data_latest.json
                             + Scraping/runs/run_log.jsonl
                             + Scraping/runs/failed_urls.log
```

---

## Output Schema

```json
{
  "source": "accessibility.emory.edu",
  "last_updated": "2026-03-17T14:32:01",
  "total_pages": 51,
  "records": [
    {
      "url": "https://accessibility.emory.edu/students/register/",
      "title": "Register for Accommodations",
      "description": "Learn how to register with Emory DAS to receive academic accommodations.",
      "content_type": "html",
      "markdown": "# Register for Accommodations\n...",
      "last_scraped": "2026-03-17",
      "scraped_at": "2026-03-17T14:32:01",
      "word_count": 412,
      "content_hash": "a3f5c9..."
    }
  ]
}
```

---

## Project Structure

```
MedEase-Utils/
├── requirements.txt
├── README.md
├── CLAUDE.md
├── log/
│   ├── scraping-meta-plan.md     # V1→V2→V3 planning document
│   ├── v1_assessment.md          # V1 post-mortem
│   └── v2_assessment.md          # V2 delivery summary + V3 rationale
└── Scraping/
    ├── config/
    │   └── emory_das.json        # Site-specific config
    ├── core/
    │   ├── schema.py             # Page + CorpusEnvelope dataclasses
    │   └── config_loader.py      # JSON config loader
    ├── discovery/
    │   └── sitemap.py            # URL discovery: sitemap.xml + BFS fallback
    ├── scrapers/
    │   ├── html_scraper.py       # crawl4ai HTML scraper
    │   └── pdf_extractor.py      # pdfplumber + OCR PDF extractor
    ├── legacy/                   # V1 reference (scraper_v1.py, emory_data_v1.json)
    ├── output/                   # Generated corpus files (gitignored)
    ├── runs/                     # run_log.jsonl + failed_urls.log (gitignored)
    ├── main.py                   # Pipeline orchestrator
    └── read.py                   # Corpus inspection CLI
```

---

## Logs

| File | Contents |
|------|----------|
| `log/scraping-meta-plan.md` | End-to-end planning doc covering V1 through V3 |
| `log/v1_assessment.md` | V1 PoC post-mortem and gap analysis |
| `log/v2_assessment.md` | V2 delivery summary, quality assessment, V3 rationale |

---

## Downstream

V2's output (`emory_das_data_latest.json`) feeds the MedEase RAG ingestion pipeline. The schema above is a contract — changes must be coordinated with the ingestion side.

The downstream pipeline (out of scope here) will chunk by heading/paragraph, generate embeddings, and index into ChromaDB.
