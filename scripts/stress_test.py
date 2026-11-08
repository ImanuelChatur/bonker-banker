"""Population stress test: every shock in the grid applied to all 4,500 accounts at once (vectorised).

Run from the repo root after precompute:  python scripts/stress_test.py

Grid: EI {100, 75, 55, 40, 0}% x household bills {+0, +10, +15, +25}% x repair {0, 1, 2} months of spending = 60 scenarios.
Runway is the judges' formula, exactly as engine/runway.py + engine/shocks.py compute it:
  income' = I * ei   spending' = S + bills * H   one_off = repair_months * S
  buffer_left = B - one_off;  0 if buffer_left <= 0;  120 (no shortfall) if spending' <= income';
  else min(buffer_left / (spending' - income'), 120) rounded to 1 decimal.
tests/test_stress.py checks 20 random accounts against apply_shock() for equality.

Outputs (data/processed/):
  stress_grid.parquet       one row per scenario: ei_pct, bills_pct, one_off_months, pct_runout_3m, pct_runout_6m, n
  stress_breakdown.parquet  per scenario x group (age_band, household_size, region, income_band): pct_runout_6m, n
  at_risk.parquet           every account ranked by runway under EI 55%, with plain-English reasons
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"

EI = [100, 75, 55, 40, 0]
BILLS = [0, 10, 15, 25]
REPAIR = [0, 1, 2]
CAP = 120.0
GROUPS = ["age_band", "household_size", "region", "income_band"]


def runway_vec(B, I, S, H, ei_pct: float, bills_pct: float, repair_months: float) -> np.ndarray:
    """Vectorised twin of engine.runway.runway() after engine.shocks.apply_shock(); 'no shortfall' -> 120."""
    income = I * (ei_pct / 100.0)
    spending = S + (bills_pct / 100.0) * H
    buffer_left = B - repair_months * S
    gap = spending - income
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = np.minimum(buffer_left / gap, CAP)
    out = np.where(buffer_left <= 0, 0.0, np.where(gap <= 0, CAP, raw))
    return np.array([round(float(v), 1) for v in out])     # Python round(), same as the engine


def main() -> int:
    src = OUT / "account_profile.parquet"
    if not src.exists():
        print("run scripts/precompute.py first", file=sys.stderr)
        return 1
    prof = pd.read_parquet(src)
    B, I, S, H = (prof[c].to_numpy(float) for c in ("B", "I", "S", "H"))
    n = len(prof)
    prof["household_size"] = prof["household_size"].fillna(1).astype(int).astype(str)

    grid, breakdown = [], []
    for ei, bills, rep in itertools.product(EI, BILLS, REPAIR):
        r = runway_vec(B, I, S, H, ei, bills, rep)
        grid.append({"ei_pct": ei, "bills_pct": bills, "one_off_months": rep,
                     "pct_runout_3m": round(100 * float((r < 3).mean()), 1),
                     "pct_runout_6m": round(100 * float((r < 6).mean()), 1), "n": n})
        short6 = pd.Series(r < 6, index=prof.index)
        for gt in GROUPS:
            for grp, idx in prof.groupby(gt).groups.items():
                breakdown.append({"ei_pct": ei, "bills_pct": bills, "one_off_months": rep, "group_type": gt,
                                  "group": str(grp), "pct_runout_6m": round(100 * float(short6[idx].mean()), 1),
                                  "n": len(idx)})
    pd.DataFrame(grid).to_parquet(OUT / "stress_grid.parquet", index=False)
    pd.DataFrame(breakdown).to_parquet(OUT / "stress_breakdown.parquet", index=False)

    # Who to call: shortest runway on EI at 55%, then today's runway. Reasons are facts, not judgements.
    loans = pd.read_parquet(OUT / "loans.parquet").set_index("account_id")["status"]
    risk = prof[["account_id", "runway", "district_name", "I", "S", "income_volatility", "avg_days_below_zero",
                 "penalty_fees_12m"]].copy()
    risk["runway_ei55"] = runway_vec(B, I, S, H, 55, 0, 0)
    risk["loan_status"] = risk["account_id"].map(loans)
    reasons = []
    for r in risk.itertuples():
        if r.runway_ei55 <= 0:
            why = ["No savings buffer left today"]
        elif r.runway_ei55 < CAP:
            why = [f"Runs out in {r.runway_ei55:g} months on EI at 55%"]
        else:
            why = ["Covered even on EI at 55%"]
        if r.S > r.I:
            why.append(f"Spends ${r.S - r.I:,.0f}/month more than it earns today")
        if r.income_volatility is not None and r.income_volatility >= 0.5:
            why.append(f"Income swings about {r.income_volatility * 100:.0f}% month to month")
        if r.avg_days_below_zero >= 1:
            why.append(f"Below zero about {r.avg_days_below_zero:.0f} days a month")
        if r.penalty_fees_12m > 0:
            why.append(f"${r.penalty_fees_12m:,.0f} in overdraft penalty interest in 2025")
        if r.loan_status in ("B", "D"):
            why.append("Loan recorded as in arrears" if r.loan_status == "D" else "Past loan not repaid")
        reasons.append(why)
    risk["reasons"] = reasons
    risk = risk.sort_values(["runway_ei55", "runway"]).reset_index(drop=True)
    risk[["account_id", "runway", "runway_ei55", "district_name", "reasons"]].to_parquet(OUT / "at_risk.parquet", index=False)

    print(f"stress_grid: {len(grid)} scenarios x {n:,} accounts; breakdown rows: {len(breakdown):,}; at_risk: {len(risk):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
