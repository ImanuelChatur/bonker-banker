"""Richer customer profile from every data file, read from data/processed/account_profile.parquet.

Built by scripts/precompute.py. Notes on the less obvious fields:
- age / age_band: the account owner's age on 2025-12-31 (the dataset's last day). Gender is never used.
- household_size: people attached to the account (owner + authorized users) in dispositions.csv.
- true_fixed_costs: the judges' F (median bills + insurance + loan payments) PLUS standing orders whose purpose F
  doesn't already count (leasing and blank/"other"). Standing-order amounts are treated as monthly. Our measure,
  never a replacement for F in the judges' runway.
- income_volatility: coefficient of variation of monthly money_in (std / mean) over the whole history.
- penalty_fees_12m: penalty interest for a negative balance, Jan to Dec 2025.
- income_band: quintile of typical monthly income (I) across all 4,500 accounts.
"""
from __future__ import annotations

import math

from services import data_store


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def _row(account_id) -> dict:
    df = data_store.table("account_profile")
    hit = df[df["account_id"] == str(account_id)]
    if hit.empty:
        raise KeyError(f"unknown account_id {account_id}")
    return {k: _clean(v) for k, v in hit.iloc[0].to_dict().items()}


def customer_profile(account_id) -> dict:
    r = _row(account_id)
    return {
        "age": int(r["age"]) if r["age"] is not None else None,
        "age_band": r["age_band"],
        "tenure_years": r["tenure_years"],
        "household_size": int(r["household_size"]) if r["household_size"] is not None else None,
        "district_name": r["district_name"],
        "region": r["region"],
        "district_unemployment_2023": r["district_unemployment_2023"],
        "unemployment_trend": r["unemployment_trend"],
        "district_avg_salary": r["district_avg_salary"],
        "card_type": r["card_type"],
        "standing_orders_monthly": r["standing_orders_monthly"],
        "leasing_monthly": r["leasing_monthly"],
        "true_fixed_costs": r["true_fixed_costs"],
        "income_volatility": r["income_volatility"],
        "avg_days_below_zero": r["avg_days_below_zero"],
        "penalty_fees_12m": r["penalty_fees_12m"],
        "income_band": r["income_band"],
    }
