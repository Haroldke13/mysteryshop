"""CSV and Markdown output for mystery-shopping visits.

WRITTEN TO FILL A GAP, 2026-09-20. app.py calls `visits_to_csv(visits)` for
the whole set and `visit_to_markdown(visit)` for one record; both return a
string that the route wraps in a Response.

Both deliberately carry the QA verdict and its reasons. A client receiving
an export needs to see that a row is NEEDS_REVIEW and why, otherwise the QA
gate in domain.py stops at the screen it was displayed on and the export
quietly launders an unready record into a deliverable.
"""
from __future__ import annotations

import csv
import io
from typing import Any, Iterable

__all__ = ["visits_to_csv", "visit_to_markdown", "CSV_COLUMNS"]

CSV_COLUMNS = (
    "id", "created_at", "assignment_city", "venue_code", "visit_date",
    "arrival_time", "departure_time", "wait_minutes",
    "beverage_type", "ordered_item", "alcohol_ordered",
    "age_eligibility_confirmed", "staff_identifier",
    "greeting_score", "attentiveness_score", "professionalism_score",
    "cleanliness_score", "comfort_score", "total_score",
    "currency", "expected_amount", "charged_amount",
    "receipt_provided", "receipt_amount", "pricing_explained",
    "payment_method", "receipt_filename", "photo_filenames",
    "photo_permission_status", "qa_status", "qa_issues", "is_demo",
    "observations",
)


def _flat(visit: dict[str, Any], key: str) -> str:
    value = visit.get(key)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item) for item in value)
    return str(value)


def visits_to_csv(visits: Iterable[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for visit in visits:
        merged = {**visit.get("metrics", {}), **visit}
        writer.writerow([_flat(merged, column) for column in CSV_COLUMNS])
    return buffer.getvalue()


def visit_to_markdown(visit: dict[str, Any]) -> str:
    metrics = visit.get("metrics", {})
    issues = visit.get("qa_issues") or []
    out: list[str] = []
    add = out.append

    add(f"# Mystery shopping visit {visit.get('id', '')}")
    add("")
    if visit.get("is_demo"):
        add("> **DEMO RECORD — synthetic data, not valid for client submission.**")
        add("")
    add(f"**QA status:** {visit.get('qa_status', 'UNKNOWN')}")
    if issues:
        add("")
        add("Outstanding before submission:")
        for issue in issues:
            add(f"- {issue}")
    add("")

    add("## Assignment")
    for label, key in (("City", "assignment_city"), ("Venue code", "venue_code"),
                       ("Date", "visit_date"), ("Arrival", "arrival_time"),
                       ("Departure", "departure_time"), ("Wait (minutes)", "wait_minutes"),
                       ("Staff identifier", "staff_identifier")):
        add(f"- **{label}:** {_flat(visit, key) or '—'}")
    add("")

    add("## Order")
    for label, key in (("Beverage", "beverage_type"), ("Item", "ordered_item"),
                       ("Alcohol ordered", "alcohol_ordered"),
                       ("Age eligibility confirmed", "age_eligibility_confirmed")):
        add(f"- **{label}:** {_flat(visit, key) or '—'}")
    add("")

    add("## Scores")
    add("| Measure | Value |")
    add("| --- | --- |")
    for label, key in (("Greeting", "greeting_score"), ("Attentiveness", "attentiveness_score"),
                       ("Professionalism", "professionalism_score"),
                       ("Cleanliness", "cleanliness_score"), ("Comfort", "comfort_score")):
        add(f"| {label} | {_flat(visit, key)} / 5 |")
    for label, key in (("Service points", "service_points"),
                       ("Atmosphere points", "atmosphere_points"),
                       ("Payment points", "payment_points"),
                       ("Evidence points", "evidence_points"),
                       ("Total score", "total_score")):
        add(f"| {label} | {_flat(metrics, key)} |")
    add("")

    currency = visit.get("currency", "")
    add("## Payment")
    add(f"- **Expected:** {currency} {_flat(visit, 'expected_amount')}")
    add(f"- **Charged:** {currency} {_flat(visit, 'charged_amount')}")
    add(f"- **Receipt provided:** {_flat(visit, 'receipt_provided')}")
    add(f"- **Receipt amount:** {currency} {_flat(visit, 'receipt_amount') or '—'}")
    add(f"- **Charged vs expected:** {_flat(metrics, 'expected_delta')}")
    add(f"- **Charged vs receipt:** {_flat(metrics, 'receipt_delta') or '—'}")
    add(f"- **Payment match:** {_flat(metrics, 'payment_match')}")
    add(f"- **Pricing explained:** {_flat(visit, 'pricing_explained')}")
    add(f"- **Method:** {_flat(visit, 'payment_method')}")
    add("")

    add("## Evidence")
    add(f"- **Receipt file:** {_flat(visit, 'receipt_filename') or '—'}")
    add(f"- **Photos:** {_flat(visit, 'photo_filenames') or '—'}")
    add(f"- **Photo permission:** {_flat(visit, 'photo_permission_status')}")
    add("")

    add("## Observations")
    add(str(visit.get("observations", "")).strip() or "—")
    add("")
    return "\n".join(out)
