import pytest

from ingest import parse_pdf
from ingest.parsers.base import _find_account

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("text, expected", [
    ("Account No: 9876\n12/20 DIRECT DEPOSIT 1,000.00", "9876"),     # must not swallow the next line's digits
    ("Account Number: ****1234", "1234"),
    ("Account # 4000 1234 5678", "5678"),
    ("account number: xxxx-4321\n15 Mar PAYROLL 100.00", "4321"),
    ("Account: •••7777", "7777"),
    ("Your account number:\nQuestions?", "unknown"),                  # label with no number on that line
])
def test_account_number_stays_on_its_own_line(text, expected):
    assert _find_account(text) == expected


def test_generic_fixture_account():
    assert parse_pdf(FIXTURES / "simple_sample.pdf", use_llm=False).account == "9876"
