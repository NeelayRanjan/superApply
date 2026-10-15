"""Unverified seeds and opt-in discovery. Importing never accesses the network."""

import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import httpx

from firstlook.models import Company
from firstlook.paths import DATA

PATTERNS = {
    "greenhouse": r"(?:boards(?:-api)?|job-boards)\.greenhouse\.io/(?:v1/boards/)?([\w-]+)",
    "lever": r"(?:jobs|api)\.lever\.co/(?:v0/postings/)?([\w-]+)",
    "ashby": r"jobs\.ashbyhq\.com/([\w-]+)",
    "smartrecruiters": r"(?:careers|jobs)\.smartrecruiters\.com/([\w-]+)",
    "workable": r"(?:apply|jobs)\.workable\.com/([\w-]+)",
    "recruitee": r"([\w-]+)\.recruitee\.com",
}


def detect(url: str, html: str = "") -> tuple[str, str] | None:
    for platform, pattern in PATTERNS.items():
        match = re.search(pattern, url + " " + html, re.I)
        if match:
            return platform, match[1]
    if "JobPosting" in html:
        return "jsonld", url
    return None


def allowed_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ValueError("Use an absolute HTTPS careers URL")
    blocked = ("linkedin.com", "indeed.com", "glassdoor.com")
    if any(parsed.hostname == x or parsed.hostname.endswith("." + x) for x in blocked):
        raise ValueError("This source is outside the permitted sources")
    return url


def upsert(db: sqlite3.Connection, company: Company) -> None:
    db.execute(
        """INSERT INTO company(id,name,domain,platform,token,tags,size,verified,notes)
        VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,
        domain=excluded.domain,platform=excluded.platform,token=excluded.token""",
        (
            company.id,
            company.name,
            company.domain,
            company.platform,
            company.token,
            json.dumps(company.tags),
            company.size,
            int(company.verified),
            company.notes,
        ),
    )
    db.commit()


def seed(db: sqlite3.Connection, path: Path = DATA / "registry.seed.jsonl") -> int:
    companies = [
        Company.model_validate_json(line) for line in path.read_text().splitlines() if line
    ]
    if any(c.verified for c in companies):
        raise ValueError("Seeded companies must never be marked verified")
    for company in companies:
        upsert(db, company)
    return len(companies)


def companies(db: sqlite3.Connection) -> list[dict]:
    result = []
    for row in db.execute("SELECT * FROM company ORDER BY name"):
        item = dict(row)
        item["tags"] = json.loads(item["tags"])
        item["verified"] = bool(item["verified"])
        result.append(item)
    return result


def discover(db: sqlite3.Connection, url: str, client: httpx.Client) -> Company:
    allowed_url(url)
    response = client.get(url)
    response.raise_for_status()
    found = detect(url, response.text)
    if not found:
        raise ValueError("No supported ATS detected; add an explicit registry entry")
    platform, token = found
    host = urlparse(url).hostname or ""
    company = Company(
        id=re.sub(r"\W+", "-", host),
        name=host.split(".")[0].title(),
        domain=host,
        platform=platform,  # type: ignore[arg-type]
        token=token,
    )
    upsert(db, company)
    return company


def board_url(company: Company) -> str:
    return {
        "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{company.token}/jobs?content=true",
        "lever": f"https://api.lever.co/v0/postings/{company.token}?mode=json",
        "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{company.token}",
        "smartrecruiters": f"https://api.smartrecruiters.com/v1/companies/{company.token}/postings",
        "workable": f"https://apply.workable.com/api/v1/widget/accounts/{company.token}",
        "recruitee": f"https://{company.token}.recruitee.com/api/offers/",
        "jsonld": company.token,
    }[company.platform]


def verify(db: sqlite3.Connection, client: httpx.Client) -> list[dict]:
    outcomes = []
    for row in companies(db):
        company = Company.model_validate(row)
        try:
            response = client.get(allowed_url(board_url(company)))
            response.raise_for_status()
            verified = True
            message = "Endpoint reachable; inspect content on first crawl"
        except (httpx.HTTPError, ValueError) as exc:
            verified, message = False, str(exc)
        db.execute(
            "UPDATE company SET verified=?,notes=? WHERE id=?", (int(verified), message, company.id)
        )
        outcomes.append({"id": company.id, "verified": verified, "message": message})
    db.commit()
    return outcomes
