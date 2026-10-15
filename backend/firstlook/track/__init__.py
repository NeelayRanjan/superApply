import json
import sqlite3

from firstlook.ingest import now

STATES = [
    "saved",
    "applied",
    "acknowledged",
    "screen",
    "interview",
    "offer",
    "rejected",
    "ghosted",
    "withdrawn",
]
RESPONSES = {"acknowledged", "screen", "interview", "offer", "rejected"}


def queue(db: sqlite3.Connection, job_id: int, variant_id: int | None = None) -> dict:
    if not db.execute("SELECT id FROM job WHERE id=?", (job_id,)).fetchone():
        raise ValueError("Job not found")
    if variant_id:
        v = db.execute("SELECT job_id FROM resume_variant WHERE id=?", (variant_id,)).fetchone()
        if not v or v[0] != job_id:
            raise ValueError("Resume variant belongs to a different job")
    existing = db.execute(
        "SELECT id FROM application WHERE job_id=? AND state NOT IN ('withdrawn','rejected') ORDER BY id DESC LIMIT 1",
        (job_id,),
    ).fetchone()
    if existing:
        if variant_id:
            db.execute(
                "UPDATE application SET variant_id=? WHERE id=? AND state='saved'",
                (variant_id, existing[0]),
            )
            db.commit()
        return dict(db.execute("SELECT * FROM application WHERE id=?", (existing[0],)).fetchone())
    row = db.execute(
        "INSERT INTO application(job_id,variant_id) VALUES(?,?)", (job_id, variant_id)
    ).lastrowid
    db.execute("INSERT INTO application_event(application_id,state) VALUES(?,'saved')", (row,))
    db.commit()
    return dict(db.execute("SELECT * FROM application WHERE id=?", (row,)).fetchone())


def transition(
    db: sqlite3.Connection,
    application_id: int,
    state: str,
    notes: str | None = None,
    contacts: str | None = None,
) -> dict:
    if state not in STATES:
        raise ValueError("Unknown pipeline state")
    row = db.execute("SELECT * FROM application WHERE id=?", (application_id,)).fetchone()
    if not row:
        raise ValueError("Application not found")
    db.execute(
        "UPDATE application SET state=?,notes=?,contacts=?,applied_at=CASE WHEN ?!=? THEN COALESCE(applied_at,?) ELSE applied_at END,response_at=CASE WHEN ? THEN COALESCE(response_at,?) ELSE response_at END WHERE id=?",
        (
            state,
            notes if notes is not None else row["notes"],
            contacts if contacts is not None else row["contacts"],
            state,
            "saved",
            now(),
            int(state in RESPONSES),
            now(),
            application_id,
        ),
    )
    db.execute(
        "INSERT INTO application_event(application_id,state,note) VALUES(?,?,?)",
        (application_id, state, notes or ""),
    )
    if row["variant_id"] and state != "saved":
        db.execute("UPDATE resume_variant SET used=1 WHERE id=? AND used=0", (row["variant_id"],))
    db.commit()
    if state in ("screen", "interview", "offer", "rejected", "ghosted"):
        from firstlook.match import feedback

        try:
            feedback(db, row["job_id"], int(state in ("screen", "interview", "offer")))
        except ValueError:
            pass
    return dict(db.execute("SELECT * FROM application WHERE id=?", (application_id,)).fetchone())


def applications(db: sqlite3.Connection) -> list[dict]:
    setting = db.execute("SELECT value FROM setting WHERE key='reminder_days'").fetchone()
    days = int(json.loads(setting[0])) if setting else 14
    return [
        dict(r)
        for r in db.execute(
            """SELECT a.*,j.title,c.name company,j.apply_url,
        CASE WHEN a.applied_at IS NOT NULL AND a.response_at IS NULL AND a.state NOT IN ('withdrawn','rejected','offer','ghosted') AND julianday('now')-julianday(a.applied_at)>=? THEN 1 ELSE 0 END reminder
        FROM application a JOIN job j ON j.id=a.job_id JOIN company c ON c.id=j.company_id ORDER BY a.id DESC""",
            (days,),
        )
    ]
