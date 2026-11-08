"""/insights: every shock across all accounts, who is hit hardest, who to call, and what predicts default."""
import logging

from flask import Blueprint, render_template, request

from engine.findings import biggest_finding
from engine.regions import region_summary

from ._common import error_html, friendly_errors
from ._placeholders import engine_fn

bp = Blueprint("insights", __name__)
log = logging.getLogger(__name__)

REPAIRS = [(0, "No repair"), (1, "Repair = 1 month of spending"), (2, "Repair = 2 months")]
BREAKDOWN_LABELS = {"age_band": "Age", "household_size": "People on the account", "region": "Region",
                    "income_band": "Monthly income"}


def heatmap(one_off: int) -> dict:
    """EI % (x) by bills % (y), colour = % of accounts out of savings within 6 months."""
    rows = [r for r in engine_fn("insights", "stress_grid")() if r["one_off_months"] == one_off]
    xs = sorted({r["ei_pct"] for r in rows})
    ys = sorted({r["bills_pct"] for r in rows})
    return {"kind": "heatmap", "xName": "Income on EI", "yName": "Bills up",
            "xLabels": [f"{x}%" for x in xs], "yLabels": [f"+{y}%" for y in ys],
            "data": [[xs.index(r["ei_pct"]), ys.index(r["bills_pct"]), r["pct_runout_6m"]] for r in rows],
            "placeholder": any(r.get("_placeholder") for r in rows)}


def breakdowns(scenario: dict) -> list[dict]:
    """[{label, rows: [{group, pct_runout_6m, n}]}] for the headline scenario."""
    rows = engine_fn("insights", "stress_breakdown")(scenario.get("ei_pct", 55), scenario.get("bills_pct", 15),
                                                      scenario.get("one_off_months", 0))
    out = []
    for key, label in BREAKDOWN_LABELS.items():
        grp = [r for r in rows if r["group_type"] == key]
        if grp:
            out.append({"label": label, "rows": grp})
    return out


def _regions():
    """Regional section is optional: skip it if accounts/districts data hasn't been processed."""
    try:
        return region_summary()
    except (FileNotFoundError, KeyError) as e:
        log.warning("Regional view skipped (%s). Run: python scripts/precompute.py", e)
        return None


@bp.get("/insights")
@friendly_errors(error_html)
def page():
    f = biggest_finding()
    max_rate = max([r["rate"] or 0 for r in f["default_by_grade"] + f["default_by_runway"]] + [1])
    head = engine_fn("insights", "headline")()
    scenario = head.get("scenario") if isinstance(head.get("scenario"), dict) else {}
    return render_template("insights.html", f=f, max_rate=max_rate, regions=_regions(), head=head,
                           heat=heatmap(0), repairs=REPAIRS, one_off=0, groups=breakdowns(scenario),
                           at_risk=engine_fn("insights", "at_risk_customers")(50))


@bp.get("/insights/heatmap")
@friendly_errors(error_html)
def heatmap_partial():
    one_off = int(request.args.get("one_off", 0)) if request.args.get("one_off", "0").isdigit() else 0
    one_off = one_off if one_off in dict(REPAIRS) else 0
    return render_template("partials/heatmap.html", heat=heatmap(one_off), repairs=REPAIRS, one_off=one_off)
