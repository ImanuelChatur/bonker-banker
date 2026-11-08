"""Login, logout and the guard that keeps every page behind a login.

- Anyone can create an account at /register (BB_REGISTRATION=off closes it). Sign-ups are limited to 5 per address
  per hour; the new account is logged in straight away.
- Every request needs a logged-in session except /login, /register and /static/*. Plain page requests are redirected to /login
  (and come back afterwards); HTMX requests get 401 with HX-Redirect so the whole page goes to /login.
- Session cookie: signed with BB_SECRET_KEY, HttpOnly, SameSite=Lax, Secure when BB_COOKIE_SECURE=1, lasts 12 hours.
- The login and logout forms carry a CSRF token. Other forms are covered by SameSite=Lax (browsers don't send the
  cookie on cross-site POSTs).
- 5 wrong passwords for the same username from the same address within 5 minutes locks that pair for 5 minutes.
- The session is cleared on login (no session fixation). Usernames that don't exist cost the same time as wrong passwords.
Turn the whole thing off with BB_AUTH=off (local development, test suite).
"""
from __future__ import annotations

import secrets
import time
from datetime import timedelta
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for

import config
from services import users

bp = Blueprint("auth", __name__)

MAX_FAILURES, WINDOW_S, LOCK_S = 5, 300, 300
_failures: dict[tuple[str, str], list[float]] = {}
MAX_SIGNUPS_PER_HOUR = 5                      # per address, so one visitor can't mass-create accounts
_signups: dict[str, list[float]] = {}
OPEN_ENDPOINTS = {"auth.login", "auth.register", "static"}


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def _check_csrf() -> None:
    sent = request.form.get("csrf", "")
    if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
        abort(400, "Invalid or missing form token. Reload the page and try again.")


def _safe_next(target: str | None) -> str:
    """Only same-site relative paths, so /login?next= can't bounce people to another website."""
    if not target:
        return "/"
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return "/"
    return target


def _locked(key: tuple[str, str]) -> bool:
    now = time.time()
    recent = [t for t in _failures.get(key, []) if now - t < WINDOW_S]
    _failures[key] = recent
    return len(recent) >= MAX_FAILURES and now - recent[-1] < LOCK_S


def current_user() -> str | None:
    return session.get("user")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if not current_app.config.get("AUTH_REQUIRED", True):
        return redirect("/")
    error, username = None, ""
    if request.method == "POST":
        _check_csrf()
        username = request.form.get("username", "").strip()[:64]
        password = request.form.get("password", "")[:256]
        key = (request.remote_addr or "?", username.lower())
        if _locked(key):
            error = "Too many attempts. Wait 5 minutes and try again."
        else:
            user = users.verify(username, password, current_app.config.get("USERS_DB"))
            if user:
                _failures.pop(key, None)
                nxt = _safe_next(request.form.get("next"))
                _start_session(user)
                return redirect(nxt)
            _failures.setdefault(key, []).append(time.time())
            error = "Wrong username or password."
    return render_template("login.html", error=error, username=username,
                           next=_safe_next(request.values.get("next")),
                           no_users=users.user_count(current_app.config.get("USERS_DB")) == 0,
                           registration_open=current_app.config.get("REGISTRATION_OPEN", True))


def _start_session(user: str) -> None:
    session.clear()                                  # fresh session: no fixation
    session.permanent = True
    session["user"] = user
    csrf_token()


@bp.route("/register", methods=["GET", "POST"])
def register():
    if not current_app.config.get("AUTH_REQUIRED", True):
        return redirect("/")
    if not current_app.config.get("REGISTRATION_OPEN", True):
        abort(404)
    error, username = None, ""
    if request.method == "POST":
        _check_csrf()
        username = request.form.get("username", "").strip()[:64]
        password = request.form.get("password", "")[:256]
        ip = request.remote_addr or "?"
        now = time.time()
        recent = [t for t in _signups.get(ip, []) if now - t < 3600]
        _signups[ip] = recent
        if len(recent) >= MAX_SIGNUPS_PER_HOUR:
            error = "Too many new accounts from this connection. Try again in an hour."
        elif password != request.form.get("password2", ""):
            error = "The two passwords don't match."
        else:
            try:
                users.create_user(username, password, current_app.config.get("USERS_DB"))
            except ValueError as e:
                error = str(e)
            else:
                recent.append(now)
                _start_session(users.verify(username, password, current_app.config.get("USERS_DB")) or username)
                return redirect(_safe_next(request.form.get("next")))
    return render_template("register.html", error=error, username=username,
                           next=_safe_next(request.values.get("next")), min_password=users.MIN_PASSWORD)


@bp.post("/logout")
def logout():
    _check_csrf()
    session.clear()
    return redirect(url_for("auth.login"))


def init_auth(app) -> None:
    """Call once from register_routes: session settings, the guard, and template helpers."""
    app.secret_key = app.config.get("SECRET_KEY") or config.secret_key()
    app.config.setdefault("AUTH_REQUIRED", config.auth_required())
    app.config.setdefault("USERS_DB", config.USERS_DB)
    app.config.setdefault("REGISTRATION_OPEN", config.registration_open())
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=config.cookie_secure(), PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
    app.register_blueprint(bp)

    @app.before_request
    def require_login():
        if not app.config.get("AUTH_REQUIRED") or request.endpoint in OPEN_ENDPOINTS or current_user():
            return None
        if request.headers.get("HX-Request"):
            return "", 401, {"HX-Redirect": url_for("auth.login")}
        nxt = request.full_path if request.query_string else request.path
        return redirect(url_for("auth.login", next=nxt))

    @app.context_processor
    def auth_context():
        return {"current_user": current_user(), "auth_required": app.config.get("AUTH_REQUIRED"),
                "csrf_token": csrf_token}
