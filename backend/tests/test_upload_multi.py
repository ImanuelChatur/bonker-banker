import io
from pathlib import Path

import pytest

import config
from app import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path)
    return create_app().test_client()


def pdf(name, as_name=None):
    return ((FIXTURES / name).open("rb"), as_name or name)


def post(client, files):
    return client.post("/upload", data={"files": files}, content_type="multipart/form-data")


def test_several_statements_in_one_go(client):
    r = post(client, [pdf("tangerine_sample.pdf"), pdf("scotia_sample.pdf"), pdf("simple_sample.pdf")])
    html = r.data.decode()
    assert r.status_code == 200
    assert "3 of 3 statements parsed" in html
    assert "tangerine" in html and "scotiabank" in html            # each file got its own parser
    assert "Everything below combines all 3 statements" in html
    assert "<th>Statement</th>" in html                            # table shows which file each row came from


def test_one_bad_file_does_not_sink_the_others(client):
    r = post(client, [pdf("tangerine_sample.pdf"), (io.BytesIO(b"definitely not a pdf"), "notes.pdf")])
    html = r.data.decode()
    assert r.status_code == 200
    assert "1 of 2 statement" in html and "1 failed" in html
    assert "Not a PDF file." in html and "HYDRO ONE BILL PAYMENT" in html


def test_same_statement_twice_is_counted_once(client):
    r = post(client, [pdf("tangerine_sample.pdf", "march.pdf"), pdf("tangerine_sample.pdf", "march-copy.pdf")])
    html = r.data.decode()
    assert "2 of 2 statements parsed" in html
    assert html.count("HYDRO ONE BILL PAYMENT") == 1               # merged view removed the duplicate rows
    assert "7 new" in html and "0 new" in html                     # and the ledger only stored them once


def test_everything_failing_is_a_400_with_reasons(client):
    r = post(client, [(io.BytesIO(b"nope"), "a.pdf"), (io.BytesIO(b"nope"), "b.pdf")])
    assert r.status_code == 400
    assert r.data.decode().count("Not a PDF file.") == 2


def test_limits(client):
    assert client.post("/upload", data={}, content_type="multipart/form-data").status_code == 400
    too_many = [(io.BytesIO(b"%PDF-"), f"{i}.pdf") for i in range(config.MAX_FILES + 1)]
    r = post(client, too_many)
    assert r.status_code == 400 and f"at most {config.MAX_FILES}" in r.data.decode()


def test_old_single_file_field_still_works(client):
    with (FIXTURES / "tangerine_sample.pdf").open("rb") as f:
        r = client.post("/upload", data={"file": (f, "s.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 200 and b"1 of 1 statement parsed" in r.data
