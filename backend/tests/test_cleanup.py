from ingest.parsers.base import clean_desc, parse_text


def test_clean_desc_cuts_boilerplate_and_refs():
    d = ("Point of sale purchase Apos Rabba Fine Food Oakville ONCA MR DERIN Your account number: "
         "Questions? Call 1 800 4-SCOTIA For online account access: www.scotiabank.com")
    assert clean_desc(d) == "Point of sale purchase Apos Rabba Fine Food Oakville ONCA"
    assert clean_desc("Deposit 08989173 Free Interac E-Transfer ---- |") == "Deposit Free Interac E-Transfer"


def test_footer_not_appended_and_page_break_resets():
    text = "\n".join([
        "2026-09-16 Point of sale purchase Opos Eventbrite -38.61",
        "Questions? Call 1 800 4-SCOTIA",
        "MR DERIN Your account number:",
        "<<PAGE>>",
        "Some stray header line",
        "2026-09-17 Withdrawal 08955673 Free Interac E-Transfer -15.00",
    ])
    st = parse_text(text)
    assert [t.description for t in st.transactions] == [
        "Point of sale purchase Opos Eventbrite", "Withdrawal Free Interac E-Transfer"]


# ---- Scotiabank-style layout (fake fixture: backend/tests/fixtures/scotia_sample.pdf) ----
from decimal import Decimal
from datetime import date
from pathlib import Path

from ingest import parse_pdf
from ingest.categorize import categorize
from ingest.ledger import reconcile

SCOTIA = Path(__file__).parent / "fixtures" / "scotia_sample.pdf"


def test_scotia_period_account_and_balances():
    st = parse_pdf(SCOTIA, use_llm=False)
    assert st.bank == "scotiabank" and st.account == "2222"
    assert (st.period_start, st.period_end) == (date(2026, 9, 10), date(2026, 10, 9))
    assert st.opening_balance == Decimal("1000.00") and st.closing_balance == Decimal("1149.60")
    reconcile(st)
    assert not st.warnings


def test_scotia_repeated_merchants_kept_and_sidebar_not_attached():
    st = parse_pdf(SCOTIA, use_llm=False)
    descs = [t.description for t in st.transactions]
    assert descs.count("Point of sale purchase Apos Rabba Fine Food Oakville ONCA") == 3   # repeats across pages
    assert "Point of sale purchase Opos Doordashoshawa ONCA" in descs                       # phone number stripped
    assert "Withdrawal Free Interac E-Transfer" in descs and "Deposit Free Interac E-Transfer" in descs
    assert not any(w in d for d in descs for w in ("DERIN", "TEST PERSON", "Questions", "800 555", "account number"))
    assert [t.amount for t in st.transactions[:2]] == [Decimal("-10.00"), Decimal("200.00")]   # sign from balance


def test_period_falls_back_to_transaction_dates():
    st = parse_text("Sep 11 Point of sale purchase 10.00 990.00\nSep 20 Deposit 5.00 995.00")
    assert st.period_start is not None and st.period_start.month == 9 and st.period_end.day == 20


def test_scotia_category_fixes():
    D = Decimal
    assert categorize("Point of sale purchase Opos Doordashosmowsshawa ONCA", D("-23.76")) == "card_withdrawals"
    assert categorize("Error correction Apos Nayax Canada in", D("50")) == "transfers_in"
    assert categorize("Canada Essentials Benefit Canada", D("111.25")) == "transfers_in"
    assert categorize("Deposit MB-Dep", D("509.76")) == "cash_deposits"
    assert categorize("Point of sale purchase Opos Freedom Mobile 877-946-318ONCA", D("-45.20")) == "household_bills"
