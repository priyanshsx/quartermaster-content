"""SQLite store: cooldowns, so the same note doesn't come back every day, and an archive of what was sent."""
import sqlite3
from datetime import date

SCHEMA = """
CREATE TABLE IF NOT EXISTS sent (
    check_name TEXT NOT NULL,
    ticker     TEXT NOT NULL,
    key        TEXT NOT NULL,
    sent_on    TEXT NOT NULL,   -- ISO date of the run
    score      REAL,
    text       TEXT
);
CREATE INDEX IF NOT EXISTS sent_lookup ON sent (check_name, ticker, key, sent_on);
"""


def connect(path):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def on_cooldown(con, note, cooldown_days, today):
    row = con.execute(
        "SELECT MAX(sent_on) FROM sent WHERE check_name = ? AND ticker = ? AND key = ?",
        (note["check"], note["ticker"], note["key"]),
    ).fetchone()
    if not row or not row[0]:
        return False
    return (today - date.fromisoformat(row[0])).days < cooldown_days


def record(con, notes, today):
    """Records the notes that went into the digest. Only these start a cooldown."""
    rows = []
    for n in notes:
        rows.append((n["check"], n["ticker"], n["key"], today.isoformat(), n["score"], n["text"]))
        for other in n.get("also", []):   # context lines count as covered too
            rows.append((other["check"], other["ticker"], other["key"], today.isoformat(), other["score"], ""))
    con.executemany("INSERT INTO sent VALUES (?, ?, ?, ?, ?, ?)", rows)
    con.commit()
