"""/demo: a one-page walkthrough for one account (know -> shock -> explain -> plan -> report)."""
from flask import Blueprint, render_template, request

from engine import customer_metrics, runway

from ._common import build_scenario, error_html, friendly_errors
from .customer import optional_extras
from .plans import optional_actions
from .report import _preset_shock
from .shocks import PRESET_LABELS, PRESETS

bp = Blueprint("demo", __name__)


@bp.get("/demo")
@friendly_errors(error_html)
def page():
    account_id = request.args.get("account_id", "").strip() or "20111"
    m = customer_metrics(account_id)
    return render_template("demo.html", account_id=account_id, m=m,
                           runway=runway(m.buffer, m.income, m.spending),
                           presets=PRESET_LABELS, **optional_extras(account_id, m))


@bp.post("/demo/run")
@friendly_errors(error_html)
def run():
    account_id = request.form.get("account_id", "").strip()
    key = request.form.get("preset", "job_loss")
    shock = _preset_shock(PRESETS.get(key, PRESETS["job_loss"]))
    ctx = build_scenario(account_id, shock)
    label = dict(PRESET_LABELS).get(key, key)
    return render_template("partials/demo_result.html", **ctx, account_id=account_id, preset_label=label,
                           actions=optional_actions(ctx["m"], shock))
