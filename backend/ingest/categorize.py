"""Labels transactions using the same vocabulary as the Tangerine dataset's monthly_summary.csv.

money_in parts : cash_deposits, transfers_in, pension_in, interest_in
money_out parts: household_bills, insurance, loan_payments, bank_fees,
                 cash_withdrawals_genuine, card_withdrawals, transfers_out_other
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from .models import Transaction

IN_CATEGORIES = ["cash_deposits", "transfers_in", "pension_in", "interest_in"]
OUT_CATEGORIES = ["household_bills", "insurance", "loan_payments", "bank_fees",
                  "cash_withdrawals_genuine", "card_withdrawals", "transfers_out_other"]

# (category, regex, direction) - direction: "in", "out" or None (either). First match wins.
RULES: list[tuple[str, str, str | None]] = [
    ("loan_payments", r"\bloan\b|mortgage|line of credit|\bloc\b|student aid|auto finance|leasing", "out"),
    ("insurance", r"insur|intact|manulife|sun ?life|state farm|allstate", "out"),
    ("household_bills", r"hydro|electric|enbridge|gas bill|water|rogers|\bbell\b|telus|fido|koodo|"
                        r"shaw|videotron|internet|utility|property tax|\brent\b|bill payment", "out"),
    ("pension_in", r"pension|\bcpp\b|\boas\b|old age|retirement", "in"),
    ("interest_in", r"interest (?:paid|earned|credit)|credit interest|interest$", "in"),
    ("bank_fees", r"\bfee\b|service charge|penalty interest|overdraft|\bnsf\b|interest charge", "out"),
    ("cash_deposits", r"cash deposit|atm deposit|branch deposit|deposit cash", "in"),
    ("cash_withdrawals_genuine", r"\batm\b|cash withdrawal|withdrawal cash|\babm\b", "out"),
    # Transfers: wires, credit memos, e-transfers, payroll deposits and similar.
    ("transfers", r"wire|credit memo|transfer|interac|e-?transfer|zelle|payroll|salary|direct dep|"
                  r"\bdeposit\b|\bwithdrawal\b|\bpayment from\b|\bpayment to\b", None),
    ("card_withdrawals", r"point of sale|\bpos\b|\bopos\b|\bapos\b|purchase|visa|mastercard|debit card", "out"),
]
_COMPILED = [(c, re.compile(p, re.I), d) for c, p, d in RULES]


def categorize(desc: str, amount=None) -> str:
    """amount is signed (negative = out); used to pick transfers_in vs transfers_out_other."""
    is_in = amount is not None and amount > 0
    is_out = amount is not None and amount < 0
    for cat, rx, direction in _COMPILED:
        if direction == "in" and is_out or direction == "out" and is_in:
            continue
        if rx.search(desc):
            if cat == "transfers":
                return "transfers_in" if is_in else "transfers_out_other"
            return cat
    return "uncategorized"


MIN_LEARNED_CONFIDENCE = 0.6


@lru_cache(maxsize=1)
def _priors() -> dict:
    p = Path(__file__).with_name("learned_priors.json")     # built by: python -m ingest.learn
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def learned_category(amount, recurrence: int = 0, day: int = 1) -> tuple[str | None, float]:
    """Structural guess (direction, amount size, recurrence, day) learned from the Tangerine dataset."""
    from .learn import features              # local import: learn.py is only needed for the helpers
    key = "|".join(map(str, features("in" if amount > 0 else "out", abs(float(amount)), recurrence, day)))
    hit = _priors().get(key)
    if hit and hit["confidence"] >= MIN_LEARNED_CONFIDENCE:
        return hit["category"], hit["confidence"]
    return None, 0.0


def categorize_all(txns: list[Transaction], recurrence=None) -> None:
    """Keyword rules first; learned priors only for what's left. recurrence(t) -> months seen elsewhere."""
    for t in txns:
        t.category, t.category_source = categorize(t.description, t.amount), "rule"
        if t.category == "uncategorized":
            cat, _ = learned_category(t.amount, recurrence(t) if recurrence else 0, t.date.day)
            if cat:
                t.category, t.category_source = cat, "learned"
