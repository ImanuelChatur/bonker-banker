"""Concrete next steps for a customer, each with the runway it buys."""
from __future__ import annotations

from .metrics import Metrics
from .plans import _usd
from .runway import RUNWAY_CAP, runway
from .shocks import Shock, apply_shock


def _months(m: Metrics, income: float, spending: float, buffer: float | None = None, one_off: float = 0.0) -> float:
    r = runway(m.buffer if buffer is None else buffer, income, spending, one_off)
    return RUNWAY_CAP if isinstance(r, str) else float(r)


def action_plan(m: Metrics, shock: Shock | None = None) -> list[dict]:
    """Things to do, biggest runway gain first.

    Returns [{"title", "monthly_change", "runway_gain_months", "detail"}]. monthly_change is the dollars per month
    the action improves cash flow (0 for a one-time top-up). With a shock, gains are measured after the shock.
    When there is no shortfall the list has one item about growing the cushion (runway_gain_months is None).
    """
    after = apply_shock(m, shock or Shock())["after"]
    income, spending, one_off = after["income"], after["spending"], after["one_off_cost"]
    base = _months(m, income, spending, one_off=one_off)
    gap = spending - income
    flexible = max(m.spending - m.fixed_costs, 0.0)

    if gap <= 0:
        surplus = -gap
        target = 6 * m.spending
        need = max(target - m.buffer, 0.0)
        if need == 0:
            detail = "Savings already cover 6 months of spending. Keep the surplus working for you."
        elif surplus > 0:
            detail = (f"Moving {_usd(surplus)}/month into savings reaches a 6-month cushion "
                      f"({_usd(target)}) in about {need / surplus:.0f} months.")
        else:
            detail = f"Aim for a 6-month cushion of {_usd(target)}."
        return [{"title": "Build the cushion", "monthly_change": round(surplus, 2),
                 "runway_gain_months": None, "detail": detail}]

    def gain(new_spending: float, new_income: float | None = None, extra_buffer: float = 0.0) -> float:
        inc = income if new_income is None else new_income
        return round(_months(m, inc, new_spending, buffer=m.buffer + extra_buffer, one_off=one_off) - base, 1)

    actions = []
    if flexible > 0:
        for pct in (10, 25):
            cut = flexible * pct / 100
            g = gain(spending - cut)
            actions.append({"title": f"Trim flexible spending by {pct}%", "monthly_change": round(cut, 2),
                            "runway_gain_months": g,
                            "detail": f"Cutting {_usd(cut)}/month from the {_usd(flexible)} that is not bills, "
                                      f"insurance or loans buys about {g:g} more months."})
    if m.household_bills > 0:
        save = m.household_bills * 0.10
        g = gain(spending - save)
        actions.append({"title": "Renegotiate household bills by 10%", "monthly_change": round(save, 2),
                        "runway_gain_months": g,
                        "detail": f"Lower phone, internet or utility plans to save {_usd(save)}/month: "
                                  f"about {g:g} more months."})
    extra = max(m.income * 0.10, 0.0)
    if extra > 0:
        g = gain(spending, income + extra)
        actions.append({"title": "Bring in 10% more income", "monthly_change": round(extra, 2),
                        "runway_gain_months": g,
                        "detail": f"An extra {_usd(extra)}/month (shifts, side work, benefits) adds about {g:g} months."})
    g = gain(spending, extra_buffer=m.spending)
    actions.append({"title": "Add one month of spending to savings", "monthly_change": 0.0,
                    "runway_gain_months": g,
                    "detail": f"A one-time {_usd(m.spending)} top-up (tax refund, sale, gift) adds about {g:g} months."})
    actions.sort(key=lambda a: -(a["runway_gain_months"] or 0))
    return actions
