"""Scotiabank chequing / savings statements.

Layout seen: year-less dates ("Sep 9"), unsigned withdrawal/deposit amounts followed by the
running balance, merchant text on the line below, a period line "September 10 to October 9, 2026",
and a header line like "SBSAV16000_<digits>_007 E D <transit> <account>".
The generic parser handles rows and periods; this adds bank detection and the account number.
"""
import re

from ..models import Statement
from .base import StatementParser


class ScotiabankParser(StatementParser):
    name = "scotiabank"

    @classmethod
    def detect(cls, text: str) -> bool:
        return bool(re.search(r"scotiabank|4-scotia|scotiawire", text, re.I))

    def parse(self, text: str, source: str = "<text>") -> Statement:
        st = super().parse(text, source)
        # Header: "... E D 73452 57913" = transit, account. Keep only the last 4 digits of the account.
        mt = re.search(r"\bE D\s+(\d{5})\s+(\d{4,})\b", text)
        if mt:
            st.account = mt.group(2)[-4:]
        else:
            st.warnings.append("Account number not found; transactions are filed under 'unknown'.")
        return st
