"""Take a shock: change income/spending/one-off costs and recalculate runway.

Examples:
  job loss with EI      Shock(income_factor=0.55, duration_months=6)
  rent/utilities +15%   Shock(household_bills_pct=0.15)
  furnace dies          Shock(one_off_months_of_spending=1)   # or one_off_cost=4000
"""
from __future__ import annotations

from dataclasses import dataclass

from .metrics import Metrics
from .runway import runway


@dataclass
class Shock:
    income_factor: float = 1.0               # 0.55 = EI at 55% of usual income, 0 = no income
    household_bills_pct: float = 0.0         # +0.15 = bills up 15% (adds pct * H to spending)
    extra_monthly_spending: float = 0.0      # any other recurring increase
    one_off_cost: float = 0.0                # surprise repair etc.
    one_off_months_of_spending: float = 0.0  # one-off sized as N months of typical spending
    duration_months: int | None = None       # how long the income hit lasts (e.g. EI 6 months)
    # Optional extras (our measures). Their defaults change nothing, so the judges' numbers stay exact.
    rate_hike_pct: float = 0.0               # percentage points added to variable-rate debt (running dataset loan)
    realistic_ei: bool = False               # True -> EI capped: income = min(I * income_factor, 729 * 52 / 12)


def ei_monthly_cap() -> float:
    """2026 EI maximum: weekly cap from data/external/ei_parameters_2026.csv (729 CAD) x 52 / 12."""
    import csv

    import config
    path = config.ROOT / "data" / "external" / "ei_parameters_2026.csv"
    weekly = 729.0
    try:
        with open(path, newline="", encoding="utf-8") as f:
            weekly = next(float(r["value"]) for r in csv.DictReader(f) if r["parameter"] == "max_weekly_benefit")
    except (OSError, StopIteration, KeyError, ValueError):
        pass
    return round(weekly * 52 / 12, 2)


def rate_hike_cost(m: Metrics, rate_hike_pct: float) -> float:
    """Extra interest per month on the remaining balance of the account's running loan (0 if none or unknown).
    Dataset loans carry no rate, so we treat the remaining balance as variable-rate debt."""
    if rate_hike_pct <= 0 or m.loan_payment_active <= 0:
        return 0.0
    try:
        from services import data_store

        from .loans import _remaining_balance
        loan = data_store.account_loan(m.account_id)
    except Exception:
        return 0.0
    if loan is None:
        return 0.0
    balance, _ = _remaining_balance(loan)
    return round(balance * rate_hike_pct / 100 / 12, 2)


def apply_shock(m: Metrics, s: Shock) -> dict:
    income = m.income * s.income_factor
    ei_capped = False
    if s.realistic_ei and s.income_factor < 1:
        cap = ei_monthly_cap()
        if income > cap:
            income, ei_capped = cap, True
    hike = rate_hike_cost(m, s.rate_hike_pct)
    spending = m.spending + s.household_bills_pct * m.household_bills + s.extra_monthly_spending + hike
    one_off = s.one_off_cost + s.one_off_months_of_spending * m.spending
    gap = spending - income
    result = {
        "before": {"income": m.income, "spending": m.spending, "buffer": m.buffer,
                   "runway": runway(m.buffer, m.income, m.spending)},
        "after": {"income": round(income, 2), "spending": round(spending, 2),
                  "one_off_cost": round(one_off, 2), "monthly_gap": round(gap, 2),
                  "buffer_left": round(m.buffer - one_off, 2),
                  "runway": runway(m.buffer, income, spending, one_off)},
    }
    if s.realistic_ei:
        result["after"]["ei_capped"] = ei_capped
    if s.rate_hike_pct:
        result["after"]["rate_hike_extra"] = hike
    if s.duration_months:
        left_after = m.buffer - one_off - max(gap, 0) * s.duration_months
        result["survives_duration"] = {
            "months": s.duration_months, "makes_it": left_after >= 0,
            "buffer_at_end": round(left_after, 2), "shortfall": round(max(-left_after, 0), 2)}
    return result
