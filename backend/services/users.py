"""Login accounts: a tiny SQLite table of usernames and password hashes (uploads/users.db, never committed).

Anyone can sign up at /register; accounts can also be managed with  python scripts/create_user.py
Passwords are stored only as salted hashes (werkzeug's default scrypt), never in plain text.
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

import config

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD = 10

# Hash used to keep "unknown user" as slow as "wrong password", so timing doesn't reveal which usernames exist.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _db(path: Path | None = None) -> sqlite3.Connection:
    p = path or config.USERS_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY COLLATE NOCASE, "
                "password_hash TEXT NOT NULL, created REAL NOT NULL)")
    return con


def validate(username: str, password: str) -> str | None:
    """None if acceptable, else a message saying what's wrong."""
    if not USERNAME_RE.match(username or ""):
        return "Username must be 3 to 32 letters, digits, dots, dashes or underscores."
    if len(password or "") < MIN_PASSWORD:
        return f"Password must be at least {MIN_PASSWORD} characters."
    return None


def create_user(username: str, password: str, path: Path | None = None) -> None:
    problem = validate(username, password)
    if problem:
        raise ValueError(problem)
    with _db(path) as con:
        try:
            con.execute("INSERT INTO users VALUES (?, ?, ?)", (username, generate_password_hash(password), time.time()))
        except sqlite3.IntegrityError:
            raise ValueError(f"User '{username}' already exists.") from None


def set_password(username: str, password: str, path: Path | None = None) -> None:
    problem = validate(username, password)
    if problem:
        raise ValueError(problem)
    with _db(path) as con:
        if con.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                       (generate_password_hash(password), username)).rowcount == 0:
            raise ValueError(f"No user '{username}'.")


def delete_user(username: str, path: Path | None = None) -> bool:
    with _db(path) as con:
        return con.execute("DELETE FROM users WHERE username = ?", (username,)).rowcount > 0


def verify(username: str, password: str, path: Path | None = None) -> str | None:
    """The stored username (canonical case) if the password is right, else None."""
    with _db(path) as con:
        row = con.execute("SELECT username, password_hash FROM users WHERE username = ?", (username or "",)).fetchone()
    if row is None:
        check_password_hash(_DUMMY_HASH, password or "")
        return None
    return row[0] if check_password_hash(row[1], password or "") else None


def user_count(path: Path | None = None) -> int:
    with _db(path) as con:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def list_users(path: Path | None = None) -> list[str]:
    with _db(path) as con:
        return [r[0] for r in con.execute("SELECT username FROM users ORDER BY username")]
