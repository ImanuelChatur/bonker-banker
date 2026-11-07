"""Pulls raw text out of a PDF. Text-based PDFs only; scanned ones need OCR."""
import re
from collections import Counter
from pathlib import Path

import pdfplumber

PAGE_BREAK = "<<PAGE>>"
_DATED = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}|\d{1,2}\s+[A-Za-z]{3}|[A-Za-z]{3}\s+\d{1,2})\b")


def read_pdf_text(path: str | Path) -> str:
    with pdfplumber.open(str(path)) as pdf:
        pages = [[ln.strip() for ln in (p.extract_text() or "").splitlines()] for p in pdf.pages]

    # Lines repeated on 2+ pages (running headers/footers) are not transactions.
    if len(pages) > 1:
        counts = Counter(ln for pg in pages for ln in set(pg) if ln)
        repeated = {ln for ln, n in counts.items() if n >= 2 and not _DATED.match(ln)}
        pages = [[ln for ln in pg if ln not in repeated] for pg in pages]

    return f"\n{PAGE_BREAK}\n".join("\n".join(pg) for pg in pages)
