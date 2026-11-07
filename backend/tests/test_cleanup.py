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
