"""/assistant/twist: turn a judge's twist card (plain English) into shock settings, then run it."""
import json

from flask import Blueprint, make_response, render_template, request

from engine import Shock
from services import llm

from ._common import build_scenario, error_html, friendly_errors

bp = Blueprint("assistant", __name__)

SCHEMA = {"type": "OBJECT", "properties": {
    "income_pct": {"type": "NUMBER"}, "bills_pct": {"type": "NUMBER"}, "extra_spending": {"type": "NUMBER"},
    "one_off_cost": {"type": "NUMBER"}, "one_off_months": {"type": "NUMBER"}, "duration_months": {"type": "NUMBER"},
    "rate_hike_pct": {"type": "NUMBER"}, "realistic_ei": {"type": "BOOLEAN"}}}

PROMPT = (
    "Convert this financial 'twist card' into shock settings. Return JSON with:\n"
    "income_pct (100 = unchanged; EI at 55% pays 55), bills_pct (+15 = household bills up 15%),\n"
    "extra_spending (extra dollars per month), one_off_cost (dollars), one_off_months (a one-off cost "
    "sized as N months of the customer's typical spending), duration_months (how long the income change "
    "lasts, 0 if permanent/not stated), rate_hike_pct (percentage points interest rates go up, e.g. "
    "'rates go up 1%' -> 1), realistic_ei (true only if the card mentions the EI maximum or a capped benefit). "
    "Use 0 or false for anything not mentioned; income_pct defaults to 100.\n\n"
    "TWIST CARD:\n")


@bp.post("/assistant/twist")
@friendly_errors(error_html)
def twist():
    account_id = request.form.get("account_id", "").strip()
    text = request.form.get("twist", "").strip()[:1000]
    if not text:
        return error_html("Type a shock in your own words first, e.g. \"They lose their job and bills go up 15%.\""), 400
    try:
        s = llm.generate_json(PROMPT + text, SCHEMA)
        if not isinstance(s, dict):
            raise ValueError("unexpected reply")
    except (ValueError, KeyError, IndexError, TypeError, OSError) as e:   # timeout, bad JSON, odd reply
        return error_html("The assistant couldn't read that card just now. The common shocks and sliders do the same "
                          f"job: pick one, or set the sliders to match the card. ({type(e).__name__})"), 503
    except llm.LLMUnavailable as e:
        return error_html(f"The assistant isn't available right now ({e}). The common shocks and sliders do the same "
                          "job: pick one, or set the sliders to match the card."), 503
    shock = Shock(
        income_factor=min(max(float(s.get("income_pct", 100)), 0), 200) / 100,
        household_bills_pct=min(max(float(s.get("bills_pct", 0)), -50), 300) / 100,
        extra_monthly_spending=max(float(s.get("extra_spending", 0)), 0),
        one_off_cost=max(float(s.get("one_off_cost", 0)), 0),
        one_off_months_of_spending=min(max(float(s.get("one_off_months", 0)), 0), 24),
        duration_months=int(min(max(float(s.get("duration_months", 0)), 0), 120)) or None,
        rate_hike_pct=min(max(float(s.get("rate_hike_pct", 0) or 0), 0), 10),
        realistic_ei=bool(s.get("realistic_ei", False)))
    ctx = build_scenario(account_id, shock)
    resp = make_response(render_template("partials/scenario_result.html", **ctx, show_plan=True, twist=text))
    # Tell the Shock Lab page what was parsed so its sliders move to match (see static/js/shock_lab.js).
    sliders = {
        "job_loss": shock.income_factor < 1,
        "income_pct": round(shock.income_factor * 100),
        "duration_months": shock.duration_months or 0,
        "bills_pct": round(shock.household_bills_pct * 100),
        "one_off_months": shock.one_off_months_of_spending,
        "one_off_cost": shock.one_off_cost,
        "extra_spending": shock.extra_monthly_spending,
        "rate_hike_pct": shock.rate_hike_pct,
        "realistic_ei": shock.realistic_ei,
    }
    resp.headers["HX-Trigger"] = json.dumps({"twistParsed": sliders})
    return resp
