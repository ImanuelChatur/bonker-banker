"""Bank-statement PDF -> Statement (transactions + balances).

Text-based PDFs only (scanned images would need OCR). The parser is
layout-tolerant: it works line by line, so it copes with the common
"date  description  amount  [balance]" layouts without per-bank templates.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from ..models import Statement, Transaction

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"

# Leading date formats, tried in order (most specific first).
DATE_PATTERNS = [
    (re.compile(r"^(\d{4})-(\d{2})-(\d{2})\b"), "ymd"),
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})\b"), "mdy"),
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})\b"), "mdy2"),
    (re.compile(rf"^({MON})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.I), "mon_d_y"),
    (re.compile(rf"^(\d{{1,2}})\s+({MON})\s+(\d{{4}})\b", re.I), "d_mon_y"),
    (re.compile(r"^(\d{1,2})/(\d{1,2})\b"), "md"),
    (re.compile(rf"^({MON})\s+(\d{{1,2}})\b", re.I), "mon_d"),
    (re.compile(rf"^(\d{{1,2}})\s+({MON})\b", re.I), "d_mon"),
]

AMOUNT_RE = re.compile(r"^\(?[-+]?\$?\d{1,3}(?:,\d{3})*\.\d{2}\)?-?$|^\(?[-+]?\$?\d+\.\d{2}\)?-?$")
SUFFIX_RE = re.compile(r"^(CR|DR)$", re.I)

OPENING_RE = re.compile(
    r"(?:beginning|opening|previous|starting)\s+balance|balance\s+(?:brought\s+)?forward", re.I)
CLOSING_RE = re.compile(r"(?:ending|closing|new)\s+balance|balance\s+carried", re.I)
SKIP_RE = re.compile(r"^(?:date\b|page\s+\d|total\b|subtotal\b|continued)", re.I)

PAGE_BREAK = "<<PAGE>>"      # inserted by pdf_reader between pages

# Boilerplate that shows up in page headers/footers (and sometimes bleeds into a row).
NOISE_RE = re.compile(
    r"your account number|questions\?|call\s+1[\s-]*8\d\d|for online account access|"
    r"www\.|https?://|page\s+\d+\s*(?:of\s*\d+)?|preferred package|account summary|"
    r"statement period|^-{3,}|^[|\s-]+$|continued on next page|\(continued\)|"
    r"what happened in your account|^date\s+transactions|^amounts?\b|total (?:withdrawals|deposits)|"
    r"^(?:MR|MS|MRS|MX)\s+[A-Z]+(?:\s+[A-Z]+){0,2}$",     # all-caps salutation line, e.g. "MR DERIN"
    re.I)
# Everything from the first boilerplate marker to the end of the description is dropped,
# together with a preceding "MR/MS NAME" salutation.
CUT_RE = re.compile(
    r"\s*(?:\b(?:MR|MS|MRS|MX|DR)\b\s+[A-Z][A-Z .'-]+\s+)?"
    r"(?:your account number|questions\?|for online account access|your preferred|www\.|https?://).*$",
    re.I)
MAX_CONTINUATION_LINES = 2
MAX_CONTINUATION_LEN = 60


def clean_desc(desc: str) -> str:
    d = CUT_RE.sub("", desc)
    d = re.sub(r"(?:^|\s)[|\-_=]{2,}(?=\s|$)|\s\|(?=\s|$)", " ", d)   # table borders / separators
    d = re.sub(r"(?<!\d)\+?\d{8,}", "", d)        # phone / reference numbers, even when glued to a word
    d = re.sub(r"\s+", " ", d).strip(" |-")
    return d or desc.strip()


CREDIT_WORDS = re.compile(
    r"\b(deposit|payroll|salary|refund|interest\s+(?:paid|earned|credit)|credit|reversal|"
    r"cashback|transfer\s+from|zelle\s+from|direct\s+dep)", re.I)


# ---------------------------------------------------------------- helpers
def _dec(tok: str) -> tuple[Decimal, bool | None]:
    """Parse '1,234.56', '(12.00)', '12.00-', '-12.00' -> (abs value, is_negative or None)."""
    t = tok.strip()
    neg = None
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    if t.endswith("-"):
        neg, t = True, t[:-1]
    if t.startswith("-"):
        neg, t = True, t[1:]
    elif t.startswith("+"):
        neg, t = False, t[1:]
    t = t.replace("$", "").replace(",", "")
    try:
        return Decimal(t), neg
    except InvalidOperation:
        raise ValueError(tok)


def _month(s: str) -> int:
    return MONTHS[s[:3].lower()]


def _resolve_year(m: int, d: int, ps: date | None, pe: date | None) -> int:
    """Pick the year that places (m, d) inside the statement period."""
    if ps and pe:
        for y in sorted({ps.year, pe.year}):
            try:
                if ps <= date(y, m, d) <= pe:
                    return y
            except ValueError:
                pass
        return pe.year if m <= pe.month else ps.year
    ref = pe or ps
    return ref.year if ref else date.today().year


def parse_leading_date(line: str, ps: date | None, pe: date | None):
    """Return (date, rest_of_line) if the line starts with a date, else None."""
    for rx, kind in DATE_PATTERNS:
        mt = rx.match(line)
        if not mt:
            continue
        g = mt.groups()
        try:
            if kind == "ymd":
                d = date(int(g[0]), int(g[1]), int(g[2]))
            elif kind == "mdy":
                d = date(int(g[2]), int(g[0]), int(g[1]))
            elif kind == "mdy2":
                d = date(2000 + int(g[2]), int(g[0]), int(g[1]))
            elif kind == "mon_d_y":
                d = date(int(g[2]), _month(g[0]), int(g[1]))
            elif kind == "d_mon_y":
                d = date(int(g[2]), _month(g[1]), int(g[0]))
            else:
                if kind == "md":
                    m, dd = int(g[0]), int(g[1])
                elif kind == "mon_d":
                    m, dd = _month(g[0]), int(g[1])
                else:
                    m, dd = _month(g[1]), int(g[0])
                d = date(_resolve_year(m, dd, ps, pe), m, dd)
        except ValueError:
            continue
        return d, line[mt.end():].strip()
    return None


def _find_period(text: str) -> tuple[date | None, date | None]:
    one = (r"(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|" + MON + r"\s+\d{1,2},?\s+\d{4}"
           r"|\d{1,2}\s+" + MON + r"\s+\d{4})")
    sep = r"\s*(?:-|–|to|through|thru)\s*"
    mt = re.search(one + sep + one, text, re.I)
    if mt:
        a = parse_leading_date(mt.group(1), None, None)
        b = parse_leading_date(mt.group(2), None, None)
        return (a[0] if a else None), (b[0] if b else None)

    # "September 10 to October 9, 2026": the first date has no year, borrow the second one's.
    mt = re.search(rf"\b({MON}\s+\d{{1,2}}){sep}({MON}\s+\d{{1,2}},?\s+\d{{4}})", text, re.I)
    if mt:
        end = parse_leading_date(mt.group(2), None, None)
        if end:
            start = parse_leading_date(f"{mt.group(1)}, {end[0].year}", None, None)
            if start and start[0] > end[0]:                      # e.g. "Dec 10 to Jan 9, 2026"
                start = parse_leading_date(f"{mt.group(1)}, {end[0].year - 1}", None, None)
            if start:
                return start[0], end[0]

    # "Opening Balance on <date>" ... "Closing Balance on <date>"
    a = re.search(r"opening balance on\s+" + one, text, re.I)
    b = re.search(r"closing balance on\s+" + one, text, re.I)
    pa = parse_leading_date(a.group(1), None, None) if a else None
    pb = parse_leading_date(b.group(1), None, None) if b else None
    return (pa[0] if pa else None), (pb[0] if pb else None)


def _find_account(text: str) -> str:
    mt = re.search(r"account\s*(?:number|no\.?|#)?\s*[:#]?\s*[*xX•\-\s]*(\d[\d\s-]{2,})", text, re.I)
    if mt:
        digits = re.sub(r"\D", "", mt.group(1))
        if len(digits) >= 4:
            return digits[-4:]
    return "unknown"


def _amounts_from_tail(tokens: list[str]):
    """Peel numeric tokens (and CR/DR markers) off the end of a line."""
    amts: list[tuple[Decimal, bool | None]] = []
    i = len(tokens)
    while i > 0 and len(amts) < 3:
        tok = tokens[i - 1]
        suffix = None
        if SUFFIX_RE.match(tok) and i > 1 and AMOUNT_RE.match(tokens[i - 2]):
            suffix, i = tok.upper(), i - 1
            tok = tokens[i - 1]
        elif re.match(r"^.*\d(CR|DR)$", tok, re.I) and AMOUNT_RE.match(tok[:-2]):
            suffix, tok = tok[-2:].upper(), tok[:-2]
        if not AMOUNT_RE.match(tok):
            break
        val, neg = _dec(tok)
        if suffix == "DR":
            neg = True
        elif suffix == "CR" and neg is None:
            neg = False
        amts.append((val, neg))
        i -= 1
    amts.reverse()
    return amts, tokens[:i]


# ---------------------------------------------------------------- parsing
def parse_text(text: str, source: str = "<text>") -> Statement:
    st = Statement(source=source)
    st.period_start, st.period_end = _find_period(text)
    st.account = _find_account(text)

    prev_bal = None
    last: Transaction | None = None
    pending: tuple[date, str] | None = None
    cont_lines = 0

    for raw in (ln.strip() for ln in text.splitlines()):
        if not raw:
            continue
        if raw == PAGE_BREAK:                       # a row never continues across pages
            last = pending = None
            cont_lines = 0
            continue
        toks_all = raw.split()

        # Opening / closing balance lines (may or may not start with a date)
        is_open, is_close = OPENING_RE.search(raw), CLOSING_RE.search(raw)
        if is_open or is_close:
            amts, _ = _amounts_from_tail(toks_all)
            if amts:
                val, neg = amts[-1]
                val = -val if neg else val
                if is_open and st.opening_balance is None:
                    st.opening_balance = val
                    prev_bal = val
                elif is_close:
                    st.closing_balance = val
            last = None
            continue

        parsed = parse_leading_date(raw, st.period_start, st.period_end)
        # A dated line with no amounts starts a row whose amounts arrive on a later line.
        if pending and not parsed and (SKIP_RE.match(raw) or NOISE_RE.search(raw)):
            pending = None                           # boilerplate ends a half-built row
        elif pending and not parsed:
            if _amounts_from_tail(toks_all)[0]:
                parsed = (pending[0], pending[1] + " " + raw)
                pending = None
            else:
                pending = (pending[0], pending[1] + " " + raw)
                continue
        elif parsed:
            pending = None
        if not parsed or SKIP_RE.match(raw):
            # continuation of the previous description (wrapped line, no amounts)
            if last and (SKIP_RE.match(raw) or NOISE_RE.search(raw)):
                last = None                          # boilerplate (sidebar, footer) closes the row
            elif (last and cont_lines < MAX_CONTINUATION_LINES and len(raw) <= MAX_CONTINUATION_LEN
                    and not _amounts_from_tail(toks_all)[0]):
                last.description = clean_desc(last.description + " " + raw)
                last.raw += " | " + raw
                cont_lines += 1
            continue

        d, rest = parsed
        # Some layouts have a second (posting) date right after the first.
        second = parse_leading_date(rest, st.period_start, st.period_end)
        if second and second[0].year == d.year:
            rest = second[1]

        amts, desc_toks = _amounts_from_tail(rest.split())
        if not amts and desc_toks:
            pending = (d, rest)
            continue
        if not amts or not desc_toks:
            continue

        # Last number is the running balance when two or more numbers are present.
        if len(amts) >= 2:
            (amt, neg), (bal_abs, bal_neg) = amts[-2], amts[-1]
            bal = -bal_abs if bal_neg else bal_abs
        else:
            (amt, neg), bal = amts[0], None
        desc = clean_desc(" ".join(desc_toks))
        cont_lines = 0

        inferred = False
        if bal is not None and prev_bal is not None and abs(bal - prev_bal) == amt and amt != 0:
            signed = bal - prev_bal                       # most reliable: balance delta
        elif neg is not None:
            signed = -amt if neg else amt
        else:
            signed = amt if CREDIT_WORDS.search(desc) else -amt
            inferred = True

        t = Transaction(date=d, description=desc, amount=signed, balance=bal,
                        sign_inferred=inferred, raw=raw, seq=len(st.transactions))
        st.transactions.append(t)
        last = t
        if bal is not None:
            prev_bal = bal
        elif prev_bal is not None:
            prev_bal += signed

    if st.opening_balance is None and st.transactions:
        f = st.transactions[0]
        if f.balance is not None:
            st.opening_balance = f.balance - f.amount
    if st.transactions:                              # last resort: span of the transactions themselves
        dates = [t.date for t in st.transactions]
        st.period_start = st.period_start or min(dates)
        st.period_end = st.period_end or max(dates)
    else:
        st.warnings.append("No transactions recognised.")
    return st


class StatementParser:
    """Interface every bank parser follows: detect() then parse().

    Subclasses override detect() and, where the bank layout needs it, parse().
    The default parse() is the layout-tolerant line parser above.
    """
    name = "generic"

    @classmethod
    def detect(cls, text: str) -> bool:
        return True            # generic parser accepts anything (fallback)

    def parse(self, text: str, source: str = "<text>") -> Statement:
        st = parse_text(text, source)
        st.bank = self.name
        return st
