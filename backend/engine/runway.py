"""The judges' runway formula (datathon README)."""
from __future__ import annotations

RUNWAY_CAP = 120.0


def runway(buffer: float, income: float, spending: float, one_off: float = 0.0) -> float | str:
    """Months until the buffer runs out, rounded to 1 decimal; capped at 120."""
    buffer_left = buffer - one_off
    gap = spending - income
    if buffer_left <= 0:
        return 0.0
    if gap <= 0:
        return "no shortfall (120+)"
    return round(min(buffer_left / gap, RUNWAY_CAP), 1)


def projection(buffer: float, income: float, spending: float, one_off: float = 0.0, months: int = 24) -> list[float]:
    """Buffer at month 0..N under a constant monthly gap, floored at zero (for charts)."""
    gap = spending - income
    out, b = [], buffer - one_off
    for _ in range(months + 1):
        out.append(round(max(b, 0.0), 2))
        b -= max(gap, 0.0)
    return out
