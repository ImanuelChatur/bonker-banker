# Bonker Banker: know your runway before life goes bonkers

Sheridan Datathon 2026, Tangerine track "Resilience Rewired".

## What it does

Bonker Banker answers one question for any customer: **if something goes wrong, how many months until the money runs out?**

1. **Know the customer.** Pick any of the 4,500 accounts. We show typical monthly income, spending, fixed costs,
   household bills, savings buffer and **runway**, all with the datathon's definitions, plus a 0 to 100
   **resilience score** that explains every point it gives or takes away.
2. **Take a shock.** The Shock Lab applies a job loss on EI, higher bills, a surprise repair or any mix, with sliders
   for the size. The runway recalculates instantly and the judges' formula is shown worked through with the
   account's real numbers. A twist card typed in plain English can be turned into shock settings.
3. **Make a plan.** A goal plan (an emergency fund sized to the customer's own spending) and a backup plan if the
   shock hits, plus a ranked list of concrete actions with the months of runway each one buys.
4. **Share it.** A printable one-page Runway Report per customer, and a `/demo` page that walks a live twist from
   customer, to shock, to the worked formula, to the plan and report, one click per step.
5. **Bring your own statements.** Upload one or more bank statement PDFs: we parse them, categorize every
   transaction, break down spending, and flag unusual activity (large outliers, possible duplicate charges, large
   transfers, purchases billed abroad). Uploaded data produces the same monthly summary as the dataset, so the
   same engine runs on it.

## Biggest finding

**Judged only on the months before the loan was granted, borrowers with an F resilience grade went on to default 47.1% of the time, against 8.5% for grade A (5.5 times as often).**

We scored each of the 615 borrowers with at least six months of history using **only the months before their loan
started**, the way a lender would have to (67 loans with less history are left out). Then we checked loans.csv:

| Grade (our score) | Loans | Defaulted |
| :-- | --: | --: |
| A (80+) | 485 | 8.5% |
| B (65-79) | 66 | 9.1% |
| C (50-64) | 24 | 25.0% |
| D (35-49) | 23 | 17.4% |
| F (under 35) | 17 | 47.1% |

- Grade F borrowers defaulted **5.5 times as often** as grade A.
- The score separates defaulters from repayers better than runway alone: AUC **0.70** vs **0.57**.
- The strongest early warning signs were **unstable income** and **days below zero** (AUC 0.70 each), not the size of
  the savings balance.

**Shocks hit unevenly.** Applying each README twist card to every account:

| Scenario | Accounts out of savings within 6 months |
| :-- | --: |
| No shock (today) | 2.7% |
| Household bills +15% | 3.1% |
| Repair costing 1 month of spending | 8.7% |
| Job loss, EI at 55% | 35.1% |
| Job loss and bills +15% | 38.7% |

A job loss is by far the biggest threat. Higher bills barely move the population, because many accounts record no
household bills at all (their median H is $0). That's worth knowing during a live twist.

**Caveats.** These are associations, not proof of cause. We designed the score first and checked it against defaults
afterwards. The middle grades are small groups (about 24 loans each), which is why C and D are out of order.

## Definitions

The judges' numbers are used exactly as defined in the track README: I, S, F, H, B, P and
runway = (B - one-off costs) / (spending after shock - income after shock), capped at 120 months, 1 decimal.
Everything else is labelled **"our measure"** in the app:

- **Resilience score (0 to 100):** runway 40, cash flow 20, fixed-cost burden 15, income stability 15, overdraft days
  10 points. Each part shows why it scored what it did.
- **Peer percentile:** where an account ranks among all 4,500 (ties count half).
- **Action plan:** each action's runway gain is the judges' formula re-run with that action applied.

## Run it

```bash
python -m pip install -r backend/requirements.txt
python scripts/precompute.py          # needs the provided CSVs in data/raw/
python -m flask --app backend/app.py run
```

Tests: `python -m pytest backend/tests -q`.

## Sources

- **PKDD'99 Discovery Challenge Financial dataset** (real, anonymized bank data), CTU Prague Relational Dataset
  Repository: https://relational.fel.cvut.cz/dataset/Financial. All account, transaction, loan and monthly-summary
  numbers, via the Tangerine datathon data pack.
- **Employment Insurance regular benefits**, Government of Canada:
  https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit.html. The 55% income figure behind the job-loss preset.
- **Gemini API**, Google: https://ai.google.dev/. Turns a twist card typed in plain English into shock settings, and
  reads unfamiliar statement layouts. Only card text or masked statement text is sent; no dataset rows.

The same list drives the app's `/sources` page (`backend/engine/sources.py`); a test checks the two stay in sync.
