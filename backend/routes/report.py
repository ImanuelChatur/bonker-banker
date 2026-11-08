"""/report/<account_id>: a one-page, printable Runway Report for a customer."""
from datetime import date

from flask import Blueprint, render_template

from engine import Shock, apply_shock, backup_plan, customer_metrics, goal_plan, runway
from services import data_store

from ._common import error_html, friendly_errors, shock_from_form
from .customer import optional_extras, spending_mix
from .plans import optional_actions
from .shocks import PRESET_LABELS, PRESETS

bp = Blueprint("report", __name__)


def _preset_shock(fields: dict) -> Shock:
    # Income % and duration only apply when the preset includes a job loss (same as the Shock Lab toggle)
    form = {**fields} if fields["job_loss"] else {**fields, "income_pct": 100, "duration_months": 0}
    return shock_from_form(form)


@bp.get("/report/<account_id>")
@friendly_errors(error_html)
def show(account_id):
    m = customer_metrics(account_id)
    scenarios = []
    for key, label in PRESET_LABELS:
        shock = _preset_shock(PRESETS[key])
        res = apply_shock(m, shock)
        scenarios.append({"key": key, "label": label, "res": res, "backup": backup_plan(m, shock)})
    return render_template("report.html", m=m, account_id=account_id, today=date.today(),
                           runway=runway(m.buffer, m.income, m.spending),
                           no_income_runway=runway(m.buffer, 0.0, m.spending),
                           surplus=m.income - m.spending, mix=spending_mix(data_store.account_rows(account_id)),
                           goal=goal_plan(m), scenarios=scenarios, actions=optional_actions(m, None), **optional_extras(account_id, m))
