"""Gemini fallback for statement layouts the rule-based parsers can't reconcile.

Only used when the normal parse finds nothing or fails the balance check, and the
result is accepted only if it reconciles better than the rule-based one.
Long digit runs (account/card numbers) are masked before the text leaves the machine.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from services import llm

from .models import Statement, Transaction

PROMPT = (
    "Extract every transaction from this bank statement text. Return JSON only.\n"
    "- date: ISO YYYY-MM-DD (infer the year from the statement period).\n"
    "- amount: signed number, negative = money out, positive = money in.\n"
    "- balance: running balance after the transaction if printed, else null.\n"
    "- opening_balance / closing_balance if printed, else null.\n"
    "Do not invent rows. Skip headers, totals and summaries.\n\nSTATEMENT TEXT:\n"
)

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "opening_balance": {"type": "NUMBER", "nullable": True},
        "closing_balance": {"type": "NUMBER", "nullable": True},
        "period_start": {"type": "STRING", "nullable": True},
        "period_end": {"type": "STRING", "nullable": True},
        "transactions": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "date": {"type": "STRING"}, "description": {"type": "STRING"},
            "amount": {"type": "NUMBER"}, "balance": {"type": "NUMBER", "nullable": True}},
            "required": ["date", "description", "amount"]}},
    },
    "required": ["transactions"],
}


def available() -> bool:
    return llm.available()


def mask_numbers(text: str) -> str:
    return re.sub(r"\b\d{6,}\b", lambda m: "*" * (len(m.group()) - 4) + m.group()[-4:], text)


def _d(v) -> Decimal | None:
    return None if v is None else Decimal(str(v)).quantize(Decimal("0.01"))


def _date(s) -> date | None:
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def parse_with_gemini(text: str, source: str, base: Statement | None = None) -> Statement:
    data = llm.generate_json(PROMPT + mask_numbers(text), SCHEMA)
    st = Statement(source=source, bank="gemini")
    if base:
        st.account = base.account
    st.opening_balance, st.closing_balance = _d(data.get("opening_balance")), _d(data.get("closing_balance"))
    st.period_start, st.period_end = _date(data.get("period_start")), _date(data.get("period_end"))
    for i, t in enumerate(data.get("transactions", [])):
        d = _date(t.get("date"))
        if d is None:
            continue
        st.transactions.append(Transaction(date=d, description=str(t["description"]).strip(),
                                           amount=_d(t["amount"]), balance=_d(t.get("balance")),
                                           raw="gemini", seq=i))
    return st
