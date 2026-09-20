"""Mystery-shopping fieldwork capture.

Package marker. The working code is in:

    domain.py     validation, scoring and the QA gate  (committed originally)
    storage.py    persistence and the audit log        (added 2026-09-20)
    evidence.py   receipt/photo upload handling        (added 2026-09-20)
    exporters.py  CSV and Markdown output              (added 2026-09-20)

app.py imported all four from the start; only domain.py was ever written, so
the application could not start. The three added modules implement exactly the
call signatures app.py already uses, and nothing in domain.py was changed.
"""
