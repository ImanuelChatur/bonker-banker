"""Stand-ins for ClaudeOne's engine functions, in the exact interface-contract shapes.

`engine_fn(module, name)` returns the real engine function when it exists, otherwise the placeholder below.
Placeholder results carry "_placeholder": True (dicts) so pages can show a "sample data" badge.
Delete each placeholder once the real function lands.
"""
from __future__ import annotations

import hashlib
import importlib


def engine_fn(module: str, name: str):
    """engine.<module>.<name> if ClaudeOne has shipped it, else the placeholder of the same name."""
    try:
        return getattr(importlib.import_module(f"engine.{module}"), name)
    except (ImportError, AttributeError):
        return globals()[name]


def is_placeholder(module: str, name: str) -> bool:
    return engine_fn(module, name) is globals().get(name)


def _seed(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _pct(*parts) -> int:
    return _seed(*parts) % 101


# ---------------------------------------------------------------- engine/profile.py
def customer_profile(account_id) -> dict:
    s = _seed(account_id)
    return {"_placeholder": True,
            "age": 25 + s % 50, "age_band": ["25-34", "35-44", "45-54", "55-64", "65+"][s % 5],
            "tenure_years": 1 + s % 6, "household_size": 1 + s % 3,
            "district_name": "Sample district", "region": "Sample region",
            "district_unemployment_2023": 4.2, "unemployment_trend": ["rising", "falling", "flat"][s % 3],
            "district_avg_salary": 9800, "card_type": [None, "classic", "gold"][s % 3],
            "standing_orders_monthly": 410.0, "leasing_monthly": 0.0, "true_fixed_costs": 2740.0,
            "income_volatility": round(0.1 + (s % 60) / 100, 2), "avg_days_below_zero": s % 4,
            "penalty_fees_12m": s % 3, "income_band": ["under 3k", "3k-6k", "6k-10k", "10k+"][s % 4]}


# ---------------------------------------------------------------- engine/benchmarks.py
def peer_benchmarks(account_id) -> dict:
    metric = lambda k, v: {"value": v, "percentile": _pct(account_id, k), "peer_median": round(v * 1.1, 2)}
    return {"_placeholder": True,
            "group": {"income_band": "3k-6k", "age_band": "35-44", "district_name": "Sample district"},
            "peer_count": 120,
            "metrics": {"buffer": metric("buffer", 12000), "runway": metric("runway", 7.5),
                        "fixed_cost_share": metric("fixed", 0.31), "income_volatility": metric("vol", 0.22)}}


# ---------------------------------------------------------------- engine/insights.py
def stress_grid() -> list[dict]:
    rows = []
    for one_off in (0, 1, 2):
        for ei in range(0, 101, 10):
            for bills in range(0, 31, 5):
                base = max(0.0, (100 - ei) * 0.55 + bills * 0.3 + one_off * 9)
                rows.append({"ei_pct": ei, "bills_pct": bills, "one_off_months": one_off,
                             "pct_runout_3m": round(min(base * 0.6, 100), 1),
                             "pct_runout_6m": round(min(base, 100), 1), "n": 4500, "_placeholder": True})
    return rows


def stress_breakdown(ei_pct=55, bills_pct=15, one_off_months=0) -> list[dict]:
    groups = {"age_band": ["25-34", "35-44", "45-54", "55-64", "65+"], "household_size": ["1", "2", "3+"],
              "region": ["Region A", "Region B", "Region C"], "income_band": ["under 3k", "3k-6k", "6k-10k", "10k+"]}
    return [{"group_type": t, "group": g, "pct_runout_6m": float(_pct(t, g, ei_pct, bills_pct) % 60),
             "n": 100 + _seed(g) % 900, "_placeholder": True} for t, gs in groups.items() for g in gs]


def headline() -> dict:
    return {"_placeholder": True, "text": "Sample: a job loss on EI would leave about 1 in 3 accounts out of savings within 6 months.",
            "pct_runout_3m": 20.0, "pct_runout_6m": 35.0, "scenario": "EI 55%, 6 months"}


def at_risk_customers(limit=50) -> list[dict]:
    return [{"account_id": str(20000 + i * 37), "runway": round(0.5 + i * 0.1, 1), "runway_ei55": round(0.2 + i * 0.05, 1),
             "district_name": "Sample district", "reasons": ["Sample reason"], "_placeholder": True}
            for i in range(limit)]


# ---------------------------------------------------------------- engine/loans.py
def rates() -> list[dict]:
    return [{"category": "consumer_credit", "product": "Personal loan plans (new lending)", "rate_pct": 7.92,
             "as_of": "2026-08", "source_name": "Bank of Canada (sample row)", "source_url": "https://bankofcanada.ca",
             "_placeholder": True}]


def monthly_payment(amount, annual_rate_pct, months) -> float:
    r = annual_rate_pct / 100 / 12
    return round(amount / months if r == 0 else amount * r / (1 - (1 + r) ** -months), 2)


def affordability(m, amount, months, rate_pct=None, shock=None) -> dict:
    rate = 7.92 if rate_pct is None else rate_pct
    pay = monthly_payment(amount, rate, months)
    return {"_placeholder": True, "payment": pay, "rate_used": rate, "rate_source": "Sample",
            "runway_before": 7.8, "runway_with_loan": 5.1, "runway_with_loan_and_shock": 2.3,
            "verdict": "tight", "explanation": "Sample explanation until engine/loans.py lands."}


def prepay_strategies(m, shock, months=24, target_buffer_months=3) -> dict:
    line = lambda a, b: [round(a + (b - a) * i / months) for i in range(months + 1)]
    return {"_placeholder": True, "rate_used": 7.92, "strategies": [
        {"name": "Prepay", "buffer_by_month": line(5000, 5200), "runway_if_shock_hits_by_month": line(1.0, 1.1),
         "loan_paid_off_month": 14},
        {"name": "Buffer first", "buffer_by_month": line(5000, 12000), "runway_if_shock_hits_by_month": line(1.0, 2.6),
         "loan_paid_off_month": None},
        {"name": "Hybrid", "buffer_by_month": line(5000, 8600), "runway_if_shock_hits_by_month": line(1.0, 1.9),
         "loan_paid_off_month": 22}]}
