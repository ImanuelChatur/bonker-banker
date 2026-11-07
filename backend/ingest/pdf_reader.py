"""Pulls raw text out of a PDF. Text-based PDFs only; scanned ones need OCR.

Pages are joined with a PAGE_BREAK marker so a transaction never continues across a page.
Nothing is dropped here: merchants legitimately repeat across pages, so header/footer
boilerplate is handled by pattern in the parser instead.
"""
from pathlib import Path

import pdfplumber

PAGE_BREAK = "<<PAGE>>"


def read_pdf_text(path: str | Path) -> str:
    with pdfplumber.open(str(path)) as pdf:
        pages = [[ln.strip() for ln in (p.extract_text() or "").splitlines() if ln.strip()] for p in pdf.pages]
    return f"\n{PAGE_BREAK}\n".join("\n".join(pg) for pg in pages)
