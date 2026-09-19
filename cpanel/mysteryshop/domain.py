from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

TARGET_CITIES = (
    "Addis Ababa",
    "Belle Mare",
    "Conakry",
    "Brazzaville",
    "Juba",
    "Freetown",
)

SCORE_FIELDS = (
    "greeting_score",
    "attentiveness_score",
    "professionalism_score",
    "cleanliness_score",
    "comfort_score",
)


class VisitValidationError(ValueError):
    """Raised when submitted visit data is structurally invalid or unsafe to accept."""


@dataclass(frozen=True)
class QaResult:
    status: str
    issues: tuple[str, ...]


def _decimal(value: Any, field: str, *, required: bool = True) -> Decimal | None:
    if value in (None, ""):
        if required:
            raise VisitValidationError(f"{field} is required")
        return None
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise VisitValidationError(f"{field} must be a valid monetary amount") from exc
    if number < 0:
        raise VisitValidationError(f"{field} cannot be negative")
    return number


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_dt(date_text: str, time_text: str, field: str) -> datetime:
    try:
        return datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise VisitValidationError(f"{field} must use YYYY-MM-DD and HH:MM") from exc


def normalize_visit(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize user-supplied visit data into a storage-ready mapping."""
    required_text = (
        "assignment_city",
        "venue_code",
        "visit_date",
        "arrival_time",
        "departure_time",
        "beverage_type",
        "ordered_item",
        "currency",
        "payment_method",
        "observations",
    )
    missing = [field for field in required_text if not str(payload.get(field, "")).strip()]
    if missing:
        raise VisitValidationError("Missing required fields: " + ", ".join(missing))

    city = str(payload["assignment_city"]).strip()
    if city not in TARGET_CITIES:
        raise VisitValidationError("assignment_city must be one of the configured target cities")

    normalized: dict[str, Any] = {
        key: str(payload[key]).strip() for key in required_text
    }

    arrival = _parse_dt(normalized["visit_date"], normalized["arrival_time"], "arrival_time")
    departure = _parse_dt(normalized["visit_date"], normalized["departure_time"], "departure_time")
    if departure <= arrival:
        raise VisitValidationError("departure_time must be later than arrival_time")
    if (departure - arrival).total_seconds() > 8 * 3600:
        raise VisitValidationError("visit duration cannot exceed 8 hours")

    for field in SCORE_FIELDS:
        try:
            score = int(payload.get(field, 0))
        except (TypeError, ValueError) as exc:
            raise VisitValidationError(f"{field} must be an integer from 1 to 5") from exc
        if score < 1 or score > 5:
            raise VisitValidationError(f"{field} must be between 1 and 5")
        normalized[field] = score

    try:
        wait_minutes = int(payload.get("wait_minutes", 0))
    except (TypeError, ValueError) as exc:
        raise VisitValidationError("wait_minutes must be a whole number") from exc
    if wait_minutes < 0 or wait_minutes > 180:
        raise VisitValidationError("wait_minutes must be between 0 and 180")
    normalized["wait_minutes"] = wait_minutes

    expected = _decimal(payload.get("expected_amount"), "expected_amount")
    charged = _decimal(payload.get("charged_amount"), "charged_amount")
    receipt_provided = _bool(payload.get("receipt_provided"))
    receipt_amount = _decimal(payload.get("receipt_amount"), "receipt_amount", required=False)

    if receipt_provided and receipt_amount is None:
        raise VisitValidationError("receipt_amount is required when receipt_provided is selected")
    if not receipt_provided and receipt_amount is not None:
        raise VisitValidationError("receipt_amount must be empty when no receipt was provided")

    normalized["expected_amount"] = str(expected)
    normalized["charged_amount"] = str(charged)
    normalized["receipt_amount"] = str(receipt_amount) if receipt_amount is not None else None
    normalized["receipt_provided"] = receipt_provided
    normalized["pricing_explained"] = _bool(payload.get("pricing_explained"))
    normalized["alcohol_ordered"] = _bool(payload.get("alcohol_ordered"))
    normalized["age_eligibility_confirmed"] = _bool(payload.get("age_eligibility_confirmed"))
    normalized["is_demo"] = _bool(payload.get("is_demo"))

    if normalized["alcohol_ordered"] and not normalized["age_eligibility_confirmed"]:
        raise VisitValidationError(
            "age_eligibility_confirmed is required when an alcoholic drink is recorded"
        )

    permission = str(payload.get("photo_permission_status", "not_taken")).strip()
    if permission not in {"not_taken", "allowed_by_assignment", "unclear"}:
        raise VisitValidationError("Invalid photo_permission_status")
    normalized["photo_permission_status"] = permission

    normalized["staff_identifier"] = str(payload.get("staff_identifier", "")).strip()
    normalized["receipt_filename"] = str(payload.get("receipt_filename", "")).strip()
    photo_filenames = payload.get("photo_filenames", [])
    if isinstance(photo_filenames, str):
        photo_filenames = [item.strip() for item in photo_filenames.split(",") if item.strip()]
    normalized["photo_filenames"] = list(photo_filenames)

    if normalized["photo_filenames"] and permission != "allowed_by_assignment":
        raise VisitValidationError(
            "photo evidence may only be attached when assignment permission is recorded"
        )

    return normalized


def compute_metrics(visit: dict[str, Any]) -> dict[str, Any]:
    """Compute transparent score and payment checks from a normalized visit."""
    greeting = int(visit["greeting_score"])
    attention = int(visit["attentiveness_score"])
    professionalism = int(visit["professionalism_score"])
    cleanliness = int(visit["cleanliness_score"])
    comfort = int(visit["comfort_score"])

    service_points = round(((greeting + attention + professionalism) / 15) * 45, 1)
    atmosphere_points = round(((cleanliness + comfort) / 10) * 25, 1)

    charged = Decimal(str(visit["charged_amount"]))
    expected = Decimal(str(visit["expected_amount"]))
    expected_delta = (charged - expected).quantize(Decimal("0.01"))

    receipt_amount = visit.get("receipt_amount")
    receipt_delta: Decimal | None = None
    payment_match = False
    if visit.get("receipt_provided") and receipt_amount not in (None, ""):
        receipt_delta = (charged - Decimal(str(receipt_amount))).quantize(Decimal("0.01"))
        payment_match = abs(receipt_delta) <= Decimal("0.01")

    payment_points = 20.0 if payment_match else 0.0
    evidence_points = 0.0
    if visit.get("receipt_provided"):
        evidence_points += 5.0
    if visit.get("pricing_explained"):
        evidence_points += 5.0

    total_score = round(service_points + atmosphere_points + payment_points + evidence_points, 1)
    return {
        "service_points": service_points,
        "atmosphere_points": atmosphere_points,
        "payment_points": payment_points,
        "evidence_points": evidence_points,
        "total_score": total_score,
        "expected_delta": str(expected_delta),
        "receipt_delta": str(receipt_delta) if receipt_delta is not None else None,
        "payment_match": payment_match,
    }


def assess_qa(visit: dict[str, Any], *, evidence_exists: bool = False) -> QaResult:
    """Apply the QA gate used before a report is considered submission-ready."""
    if visit.get("is_demo"):
        return QaResult("DEMO_ONLY", ("Synthetic record; not valid for client submission.",))

    issues: list[str] = []
    metrics = compute_metrics(visit)

    if len(str(visit.get("observations", "")).strip()) < 60:
        issues.append("Observations are too short; provide at least 60 characters of factual detail.")
    if not visit.get("receipt_provided"):
        issues.append("No receipt was provided; explain this explicitly in the client survey.")
    elif not evidence_exists:
        issues.append("Receipt was recorded but receipt evidence is not attached.")
    if visit.get("receipt_provided") and not metrics["payment_match"]:
        issues.append("Charged amount does not match the receipt amount.")
    if visit.get("photo_filenames") and visit.get("photo_permission_status") != "allowed_by_assignment":
        issues.append("Photo evidence lacks recorded assignment permission.")
    if abs(Decimal(metrics["expected_delta"])) > Decimal("0.01"):
        issues.append("Charged amount differs from the expected/menu amount; verify or explain.")

    return QaResult("READY" if not issues else "NEEDS_REVIEW", tuple(issues))


def summarize(visits: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = list(visits)
    if not records:
        return {
            "count": 0,
            "average_score": 0.0,
            "ready_count": 0,
            "review_count": 0,
            "demo_count": 0,
            "payment_mismatch_count": 0,
        }

    scores = [float(item.get("total_score", compute_metrics(item)["total_score"])) for item in records]
    return {
        "count": len(records),
        "average_score": round(sum(scores) / len(scores), 1),
        "ready_count": sum(1 for item in records if item.get("qa_status") == "READY"),
        "review_count": sum(1 for item in records if item.get("qa_status") == "NEEDS_REVIEW"),
        "demo_count": sum(1 for item in records if item.get("qa_status") == "DEMO_ONLY"),
        "payment_mismatch_count": sum(1 for item in records if not bool(item.get("payment_match"))),
    }