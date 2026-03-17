# MedEase-Utils — Scraping Meta-Plan (Phase 1)
**Created:** 2026-03-16
**Scope:** `Scraping/` — Emory DAS corpus builder for the MedEase RAG pipeline

---

## Context & Goal

MedEase is a RAG-powered assistant. Its retrieval quality depends entirely on the quality of its corpus. The role of this repo (`MedEase-Utils`) is to build and maintain that corpus by systematically harvesting structured content from educational and institutional websites.

**Phase 1 target:** `accessibility.emory.edu` (Emory Disability Access Services)
**Why this source:** DAS content (accommodation procedures, faculty resources, policies) is exactly the kind of structured, factual, question-answerable text that anchors a reliable RAG agent.
**Phase 1 end goal:** A complete, versioned JSON data lake of all DAS pages and documents, ready to be chunked and indexed into ChromaDB downstream.

---

## Resolved Decisions

| Question | Decision |
|---|---|
| Target vector DB? | ChromaDB — but embedding pipeline is **out of scope** for this project. This project delivers raw corpus only. |
| Refresh cadence? | Weekly. Each run records a `last_updated` datetime in the corpus metadata. |
| Include PDFs? | Yes. V1's exclusion of `.pdf` was unintentional and must be corrected in V2. |
| Content freshness SLA? | None enforced at this layer. |

---

## V1 — Proof of Concept

**Status: Done**
**Delivered:** `Scraping/test.py` + `Scraping/emory_data.json` (30 pages, ~118KB)

### What V1 Achieved

| Goal | Status |
|---|---|
| Async BFS crawl with domain filtering | Done |
| Main content extraction via `css_selector="main"` | Done |
| Politeness delay (2s) | Done |
| URL deduplication | Done |
| JSON output | Done |
| Title extraction | Broken — all records show `"No Title"` |
| Dynamic timestamp | Broken — hardcoded to `"2026-01-18"` |
| Retry logic | Missing |
| Incremental updates | Missing |
| PDF inclusion | Missing (unintentionally filtered out) |

### V1 Limitations (Blocking for Production Use)

1. **Broken metadata** — title and timestamp fields are unusable; RAG citations will be malformed
2. **Incomplete corpus** — V1 capped at 50 pages and found 30; actual site scope is unknown. The 30-page figure should not be treated as ground truth.
3. **PDFs excluded** — linked documents (forms, policy PDFs) are silently skipped, leaving gaps in the corpus
4. **Full-rewrite on every run** — no incremental update logic; entire file is overwritten each run
5. **No error recovery** — a single network blip silently drops a page
6. **Hardcoded, non-reusable** — `BASE_URL`, `DOMAIN`, `css_selector` all baked in
7. **No requirements file** — not reproducible without tribal knowledge
8. **No schema validation** — malformed records can silently corrupt the data lake
9. **`read.py` is a stub** — data inspection tooling essentially doesn't exist

---

## V2 — Production-Ready DAS Corpus Builder

**Target:** A reliable, reproducible scraper that produces a complete and auditable corpus covering the full scope of `accessibility.emory.edu`.
**Scope:** Emory DAS only. Multi-site generalization is Phase 2.

---

### Pre-Step: Site Discovery (Site Map)

Before any content scraping, V2 must establish the **complete URL inventory** of the domain. V1 never did this — it just crawled until it ran out of queue or hit the 50-page cap. The actual number of pages is unknown.

**Approach (in priority order):**

1. **Check for `sitemap.xml`** — fetch `https://accessibility.emory.edu/sitemap.xml` and `sitemap_index.xml`. If present, parse all `<loc>` entries. This is the fastest and most complete discovery method.
2. **BFS link crawl (fallback)** — if no sitemap exists, run a lightweight BFS pass with **no page cap** and **no content extraction** (just follow links, collect URLs). This produces a `emory_sitemap.json` of all discovered URLs before any scraping begins.

**Output:** `Scraping/emory_sitemap.json` — a flat list of all discovered URLs with their type (`html` or `pdf`).

```json
[
  { "url": "https://accessibility.emory.edu/students/", "type": "html" },
  { "url": "https://accessibility.emory.edu/forms/accommodation-request.pdf", "type": "pdf" }
]
```

This sitemap file serves as the authoritative crawl target list and can be version-controlled to track site growth over time. Every subsequent scraping run starts from this file rather than re-discovering the site from scratch.

---

### V2 Goals

#### 2.1 — PDF Handling
- V1 explicitly filtered out `.pdf`, `.jpg`, `.png` — PDFs must now be included
- HTML pages are handled by `crawl4ai` as before
- PDFs require a separate extraction path: download the file and extract text using `pdfplumber` or `pymupdf`, converting to plain text (stored in the `markdown` field for schema consistency)
- Record `content_type: "html"` or `content_type: "pdf"` in the schema to allow downstream consumers to handle them differently if needed

#### 2.2 — Fix Broken Metadata
- Extract page title from `<title>` tag via `crawl4ai`'s `result.metadata` or a fallback `BeautifulSoup` parse of `result.html`
- For PDFs, use the document's metadata title if available, otherwise derive from filename
- Replace hardcoded date with `datetime.date.today().isoformat()`
- Add `scraped_at` (ISO 8601 datetime) for per-record audit precision
- Add a top-level `run_metadata` envelope (see schema below)

#### 2.3 — Incremental Crawling (Weekly Refresh)
- Load existing corpus on startup; build a `{url: content_hash}` index
- On re-crawl, skip pages whose content hash hasn't changed
- Append new records (new pages discovered since last run); update changed records; preserve unchanged records
- Write atomically (write to temp file, then rename) to prevent corrupt JSON on crash
- Target: weekly runs where most pages are skipped (unchanged), keeping runtime low

#### 2.4 — Retry Logic
- Wrap `crawler.arun()` in a retry loop: up to 3 attempts with exponential backoff (2s, 4s, 8s)
- Log permanently failed URLs to `failed_urls.log` after exhausting retries
- Failed URLs should not block the rest of the crawl

#### 2.5 — Schema Enforcement
- Define a `Page` dataclass (or Pydantic model):
  ```python
  @dataclass
  class Page:
      url: str
      title: str
      content_type: str       # "html" or "pdf"
      markdown: str           # plain text for PDFs, markdown for HTML
      last_scraped: str       # ISO date (YYYY-MM-DD)
      scraped_at: str         # ISO datetime
      word_count: int
      content_hash: str       # MD5 of markdown for change detection
  ```
- Validate every record before writing; reject and log records with empty content or word count below threshold

#### 2.6 — Config File
- Extract all constants (`BASE_URL`, `DOMAIN`, `MAX_PAGES`, `POLITENESS_DELAY`, `css_selector`) into `config.json`
- The scraper reads config at startup; no hardcoded values in code
- Bridge toward Phase 2: adding a new site means adding a new config entry, not forking code

#### 2.7 — Output Format
- Corpus file: `emory_data_YYYY-MM-DD.json` per run, plus `emory_data_latest.json` as a stable pointer
- Run audit log: `run_log.jsonl` — one line per run with: `run_date`, `pages_crawled`, `pages_new`, `pages_updated`, `pages_unchanged`, `pages_failed`, `duration_seconds`
- Top-level corpus envelope:
  ```json
  {
    "source": "accessibility.emory.edu",
    "last_updated": "2026-03-16T14:32:01",
    "total_pages": 47,
    "records": [ ... ]
  }
  ```

#### 2.8 — Tooling & DX
- `requirements.txt` with pinned versions: `crawl4ai`, `pandas`, `pdfplumber` (or `pymupdf`)
- `read.py` upgraded: summary table (url, title, content_type, word_count, last_scraped), duplicate URL detection, export to CSV
- Structured logging to stdout: `INFO`, `WARNING`, `ERROR`

---

### V2 Success Criteria

- [ ] Site discovery step produces a complete `emory_sitemap.json` — total URL count is known before scraping starts
- [ ] All HTML pages have non-empty, correct titles
- [ ] All PDF links are downloaded and their text extracted into corpus records
- [ ] Timestamps are accurate and dynamic
- [ ] Re-running on an unchanged site produces zero record updates (idempotent)
- [ ] A single network failure does not drop the page; retries exhaust before logging to `failed_urls.log`
- [ ] A new developer can install and run with only `pip install -r requirements.txt && python scraper.py`
- [ ] `read.py` outputs a summary table for all records

---

## Downstream Handoff (RAG Pipeline Interface)

V2's output (`emory_data_latest.json`) will be consumed by the MedEase RAG ingestion pipeline. The schema is a contract — changes must be coordinated with the ingestion side.

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
      "markdown": "# Register for Accommodations\n...",
      "last_scraped": "2026-03-16",
      "scraped_at": "2026-03-16T14:32:01",
      "word_count": 412,
      "content_hash": "a3f5c..."
    }
  ]
}
```

The downstream RAG ingestion pipeline (out of scope here) will:
1. Validate schema
2. Chunk by heading/paragraph
3. Generate embeddings
4. Index into ChromaDB

---

## Phase 2 Preview (Out of Scope for Now)

Once V2 is stable and the DAS corpus is validated end-to-end in the RAG pipeline, Phase 2 will extend the scraper to additional sources:

- Other Emory student services (registrar, housing, financial aid)
- Potentially other university DAS sites for broader coverage
- Config-driven multi-site orchestration (one config entry per site, separate output files per source)
- Scheduled runs (cron or GitHub Actions) for automated weekly refresh across all sources
