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


@needs_data
def test_insights_still_works_without_district_data(monkeypatch):
    """A teammate who pulled without districts.csv/parquet still gets /insights, minus the regional section."""
    from engine import regions
    from app import create_app

    def missing(name):
        raise FileNotFoundError(f"{name} not processed")
    monkeypatch.setattr(regions, "_read", missing)
    regions._lookup.cache_clear()
    if hasattr(regions.region_summary, "cache_clear"):
        regions.region_summary.cache_clear()
    try:
        r = create_app().test_client().get("/insights")
        assert r.status_code == 200 and b"resilience grade" in r.data and b"Does where you live" not in r.data
    finally:
        regions._lookup.cache_clear()
        if hasattr(regions.region_summary, "cache_clear"):
            regions.region_summary.cache_clear()


def test_precompute_includes_accounts_and_districts():
    import importlib.util
    from config import ROOT
    spec = importlib.util.spec_from_file_location("precompute", ROOT / "scripts" / "precompute.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert {"monthly_summary", "loans", "accounts", "districts"} <= set(mod.FILES)
