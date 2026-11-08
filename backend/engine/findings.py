"""The "biggest finding" for /insights, measured without peeking at the future.

Each account's runway on the /customer page uses its LAST six months, which can come after a loan defaulted. So
here every loan is judged only on the monthly rows BEFORE it was granted, the way a lender would have to.
Loans with under six months of prior history are left out. Also: a population stress test (apply each README
twist card to every account and count who runs out within six months).
"""
from __future__ import annotations

from functools import lru_cache

from services import data_store

from .metrics import metrics_from_rows
from .resilience import resilience_score, runway_months
from .risk import population
from .runway import RUNWAY_CAP, runway

MIN_HISTORY = 6
GRADE_BANDS = [("A (80+)", 80, 101), ("B (65-79)", 65, 80), ("C (50-64)", 50, 65), ("D (35-49)", 35, 50),
               ("F (under 35)", 0, 35)]
RUNWAY_BANDS = [("under 3 mo", 0, 3), ("3 to 12 mo", 3, 12), ("12+ mo", 12, RUNWAY_CAP + 1)]
SHOCKS = [  # (name, income factor, bills increase, one-off as months of spending): the README's twist cards
    ("Job loss, EI at 55%", 0.55, 0.0, 0.0),
    ("Household bills +15%", 1.0, 0.15, 0.0),
    ("Repair = 1 month of spending", 1.0, 0.0, 1.0),
    ("Job loss (EI 55%) + bills +15%", 0.55, 0.15, 0.0),
]


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


def _bands(rows: list[dict], key: str, bands, name: str) -> list[dict]:
    res = []
    for label, lo, hi in bands:
        grp = [r for r in rows if lo <= r[key] < hi]
        d = sum(r["defaulted"] for r in grp)
        res.append({name: label, "loans": len(grp), "defaults": d, "rate": round(100 * d / len(grp), 1) if grp else None})
    return res


def _months_after(r: dict, income_factor: float, bills_pct: float, one_off_months: float) -> float:
    rw = runway(r["buffer"], r["income"] * income_factor, r["spending"] + bills_pct * r["bills"],
                one_off_months * r["spending"])
    return RUNWAY_CAP if isinstance(rw, str) else float(rw)


def stress_test(within_months: float = 6.0) -> list[dict]:
    """Share of all accounts whose buffer runs out within `within_months`, today and under each twist card."""
    pop = population()
    base = sum(r["runway"] < within_months for r in pop)
    out = [{"name": "No shock (today)", "short": base, "share_pct": round(100 * base / len(pop), 1)}]
    for name, inc, bills, one_off in SHOCKS:
        short = sum(_months_after(r, inc, bills, one_off) < within_months for r in pop)
        out.append({"name": name, "short": short, "share_pct": round(100 * short / len(pop), 1)})
    return out


@lru_cache(maxsize=1)
def biggest_finding() -> dict:
    rows = pre_loan_table()
    total_loans = sum(1 for aid in data_store.account_ids() if data_store.account_loan(aid) is not None)
    bad = [r for r in rows if r["defaulted"]]
    good = [r for r in rows if not r["defaulted"]]

    by_grade = _bands(rows, "score", GRADE_BANDS, "band")
    by_runway = _bands(rows, "runway", RUNWAY_BANDS, "bucket")
    low, high = by_runway[0], by_runway[-1]
    a, f = by_grade[0], by_grade[-1]
    ratio = round(f["rate"] / a["rate"], 1) if f["rate"] is not None and a["rate"] else None
    auc_score = round(_auc([r["score"] for r in bad], [r["score"] for r in good]), 2)
    auc_runway = round(_auc([r["runway"] for r in bad], [r["runway"] for r in good]), 2)
    names = sorted({k for r in rows for k in r["parts"]})
    signals = sorted(({"name": n, "auc": round(_auc([r["parts"].get(n, 0) for r in bad],
                                                     [r["parts"].get(n, 0) for r in good]), 2)} for n in names),
                     key=lambda s: -s["auc"])
    stress = stress_test()
    job = next(s for s in stress if s["name"].startswith("Job loss, EI"))

    return {
        "headline": (f"Judged only on the months before the loan was granted, borrowers with an F resilience grade "
                     f"went on to default {f['rate']:g}% of the time, against {a['rate']:g}% for grade A "
                     f"({ratio:g} times as often)." if ratio else "Not enough loans with prior history to compare."),
        "subhead": (f"A job loss on EI would leave {job['share_pct']:g}% of all accounts out of savings within 6 months, "
                    f"up from {stress[0]['share_pct']:g}% today."),
        "low_runway": {k: low[k] for k in ("loans", "defaults", "rate")},
        "high_runway": {k: high[k] for k in ("loans", "defaults", "rate")},
        "ratio": ratio,
        "default_by_runway": by_runway,
        "default_by_grade": by_grade,
        "auc_score": auc_score, "auc_runway": auc_runway, "signals": signals,
        "stress": stress,
        "n_accounts": len(population()),
        "n_loans": len(rows), "n_excluded": total_loans - len(rows),
        "method": (f"Each loan's account was scored using only the monthly rows before the loan start date "
                   f"(at least {MIN_HISTORY} months). Default = loan status B or D in loans.csv."),
        "caveats": [
            "Association, not proof of cause. We designed the score first, then checked it against defaults.",
            f"Small groups: grade F has {f['loans']} loans, so its rate could move several points with a few cases.",
            f"AUC {auc_score:.2f} means the score ranks a random repaying borrower above a random defaulter "
            f"{auc_score * 100:.0f}% of the time: useful, not decisive.",
            "The resilience score is our own measure; runway uses the judges' formula.",
        ],
    }
