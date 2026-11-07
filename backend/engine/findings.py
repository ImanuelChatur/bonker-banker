"""The "biggest finding" for /insights, measured without peeking at the future.

risk.default_rate_by_runway() uses each account's LAST six months, which can come after a default, so part of
that pattern is the default itself. Here every loan is judged only on the months BEFORE it was granted, the
way a lender would have to. Loans with under six months of prior history are left out.

Also: a population stress test (apply one shock to every account and count who runs out).
"""
from __future__ import annotations

from functools import lru_cache

from services import data_store

from .metrics import metrics_from_rows
from .resilience import resilience_score, runway_months
from .runway import RUNWAY_CAP, runway

GRADE_BANDS = [("A", 80, 101), ("B", 65, 80), ("C", 50, 65), ("D", 35, 50), ("F", 0, 35)]
RUNWAY_BANDS = [("Under 3 months", 0, 3), ("3 to 12 months", 3, 12), ("12+ months", 12, RUNWAY_CAP),
                ("No shortfall", RUNWAY_CAP, RUNWAY_CAP + 1)]
MIN_HISTORY = 6


def _auc(pos: list[float], neg: list[float]) -> float:
    """Chance a random non-defaulter scores higher than a random defaulter (0.5 = no signal)."""
    if not pos or not neg:
        return 0.5
    wins = sum((n > p) + 0.5 * (n == p) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


@lru_cache(maxsize=1)
def pre_loan_table() -> list[dict]:
    """One row per loan: score, parts and runway measured on the months before the loan started."""
    out = []
    for aid in data_store.account_ids():
        loan = data_store.account_loan(aid)
        if loan is None:
            continue
        start = str(loan["loan_start"])[:7]
        pre = [r for r in data_store.account_rows(aid) if r["month"] < start]
        if len(pre) < MIN_HISTORY:
            continue
        m = metrics_from_rows(pre, aid, None)
        s = resilience_score(m, pre)
        out.append({"account_id": aid, "runway": runway_months(m), "score": s["score"],
                    "parts": {p["name"]: p["points"] / p["max"] for p in s["parts"]},
                    "defaulted": int(loan["defaulted"])})
    return out


def _band_rates(rows: list[dict], key: str, bands) -> list[dict]:
    res = []
    for label, lo, hi in bands:
        grp = [r for r in rows if lo <= r[key] < hi]
        d = sum(r["defaulted"] for r in grp)
        res.append({"label": label, "loans": len(grp), "defaults": d,
                    "rate": round(100 * d / len(grp), 1) if grp else None})
    return res


def loan_default_finding() -> dict:
    """
    {"headline": str, "n_loans": int, "n_excluded": int, "overall_rate": float,
     "by_grade": [{"label","loans","defaults","rate"}], "by_runway": [...same...],
     "auc_score": float, "auc_runway": float, "signals": [{"name","auc"}] (strongest first),
     "method": str, "caveats": [str]}
    Rates are percentages with one decimal.
    """
    rows = pre_loan_table()
    total_loans = sum(1 for aid in data_store.account_ids() if data_store.account_loan(aid) is not None)
    d = [r for r in rows if r["defaulted"]]
    ok = [r for r in rows if not r["defaulted"]]

    by_grade = _band_rates(rows, "score", GRADE_BANDS)
    by_runway = _band_rates(rows, "runway", RUNWAY_BANDS)
    auc_score = round(_auc([r["score"] for r in d], [r["score"] for r in ok]), 3)
    auc_runway = round(_auc([r["runway"] for r in d], [r["runway"] for r in ok]), 3)

    names = sorted({k for r in rows for k in r["parts"]})
    signals = sorted(({"name": n, "auc": round(_auc([r["parts"].get(n, 0) for r in d],
                                                     [r["parts"].get(n, 0) for r in ok]), 3)} for n in names),
                     key=lambda s: -s["auc"])

    a = next(b for b in by_grade if b["label"] == "A")
    f = next(b for b in by_grade if b["label"] == "F")
    overall = round(100 * len(d) / len(rows), 1) if rows else None
    if f["rate"] is not None and a["rate"]:
        headline = (f"Judged only on the months before the loan was granted, customers with an F resilience grade went "
                    f"on to default {f['rate']:g}% of the time, against {a['rate']:g}% for grade A "
                    f"({f['rate'] / a['rate']:.1f} times as often).")
    else:
        headline = "Not enough loans with prior history to compare grades."

    return {
        "headline": headline, "n_loans": len(rows), "n_excluded": total_loans - len(rows), "overall_rate": overall,
        "by_grade": by_grade, "by_runway": by_runway, "auc_score": auc_score, "auc_runway": auc_runway,
        "signals": signals,
        "method": (f"Each loan's account was scored using only the monthly rows before the loan start date "
                   f"(at least {MIN_HISTORY} months). Default = loan status B or D in loans.csv."),
        "caveats": [
            f"Small groups: grade F has {f['loans']} loans, so its rate could move by several points with a few cases.",
            "Association, not proof of cause. The score was designed by us, then checked against defaults.",
            f"AUC {auc_score:.2f} means the score ranks a random non-defaulter above a random defaulter "
            f"{auc_score * 100:.0f}% of the time: useful, not decisive.",
            "Historical, anonymized bank data (PKDD'99) presented in Canadian dollars by the datathon.",
        ],
    }


def population_stress(income_factor: float = 0.55, bills_pct: float = 0.0, months: int = 6) -> dict:
    """Apply one shock to every account. {"n","short_within":months,"share_short","share_no_shortfall_before",
    "share_short_before"}: shares are percentages. Uses the judges' runway formula per account."""
    from .risk import population
    pop = population()
    short_after = short_before = no_short_before = 0
    for r in pop:
        before = runway(r["buffer"], r["income"], r["spending"])
        after = runway(r["buffer"], r["income"] * income_factor, r["spending"] + bills_pct * r["bills"])
        to_m = lambda x: RUNWAY_CAP if isinstance(x, str) else x
        no_short_before += isinstance(before, str)
        short_before += to_m(before) < months
        short_after += to_m(after) < months
    n = len(pop)
    pct = lambda k: round(100 * k / n, 1) if n else None
    return {"n": n, "short_within": months, "income_factor": income_factor, "bills_pct": bills_pct,
            "share_short": pct(short_after), "share_short_before": pct(short_before),
            "share_no_shortfall_before": pct(no_short_before)}
