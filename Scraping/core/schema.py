from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Page:
    url: str
    title: str
    description: str               # from <meta name="description"> or PDF metadata; "" if unavailable
    content_type: Literal["html", "pdf"]
    markdown: str                  # plain text for PDFs, markdown for HTML
    last_scraped: str              # ISO date  (YYYY-MM-DD)
    scraped_at: str                # ISO datetime
    word_count: int
    content_hash: str              # MD5 of markdown — used for change detection


@dataclass
class CorpusEnvelope:
    source: str
    last_updated: str              # ISO datetime of this run
    total_pages: int
    records: list = field(default_factory=list)
