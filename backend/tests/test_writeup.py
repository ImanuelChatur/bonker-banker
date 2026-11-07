"""The submission write-up must credit every source the app uses, and quote the numbers the engine computes."""
from pathlib import Path

import pytest

from engine.sources import SOURCES
from services import data_store

WRITEUP = (Path(__file__).resolve().parents[2] / "docs" / "WRITEUP.md").read_text(encoding="utf-8")


def test_every_source_is_credited():
    for s in SOURCES:
        assert s["url"] in WRITEUP, f"WRITEUP.md is missing {s['name']}"


@pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")
def test_quoted_numbers_match_the_engine():
    from engine.findings import biggest_finding
    f = biggest_finding()
    g = {b["band"][0]: b for b in f["default_by_grade"]}
    for grade in "ABCDF":
        assert f"| {g[grade]['loans']} | {g[grade]['rate']:.1f}% |" in WRITEUP
    assert f"{f['auc_score']:.2f}" in WRITEUP and f"{f['auc_runway']:.2f}" in WRITEUP
    assert f"{f['n_loans']} borrowers" in WRITEUP and f"{f['n_excluded']} loans" in WRITEUP
    for row in f["stress"]:
        assert f"{row['share_pct']:.1f}%" in WRITEUP
