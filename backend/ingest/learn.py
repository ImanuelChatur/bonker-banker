"""Learns structural category priors from the Tangerine dataset and writes learned_priors.json.

The dataset has no merchant text, so this does NOT learn keywords. It learns how
direction, amount size, month-to-month recurrence and day-of-month relate to the
dataset's own categories, which is used only for rows the keyword rules can't place.

Run from backend/:  python -m ingest.learn     (trains + prints held-out accuracy)
"""
from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "raw" / "transactions.csv"
OUT = Path(__file__).with_name("learned_priors.json")

LABELS = {  # (direction, operation, purpose) -> category
    ("cash withdrawal", ""): "cash_withdrawals_genuine",
    ("interest", "interest credited"): "interest_in",
    ("cash deposit", ""): "cash_deposits",
    ("bank fee", "statement fee"): "bank_fees",
    ("bank fee", "penalty interest (negative balance)"): "bank_fees",
    ("transfer out to another bank", "household bills"): "household_bills",
    ("bill payment", "household bills"): "household_bills",
    ("transfer out to another bank", ""): "transfers_out_other",
    ("transfer in from another bank", ""): "transfers_in",
    ("transfer in from another bank", "pension"): "pension_in",
    ("transfer out to another bank", "insurance"): "insurance",
    ("bill payment", "insurance"): "insurance",
    ("transfer out to another bank", "loan payment"): "loan_payments",
    ("card withdrawal", ""): "card_withdrawals",
}


def amount_bucket(a: float) -> int:
    return int(math.floor(math.log10(max(a, 0.01)) * 4))      # quarter-decade buckets


def recur_bucket(n: int) -> int:
    return 0 if n == 0 else 1 if n <= 2 else 2 if n <= 5 else 3


def features(direction: str, amount: float, recurrence: int, day: int) -> tuple:
    """direction: 'in'|'out'; recurrence = other months with the same amount in this account."""
    return (direction, amount_bucket(amount), recur_bucket(recurrence), min(day // 8, 3))


def load():
    rows = []
    with open(DATA, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cat = LABELS.get((r["operation"], r["purpose"]))
            if cat:
                rows.append((r["account_id"], r["date"], "in" if r["direction"].startswith("cre") else "out",
                             float(r["amount"]), cat))
    months_by_key = defaultdict(set)
    for acct, d, dr, amt, _ in rows:
        months_by_key[(acct, dr, round(amt))].add(d[:7])
    out = []
    for acct, d, dr, amt, cat in rows:
        rec = len(months_by_key[(acct, dr, round(amt))] - {d[:7]})
        out.append((acct, features(dr, amt, rec, int(d[8:10])), cat))
    return out


def train(samples):
    table = defaultdict(Counter)
    for _, f, cat in samples:
        table[f][cat] += 1
    return table


def predict(table, f):
    c = table.get(f)
    if not c:
        return None, 0.0
    cat, n = c.most_common(1)[0]
    return cat, n / sum(c.values())


def main() -> None:
    samples = load()
    accts = sorted({a for a, _, _ in samples})
    random.Random(7).shuffle(accts)
    test_accts = set(accts[: len(accts) // 5])
    tr = [s for s in samples if s[0] not in test_accts]
    te = [s for s in samples if s[0] in test_accts]
    table = train(tr)
    base = {d: Counter(c for _, f, c in tr if f[0] == d).most_common(1)[0][0] for d in ("in", "out")}
    hit = base_hit = cov = hit_conf = 0
    for _, f, cat in te:
        p, conf = predict(table, f)
        hit += p == cat
        base_hit += base[f[0]] == cat
        if conf >= 0.6:
            cov += 1
            hit_conf += p == cat
    n = len(te)
    print(f"held-out rows {n}: model {hit/n:.1%} vs direction-only baseline {base_hit/n:.1%}")
    print(f"confidence>=0.6 covers {cov/n:.1%} of rows with {hit_conf/max(cov,1):.1%} accuracy")

    final = train(samples)                               # ship the model trained on everything
    priors = {"|".join(map(str, f)): {"category": c.most_common(1)[0][0],
                                       "confidence": round(c.most_common(1)[0][1] / sum(c.values()), 3),
                                       "n": sum(c.values())}
              for f, c in final.items() if sum(c.values()) >= 30}
    OUT.write_text(json.dumps(priors, indent=0), encoding="utf-8")
    print(f"wrote {len(priors)} priors to {OUT.name}")


if __name__ == "__main__":
    main()
