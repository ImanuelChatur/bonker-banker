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


def register_routes(app):
    app.config.setdefault("MAX_CONTENT_LENGTH", config.MAX_UPLOAD_BYTES)
    app.jinja_env.filters["money"] = _money
    app.jinja_env.filters["months"] = _months
    data_store.load()          # once at startup; logs a warning if scripts/precompute.py hasn't been run

    from . import assistant, customer, plans, shocks, uploads
    for module in (customer, shocks, plans, uploads, assistant):
        app.register_blueprint(module.bp)
