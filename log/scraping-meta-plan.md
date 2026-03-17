# MedEase-Utils — Scraping Meta-Plan (Phase 1)
**Created:** 2026-03-16
**Checkpoint:** 2026-03-17 — V2 complete, PR #2 open against main
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

## ~~V1 — Proof of Concept~~ ✅ Archived

**Status: Done — code moved to `Scraping/legacy/`**
**Delivered:** `Scraping/legacy/scraper_v1.py` + `Scraping/legacy/emory_data_v1.json` (30 pages, ~118KB)

### What V1 Achieved

| Goal | Status |
|---|---|
| Async BFS crawl with domain filtering | ~~Done~~ |
| Main content extraction via `css_selector="main"` | ~~Done~~ |
| Politeness delay (2s) | ~~Done~~ |
| URL deduplication | ~~Done~~ |
| JSON output | ~~Done~~ |
| Title extraction | ~~Broken — all records show `"No Title"`~~ → Fixed in V2 |
| Dynamic timestamp | ~~Broken — hardcoded to `"2026-01-18"`~~ → Fixed in V2 |
| Retry logic | ~~Missing~~ → Added in V2 |
| Incremental updates | ~~Missing~~ → Added in V2 |
| PDF inclusion | ~~Missing (unintentionally filtered out)~~ → Added in V2 |

### ~~V1 Limitations (Blocking for Production Use)~~

1. ~~**Broken metadata** — title and timestamp fields are unusable; RAG citations will be malformed~~
2. ~~**Incomplete corpus** — V1 capped at 50 pages and found 30; actual site scope is unknown~~
3. ~~**PDFs excluded** — linked documents (forms, policy PDFs) are silently skipped~~
4. ~~**Full-rewrite on every run** — no incremental update logic~~
5. ~~**No error recovery** — a single network blip silently drops a page~~
6. ~~**Hardcoded, non-reusable** — `BASE_URL`, `DOMAIN`, `css_selector` all baked in~~
7. ~~**No requirements file** — not reproducible without tribal knowledge~~
8. ~~**No schema validation** — malformed records can silently corrupt the data lake~~
9. ~~**`read.py` is a stub** — data inspection tooling essentially doesn't exist~~

---

## V2 — Production-Ready DAS Corpus Builder ✅ Complete

**Status: Done — PR #2 open, pending merge to main**
**Result: 51 records (42 HTML + 9 PDFs), avg 293 words, 0 failed (1 external 403)**

**Target:** A reliable, reproducible scraper that produces a complete and auditable corpus covering the full scope of `accessibility.emory.edu`.
**Scope:** Emory DAS only. Multi-site generalization is Phase 2.

---

### ~~Pre-Step: Site Discovery (Site Map)~~ ✅

~~Before any content scraping, V2 must establish the **complete URL inventory** of the domain. V1 never did this — it just crawled until it ran out of queue or hit the 50-page cap. The actual number of pages is unknown.~~

**What was built:** `discovery/sitemap.py` — fetches `sitemap.xml`, validates it with evenly-spaced sampling (detects stale sitemaps via >20% 404 rate), falls back to full BFS crawl. Saves `output/emory_sitemap.json` as a cached artifact.

**Finding during implementation:** The live site had been restructured — the sitemap had 86% dead URLs (old `students/*` paths, new paths are `students-accommodations/*`). BFS fallback was essential.

**Output:** `Scraping/output/emory_sitemap.json` — flat list of `{"url", "type", "lastmod"}` dicts. 51 live URLs discovered (42 HTML + 9 PDF).

---

### V2 Goals

#### ~~2.1 — PDF Handling~~ ✅
- ~~V1 explicitly filtered out `.pdf`, `.jpg`, `.png` — PDFs must now be included~~
- ~~PDFs require a separate extraction path: download the file and extract text using `pdfplumber` or `pymupdf`~~
- ~~Record `content_type: "html"` or `content_type: "pdf"` in the schema~~

**What was built:** `scrapers/pdf_extractor.py` — `pdfplumber` → `pytesseract` + `pdf2image` OCR fallback for scanned/image-only PDFs. 9 PDFs extracted successfully.

#### ~~2.2 — Fix Broken Metadata~~ ✅
- ~~Extract page title from `<title>` tag via `crawl4ai`'s `result.metadata` or a fallback `BeautifulSoup` parse of `result.html`~~
- ~~Replace hardcoded date with `datetime.date.today().isoformat()`~~
- ~~Add `scraped_at` (ISO 8601 datetime) for per-record audit precision~~

**What was built:** `BeautifulSoup` parse of `result.html` with fallback chain: `<title>` tag (first segment before `|`) → `<h1>` → URL slug. Note: `crawl4ai 0.8`'s `result.metadata.title` was unreliable — BS4 was necessary. Added `description` field from `<meta name="description">` for RAG benchmarking context.

#### ~~2.3 — Incremental Crawling (Weekly Refresh)~~ ✅
- ~~Load existing corpus on startup; build a `{url: content_hash}` index~~
- ~~On re-crawl, skip pages whose content hash hasn't changed~~
- ~~Write atomically (write to temp file, then rename) to prevent corrupt JSON on crash~~

**What was built:** Compares sitemap `lastmod` against stored `last_scraped` — avoids fetching pages that haven't changed. Also prunes orphaned records no longer present in the current sitemap. Idempotency confirmed: re-run on unchanged site → 0 updates.

> **Note:** Atomic write (temp file + rename) was not implemented — direct write used instead. Low-risk for current use but worth revisiting.

#### ~~2.4 — Retry Logic~~ ✅
- ~~Wrap `crawler.arun()` in a retry loop: up to 3 attempts with exponential backoff (2s, 4s, 8s)~~
- ~~Log permanently failed URLs to `failed_urls.log` after exhausting retries~~
- ~~Failed URLs should not block the rest of the crawl~~

**What was built:** Both `html_scraper.py` and `pdf_extractor.py` have retry loops with exponential backoff. Failures logged to `Scraping/runs/failed_urls.log`.

#### ~~2.5 — Schema Enforcement~~ ✅
**What was built:** `core/schema.py` — `Page` dataclass. `description` field added beyond original spec.

```python
@dataclass
class Page:
    url: str
    title: str
    description: str           # <meta name="description"> — added for RAG benchmarking
    content_type: str          # "html" or "pdf"
    markdown: str
    last_scraped: str
    scraped_at: str
    word_count: int
    content_hash: str
```

> **Note:** Per-record validation (reject empty/below-threshold records before write) was not implemented.

#### ~~2.6 — Config File~~ ✅
**What was built:** `Scraping/config/emory_das.json` — all site constants externalized.

#### ~~2.7 — Output Format~~ ✅
**What was built:** Dated output files (`emory_das_data_YYYY-MM-DD.json`) + `_latest.json` stable pointer. `run_log.jsonl` per run. `CorpusEnvelope` with `source`, `last_updated`, `total_pages`.

#### ~~2.8 — Tooling & DX~~ ✅
**What was built:** `requirements.txt` (with `beautifulsoup4` added beyond original spec), `read.py` with summary table + description column + CSV export, structured logging.

---

### V2 Success Criteria

- [x] Site discovery produces a complete `emory_sitemap.json` — **51 URLs found**
- [x] All HTML pages have non-empty, correct titles — **verified: `"Register for Accommodations"` not `"Registration"`**
- [x] All PDF links are downloaded and their text extracted — **9 PDFs extracted**
- [x] Timestamps are accurate and dynamic
- [x] Re-running on an unchanged site produces zero record updates (idempotent)
- [x] A single network failure does not drop the page; retries exhaust before `failed_urls.log`
- [x] A new developer can install and run with `pip install -r requirements.txt && python main.py`
- [x] `read.py` outputs a summary table for all records

---

## Actual Corpus Output Schema (V2 Final)

```json
{
  "source": "accessibility.emory.edu",
  "last_updated": "2026-03-17T...",
  "total_pages": 51,
  "records": [
    {
      "url": "https://accessibility.emory.edu/students-accommodations/registration.html",
      "title": "Register for Accommodations",
      "description": "...",
      "content_type": "html",
      "markdown": "# Register for Accommodations\n...",
      "last_scraped": "2026-03-17",
      "scraped_at": "2026-03-17T...",
      "word_count": 368,
      "content_hash": "..."
    }
  ]
}
```

> **Downstream handoff:** This schema is the contract with the MedEase RAG ingestion pipeline. The `description` field was added in V2 to support no-vector RAG benchmarking (e.g., passing corpus metadata directly to Claude without embeddings). Any schema changes must be coordinated with the ingestion side.

---

## Open Items / Known Gaps

- **Atomic write not implemented** — corpus written directly, not via temp+rename. Low risk at current scale.
- **Per-record validation not implemented** — records with empty markdown are not explicitly rejected before write (word_count threshold in crawl4ai config provides partial coverage).
- **PDF description always `""`** — no equivalent of `<meta name="description">` for PDFs.
- **External PDFs blocked** — 1 external PDF (ABA toolkit) permanently failed with HTTP 403. Expected, not fixable without authentication.

---

## V3 — Gap Closure

**Status: Planned**
**Scope:** Fix known V2 gaps and validate corpus quality end-to-end. No new sites, no scope expansion.
**Goal:** Bring maturity from 7/10 → 9/10 before handing the corpus to the RAG ingestion pipeline.

---

### V3 Goals

#### 3.1 — Atomic Write
- Current: corpus JSON written directly to `output/` — a crash mid-write corrupts the file
- Fix: write to a temp file (`emory_das_data_latest.tmp.json`), then `os.replace()` on success
- Applies to both the dated file and `_latest.json`

#### 3.2 — Per-Record Validation
- Current: records with empty markdown can silently enter the corpus
- Fix: before appending any record to `records`, check `word_count > 0` and `markdown.strip() != ""`
- Rejected records should be logged to `runs/failed_urls.log` with reason `"empty content after scrape"`
- This catches pages that render a 200 but return no meaningful content (e.g. JS-only pages, redirect pages)

#### 3.3 — PDF Metadata Extraction
- Current: PDF `title` is derived from filename slug (e.g. `"Das Flexibility Attendance Form"`); `description` is always `""`
- Fix: use `pdfplumber`'s `pdf.metadata` to extract the document's embedded `Title` and `Subject` fields where available
- Fallback chain: PDF metadata title → filename slug (current behavior)
- `description`: try PDF metadata `Subject` field → `""`

#### 3.4 — Corpus Quality Gate in `read.py`
- Current: `read.py` shows summary table but does not flag quality issues
- Add `--validate` flag that checks every record and reports:
  - Records with `word_count == 0`
  - Records with empty `title` or `title` that is still a URL slug (heuristic: all lowercase, contains `-`)
  - Records with empty `description` (informational, not a failure)
  - Duplicate `content_hash` values (identical content at different URLs)
- Exit with non-zero code if any hard failures found — usable as a pre-handoff quality gate

---

### V3 Success Criteria

- [ ] Re-running the scraper on an interrupted write leaves corpus intact (atomic write)
- [ ] Zero records with `word_count == 0` in the output corpus
- [ ] PDFs with embedded metadata show real titles (verified against actual PDF files)
- [ ] `python read.py --validate` exits 0 on the current clean corpus
- [ ] `python read.py --validate` exits non-zero when a synthetic bad record is injected (test)

---

## Phase 2 Preview (Out of Scope for Now)

Once V2 is stable and the DAS corpus is validated end-to-end in the RAG pipeline, Phase 2 will extend the scraper to additional sources:

- Other Emory student services (registrar, housing, financial aid)
- Potentially other university DAS sites for broader coverage
- Config-driven multi-site orchestration (one config entry per site, separate output files per source)
- Scheduled runs (cron or GitHub Actions) for automated weekly refresh across all sources
