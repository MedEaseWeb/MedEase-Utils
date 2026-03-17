# V2 Assessment — Emory DAS Corpus Builder
**Date:** 2026-03-17
**Branch:** feat/v2-implementation (merged → main, PR #2)

---

## Delivery Summary

| Metric | Value |
|--------|-------|
| Total records | 51 |
| HTML pages | 42 |
| PDF documents | 9 |
| Average word count | 293 |
| Failed internal URLs | 0 |
| Failed external PDF links | 1 (403 Forbidden — expected) |
| Scrape duration (est.) | ~4 min |

---

## Goal-by-Goal Status

| Goal | Plan | Outcome |
|------|------|---------|
| 2.1 PDF handling | pdfplumber + OCR fallback | ✅ Done — 9 PDFs extracted |
| 2.2 Fix broken metadata | BS4 title/description extraction | ✅ Done — titles accurate; `description` field added |
| 2.3 Incremental crawling | content_hash skip + orphan pruning | ✅ Done — atomic write deferred (V3) |
| 2.4 Retry logic | 3 attempts, exponential backoff | ✅ Done — both scrapers |
| 2.5 Schema enforcement | Page dataclass, typed fields | ✅ Done — per-record validation gate deferred (V3) |
| 2.6 Config file | emory_das.json | ✅ Done |
| 2.7 Output format | dated JSON + latest symlink + run log | ✅ Done |
| 2.8 Tooling & DX | requirements.txt + read.py | ✅ Done |

---

## Deviations from Plan

### 1. Sitemap was stale (~80% dead URLs)
`accessibility.emory.edu` restructured its URL paths after the last sitemap generation. Paths like `/students/*` became `/students-accommodations/*`. The sitemap XML existed and returned 200, but the majority of its entries 404'd.

**Resolution:** Added staleness validation to `sitemap.py` — evenly-spaced HTTP sampling (every N-th URL), >20% 404 triggers BFS fallback. This ran on every test run. The initial sampling approach (first 10 URLs) masked the problem because recently-modified staff pages at the top of the list were still valid; fixed by using `urls[::step]` for representative coverage.

### 2. `crawl4ai 0.8` API differences
- `result.markdown` is a `MarkdownGenerationResult` object, not a string → must use `.raw_markdown`
- `result.metadata.title` unreliable → BeautifulSoup parse of `result.html` required
- Playwright Chromium must be installed separately (`playwright install chromium`)

### 3. SSL error on macOS Python 3.13
`urllib.request.urlopen` in `sitemap.py` failed with `SSLCertVerificationError`. Switched to `requests` library (uses certifi) to resolve.

### 4. Staging pages leaking through BFS
`/do-not-trash/` pages (staging content) and `/search.html` were discovered by BFS. Added to `_EXCLUDE_PATTERNS` in `sitemap.py`.

### 5. Old stale records persisting
First run seeded `records = dict(existing)` preserving all V1-era stale URLs. Fixed by pruning records not in current `sitemap_urls` set (orphan removal) before merging new scrape results.

---

## Data Quality Assessment

**Overall: 7 / 10**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Coverage | 8/10 | 51 records; BFS confirmed completeness of crawlable content |
| Title accuracy | 9/10 | BS4 extraction reliable; a few PDFs derive title from filename |
| Description coverage | 6/10 | HTML: good; PDFs: always `""` — V3 will extract from PDF metadata |
| Content quality | 7/10 | crawl4ai markdown is clean for most pages; some nav/footer leakage |
| Freshness metadata | 9/10 | `scraped_at` and `last_scraped` accurate |
| Idempotency | 6/10 | Content hash skip logic implemented but not verified with a second run |

---

## Open Issues → V3

| Issue | Priority | V3 Goal |
|-------|----------|---------|
| No atomic write | High | 3.1 |
| Empty markdown records written to corpus | Medium | 3.2 |
| PDF `description` always `""` | Medium | 3.3 |
| No CLI quality gate | Low | 3.4 |
| Idempotency not verified | Medium | Run twice on same site, confirm zero updates |

---

## V3 Rationale

V2 delivered a functional, complete corpus. The open issues above are robustness and quality gaps rather than missing features. V3 is scoped purely as gap closure — no new scraping targets, no pipeline expansion. The goal is to raise corpus quality maturity from 7/10 to 9/10 before the RAG team begins indexing.

See `log/scraping-meta-plan.md` → V3 section for full goal definitions and success criteria.
