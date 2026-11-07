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


def gemini_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or None


def gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
