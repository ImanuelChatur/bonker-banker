# AI notes: changes to shared files

Shared files: `base.html`, `styles.css`, `main.js`, `routes/__init__.py`, `routes/_common.py`, `services/data_store.py`.
Every change to one of them gets a line here: who, file, what, why.

| Who | File | Change | Why |
| :-- | :-- | :-- | :-- |
| ClaudeOne | `services/data_store.py` | Added `table(name)`: reads any `data/processed/<name>.parquet` once, cached; raises `DataNotReady` if missing. Existing functions unchanged. | New precomputed tables (account_profile, stress_grid, stress_breakdown, at_risk) without loading them all at startup. |
