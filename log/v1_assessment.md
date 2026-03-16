# MedEase-Utils — v1 Assessment Log
**Date:** 2026-03-16
**Assessed by:** Claude (claude-sonnet-4-6)
**Purpose:** Systematic review of the MedEase-Utils repo as a datasource gatherer / data lake foundation for the MedEase RAG ecosystem.

---

## Project Structure

```
MedEase-Utils/
├── Scraping/
│   ├── test.py           # Main scraper (100 lines)
│   ├── read.py           # Data loader (6 lines, incomplete)
│   └── emory_data.json   # Scraped output: 30 records, 118KB
└── test.py               # Empty file
```

---

## What It Does

An async web scraper using `crawl4ai` targeting a single source:

- **Target:** `accessibility.emory.edu`
- **Pages scraped:** 30 (student accommodations, faculty resources, workplace accommodations)
- **Content extraction:** CSS selector `main` → converted to markdown
- **Output:** JSON array written to `emory_data.json`

---

## Data Lake Schema

```json
{
  "url": "https://accessibility.emory.edu/...",
  "title": "No Title",
  "markdown": "# Register for Accommodations\n...",
  "last_scraped": "2026-01-18"
}
```

- 30 records, all unique URLs
- Average page length: ~3,800 characters / ~423 words
- Markdown format is clean and RAG-friendly

---

## What Works

- Async crawling with 2-second politeness delay
- Strict domain filtering (no external links followed)
- Main content extraction (navbars/footers excluded)
- Graceful error handling
- URL deduplication
- Valid, pretty-printed JSON output

---

## Issues Found

| Issue | Severity |
|---|---|
| Title extraction broken — all records show "No Title" | Medium |
| Timestamp is hardcoded (`"2026-01-18"`), not dynamic | Medium |
| No `requirements.txt`, no README, no docs | High |
| Hardcoded for one domain only — not reusable | High |
| No retry logic on network failures | Medium |
| Full JSON rewrite every run — no incremental updates | High |
| `read.py` is essentially empty (6 lines, loads data only) | High |
| No data validation or schema enforcement | Medium |
| No tests | Medium |
| `css_selector="main"` is site-specific — won't generalize | High |

---

## RAG Integration Readiness

**Strengths:**
- Markdown format is ideal for chunking
- Content-focused extraction reduces noise
- Source URLs preserved for citation/traceability
- ~400 words/page average — sufficient chunk density

**Gaps:**
- No semantic chunking pipeline
- No metadata enrichment (categories, publish dates, authors)
- No deduplication logic
- No embedding generation
- No vector DB integration
- No update tracking (can't detect changed pages)

**Recommended pipeline:**
```
raw JSON
  → validate schema
  → enrich metadata (title, category, date)
  → clean & deduplicate
  → chunk by heading/paragraph
  → generate embeddings
  → index in vector DB
```

---

## Overall Assessment

**Maturity: 2 / 10**
Functional proof-of-concept for a single site. The scraping core is intentional (RAG-aware CSS selectors, async, markdown output) but the project is far from production-ready as a multi-source data lake.

### Prioritized Next Steps

1. **Immediate:** Fix title extraction, make timestamp dynamic, add `requirements.txt`
2. **Short-term:** Config-driven multi-site support, incremental crawling, retry logic, README
3. **RAG pipeline:** Chunking, metadata enrichment, embedding generation, vector DB integration
