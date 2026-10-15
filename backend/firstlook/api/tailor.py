from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from firstlook.bank import Entry, entries, save
from firstlook.db import connect
from firstlook.tailor import create, decide, get, render, suggest

router = APIRouter()


@router.get("/api/bank")
def bank():
    with connect() as db:
        return entries(db)


@router.put("/api/bank")
def save_bank(entry: Entry):
    with connect() as db:
        return save(db, entry)


@router.post("/api/tailor/{job_id}")
def tailor(job_id: int, data: dict | None = None):
    with connect() as db:
        return create(db, job_id, (data or {}).get("template", "classic"))


@router.get("/api/variants/{variant_id}")
def variant(variant_id: int):
    with connect() as db:
        return get(db, variant_id)


@router.post("/api/lines/{line_id}/suggest")
def suggestion(line_id: int, data: dict):
    with connect() as db:
        return suggest(db, line_id, str(data["text"]))


@router.post("/api/lines/{line_id}/decide")
def decision(line_id: int, data: dict):
    with connect() as db:
        return decide(db, line_id, bool(data["accept"]))


@router.post("/api/variants/{variant_id}/render")
def export(variant_id: int):
    with connect() as db:
        return render(db, variant_id)


@router.get("/api/variants/{variant_id}/pdf")
def pdf(variant_id: int):
    with connect() as db:
        v = get(db, variant_id)
        if not v["ready"] or not v["pdf_path"] or not Path(v["pdf_path"]).exists():
            raise ValueError("A verified PDF is not available")
        return FileResponse(v["pdf_path"], media_type="application/pdf")


@router.post("/api/lines/{line_id}/ai-suggest")
def ai_suggestion(line_id: int):
    import json

    from firstlook.llm import Client

    with connect() as db:
        line = db.execute("SELECT * FROM variant_line WHERE id=?", (line_id,)).fetchone()
        if not line:
            raise ValueError("Line not found")
        variant = get(db, line["variant_id"])
        if variant["used"]:
            raise ValueError("Used variant is immutable")
        job = db.execute(
            "SELECT title,description FROM job WHERE id=?", (variant["job_id"],)
        ).fetchone()
        prompt = json.dumps(
            {
                "instruction": "Rephrase this bullet using only its source facts. Keep every number verbatim. Return the bullet only.",
                "source": line["original"],
                "job": dict(job),
                "remaining_lines": variant["remaining_lines"],
                "bank_version": variant["snapshot"],
            }
        )
        result = Client(db).call("rephrase", variant["job_id"], prompt)
        if result["text"]:
            try:
                return suggest(db, line_id, result["text"])
            except ValueError as exc:
                return dict(variant, note=f"Suggestion rejected by provenance/metrics gate: {exc}")
        return dict(variant, note=result["note"])


@router.get("/api/variants")
def variants():
    with connect() as db:
        return [
            dict(r)
            for r in db.execute(
                "SELECT id,job_id,ready,used,created_at FROM resume_variant ORDER BY id DESC"
            )
        ]


@router.post("/api/variants/{variant_id}/layout")
def edit_layout(variant_id: int, data: dict):
    from firstlook.tailor import layout

    with connect() as db:
        return layout(db, variant_id, data["selection"])


@router.get("/api/jobs/{job_id}/gap")
def job_gap(job_id: int):
    import json

    with connect() as db:
        variant = db.execute(
            "SELECT id FROM resume_variant WHERE job_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
        if variant:
            return get(db, variant[0])["gap"]
        extracted = db.execute("SELECT data FROM job_extract WHERE job_id=?", (job_id,)).fetchone()
        skills = json.loads(extracted[0]).get("skills", []) if extracted else []
        bank_text = json.dumps(entries(db)).lower()
        return {
            "not_surfaced": [s for s in skills if s.lower() in bank_text],
            "not_in_bank": [s for s in skills if s.lower() not in bank_text],
        }
