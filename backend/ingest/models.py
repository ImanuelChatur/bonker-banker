from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Transaction:
    date: date
    description: str
    amount: Decimal                       # negative = money out, positive = money in
    balance: Optional[Decimal] = None     # balance printed on the statement, if any
    sign_inferred: bool = False           # True when direction was guessed (low confidence)
    category: str = "uncategorized"
    category_source: str = "rule"        # "rule" (keywords) or "learned" (dataset priors)
    raw: str = ""
    seq: int = 0                          # position within the statement
    source: str = ""                      # which statement file it came from (set when merging uploads)

    def key(self, account: str) -> str:
        """Stable id so re-uploading / overlapping statements don't duplicate rows."""
        norm = " ".join(self.description.upper().split())
        base = f"{account}|{self.date.isoformat()}|{self.amount}|{norm}|{self.balance}"
        return hashlib.sha1(base.encode()).hexdigest()[:20]


@dataclass
class Statement:
    source: str
    account: str = "unknown"
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    transactions: list[Transaction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bank: str = "generic"
