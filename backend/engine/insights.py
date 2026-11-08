"""Population stress test results for /insights and "who to call this week".

Reads tables precomputed by scripts/stress_test.py (no heavy work at request time). The runway in those tables is
the judges' formula, checked against engine.shocks.apply_shock in tests/test_stress.py.
"""
from __future__ import annotations

from services import data_store

HEADLINE_SCENARIO = {"ei_pct": 55, "bills_pct": 15, "one_off_months": 0}   # README twist: job loss on EI + bills +15%


def stress_grid() -> list[dict]:
    """[{"ei_pct", "bills_pct", "one_off_months", "pct_runout_3m", "pct_runout_6m", "n"}] for all 60 scenarios."""
    df = data_store.table("stress_grid")
    return [{k: (int(v) if k in ("ei_pct", "bills_pct", "one_off_months", "n") else float(v)) for k, v in r.items()}
            for r in df.to_dict("records")]


def stress_breakdown(ei_pct: float = 55, bills_pct: float = 15, one_off_months: float = 0) -> list[dict]:
    """[{"group_type", "group", "pct_runout_6m", "n"}] for one grid scenario; [] if it isn't in the grid
    (EI in 100/75/55/40/0, bills in 0/10/15/25, repair in 0/1/2 months)."""
    df = data_store.table("stress_breakdown")
    sel = df[(df["ei_pct"] == ei_pct) & (df["bills_pct"] == bills_pct) & (df["one_off_months"] == one_off_months)]
    return [{"group_type": r["group_type"], "group": r["group"], "pct_runout_6m": float(r["pct_runout_6m"]),
             "n": int(r["n"])} for r in sel.to_dict("records")]


def headline() -> dict:
    """{"text", "pct_runout_3m", "pct_runout_6m", "scenario"} for the README's combined twist card."""
    sc = HEADLINE_SCENARIO
    row = next(r for r in stress_grid() if all(r[k] == v for k, v in sc.items()))
    today = next(r for r in stress_grid() if r["ei_pct"] == 100 and r["bills_pct"] == 0 and r["one_off_months"] == 0)
    text = (f"If every customer lost their job (EI at 55% of income) and household bills rose 15%, "
            f"{row['pct_runout_6m']:g}% would run out of savings within 6 months and {row['pct_runout_3m']:g}% within 3, "
            f"against {today['pct_runout_6m']:g}% within 6 months today.")
    return {"text": text, "pct_runout_3m": row["pct_runout_3m"], "pct_runout_6m": row["pct_runout_6m"], "scenario": dict(sc)}


def at_risk_customers(limit: int = 50) -> list[dict]:
    """[{"account_id", "runway", "runway_ei55", "district_name", "reasons": [str]}], shortest runway on EI first."""
    df = data_store.table("at_risk").head(limit)
    return [{"account_id": str(r["account_id"]), "runway": float(r["runway"]), "runway_ei55": float(r["runway_ei55"]),
             "district_name": r["district_name"], "reasons": [str(x) for x in r["reasons"]]}
            for r in df.to_dict("records")]
