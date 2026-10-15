from fastapi import APIRouter

from firstlook.chat import chat, tool
from firstlook.db import connect

router = APIRouter()


@router.post("/api/chat")
def message(data: dict):
    with connect() as db:
        return chat(db, str(data.get("message", "")), data.get("context", {}))


@router.post("/api/tools/{name}")
def execute(name: str, data: dict):
    with connect() as db:
        return tool(db, name, data)


@router.get("/api/budget")
def ledger():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM llm_call ORDER BY id DESC")]
