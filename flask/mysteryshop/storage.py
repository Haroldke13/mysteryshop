"""Persistence and the audit log for mystery-shopping visits.

WRITTEN TO FILL A GAP, 2026-09-20. app.py constructs `VisitStore(DB_PATH)`
and calls four methods: `list_visits`, `add_visit(payload, evidence_exists=)`,
`get_visit(id)` (KeyError when absent) and `log_action`. The demo generator
in scripts/ uses the same constructor and `add_visit`.

WHY A DOCUMENT ROW RATHER THAN 25 COLUMNS
-----------------------------------------
`normalize_visit` already returns the authoritative record, and it contains a
list (`photo_filenames`), a nullable decimal held as a string
(`receipt_amount`) and booleans. Spreading that over columns would mean
serialising the list anyway and re-deriving types on every read, for no
query that this application performs -- it lists everything and fetches by
id, nothing else.

So the row is the JSON document, with the handful of fields actually used for
listing, ordering and the summary promoted to real columns. Those are
derived from the document on write, never edited independently, so they
cannot drift from it.

The audit log is separate and append-only: it records exports as well as
writes, because "who took a copy of the data" is the question that matters
for fieldwork evidence.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .domain import assess_qa, compute_metrics, normalize_visit

__all__ = ["VisitStore"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
    id              TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    assignment_city TEXT NOT NULL,
    venue_code      TEXT NOT NULL,
    visit_date      TEXT NOT NULL,
    qa_status       TEXT NOT NULL,
    total_score     REAL NOT NULL,
    is_demo         INTEGER NOT NULL DEFAULT 0,
    document        TEXT NOT NULL      -- the full normalized record, JSON
);
CREATE INDEX IF NOT EXISTS ix_visits_date ON visits (visit_date DESC);

CREATE TABLE IF NOT EXISTS audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    at       TEXT NOT NULL,
    action   TEXT NOT NULL,
    visit_id TEXT,
    detail   TEXT NOT NULL DEFAULT ''
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class VisitStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── writes ───────────────────────────────────────────────────────────
    def add_visit(self, payload: dict[str, Any], *,
                  evidence_exists: bool = False) -> dict[str, Any]:
        """Validate, score, store and return the complete visit record.

        Raises VisitValidationError (from domain.normalize_visit) before
        anything is written, so a rejected submission leaves no row.
        """
        visit = normalize_visit(payload)
        metrics = compute_metrics(visit)
        qa = assess_qa(visit, evidence_exists=evidence_exists)

        visit["id"] = uuid.uuid4().hex[:12]
        visit["created_at"] = _now()
        visit["metrics"] = metrics
        visit["total_score"] = metrics["total_score"]
        visit["qa_status"] = qa.status
        visit["qa_issues"] = list(qa.issues)

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO visits (id, created_at, assignment_city, venue_code,
                                       visit_date, qa_status, total_score, is_demo, document)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (visit["id"], visit["created_at"], visit["assignment_city"],
                 visit["venue_code"], visit["visit_date"], visit["qa_status"],
                 float(visit["total_score"]), int(bool(visit["is_demo"])),
                 json.dumps(visit, default=str)),
            )
        self.log_action("visit_created", visit["id"],
                        f"qa_status={visit['qa_status']} score={visit['total_score']}")
        return visit

    def log_action(self, action: str, visit_id: str | None, detail: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (at, action, visit_id, detail) VALUES (?, ?, ?, ?)",
                (_now(), action, visit_id, detail),
            )

    # ── reads ────────────────────────────────────────────────────────────
    def list_visits(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT document FROM visits ORDER BY visit_date DESC, created_at DESC"
            ).fetchall()
        return [json.loads(row["document"]) for row in rows]

    def get_visit(self, visit_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT document FROM visits WHERE id = ?", (visit_id,)
            ).fetchone()
        if row is None:
            raise KeyError(visit_id)
        return json.loads(row["document"])

    def audit_trail(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT at, action, visit_id, detail FROM audit_log "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
