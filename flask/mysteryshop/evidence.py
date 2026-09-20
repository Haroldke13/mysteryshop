"""Receipt and photo upload handling.

WRITTEN TO FILL A GAP, 2026-09-20. app.py calls exactly one function --
`save_evidence(upload, UPLOAD_DIR)` -- and expects a stored filename back, or
an `EvidenceError` it can show to the shopper. On failure app.py unlinks the
filenames it collected, so this must return a plain name inside UPLOAD_DIR
and never a path that escapes it.

The rules are deliberately strict, because this is field evidence attached to
a paid assignment:

  - extension AND magic bytes must agree, so a .jpg that is really a script
    is refused. Extension alone is not a check; browsers set content-type
    from the extension too, so that is not independent either.
  - the stored name is generated, never taken from the client. An uploaded
    name is attacker-controlled and the traversal risk is not worth the
    cosmetic benefit of keeping it. The original is recorded in the audit log
    by the caller instead.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

__all__ = ["EvidenceError", "save_evidence", "ALLOWED", "MAX_BYTES"]


class EvidenceError(ValueError):
    """Raised when an upload is missing, too large, or not an accepted type."""


# extension -> the magic-byte prefixes that must match it
ALLOWED: dict[str, tuple[bytes, ...]] = {
    ".jpg":  (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png":  (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
    ".heic": (b"\x00\x00\x00",),      # ISO-BMFF box length, then 'ftyp'
    ".pdf":  (b"%PDF-",),
}

MAX_BYTES = int(os.environ.get("MYSTERY_MAX_EVIDENCE_BYTES", 10 * 1024 * 1024))
_SNIFF = 16


def _looks_like(head: bytes, suffix: str) -> bool:
    if suffix == ".heic":                       # 'ftyp' sits at offset 4
        return head[4:8] == b"ftyp"
    return any(head.startswith(sig) for sig in ALLOWED[suffix])


def save_evidence(upload, upload_dir: str | Path) -> str:
    """Persist one uploaded file and return the generated filename.

    `upload` is a Werkzeug FileStorage. Returns the bare filename, which the
    caller stores on the visit record and joins to UPLOAD_DIR itself.
    """
    if upload is None or not getattr(upload, "filename", ""):
        raise EvidenceError("No file was received.")

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in ALLOWED:
        raise EvidenceError(
            f"{suffix or 'that file type'} is not accepted. Attach a photo "
            f"({', '.join(sorted(k for k in ALLOWED if k != '.pdf'))}) or a PDF receipt."
        )

    head = upload.stream.read(_SNIFF)
    upload.stream.seek(0)
    if not _looks_like(head, suffix):
        raise EvidenceError(
            f"The file does not look like a real {suffix.lstrip('.').upper()} "
            f"file. Re-export it and attach it again."
        )

    directory = Path(upload_dir)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    destination = directory / filename

    written = 0
    with destination.open("wb") as handle:
        while chunk := upload.stream.read(64 * 1024):
            written += len(chunk)
            if written > MAX_BYTES:
                handle.close()
                destination.unlink(missing_ok=True)
                raise EvidenceError(
                    f"File is larger than the {MAX_BYTES // (1024 * 1024)} MB limit."
                )
            handle.write(chunk)

    if written == 0:
        destination.unlink(missing_ok=True)
        raise EvidenceError("The uploaded file was empty.")
    return filename
