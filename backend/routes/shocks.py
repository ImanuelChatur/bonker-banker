"""/shock: Shock Lab - apply a shock and recalculate, live as the sliders move."""
from flask import Blueprint, render_template, request

from ._common import build_scenario, error_html, friendly_errors, shock_from_form

bp = Blueprint("shocks", __name__)

# Every preset sets ALL fields, so clicking one fully replaces the previous scenario.
_BLANK = {"job_loss": False, "income_pct": 55, "duration_months": 6, "bills_pct": 0,
          "one_off_months": 0, "one_off_cost": 0, "extra_spending": 0}
PRESETS = {  # the README's example twists, one click each
    "job_loss": {**_BLANK, "job_loss": True, "income_pct": 55, "duration_months": 6},
    "bills_up": {**_BLANK, "bills_pct": 15},
    "repair": {**_BLANK, "one_off_months": 1},
    "combo": {**_BLANK, "job_loss": True, "income_pct": 55, "duration_months": 6, "bills_pct": 15},
}
PRESET_LABELS = [
    ("job_loss", "Laid off · EI 55% · 6 mo"),
    ("repair", "Furnace · 1 month of spending"),
    ("bills_up", "Bills +15%"),
    ("combo", "Laid off + bills +15%"),
]


@bp.get("/shock")
def page():
    preset = request.args.get("preset", "")
    return render_template("shock_lab.html", account_id=request.args.get("account_id", "").strip(),
                           f=PRESETS.get(preset, _BLANK), active_preset=preset,
                           presets=PRESETS, preset_labels=PRESET_LABELS, blank=_BLANK)


@bp.post("/shock/run")
@friendly_errors(error_html)
def run():
    account_id = request.form.get("account_id", "").strip()
    if not account_id:
        return render_template("partials/shock_empty.html")
    ctx = build_scenario(account_id, shock_from_form(request.form))
    return render_template("partials/scenario_result.html", **ctx, show_plan=False)
