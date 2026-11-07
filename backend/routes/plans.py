"""/plan: goal plan (emergency fund) and backup plan (if the shock hits)."""
from flask import Blueprint, render_template, request

from ._common import build_scenario, error_html, friendly_errors, num, shock_from_form

bp = Blueprint("plans", __name__)


@bp.get("/plan")
def page():
    return render_template("plan.html", account_id=request.args.get("account_id", ""))


@bp.post("/plan/run")
@friendly_errors(error_html)
def run():
    account_id = request.form.get("account_id", "").strip()
    ctx = build_scenario(account_id, shock_from_form(request.form),
                         goal_months=num(request.form, "goal_months", 3, 0.5, 24),
                         target_runway=num(request.form, "target_runway", 6, 1, 60))
    return render_template("partials/scenario_result.html", **ctx, show_plan=True)
