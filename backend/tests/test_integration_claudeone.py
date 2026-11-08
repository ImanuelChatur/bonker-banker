"""ClaudeOne's engine functions as ClaudeTwo's pages render them (score, peers, actions, dollar text)."""
import re

import pytest

from services import data_store

pytestmark = pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")


@pytest.fixture(scope="module")
def client():
    from app import create_app
    return create_app().test_client()


def test_customer_page_shows_score_and_peers(client):
    html = client.get("/customer/20111").data.decode()
    assert "Resilience" in html or "resilience" in html
    assert "Compared with people like them" in html          # peer benchmarks section (replaced the 4,500-wide percentile)


def test_report_page_renders(client):
    r = client.get("/report/21817")
    assert r.status_code == 200


def test_plan_shows_actions_and_whole_dollars(client):
    html = client.post("/plan/run", data={"account_id": "20111", "income_pct": "55"}).data.decode()
    assert "Trim flexible spending" in html
    assert not re.search(r"\d+\.\d{2}/month", html)         # no raw floats like 2177.63/month
