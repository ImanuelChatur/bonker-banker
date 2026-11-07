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


def apply_shock(m: Metrics, s: Shock) -> dict:
    income = m.income * s.income_factor
    spending = m.spending + s.household_bills_pct * m.household_bills + s.extra_monthly_spending
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
    if s.duration_months:
        left_after = m.buffer - one_off - max(gap, 0) * s.duration_months
        result["survives_duration"] = {
            "months": s.duration_months, "makes_it": left_after >= 0,
            "buffer_at_end": round(left_after, 2), "shortfall": round(max(-left_after, 0), 2)}
    return result
