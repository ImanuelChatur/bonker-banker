"""Peer benchmarking: how a customer compares with people like them.

Peer group = same income band AND same age band (from account_profile). If that group has fewer than 30 other
people, it widens to the income band only; `group` then reports age_band = None. Gender is never used.
Percentile = 0-100, HIGHER = better off than peers. For measures where lower is better (fixed-cost share, income
volatility) the percentile is inverted. Ties count half. The customer is excluded from their own peer group.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from statistics import median

from services import data_store

MIN_PEERS = 30
# measure -> (column or formula, higher_is_better)
MEASURES = {
    "buffer": (lambda d: d["B"], True),
    "runway": (lambda d: d["runway"], True),
    "fixed_cost_share": (lambda d: (d["F"] / d["I"]).where(d["I"] > 0), False),
    "income_volatility": (lambda d: d["income_volatility"], False),
}


def _pct_beaten(sorted_vals: list[float], x: float) -> float:
    lo, hi = bisect_left(sorted_vals, x), bisect_right(sorted_vals, x)
    return 100 * (lo + 0.5 * (hi - lo)) / len(sorted_vals)


def peer_benchmarks(account_id) -> dict:
    df = data_store.table("account_profile")
    me = df[df["account_id"] == str(account_id)]
    if me.empty:
        raise KeyError(f"unknown account_id {account_id}")
    me = me.iloc[0]
    others = df[df["account_id"] != str(account_id)]

    peers = others[(others["income_band"] == me["income_band"]) & (others["age_band"] == me["age_band"])]
    group = {"income_band": me["income_band"], "age_band": me["age_band"], "district_name": me["district_name"]}
    if len(peers) < MIN_PEERS:
        peers = others[others["income_band"] == me["income_band"]]
        group["age_band"] = None

    metrics = {}
    my_vals = {name: fn(me.to_frame().T).iloc[0] for name, (fn, _) in MEASURES.items()}
    for name, (fn, higher_better) in MEASURES.items():
        vals = sorted(float(v) for v in fn(peers).dropna())
        mine = my_vals[name]
        if mine is None or mine != mine or not vals:            # NaN or no peers with this measure
            metrics[name] = {"value": None, "percentile": None, "peer_median": median(vals) if vals else None}
            continue
        p = _pct_beaten(vals, float(mine))
        metrics[name] = {"value": round(float(mine), 3), "percentile": round(p if higher_better else 100 - p),
                         "peer_median": round(median(vals), 3)}
    return {"group": group, "peer_count": int(len(peers)), "metrics": metrics}
