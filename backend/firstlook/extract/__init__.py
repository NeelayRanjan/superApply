"""Tier 1 extraction: deterministic, explainable, and entirely local."""

import json
import re
import sqlite3
from functools import lru_cache

import yaml

from firstlook.paths import DATA


@lru_cache
def dictionaries() -> tuple[dict, dict]:
    return yaml.safe_load((DATA / "skills.yaml").read_text()), yaml.safe_load(
        (DATA / "categories.yaml").read_text()
    )


def extract(title: str, text: str, structured: dict | None = None) -> dict:
    skills, _ = dictionaries()
    required, preferred, negated = set(), set(), set()
    for sentence in re.split(r"[\n;]|(?<=[.!?])\s+", text.lower()):
        for canonical, aliases in skills.items():
            if canonical == "CAD" and re.search(r"cad\s+\d", sentence):
                continue
            if not any(
                re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", sentence) for alias in aliases
            ):
                continue
            if re.search(
                r"\b(?:no .{0,20}required|not required|not necessary|do not need)\b", sentence
            ):
                negated.add(canonical)
            elif re.search(r"nice.to.have|preferred|bonus|optional|a plus", sentence):
                preferred.add(canonical)
            else:
                required.add(canonical)
    seniority = "mid"
    for level, pattern in [
        ("intern", "intern|internship"),
        ("junior", "junior|entry.level|graduate|associate"),
        ("senior", "senior|\bsr\b"),
        ("lead", "staff|principal|lead"),
        ("executive", "director|head of|vice president|chief|\bvp\b"),
    ]:
        if re.search(pattern, title, re.I):
            seniority = level
    years = re.findall(r"(\d+)\s*(?:\+|[-–]\s*\d+)?\s*(?:years|yrs)", text, re.I)
    comp = dict(structured or {})
    money = re.search(
        r"(?P<currency>USD|CAD|EUR|GBP|[$€£])\s*(?P<low>\d[\d,]*(?:\.\d+)?)\s*(?P<lk>[kK])?\s*(?:-|–|to)\s*(?:USD|CAD|EUR|GBP|[$€£])?\s*(?P<high>\d[\d,]*(?:\.\d+)?)\s*(?P<hk>[kK])?",
        text,
    )
    if money and not comp:
        high = float(money["high"].replace(",", "")) * (1000 if money["hk"] else 1)
        low = float(money["low"].replace(",", "")) * (
            1000
            if money["lk"] or (money["hk"] and float(money["low"].replace(",", "")) < 1000)
            else 1
        )
        comp = {
            "min_cents": round(low * 100),
            "max_cents": round(high * 100),
            "currency": {"$": "USD", "€": "EUR", "£": "GBP"}.get(
                money["currency"], money["currency"]
            ),
            "period": "hour"
            if re.search(r"per hour|/hr|hourly", text, re.I)
            else "month"
            if re.search(r"per month|/mo", text, re.I)
            else "year",
        }
    if "min" in comp:
        comp["min_cents"] = round(float(comp.pop("min")) * 100)
    if "max" in comp:
        comp["max_cents"] = round(float(comp.pop("max")) * 100)
    remote = "unknown"
    if re.search(r"\bremote|work from home|telecommut", text, re.I):
        remote = "remote"
    if re.search(r"\bhybrid\b", text, re.I):
        remote = "hybrid"
    if re.search(r"\bonsite|on-site|on site|no remote|not remote", text, re.I):
        remote = "onsite"
    geo = re.search(
        r"(?:remote (?:within|in|from)|must (?:reside|be based) in|restricted to)\s+([^.;\n]+)",
        text,
        re.I,
    )
    visa = "unknown"
    if re.search(
        r"(?:no|not|unable|cannot|without).{0,30}sponsor|sponsorship.{0,15}(?:not available|unavailable)",
        text,
        re.I,
    ):
        visa = "no"
    elif re.search(
        r"sponsorship (?:available|provided)|(?:offer|provide|offers) (?:visa )?sponsorship",
        text,
        re.I,
    ):
        visa = "yes"
    clearance = bool(
        re.search(r"(?:security |secret |ts/sci )clearance|clearance required", text, re.I)
    ) and not bool(re.search(r"no .{0,20}clearance", text, re.I))
    degree = re.search(r"\b(ph\.?d|doctorate|master.?s?|bachelor.?s?|bs|ms)\b", text, re.I)
    size = re.search(r"(\d[\d,]*)\s*(?:\+|[-–]\s*\d[\d,]*)?\s+employees", text, re.I)
    return {
        "skills": sorted(required),
        "preferred_skills": sorted(preferred - required),
        "negated_skills": sorted(negated - required),
        "seniority": seniority,
        "years": max(map(int, years), default=0),
        "degree": degree[0] if degree else None,
        "compensation": comp,
        "remote": remote,
        "geography": geo[1].strip() if geo else None,
        "visa": visa,
        "clearance": clearance,
        "size_cue": size[0] if size else None,
    }


def categories(platform: str, count: int, text: str, seeded: list[str]) -> list[str]:
    _, rules = dictionaries()
    tags = set(seeded)
    for tag, phrases in rules.items():
        if any(phrase in text.lower() for phrase in phrases):
            tags.add(tag)
    if platform in ("ashby", "lever") and count < 100:
        tags.add("startup")
    if count >= 500:
        tags.add("enterprise")
    return sorted(tags)


def index_extract(db: sqlite3.Connection) -> int:
    for row in db.execute("SELECT * FROM job").fetchall():
        result = extract(row["title"], row["description"], json.loads(row["compensation"]))
        if row["remote"] and result["remote"] == "unknown":
            result["remote"] = "remote"
        db.execute(
            "INSERT INTO job_extract(job_id,data) VALUES(?,?) ON CONFLICT(job_id) DO UPDATE SET data=excluded.data",
            (row["id"], json.dumps(result)),
        )
    for row in db.execute("SELECT * FROM company WHERE user_tags=0").fetchall():
        count = db.execute(
            "SELECT count(*) FROM job WHERE company_id=? AND closed_detected_at IS NULL",
            (row["id"],),
        ).fetchone()[0]
        tags = categories(row["platform"], count, row["notes"], json.loads(row["tags"]))
        db.execute("UPDATE company SET tags=? WHERE id=?", (json.dumps(tags), row["id"]))
    db.commit()
    return db.execute("SELECT count(*) FROM job_extract").fetchone()[0]


def set_tags(db: sqlite3.Connection, company_id: str, tags: list[str]) -> None:
    db.execute("UPDATE company SET tags=?,user_tags=1 WHERE id=?", (json.dumps(tags), company_id))
    db.commit()
