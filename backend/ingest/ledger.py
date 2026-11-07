"""Builds the transactions table (SQLite) + monthly summary from parsed statements."""
from __future__ import annotations

import calendar
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from .categorize import IN_CATEGORIES, OUT_CATEGORIES, categorize_all
from .models import Statement

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions(
  id TEXT PRIMARY KEY, account TEXT, date TEXT, description TEXT,
  amount TEXT, balance TEXT, category TEXT, sign_inferred INTEGER,
  source TEXT, running_balance TEXT);
CREATE TABLE IF NOT EXISTS statements(
  source TEXT PRIMARY KEY, account TEXT, bank TEXT, period_start TEXT, period_end TEXT,
  opening_balance TEXT, closing_balance TEXT, warnings TEXT);
"""


def _s(v):
    return None if v is None else str(v)


def reconcile(st: Statement) -> list[Decimal | None]:
    """Recompute a running balance from the opening balance; warn on any mismatch."""
    running, out = st.opening_balance, []
    for t in st.transactions:
        if running is not None:
            running += t.amount
            if t.balance is not None and t.balance != running:
                st.warnings.append(
                    f"{t.date} {t.description[:30]}: printed balance {t.balance} != computed {running}")
                running = t.balance          # resync so one bad row doesn't cascade
        out.append(running)
    if running is not None and st.closing_balance is not None and running != st.closing_balance:
        st.warnings.append(f"closing balance {st.closing_balance} != computed {running}")
    return out


class Ledger:
    def __init__(self, db_path: str | Path = "ledger.db"):
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    def _recurrence_fn(self, st: Statement):
        """Months (other than the row's own) where this account had a same-size amount in the same direction."""
        seen: dict[tuple, set] = {}
        for acct, d, amt in self.db.execute("SELECT account, date, amount FROM transactions WHERE account=?",
                                            (st.account,)):
            a = Decimal(amt)
            seen.setdefault(("in" if a > 0 else "out", round(abs(a))), set()).add(d[:7])
        for t in st.transactions:
            seen.setdefault(("in" if t.amount > 0 else "out", round(abs(t.amount))), set()).add(t.date.isoformat()[:7])
        return lambda t: len(seen[("in" if t.amount > 0 else "out", round(abs(t.amount)))] - {t.date.isoformat()[:7]})

    def add_statement(self, st: Statement) -> int:
        """Insert a statement's rows (idempotent). Returns number of new transactions."""
        categorize_all(st.transactions, self._recurrence_fn(st))
        running = reconcile(st)
        new, seen = 0, {}
        for t, rb in zip(st.transactions, running):
            k = t.key(st.account)
            n = seen[k] = seen.get(k, 0) + 1       # identical same-day rows stay distinct
            cur = self.db.execute(
                "INSERT OR IGNORE INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?)",
                (f"{k}-{n}", st.account, t.date.isoformat(), t.description, str(t.amount),
                 _s(t.balance), t.category, int(t.sign_inferred), st.source, _s(rb)))
            new += cur.rowcount
        self.db.execute(
            "INSERT OR REPLACE INTO statements VALUES(?,?,?,?,?,?,?,?)",
            (st.source, st.account, st.bank, _s(st.period_start), _s(st.period_end),
             _s(st.opening_balance), _s(st.closing_balance), "\n".join(st.warnings)))
        self.db.commit()
        return new

    def transactions(self, account: str | None = None) -> list[dict]:
        q, a = "SELECT * FROM transactions", ()
        if account:
            q, a = q + " WHERE account=?", (account,)
        cur = self.db.execute(q + " ORDER BY date, rowid", a)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def monthly_summary(self, account: str | None = None) -> list[dict]:
        """One row per account-month with the same columns as the dataset's monthly_summary.csv."""
        parts = IN_CATEGORIES + OUT_CATEGORIES
        months: dict[tuple[str, str], dict] = {}
        for r in self.transactions(account):
            row = months.setdefault((r["account"], r["date"][:7]), {c: Decimal(0) for c in parts})
            amt = Decimal(r["amount"])
            cat = r["category"]
            if cat not in row:                     # uncategorized -> generic transfer bucket
                cat = "transfers_in" if amt > 0 else "transfers_out_other"
            row[cat] += abs(amt)
        # end-of-day balances (last transaction of each day wins), carried forward through the month
        eod: dict[str, dict[date, Decimal]] = {}
        for r in self.transactions(account):
            if r["running_balance"] is not None:
                eod.setdefault(r["account"], {})[date.fromisoformat(r["date"])] = Decimal(r["running_balance"])
        out = []
        for (acct, month), row in sorted(months.items()):
            y, m = map(int, month.split("-"))
            days = [date(y, m, d) for d in range(1, calendar.monthrange(y, m)[1] + 1)]
            bal = eod.get(acct, {})
            carry = next((bal[d] for d in sorted(bal, reverse=True) if d < days[0]), None)
            series = []
            for d in days:
                carry = bal.get(d, carry)
                if carry is not None:
                    series.append(carry)
            rec = {"account_id": acct, "month": month,
                   "money_in": str(sum(row[c] for c in IN_CATEGORIES)),
                   "money_out": str(sum(row[c] for c in OUT_CATEGORIES)),
                   **{c: str(row[c]) for c in parts},
                   "month_end_balance": str(series[-1]) if series else None,
                   "min_balance": str(min(series)) if series else None,
                   "avg_daily_balance": str((sum(series) / len(series)).quantize(Decimal("0.01"))) if series else None,
                   "days_below_zero": sum(1 for b in series if b < 0) if series else None}
            out.append(rec)
        return out
