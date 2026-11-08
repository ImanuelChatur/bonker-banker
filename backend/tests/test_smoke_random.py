"""Pre-judging smoke test: 10 random accounts through every engine function and every page, with each README twist."""
import random

import pytest

import config
from services import data_store

pytestmark = pytest.mark.skipif(not (config.DATA_PROCESSED / "at_risk.parquet").exists() or not data_store.load(),
                                reason="run scripts/precompute.py and scripts/stress_test.py first")

TWISTS = [  # the README's example twist cards, as Shock Lab form fields
    {"income_pct": "55", "duration_months": "6"},
    {"one_off_months": "1"},
    {"income_pct": "55", "bills_pct": "15"},
    {"income_pct": "55", "realistic_ei": "1", "rate_hike_pct": "1"},
]


@pytest.fixture(scope="module")
def ids():
    return random.Random(2026).sample(data_store.account_ids(), 10)


@pytest.fixture(scope="module")
def client():
    from app import create_app
    return create_app().test_client()


def test_every_engine_function(ids):
    from engine import Shock, action_plan, apply_shock, customer_metrics, goal_plan, peer_percentile, resilience_score
    from engine.benchmarks import peer_benchmarks
    from engine.loans import affordability, prepay_strategies
    from engine.profile import customer_profile
    for aid in ids:
        m = customer_metrics(aid)
        for sh in (Shock(), Shock(income_factor=0.55, household_bills_pct=0.15), Shock(one_off_months_of_spending=1),
                   Shock(income_factor=0.55, realistic_ei=True, rate_hike_pct=1)):
            assert apply_shock(m, sh)["after"]["runway"] is not None
            action_plan(m, sh)
        assert 0 <= resilience_score(m)["score"] <= 100
        assert peer_percentile(aid)["n"] == 4500
        goal_plan(m)
        customer_profile(aid)
        peer_benchmarks(aid)
        assert affordability(m, 10000, 36)["verdict"] in ("comfortable", "tight", "risky")
        prepay_strategies(m, None)


def test_every_page(ids, client):
    for aid in ids:
        assert client.get(f"/customer/{aid}").status_code == 200, aid
        assert client.get(f"/report/{aid}").status_code == 200, aid
        assert client.get(f"/demo?account_id={aid}").status_code == 200, aid
        for t in TWISTS:
            assert client.post("/shock/run", data={"account_id": aid, **t}).status_code == 200, (aid, t)
            assert client.post("/plan/run", data={"account_id": aid, **t}).status_code == 200, (aid, t)
    for page in ("/", "/insights", "/sources", "/upload", "/shock", "/plan"):
        assert client.get(page).status_code == 200, page
