# What changed overnight

Branch `overnight`, on top of `main` at `85318eb` (every commit is listed in `OVERNIGHT_LOG.md`). Goal: easy to understand at first sight, with the
depth still one click away. **No calculation, engine file, precompute output or test expectation was changed**; all
112 tests pass. Screenshots: `docs/reports/screenshots/` (`before_*` = `main`, `after_*` = this branch, account 36359).

## Across the app

- **Simple / Advisor toggle** in the nav (and beside the brand on phones). Simple is the default. Advisor content is
  hidden with CSS, never removed; the choice is remembered in the browser. A link can pick the view with
  `?view=advisor` or `?view=simple`.
- **Every page answers one question first**, as a sentence, then one big number and at most three supporting
  numbers, then one primary button leading to the next step: Customer → Shock Lab → Plan.
- **Plain-language tooltips** on jargon (runway, savings, EI, realistic EI, fixed costs, true fixed costs, shortfall)
  and a **"How to read this"** expander on Customer, Shock Lab, Plan and Insights.
- **Colour only means good / warn / bad.** Charts now draw plain lines in neutral ink (the balance line was orange);
  the heatmap scales to red; bars are grey unless they mean something.
- **Design system layer** `static/css/ui.css`, loaded last: spacing and type scale, page skeleton (question, lead
  sentence, hero, supporting numbers, next step), tabs, tooltips, notices, phone fixes. Existing classes untouched.
- **Friendly empty, loading and error states**: "Pick a customer to start" with sample accounts; an "Updating…" pill
  during live updates; a proper page for unknown accounts and unknown URLs (it used to be a bare text snippet or
  Flask's "Not Found"); a useful message when the twist-card assistant is unavailable.
- **Wording for customers and advisors**, not judges: "the judges' numbers / formula" → "the standard numbers /
  formula"; the demo page is "One account, start to finish".

## Page by page

| Page | Before | After |
| :-- | :-- | :-- |
| **Home** | Tagline, search, three named samples, a "Judges:" link, headline stat, three links | Tagline, one search, headline stat (in "bad" red), three **numbered steps** with their questions, four sample-account chips, plain link to the one-page walkthrough |
| **Customer** | Hero runway with a resilience ring; peers, profile and a "Details" card with five expanders always on screen | Question + lead sentence ("They spend $801 a month more than they earn, so their savings would last about 36.1 months"), hero runway, three numbers (savings, monthly in − out, months on EI after a job loss), one chart with the spending mix in a tab, **Stress-test this customer**. Score, peers, profile, true fixed costs and I/S/F/H/B/P → Advisor |
| **Shock Lab** | All sliders, rate hike, realistic EI, dollar inputs, save and twist card on screen; result card with "what changed" and the formula always open | Presets + job-loss and cost sliders; rate hike, realistic EI and exact dollars under **More options** (opens by itself in Advisor, or when a preset/twist uses them); save folded away. Result leads with a sentence ("With this shock, their savings would last 2 months, down from 36.1 months"), hero, two supporting numbers, the EI check, one chart; the worked formula in an expander; **Make a plan for this** carries the shock to Plan |
| **Plan** | Goal plan, actions table, backup plan and full shock card stacked | Lead sentence, hero = amount still to save (progress bar), three numbers, **top three actions**, backup line, **Print the runway report**. Full table, backup detail and the shock card → Advisor. Plan now uses the settings passed from the Shock Lab |
| **Plan → loan** | Verdict + prepay-vs-save strategies | Verdict; strategies → Advisor; the rate line names the Bank of Canada product instead of "Rate entered by the user" |
| **Insights** | Hero, heatmap, 8-row call list, "What predicts trouble" and "More" with expanders | Lead + hero + three numbers; one card with tabs (Every shock / Who is hit hardest / What predicts default / Where they live); call list = top 5 in Simple, all 50 with every reason in Advisor |
| **Sign in / sign up** | Username and password only | **"I'm a customer" / "I'm an advisor"** opens the app in Simple or Advisor view. Says the data is anonymized sample data and asks for a password not used elsewhere. **Create one in under a minute** button so nobody is stuck. Still real password login (it protects the hosted site) |

## Bugs fixed

- `/customer/21132` crashed (500) for an account whose typical income is $0; this bug is also on `main`.
- Negative money printed as `$-2,513`; "Card: None"; "Customer for 1 years".
- "Adding standing orders ($2,330) that F doesn't already count gives $2,330" when nothing was added.
- Plan said "The one-off cost wipes out the buffer" when there was no one-off cost (template only; the engine text
  is a Known Issue).
- A malformed reply from the assistant would have shown "Account not found".

## Docs added

`README.md` (new), and in `docs/reports/`: `OVERNIGHT_LOG.md`, this file, `DEMO_GUIDE.md`, `KEY_FINDINGS.md` (+
`compute_key_findings.py`, which recomputes every number), `QA_REPORT.md`, `KNOWN_ISSUES_AND_QA_PREP.md`, screenshots.

## Commits you might want to drop, and why

The commits are small, but `ui.css` is appended to in order by many of them, so **use `git revert <hash>`** rather
than dropping a commit from the middle of the history.

| Commit | What | Why you might drop it |
| :-- | :-- | :-- |
| `c107515` Friendly error pages | Adds an `errorhandler(Exception)` | In `--debug` mode an unexpected error now shows the friendly page instead of Flask's interactive debugger (the traceback still goes to the log). Developers may prefer the debugger; keep the 404 and unknown-account parts |
| `f1b84bc` Sign-in role choice | Customer/advisor choice at sign-in | If you'd rather keep sign-in to username and password only. Nothing else depends on it |
| `ab39294` Calm chart colours | Neutral lines, red heatmap | Taste: lines are now dark ink rather than orange. **This commit also carries the CSS that stops pages scrolling sideways on narrow screens and the phone-toggle CSS used by `604c49c`**, so revert only the `charts.js` part if you want the old colours |
| `0dc55d5` Money filter | `−$2,513` with a Unicode minus | If anything copies amounts as text and expects an ASCII hyphen |
| `90f721d` Home | Removed the "Judges:" line | If you present to judges and want that link labelled for them again |
| `188a7f0` Screenshots | ~1.8 MB of PNGs in `docs/reports/screenshots/` | If you don't want binaries in the repo (the demo guide's offline fallback mentions them) |

## Not done

- Upload, Report, Compare and Sources were not restructured. Report and Sources wording was tidied; Upload and Report were checked by screenshot; Compare only through the existing tests and the unknown-account check.
- No change to `main`, to the engine, to `scripts/` or to test expectations.
