"""Saved scenarios: named Shock Lab settings per account, stored in SQLite (uploads/saved.db, gitignored).

Settings are kept as the Shock Lab's own form fields, so routes rebuild the shock with shock_from_form().
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import config

_lock = threading.Lock()
FIELDS = ("income_pct", "duration_months", "bills_pct", "one_off_months", "one_off_cost", "extra_spending",
          "rate_hike_pct", "realistic_ei")
MAX_PER_ACCOUNT = 20


def _db(path: Path | None = None) -> sqlite3.Connection:
    path = path or (config.UPLOAD_DIR / "saved.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL, name TEXT NOT NULL,
        settings TEXT NOT NULL, created_at TEXT NOT NULL)""")
    return con


@contextmanager
def _conn():
    """Open, commit on success, always close (Windows keeps the file locked otherwise)."""
    con = _db()
    try:
        with con:
            yield con
    finally:
        con.close()


def clean_settings(form) -> dict:
    """Only the known shock fields, as strings (what shock_from_form expects)."""
    return {k: str(form.get(k)).strip()[:20] for k in FIELDS if form.get(k) not in (None, "")}


def save(account_id: str, name: str, settings: dict) -> int:
    name = (name or "").strip()[:60] or "Untitled scenario"
    with _lock, _conn() as con:
        cur = con.execute("INSERT INTO scenarios (account_id, name, settings, created_at) VALUES (?, ?, ?, ?)",
                          (str(account_id), name, json.dumps(settings),
                           datetime.now(timezone.utc).isoformat(timespec="seconds")))
        # Keep the list short: drop the oldest beyond the cap.
        con.execute("""DELETE FROM scenarios WHERE account_id = ? AND id NOT IN (
                       SELECT id FROM scenarios WHERE account_id = ? ORDER BY id DESC LIMIT ?)""",
                    (str(account_id), str(account_id), MAX_PER_ACCOUNT))
        return cur.lastrowid


def _row(r) -> dict:
    return {"id": r["id"], "account_id": r["account_id"], "name": r["name"],
            "settings": json.loads(r["settings"]), "created_at": r["created_at"]}


def list_for(account_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM scenarios WHERE account_id = ? ORDER BY id DESC", (str(account_id),))
        return [_row(r) for r in rows]


def get(ids: list[int], account_id: str) -> list[dict]:
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    with _conn() as con:
        rows = con.execute(f"SELECT * FROM scenarios WHERE account_id = ? AND id IN ({marks}) ORDER BY id",
                           (str(account_id), *ids))
        return [_row(r) for r in rows]


def delete(scenario_id: int, account_id: str) -> None:
    with _lock, _conn() as con:
        con.execute("DELETE FROM scenarios WHERE id = ? AND account_id = ?", (scenario_id, str(account_id)))
