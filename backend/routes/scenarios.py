"""Saved scenarios: save Shock Lab settings by name, list them per customer, compare 2-3 side by side."""
from flask import Blueprint, render_template, request
from markupsafe import escape

from engine import apply_shock, customer_metrics
from services import saved

from ._common import error_html, friendly_errors, shock_from_form

bp = Blueprint("scenarios", __name__)


def describe(settings: dict) -> str:
    """Plain-English one-liner for a saved shock."""
    s, parts = settings, []
    if "income_pct" in s and float(s["income_pct"]) < 100:
        dur = int(float(s.get("duration_months") or 0))
        parts.append(f"job loss, EI {float(s['income_pct']):g}%" + (f" for {dur} months" if dur else "")
                     + (" (capped)" if s.get("realistic_ei") == "1" else ""))
    if float(s.get("bills_pct") or 0):
        parts.append(f"bills +{float(s['bills_pct']):g}%")
    if float(s.get("one_off_months") or 0):
        n = float(s["one_off_months"])
        parts.append(f"repair costing {n:g} month{'' if n == 1 else 's'} of spending")
    if float(s.get("one_off_cost") or 0):
        parts.append(f"one-off ${float(s['one_off_cost']):,.0f}")
    if float(s.get("extra_spending") or 0):
        parts.append(f"+${float(s['extra_spending']):,.0f}/month")
    if float(s.get("rate_hike_pct") or 0):
        parts.append(f"rates +{float(s['rate_hike_pct']):g} pts")
    text = ", ".join(parts)
    return text[:1].upper() + text[1:] if text else "No shock"   # not .capitalize(): it would lowercase "EI"


def shock_lab_fields(settings: dict) -> dict:
    """Saved settings -> the Shock Lab's slider values (used by /shock?saved=<id>)."""
    out = {k: v for k, v in settings.items()}
    out["job_loss"] = "income_pct" in settings and float(settings["income_pct"]) < 100
    out["realistic_ei"] = settings.get("realistic_ei") == "1"
    return out


@bp.post("/shock/save")
def save_scenario():
    account_id = request.form.get("account_id", "").strip()
    if not account_id:
        return '<span class="text-muted text-sm">Enter an account ID first.</span>'
    settings = saved.clean_settings(request.form)
    name = request.form.get("name", "").strip() or describe(settings)
    saved.save(account_id, name, settings)
    return (f'<span class="text-sm">Saved "{escape(name)}". '
            f'<a class="link" href="/customer/{escape(account_id)}#saved">Compare on the customer page</a></span>')


@bp.post("/scenarios/<int:scenario_id>/delete")
def delete_scenario(scenario_id):
    saved.delete(scenario_id, request.form.get("account_id", ""))
    return ""


@bp.get("/customer/<account_id>/compare")
@friendly_errors(error_html)
def compare(account_id):
    ids = [int(i) for i in request.args.getlist("ids") if i.isdigit()][:3]
    m = customer_metrics(account_id)
    cols = []
    for sc in saved.get(ids, account_id):
        res = apply_shock(m, shock_from_form(sc["settings"]))
        cols.append({**sc, "res": res, "summary": describe(sc["settings"])})
    return render_template("compare.html", account_id=account_id, m=m, cols=cols)
