"""data/raw CSVs -> data/processed Parquet (fast to load at app startup), plus one profile row per account.

Run from the repo root:  python scripts/precompute.py      (then: python scripts/stress_test.py)

Outputs in data/processed/:
  monthly_summary, loans, accounts, districts, clients, dispositions, cards, standing_orders  (straight copies)
  account_profile  (one row per account: the judges' I/S/F/H/B/P and runway from the engine itself,
                    plus age, household, district, card, standing orders, volatility, overdraft, penalty fees)
No gender is carried into the profile: benchmarks, scores and advice must not use it.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT / "backend"))

FILES = {  # name -> columns that must stay text
    "monthly_summary": ["account_id", "month"],
    "loans": ["loan_id", "account_id", "status"],
    "accounts": ["account_id", "district_id"],
    "districts": ["district_id"],
    "clients": ["client_id", "district_id"],
    "dispositions": ["disposition_id", "client_id", "account_id"],
    "cards": ["card_id", "disposition_id"],
    "standing_orders": ["order_id", "account_id", "to_account"],
}

DATA_END = pd.Timestamp("2025-12-31")           # last day covered by the dataset
AGE_BANDS = [(0, 25, "under 25"), (25, 35, "25-34"), (35, 45, "35-44"), (45, 55, "45-54"), (55, 65, "55-64"),
             (65, 200, "65+")]
CARD_RANK = {"junior": 1, "classic": 2, "gold": 3}
# Standing-order purposes the judges' F already counts (household bills + insurance + loan payments). Orders with
# any OTHER purpose (leasing, blank/other) are committed monthly outflows that F misses -> added to true fixed costs.
COUNTED_IN_F = {"household bills", "insurance", "loan payment"}


def _copy_raw() -> dict[str, pd.DataFrame]:
    out = {}
    for name, text_cols in FILES.items():
        src = RAW / f"{name}.csv"
        if not src.exists():
            raise FileNotFoundError(f"missing {src} - copy the provided CSVs into data/raw/")
        df = pd.read_csv(src, dtype={c: str for c in text_cols})
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"{name}: {len(df):,} rows -> data/processed/{name}.parquet")
        out[name] = df
    return out


def age_band(age: float | None) -> str | None:
    if age is None or pd.isna(age):
        return None
    return next(label for lo, hi, label in AGE_BANDS if lo <= age < hi)


def income_bands(income: pd.Series, n: int = 5) -> tuple[pd.Series, list[float]]:
    """Quintile bands of typical monthly income, labelled in round dollars, e.g. '$2,500 to $4,500 / mo'."""
    edges = list(np.quantile(income, np.linspace(0, 1, n + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    inner = [round(e, -2) for e in edges[1:-1]]
    labels = ([f"under ${inner[0]:,.0f} / mo"]
              + [f"${inner[i]:,.0f} to ${inner[i + 1]:,.0f} / mo" for i in range(len(inner) - 1)]
              + [f"${inner[-1]:,.0f}+ / mo"])
    return pd.cut(income, bins=edges, labels=labels).astype(str), inner


def _penalty_fees_12m() -> pd.Series:
    """Penalty interest charged for a negative balance in the dataset's last 12 months, per account."""
    tx = pd.read_csv(RAW / "transactions.csv", usecols=["account_id", "date", "purpose", "amount"],
                     dtype={"account_id": str})
    tx = tx[(tx["purpose"] == "penalty interest (negative balance)") & (tx["date"] >= "2025-01-01")]
    return tx.groupby("account_id")["amount"].sum()


def build_profiles(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    from engine.metrics import metrics_from_rows      # the judges' definitions, so numbers match every page
    from engine.runway import RUNWAY_CAP, runway

    ms = raw["monthly_summary"].sort_values(["account_id", "month"])
    loans = {r["account_id"]: r for r in raw["loans"].to_dict("records")}

    rows = []
    for aid, g in ms.groupby("account_id", sort=False):
        recs = g.to_dict("records")
        m = metrics_from_rows(recs, aid, loans.get(aid))
        r = runway(m.buffer, m.income, m.spending)
        inc = g["money_in"].astype(float)
        rows.append({"account_id": aid, "I": m.income, "S": m.spending, "F": m.fixed_costs, "H": m.household_bills,
                     "B": m.buffer, "P": m.loan_payment_active,
                     "runway": RUNWAY_CAP if isinstance(r, str) else float(r),
                     "income_volatility": round(float(inc.std(ddof=0) / inc.mean()), 3) if inc.mean() > 0 else None,
                     "avg_days_below_zero": round(float(g["days_below_zero"].astype(float).mean()), 2),
                     "months_of_history": len(g)})
    prof = pd.DataFrame(rows)

    # Account -> branch district (districts.csv facts, incl. unemployment trend 2022 -> 2023).
    dist = raw["districts"].copy()
    d22, d23 = pd.to_numeric(dist["unemployment_rate_2022"], errors="coerce"), pd.to_numeric(dist["unemployment_rate_2023"], errors="coerce")
    diff = d23 - d22
    dist["unemployment_trend"] = np.where(diff.isna(), None, np.where(diff > 0.1, "rising", np.where(diff < -0.1, "falling", "flat")))
    acc = raw["accounts"][["account_id", "district_id", "account_opened"]].merge(
        dist[["district_id", "district_name", "region", "unemployment_rate_2023", "unemployment_trend", "average_salary"]],
        on="district_id", how="left")
    acc["tenure_years"] = ((DATA_END - pd.to_datetime(acc["account_opened"])).dt.days / 365.25).round(1)
    prof = prof.merge(acc.rename(columns={"unemployment_rate_2023": "district_unemployment_2023",
                                          "average_salary": "district_avg_salary"}), on="account_id", how="left")

    # Owner's age, household size (owner + authorized users), best card held on the account.
    disp, cl, cards = raw["dispositions"], raw["clients"], raw["cards"]
    owners = disp[disp["type"] == "owner"].merge(cl[["client_id", "birth_date"]], on="client_id", how="left")
    owners["age"] = ((DATA_END - pd.to_datetime(owners["birth_date"])).dt.days / 365.25).round(0)
    prof = prof.merge(owners[["account_id", "age"]], on="account_id", how="left")
    prof["age_band"] = prof["age"].map(age_band)
    prof = prof.merge(disp.groupby("account_id").size().rename("household_size"), on="account_id", how="left")
    cd = cards.merge(disp[["disposition_id", "account_id"]], on="disposition_id")
    cd["rank"] = cd["card_type"].map(CARD_RANK)
    best = cd.sort_values("rank").groupby("account_id").tail(1).set_index("account_id")["card_type"]
    prof["card_type"] = prof["account_id"].map(best)

    # Standing orders (amounts treated as monthly): all, leasing, and the ones F doesn't already count.
    so = raw["standing_orders"].copy()
    so["purpose"] = so["purpose"].fillna("")
    so["amount"] = so["amount"].astype(float)
    prof["standing_orders_monthly"] = prof["account_id"].map(so.groupby("account_id")["amount"].sum()).fillna(0.0)
    prof["leasing_monthly"] = prof["account_id"].map(
        so[so["purpose"] == "leasing"].groupby("account_id")["amount"].sum()).fillna(0.0)
    extra = so[~so["purpose"].isin(COUNTED_IN_F)].groupby("account_id")["amount"].sum()
    prof["true_fixed_costs"] = prof["F"] + prof["account_id"].map(extra).fillna(0.0)

    prof["penalty_fees_12m"] = prof["account_id"].map(_penalty_fees_12m()).fillna(0.0).round(2)
    prof["income_band"], _ = income_bands(prof["I"])
    for c in ("I", "S", "F", "H", "B", "P", "standing_orders_monthly", "leasing_monthly", "true_fixed_costs"):
        prof[c] = prof[c].astype(float).round(2)
    return prof


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        raw = _copy_raw()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    prof = build_profiles(raw)
    prof.to_parquet(OUT / "account_profile.parquet", index=False)
    print(f"account_profile: {len(prof):,} rows -> data/processed/account_profile.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
