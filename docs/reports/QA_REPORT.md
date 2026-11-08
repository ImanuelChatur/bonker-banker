# QA report: overnight run, 2026-11-08

Branch `overnight`. Everything below was run tonight against the full data in `data/processed/`.

## Summary

| Check | Result |
| :-- | :-- |
| Test suite (`cd backend && python -m pytest -q`) | **112 passed**, run after every change. One failure along the way was caused by my change and fixed before moving on (see "What I fixed") |
| Page sweep: 25 accounts × every page × 4 scenarios | **333 / 333 checks pass** (after fixes; first run found 1 crash and 104 bad "None" labels) |
| Every internal link and form on 14 pages and 5 live results | **83 / 83** links load (200, or a redirect to a page that loads) |
| Browser interaction tests (real headless Edge, clicking) | **20 / 20** pass, plus **4 / 4** for the twist-card slider sync |
| Browser console errors on 8 pages | **None** (only Edge's own tracking-prevention notices about the Tailwind CDN) |
| Unknown / bad account IDs | Friendly page or notice everywhere, correct 404 status |
| Layout at 1280px and ~500px wide | Checked by screenshot; no sideways scrolling |

## Accounts tested

20 random accounts (Python `random.seed(20261108)`, `random.sample` over all 4,500 IDs), plus 5 picked for edge cases.

Scenarios, as the brief asks: **job loss with EI at 55% for 6 months**; **a repair costing one month of typical
spending**; **job loss (EI 55%) plus household bills up 15%**; and no shock. Each scenario was run through
`POST /shock/run` and `POST /plan/run`; each account also loaded `/customer/<id>`, `/shock?preset=combo`,
`/plan/loan` ($10,000 over 36 months), `/report/<id>` and `/demo?account_id=<id>`.

Runway in months from the engine (`customer_metrics`, `runway`, `apply_shock`), as shown on the pages:

| Account | History (mo) | Loan payment | Runway today | Job loss, EI 55%, 6 mo | Lasts 6 mo? | Repair = 1 mo spending | Job loss + bills +15% |
| :-- | --: | --: | --: | --: | :-- | --: | --: |
| 68174 | 25 | – | 34.6 | 2.9 | no | 9.7 | 2.7 |
| 85953 | 29 | – | no shortfall | 36.1 | yes | no shortfall | 33.8 |
| 52438 | 57 | – | no shortfall | 4.7 | no | no shortfall | 4.7 |
| 64024 | 17 | – | no shortfall | 15.2 | yes | no shortfall | 14.3 |
| 76364 | 34 | $1,040 | no shortfall | 32.7 | yes | no shortfall | 22.2 |
| 22112 | 71 | – | no shortfall | 7.8 | yes | no shortfall | 6.7 |
| 99952 | 20 | $2,153 | 40.6 | 2.5 | no | 6.2 | 2.5 |
| 82103 | 33 | – | no shortfall | 5.9 | no | no shortfall | 5.6 |
| 31802 | 58 | $2,438 | 9.8 | 4.2 | no | 5.9 | 3.9 |
| 82008 | 31 | $4,173 | no shortfall | 3.9 | no | no shortfall | 3.5 |
| 35986 | 71 | – | no shortfall | 14.4 | yes | no shortfall | 10.4 |
| 20160 | 34 | – | 120 | 5.1 | no | 104.9 | 4.8 |
| 74617 | 30 | – | 52.4 | 3.3 | no | 17.9 | 2.8 |
| 63929 | 69 | – | no shortfall | 108.3 | yes | no shortfall | 55.2 |
| 79014 | 28 | – | 66.5 | 4.2 | no | 32.4 | 3.7 |
| 88446 | 28 | – | no shortfall | 36 | yes | no shortfall | 27.7 |
| 31954 | 70 | – | no shortfall | 64.4 | yes | no shortfall | 40.4 |
| 58542 | 27 | – | no shortfall | 11.4 | yes | no shortfall | 9.9 |
| 74775 | 22 | – | no shortfall | 120 | yes | no shortfall | 38.6 |
| 20111 | 38 | $2,330 | 7.8 | 3.4 | no | 4 | 3.4 |
| **49649** (shortest history: 12 months) | 12 | – | no shortfall | no shortfall | yes | no shortfall | no shortfall |
| **32078** (negative savings, −$2,513) | 70 | – | 0 | 0 | no | 0 | 0 |
| **21132** (no income and no spending) | 35 | – | no shortfall | no shortfall | yes | no shortfall | no shortfall |
| **20578** (no spending) | 33 | – | no shortfall | no shortfall | yes | no shortfall | no shortfall |
| **45405** (largest active loan payment, $6,196) | 32 | $6,196 | no shortfall | 8.4 | yes | no shortfall | 7.7 |

Every account in the table renders every page. Accounts with no loan (19 of the 25) were checked on the loan tab:
the Advisor section says "No running loan on this account" instead of a prepay comparison; the 6 accounts with a loan get the comparison (and a pointer to it in Simple view).

**Unknown IDs:** `99999` and `abc` on `/customer/<id>`, `/report/<id>`, `/demo`, `/customer/<id>/compare`,
`POST /shock/run`, `POST /plan/run`, `POST /plan/loan`. All return 404 with "We couldn't find account …" and sample
accounts; full pages keep the navigation. An unknown URL (`/nope`) gets the same friendly 404 page.

**Empty account field** on the Shock Lab and Plan: "Pick a customer to start" with sample accounts.

**Twist card without `GEMINI_API_KEY`:** 503 with "The assistant isn't available right now … The common shocks and
sliders do the same job." (No key on this machine, so the real Gemini round trip was not tested.)

## How the sweep checked pages

A script (`smoke.py`, kept out of the repo) loads each URL through Flask's test client and fails a page if:
the status is wrong; the visible text contains `Traceback`, `Undefined`, `nan`, `inf`, `None months`, a bare
`None`, `$-`, `-0 month`, or leftover template braces.

## Browser interaction tests (headless Edge, clicking for real)

| What | Result |
| :-- | :-- |
| Simple is the default: resilience score hidden | pass |
| Clicking "Advisor" shows it; choice saved in `localStorage`; survives a reload | pass |
| Advisor opens the expanders marked for advisors | pass |
| Back to Simple | pass |
| Customer chart tabs: "Where the money goes" shows and draws the donut at full width | pass |
| Shock Lab, no shock: lead says "No shock yet" | pass |
| Preset "Laid off + bills +15%": result updates, bills slider moves to 15 | pass |
| Dragging the EI slider to 20%: result updates live | pass |
| "More options" closed in Simple view | pass |
| Job loss off disables the realistic-EI box | pass |
| "Make a plan for this" link carries the shock settings | pass |
| Insights tabs switch; heatmap repair buttons swap the chart | pass |
| `/plan?…&bills_pct=15` prefills the plan form and loads the result | pass |
| Loan tab loads a verdict | pass |
| Twist card result event moves the sliders, sets rate hike and realistic EI, opens "More options" | 4 / 4 pass (event fired directly, as the server would) |

## What I fixed

| Problem | Where | Fix | Commit |
| :-- | :-- | :-- | :-- |
| `/customer/21132` crashed (500): the peer comparison rounded an empty percentile for an account with no income. Also on `main`. | `customer.html` | Skip peer rows with no value, percentile or peer median | `df2b035` |
| An unknown account on a full page showed a bare text snippet with no navigation | `routes/_common.py` | Proper error page with lookup and samples; notice card inside live results | `c107515` |
| Unknown URLs showed Flask's plain "Not Found" text; unexpected errors showed a stack trace (in debug) or a bare 500 | `routes/__init__.py` | Friendly 404 / 413 / 500 pages | `c107515` |
| A malformed Gemini reply would have shown "Account not found" | `routes/assistant.py` | Caught separately, with a useful message | `c107515` |
| Negative money shown as `$-2,513` | `money` filter | Shows `−$2,513`; NaN/inf show `n/a` | `0dc55d5` |
| "Card: None", "Monthly shortfall: None" | templates | "No card", "No shortfall" | `df2b035` |
| Loan check said "Rate entered by the user" for a Bank of Canada rate picked from the list | `loan_result.html` | Names the product and source | `9c9e5dc` |
| "Adding standing orders ($2,330) that F doesn't already count gives $2,330" when nothing was added | `customer.html` | Says the standing orders are already in F | `a75491a` |
| Backup plan said "The one-off cost wipes out the buffer" when there was no one-off cost (savings already negative) | `plan_result.html` | Plain wording in the template; engine text logged as a Known Issue | `9c9e5dc` |
| I moved Sources out of the nav and broke `test_nav_links_all_point_to_real_pages` | `base.html` | Put it back | `4b9df0f` |

## Not tested

- The real Gemini calls (twist card, statement fallback): no API key on this machine.
- Uploading real bank statements: only the existing test fixtures (via the test suite).
- Real phones: "phone" checks were headless Edge at about 500px wide (its minimum), not a real device.
- Browsers other than Edge (Chromium engine).
