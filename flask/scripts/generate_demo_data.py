from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mysteryshop.domain import TARGET_CITIES  # noqa: E402
from mysteryshop.storage import VisitStore  # noqa: E402


def build_demo_record(fake: Faker, rng: random.Random, index: int) -> dict:
    city = TARGET_CITIES[index % len(TARGET_CITIES)]
    visit_day = date.today() - timedelta(days=index + 1)
    expected = rng.choice([5, 8, 10, 12, 15, 20])
    charged = expected if rng.random() > 0.2 else expected + rng.choice([1, 2])
    return {
        "assignment_city": city,
        "venue_code": f"DEMO-{city[:3].upper()}-{index + 1:02d}",
        "visit_date": visit_day.isoformat(),
        "arrival_time": f"{18 + (index % 3):02d}:15",
        "departure_time": f"{19 + (index % 3):02d}:05",
        "beverage_type": rng.choice(["non-alcoholic", "alcoholic"]),
        "ordered_item": rng.choice(["Sparkling water", "Soft drink", "Local beer", "Juice"]),
        "expected_amount": str(expected),
        "charged_amount": str(charged),
        "receipt_amount": None,
        "currency": rng.choice(["USD", "ETB", "MUR", "GNF", "XAF", "SSP", "SLE"]),
        "receipt_provided": False,
        "pricing_explained": rng.choice([True, False]),
        "alcohol_ordered": False,
        "age_eligibility_confirmed": False,
        "greeting_score": rng.randint(2, 5),
        "attentiveness_score": rng.randint(2, 5),
        "professionalism_score": rng.randint(2, 5),
        "cleanliness_score": rng.randint(2, 5),
        "comfort_score": rng.randint(2, 5),
        "wait_minutes": rng.randint(2, 18),
        "payment_method": rng.choice(["cash", "card", "mobile money"]),
        "photo_permission_status": "not_taken",
        "staff_identifier": "",
        "observations": (
            f"Synthetic demonstration note {index + 1}: the server acknowledged the guest, "
            f"confirmed the order, delivered it after a short wait, and completed payment. "
            "No real venue, employee, receipt, or client submission is represented by this record."
        ),
        "receipt_filename": "",
        "photo_filenames": [],
        "is_demo": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic demo mystery-shopping records.")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument("--db", default=str(ROOT / "data" / "mystery_shop.db"))
    args = parser.parse_args()

    if args.count < 1 or args.count > 100:
        raise SystemExit("--count must be between 1 and 100")

    fake = Faker()
    fake.seed_instance(args.seed)
    rng = random.Random(args.seed)
    store = VisitStore(args.db)
    for index in range(args.count):
        store.add_visit(build_demo_record(fake, rng, index), evidence_exists=False)
    print(f"Generated {args.count} synthetic demo records in {args.db}")


if __name__ == "__main__":
    main()