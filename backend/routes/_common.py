"""Helpers shared by the route modules (form parsing, scenario building, friendly errors)."""
from __future__ import annotations

from functools import wraps

from engine import Shock, apply_shock, backup_plan, customer_metrics, goal_plan, projection
from services.data_store import DataNotReady


def num(form, name: str, default: float = 0.0, lo: float | None = None, hi: float | None = None) -> float:
    try:
        v = float(str(form.get(name, "")).replace(",", "").strip() or default)
    except ValueError:
        v = default
    if lo is not None:
        v = max(v, lo)
    if hi is not None:
        v = min(v, hi)
    return v


def shock_from_form(form) -> Shock:
    """Form uses percentages (55 = 55%); the engine uses fractions."""
    dur = num(form, "duration_months", 0, 0, 120)
    return Shock(
        income_factor=num(form, "income_pct", 100, 0, 200) / 100,
        household_bills_pct=num(form, "bills_pct", 0, -50, 300) / 100,
        extra_monthly_spending=num(form, "extra_spending", 0, 0),
        one_off_cost=num(form, "one_off_cost", 0, 0),
        one_off_months_of_spending=num(form, "one_off_months", 0, 0, 24),
        duration_months=int(dur) or None,
        rate_hike_pct=num(form, "rate_hike_pct", 0, 0, 10),
        realistic_ei=str(form.get("realistic_ei", "")).strip() in ("1", "true", "on"),
    )


def _chart(m, res) -> dict:
    a = res["after"]
    before = projection(m.buffer, m.income, m.spending)
    after = projection(m.buffer, a["income"], a["spending"], a["one_off_cost"])
    nonzero = [i for series in (before, after) for i, v in enumerate(series) if v > 0]
    n = min((max(nonzero) if nonzero else 0) + 2, len(before))   # stop shortly after the buffer hits zero
    return {"labels": ["Now"] + [f"M{i}" for i in range(1, n)], "yName": "Buffer ($)",
            "series": [{"name": "Typical", "data": before[:n], "color": "#94a3b8", "smooth": False},
                       {"name": "After shock", "data": after[:n], "color": "#dc2626", "smooth": False}]}


def build_scenario(account_id: str, shock: Shock, goal_months: float = 3.0, target_runway: float = 6.0,
                   metrics=None) -> dict:
    m = metrics or customer_metrics(account_id)
    res = apply_shock(m, shock)
    return {"m": m, "res": res, "chart": _chart(m, res), "goal": goal_plan(m, goal_months),
            "backup": backup_plan(m, shock, target_runway), "shock": shock}


def _account_asked() -> str:
    from flask import request
    return str((request.view_args or {}).get("account_id") or request.values.get("account_id") or "").strip()


def error_response(title: str, msg: str, status: int, samples: bool = False):
    """A full page (with the nav) for normal page loads; a notice card for HTMX swaps and form posts."""
    from flask import render_template, request
    full = request.method == "GET" and not request.headers.get("HX-Request")
    tpl = "error.html" if full else "partials/notice.html"
    return render_template(tpl, title=title, msg=msg, samples=samples, is_error=status >= 500), status


def friendly_errors(render_error):
    """Decorator: turn missing data / unknown account into a readable message instead of a 500."""
    def deco(fn):
        @wraps(fn)
        def inner(*a, **kw):
            try:
                return fn(*a, **kw)
            except DataNotReady as e:
                return error_response("The data isn't ready yet",
                                      f"{e} Ask whoever runs this site to run scripts/precompute.py, then reload.", 503)
            except KeyError as e:
                asked = _account_asked()
                if asked:
                    hint = ("Account IDs are numbers, like 20111." if not asked.isdigit()
                            else "Check the number, or start with one of these:")
                    return error_response(f"We couldn't find account {asked}", hint, 404, samples=True)
                return error_response("Something is missing", f"Not found: {e.args[0] if e.args else e}", 404)
        return inner
    return deco


def error_html(msg: str) -> str:
    from markupsafe import escape
    return f'<div class="notice" role="alert"><p>{escape(msg)}</p></div>'
