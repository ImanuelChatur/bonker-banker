"""Loan planner: "Can I afford this loan?" and, for a running loan, prepay vs build-a-buffer strategies.

Rates come from data/external/canadian_lending_rates_2026.csv (Bank of Canada, 2026). The default is the
"Personal loan plans (new lending)" rate, 7.92%.

Assumptions (stated in every explanation):
- A new loan pays for something (it doesn't sit in savings): its payment is added to monthly spending, the buffer
  is unchanged. Runway is the judges' formula with that higher spending.
- Dataset loans carry no interest (amount = months x payment). For the prepay strategies we apply the external rate
  to the REMAINING balance, so extra payments save real interest.
"""
from __future__ import annotations

import csv
from functools import lru_cache

import config

from .metrics import Metrics
from .runway import RUNWAY_CAP, runway
from .shocks import Shock, apply_shock

RATES_FILE = config.ROOT / "data" / "external" / "canadian_lending_rates_2026.csv"
DEFAULT_PRODUCT = "Personal loan plans (new lending)"
DEFAULT_SHOCK = Shock(income_factor=0.55)        # used when the caller doesn't pass one: job loss on EI
DATA_END_MONTH = "2025-12"


@lru_cache(maxsize=1)
def rates() -> list[dict]:
    """Rows of the rates CSV, for dropdowns and citations. rate_pct is a float."""
    with open(RATES_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["rate_pct"] = float(r["rate_pct"])
    return rows


def _default_rate() -> dict:
    return next(r for r in rates() if r["product"] == DEFAULT_PRODUCT)


def monthly_payment(amount: float, annual_rate_pct: float, months: int) -> float:
    """Standard amortization: P = A r / (1 - (1 + r)^-n), r = monthly rate. Zero rate -> straight line."""
    if months <= 0:
        raise ValueError("months must be positive")
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return round(amount / months, 2)
    return round(amount * r / (1 - (1 + r) ** -months), 2)


def _num(rw) -> float:
    return RUNWAY_CAP if isinstance(rw, str) else float(rw)


def affordability(m: Metrics, amount: float, months: int, rate_pct: float | None = None,
                  shock: Shock | None = None) -> dict:
    src = _default_rate()
    rate = src["rate_pct"] if rate_pct is None else float(rate_pct)
    source = (f"{src['source_name']} ({src['as_of']})" if rate_pct is None else "Rate entered by the user")
    pay = monthly_payment(amount, rate, months)

    before = runway(m.buffer, m.income, m.spending)
    with_loan = runway(m.buffer, m.income, m.spending + pay)
    sh = shock or DEFAULT_SHOCK
    a = apply_shock(m, sh)["after"]
    with_both = runway(m.buffer, a["income"], a["spending"] + pay, a["one_off_cost"])

    covers = m.income >= m.spending + pay
    if _num(with_loan) < 6:
        verdict = "risky"
    elif covers and _num(with_both) >= 6:
        verdict = "comfortable"
    else:
        verdict = "tight"
    shock_label = "a job loss on EI (55% of income)" if shock is None else "the selected shock"
    explanation = (
        f"Borrowing ${amount:,.0f} over {months} months at {rate:g}% costs ${pay:,.0f}/month. "
        + (f"Income still covers spending plus the payment (${m.income - m.spending - pay:,.0f}/month left). " if covers
           else f"With the payment, spending exceeds income by ${m.spending + pay - m.income:,.0f}/month. ")
        + f"Runway goes from {_fmt(before)} to {_fmt(with_loan)}; with {shock_label} as well it would be {_fmt(with_both)}. "
        "We assume the loan pays for something rather than sitting in savings, so the buffer doesn't grow.")
    return {"payment": pay, "rate_used": rate, "rate_source": source, "runway_before": before,
            "runway_with_loan": with_loan, "runway_with_loan_and_shock": with_both, "verdict": verdict,
            "explanation": explanation}


def _fmt(rw) -> str:
    return "no shortfall" if isinstance(rw, str) else f"{rw:g} months"


def _remaining_balance(loan: dict) -> tuple[float, int]:
    """Balance left at the dataset's end (no interest in the dataset) and payments still due."""
    start = str(loan["loan_start"])[:7]
    y0, m0 = map(int, start.split("-"))
    y1, m1 = map(int, DATA_END_MONTH.split("-"))
    paid = max(0, (y1 - y0) * 12 + (m1 - m0))
    left = max(0, int(loan["duration_months"]) - paid)
    return round(left * float(loan["monthly_payment"]), 2), left


def prepay_strategies(m: Metrics, shock: Shock | None, months: int = 24, target_buffer_months: float = 3) -> dict:
    from services import data_store

    loan = data_store.account_loan(m.account_id)
    if loan is None or m.loan_payment_active <= 0:
        return {"no_loan": True}
    balance0, _ = _remaining_balance(loan)
    if balance0 <= 0:
        return {"no_loan": True}

    rate = _default_rate()["rate_pct"]
    r = rate / 100 / 12
    pay = m.loan_payment_active                          # already inside S (it's in money_out)
    sh = apply_shock(m, shock or DEFAULT_SHOCK)["after"]
    target = target_buffer_months * m.spending

    def simulate(share_to_prepay) -> dict:
        buffer, balance, paid_off = m.buffer, balance0, None
        buffer = max(buffer, 0.0)
        buffers, runways = [round(buffer, 2)], []
        for t in range(months + 1):
            loan_cost = pay if balance > 0 else 0.0
            # runway if the shock hits now: shocked spending minus the payment once the loan is gone
            runways.append(_num(runway(buffer, sh["income"], sh["spending"] - (pay - loan_cost), sh["one_off_cost"])))
            if t == months:
                break
            interest = balance * r
            balance = max(0.0, balance + interest - min(pay, balance + interest))
            surplus = m.income - (m.spending - pay + loan_cost)
            to_loan = max(surplus, 0) * share_to_prepay(buffer) if balance > 0 else 0.0
            to_loan = min(to_loan, balance)
            balance -= to_loan
            buffer += surplus - to_loan
            if balance <= 0 and paid_off is None:
                paid_off = t + 1
            buffer = max(buffer, 0.0)               # savings can't go below zero; runway is already 0 there
            buffers.append(round(buffer, 2))
        return {"buffer_by_month": buffers, "runway_if_shock_hits_by_month": runways, "loan_paid_off_month": paid_off}

    strategies = [
        {"name": "Prepay", **simulate(lambda b: 1.0)},
        {"name": "Buffer first", **simulate(lambda b: 0.0 if b < target else 1.0)},
        {"name": "Hybrid", **simulate(lambda b: 0.5)},
    ]
    surplus = m.income - m.spending
    explanation = (
        f"Remaining balance ${balance0:,.0f}, payment ${pay:,.0f}/month. The dataset's loans carry no interest, so we "
        f"apply {rate:g}% (Bank of Canada, personal loan plans) to the remaining balance. "
        + (f"Each month the ${surplus:,.0f} surplus goes to extra loan payments (Prepay), to savings until the buffer "
           f"covers {target_buffer_months:g} months of spending (Buffer first), or half and half (Hybrid)."
           if surplus > 0 else
           "There is no monthly surplus, so all three strategies are the same: the first step is closing the gap."))
    return {"rate_used": rate, "remaining_balance": balance0, "explanation": explanation, "strategies": strategies}
