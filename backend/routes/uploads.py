"""/upload: receive one or more statement PDFs, parse them in parallel, add them to the ledger, preview."""
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from flask import Blueprint, render_template, request

import config
from engine import goal_plan, metrics_from_rows, runway
from engine.spending import CATEGORY_LABELS, flag_unusual, merge_statements, spending_breakdown
from ingest import parse_pdf
from ingest.ledger import Ledger

from ._common import error_html

bp = Blueprint("uploads", __name__)
log = logging.getLogger(__name__)


@bp.get("/upload")
def page():
    return render_template("upload.html", max_files=config.MAX_FILES)


def _parse_one(name: str, data: bytes) -> dict:
    """Parse one uploaded file. Never raises: a bad file becomes an error entry, the rest carry on."""
    entry = {"name": name, "st": None, "error": None, "added": 0}
    if not data.startswith(b"%PDF"):                          # check content, not just the filename
        entry["error"] = "Not a PDF file."
        return entry
    if len(data) > config.MAX_FILE_BYTES:
        entry["error"] = f"Larger than {config.MAX_FILE_BYTES // (1024 * 1024)} MB."
        return entry
    try:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "statement.pdf"                       # never use the client's filename on disk
            p.write_bytes(data)
            st = parse_pdf(p)
    except Exception:                                           # damaged / encrypted / unreadable PDF
        log.exception("could not parse %s", name)
        entry["error"] = "Couldn't read this PDF. It may be damaged or password-protected."
        return entry
    if not st.transactions:
        entry["error"] = " ".join(st.warnings) or "No transactions found in this statement."
        return entry
    st.source = name
    entry["st"] = st
    return entry


@bp.post("/upload")
def receive():
    uploads = [f for f in request.files.getlist("files") + request.files.getlist("file") if f and f.filename]
    if not uploads:
        return error_html("Choose at least one PDF statement first."), 400
    if len(uploads) > config.MAX_FILES:
        return error_html(f"Upload at most {config.MAX_FILES} statements at once."), 400

    jobs = [(Path(f.filename).name, f.read()) for f in uploads]
    with ThreadPoolExecutor(max_workers=min(4, len(jobs))) as pool:     # PDFs parse independently
        entries = list(pool.map(lambda j: _parse_one(*j), jobs))

    ok = sorted((e for e in entries if e["st"]), key=lambda e: e["st"].period_start or date.min)
    ctx = {"entries": entries, "ok_count": len(ok), "failed": len(entries) - len(ok), "labels": CATEGORY_LABELS,
           "multi": len(ok) > 1, "merged": [], "accounts": [], "spend": None, "flags": [], "flag_by_index": {}}
    if not ok:
        return render_template("partials/upload_result.html", **ctx), 400

    config.UPLOAD_DIR.mkdir(exist_ok=True)
    ledger = Ledger(config.UPLOAD_DIR / "ledger.db")
    try:
        for e in ok:                                                    # oldest first, so recurrence hints build up
            e["added"] = ledger.add_statement(e["st"])
        for acct in sorted({e["st"].account for e in ok}):
            summary = ledger.monthly_summary(acct)
            m = metrics_from_rows(summary, acct) if summary else None
            ctx["accounts"].append({"account": acct, "summary": summary, "m": m,
                                    "runway": runway(m.buffer, m.income, m.spending) if m else None,
                                    "goal": goal_plan(m) if m else None})
    finally:
        ledger.close()

    merged = merge_statements([e["st"] for e in ok])      # categories were set by the ledger step above
    flags = flag_unusual(merged)
    ctx.update(merged=merged, spend=spending_breakdown(merged), flags=flags,
               flag_by_index={f.index: f for f in flags}, total_added=sum(e["added"] for e in ok))
    return render_template("partials/upload_result.html", **ctx)
