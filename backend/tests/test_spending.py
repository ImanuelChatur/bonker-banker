from datetime import date
from decimal import Decimal as D
from pathlib import Path

from engine.spending import flag_unusual, merchant_name, spending_breakdown
from ingest import parse_pdf
from ingest.categorize import categorize_all
from ingest.models import Transaction

FIXTURES = Path(__file__).parent / "fixtures"


def tx(day, desc, amount, cat=None):
    t = Transaction(date=date(2026, 9, day), description=desc, amount=D(str(amount)))
    from ingest.categorize import categorize
    t.category = cat or categorize(desc, t.amount)
    return t


def card(day, name, amount):
    return tx(day, f"Point of sale purchase Opos {name} Oakville ONCA", -amount)


def test_merchant_grouping():
    assert merchant_name("Point of sale purchase Opos Doordashharveys +1650681947ONCA") == "DoorDash"
    assert merchant_name("Point of sale purchase Opos Amzn Mktp CA 866- 216-107ONCA") == "Amazon"
    assert merchant_name("Point of sale purchase Opos Amazon.ca 866-216- 107ONCA") == "Amazon"
    assert merchant_name("MB-Bill payment Sheridan College") == "Sheridan College"
    assert merchant_name("Withdrawal Free Interac E-Transfer") == "Interac e-Transfer"


def test_breakdown_excludes_transfers_from_everyday_spending():
    txns = [card(1, "Tim Hortons", 5), card(2, "Tim Hortons", 7), card(3, "Rabba", 20),
            tx(4, "MB-Transfer to 12345", -1000), tx(5, "Payroll", 500)]
    b = spending_breakdown(txns)
    assert b["money_out"] == D("1032") and b["everyday"] == D("32") and b["transfers_out"] == D("1000")
    assert b["money_in"] == D("500")
    assert [c["key"] for c in b["categories"]] == ["card_withdrawals"] and b["categories"][0]["share"] == 100
    assert b["merchants"][0]["name"] == "Rabba" and b["merchants"][1] == {
        "name": "Tim Hortons", "total": D("12"), "count": 2, "bar": 60.0}
    assert b["largest"]["amount"] == D("20") and b["days"] == 5


def test_flags_large_outlier_duplicate_and_transfer_passthrough():
    txns = [card(d, "Rabba", 8 + d) for d in range(1, 9)]                # 9..16: a normal pattern
    txns += [card(9, "Gadget Store", 480),                                # ~35x the usual
             tx(10, "Withdrawal Free Interac E-Transfer", -42.16),
             tx(10, "Withdrawal Free Interac E-Transfer", -42.16),        # duplicate
             tx(11, "Wire In", 5000), tx(12, "MB-Transfer to 999", -5000)]
    flags = {f.index: f for f in flag_unusual(txns)}
    big = flags[8]
    assert big.severity == "high" and "typical card purchase" in big.reasons[0]     # 10x+ the median = high
    assert "duplicate" in flags[10].reasons[0]
    assert 9 not in flags                                                # first of the pair isn't flagged
    assert "same size as a deposit" in flags[12].reasons[0]
    assert all(i not in flags for i in range(8))                         # normal purchases stay quiet


def test_no_outlier_flags_with_too_few_purchases():
    txns = [card(1, "Rabba", 10), card(2, "Rabba", 12), card(3, "Gadget Store", 900)]
    assert flag_unusual(txns) == []


def test_us_purchase_and_same_day_repeats():
    txns = [tx(1, "Point of sale purchase Opos Wl *Steam Purchase 425-889- 964WAUS", -9.31)]
    txns += [card(2, "Corner Cafe", 3 + i) for i in range(3)]
    flags = {f.index: f for f in flag_unusual(txns)}
    assert flags[0].severity == "low" and "United States" in flags[0].reasons[0]
    assert all("3 charges" in flags[i].reasons[0] for i in (1, 2, 3))


def test_scotia_fixture_end_to_end():
    st = parse_pdf(FIXTURES / "scotia_sample.pdf", use_llm=False)
    categorize_all(st.transactions)
    b = spending_breakdown(st.transactions)
    assert b["merchants"][0]["name"] == "Rabba" and b["merchants"][0]["count"] == 3
    assert flag_unusual(st.transactions) == []                           # nothing odd in the fake statement
