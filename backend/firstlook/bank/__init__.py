import json
import sqlite3
from typing import Literal

from pydantic import BaseModel, Field


class Entry(BaseModel):
    id: str = Field(min_length=1)
    kind: Literal["role", "project", "publication", "education", "skill", "identity"] = "role"
    title: str = Field(min_length=1)
    organisation: str = ""
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)
    metrics: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    weight: float = Field(default=1, ge=0, le=10)


def entries(db: sqlite3.Connection) -> list[dict]:
    return [
        dict(json.loads(r["data"]), version=r["version"])
        for r in db.execute("SELECT * FROM bank_entry ORDER BY id")
    ]


def save(db: sqlite3.Connection, entry: Entry) -> dict:
    old = db.execute("SELECT data FROM bank_entry WHERE id=?", (entry.id,)).fetchone()
    if old and json.loads(old[0])["metrics"] != entry.metrics:
        raise ValueError("Metrics are immutable. Create a new bank entry for a corrected source.")
    for bullet in entry.bullets:
        expand(bullet, entry.metrics)
    db.execute(
        "INSERT INTO bank_entry(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,version=bank_entry.version+1",
        (entry.id, entry.model_dump_json()),
    )
    db.commit()
    return entry.model_dump()


def expand(text: str, metrics: dict[str, str]) -> str:
    for key, value in metrics.items():
        text = text.replace("{" + key + "}", value)
    if "{" in text or "}" in text:
        raise ValueError("Unresolved metric placeholder")
    return text
