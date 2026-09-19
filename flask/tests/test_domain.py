from __future__ import annotations

import pytest

from mysteryshop.domain import VisitValidationError, assess_qa, compute_metrics, normalize_visit


def valid_payload() -> dict:
    return {
        "assignment_city": "Addis Ababa",
        "venue_code": "TEST-001",
        "visit_date": "2026-09-18",
        "arrival_time": "18:00",
        "departure_time": "19:00",
        "beverage_type": "non-alcoholic",
        "ordered_item": "Sparkling water",
        "expected_amount": "10.00",
        "charged_amount": "10.00",
        "receipt_amount": "10.00",
        "currency": "USD",
        "receipt_provided": True,
        "pricing_explained": True,
        "alcohol_ordered": False,
        "age_eligibility_confirmed": False,
        "greeting_score": 5,
        "attentiveness_score": 4,
        "professionalism_score": 5,
        "cleanliness_score": 4,
        "comfort_score": 4,
        "wait_minutes": 5,
        "payment_method": "cash",
        "photo_permission_status": "not_taken",
        "staff_identifier": "bartender at main counter",
        "observations": "The guest was greeted promptly, the order was repeated back accurately, service remained attentive, and payment matched the printed receipt total.",
        "receipt_filename": "receipt.png",
        "photo_filenames": [],
        "is_demo": False,
    }


def test_normalize_valid_visit():
    visit = normalize_visit(valid_payload())
    assert visit["assignment_city"] == "Addis Ababa"
    assert visit["receipt_provided"] is True
    assert visit["charged_amount"] == "10.00"


def test_reject_score_out_of_range():
    payload = valid_payload()
    payload["greeting_score"] = 6
    with pytest.raises(VisitValidationError, match="between 1 and 5"):
        normalize_visit(payload)


def test_reject_departure_before_arrival():
    payload = valid_payload()
    payload["departure_time"] = "17:59"
    with pytest.raises(VisitValidationError, match="later than arrival"):
        normalize_visit(payload)


def test_reject_receipt_amount_without_receipt():
    payload = valid_payload()
    payload["receipt_provided"] = False
    with pytest.raises(VisitValidationError, match="must be empty"):
        normalize_visit(payload)


def test_reject_alcohol_without_age_confirmation():
    payload = valid_payload()
    payload["alcohol_ordered"] = True
    payload["age_eligibility_confirmed"] = False
    with pytest.raises(VisitValidationError, match="age_eligibility_confirmed"):
        normalize_visit(payload)


def test_reject_photo_without_permission():
    payload = valid_payload()
    payload["photo_filenames"] = ["interior.jpg"]
    payload["photo_permission_status"] = "not_taken"
    with pytest.raises(VisitValidationError, match="assignment permission"):
        normalize_visit(payload)


def test_payment_metrics_match():
    visit = normalize_visit(valid_payload())
    metrics = compute_metrics(visit)
    assert metrics["payment_match"] is True
    assert metrics["receipt_delta"] == "0.00"
    assert metrics["total_score"] == 92.0


def test_payment_metrics_mismatch_is_flagged():
    payload = valid_payload()
    payload["receipt_amount"] = "12.00"
    visit = normalize_visit(payload)
    metrics = compute_metrics(visit)
    qa = assess_qa(visit, evidence_exists=True)
    assert metrics["payment_match"] is False
    assert qa.status == "NEEDS_REVIEW"
    assert any("does not match" in issue for issue in qa.issues)


def test_ready_requires_evidence_when_receipt_recorded():
    visit = normalize_visit(valid_payload())
    assert assess_qa(visit, evidence_exists=False).status == "NEEDS_REVIEW"
    assert assess_qa(visit, evidence_exists=True).status == "READY"


def test_demo_never_becomes_submission_ready():
    payload = valid_payload()
    payload["is_demo"] = True
    visit = normalize_visit(payload)
    qa = assess_qa(visit, evidence_exists=True)
    assert qa.status == "DEMO_ONLY"