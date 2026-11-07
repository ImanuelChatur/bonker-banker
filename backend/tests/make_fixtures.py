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


# Scotiabank-style: year-less dates, unsigned amounts + balance, merchant on the next line, a period line
# without a year on its first date, a sidebar interleaved between rows on page 2, and a merchant that
# repeats on several pages. All names and numbers are fake.
SCOTIA_LINES = [
    "FAKE BANK PRIVATE",
    "SBSAV16000_1234567_007 E D 11111 22222",
    "Sep 10 Opening Balance 1,000.00",
    "Sep 11 Point of sale purchase 10.00 990.00",
    "Apos Rabba Fine Food Oakville ONCA",
    "Sep 12 Deposit 200.00 1,190.00",
    "12345678 Free Interac E-Transfer",
    "Page 1 of 3",
    "---PAGE---",
    "Sep 13 Point of sale purchase 5.50 1,184.50",
    "Opos Doordashoshawa +16505551234ONCA",
    "Sep 14 Point of sale purchase 7.90 1,176.60",
    "Apos Rabba Fine Food Oakville ONCA",
    "MR TEST PERSON",
    "Your account number:",
    "Questions?",
    "Call 1 800 4-SCOTIA (1",
    "800 555-0100)",
    "For online account access:",
    "YourPreferredPackageaccountsummary www.scotiabank.com",
    "Opening Balance on September 10, 2026 $1,000.00",
    "Here's what happened in your account this statement period",
    "September 10 to October 9, 2026 12345678",
    "Sep 15 Withdrawal 20.00 1,156.60",
    "99999999 Free Interac E-Transfer",
    "Page 2 of 3",
    "---PAGE---",
    "Oct 1 Point of sale purchase 3.00 1,153.60",
    "Apos Rabba Fine Food Oakville ONCA",
    "Oct 2 Point of sale purchase 4.00 1,149.60",
    "Oct 9 Closing Balance $1,149.60",
    "Page 3 of 3",
]


def make_pdf(path: Path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 750
    for ln in lines:
        if ln == "---PAGE---":
            c.showPage()
            y = 750
            continue
        c.drawString(50, y, ln)
        y -= 18
    c.save()


def main() -> None:
    FIXTURES.mkdir(exist_ok=True)
    make_pdf(FIXTURES / "tangerine_sample.pdf", TANGERINE_LINES)
    make_pdf(FIXTURES / "simple_sample.pdf", SIMPLE_LINES)
    make_pdf(FIXTURES / "scotia_sample.pdf", SCOTIA_LINES)


if __name__ == "__main__":
    main()
