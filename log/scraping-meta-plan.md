# MedEase-Utils — Scraping Meta-Plan (Phase 1)
**Created:** 2026-03-16
**Scope:** `Scraping/` — Emory DAS corpus builder for the MedEase RAG pipeline

> **Checkpoint — 2026-03-17**
> V2 complete and merged (PR #2). 51 records delivered (42 HTML + 9 PDF).
> V3 gap-closure section added below.

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

## ~~V1 — Proof of Concept~~ ✓ Done

**Status: Done**
**Delivered:** `Scraping/test.py` + `Scraping/emory_data.json` (30 pages, ~118KB)

### What V1 Achieved

| Goal | Status |
|---|---|
| ~~Async BFS crawl with domain filtering~~ | ~~Done~~ ✓ |
| ~~Main content extraction via `css_selector="main"`~~ | ~~Done~~ ✓ |
| ~~Politeness delay (2s)~~ | ~~Done~~ ✓ |
| ~~URL deduplication~~ | ~~Done~~ ✓ |
| ~~JSON output~~ | ~~Done~~ ✓ |
| Title extraction | Broken — all records show `"No Title"` |
| Dynamic timestamp | Broken — hardcoded to `"2026-01-18"` |
| Retry logic | Missing |
| Incremental updates | Missing |
| PDF inclusion | Missing (unintentionally filtered out) |

### V1 Limitations (Blocking for Production Use)

1. **Broken metadata** — title and timestamp fields are unusable; RAG citations will be malformed
2. **Incomplete corpus** — V1 capped at 50 pages and found 30; actual site scope is unknown
3. **PDFs excluded** — linked documents (forms, policy PDFs) are silently skipped
4. **Full-rewrite on every run** — no incremental update logic
5. **No error recovery** — a single network blip silently drops a page
6. **Hardcoded, non-reusable** — `BASE_URL`, `DOMAIN`, `css_selector` all baked in
7. **No requirements file** — not reproducible without tribal knowledge
8. **No schema validation** — malformed records can silently corrupt the data lake
9. **`read.py` is a stub** — data inspection tooling essentially doesn't exist

---

## ~~V2 — Production-Ready DAS Corpus Builder~~ ✓ Done

**Status: Done — 2026-03-17**
**Delivered:** 51 records (42 HTML + 9 PDF), avg 293 words, 0 internal failures

---

### ~~Pre-Step: Site Discovery~~ ✓ Done

*What was built:* `discovery/sitemap.py` — fetches `sitemap.xml`, validates by evenly-spaced HTTP sampling (>20% 404 → stale), falls back to async BFS. Filters out `/do-not-trash/`, `/search.html`, `/404/`. Outputs `emory_sitemap.json`.

*Key deviation:* `accessibility.emory.edu` had restructured its URL paths after the sitemap was generated (~80% of sitemap URLs were 404). Staleness validation was essential and BFS fallback ran in practice on every run.

---

### ~~V2 Goals~~ ✓ All Done

#### ~~2.1 — PDF Handling~~ ✓
*What was built:* `scrapers/pdf_extractor.py` — pdfplumber text extraction with pytesseract + pdf2image OCR fallback for scanned/image PDFs. PDFs discovered both from sitemap and from `<a href>` links on HTML pages.

#### ~~2.2 — Fix Broken Metadata~~ ✓
*What was built:* `html_scraper.py` uses BeautifulSoup on `result.html` for reliable title/description extraction. `crawl4ai 0.8` returns `result.markdown` as a `MarkdownGenerationResult` object; `.raw_markdown` required. Added `description` field (from `<meta name="description">`) to `Page` schema for RAG benchmarking.

#### ~~2.3 — Incremental Crawling~~ ✓ (partial)
*What was built:* Existing corpus loaded on startup; records not in current sitemap are pruned (orphan removal); records with unchanged `content_hash` are preserved. **Deviation:** atomic write (temp + `os.replace()`) was deferred to V3.

#### ~~2.4 — Retry Logic~~ ✓
*What was built:* Both `html_scraper.py` and `pdf_extractor.py` implement exponential backoff retry (2s → 4s → 8s, up to 3 attempts). Permanent failures logged to `runs/failed_urls.log`.

#### ~~2.5 — Schema Enforcement~~ ✓ (partial)
*What was built:* `Page` dataclass with typed fields including `description`. **Deviation:** per-record validation gate (reject empty markdown before write) deferred to V3.

#### ~~2.6 — Config File~~ ✓
*What was built:* `config/emory_das.json` with all site-specific values. Config loaded at startup via `core/config_loader.py`.

#### ~~2.7 — Output Format~~ ✓
*What was built:* `output/emory_das_data_YYYY-MM-DD.json` + `output/emory_das_data_latest.json`. `runs/run_log.jsonl` per-run audit log. `CorpusEnvelope` wrapper with `source`, `last_updated`, `total_pages`.

#### ~~2.8 — Tooling & DX~~ ✓
*What was built:* `requirements.txt` with system dep notes. `read.py` with summary table, duplicate detection, CSV export.

---

### V2 Success Criteria — Final Status

- [x] Site discovery produces complete `emory_sitemap.json`
- [x] All HTML pages have non-empty, correct titles
- [x] All PDF links downloaded and text extracted
- [x] Timestamps accurate and dynamic
- [x] Single network failure does not drop page (retry + log)
- [x] New developer can install and run with `pip install -r requirements.txt`
- [x] `read.py` outputs summary table
- [ ] Re-running on unchanged site produces zero record updates — *not verified; needs test run*

---

## V3 — Gap Closure

**Status: Planned**
**Goal:** Close the quality and robustness gaps identified during V2 delivery. No new features or site expansion.

### V3 Goals

#### 3.1 — Atomic Write
- **Problem:** `main.py` writes directly to the output file. A crash mid-write produces corrupt JSON.
- **Fix:** Write to a temp file (`output/.tmp_corpus.json`), then `os.replace(tmp, final)`. One-line change in `main.py`.

#### 3.2 — Per-Record Validation Gate
- **Problem:** Records with empty `markdown` (scraper returned content but text extraction yielded nothing) are logged but still written to the corpus.
- **Fix:** Before appending to the output list, reject records where `word_count < threshold` (use config `word_count_threshold`). Log rejected records to `runs/failed_urls.log` with reason.

#### 3.3 — PDF Metadata Extraction
- **Problem:** `description` is always `""` for PDFs. `pdfplumber` can read embedded PDF metadata (title, subject, author).
- **Fix:** In `pdf_extractor.py`, try `pdf.metadata` for title and subject before falling back to filename derivation.

#### 3.4 — `--validate` Flag in `read.py`
- **Problem:** No CLI quality gate. A downstream consumer has no automated way to verify the corpus meets minimum quality standards.
- **Fix:** Add `python read.py --validate` that exits non-zero if: any record has empty title, avg word count < 50, or >5% of records have `word_count < 10`. Usable in CI.

### V3 Success Criteria

- [ ] A crash during `main.py` write leaves the previous corpus intact
- [ ] Records with empty text are absent from the output corpus
- [ ] PDF records have non-empty `description` where PDF metadata is available
- [ ] `python read.py --validate` exits 0 on a healthy corpus and non-zero on a degraded one

---

## Downstream Handoff (RAG Pipeline Interface)

V2's output (`emory_das_data_latest.json`) will be consumed by the MedEase RAG ingestion pipeline. The schema is a contract — changes must be coordinated with the ingestion side.

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
