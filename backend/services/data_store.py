"""Loads the processed Parquet files once and serves per-account rows.

Build the Parquet files with:  python scripts/precompute.py   (reads data/raw/*.csv)
"""
from __future__ import annotations

import logging
import threading

import pandas as pd

import config

log = logging.getLogger(__name__)
_lock = threading.Lock()
_state: dict = {}


class DataNotReady(RuntimeError):
    pass


def load(force: bool = False) -> bool:
    """Load Parquet into memory. Returns False (and logs) if precompute hasn't been run."""
    with _lock:
        if _state and not force:
            return True
        ms, ln = config.DATA_PROCESSED / "monthly_summary.parquet", config.DATA_PROCESSED / "loans.parquet"
        if not ms.exists() or not ln.exists():
            log.warning("Processed data not found in %s - run: python scripts/precompute.py", config.DATA_PROCESSED)
            return False
        df = pd.read_parquet(ms)
        _state["monthly"] = {str(k): g.sort_values("month").to_dict("records") for k, g in df.groupby("account_id")}
        _state["loans"] = {str(r["account_id"]): r for r in pd.read_parquet(ln).to_dict("records")}
        return True


def _need():
    if not _state and not load():
        raise DataNotReady("Dataset not processed yet. Put the CSVs in data/raw/ and run: python scripts/precompute.py")


def account_rows(account_id) -> list[dict]:
    _need()
    rows = _state["monthly"].get(str(account_id))
    if not rows:
        raise KeyError(f"unknown account_id {account_id}")
    return rows


def account_loan(account_id) -> dict | None:
    _need()
    return _state["loans"].get(str(account_id))


def table(name: str) -> pd.DataFrame:
    """Any other processed table (account_profile, stress_grid, at_risk, ...), read once and cached.

    Raises DataNotReady if the script that builds it hasn't been run yet.
    """
    key = f"table:{name}"
    with _lock:
        if key not in _state:
            path = config.DATA_PROCESSED / f"{name}.parquet"
            if not path.exists():
                raise DataNotReady(f"data/processed/{name}.parquet is missing. Run: python scripts/precompute.py "
                                   "and python scripts/stress_test.py")
            _state[key] = pd.read_parquet(path)
        return _state[key]


def account_ids() -> list[str]:
    _need()
    return sorted(_state["monthly"], key=int)
