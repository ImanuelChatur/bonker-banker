# Demo guide: Bonker Banker in about 5 minutes

For whoever presents. All numbers below were computed tonight with the app's own engine on the full data.

## Before you start (2 minutes, do it before people arrive)

1. `flask --app backend/app run --debug` from the repo root, then open http://127.0.0.1:5000.
   For a local demo, put `BB_AUTH=off` in `.env` so nobody has to sign in. To show the sign-in screen, leave
   login on and create an account beforehand.
2. Open these tabs in order, so each click is instant:
   - `/` (home)
   - `/customer/36359`
   - `/shock?preset=job_loss&account_id=36359`
   - `/plan?account_id=36359`
   - `/insights`
3. Click **Simple** at the top (the default). You'll switch to **Advisor** live during the demo.
4. If you have a `GEMINI_API_KEY`, try one twist card in the Shock Lab once, so the first real call isn't on stage.

## 1-minute opening

> "If your paycheque stopped tomorrow, how many months could you last? Most people don't know. Bonker Banker
> answers that for any customer in one sentence, shows what a job loss, a repair or higher bills would do,
> and turns it into a plan. It runs on real, anonymized bank data: 4,500 accounts and a million transactions.
>
> Across all of them, if everyone lost their job and their bills went up 15%, **38.7% would be out of savings
> within 6 months**, against 2.7% today. And it's not who you'd expect."

The 38.7% is on the home page, so you can point at it.

## The walk-through (about 4 minutes)

Each page answers one question, and each has one big button that leads to the next page.

| # | Page | Say | Do |
| :-- | :-- | :-- | :-- |
| 1 | **Home** | "One search box, one number, three steps." | Point at 38.7%. Click the **36359** chip ("fine until a job loss"). |
| 2 | **Customer** (36359) | "How long could they last? Today their savings aren't running down at all: income covers spending. But if they lost their job and lived on EI, the savings would last **2.1 months**." | Read the sentence at the top. Hover the dotted word **runway** to show the plain-English tooltip. |
| 3 | Same page, **Advisor** | "An advisor sees more on the same page." | Click **Advisor** at the top. Point at the **resilience score of 90, grade A**: "Healthy by every usual measure, and still two months from trouble." Click **Simple** again. |
| 4 | **Shock Lab** | "What if something goes wrong?" | Click **Stress-test this customer**. Click the presets in turn: **Laid off**, **Furnace** (a repair the size of one month's spending wipes the savings out, since it's bigger than their $20,277), **Laid off + bills +15%**. Drag the **Income on EI** slider; the answer updates as you drag. |
| 5 | Shock Lab, twist card | "Or just say it in plain English." | Type: *They lose their job (EI at 55%) and their household bills go up 15% in the same month.* Click **Interpret and run**: the sliders move to match. |
| 6 | **Plan** | "What should they do about it?" | Click **Make a plan for this**: the plan uses the shock you just tried. Read the sentence, then point at **What helps most** (top three actions, each with the months it buys). |
| 7 | **Insights** | "What do we see across all customers?" | Show the heatmap (left to right: less income; top to bottom: higher bills). Click **Who is hit hardest**: **74.2%** of customers earning over $14,500 a month run out within 6 months, against **4.8%** under $3,000. Then **What predicts default**: grade F borrowers defaulted **47.1%** of the time against **8.5%** for grade A. |
| 8 | Close | "Know your runway before life goes bonkers." | Optional: **Print the runway report** from the Plan page. |

**Shortcut:** `/demo?account_id=36359` shows customer, shock, worked formula, plan and report on one page, one click
per shock. Good for questions, or if you're short on time.

## Running any scenario fast

- **Presets** (Shock Lab): *Laid off · EI 55% · 6 mo*, *Furnace · 1 month of spending*, *Bills +15%*,
  *Laid off + bills +15%*. One click each, and each fully replaces the previous settings.
- **Sliders**: job loss on/off, income on EI, how long EI lasts, bills up, repair size. Results update live.
- **More options**: rate hike, realistic EI (capped at $729 a week), exact dollar amounts. Open by default in Advisor.
- **Twist card**: type the scenario in plain English. Needs `GEMINI_API_KEY`.
- **Links that open straight into a view**: add `?view=advisor` or `?view=simple` to any page URL,
  e.g. `/customer/20111?view=advisor`.
- **Reset to no shock** puts everything back.

## Five sample accounts

| Account | What it shows | Runway today | Job loss, EI 55% | Repair (1 month) | Score |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **20176** | **Strong.** Saves about $1,070 a month; $34,694 in savings. Makes it through 6 months of EI with $29,553 left. | No shortfall | 40.5 months | No shortfall | 100 (A) |
| **28667** | **No shortfall at all, even on EI.** Spends $1,331 of a $2,607 income; $54,102 saved. | No shortfall | No shortfall | No shortfall | 85 (A) |
| **36359** | **Fails the EI test.** Fine today (income just covers spending), grade A, but a job loss leaves 2.1 months and a one-month repair wipes out the savings. The best story. | No shortfall | 2.1 months | 0 | 90 (A) |
| **20111** | **Has a loan.** Pays $2,330 a month on a running loan and spends $2,260 a month more than it earns. Shows the loan tab and, in Advisor, prepay vs save first. | 7.8 months | 3.4 months | 4 months | 40 (D) |
| **21817** | **Fragile.** $1,943 in savings against a $2,578 monthly gap. | 0.8 months | 0.2 months | 0 | 21 (F) |

Also handy: **32078** (overdrawn on average, top of "Who to call"), **39507** (36.1 months today, 2 months on EI).

## If something fails

| Problem | What to do |
| :-- | :-- |
| **Twist card / assistant fails** (no key, no network, slow) | It shows a friendly message. Say "the same thing with one click" and use the **Laid off + bills +15%** preset: it's the same scenario as the example card. |
| **No internet at all** | Pages still load but look unstyled (Tailwind, HTMX and charts come from CDNs). Use the screenshots in `docs/reports/screenshots/` and `KEY_FINDINGS.md` for the numbers. Test on the venue network beforehand; a phone hotspot is the quickest fix. |
| **Sign-in in the way** | Set `BB_AUTH=off` in `.env` and restart. Or click **Create one in under a minute** on the sign-in page. |
| **"The data isn't ready yet"** | `python scripts/precompute.py` then `python scripts/stress_test.py`, then restart. Takes a few minutes, so do it beforehand. |
| **A page looks wrong after switching branches** | Restart the Flask server; templates are cached when not running with `--debug`. |
| **Someone types an account that doesn't exist** | The app says it can't find it and offers sample accounts. Click one. |
