# Mystery Bar Visit QA & Reporting Toolkit

A small, runnable Flask application and reporting workflow for a mystery shopper conducting bar-service assignments. It converts field notes and permitted evidence into a structured visit record, checks payment arithmetic and evidence completeness, applies a transparent QA gate, and exports reviewable CSV/Markdown outputs before the shopper completes the client's official BARE survey.

## What this project solves

The posted work is operational rather than a conventional software project: a shopper must physically visit an assigned bar, behave like a normal guest, order a drink, observe service/atmosphere/payment handling, retain the receipt, and submit a survey within 24 hours. The software in this repository supports that workflow without pretending the physical visit occurred.

It provides:

- structured capture for the six posted target cities;
- service and atmosphere scoring using five 1–5 dimensions;
- expected-price, charged-amount and receipt-amount reconciliation;
- a QA gate that flags missing/short observations, missing receipt evidence, payment mismatches, and unexplained price differences;
- controlled upload of receipt/photos, including extension validation and EXIF stripping for images;
- an alcohol-order eligibility safeguard;
- synthetic demo data that is visibly labeled `DEMO_ONLY` and contains no real venues, employees or receipts;
- CSV export for all visits and Markdown export for individual reports;
- an audit log for record creation and exports;
- a retention script for deleting old evidence files and clearing their database references;
- responsive Flask pages for field entry, review, QA status and download.

## Important boundary

This repository **does not** perform or claim a physical mystery-shop visit, access the client's BARE account, upload to the BARE platform, invent a venue, create fake receipts, or reproduce unseen client guidelines. The job post says guidelines are attached, but no guideline file was available in the supplied task context. The client's actual guideline document and BARE questionnaire therefore remain external dependencies and must be mapped into the local checklist before a live assignment.

## Architecture

Browser → Flask `app.py` → domain validation / evidence sanitizer / SQLite storage → scoring and QA → CSV or Markdown reports.

The synthetic generator writes demo-only records to the same storage layer, while the retention utility deletes expired evidence.

## Scoring model

The composite score is intentionally simple and auditable:

| Component | Weight |
|---|---:|
| Greeting, attentiveness, professionalism | 45 |
| Cleanliness and comfort | 25 |
| Charged amount matches receipt | 20 |
| Receipt provided | 5 |
| Pricing explained/clear | 5 |
| **Total** | **100** |

A score is not the same as a submission decision. The separate QA gate can mark a record `NEEDS_REVIEW` even when the numerical score is high.

## QA rules

A real field record is `READY` only when the local checks find no issue. Examples of issues:

- factual observation text is shorter than 60 characters;
- no receipt was provided;
- the receipt was recorded but no evidence file is attached;
- charged amount differs from receipt amount by more than 0.01 currency units;
- charged amount differs from the expected/menu amount and needs explanation;
- photo evidence exists without the assignment being marked as allowing photos.

Synthetic demo records are always `DEMO_ONLY` regardless of score.

## Evidence and privacy controls

The implementation follows data minimization rather than collecting unnecessary identity data. Staff identification is optional and should use a role/description (for example, “bartender at main counter”) unless the client specifically requires a name. Images are re-saved without EXIF metadata. Additional venue photos cannot be attached unless `allowed_by_assignment` is selected. Default evidence retention is 30 days and can be changed through `.env`.

This is an operational safeguard, not a jurisdiction-specific legal opinion. Before a live assignment, the shopper should follow the client's written rules and any venue/local restrictions on photography. No covert audio/video recording feature is included.

## Prerequisites

- Python 3.10+
- pip

## Installation

Use these commands:

- `git clone <repository-url>`
- `cd mystery_bar_audit`
- `python -m venv .venv`
- Linux/macOS: `source .venv/bin/activate`
- Windows: `.venv\Scripts\activate`
- `pip install -r requirements.txt`
- `cp .env.example .env`

## Run the application

Run `python app.py`, then open `http://127.0.0.1:5000`.

Health endpoint: `http://127.0.0.1:5000/health`.

## Generate synthetic demo data

The generator uses Faker only as a reproducible fixture dependency. It does not generate personal identities; it creates generic, synthetic visit records and labels every record as demo-only.

Run `python scripts/generate_demo_data.py --count 8 --seed 20260918`, then `python app.py`.

To use a disposable database, run `python scripts/generate_demo_data.py --count 6 --db /tmp/mystery-demo.db`.

## Record a real visit

1. Open **New visit**.
2. Enter the client-assigned city and venue code.
3. Record the visit timing, ordered item, expected/menu amount, charged amount and receipt amount.
4. Score only observed service/atmosphere dimensions.
5. Upload the receipt if it was provided and retained.
6. Upload any additional photos only when the assignment explicitly permits them.
7. Save the record and resolve every QA issue before using the information in the official BARE survey.
8. Download the per-visit Markdown report as a working record.

## Exports

- `GET /exports/visits.csv` — all stored records.
- `GET /exports/visit/<visit-id>.md` — a single visit working report.

The client-facing BARE form remains external and is not automated because credentials, form fields and permission to automate that platform were not supplied.

## Retention/deletion

Default: 30 days.

Run `python scripts/purge_expired_evidence.py`.

This deletes evidence files older than `RETENTION_DAYS` and clears filename references for older database records. Schedule this command with cron/Task Scheduler only after confirming the client's required retention period.

## Run tests

Run `pytest -q`.

The tests cover normalization, invalid score ranges, age eligibility, visit timing, receipt arithmetic, QA behavior, storage round trips, Flask health/index routes, successful form creation and invalid submissions.

## Data model

The SQLite database stores operational fields including:

- assignment city and venue code;
- visit date, arrival/departure time;
- item/beverage type;
- currency, expected amount, charged amount, receipt amount;
- payment method and receipt status;
- five observation scores and wait time;
- factual notes;
- evidence filenames only;
- derived score/payment checks;
- QA status/issues;
- demo flag and audit timestamps.

## Configuration

See `.env.example`.

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session/flash signing | development placeholder |
| `MYSTERY_DB_PATH` | SQLite path | `data/mystery_shop.db` |
| `MYSTERY_UPLOAD_DIR` | evidence directory | `data/evidence` |
| `MAX_UPLOAD_MB` | request limit | `10` |
| `RETENTION_DAYS` | evidence retention | `30` |
| `FLASK_HOST` | listen address | `127.0.0.1` |
| `FLASK_PORT` | listen port | `5000` |

For production, set a strong secret key, use HTTPS, put the app behind an authenticated reverse proxy, use encrypted storage, and avoid exposing evidence directories as public static files.

## Deployment considerations

This build is deliberately local-first because field evidence may contain transaction and location details. For multi-user deployment, add authenticated user accounts, role-based access, encrypted object storage, per-assignment tenancy, server-side CSRF protection, centralized logs, backups, and a documented data-processing agreement before placing it on the public internet.

## Limitations

- No physical visit has been conducted by this software.
- No BARE credentials or client survey schema were supplied, so final platform submission is manual.
- The job post references attached guidelines, but those guidelines were not available here; the local QA rules are therefore a defensible generic layer, not a claim to reproduce the client's exact scoring rubric.
- No real venue, staff identity, receipt, customer, or transaction appears in the bundled demo data.
- Currency conversion is intentionally absent; mystery shopping should preserve the currency actually used at the venue.
- The score is an internal organization aid, not a client-issued score unless the client adopts it.

## Skills actually exercised

The requested work primarily exercises observation capture, written reporting, instruction compliance, evidence QA and professional discretion. It does **not** genuinely require broad market-research list building, and the repository does not fabricate that capability merely to claim it.