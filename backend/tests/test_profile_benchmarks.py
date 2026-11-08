import pytest

import config
from services import data_store

pytestmark = pytest.mark.skipif(not (config.DATA_PROCESSED / "account_profile.parquet").exists() or not data_store.load(),
                                reason="run scripts/precompute.py first")

PROFILE_KEYS = {"age", "age_band", "tenure_years", "household_size", "district_name", "region",
                "district_unemployment_2023", "unemployment_trend", "district_avg_salary", "card_type",
                "standing_orders_monthly", "leasing_monthly", "true_fixed_costs", "income_volatility",
                "avg_days_below_zero", "penalty_fees_12m", "income_band"}


def test_profile_contract_and_no_gender():
    from engine.profile import customer_profile
    p = customer_profile("20111")
    assert set(p) == PROFILE_KEYS                                     # exactly the contract, nothing else (no gender)
    assert p["household_size"] >= 1 and p["unemployment_trend"] in ("rising", "falling", "flat", None)
    with pytest.raises(KeyError):
        customer_profile("no-such-account")


def test_profile_matches_judges_numbers():
    from engine import customer_metrics
    prof = data_store.table("account_profile").set_index("account_id")
    for aid in ("20111", "20176", "21817"):
        m = customer_metrics(aid)
        assert prof.loc[aid, "F"] == round(m.fixed_costs, 2) and prof.loc[aid, "B"] == round(m.buffer, 2)
        assert prof.loc[aid, "true_fixed_costs"] >= prof.loc[aid, "F"]          # only ever adds orders F misses


def test_no_gender_anywhere_in_profile_table():
    assert "gender" not in data_store.table("account_profile").columns


def test_benchmarks_contract():
    from engine.benchmarks import peer_benchmarks
    b = peer_benchmarks("20111")
    assert set(b) == {"group", "peer_count", "metrics"}
    assert set(b["group"]) == {"income_band", "age_band", "district_name"} and b["peer_count"] >= 30
    assert set(b["metrics"]) == {"buffer", "runway", "fixed_cost_share", "income_volatility"}
    for v in b["metrics"].values():
        assert set(v) == {"value", "percentile", "peer_median"}
        assert v["percentile"] is None or 0 <= v["percentile"] <= 100


def test_lower_is_better_measures_are_inverted():
    from engine.benchmarks import peer_benchmarks
    b = peer_benchmarks("20176")                                      # fixed costs ~1% of income: best in group
    assert b["metrics"]["fixed_cost_share"]["percentile"] >= 90
