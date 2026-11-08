# Key findings across all customers

Every number below was computed on 2026-11-08 (overnight run) by running the app's own code on the data in
`data/processed/`. Nothing is estimated. To reproduce all of them in one go (read-only, about a minute):

```
.venv/Scripts/python.exe docs/reports/compute_key_findings.py      # Windows
.venv/bin/python docs/reports/compute_key_findings.py              # macOS / Linux
```

Each section names the function behind its numbers. "Out of savings within 6 months" means a runway under
6 months using the standard runway formula, runway = savings ÷ (spending − income), capped at 120 months.

---

## 1. One shock most customers can't absorb: a job loss

**If every customer lost their job (EI at 55% of income) and household bills rose 15%, 38.7% would run out of
savings within 6 months and 11.2% within 3, against 2.7% within 6 months today.**
Source: `engine.insights.headline()` (this is the sentence on the home page and the top of Insights).

Each standard shock on its own (`engine.findings.biggest_finding()["stress"]`, 4,500 accounts):

| Scenario | Accounts out of savings within 6 months | Share |
| :-- | --: | --: |
| No shock (today) | 120 | 2.7% |
| Job loss, EI at 55% | 1,578 | 35.1% |
| Household bills +15% | 139 | 3.1% |
| Repair = 1 month of spending | 393 | 8.7% |
| Job loss (EI 55%) + bills +15% | 1,740 | 38.7% |

- **The job loss does almost all the damage.** Bills +15% alone moves the share from 2.7% to 3.1%; a job loss
  moves it to 35.1%.
- Worst cell of the stress grid (`engine.insights.stress_grid()`): no income at all plus bills +25% leaves
  **75.0%** out of savings within 6 months; with a repair of 1 or 2 months of spending on top, **80.1%** and **83.9%**.

## 2. Who is hit hardest by a job loss

Scenario: EI at 55% and bills +15%. Source: `engine.insights.stress_breakdown(55, 15, 0)`.

| Group | Share out of savings within 6 months |
| :-- | --: |
| Monthly income $14,500+ (900 accounts) | **74.2%** |
| Monthly income $9,900 to $14,500 (900) | 56.4% |
| Monthly income $5,100 to $9,900 (900) | 46.8% |
| Monthly income $3,000 to $5,100 (900) | 11.1% |
| Monthly income under $3,000 (900) | **4.8%** |
| Age 45-54 (824) | 49.0% |
| Age 65+ (656) | **2.6%** |
| Age under 25 (682) | 35.5% |
| One person on the account (3,631) | 39.4% |
| Two people on the account (869) | 35.8% |

- **Higher earners are the most exposed**, the opposite of what most people expect. Checked tonight (section 10 of the script) from
  `customer_metrics` for every account, grouped by monthly income (I) with fixed cut-offs at $3,000 / $5,100 /
  $9,900 / $14,500, close to the engine's own bands: the median account under $3,000 spends **70%** of its income
  and holds savings worth **8.4 months** of spending; the median account over $14,500 spends **95%** of its income
  and holds **1.8 months**. Losing 45% of income therefore opens a far bigger gap for high earners, with less
  cushion behind it.
- **Customers aged 65+ barely move (2.6%).** (Not broken down further tonight.)
- Region matters little: from 33.7% (west Bohemia) to 44.1% (south Bohemia).

## 3. Today, most customers are fine; a job loss changes that

Source: `engine.customer_metrics`, `engine.runway` and `engine.apply_shock` run over all 4,500 accounts (section 7 of the script).

- **3,315 accounts (73.7%) have no shortfall** at their usual income: savings don't run down at all.
- **60 accounts** have under 3 months of runway today, **181** have 3 to 12 months.
- On EI at 55%, the **median runway is 8.6 months** (accounts that still have no shortfall are counted as 120).
- **2,904 accounts (64.5%) make it through 6 months of EI at 55%**, so about a third don't.
- **23 accounts** have a negative savings buffer (overdrawn on average over the last 6 months).
- History length: 12 to 72 months per account (median 36).

## 4. What predicts loan default

Source: `engine.findings.biggest_finding()`. Each borrower is scored only on the months **before** their loan
started, the way a lender would have to. 615 borrowers are scored; 67 loans are left out because the account
had under 6 months of history before the loan.

**Judged only on the months before the loan was granted, borrowers with an F resilience grade went on to default
47.1% of the time, against 8.5% for grade A (5.5 times as often).**

| Resilience grade (our score) | Loans | Defaulted | Rate |
| :-- | --: | --: | --: |
| A (80+) | 485 | 41 | 8.5% |
| B (65-79) | 66 | 6 | 9.1% |
| C (50-64) | 24 | 6 | 25.0% |
| D (35-49) | 23 | 4 | 17.4% |
| F (under 35) | 17 | 8 | 47.1% |

| Runway before the loan | Loans | Defaulted | Rate |
| :-- | --: | --: | --: |
| Under 3 months | 16 | 7 | 43.8% |
| 3 to 12 months | 48 | 10 | 20.8% |
| 12+ months | 551 | 48 | 8.7% |

- The resilience score separates defaulters better than runway alone: **AUC 0.70 vs 0.57** (0.5 = coin flip).
- Strongest single warning signs: **income stability (AUC 0.70)** and **overdraft days (0.70)**; runway 0.59,
  cash flow 0.52, fixed costs 0.47.
- Caution: grades C, D and F hold only 24, 23 and 17 loans, so those rates move a lot with a few loans
  (D is lower than C, for example).
- Across all 682 loans in the data, **76 (11.1%)** are counted as defaulted: 31 "finished, not repaid" and
  45 "running, client in debt" (`data/processed/loans.parquet`, column `defaulted`).

## 5. Where people live barely matters

Source: `engine.regions.region_summary()`. Across districts, rank correlation (Spearman) of local unemployment
with the resilience score is **−0.11**, with shortfalls **0.04**, with default **0.18**. Individual income
stability matters far more than location.

## 6. Loans

- **448 accounts** have an active loan payment (`Metrics.loan_payment_active > 0`).
- A new **$10,000 loan over 36 months** at the default Bank of Canada personal-loan rate
  (`engine.loans.affordability(m, 10000, 36)` for every account): **2,208 comfortable, 2,159 tight, 133 risky**.
- The source data has no interest rates for existing loans; see `KNOWN_ISSUES_AND_QA_PREP.md`.

## 7. Who to call this week

Source: `engine.insights.at_risk_customers(50)`. The list holds 50 accounts; **24 have a runway of 0 today**.
The top three are 32078, 36407 and 37897, all with no savings buffer left.

## What could not be computed

- Nothing in the list above failed. The twist-card assistant (Gemini) was not exercised tonight because no
  `GEMINI_API_KEY` is set on this machine; it doesn't produce any of these numbers.
