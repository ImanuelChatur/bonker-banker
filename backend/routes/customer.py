"""/customer and /customer/<id>: know the customer."""
from flask import Blueprint, redirect, render_template, request

from engine import customer_metrics, goal_plan, runway
from services import data_store

from ._common import error_html, friendly_errors

bp = Blueprint("customer", __name__)


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
    rows = data_store.account_rows(account_id)[-36:]
    history = {"labels": [r["month"] for r in rows], "yName": "Avg daily balance ($)",
               "series": [{"name": "Balance", "data": [round(float(r["avg_daily_balance"]), 2) for r in rows]}]}
    return render_template("customer.html", m=m, runway=runway(m.buffer, m.income, m.spending),
                           history=history, goal=goal_plan(m), account_id=account_id)
