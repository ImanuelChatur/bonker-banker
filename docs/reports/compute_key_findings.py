"""Recompute every number quoted in docs/reports/KEY_FINDINGS.md from the app's own code and data.

Run from the repo root (needs data/processed/, i.e. scripts/precompute.py has been run):
    .venv/Scripts/python.exe docs/reports/compute_key_findings.py      (Windows)
    .venv/bin/python docs/reports/compute_key_findings.py              (macOS / Linux)
Read-only: it calls engine functions and reads data/processed; it writes nothing.
"""
import logging
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("BB_AUTH", "off")
logging.disable(logging.WARNING)

from engine import Shock, apply_shock, customer_metrics, runway          # noqa: E402
from engine import insights                                              # noqa: E402
from engine.findings import biggest_finding                              # noqa: E402
from engine.loans import affordability                                   # noqa: E402
from engine.regions import region_summary                                # noqa: E402
from services import data_store                                          # noqa: E402

data_store.load()


def section(t):
    print(f"\n## {t}")


section("1. Headline stress test  [engine.insights.headline()]")
h = insights.headline()
print(h["text"])
print("pct_runout_6m =", h["pct_runout_6m"], "| pct_runout_3m =", h["pct_runout_3m"], "| scenario =", h["scenario"])

section("2. Each standard shock alone  [engine.findings.biggest_finding()['stress']]")
f = biggest_finding()
for s in f["stress"]:
    print(f"{s['name']:40} {s['short']:>5} accounts  {s['share_pct']:>5}% out of savings within 6 months")

section("3. Stress grid extremes  [engine.insights.stress_grid()]")
grid = insights.stress_grid()
for one_off in (0, 1, 2):
    rows = [r for r in grid if r["one_off_months"] == one_off]
    worst = max(rows, key=lambda r: r["pct_runout_6m"])
    print(f"repair={one_off} months of spending: worst cell EI {worst['ei_pct']}%, bills +{worst['bills_pct']}% "
          f"-> {worst['pct_runout_6m']}%; cells: {len(rows)}")

section("4. Who is hit hardest (EI 55%, bills +15%)  [engine.insights.stress_breakdown(55, 15, 0)]")
for r in insights.stress_breakdown(55, 15, 0):
    print(f"{r['group_type']:15} {str(r['group']):18} n={r.get('n', '?'):>5}  {r['pct_runout_6m']}%")

section("5. Default prediction  [engine.findings.biggest_finding()]")
print(f["headline"])
print("borrowers scored:", f["n_loans"], "| excluded (under 6 months of pre-loan history):", f["n_excluded"])
for g in f["default_by_grade"]:
    print(f"grade {g['band']:14} loans={g['loans']:>4} defaults={g['defaults']:>3} rate={g['rate']}%")
for g in f["default_by_runway"]:
    print(f"runway {g['bucket']:12} loans={g['loans']:>4} defaults={g['defaults']:>3} rate={g['rate']}%")
print("AUC score =", f["auc_score"], "| AUC runway alone =", f["auc_runway"])
for s in f["signals"]:
    print(f"signal {s['name']:18} AUC {s['auc']}")

section("6. Regions  [engine.regions.region_summary()]")
try:
    r = region_summary()
    print(r["headline"])
    print("spearman unemployment vs score / shortfall / default:",
          r["unemployment_vs_score"], r["unemployment_vs_shortfall"], r["unemployment_vs_default"])
except Exception as e:  # regional data optional
    print("not available:", e)

section("7. Every account through the standard formula  [engine.customer_metrics + runway + apply_shock]")
ids = sorted({str(a) for a in data_store.table("monthly_summary")["account_id"].unique()})
rw, ei, ei_ok, hist, buf_neg, loan_active, afford = [], [], 0, [], 0, 0, Counter()
isb = []
job = Shock(income_factor=0.55, duration_months=6)
for a in ids:
    m = customer_metrics(a)
    r0 = runway(m.buffer, m.income, m.spending)
    j = apply_shock(m, job)
    rw.append(r0)
    ei.append(j["after"]["runway"])
    ei_ok += bool(j["survives_duration"] and j["survives_duration"]["makes_it"])
    hist.append(m.months_of_history)
    buf_neg += m.buffer < 0
    loan_active += m.loan_payment_active > 0
    afford[affordability(m, 10000, 36)["verdict"]] += 1
    isb.append((m.income, m.spending, m.buffer))
n = len(ids)
no_short = sum(isinstance(x, str) for x in rw)
num = [x for x in rw if not isinstance(x, str)]
ei_num = [120.0 if isinstance(x, str) else x for x in ei]
print("accounts:", n)
print(f"no shortfall at usual income: {no_short} ({100 * no_short / n:.1f}%)")
print(f"runway under 3 months today: {sum(x < 3 for x in num)} | 3 to 12: {sum(3 <= x < 12 for x in num)}")
print(f"median runway on EI 55% (no shortfall counted as 120): {statistics.median(ei_num):.1f} months")
print(f"survive 6 months of EI at 55%: {ei_ok} ({100 * ei_ok / n:.1f}%)")
print(f"negative savings buffer: {buf_neg} | active loan payment: {loan_active}")
print(f"history length: min {min(hist)}, median {statistics.median(hist)}, max {max(hist)} months")
print("new $10,000 loan over 36 months at the default rate:", dict(afford))

section("8. Who to call  [engine.insights.at_risk_customers(50)]")
ar = insights.at_risk_customers(50)
print("listed:", len(ar), "| runway 0 today:", sum(r["runway"] == 0 for r in ar))
print("top 3:", [(r["account_id"], r["runway"], r["reasons"][:1]) for r in ar[:3]])

section("9. Loans in the data  [data/processed/loans.parquet]")
loans = data_store.table("loans")
print("loans:", len(loans), "| columns:", list(loans.columns))
print("defaulted:", int(loans["defaulted"].sum()), f"({100 * loans['defaulted'].mean():.1f}%)",
      "| status counts:", loans["status_meaning"].value_counts().to_dict())

section("10. Why high earners are hit harder  [customer_metrics, grouped by income I]")
edges = [(-1, 3000, "under $3,000"), (3000, 5100, "$3,000-5,100"), (5100, 9900, "$5,100-9,900"),
         (9900, 14500, "$9,900-14,500"), (14500, float("inf"), "$14,500+")]
for lo, hi, name in edges:
    grp = [(i, s_, b) for i, s_, b in isb if lo < i <= hi]
    s_over_i = statistics.median([s_ / i for i, s_, b in grp if i > 0])
    b_months = statistics.median([b / s_ for i, s_, b in grp if s_ > 0])
    print(f"{name:15} n={len(grp):>4}  median spending/income {s_over_i:.2f}  median savings in months of spending {b_months:.2f}")
