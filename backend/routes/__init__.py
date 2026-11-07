"""Registers every blueprint, so app.py only needs one call: register_routes(app)."""
import config
from services import data_store


def _money(v) -> str:
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return "n/a"


def _months(v) -> str:
    return f"{v:g} months" if isinstance(v, (int, float)) else str(v)


def _runway_num(v) -> str:
    """Big display number: 4.3 -> '4.3', 'no shortfall (120+)' -> '120+'."""
    return f"{v:g}" if isinstance(v, (int, float)) else "120+"


def _runway_class(v) -> str:
    """Colour for a runway value: good (6+ months or no shortfall), warn (1-6), bad (<1)."""
    if not isinstance(v, (int, float)):
        return "good"
    return "good" if v >= 6 else "warn" if v >= 1 else "bad"


def register_routes(app):
    app.config.setdefault("MAX_CONTENT_LENGTH", config.MAX_UPLOAD_BYTES)
    app.jinja_env.filters["money"] = _money
    app.jinja_env.filters["months"] = _months
    app.jinja_env.filters["runway_num"] = _runway_num
    app.jinja_env.filters["runway_class"] = _runway_class
    if data_store.load():      # once at startup; logs a warning if scripts/precompute.py hasn't been run
        from engine import risk
        risk.warm_up()         # builds the peer-comparison table in the background (about 4 seconds)

    from . import assistant, customer, insights, plans, report, shocks, sources, uploads
    for module in (customer, shocks, plans, insights, uploads, assistant, report, sources):
        app.register_blueprint(module.bp)
