"""Probabilistic runway (our measure): how long savings last if the coming months look like the account's past ones.

Method: start at the judges' buffer B and replay the account's own monthly money in / money out in random order
(each month drawn whole, with replacement). Stop when savings drop below zero, or at 120 months. A shock, if given,
scales money in by income_factor and adds the bills increase (bills_pct x H), the same way apply_shock does.
Deterministic for a given seed.
"""
from __future__ import annotations

import numpy as np

from services import data_store

from .metrics import metrics_from_rows
from .runway import RUNWAY_CAP
from .shocks import Shock

HORIZON = int(RUNWAY_CAP)


def _f(v) -> float:
    return float(v) if v not in (None, "") else 0.0


def simulate_runway(account_id, shock: Shock | None = None, n: int = 1000, seed: int = 0, rows=None) -> dict:
    rows = rows if rows is not None else data_store.account_rows(account_id)
    m = metrics_from_rows(rows, str(account_id), None)
    inc = np.array([_f(r.get("money_in")) for r in rows])
    out = np.array([_f(r.get("money_out")) for r in rows])
    sh = shock or Shock()
    net = inc * sh.income_factor - (out + sh.household_bills_pct * m.household_bills + sh.extra_monthly_spending)
    start = m.buffer - sh.one_off_cost - sh.one_off_months_of_spending * m.spending

    rng = np.random.default_rng(seed)
    draws = net[rng.integers(0, len(net), size=(n, HORIZON))]
    path = start + np.cumsum(draws, axis=1)
    below = path < 0
    months = np.where(below.any(axis=1), below.argmax(axis=1).astype(float), RUNWAY_CAP)   # month index it went below
    if start <= 0:
        months[:] = 0.0

    p10, p50, p90 = (round(float(np.percentile(months, q)), 1) for q in (10, 50, 90))
    if p10 >= RUNWAY_CAP:
        text = "In 9 of 10 simulated futures the savings never run out within 10 years (our measure)."
    elif p10 < 1:
        text = "In at least 1 of 10 simulated futures the savings run out within the first month (our measure)."
    else:
        text = f"In 9 of 10 simulated futures the savings last at least {p10:g} month{'s' if p10 != 1 else ''} (our measure)."
    return {
        "p10": p10, "p50": p50, "p90": p90,
        "prob_runout_6m": round(100 * float((months < 6).mean()), 1),
        "prob_runout_12m": round(100 * float((months < 12).mean()), 1),
        "n_sims": n, "months_of_history": len(rows),
        "text": text,
        "method": (f"{n:,} simulations replaying this account's own {len(rows)} months in random order, starting from "
                   "its savings buffer B, until savings drop below zero (capped at 120 months)."),
    }
