"""Paths and environment settings. Secrets come from .env (gitignored); see .env.example."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_RAW = ROOT / "data" / "raw"              # provided CSVs (gitignored, too big for GitHub)
DATA_PROCESSED = ROOT / "data" / "processed"  # Parquet written by scripts/precompute.py (gitignored)
UPLOAD_DIR = ROOT / "uploads"                 # ledger.db lives here (gitignored)

MAX_FILES = 10                                    # statements per upload
MAX_FILE_BYTES = 15 * 1024 * 1024                 # per statement
MAX_UPLOAD_BYTES = MAX_FILES * MAX_FILE_BYTES + 1024 * 1024   # whole request (Flask MAX_CONTENT_LENGTH)


USERS_DB = Path(os.environ.get("BB_USERS_DB") or UPLOAD_DIR / "users.db")   # login accounts (gitignored)


def secret_key() -> str:
    """Signs the session cookie. Set BB_SECRET_KEY in .env before hosting; without it a random key is used,
    so everyone is logged out whenever the server restarts."""
    key = os.environ.get("BB_SECRET_KEY")
    if key:
        return key
    import logging
    import secrets
    logging.getLogger(__name__).warning("BB_SECRET_KEY not set: using a random key (sessions end on restart)")
    return secrets.token_hex(32)


def auth_required() -> bool:
    """Login is on by default. BB_AUTH=off disables it (local development and the test suite)."""
    return os.environ.get("BB_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")


def registration_open() -> bool:
    """Anyone can create an account at /register. BB_REGISTRATION=off closes sign-up (accounts then only via the script)."""
    return os.environ.get("BB_REGISTRATION", "on").strip().lower() not in ("off", "0", "false", "no")


def cookie_secure() -> bool:
    """Send the session cookie over HTTPS only. Turn on (BB_COOKIE_SECURE=1) once the site is served over HTTPS."""
    return os.environ.get("BB_COOKIE_SECURE", "0").strip().lower() in ("1", "true", "on", "yes")


def gemini_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or None


def gemini_models() -> list[str]:
    """Models to try in order. GEMINI_MODEL may list several, comma-separated; the next one is tried when one
    is busy or retired. Pinned names, not "-latest" aliases, which can jump to a brand-new, overloaded model."""
    raw = os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash,gemini-3.5-flash-lite"
    return [m.strip() for m in raw.split(",") if m.strip()]
