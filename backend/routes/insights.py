"""/insights: the biggest finding across the whole dataset (resilience grade vs real loan defaults)."""
import logging

from flask import Blueprint, render_template

from engine.findings import biggest_finding
from engine.regions import region_summary

from ._common import error_html, friendly_errors

bp = Blueprint("insights", __name__)
log = logging.getLogger(__name__)


@bp.get("/insights")
@friendly_errors(error_html)
def page():
    f = biggest_finding()
    max_rate = max([r["rate"] or 0 for r in f["default_by_grade"] + f["default_by_runway"]] + [1])
    return render_template("insights.html", f=f, max_rate=max_rate, regions=_regions())


def _regions():
    """Regional section is optional: skip it if accounts/districts data hasn't been processed."""
    try:
        return region_summary()
    except (FileNotFoundError, KeyError) as e:
        log.warning("Regional view skipped (%s). Run: python scripts/precompute.py", e)
        return None
