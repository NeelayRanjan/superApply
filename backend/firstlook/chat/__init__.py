"""UI and CLI share this bounded tool dispatch. No submission tool exists."""

import json
import sqlite3

from firstlook.llm import Client, estimate
from firstlook.match import rank
from firstlook.tailor import create, draft_answer, get

TOOLS = [
    "search_jobs",
    "open_job",
    "explain_match",
    "tailor",
    "diff_variant",
    "draft_answer",
    "star",
    "queue_apply",
    "track",
    "analytics",
    "registry_add",
]


def tool(db: sqlite3.Connection, name: str, args: dict) -> object:
    if name not in TOOLS:
        raise ValueError("Unknown or forbidden tool")
    if name == "search_jobs":
        filters = args.get("filters", {})
        return [
            j
            for j in rank(db, include_filtered=bool(filters.get("include_filtered")))
            if (
                not filters.get("query")
                or filters["query"].lower()
                in (j["title"] + " " + j["company"] + " " + j["description"]).lower()
            )
        ][:50]
    if name in ("open_job", "explain_match"):
        job = next((j for j in rank(db, include_filtered=True) if j["id"] == args["id"]), None)
        if job is None:
            raise ValueError("Job not found")
        db.execute("UPDATE job SET touched=1 WHERE id=?", (args["id"],))
        db.commit()
        return job
    if name == "tailor":
        return create(db, args["job_id"])
    if name == "diff_variant":
        return get(db, args["id"])
    if name == "draft_answer":
        return draft_answer(db, args["job_id"], args["question"])
    if name == "star":
        db.execute("UPDATE job SET starred=1,touched=1 WHERE id=?", (args["id"],))
        db.commit()
        return {"saved": True}
    if name in ("queue_apply", "track"):
        from firstlook.track import queue, transition  # type: ignore[attr-defined]

        return (
            queue(db, args["id"], args.get("variant_id"))
            if name == "queue_apply"
            else transition(db, args["id"], args["state"], args.get("notes", ""))
        )
    if name == "analytics":
        from firstlook.analytics import report  # type: ignore[attr-defined]

        return report(db)
    if name == "registry_add":
        from firstlook.ingest.http import PoliteClient
        from firstlook.registry import discover

        client = PoliteClient(db)
        try:
            return discover(db, args["url"], client).model_dump()
        finally:
            client.close()
    raise ValueError("Unsupported tool")


def chat(db: sqlite3.Connection, message: str, context: dict, transport=None) -> dict:
    job_id = context.get("job_id")
    text = message.lower().strip()
    if "strong" in text or text.startswith("search") or "show" in text:
        matches = rank(db)[:5]
        return {
            "message": "Your leading matches:\n"
            + "\n".join(
                f"• {j['title']} at {j['company']} — {j['band']}, matches {', '.join(j['matched']) or 'title overlap'}"
                for j in matches
            ),
            "mode": "local",
        }
    if text.startswith("star") and job_id:
        tool(db, "star", {"id": job_id})
        return {"message": "Saved this opportunity to your starred jobs.", "mode": "local"}
    if ("explain" in text or "match" in text) and job_id:
        job = tool(db, "explain_match", {"id": job_id})
        return {"message": json.dumps(job, indent=2), "mode": "local"}
    if text.startswith("tailor") and job_id:
        variant = create(db, job_id)
        return {
            "message": f"Created local variant #{variant['id']} with {len(variant['lines'])} sourced lines. Open Tailor to review it.",
            "mode": "local",
        }
    if text.startswith("ask ") and job_id:
        job = tool(db, "open_job", {"id": job_id})
        prompt = json.dumps({"question": message[4:], "view": context.get("view"), "job": job})
        result = Client(db, transport=transport).call("chat", job_id, prompt)
        return {
            "message": result["text"] or result["note"],
            "mode": "provider" if result["text"] else "local",
            "estimate": estimate("chat"),
        }
    return {
        "message": "Local tools are ready. Try “show my strongest matches”, “explain this match”, “star this job”, or “tailor this job”. Choose a job first for context. With a provider configured, prefix a specific question with “ask”. No application is submitted from chat.",
        "mode": "local",
    }
