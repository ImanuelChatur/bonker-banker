"""The "biggest finding" for /insights: what runway says about who defaults, and who a shock would break.

Descriptive statistics over all 4,500 accounts and 682 loans. Runway uses the judges' formula. The caveats travel
with the numbers so the page can't show one without the other.
"""
from __future__ import annotations

from functools import lru_cache

from .risk import BUCKETS, default_rate_by_runway, population
from .runway import RUNWAY_CAP, runway

GRADE_BANDS = [(80, 101, "A (80+)"), (65, 80, "B (65-79)"), (50, 65, "C (50-64)"), (35, 50, "D (35-49)"), (0, 35, "F (under 35)")]

SHOCKS = [  # (name, income factor, bills increase, one-off as months of spending) -- the README's twist cards
    ("Job loss, EI at 55%", 0.55, 0.0, 0.0),
    ("Household bills +15%", 1.0, 0.15, 0.0),
    ("Repair = 1 month of spending", 1.0, 0.0, 1.0),
    ("Job loss (EI 55%) + bills +15%", 0.55, 0.15, 0.0),
]


def _rate(group: list[dict]) -> dict:
    n, d = len(group), sum(r["defaulted"] for r in group)
    return {"loans": n, "defaults": d, "rate": round(100 * d / n, 1) if n else None}


def default_rate_by_grade() -> list[dict]:
    loans = [r for r in population() if r["has_loan"]]
    return [{"band": label, **_rate([r for r in loans if lo <= r["score"] < hi])} for lo, hi, label in GRADE_BANDS]


def _months_after(r: dict, income_factor: float, bills_pct: float, one_off_months: float) -> float:
    rw = runway(r["buffer"], r["income"] * income_factor, r["spending"] + bills_pct * r["bills"],
                one_off_months * r["spending"])
    return RUNWAY_CAP if isinstance(rw, str) else float(rw)


def stress_test(within_months: float = 6.0) -> list[dict]:
    """Share of all accounts whose buffer runs out within `within_months` under each twist card."""
    pop = population()
    base_short = sum(r["runway"] < within_months for r in pop)
    out = [{"name": "No shock (today)", "short": base_short, "share_pct": round(100 * base_short / len(pop), 1)}]
    for name, inc, bills, one_off in SHOCKS:
        short = sum(_months_after(r, inc, bills, one_off) < within_months for r in pop)
        out.append({"name": name, "short": short, "share_pct": round(100 * short / len(pop), 1)})
    return out


@lru_cache(maxsize=1)
def biggest_finding() -> dict:
    by_runway = default_rate_by_runway()
    low = [b for b in by_runway if b["bucket"] in ("under 1 mo", "1 to 3 mo")]
    high = next(b for b in by_runway if b["bucket"] == "12+ mo")
    low_loans, low_defaults = sum(b["loans"] for b in low), sum(b["defaults"] for b in low)
    low_rate = round(100 * low_defaults / low_loans, 1) if low_loans else None
    ratio = round(low_rate / high["rate"], 1) if low_rate and high["rate"] else None
    stress = stress_test()
    job = next(s for s in stress if s["name"].startswith("Job loss, EI"))
    pop = population()
    return {
        "headline": (f"Borrowers with under 3 months of runway defaulted {low_rate:g}% of the time, "
                     f"about {ratio:g}x the {high['rate']:g}% rate of those with 12+ months."
                     if ratio else "Not enough loans in the low-runway group to compare."),
        "subhead": (f"A job loss on EI would leave {job['share_pct']:g}% of all accounts out of savings within 6 months, "
                    f"up from {stress[0]['share_pct']:g}% today."),
        "low_runway": {"loans": low_loans, "defaults": low_defaults, "rate": low_rate},
        "high_runway": {"loans": high["loans"], "defaults": high["defaults"], "rate": high["rate"]},
        "ratio": ratio,
        "default_by_runway": by_runway,
        "default_by_grade": default_rate_by_grade(),
        "stress": stress,
        "n_accounts": len(pop),
        "n_loans": sum(r["has_loan"] for r in pop),
        "caveats": [
            "Association, not prediction: runway uses each account's latest 6 months, which can come after the default.",
            f"The low-runway group is small ({low_loans} loans), so its rate is uncertain.",
            "The resilience score is our own measure; the runway buckets use the judges' formula.",
        ],
    }
