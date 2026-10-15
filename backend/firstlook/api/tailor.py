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
def tailor(job_id: int):
    with connect() as db:
        return create(db, job_id)


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
