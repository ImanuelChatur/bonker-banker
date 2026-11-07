"""data/raw CSVs -> data/processed Parquet (fast to load at app startup).

Run from the repo root:  python scripts/precompute.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"

FILES = {  # name -> columns that must stay text
    "monthly_summary": ["account_id", "month"],
    "loans": ["loan_id", "account_id", "status"],
    "accounts": ["account_id", "district_id"],
}


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text_cols in FILES.items():
        src = RAW / f"{name}.csv"
        if not src.exists():
            print(f"missing {src} - copy the provided CSVs into data/raw/", file=sys.stderr)
            return 1
        df = pd.read_csv(src, dtype={c: str for c in text_cols})
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"{name}: {len(df):,} rows -> data/processed/{name}.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
