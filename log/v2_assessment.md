# MedEase-Utils — V2 Assessment Log
**Date:** 2026-03-17
**Assessed by:** Claude (claude-sonnet-4-6)
**Purpose:** Post-implementation review of V2 against the original goals, documenting what was delivered, what deviated from plan, and what remains open.

---

## Delivery Summary

| Metric | Value |
|---|---|
| Total records | 51 |
| HTML pages | 42 |
| PDF documents | 9 |
| Average word count | 293 |
| Failed scrapes | 0 internal / 1 external (ABA PDF, HTTP 403 — expected) |
| Run time (first full run) | ~250s |
| Corpus file size | ~61KB |

---

## Project Structure (V2 Final)

```
Scraping/
├── config/emory_das.json         # Site config
├── core/schema.py                # Page + CorpusEnvelope dataclasses
├── core/config_loader.py
├── discovery/sitemap.py          # sitemap.xml → staleness validation → BFS fallback
├── scrapers/html_scraper.py      # crawl4ai + BeautifulSoup metadata extraction
├── scrapers/pdf_extractor.py     # pdfplumber + pytesseract OCR fallback
├── output/                       # emory_das_data_YYYY-MM-DD.json + _latest.json
├── runs/                         # run_log.jsonl, failed_urls.log
├── legacy/                       # V1 artifacts
├── main.py                       # Two-phase orchestrator
└── read.py                       # Corpus inspection CLI
```

---

## What V2 Achieved

| Goal | Status | Notes |
|---|---|---|
| Site discovery (sitemap + BFS fallback) | ✅ Done | Sitemap staleness validation was critical — live site had 86% dead URLs in sitemap |
| PDF inclusion + extraction | ✅ Done | pdfplumber primary, pytesseract OCR fallback for scanned docs |
| Accurate title extraction | ✅ Done | BeautifulSoup parse of raw HTML; `crawl4ai` metadata was unreliable |
| `description` field | ✅ Done (beyond spec) | `<meta name="description">` captured; added to support RAG benchmarking |
| Dynamic timestamps | ✅ Done | `last_scraped` (date) + `scraped_at` (datetime) per record |
| Incremental crawling | ✅ Done | Compares sitemap `lastmod` vs stored `last_scraped` |
| Orphan pruning | ✅ Done | Records no longer in sitemap are removed on each run |
| Retry logic | ✅ Done | 3 attempts, exponential backoff in both scrapers |
| `failed_urls.log` | ✅ Done | Permanent failures logged with timestamp and reason |
| Config-driven | ✅ Done | All site constants in `config/emory_das.json` |
| Versioned output | ✅ Done | Dated files + `_latest.json` stable pointer |
| `run_log.jsonl` | ✅ Done | Per-run stats: new, updated, unchanged, failed, duration |
| `read.py` inspection CLI | ✅ Done | Summary table, duplicate detection, CSV export |
| `requirements.txt` | ✅ Done | All deps declared including system dep notes |
| Atomic write | ❌ Not implemented | Direct file write used — see Known Gaps |
| Per-record validation | ❌ Not implemented | No explicit rejection of empty/low-quality records |
| PDF `description` | ❌ Not applicable | PDFs have no meta description equivalent; field always `""` |

---

## Deviations from Original Plan

### Added beyond spec
- **`description` field** — not in the original schema. Added during implementation after the user indicated intent to benchmark with a no-vector Claude RAG approach. Title + description together give a compact, human-readable summary of each record without embedding lookups.
- **`beautifulsoup4` dependency** — not in original requirements. Added when `crawl4ai 0.8`'s `result.metadata.title` proved unreliable.

### Implemented differently than planned
- **Incremental change detection** — planned as content-hash comparison; implemented as sitemap `lastmod` vs `last_scraped` comparison. This is faster (no need to re-fetch to compare hashes) and sufficient given the weekly cadence. Content hash is still stored per record for future use.
- **Sitemap discovery** — planned as "try sitemap, else BFS". Implemented with an explicit staleness validation step in between (evenly-spaced HTTP probe sample), since a stale sitemap is worse than no sitemap.
- **PDF discovery** — planned as links found during HTML scraping only. Implementation also types PDF entries in the sitemap directly as `"pdf"`, routing them through `pdf_extractor` rather than `html_scraper`.

### Not implemented
- **Atomic write** — temp file + rename pattern was planned but not executed. Risk is low at current scale (single-writer, ~61KB file) but worth addressing.
- **Per-record validation** — planned as explicit schema validation before write. Currently, `word_count_threshold=10` in the crawl config provides partial filtering but records with empty markdown can still slip through.

---

## Data Quality Assessment

| Dimension | Assessment |
|---|---|
| Title accuracy | ✅ High — BS4 extraction verified on multiple pages |
| Content completeness | ✅ High — BFS discovery confirmed all 51 live pages captured |
| Markdown quality | ✅ Good — `css_selector="main"` strips nav/footer noise |
| PDF text quality | ✅ Good for text PDFs; OCR adds noise for scanned docs |
| Description coverage | ⚠️ Partial — depends on whether site populates `<meta name="description">`; many pages may have `""` |
| Word count distribution | ⚠️ Uneven — some pages are legitimately sparse (index/landing pages ~40 words); not a data quality issue but worth noting for chunking strategy downstream |

**RAG readiness: 7 / 10**
The corpus is structurally sound and ready for ingestion. The main downstream concerns are (1) sparse index pages that may produce low-quality chunks, and (2) empty `description` fields on many records. Neither blocks ingestion but both affect retrieval precision.

---

## Issues Found

| Issue | Severity | Status |
|---|---|---|
| Atomic write not implemented | Low | Open — V3 |
| Per-record validation not implemented | Low | Open — V3 |
| PDF `description` always `""` | Low | Open — V3 (pdfplumber metadata extraction) |
| PDF title derived from filename slug only | Low | Open — V3 (pdfplumber metadata title) |
| Sparse index/landing pages (~40 words) included in corpus | Low | Acceptable — downstream chunker should handle |
| External PDFs behind auth/bot-protection (403) blocked | Info | Expected, not fixable without credentials |

---

## Overall Assessment

**Maturity: 7 / 10**
V2 delivered a fully functional, reproducible, incremental corpus scraper. The core pipeline (discovery → scrape → extract → output) works end-to-end with real data. Remaining gaps are all low-risk mechanical fixes, not design problems. The corpus is ready for downstream RAG ingestion and benchmarking.

### Prioritized Next Steps (V3)

1. **Per-record validation** — reject and log records with empty markdown before write
2. **Atomic write** — write to temp file, rename on success
3. **PDF metadata extraction** — use `pdfplumber` document metadata for title and description where available
4. **End-to-end corpus validation script** — `read.py` extension that flags records with 0 words, missing titles, or empty descriptions as a quality gate before handoff
