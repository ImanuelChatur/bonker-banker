"""Make a plan: a goal plan (emergency fund) and a backup plan if the shock hits.

Both use only the customer's own numbers (I, S, F, B from metrics).
"""
from __future__ import annotations

from .metrics import Metrics
from .shocks import Shock, apply_shock


def goal_plan(m: Metrics, target_months: float = 3.0) -> dict:
    """Emergency fund of `target_months` x typical spending."""
    target = target_months * m.spending
    shortfall = max(target - m.buffer, 0.0)
    capacity = max(m.income - m.spending, 0.0)           # what they typically save per month
    out = {"target_months": target_months, "target_amount": round(target, 2),
           "current_buffer": round(m.buffer, 2), "still_needed": round(shortfall, 2),
           "typical_monthly_surplus": round(capacity, 2)}
    if shortfall == 0:
        out["plan"] = "Goal already met."
    elif capacity > 0:
        out["months_at_current_surplus"] = round(shortfall / capacity, 1)
        out["plan"] = (f"Save {round(capacity, 2)}/month to reach the goal in "
                       f"{round(shortfall / capacity, 1)} months.")
    else:
        discretionary = max(m.spending - m.fixed_costs, 0.0)
        out["plan"] = ("No monthly surplus. Income does not cover typical spending, so the first step is "
                       f"trimming spending (about {round(discretionary, 2)}/month is non-fixed).")
    return out


def backup_plan(m: Metrics, shock: Shock, target_runway_months: float = 6.0) -> dict:
    """If the shock hits: how much spending must be cut to last `target_runway_months`."""
    r = apply_shock(m, shock)["after"]
    buffer_left = r["buffer_left"]
    if buffer_left <= 0:
        return {"feasible_with_cuts": False, "plan": "The one-off cost wipes out the buffer; "
                "outside help (credit, family, deferral) is needed before any cuts can work."}
    affordable_gap = buffer_left / target_runway_months
    cut_needed = max(r["monthly_gap"] - affordable_gap, 0.0)
    discretionary = max(r["spending"] - m.fixed_costs, 0.0)
    out = {"target_runway_months": target_runway_months,
           "monthly_cut_needed": round(cut_needed, 2),
           "discretionary_spending": round(discretionary, 2)}
    if cut_needed == 0:
        out.update(feasible_with_cuts=True, plan="Buffer already lasts the target without cuts.")
    elif cut_needed <= discretionary:
        out.update(feasible_with_cuts=True, cut_pct_of_discretionary=round(100 * cut_needed / discretionary, 1),
                   plan=f"Cut spending by {round(cut_needed, 2)}/month "
                        f"({round(100 * cut_needed / discretionary)}% of non-fixed spending) to last "
                        f"{target_runway_months:g} months.")
    else:
        out.update(feasible_with_cuts=False,
                   plan=f"Cutting all non-fixed spending still leaves a gap of {round(cut_needed - discretionary, 2)}/month; "
                        "fixed costs (bills, insurance, loan) must be renegotiated or income replaced.")
    return out
