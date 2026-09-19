from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for

from mysteryshop.domain import TARGET_CITIES, VisitValidationError, summarize
from mysteryshop.evidence import EvidenceError, save_evidence
from mysteryshop.exporters import visit_to_markdown, visits_to_csv
from mysteryshop.storage import VisitStore

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("MYSTERY_DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = Path(os.getenv("MYSTERY_UPLOAD_DIR", DATA_DIR / "evidence"))
DB_PATH = Path(os.getenv("MYSTERY_DB_PATH", DATA_DIR / "mystery_shop.db"))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
    MAX_CONTENT_LENGTH=int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
)
store = VisitStore(DB_PATH)


@app.get("/")
def index():
    visits = store.list_visits()
    return render_template("index.html", visits=visits, summary=summarize(visits))


@app.route("/visit/new", methods=["GET", "POST"])
def new_visit():
    if request.method == "POST":
        receipt_filename = ""
        photo_filenames: list[str] = []
        try:
            receipt = request.files.get("receipt_file")
            if receipt and receipt.filename:
                receipt_filename = save_evidence(receipt, UPLOAD_DIR)
            for upload in request.files.getlist("photo_files"):
                if upload and upload.filename:
                    photo_filenames.append(save_evidence(upload, UPLOAD_DIR))

            payload = request.form.to_dict()
            payload["receipt_filename"] = receipt_filename
            payload["photo_filenames"] = photo_filenames
            payload["is_demo"] = False
            evidence_exists = bool(receipt_filename)
            visit = store.add_visit(payload, evidence_exists=evidence_exists)
            flash(f"Visit saved with QA status {visit['qa_status']}.", "success")
            return redirect(url_for("visit_detail", visit_id=visit["id"]))
        except (VisitValidationError, EvidenceError) as exc:
            for filename in [receipt_filename, *photo_filenames]:
                (UPLOAD_DIR / filename).unlink(missing_ok=True)
            flash(str(exc), "error")

    return render_template("visit_form.html", cities=TARGET_CITIES)


@app.get("/visit/<visit_id>")
def visit_detail(visit_id: str):
    try:
        visit = store.get_visit(visit_id)
    except KeyError:
        abort(404)
    return render_template("report.html", visit=visit)


@app.get("/exports/visits.csv")
def export_visits_csv():
    visits = store.list_visits()
    store.log_action("csv_export", None, f"records={len(visits)}")
    return Response(
        visits_to_csv(visits),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=mystery-shopping-visits.csv"},
    )


@app.get("/exports/visit/<visit_id>.md")
def export_visit_markdown(visit_id: str):
    try:
        visit = store.get_visit(visit_id)
    except KeyError:
        abort(404)
    store.log_action("markdown_export", visit_id, "single visit report")
    return Response(
        visit_to_markdown(visit),
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=visit-{visit_id}.md"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "database": str(DB_PATH.name)}


@app.errorhandler(413)
def too_large(_error):
    flash("Upload exceeds the configured size limit.", "error")
    return redirect(url_for("new_visit")), 413


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", message="The requested visit record was not found."), 404


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )