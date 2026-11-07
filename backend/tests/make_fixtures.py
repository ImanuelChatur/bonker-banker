"""Generates FAKE sample statements (never real data) into tests/fixtures/.

Only needed to regenerate the committed PDFs (requires: pip install reportlab).
Run from backend/:  python -m tests.make_fixtures
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURES = Path(__file__).parent / "fixtures"

TANGERINE_LINES = [
    "Tangerine Chequing Account Statement",
    "Account Number: 4000123456",
    "Statement Period: 01 Mar 2024 - 31 Mar 2024",
    "Date Description Amount Balance",
    "Opening Balance 1,000.00",
    "01 Mar 2024 PAYROLL ACME CORP 2,500.00 3,500.00",
    "03 Mar 2024 HYDRO ONE BILL PAYMENT -120.45 3,379.55",
    "05 Mar 2024 INTACT INSURANCE PREMIUM -89.99 3,289.56",
    "05 Mar 2024 STARBUCKS #1234 -4.50 3,285.06",
    "05 Mar 2024 STARBUCKS #1234 -4.50 3,280.56",
    "12 Mar 2024 AUTO LOAN PAYMENT -450.00 2,830.56",
    "12 Mar 2024 Interac e-Transfer from J SMITH",
    "RENT SHARE 300.00 3,130.56",
    "Closing Balance 3,130.56",
]

# Month/day only, unsigned amounts, no balance column (sign must be inferred).
SIMPLE_LINES = [
    "Statement Period: December 15, 2023 - January 14, 2024",
    "Account No: 9876",
    "12/20 DIRECT DEPOSIT EMPLOYER 1,000.00",
    "12/28 ROGERS WIRELESS 85.20",
    "01/03 MORTGAGE PAYMENT 700.00",
]


def make_pdf(path: Path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 750
    for ln in lines:
        c.drawString(50, y, ln)
        y -= 18
    c.save()


def main() -> None:
    FIXTURES.mkdir(exist_ok=True)
    make_pdf(FIXTURES / "tangerine_sample.pdf", TANGERINE_LINES)
    make_pdf(FIXTURES / "simple_sample.pdf", SIMPLE_LINES)


if __name__ == "__main__":
    main()
