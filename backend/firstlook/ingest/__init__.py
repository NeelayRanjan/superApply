import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone

from rapidfuzz.fuzz import ratio

from firstlook.adapters import source
from firstlook.models import Company, RawPosting
from firstlook.registry import companies


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ingest(
    db: sqlite3.Connection, company: Company, postings: list[RawPosting], stamp: str | None = None
) -> int:
    stamp = stamp or now()
    new_count = 0
    seen = set()
    with db:
        for job in postings:
            seen.add(job.external_id)
            content = hashlib.sha256(job.model_dump_json().encode()).hexdigest()
            existing = db.execute(
                "SELECT * FROM job WHERE company_id=? AND external_id=?",
                (company.id, job.external_id),
            ).fetchone()
            duplicate = None
            repost = False
            for candidate in db.execute(
                "SELECT * FROM job WHERE company_id=? AND duplicate_of IS NULL ORDER BY id",
                (company.id,),
            ):
                if candidate["external_id"] == job.external_id:
                    continue
                if (
                    ratio(candidate["title"].lower(), job.title.lower()) >= 94
                    and ratio(candidate["description"], job.description) >= 92
                ):
                    duplicate = candidate["id"]
                    repost = candidate["external_id"] not in {p.external_id for p in postings}
                    if repost:
                        db.execute("UPDATE job SET ghost=1 WHERE id=?", (duplicate,))
                    break
            values = (
                job.title,
                job.apply_url,
                json.dumps(job.locations),
                int(job.remote),
                job.department,
                job.employment_type,
                job.posted_at,
                job.description_html,
                job.description,
                json.dumps(job.compensation),
                content,
                stamp,
                duplicate,
                int(repost),
            )
            if existing:
                db.execute(
                    """UPDATE job SET title=?,apply_url=?,locations=?,remote=?,department=?,employment_type=?,posted_at=?,
                    description_html=?,description=?,compensation=?,content_hash=?,last_seen=?,duplicate_of=?,ghost=MAX(ghost,?),missing_count=0,closed_detected_at=NULL WHERE id=?""",
                    values + (existing["id"],),
                )
            else:
                db.execute(
                    """INSERT INTO job(title,apply_url,locations,remote,department,employment_type,posted_at,description_html,
                    description,compensation,content_hash,last_seen,duplicate_of,ghost,company_id,external_id,first_seen) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    values + (company.id, job.external_id, stamp),
                )
                new_count += 1
        for row in db.execute(
            "SELECT id,external_id,missing_count FROM job WHERE company_id=?", (company.id,)
        ).fetchall():
            if row["external_id"] not in seen:
                misses = row["missing_count"] + 1
                db.execute(
                    "UPDATE job SET missing_count=?,closed_detected_at=CASE WHEN ?>=2 THEN COALESCE(closed_detected_at,?) ELSE closed_detected_at END WHERE id=?",
                    (misses, misses, stamp, row["id"]),
                )
        setting = db.execute("SELECT value FROM setting WHERE key='ghost_days'").fetchone()
        age = int(json.loads(setting[0])) if setting else 60
        db.execute(
            "UPDATE job SET ghost=1 WHERE closed_detected_at IS NULL AND julianday(?)-julianday(first_seen)>?",
            (stamp, age),
        )
    return new_count


def scheduled(db: sqlite3.Connection) -> list[dict]:
    rows = companies(db)
    return sorted(rows, key=lambda c: ((c["last_crawled"] or ""), -c["hit_rate"], c["id"]))


def crawl(db: sqlite3.Connection, client, selected: list[dict] | None = None) -> dict:
    started = time.monotonic()
    run = db.execute("INSERT INTO crawl_run(started_at) VALUES(?)", (now(),)).lastrowid
    db.commit()
    count = 0
    outcomes = []
    for row in selected if selected is not None else scheduled(db):
        company = Company.model_validate(row)
        start, before = time.monotonic(), client.bytes
        try:
            postings = source(company.platform, client).fetch(company)
            added = ingest(db, company, postings) if postings is not None else 0
            count += added
            status = "unchanged" if postings is None else "ok"
            error = None
            db.execute(
                "UPDATE company SET last_crawled=?,last_success=?,consecutive_failures=0,hit_rate=0.8*hit_rate+0.2*? WHERE id=?",
                (now(), now(), added, company.id),
            )
        except Exception as exc:
            status, added, error = "error", 0, str(exc)
            db.execute(
                "UPDATE company SET last_crawled=?,consecutive_failures=consecutive_failures+1 WHERE id=?",
                (now(), company.id),
            )
        db.execute(
            "INSERT INTO crawl_result(run_id,company_id,status,count,bytes,duration,error) VALUES(?,?,?,?,?,?,?)",
            (
                run,
                company.id,
                status,
                added,
                client.bytes - before,
                time.monotonic() - start,
                error,
            ),
        )
        outcomes.append(dict(company=company.name, status=status, count=added, error=error))
        db.commit()
    db.execute(
        "UPDATE crawl_run SET finished_at=?,counts=?,bytes=?,duration=? WHERE id=?",
        (now(), count, client.bytes, time.monotonic() - started, run),
    )
    db.commit()
    return dict(id=run, new=count, bytes=client.bytes, outcomes=outcomes)
