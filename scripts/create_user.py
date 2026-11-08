"""Manage login accounts (invite-only; there is no public sign-up page).

Run from the repo root:
  python scripts/create_user.py add <username>        # asks for the password twice (not echoed)
  python scripts/create_user.py password <username>   # change a password
  python scripts/create_user.py remove <username>
  python scripts/create_user.py list
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from services import users  # noqa: E402


def _ask() -> str:
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Repeat password: "):
        raise ValueError("Passwords don't match.")
    return pw


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("add", "password", "remove", "list") or (argv[0] != "list" and len(argv) != 2):
        print(__doc__)
        return 2
    cmd = argv[0]
    try:
        if cmd == "list":
            print("\n".join(users.list_users()) or "(no users yet)")
        elif cmd == "add":
            users.create_user(argv[1], _ask())
            print(f"Created '{argv[1]}'.")
        elif cmd == "password":
            users.set_password(argv[1], _ask())
            print(f"Password changed for '{argv[1]}'.")
        elif cmd == "remove":
            print(f"Removed '{argv[1]}'." if users.delete_user(argv[1]) else f"No user '{argv[1]}'.")
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
