import json
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from firstlook.db import connect
from firstlook.embed import Encoder
from firstlook.match import Profile, feedback, get_profile, rank, save_profile
from firstlook.paths import ROOT
from firstlook.registry import companies, seed

app = FastAPI(title="firstlook", version="0.1.0")


@app.middleware("http")
async def local_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and origin
        and urlparse(origin).hostname not in ("127.0.0.1", "localhost", "::1")
    ):
        return JSONResponse({"detail": "Only local browser origins are permitted"}, status_code=403)
    return await call_next(request)


@app.exception_handler(ValueError)
async def value_error(request: Request, exc: ValueError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0", "matching": Encoder().note}


@app.get("/api/jobs")
def jobs() -> list[dict]:
    db = connect()
    try:
        return rank(db, include_filtered=True)
    finally:
        db.close()


@app.post("/api/jobs/{job_id}/star")
def star(job_id: int) -> dict:
    with connect() as db:
        db.execute("UPDATE job SET starred=1-starred,touched=1 WHERE id=?", (job_id,))
        row = db.execute("SELECT starred FROM job WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise ValueError("Job not found")
        return {"starred": bool(row[0])}


@app.post("/api/jobs/{job_id}/feedback")
def job_feedback(job_id: int, data: dict) -> dict:
    with connect() as db:
        feedback(db, job_id, int(data["label"]))
    return {"saved": True}


@app.get("/api/profile")
def profile() -> dict:
    with connect() as db:
        return get_profile(db).model_dump()


@app.put("/api/profile")
def update_profile(data: Profile) -> dict:
    with connect() as db:
        save_profile(db, data)
    return data.model_dump()


@app.get("/api/registry")
def registry() -> list[dict]:
    with connect() as db:
        return companies(db)


@app.post("/api/registry/seed")
def registry_seed() -> dict:
    with connect() as db:
        return {"count": seed(db)}


@app.put("/api/registry/{company_id}")
def registry_edit(company_id: str, data: dict) -> dict:
    from firstlook.extract import set_tags

    with connect() as db:
        set_tags(db, company_id, data.get("tags", []))
        if "token" in data:
            db.execute(
                "UPDATE company SET token=?,verified=0 WHERE id=?", (str(data["token"]), company_id)
            )
    return {"saved": True}


@app.get("/api/settings")
def settings() -> dict:
    with connect() as db:
        return {
            r["key"]: json.loads(r["value"])
            for r in db.execute("SELECT * FROM setting")
            if r["key"] != "reranker"
        }


@app.put("/api/settings")
def update_settings(data: dict) -> dict:
    allowed = {
        "saved_searches",
        "ghost_days",
        "daily_tokens",
        "run_tokens",
        "minimum_sample",
        "reminder_days",
        "provider",
        "theme",
    }
    if set(data) - allowed:
        raise ValueError(
            "Unsupported setting. Credentials belong in environment variables or OS keyring."
        )
    with connect() as db:
        for key, value in data.items():
            db.execute(
                "INSERT INTO setting(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )
    return {"saved": True}


@app.post("/api/demo")
def demo() -> dict:
    from firstlook.demo import populate

    with connect() as db:
        if db.execute("SELECT count(*) FROM job").fetchone()[0]:
            raise ValueError(
                "Load demo only into an empty database to preserve your profile and jobs."
            )
        note = populate(db)
    return {"note": note}


@app.post("/api/crawl")
def crawl() -> dict:
    from firstlook.embed import index
    from firstlook.ingest import crawl as run
    from firstlook.ingest.http import PoliteClient
    from firstlook.match import require_targets

    with connect() as db:
        require_targets(db)
        client = PoliteClient(db)
        try:
            result = run(db, client)
            result["note"] = index(db)
            return result
        finally:
            client.close()


@app.get("/api/crawls")
def crawls() -> list[dict]:
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM crawl_run ORDER BY id DESC LIMIT 30")]


# Feature routers are registered above the final static fallback.
def mount_frontend() -> None:
    static = ROOT / "frontend/dist"
    if static.exists():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        index = static / "index.html"
        if path.startswith("api/"):
            return JSONResponse({"detail": "Unknown API route"}, status_code=404)
        return (
            FileResponse(index)
            if index.exists()
            else JSONResponse({"detail": "Run npm run build in frontend/"}, status_code=503)
        )


from firstlook.api.tailor import router as tailor_router  # noqa: E402

app.include_router(tailor_router)

from firstlook.api.chat import router as chat_router  # noqa: E402

app.include_router(chat_router)
