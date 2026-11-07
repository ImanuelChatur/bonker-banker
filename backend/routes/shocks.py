"""/shock: Shock Lab - apply a shock and recalculate."""
from flask import Blueprint, render_template, request

from ._common import build_scenario, error_html, friendly_errors, shock_from_form

bp = Blueprint("shocks", __name__)

PRESETS = {  # prefill values for the one-click scenarios (README examples)
    "job_loss": {"income_pct": 55, "duration_months": 6},
    "bills_up": {"bills_pct": 15},
    "repair": {"one_off_months": 1},
    "combo": {"income_pct": 55, "bills_pct": 15, "duration_months": 6},
}


@bp.get("/shock")
def page():
    return render_template("shock_lab.html", account_id=request.args.get("account_id", ""),
                           f=PRESETS.get(request.args.get("preset", ""), {}))


@bp.post("/shock/run")
@friendly_errors(error_html)
def run():
    account_id = request.form.get("account_id", "").strip()
    ctx = build_scenario(account_id, shock_from_form(request.form))
    return render_template("partials/scenario_result.html", **ctx, show_plan=False)
