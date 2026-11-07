import copy
from pathlib import Path

from . import llm_fallback
from .ledger import reconcile
from .models import Statement, Transaction
from .parsers import pick_parser
from .pdf_reader import read_pdf_text


def _warnings(st: Statement) -> list[str]:
    c = copy.deepcopy(st)
    c.warnings = []
    reconcile(c)
    return c.warnings


def parse_pdf(path: str | Path, use_llm: bool = True) -> Statement:
    text = read_pdf_text(path)
    st = pick_parser(text).parse(text, source=str(path))
    if not text.strip():
        st.warnings.append("No extractable text (scanned PDF?). OCR is required.")
        return st

    bad = 10**6 if not st.transactions else len(_warnings(st))
    if bad and use_llm and llm_fallback.available():
        try:
            alt = llm_fallback.parse_with_gemini(text, str(path), base=st)
            alt_bad = 10**6 if not alt.transactions else len(_warnings(alt))
            if alt_bad < bad:
                alt.warnings.append("Parsed with Gemini fallback; please review.")
                return alt
        except Exception as e:  # network / quota / bad JSON: keep the rule-based result
            st.warnings.append(f"Gemini fallback failed: {type(e).__name__}")
    return st


__all__ = ["Statement", "Transaction", "parse_pdf"]
