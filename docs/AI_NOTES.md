# AI notes: changes to shared files

Shared files: `base.html`, `styles.css`, `main.js`, `routes/__init__.py`, `routes/_common.py`, `services/data_store.py`.
Every change to one of them gets a line here: who, file, what, why.

| Who | File | Change | Why |
| :-- | :-- | :-- | :-- |
| ClaudeOne | `services/data_store.py` | Added `table(name)`: reads any `data/processed/<name>.parquet` once, cached; raises `DataNotReady` if missing. Existing functions unchanged. | New precomputed tables (account_profile, stress_grid, stress_breakdown, at_risk) without loading them all at startup. |
| ClaudeOne | `routes/_common.py` | `shock_from_form` now also reads `rate_hike_pct` (0-10 points) and `realistic_ei` ("1"/"true"/"on"). Defaults 0 / off. | Handoff task 4: new optional Shock fields; existing results unchanged. |
| ClaudeOne | `routes/assistant.py` (not in the shared list, but ClaudeTwo's route) | Schema + prompt gain `rate_hike_pct` and `realistic_ei`; Shock built with them; `twistParsed` HX-Trigger payload gains both keys. | So "rates go up 1%" works; handoff task 4. |
| ClaudeTwo | `routes/__init__.py` | Registered `sources` and `demo` blueprints; `runway_class` bands now 12+ good / 3-12 warn / under 3 bad (were 6 / 1). | New pages; colour bands match the pre-loan default-rate finding (9% / 21% / 44%). |
| ClaudeTwo | `app.py` (not on the list, logged anyway) | `/` passes `stat=home_stat()` from `routes/home.py`. | Home page headline from `engine.insights.headline()`. |
| ClaudeTwo | `static/js/charts.js` (not on the list) | Added `kind: "donut"` and `kind: "heatmap"` renderers; line charts unchanged. | Spending mix and the stress-test heatmap. |
