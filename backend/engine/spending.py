"""Spending breakdown and unusual-purchase flags for parsed transactions.

Works on anything with .date, .description, .amount (signed, negative = money out) and .category
(see ingest.categorize). Flags are heuristics that say "worth a second look", not proof of fraud.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from statistics import median

TRANSFER_OUT = "transfers_out_other"
CARD = "card_withdrawals"

CATEGORY_LABELS = {
    "card_withdrawals": "Card purchases",
    "household_bills": "Household bills",
    "insurance": "Insurance",
    "loan_payments": "Loan payments",
    "bank_fees": "Bank fees",
    "cash_withdrawals_genuine": "Cash withdrawals",
    "transfers_out_other": "Transfers out",
    "uncategorized": "Other",
    "transfers_in": "Transfers in",
    "cash_deposits": "Deposits",
    "pension_in": "Pension",
    "interest_in": "Interest",
}

SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


# ------------------------------------------------------------------ merchants
_PREFIX = re.compile(
    r"^(?:point of sale purchase|mb-bill payment|mb-transfer to|withdrawal|deposit)\s+", re.I)
_POS_CODE = re.compile(r"^(?:opos|apos|fpos|aips|ipos)\s+", re.I)
_ALIASES = [  # (substring in lower-cased description, display name). First match wins.
    ("doordash", "DoorDash"), ("amzn", "Amazon"), ("amazon", "Amazon"), ("apple.com", "Apple"),
    ("steam", "Steam"), ("uber eats", "Uber Eats"), ("uber", "Uber"), ("tim hortons", "Tim Hortons"),
    ("rabba", "Rabba"), ("costco", "Costco"), ("dollarama", "Dollarama"), ("lcbo", "LCBO"),
    ("presto", "Presto"), ("freedom mobile", "Freedom Mobile"), ("anthropic", "Anthropic"),
    ("vape hut", "Vape Hut"), ("macs conv", "Macs Convenience"), ("e-transfer", "Interac e-Transfer"),
]


def merchant_name(description: str) -> str:
    """A stable, readable merchant label so repeat purchases group together."""
    s = _PREFIX.sub("", description.strip())
    s = _POS_CODE.sub("", s)
    low = s.lower()
    for needle, name in _ALIASES:
        if needle in low:
            return name
    s = re.sub(r"[#*/+]|\b\d[\d\-]*\b", " ", s)               # store numbers, phone numbers
    words = [w for w in s.split() if w]
    return " ".join(w.capitalize() for w in words[:2]) or description.strip()[:24]


# ------------------------------------------------------------------ merging several statements
def merge_statements(statements) -> list:
    """All transactions from several parsed statements, oldest first, with duplicates removed.

    Overlapping or re-uploaded statements share transactions; a row is a duplicate if the same
    account/date/amount/description/balance (nth occurrence) was already taken. Each kept row
    gets .source set to its statement's filename.
    """
    seen: set[str] = set()
    merged = []
    for st in statements:
        counts: dict[str, int] = defaultdict(int)
        for t in st.transactions:
            k = t.key(st.account)
            counts[k] += 1
            uid = f"{k}-{counts[k]}"
            if uid in seen:
                continue
            seen.add(uid)
            t.source = st.source
            merged.append(t)
    merged.sort(key=lambda t: (t.date, t.seq))
    return merged


# ------------------------------------------------------------------ breakdown
def _out(txns):
    return [t for t in txns if t.amount < 0]


def spending_breakdown(txns) -> dict:
    """Where the money went. 'Everyday spending' excludes transfers out (moving money isn't spending)."""
    out = _out(txns)
    inflow = sum((t.amount for t in txns if t.amount > 0), Decimal(0))
    total_out = -sum((t.amount for t in out), Decimal(0))
    everyday = [t for t in out if t.category != TRANSFER_OUT]
    everyday_total = -sum((t.amount for t in everyday), Decimal(0))
    transfers_total = total_out - everyday_total

    dates = [t.date for t in txns]
    days = max((max(dates) - min(dates)).days + 1, 1) if dates else 1

    by_cat: dict[str, dict] = defaultdict(lambda: {"total": Decimal(0), "count": 0})
    for t in everyday:
        c = by_cat[t.category]
        c["total"] += -t.amount
        c["count"] += 1
    categories = [
        {"key": k, "label": CATEGORY_LABELS.get(k, k.replace("_", " ").title()), "total": v["total"],
         "count": v["count"], "share": float(v["total"] / everyday_total * 100) if everyday_total else 0.0}
        for k, v in sorted(by_cat.items(), key=lambda kv: kv[1]["total"], reverse=True)]

    by_m: dict[str, dict] = defaultdict(lambda: {"total": Decimal(0), "count": 0})
    for t in everyday:
        m = by_m[merchant_name(t.description)]
        m["total"] += -t.amount
        m["count"] += 1
    merchants = [{"name": k, "total": v["total"], "count": v["count"]}
                 for k, v in sorted(by_m.items(), key=lambda kv: kv[1]["total"], reverse=True)[:8]]
    top = merchants[0]["total"] if merchants else Decimal(1)
    for m in merchants:
        m["bar"] = float(m["total"] / top * 100)

    biggest = min(everyday, key=lambda t: t.amount) if everyday else None
    return {
        "money_in": inflow, "money_out": total_out, "everyday": everyday_total, "transfers_out": transfers_total,
        "days": days, "avg_daily": everyday_total / days, "categories": categories, "merchants": merchants,
        "largest": {"description": biggest.description, "amount": -biggest.amount, "date": biggest.date}
        if biggest else None,
    }


# ------------------------------------------------------------------ unusual-purchase flags
@dataclass
class Flag:
    index: int                      # position in the transactions list
    severity: str                   # high | medium | low
    reasons: list[str] = field(default_factory=list)


def _mad(values: list[float], med: float) -> float:
    return median(abs(v - med) for v in values) * 1.4826


def _add(flags: dict[int, Flag], i: int, severity: str, reason: str) -> None:
    f = flags.setdefault(i, Flag(i, severity))
    if SEVERITY_RANK[severity] > SEVERITY_RANK[f.severity]:
        f.severity = severity
    f.reasons.append(reason)


def _money(v) -> str:
    return f"${abs(float(v)):,.2f}"


def flag_unusual(txns) -> list[Flag]:
    """Rule-based checks. Returns flags sorted most severe first, then by amount."""
    flags: dict[int, Flag] = {}
    merchants = [merchant_name(t.description) for t in txns]

    # 1. Card purchases far above this statement's norm (needs enough purchases to have a norm).
    card = [(i, float(-t.amount)) for i, t in enumerate(txns) if t.amount < 0 and t.category == CARD]
    if len(card) >= 8:
        vals = [a for _, a in card]
        med = median(vals)
        mad = max(_mad(vals, med), 1.0)
        for i, a in card:
            if a >= 100 and a >= 5 * med and (a - med) / mad >= 4:
                sev = "high" if a >= 1000 or a >= 10 * med else "medium"
                _add(flags, i, sev, f"{_money(a)} is about {a / med:.0f}x your typical card purchase "
                                    f"({_money(med)})")

    # 2. Far above that merchant's own usual amount.
    by_m: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for i, t in enumerate(txns):
        if t.amount < 0 and t.category == CARD:
            by_m[merchants[i]].append((i, float(-t.amount)))
    for name, rows in by_m.items():
        if len(rows) < 3:
            continue
        for i, a in rows:
            others = [x for j, x in rows if j != i]
            m = median(others)
            if a >= 50 and m > 0 and a >= 5 * m:
                _add(flags, i, "medium", f"{_money(a)} at {name} is {a / m:.0f}x your usual there ({_money(m)})")

    # 3. Possible duplicate: same merchant, same amount, within a day.
    for i, t in enumerate(txns):
        if t.amount >= 0 or abs(t.amount) < 5:
            continue
        for j in range(i):
            u = txns[j]
            if (u.amount == t.amount and merchants[j] == merchants[i]
                    and abs((t.date - u.date).days) <= 1):
                _add(flags, i, "medium", f"Same amount as an earlier charge at {merchants[i]} "
                                         f"on {u.date:%b %d} (possible duplicate)")
                break

    # 4. Many charges at one merchant in a single day.
    per_day: dict[tuple, list[int]] = defaultdict(list)
    for i, t in enumerate(txns):
        if t.amount < 0 and t.category == CARD:
            per_day[(merchants[i], t.date)].append(i)
    for (name, d), idxs in per_day.items():
        if len(idxs) >= 3:
            for i in idxs:
                _add(flags, i, "low", f"{len(idxs)} charges at {name} on {d:%b %d}")

    # 5. Purchases billed in the US (merchant location code ends in US).
    for i, t in enumerate(txns):
        if t.amount < 0 and t.category == CARD and re.search(r"[A-Z]{2}US\s*$", t.description):
            _add(flags, i, "low", "Purchase billed in the United States")

    # 6. Large transfers out, noting a matching deposit just before (money passing straight through).
    xfer = [float(-t.amount) for t in txns if t.amount < 0 and t.category == TRANSFER_OUT]
    xfer_med = median(xfer) if xfer else 0
    for i, t in enumerate(txns):
        if t.amount < 0 and t.category == TRANSFER_OUT:
            a = float(-t.amount)
            if a >= max(1000.0, 10 * xfer_med):
                note = f"Large transfer out ({_money(a)})"
                for u in txns:
                    if u.amount > 0 and abs(float(u.amount) - a) <= a * 0.01 and \
                            timedelta(0) <= t.date - u.date <= timedelta(days=5):
                        note += f", same size as a deposit on {u.date:%b %d}"
                        break
                _add(flags, i, "medium", note)

    return sorted(flags.values(),
                  key=lambda f: (-SEVERITY_RANK[f.severity], -abs(float(txns[f.index].amount))))
