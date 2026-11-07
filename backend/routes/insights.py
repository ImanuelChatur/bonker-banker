"""/insights: population-level view (runway vs loan default)."""
from flask import Blueprint, render_template

from engine import risk

from ._common import error_html, friendly_errors

bp = Blueprint("insights", __name__)


@bp.get("/insights")
@friendly_errors(error_html)
def page():
    rows = risk.default_rate_by_runway()
    chart = {"labels": [r["bucket"] for r in rows], "yName": "Default rate (%)",
             "series": [{"name": "Loans in default", "data": [r["rate"] or 0 for r in rows]}]}
    return render_template("insights.html", o=risk.overview(), rows=rows, chart=chart)
