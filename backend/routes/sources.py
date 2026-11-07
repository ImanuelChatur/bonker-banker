"""/sources: data sources and credits (datathon rule: credit every outside source)."""
from flask import Blueprint, render_template

from engine.sources import SOURCES

bp = Blueprint("sources", __name__)


@bp.get("/sources")
def page():
    return render_template("sources.html", sources=SOURCES)
