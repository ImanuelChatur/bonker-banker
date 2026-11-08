import re

import pytest

from routes import auth as auth_module
from services import users


@pytest.fixture()
def app(tmp_path):
    from app import create_app
    a = create_app()
    a.config.update(AUTH_REQUIRED=True, USERS_DB=tmp_path / "users.db", TESTING=True)
    users.create_user("alice", "correct horse battery", tmp_path / "users.db")
    auth_module._failures.clear()
    return a


def token(client, path="/login"):
    return re.search(r'name="csrf" value="([^"]+)"', client.get(path).data.decode()).group(1)


def login(client, username="alice", password="correct horse battery", nxt="/"):
    return client.post("/login", data={"csrf": token(client), "username": username, "password": password, "next": nxt})


def test_pages_require_login(app):
    c = app.test_client()
    r = c.get("/customer/20111")
    assert r.status_code == 302 and "/login?next=/customer/20111" in r.headers["Location"]
    assert c.get("/login").status_code == 200
    htmx = c.post("/shock/run", data={"account_id": "20111"}, headers={"HX-Request": "true"})
    assert htmx.status_code == 401 and htmx.headers["HX-Redirect"] == "/login"


def test_login_success_returns_to_next_and_logout(app):
    c = app.test_client()
    r = login(c, nxt="/insights")
    assert r.status_code == 302 and r.headers["Location"] == "/insights"
    assert c.get("/").status_code == 200
    page = c.get("/").data.decode()
    assert "Log out" in page
    out = c.post("/logout", data={"csrf": re.search(r'name="csrf" value="([^"]+)"', page).group(1)})
    assert out.status_code == 302 and c.get("/").status_code == 302          # logged out again


def test_wrong_password_and_unknown_user(app):
    c = app.test_client()
    assert "Wrong username or password." in login(c, password="nope nope nope").data.decode()
    assert "Wrong username or password." in login(c, username="mallory").data.decode()
    assert c.get("/").status_code == 302


def test_lockout_after_five_failures(app):
    c = app.test_client()
    for _ in range(5):
        login(c, password="wrong password!")
    r = login(c)                                                    # right password, but locked out
    assert "Too many attempts" in r.data.decode() and c.get("/").status_code == 302


def test_csrf_required(app):
    c = app.test_client()
    c.get("/login")
    r = c.post("/login", data={"username": "alice", "password": "correct horse battery"})
    assert r.status_code == 400


@pytest.mark.parametrize("bad", ["https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)"])
def test_next_cannot_leave_the_site(app, bad):
    r = login(app.test_client(), nxt=bad)
    assert r.headers["Location"] == "/"


def test_user_rules(tmp_path):
    db = tmp_path / "u.db"
    with pytest.raises(ValueError):
        users.create_user("ab", "long enough password", db)         # username too short
    with pytest.raises(ValueError):
        users.create_user("bob", "short", db)                       # password too short
    users.create_user("bob", "long enough password", db)
    with pytest.raises(ValueError):
        users.create_user("BOB", "another long password", db)       # case-insensitive duplicate
    assert users.verify("Bob", "long enough password", db) == "bob"
    assert users.verify("bob", "wrong password!!", db) is None
    stored = __import__("sqlite3").connect(db).execute("SELECT password_hash FROM users").fetchone()[0]
    assert "long enough password" not in stored                     # only a hash is stored
