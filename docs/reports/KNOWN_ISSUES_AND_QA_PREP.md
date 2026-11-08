# Known issues, limitations and Q&A prep

For the team to read before presenting. Numbers quoted here were computed tonight (see `KEY_FINDINGS.md` and
`QA_REPORT.md` for how).

## Known issues: engine / numbers (not changed tonight, by rule)

1. **Backup-plan wording blames a one-off cost that isn't there.** `engine/plans.py` `backup_plan()` returns
   "The one-off cost wipes out the buffer; outside help … is needed" whenever savings are at or below zero, even
   with no one-off cost (e.g. account 32078, savings −$2,513). The Plan page now replaces this sentence in the
   template when there is no one-off cost; the engine text is unchanged and still appears in the Report's stress-test
   table.
2. **"Runway 6 months" next to "doesn't make it through 6 months".** For 18 of the 4,500 accounts, the job-loss
   runway rounds to 6.0 but the month-by-month check finds the money runs out just before month 6 (short by $10 to
   $394; e.g. 21271, 30508, 31217). Both numbers are right; it's rounding. It is also why "35.1% out of savings within
   6 months" and "64.5% survive 6 months of EI" don't add up to exactly 100%.
3. **Active loan payment (P) can be missing from fixed costs (F).** F uses the median loan payment over the whole
   history, so a loan that started recently doesn't show in F. Example: 45405 pays $6,196 a month on an active
   loan, but its F counts $0 of loan payments. Runway is unaffected (it uses total spending S, which does include
   the payments), but the fixed-cost figures understate commitments for such accounts.
4. **Loan check labels a picked rate as "entered by the user".** `routes/plans.py` passes the chosen Bank of Canada
   rate to `engine.loans.affordability()` as a custom rate, so the engine's `rate_source` says "Rate entered by the
   user". The page now shows the product and source instead; the engine field is unchanged.
5. **The spending mix doesn't add up to "spending".** The donut ("Where the money goes", and on the Report) is the
   average per category over the last 12 months; spending S is the median month over the whole history. For 20111
   the donut centre says $13,005/mo while S is $8,600. Both are correct for what they measure, but they look
   inconsistent side by side.
6. **Two different "versus peers" numbers.** The Report's "Versus peers: 3%" ranks runway against all accounts; the
   Customer page's "better than 7%" ranks against similar customers (same income band and age). Same account
   (20111), different comparison groups.
7. **Resilience grade D defaults less than grade C** (17.4% vs 25.0%), because those groups are small (23 and 24
   loans). The overall trend (A 8.5% → F 47.1%) is the finding; the middle grades are noisy.
8. **Engine text still says "the judges' formula"** in `engine/findings.py` (caveats and method). Insights replaces
   the phrase when displaying it; the engine strings are unchanged.

## Fragile or unfinished

- **Uploaded transactions are kept with no expiry and aren't separated per user** (`uploads/ledger.db`). Fine for a
  local demo; on a shared hosted site any user's upload adds to the same ledger. Fix before real customer use.
- **Gemini paths untested tonight** (no API key on this machine): the twist card's real round trip and the statement
  parser's fallback. Their error handling was tested: without a key the twist card explains what to use instead.
- **Front-end libraries come from CDNs** (Tailwind browser build, HTMX, ECharts, Google Fonts). Without internet
  the pages load but look unstyled and the charts and live updates don't work.
- **Login rate limits live in memory**: they reset when the server restarts and aren't shared between server workers.
- **Simple / Advisor is a view, not a permission.** Advisor content is in the page HTML and hidden with CSS, so
  anyone can switch to it. That's intended (it's a level-of-detail switch), but it isn't access control.
- **Phone layout was checked at about 500px wide in headless Edge**, not on a real phone; Safari and Firefox weren't
  checked.

## Limitations of the data and method

- **No interest rates on existing loans.** `loans.csv` has amount, duration and monthly payment, but no rate. The
  rate-hike shock therefore treats the remaining balance of the account's running loan as variable-rate debt and
  adds `balance × hike ÷ 12` a month (`engine/shocks.py rate_hike_cost`); accounts without a running loan show
  "no effect, no variable-rate debt". New-loan checks use current Bank of Canada rates.
- **Flat 55% EI by default.** The standard shock replaces income with 55% of the usual month for everyone. The
  optional **realistic EI** switch also applies the 2026 cap of $729 a week (about $3,159 a month), so high earners
  get less than 55%. Real EI also has waiting weeks, eligibility rules and 14 to 45 weeks of benefits depending on the
  region; none of that is modelled.
- **Standing orders are a snapshot** from the end of the data, not a history. "True fixed costs" assume today's
  standing orders applied throughout.
- **Runway is a straight-line estimate**: savings ÷ monthly shortfall at a typical month, capped at 120 months. It
  ignores interest earned, inflation and seasonal months. The "simulated runway" in Advisor view (replaying the
  account's own months in random order) is our measure for that.
- **Currency.** The app shows every amount with a "$" and does no conversion. The underlying PKDD'99 data comes from
  a Czech bank; the repo doesn't document whether the data pack rescaled the amounts. Treat amounts as relative.
- **Minimum history is 12 months** (2 accounts have exactly 12); medians on short histories are less stable.

## Likely questions, with short answers

**How is runway calculated?**
Savings (average daily balance over the last 6 months) divided by the monthly shortfall (typical spending minus
typical income). If income covers spending there's no shortfall and the savings don't run down. Capped at 120
months. Advisor view and the Shock Lab show the formula worked through with the account's own numbers.

**Why does the realistic EI number differ from the standard one?**
The standard shock pays 55% of the customer's usual income, with no ceiling. Real EI stops at $729 a week in 2026
(about $3,159 a month). For anyone whose 55% would be above that, realistic EI pays less, so their runway is shorter.

**Why are high earners hit harder by a job loss?**
In this data, the typical customer earning over $14,500 a month spends about 95% of it and has savings worth about
1.8 months of spending. The typical customer under $3,000 spends about 70% and has about 8.4 months. Losing 45% of
a large income opens a big monthly gap with little cushion. (Computed tonight; see `KEY_FINDINGS.md` section 2.)

**What happens to uploaded statements?**
The PDF is parsed in a temporary folder and deleted straight away. The transactions it contained (date,
description, amount, balance, category, filename, account number) are stored in a local database so repeat uploads
aren't double-counted. Only if our own parsers can't make the balances add up, and a Gemini key is configured, is
the statement text sent to Google's Gemini, with long numbers masked except the last 4 digits. Nothing is shared
otherwise.

**Is the resilience score part of the runway?**
No. It's our own 0 to 100 measure (runway, cash flow, fixed costs, income stability, overdraft days), labelled as
ours wherever it appears. It never changes the runway. Judged only on the months before each loan, grade F
borrowers defaulted 47.1% of the time against 8.5% for grade A.

**Why does "if income stopped today" differ from "after a job loss on EI"?**
"If income stopped" assumes no income at all; "after a job loss" assumes EI pays 55% of usual income. Both use the
same formula.

**What does Simple vs Advisor change?**
Only how much is shown. Simple answers the page's question with one number and up to three supporting numbers.
Advisor adds the resilience score, peer comparison, profile, true fixed costs, every input, loan strategies and the
full at-risk list. Nothing is calculated differently.

**Is the sign-in real?**
Yes, on the hosted site: passwords are stored only as hashes, with CSRF protection and lockout after repeated wrong
passwords. Anyone can create an account. The "customer / advisor" choice only picks the starting view. Locally,
`BB_AUTH=off` skips sign-in.

**How do you know the numbers are right?**
112 automated tests check the engine against the published formula and every page; the population stress test is
checked against the per-account engine. Tonight's work changed presentation only; no calculation or test
expectation was touched.
