"""/plan: goal plan (emergency fund) and backup plan (if the shock hits)."""
from flask import Blueprint, render_template, request

from engine import Shock, customer_metrics

from ._common import build_scenario, error_html, friendly_errors, num, shock_from_form
from ._placeholders import engine_fn

bp = Blueprint("plans", __name__)


def optional_actions(m, shock) -> list | None:
    """Concrete monthly actions from engine.action_plan, once it exists (ClaudeOne's work)."""
    try:
        from engine import action_plan
    except ImportError:
        return None
    return action_plan(m, shock)


def loan_rates() -> list[tuple[int, dict]]:
    """Borrowing rates for the dropdown (policy and prime rates are context, not loan products)."""
    rows = engine_fn("loans", "rates")()
    return [(i, r) for i, r in enumerate(rows) if r.get("category") in ("consumer_credit", "mortgage")]


def _default_rate_idx(rates) -> int:
    return next((i for i, r in rates if r["product"].lower().startswith("personal loan")), rates[0][0] if rates else 0)


def _floor0(xs):
    return [max(round(float(x), 2), 0.0) for x in xs]


@bp.get("/plan")
def page():
    rates = loan_rates()
    return render_template("plan.html", account_id=request.args.get("account_id", ""),
                           loan_rates=rates, default_rate_idx=_default_rate_idx(rates))


@bp.post("/plan/loan")
@friendly_errors(error_html)
def loan():
    account_id = request.form.get("account_id", "").strip()
    if not account_id:
        return render_template("partials/shock_empty.html")
    rates = dict(loan_rates())
    idx = int(num(request.form, "rate_idx", -1))
    rate = rates.get(idx) or rates.get(_default_rate_idx(list(rates.items())))
    amount = num(request.form, "amount", 10000, 0, 5_000_000)
    months = int(num(request.form, "months", 36, 1, 360))
    m = customer_metrics(account_id)
    job_loss = Shock(income_factor=0.55, duration_months=6)
    a = engine_fn("loans", "affordability")(m, amount, months, rate["rate_pct"] if rate else None, None)
    p = engine_fn("loans", "prepay_strategies")(m, job_loss)
    chart = None
    if not p.get("no_loan"):
        strategies = p["strategies"]
        n = len(strategies[0]["buffer_by_month"])
        chart = {"labels": ["Now"] + [f"M{i}" for i in range(1, n)], "yName": "Savings ($)",
                 "series": [{"name": s["name"], "data": _floor0(s["buffer_by_month"]), "smooth": False} for s in strategies]}
    return render_template("partials/loan_result.html", a=a, p=p, chart=chart, rate=rate, amount=amount,
                           months=months, account_id=account_id)


@bp.post("/plan/run")
@friendly_errors(error_html)
def run():
    account_id = request.form.get("account_id", "").strip()
    if not account_id:
        return render_template("partials/shock_empty.html")
    ctx = build_scenario(account_id, shock_from_form(request.form),
                         goal_months=num(request.form, "goal_months", 3, 0.5, 24),
                         target_runway=num(request.form, "target_runway", 6, 1, 60))
    return render_template("partials/plan_result.html", **ctx, account_id=account_id,
                           actions=optional_actions(ctx["m"], ctx["shock"]))
