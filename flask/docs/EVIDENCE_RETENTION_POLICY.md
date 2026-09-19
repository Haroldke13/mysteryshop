# Evidence Retention and Privacy Policy

## Purpose

Evidence is collected only to support the assigned mystery-shopping report and resolve QA/payment questions.

## Data minimization

Collect only what the assignment requires. A receipt and factual notes are preferred evidence. Additional venue photographs should only be taken when the assignment explicitly allows them. Avoid unnecessary faces, identity documents, unrelated customers, minors, payment-card numbers or other sensitive details.

## Technical handling

- Uploaded images are validated and re-saved without EXIF metadata.
- Evidence files are stored outside Flask's public `static/` directory.
- Database records keep randomized evidence filenames rather than original filenames.
- No external upload or cloud synchronization is performed by default.

## Retention

The default local retention period is 30 days after collection. The client may require a different period; configure `RETENTION_DAYS` accordingly.

Run:

    python scripts/purge_expired_evidence.py

The purge deletes old evidence files and clears stale database filename references.

## Deletion/incident response

If evidence is collected in error or exceeds the assignment scope, delete it promptly and record the correction. If a file contains unrelated personal data, do not distribute it as portfolio material. Client evidence is excluded from Git by default through `.gitignore`.

## Portfolio rule

Only synthetic records and screenshots that contain no client evidence may be used publicly. Real receipts, venue photos, client survey screens and assignment instructions require explicit permission before publication.