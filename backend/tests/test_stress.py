"""Precomputed stress test must equal the engine's own runway, and engine/insights.py must honour its contract."""
import random

import pytest

import config
from services import data_store

pytestmark = pytest.mark.skipif(not (config.DATA_PROCESSED / "stress_grid.parquet").exists() or not data_store.load(),
                                reason="run scripts/precompute.py and scripts/stress_test.py first")


def test_precomputed_runway_equals_apply_shock_for_20_random_accounts():
    import sys
    sys.path.insert(0, str(config.ROOT / "scripts"))
    from stress_test import runway_vec

    from engine import Shock, apply_shock, customer_metrics
    from engine.runway import RUNWAY_CAP

    prof = data_store.table("account_profile").set_index("account_id")
    ids = random.Random(7).sample(list(prof.index), 20)
    for aid in ids:
        m = customer_metrics(aid)
        p = prof.loc[aid]
        for ei, bills, rep in [(100, 0, 0), (55, 0, 0), (55, 15, 0), (40, 25, 2), (0, 10, 1)]:
            engine = apply_shock(m, Shock(income_factor=ei / 100, household_bills_pct=bills / 100,
                                          one_off_months_of_spending=rep))["after"]["runway"]
            engine = RUNWAY_CAP if isinstance(engine, str) else engine
            import numpy as np
            pre = runway_vec(*(np.array([float(p[c])]) for c in ("B", "I", "S", "H")), ei, bills, rep)[0]
            assert pre == engine, (aid, ei, bills, rep, pre, engine)


def test_grid_shape_and_monotonic():
    from engine.insights import stress_grid
    g = stress_grid()
    assert len(g) == 60 and all(r["n"] == 4500 for r in g)
    by = {(r["ei_pct"], r["bills_pct"], r["one_off_months"]): r for r in g}
    assert by[(0, 0, 0)]["pct_runout_6m"] >= by[(55, 0, 0)]["pct_runout_6m"] >= by[(100, 0, 0)]["pct_runout_6m"]
    assert all(r["pct_runout_6m"] >= r["pct_runout_3m"] for r in g)


def test_breakdown_headline_and_at_risk_contracts():
    from engine.insights import at_risk_customers, headline, stress_breakdown
    rows = stress_breakdown(55, 15, 0)
    assert {r["group_type"] for r in rows} == {"age_band", "household_size", "region", "income_band"}
    assert sum(r["n"] for r in rows if r["group_type"] == "region") == 4500
    assert stress_breakdown(33, 15, 0) == []                       # not in the grid
    h = headline()
    assert set(h) == {"text", "pct_runout_3m", "pct_runout_6m", "scenario"} and "%" in h["text"]
    top = at_risk_customers(50)
    assert len(top) == 50 and all(r["reasons"] for r in top)
    assert [r["runway_ei55"] for r in top] == sorted(r["runway_ei55"] for r in top)
