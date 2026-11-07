"""Tangerine chequing / savings statements."""
import re

from ..models import Statement
from .base import StatementParser


class TangerineParser(StatementParser):
    name = "tangerine"

    @classmethod
    def detect(cls, text: str) -> bool:
        return "tangerine" in text.lower()

    def parse(self, text: str, source: str = "<text>") -> Statement:
        st = super().parse(text, source)
        # Tangerine prints the full account number; keep only the last 4 digits.
        mt = re.search(r"account\s+number\D{0,5}(\d{6,})", text, re.I)
        if mt:
            st.account = mt.group(1)[-4:]
        return st
