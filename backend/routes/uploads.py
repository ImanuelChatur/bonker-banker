"""/upload: receive a statement PDF, parse it, add it to the ledger, preview the result."""
import tempfile
from pathlib import Path

from flask import Blueprint, render_template, request

import config
from engine import goal_plan, metrics_from_rows, runway
from ingest import parse_pdf
from ingest.ledger import Ledger

from ._common import error_html

bp = Blueprint("uploads", __name__)


@bp.get("/upload")
def page():
    return render_template("upload.html")


@bp.post("/upload")
def receive():
    f = request.files.get("file")
    if not f or not f.filename:
        return error_html("Choose a PDF statement first."), 400
    data = f.read()
    if not data.startswith(b"%PDF"):                          # check content, not just the filename
        return error_html("That file is not a PDF."), 400

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "statement.pdf"                           # never use the client's filename on disk
        p.write_bytes(data)
        st = parse_pdf(p)
    st.source = Path(f.filename).name

    config.UPLOAD_DIR.mkdir(exist_ok=True)
    ledger = Ledger(config.UPLOAD_DIR / "ledger.db")
    try:
        added = ledger.add_statement(st)
        summary = ledger.monthly_summary(st.account)
    finally:
        ledger.close()

    m = metrics_from_rows(summary, st.account) if summary else None
    return render_template("partials/upload_result.html", st=st, added=added, summary=summary, m=m,
                           runway=runway(m.buffer, m.income, m.spending) if m else None,
                           goal=goal_plan(m) if m else None)
