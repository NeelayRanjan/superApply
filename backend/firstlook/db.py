"""Small, explicit SQLite migrations; all application data stays local."""
import os
import sqlite3
from pathlib import Path

MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS setting (
      key TEXT PRIMARY KEY, value TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    """
]


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    target = str(path or os.environ.get("FIRSTLOOK_DB", ".firstlook/firstlook.db"))
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    for number, migration in enumerate(MIGRATIONS, 1):
        if number > version:
            db.executescript(f"BEGIN;\n{migration}\nPRAGMA user_version={number};\nCOMMIT;")
    return db
