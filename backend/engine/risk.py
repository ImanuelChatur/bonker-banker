"""Population view: how runway relates to loan default across the whole dataset.

Descriptive only. Runway here uses each account's latest 6 months of balance, which can fall after
a default happened, so this shows association, not a prediction of future default.
"""
from __future__ import annotations

from functools import lru_cache
from statistics import median

from services import data_store

from .metrics import metrics_from_rows
from .resilience import resilience_score
from .runway import RUNWAY_CAP, runway

BUCKETS = [(0, 1, "under 1 mo"), (1, 3, "1 to 3 mo"), (3, 6, "3 to 6 mo"), (6, 12, "6 to 12 mo"),
           (12, float("inf"), "12+ mo")]


def _months(m) -> float:
    r = runway(m.buffer, m.income, m.spending)
    return RUNWAY_CAP if isinstance(r, str) else r


@lru_cache(maxsize=1)
def population() -> list[dict]:
    """One row per account: runway months and (if the account has a loan) whether it defaulted."""
    out = []
    for aid in data_store.account_ids():
        loan = data_store.account_loan(aid)
        rows = data_store.account_rows(aid)
        m = metrics_from_rows(rows, aid, loan)
        out.append({"account_id": aid, "runway": _months(m), "buffer": m.buffer,
                    "score": resilience_score(m, rows)["score"],
                    "has_loan": loan is not None,
                    "defaulted": int(loan["defaulted"]) if loan is not None else None})
    return out


def warm_up() -> None:
    """Compute the population table in the background so the first customer page isn't slow."""
    import threading

    def _go():
        try:
            population()
        except Exception:               # data not processed yet: pages show their own message
            pass
    threading.Thread(target=_go, daemon=True, name="warm-population").start()


def default_rate_by_runway() -> list[dict]:
    pop = [r for r in population() if r["has_loan"]]
    rows = []
    for lo, hi, label in BUCKETS:
        grp = [r for r in pop if lo <= r["runway"] < hi]
        n, d = len(grp), sum(r["defaulted"] for r in grp)
        rows.append({"bucket": label, "loans": n, "defaults": d, "rate": round(100 * d / n, 1) if n else None})
    return rows


def overview() -> dict:
    pop = population()
    loans = [r for r in pop if r["has_loan"]]
    return {
        "accounts": len(pop), "loans": len(loans),
        "default_rate": round(100 * sum(r["defaulted"] for r in loans) / len(loans), 1) if loans else None,
        "median_runway": round(median(r["runway"] for r in pop), 1),
        "share_under_3": round(100 * sum(r["runway"] < 3 for r in pop) / len(pop), 1),
    }
