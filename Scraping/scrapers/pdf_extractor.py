"""
PDF extractor: download → pdfplumber → OCR fallback (pytesseract + pdf2image).

Requires system dependencies:
  - poppler  (for pdf2image)
  - tesseract (for pytesseract)
"""
import hashlib
import io
import time
from datetime import date, datetime

import pdfplumber
import pytesseract
import requests
from pdf2image import convert_from_bytes

from core.schema import Page


def extract_pdf(url: str, max_retries: int = 3) -> Page | None:
    """
    Download and extract text from a PDF URL.
    Tries pdfplumber first; falls back to OCR for scanned/image PDFs.
    Returns Page or None after exhausting retries.
    """
    pdf_bytes = _download(url, max_retries)
    if pdf_bytes is None:
        return None

    text = _extract_with_pdfplumber(pdf_bytes)

    if not text.strip():
        print(f"[pdf] No text layer — falling back to OCR for {url}")
        text = _extract_with_ocr(pdf_bytes)

    if not text.strip():
        print(f"[pdf] Could not extract any text from {url}")
        return None

    slug = url.rstrip("/").split("/")[-1]
    title = slug.replace(".pdf", "").replace("-", " ").replace("_", " ").title()

    return Page(
        url=url,
        title=title,
        description="",
        content_type="pdf",
        markdown=text,
        last_scraped=date.today().isoformat(),
        scraped_at=datetime.now().isoformat(timespec="seconds"),
        word_count=len(text.split()),
        content_hash=hashlib.md5(text.encode()).hexdigest(),
    )


def _download(url: str, max_retries: int) -> bytes | None:
    delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            print(f"[pdf] Download attempt {attempt}/{max_retries} failed — {url}: {exc}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
    return None


def _extract_with_pdfplumber(pdf_bytes: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
    return "\n\n".join(parts)


def _extract_with_ocr(pdf_bytes: bytes) -> str:
    images = convert_from_bytes(pdf_bytes)
    parts = []
    for img in images:
        page_text = pytesseract.image_to_string(img)
        if page_text.strip():
            parts.append(page_text)
    return "\n\n".join(parts)
