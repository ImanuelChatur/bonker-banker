"""/demo walkthrough and /sources render for real accounts."""
import pytest

from config import DATA_PROCESSED

needs_data = pytest.mark.skipif(not (DATA_PROCESSED / "monthly_summary.parquet").exists(),
                                reason="run scripts/precompute.py first")


@needs_data
@pytest.mark.parametrize("preset", ["job_loss", "bills_up", "repair", "combo"])
def test_demo_run_explains_every_preset(preset):
    from app import create_app
    c = create_app().test_client()
    r = c.post("/demo/run", data={"account_id": "20111", "preset": preset})
    assert r.status_code == 200 and b"What changed" in r.data and b"/report/20111" in r.data


@needs_data
def test_demo_page_and_unknown_account():
    from app import create_app
    c = create_app().test_client()
    assert b"Know the customer" in c.get("/demo?account_id=20176").data
    assert c.get("/demo?account_id=nope").status_code == 404


def test_sources_page_lists_dataset_credit():
    from app import create_app
    r = create_app().test_client().get("/sources")
    assert r.status_code == 200 and b"relational.fel.cvut.cz" in r.data
