"""Financial resilience score (0 to 100) and where a customer sits against everyone else.

This is OUR measure, built on top of the judges' numbers. It never changes I, S, F, H, B, P or the
runway formula; it only reads them. Every point is explained, so the score can be defended live.

Parts (max points):  runway 40 | cash flow 20 | fixed-cost burden 15 | income stability 15 | overdraft days 10
The last two need monthly history. When history isn't available (e.g. one uploaded statement) they are
left out and the score is rescaled over the parts that can be measured.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from statistics import mean, pstdev

from services import data_store

from .metrics import Metrics
from .runway import RUNWAY_CAP, runway

GRADES = [(80, "A"), (65, "B"), (50, "C"), (35, "D"), (0, "F")]


def _lin(x: float, lo: float, hi: float) -> float:
    """0 at lo, 1 at hi, clamped."""
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def _f(v) -> float:
    return float(v) if v not in (None, "") else 0.0


def runway_months(m: Metrics) -> float:
    r = runway(m.buffer, m.income, m.spending)
    return RUNWAY_CAP if isinstance(r, str) else float(r)


def _history(m: Metrics, rows):
    if rows is not None:
        return rows
    try:
        return data_store.account_rows(m.account_id)
    except Exception:                      # unknown account (e.g. an uploaded statement) or data not loaded
        return None


def resilience_score(m: Metrics, rows: list[dict] | None = None) -> dict:
    """{"score": 0-100, "grade": "A".."F", "parts": [{"name","points","max","why"}]}"""
    parts: list[dict] = []

    def add(name: str, max_pts: float, frac: float, why: str) -> None:
        parts.append({"name": name, "points": round(max_pts * frac, 1), "max": max_pts, "why": why})

    # 1. Runway: months the buffer lasts at typical income and spending (the judges' formula).
    months = runway_months(m)
    if runway(m.buffer, m.income, m.spending) == "no shortfall (120+)":
        add("Runway", 40, 1.0, "Income covers typical spending, so savings are not being drained.")
    else:
        add("Runway", 40, _lin(min(months, 12), 0, 12),
            f"Savings last about {months:g} months at typical income and spending (12+ months earns full points).")

    # 2. Cash flow: share of income left after spending.
    rate = (m.income - m.spending) / m.income if m.income > 0 else -1.0
    add("Cash flow", 20, _lin(rate, -0.2, 0.2),
        f"Typically {'saves' if rate >= 0 else 'overspends by'} {abs(rate) * 100:.0f}% of income each month "
        "(+20% or better earns full points).")

    # 3. Fixed-cost burden: bills + insurance + loan payments as a share of income.
    burden = m.fixed_costs / m.income if m.income > 0 else 1.0
    add("Fixed costs", 15, 1 - _lin(burden, 0.35, 0.8),
        f"Bills, insurance and loan payments take {burden * 100:.0f}% of income (under 35% earns full points).")

    hist = _history(m, rows)
    if hist and len(hist) >= 6:
        recent = hist[-12:]
        inc = [_f(r.get("money_in")) for r in recent]
        cv = pstdev(inc) / mean(inc) if mean(inc) > 0 else 1.0
        add("Income stability", 15, 1 - _lin(cv, 0.15, 0.8),
            f"Monthly income varies by about {cv * 100:.0f}% around its average (under 15% earns full points).")

        below = sum(_f(r.get("days_below_zero")) for r in recent)
        add("Overdraft days", 10, 1 - _lin(below, 0, 30),
            f"{below:.0f} day{'s' if below != 1 else ''} below zero in the last {len(recent)} months "
            "(none earns full points).")

    earned = sum(p["points"] for p in parts)
    possible = sum(p["max"] for p in parts)
    score = round(100 * earned / possible)
    grade = next(g for floor, g in GRADES if score >= floor)
    return {"score": score, "grade": grade, "parts": parts}


# ------------------------------------------------------------------ peers
def _sorted_population():
    from . import risk
    pop = risk.population()
    return (sorted(r["runway"] for r in pop), sorted(r["score"] for r in pop),
            {r["account_id"]: r for r in pop}, len(pop))


_cache: dict = {}


def _pct(sorted_vals: list[float], x: float) -> int:
    """Percent of accounts this one beats (ties count half), so heavy ties at the cap stay fair."""
    lo, hi = bisect_left(sorted_vals, x), bisect_right(sorted_vals, x)
    return round(100 * (lo + 0.5 * (hi - lo)) / len(sorted_vals))


def peer_percentile(account_id) -> dict:
    """{"runway_pct": 0-100|None, "score_pct": 0-100|None, "n": accounts compared}"""
    if "pop" not in _cache:
        _cache["pop"] = _sorted_population()
    runways, scores, by_id, n = _cache["pop"]
    me = by_id.get(str(account_id))
    if me is None:
        return {"runway_pct": None, "score_pct": None, "n": n}
    return {"runway_pct": _pct(runways, me["runway"]), "score_pct": _pct(scores, me["score"]), "n": n}
