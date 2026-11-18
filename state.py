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
CREATE TABLE IF NOT EXISTS runs (
    run_date    TEXT PRIMARY KEY,   -- ISO date (UTC) the digest was for
    finished_at TEXT NOT NULL,      -- UTC timestamp the digest was sent
    notes       INTEGER NOT NULL    -- how many notes it contained (0 on a quiet day)
);
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


def already_ran(con, today):
    """True if today's digest has already been sent, including quiet days."""
    return con.execute("SELECT 1 FROM runs WHERE run_date = ?", (today.isoformat(),)).fetchone() is not None


def record_run(con, today, n_notes):
    con.execute(
        "INSERT OR REPLACE INTO runs VALUES (?, datetime('now'), ?)",
        (today.isoformat(), n_notes),
    )
    con.commit()


def record(con, notes, today):
    """Records the notes that went into the digest. Only these start a cooldown."""
    rows = []
    for n in notes:
        rows.append((n["check"], n["ticker"], n["key"], today.isoformat(), n["score"], n["text"]))
        for other in n.get("also", []):   # context lines count as covered too
            rows.append((other["check"], other["ticker"], other["key"], today.isoformat(), other["score"], ""))
    con.executemany("INSERT INTO sent VALUES (?, ?, ?, ?, ?, ?)", rows)
    con.commit()
