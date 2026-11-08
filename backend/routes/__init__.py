"""Registers every blueprint, so app.py only needs one call: register_routes(app)."""
import config
from services import data_store


def _money(v) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "n/a"
    if x != x or x in (float("inf"), float("-inf")):   # NaN / infinity: never print "$nan"
        return "n/a"
    s = f"${abs(x):,.0f}"
    return f"−{s}" if round(x) < 0 else s              # "−$2,513", not "$-2,513"


def _months(v) -> str:
    return f"{v:g} months" if isinstance(v, (int, float)) else str(v)


def _runway_num(v) -> str:
    """Big display number: 4.3 -> '4.3', 'no shortfall (120+)' -> '120+'."""
    if isinstance(v, (int, float)):
        return "120+" if v >= 120 else f"{v:g}"   # 120 is the formula's cap, so show it as "120+"
    return "120+"


def _runway_class(v) -> str:
    """Colour for a runway value, using the bands from /insights (pre-loan default rates 44% / 21% / 9%):
    good = 12+ months or no shortfall, warn = 3 to 12 months, bad = under 3 months."""
    if not isinstance(v, (int, float)):
        return "good"
    return "good" if v >= 12 else "warn" if v >= 3 else "bad"


def register_routes(app):
    app.config.setdefault("MAX_CONTENT_LENGTH", config.MAX_UPLOAD_BYTES)
    if config.behind_proxy():  # real visitor address for login lockouts and sign-up limits
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    from .auth import init_auth
    init_auth(app)             # login required on every page (BB_AUTH=off disables it); see routes/auth.py
    app.jinja_env.filters["money"] = _money
    app.jinja_env.filters["months"] = _months
    app.jinja_env.filters["runway_num"] = _runway_num
    app.jinja_env.filters["runway_class"] = _runway_class
    if data_store.load():      # once at startup; logs a warning if scripts/precompute.py hasn't been run
        from engine import risk
        risk.warm_up()         # builds the peer-comparison table in the background (about 4 seconds)

    _register_error_pages(app)

    from . import assistant, customer, demo, insights, plans, report, scenarios, shocks, sources, uploads
    for module in (customer, shocks, plans, insights, uploads, assistant, report, sources, demo, scenarios):
        app.register_blueprint(module.bp)


def _register_error_pages(app):
    """Friendly pages instead of the default 'Not Found' text or a stack trace."""
    import logging

    from werkzeug.exceptions import HTTPException

    from ._common import error_response

    @app.errorhandler(404)
    def not_found(e):
        return error_response("We couldn't find that page",
                              "The link may be out of date. Look up an account, or start with a sample:", 404, samples=True)

    @app.errorhandler(413)
    def too_large(e):
        return error_response("That upload is too large",
                              f"Upload at most {config.MAX_FILES} statements of up to "
                              f"{config.MAX_FILE_BYTES // (1024 * 1024)} MB each.", 413)

    @app.errorhandler(Exception)
    def unexpected(e):
        if isinstance(e, HTTPException):          # 400, 401, 405...: keep Flask's own response
            return e
        logging.getLogger(__name__).exception("Unhandled error")
        return error_response("Something went wrong on our side",
                              "Try again, or go back and pick another account. The details are in the server log.", 500)
