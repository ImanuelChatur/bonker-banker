"""Saved scenarios: save from the Shock Lab, list on /customer, compare, reopen, delete."""
import re

import pytest

from config import DATA_PROCESSED

needs_data = pytest.mark.skipif(not (DATA_PROCESSED / "monthly_summary.parquet").exists(),
                                reason="run scripts/precompute.py first")


@pytest.fixture
def client(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path)   # keep the real uploads/saved.db untouched
    from app import create_app
    return create_app().test_client()


@needs_data
def test_save_compare_reopen_delete(client):
    job = {"account_id": "20111", "income_pct": "55", "duration_months": "6", "name": "Laid off"}
    bills = {"account_id": "20111", "bills_pct": "15", "rate_hike_pct": "1", "name": ""}
    assert b"Saved" in client.post("/shock/save", data=job).data
    assert b"Bills +15%, rates +1 pts" in client.post("/shock/save", data=bills).data   # unnamed -> described

    page = client.get("/customer/20111").data.decode()
    ids = re.findall(r'name="ids" value="(\d+)"', page)
    assert len(ids) == 2 and "Laid off" in page

    cmp = client.get(f"/customer/20111/compare?ids={ids[0]}&ids={ids[1]}").data.decode()
    assert "Laid off" in cmp and "Short" in cmp and "months of runway" in cmp

    lab = client.get(f"/shock?account_id=20111&saved={ids[-1]}").data.decode()   # oldest = "Laid off"
    assert 'id="job_loss" value="1" checked' in lab

    client.post(f"/scenarios/{ids[0]}/delete", data={"account_id": "20111"})
    assert len(re.findall(r'name="ids"', client.get("/customer/20111").data.decode())) == 1


@needs_data
def test_no_saved_section_without_scenarios(client):
    assert b'id="saved"' not in client.get("/customer/20176").data


def test_save_needs_an_account(client):
    assert b"account ID first" in client.post("/shock/save", data={"bills_pct": "15"}).data
