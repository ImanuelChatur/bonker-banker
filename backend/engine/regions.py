"""Regional view: joins accounts -> districts (the bank's original regions) to runway, score and loan defaults.

Uses accounts.csv + districts.csv, which the rest of the app doesn't touch yet ("Data Use"). District names are the
dataset's own (the source bank's regions); money is in CAD as delivered by the datathon.
"""
from __future__ import annotations

from functools import lru_cache
from statistics import median

import pandas as pd

import config

from .risk import population


def _read(name: str) -> pd.DataFrame:
    pq = config.DATA_PROCESSED / f"{name}.parquet"
    if pq.exists():
        return pd.read_parquet(pq)
    return pd.read_csv(config.DATA_RAW / f"{name}.csv", dtype={"account_id": str, "district_id": str})


@lru_cache(maxsize=1)
def _lookup() -> dict[str, dict]:
    """account_id -> district facts."""
    acc = _read("accounts")[["account_id", "district_id"]].astype(str)
    dist = _read("districts")
    dist["district_id"] = dist["district_id"].astype(str)
    cols = ["district_id", "district_name", "region", "unemployment_rate_2023", "average_salary", "inhabitants"]
    merged = acc.merge(dist[cols], on="district_id", how="left")
    return {r["account_id"]: r for r in merged.to_dict("records")}


def _rank(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3:
        return None
    ra, rb = _rank(a), _rank(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return round(cov / (va * vb), 2) if va and vb else None


def _group(key: str) -> dict[str, list[dict]]:
    look = _lookup()
    groups: dict[str, list[dict]] = {}
    for r in population():
        d = look.get(r["account_id"])
        if d is None or pd.isna(d.get(key)):
            continue
        groups.setdefault(str(d[key]), []).append({**r, **d})
    return groups


def _summ(name: str, rows: list[dict]) -> dict:
    loans = [r for r in rows if r["has_loan"]]
    unemp = [float(r["unemployment_rate_2023"]) for r in rows if not pd.isna(r["unemployment_rate_2023"])]
    return {"name": name, "accounts": len(rows),
            "median_runway": round(median(r["runway"] for r in rows), 1),
            "share_shortfall_pct": round(100 * sum(r["runway"] < 120 for r in rows) / len(rows), 1),
            "share_under_3_pct": round(100 * sum(r["runway"] < 3 for r in rows) / len(rows), 1),
            "mean_score": round(sum(r["score"] for r in rows) / len(rows), 1),
            "loans": len(loans),
            "default_rate": round(100 * sum(r["defaulted"] for r in loans) / len(loans), 1) if loans else None,
            "unemployment_2023": round(sum(unemp) / len(unemp), 2) if unemp else None,
            "average_salary": round(float(median(r["average_salary"] for r in rows)), 2)}


@lru_cache(maxsize=1)
def region_summary() -> dict:
    """{"regions": [per-region summary, largest first], "districts": n, "unemployment_vs_score": spearman r,
        "unemployment_vs_runway": r, "salary_vs_score": r, "note": str}  (correlations across districts)"""
    regions = sorted((_summ(k, v) for k, v in _group("region").items()), key=lambda s: -s["accounts"])
    districts = [_summ(k, v) for k, v in _group("district_name").items() if len(v) >= 20]
    u = [d["unemployment_2023"] for d in districts]
    with_loans = [d for d in districts if d["loans"] >= 10]
    rates = [d["default_rate"] for d in regions if d["default_rate"] is not None]
    return {
        "regions": regions,
        "districts": len(districts),
        "unemployment_vs_score": spearman(u, [d["mean_score"] for d in districts]),
        "unemployment_vs_shortfall": spearman(u, [d["share_shortfall_pct"] for d in districts]),
        "salary_vs_score": spearman([d["average_salary"] for d in districts], [d["mean_score"] for d in districts]),
        "unemployment_vs_default": spearman([d["unemployment_2023"] for d in with_loans],
                                            [d["default_rate"] for d in with_loans]),
        "default_rate_range": [min(rates), max(rates)] if rates else None,
        "headline": ("Where a customer banks says little about their resilience: across districts, unemployment barely "
                     "tracks the resilience score or shortfalls. Individual income stability matters far more."),
        "note": ("Correlations are Spearman rank (-1 to 1) across districts with 20+ accounts (10+ loans for defaults). "
                 "Regions are the source bank's own, so they describe where these customers bank, not Canadian provinces. "
                 "Regional default rates rest on 57 to 129 loans each."),
    }


def account_region(account_id) -> dict | None:
    """{"district", "region", "unemployment_2023", "average_salary", "region_median_runway", "region_accounts"}"""
    d = _lookup().get(str(account_id))
    if d is None or pd.isna(d.get("region")):
        return None
    reg = next((r for r in region_summary()["regions"] if r["name"] == d["region"]), None)
    return {"district": d["district_name"], "region": d["region"],
            "unemployment_2023": None if pd.isna(d["unemployment_rate_2023"]) else float(d["unemployment_rate_2023"]),
            "average_salary": float(d["average_salary"]),
            "region_median_runway": reg["median_runway"] if reg else None,
            "region_accounts": reg["accounts"] if reg else None}
