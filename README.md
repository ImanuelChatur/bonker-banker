# Bonker Banker

**Know your runway before life goes bonkers.**

Bonker Banker shows how many months a bank customer's savings would last if something went wrong (a job loss,
higher bills, a big repair, a rate hike) and what they could do about it. It's for **customers**, who get the plain
answer, and their **advisors**, who get every number behind it plus a view across all customers.

It runs on real, anonymized bank data: 4,500 accounts, about a million transactions and 682 loans.

---

## Feature tour

Every page answers one question first, in a sentence, then shows one big number and at most three supporting
numbers. Depth sits one click away: in **Advisor** view, in tabs, or in expanders.

**Simple / Advisor view.** A toggle at the top of every page. **Simple** (the default) shows what a customer needs.
**Advisor** adds the resilience score, peer percentiles, the customer profile, true fixed costs, every input to the
formula, loan strategies, the full at-risk list and methods. Nothing is removed in Simple view, only folded away. The
choice is remembered in the browser; a link can also set it with `?view=advisor` or `?view=simple`.

| Page | Question it answers | Simple view | Advisor view adds |
| :-- | :-- | :-- | :-- |
| **Home** `/` | Where do I start? | Account search, one headline number across all customers, the three steps, sample accounts | – |
| **Customer** `/customer/<id>` | How long could they last? | Runway, savings, monthly in vs out, months on EI after a job loss; savings chart (spending mix in a tab); "Stress-test this customer" | Resilience score and why, comparison with similar customers, profile, true fixed costs, I/S/F/H/B/P, simulated runway |
| **Shock Lab** `/shock` | What if something goes wrong? | Common shocks (job loss, repair, bills up, both), job-loss and cost sliders, live result with a chart; describe a shock in your own words | "More options" open by default: rate hike, realistic EI (capped at $729/week), exact dollar amounts; worked formula open |
| **Plan** `/plan` | What should they do about it? | Amount still to save for an emergency fund, time to get there, the cut needed if the shock hits, the three steps that help most; loan check (comfortable / tight / risky) | Every action and the runway it adds, backup-plan detail, the shock the plan is for, prepay-vs-save strategies for a running loan |
| **Insights** `/insights` | What do we see across all customers? | The headline stress result, a heatmap of every shock, the 5 customers to call first | Who is hit hardest, what predicts default, regions, all 50 at-risk customers with reasons, method |
| **Report** `/report/<id>` | Something to print or save as PDF | One-page runway report | – |
| **Walkthrough** `/demo?account_id=<id>` | One account start to finish | Customer, shock, worked formula, plan and report on one page | – |
| **Upload** `/upload` | What do my own statements say? | Parse bank statement PDFs, categorize spending, flag unusual activity | – |
| **Sources** `/sources` | Where does this come from? | Every outside source and definition | – |

**Sign in.** When login is on (the hosted site), sign in with a username and password. Anyone can create an account
in under a minute. Once in, **Simple / Advisor** at the top of every page switches the view.

## How it works

```
data/raw/*.csv ──► scripts/precompute.py ──► data/processed/*.parquet ──► backend/engine ──► backend/routes + templates
 (PKDD'99 data)     (and scripts/stress_test.py:                          (runway formula,     (Flask + HTMX pages)
                     every shock × every account)                          shocks, plans)
```

1. **Data.** The CSVs (accounts, transactions summarized per month, loans, clients, districts, cards, standing
   orders) are converted to Parquet once. `stress_test.py` runs every shock in a grid over all accounts and stores
   the results for Insights.
2. **Per-account numbers** (`engine/metrics.py`), using the dataset's published definitions: typical monthly
   **income I** and **spending S** (medians), **fixed costs F** (household bills + insurance + loan payments),
   **household bills H**, **savings buffer B** (average daily balance over the last 6 months) and **active loan
   payment P**.
3. **Runway** (`engine/runway.py`): `B ÷ (S − I)` months when spending is above income; "no shortfall" when
   income covers spending; 0 when savings are gone. Capped at 120 months.
4. **Shocks** (`engine/shocks.py`): income becomes a percentage of usual (EI is 55% by default) for a number of
   months; household bills go up by a percentage of H; a one-off cost (in dollars or months of spending) comes
   out of B; optional rate hike on variable-rate debt; optional realistic EI capped at $729/week. The runway is
   recalculated with the same formula, and the page checks whether savings last the whole EI period.
5. **Plans** (`engine/plans.py`, `engine/actions.py`, `engine/loans.py`): emergency-fund goal, the monthly cut
   needed if a shock hits, ranked actions with the months of runway each buys, and loan affordability at Bank of
   Canada rates.
6. **Our own measures**, always labelled as such: resilience score (0 to 100), peer comparison, simulated runway,
   true fixed costs. They never change the runway itself.

## Setup

Developed and tested on **Python 3.14**; the code needs at least Python 3.10 (it uses `X | None` type hints). Only 3.14 was tested tonight.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS / Linux: source .venv/bin/activate
pip install -r backend/requirements.txt

# Data: put the provided CSVs in data/raw/ (accounts, cards, clients, dispositions, districts, loans,
# monthly_summary, standing_orders, transactions). They are git-ignored.
python scripts/precompute.py      # data/raw/*.csv -> data/processed/*.parquet
python scripts/stress_test.py     # population stress grid for Insights

flask --app backend/app run --debug
```

Then open http://127.0.0.1:5000.

**`.env`** in the repo root (git-ignored; see `.env.example`):

```
GEMINI_API_KEY=your-key-here   # optional: twist-card assistant and fallback statement parsing
BB_AUTH=off                    # local development: no login. Leave on (default) when hosting
BB_SECRET_KEY=...              # required when hosting: python -c "import secrets; print(secrets.token_hex(32))"
```

Without `GEMINI_API_KEY` everything works except "describe a shock in your own words", which then says to use the
common shocks and sliders instead. Login accounts can also be managed with `python scripts/create_user.py`.

### Docker

```bash
cp .env.example .env            # add GEMINI_API_KEY and a BB_SECRET_KEY
docker compose up -d --build    # needs data/processed/*.parquet (run precompute first)
```

The site is then on `http://localhost`. Hosting on EC2 (with HTTPS): see [deploy/EC2.md](deploy/EC2.md).

## Project structure

```
backend/
  app.py              Flask app factory
  config.py           paths and settings from .env
  engine/             all calculations: metrics, runway, shocks, plans, loans, insights, findings
  ingest/             statement PDF parsing, categorizing, ledger (SQLite)
  routes/             one module per page; _common.py has shared form parsing and error handling
  services/           data loading, saved scenarios, login accounts, Gemini client
  templates/          Jinja pages; _ui.html has shared pieces (tooltips, "How to read this", sample accounts)
  static/css/         styles.css, theme.css, dashboard.css, ui.css (design tokens, Simple/Advisor, loaded last)
  static/js/          main.js (view toggle, tabs), charts.js (ECharts), shock_lab.js, upload_page.js
  tests/              pytest suite
data/
  raw/                provided CSVs (git-ignored)
  processed/          Parquet written by the scripts (git-ignored)
  external/           small public reference tables (EI parameters, lending rates), committed
docs/                 notes, write-up, reports
scripts/              precompute.py, stress_test.py, create_user.py
```

## Running tests

```bash
cd backend
python -m pytest -q
```

The suite (112 tests) covers the engine against the published formula, every page, uploads, saved scenarios and
login. Tests that need the data skip themselves when `data/processed/` is missing.

## Data and sources

- **PKDD'99 Discovery Challenge Financial dataset** (real, anonymized Czech bank data), CTU Prague Relational
  Dataset Repository: https://relational.fel.cvut.cz/dataset/Financial. Provided to us as monthly summaries and
  related tables in the Tangerine data pack.
- **Employment Insurance regular benefits**, Government of Canada:
  https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit.html
- **EI regular benefits: how much you could receive** (55% benefit rate, $729/week maximum, $68,900 maximum
  insurable earnings, 14 to 45 weeks), Government of Canada:
  https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit/benefit-amount.html
  (table: `data/external/ei_parameters_2026.csv`)
- **Interest rates for new and existing household lending** (series V122667780 to V122667812), Bank of Canada:
  https://bankofcanada.ca/rates/banking-and-financial-statistics/interest-rates-for-new-and-existing-household-lending
  (table: `data/external/canadian_lending_rates_2026.csv`)
- **Policy interest rate** (2.50%, raised 2026-10-28), Bank of Canada:
  https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/
- **Prime rate in Canada**, Ratehub (aggregator, used for prime only): https://www.ratehub.ca/prime-rate
- **Gemini API**, Google (twist-card assistant and fallback statement parsing): https://ai.google.dev/
- Libraries loaded from CDNs: Tailwind CSS, HTMX, Apache ECharts; font: Public Sans (Google Fonts).

The same list, with what each source is used for, is on the `/sources` page.

## Privacy: uploaded statements

What the code does today (`backend/routes/uploads.py`, `backend/ingest/`):

- Files are accepted only if they really are PDFs (checked by content), at most 10 per upload and 15 MB each.
- Each PDF is written to a **temporary folder under a fixed name** (never the uploaded filename), parsed, and the
  folder is deleted straight away. **The PDF itself is not kept.**
- The **parsed transactions are kept**: date, description, amount, balance, category, the original filename and
  the account number found on the statement go into a SQLite database at `uploads/ledger.db` so repeat uploads
  aren't double-counted. Nothing deletes them automatically, and **the ledger isn't separated per user**.
  Delete `uploads/ledger.db` to clear it. `uploads/` is git-ignored.
- Only if the built-in parsers can't make the balances add up **and** `GEMINI_API_KEY` is set, the statement's
  text is sent to Google's Gemini API to try again. Before sending, every run of 6 or more digits (account and
  card numbers) is masked except its last 4 digits. Names and addresses on the statement are not masked.
- Login passwords are stored only as hashes (`uploads/users.db`).
