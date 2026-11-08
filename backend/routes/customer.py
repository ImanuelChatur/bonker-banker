"""/customer and /customer/<id>: know the customer."""
from flask import Blueprint, redirect, render_template, request

from engine import Shock, apply_shock, customer_metrics, goal_plan, runway
from engine.spending import CATEGORY_LABELS
from services import data_store

from ._common import error_html, friendly_errors
from ._placeholders import engine_fn

bp = Blueprint("customer", __name__)


OUT_CATEGORIES = ["household_bills", "insurance", "loan_payments", "card_withdrawals",
                  "cash_withdrawals_genuine", "transfers_out_other", "bank_fees"]


def spending_mix(rows: list[dict], months: int = 12) -> dict:
    """Donut data: average monthly money out per category over the last `months` rows."""
    recent = rows[-months:]
    avg = {c: sum(float(r.get(c) or 0) for r in recent) / max(len(recent), 1) for c in OUT_CATEGORIES}
    total = sum(avg.values())
    items = sorted(({"name": CATEGORY_LABELS.get(c, c), "value": round(v, 2)} for c, v in avg.items() if v >= 1),
                   key=lambda i: -i["value"])
    return {"kind": "donut", "center": f"${total:,.0f}/mo", "items": items, "months": len(recent)}


def profile_and_peers(account_id) -> dict:
    """customer_profile + peer_benchmarks (ClaudeOne's engine, or labelled placeholders until they land)."""
    out = {}
    for key, module, name in (("profile", "profile", "customer_profile"), ("bench", "benchmarks", "peer_benchmarks")):
        try:
            out[key] = engine_fn(module, name)(account_id)
        except KeyError:
            out[key] = None
    return out


def optional_extras(account_id, m) -> dict:
    """Resilience score and peer comparison, when the engine provides them (ClaudeOne's work)."""
    out = {}
    try:
        from engine import resilience_score
        out["score"] = resilience_score(m)
    except ImportError:
        pass
    try:
        from engine import peer_percentile
        out["peer"] = peer_percentile(account_id)
    except ImportError:
        pass
    return out


@bp.get("/customer")
def lookup():
    account_id = request.args.get("account_id", "").strip()
    if account_id:
        return redirect(f"/customer/{account_id}")
    return render_template("customer.html", m=None)


@bp.get("/customer/<account_id>")
@friendly_errors(error_html)
def show(account_id):
    m = customer_metrics(account_id)
    all_rows = data_store.account_rows(account_id)
    rows = all_rows[-36:]
    history = {"labels": [r["month"] for r in rows], "yName": "Avg daily balance ($)",
               "series": [{"name": "Balance", "data": [round(float(r["avg_daily_balance"]), 2) for r in rows]}]}
    job_loss = apply_shock(m, Shock(income_factor=0.55, duration_months=6))   # the standard job-loss twist
    return render_template("customer.html", m=m, runway=runway(m.buffer, m.income, m.spending), job_loss=job_loss,
                           no_income_runway=runway(m.buffer, 0.0, m.spending),
                           surplus=m.income - m.spending, mix=spending_mix(all_rows),
                           history=history, goal=goal_plan(m), account_id=account_id,
                           saved_scenarios=_saved(account_id), sim=_simulated(account_id),
                           **optional_extras(account_id, m), **profile_and_peers(account_id))


def _simulated(account_id) -> dict | None:
    """Monte Carlo runway (ClaudeOne's engine.simulate); the page works without it."""
    try:
        from engine.simulate import simulate_runway
        return simulate_runway(account_id)
    except (ImportError, KeyError):
        return None


def _saved(account_id) -> list[dict]:
    from services import saved
    from .scenarios import describe
    return [{**s, "summary": describe(s["settings"])} for s in saved.list_for(account_id)]
