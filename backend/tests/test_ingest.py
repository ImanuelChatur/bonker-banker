from datetime import date
from decimal import Decimal
from pathlib import Path

from ingest import parse_pdf
from ingest.ledger import Ledger

FIXTURES = Path(__file__).parent / "fixtures"   # fake statements, committed


def test_tangerine_parse():
    st = parse_pdf(FIXTURES / "tangerine_sample.pdf")
    assert st.bank == "tangerine" and st.account == "3456"
    assert st.opening_balance == Decimal("1000.00")
    assert st.closing_balance == Decimal("3130.56")
    assert len(st.transactions) == 7
    amounts = [t.amount for t in st.transactions]
    assert amounts[0] == Decimal("2500.00") and amounts[1] == Decimal("-120.45")
    # wrapped description joined onto the transfer row, credit sign from balance delta
    assert "RENT SHARE" in st.transactions[-1].description
    assert st.transactions[-1].amount == Decimal("300.00")
    assert st.transactions[0].date == date(2024, 3, 1)
    assert not st.warnings


def test_year_rollover_and_sign_inference():
    st = parse_pdf(FIXTURES / "simple_sample.pdf")
    assert [t.date for t in st.transactions] == [date(2023, 12, 20), date(2023, 12, 28), date(2024, 1, 3)]
    assert [t.amount for t in st.transactions] == [Decimal("1000.00"), Decimal("-85.20"), Decimal("-700.00")]
    assert all(t.sign_inferred for t in st.transactions)


def test_ledger_idempotent_and_categories():
    led = Ledger(":memory:")
    st = parse_pdf(FIXTURES / "tangerine_sample.pdf")
    assert led.add_statement(st) == 7
    assert led.add_statement(parse_pdf(FIXTURES / "tangerine_sample.pdf")) == 0   # re-upload
    cats = {r["description"][:6]: r["category"] for r in led.transactions()}
    assert cats["HYDRO "] == "household_bills" and cats["INTACT"] == "insurance"
    assert cats["AUTO L"] == "loan_payments"
    assert sum(1 for r in led.transactions() if r["description"].startswith("STARBUCKS")) == 2


def test_upload_route(tmp_path, monkeypatch):
    import config
    from app import create_app
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path)
    client = create_app().test_client()
    with open(FIXTURES / "tangerine_sample.pdf", "rb") as f:
        r = client.post("/upload", data={"file": (f, "s.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 200 and b"tangerine" in r.data and b"HYDRO ONE" in r.data
    r = client.post("/upload", data={"file": (__import__("io").BytesIO(b"hello"), "x.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_wire_and_summary_columns():
    from ingest.categorize import categorize
    from decimal import Decimal as D
    assert categorize("Credit memo 1/Abdullah Devrim Ozturk Wire Payment", D("15000")) == "transfers_in"
    assert categorize("MB-Transfer to 73452 05181 58", D("-15000")) == "transfers_out_other"
    assert categorize("Point of sale purchase Opos Apple.Com/Bill", D("-19.20")) == "card_withdrawals"
    led = Ledger(":memory:")
    led.add_statement(parse_pdf(FIXTURES / "tangerine_sample.pdf"))
    (row,) = led.monthly_summary()
    assert row["month"] == "2024-03" and row["money_in"] == "2800.00"
    assert row["household_bills"] == "120.45" and row["insurance"] == "89.99" and row["loan_payments"] == "450.00"
    assert row["month_end_balance"] == "3130.56"
