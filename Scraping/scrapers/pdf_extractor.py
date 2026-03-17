"""
PDF extractor using pdfplumber.
Downloads a PDF from a URL and extracts plain text.
Returns a Page record or None on permanent failure.
"""
import hashlib
from datetime import date, datetime

import pdfplumber

from core.schema import Page


# TODO: implement download + extraction with retry logic
def extract_pdf(
    url: str,
    max_retries: int = 3,
) -> Page | None:
    """Download and extract text from a PDF URL. Returns Page or None after exhausting retries."""
    raise NotImplementedError
