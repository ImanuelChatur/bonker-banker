# Routes

Run from the repo root: `flask --app backend/app.py run --debug` (or `python backend/app.py`).
`backend/` is the app root: modules import each other as `engine`, `ingest`, `services`, `routes`, `config`.

| Method | Path | What it does |
| :-- | :-- | :-- |
| GET | `/` | Landing page (existing) |
| GET | `/customer`, `/customer/<account_id>` | Know the customer: I, S, F, H, B, P, runway, balance history, goal plan |
| GET | `/shock` | Shock Lab form (`?preset=job_loss\|bills_up\|repair\|combo`, `?account_id=`) |
| POST | `/shock/run` | HTMX partial: runway before/after, survives-the-duration check, projection chart |
| GET | `/plan` | Plan form |
| POST | `/plan/run` | HTMX partial: runway + goal plan + backup plan |
| GET | `/insights` | Population view: loan default rate by runway bucket across the whole dataset |
| POST | `/assistant/twist` | Gemini turns a twist card into shock settings, then runs it (needs `GEMINI_API_KEY`) |
| GET/POST | `/upload` | Upload a statement PDF; preview transactions, monthly summary and metrics |

Form fields for shocks: `income_pct` (55 = 55% of usual), `duration_months`, `bills_pct`, `extra_spending`,
`one_off_cost`, `one_off_months`. Plans also take `goal_months` and `target_runway`.

## Data

CSVs are too big for GitHub and are git-ignored. Put them in `data/raw/` and run:

```
python scripts/precompute.py      # writes data/processed/*.parquet
```

Without the Parquet files the app still starts; data pages show a message asking you to run the script.

## Statement ingest

`ingest/pdf_reader.py` -> `parsers/` (first parser whose `detect()` matches wins, generic fallback) ->
`categorize.py` (keyword rules, then priors learned from the dataset) -> `ledger.py` (SQLite at
`uploads/ledger.db` + monthly summary in the same columns as `monthly_summary.csv`).
If the rule-based parse doesn't reconcile and `GEMINI_API_KEY` is set, `llm_fallback.py` tries Gemini and
keeps its result only if the balances reconcile better. Retrain the learned priors with
`cd backend && python -m ingest.learn`.
