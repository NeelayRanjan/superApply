"""The only LLM transport. Reserve budget atomically before any inference request."""

import hashlib
import json
import math
import os
import sqlite3
import uuid

import httpx


class Client:
    def __init__(self, db: sqlite3.Connection, transport=None, run_id: str | None = None):
        self.db = db
        self.transport = transport
        self.run_id = run_id or str(uuid.uuid4())

    def resolve(self) -> tuple[str, str, str] | None:
        local = os.environ.get("FIRSTLOOK_LOCAL_URL")
        if local:
            try:
                with httpx.Client(transport=self.transport, timeout=2) as client:
                    response = client.get(local.rstrip("/") + "/models")
                    response.raise_for_status()
                    models = response.json().get("data", [])
                    if models:
                        return (
                            local.rstrip("/"),
                            os.environ.get("FIRSTLOOK_LOCAL_MODEL", models[0]["id"]),
                            "",
                        )
            except (httpx.HTTPError, ValueError, KeyError):
                pass
        key = os.environ.get("FIRSTLOOK_API_KEY")
        url = os.environ.get("FIRSTLOOK_PROVIDER_URL")
        model = os.environ.get("FIRSTLOOK_MODEL")
        if key and url and model:
            if not url.startswith("https://"):
                raise ValueError("Hosted provider URL must use HTTPS")
            return url.rstrip("/"), model, key
        return None

    def limit(self, key: str, default: int) -> int:
        row = self.db.execute("SELECT value FROM setting WHERE key=?", (key,)).fetchone()
        return max(0, int(json.loads(row[0]))) if row else default

    def call(self, feature: str, job_id: int, content: str, max_output=512) -> dict:
        job = self.db.execute("SELECT touched,starred FROM job WHERE id=?", (job_id,)).fetchone()
        if not job or not (job["touched"] or job["starred"]):
            return {"text": "", "note": "Open or star a specific job before using AI.", "tokens": 0}
        provider = self.resolve()
        if not provider:
            return {
                "text": "",
                "note": "No provider configured. Local tools and deterministic tailoring remain available.",
                "tokens": 0,
            }
        url, model, key = provider
        cache_key = (
            "llm:"
            + hashlib.sha256(
                json.dumps([feature, model, content], ensure_ascii=False).encode()
            ).hexdigest()
        )
        cached = self.db.execute("SELECT value FROM cache WHERE key=?", (cache_key,)).fetchone()
        if cached:
            return dict(json.loads(cached[0]), tokens=0, cached=True)
        # UTF-8 bytes conservatively bound normal tokenizer input, with protocol overhead.
        reserve_input = len(content.encode()) + 256
        reserve = reserve_input + max_output
        self.db.commit()
        self.db.execute("BEGIN IMMEDIATE")
        daily = self.db.execute(
            "SELECT COALESCE(SUM(input_tokens+output_tokens),0) FROM llm_call WHERE date(created_at)=date('now')"
        ).fetchone()[0]
        run = self.db.execute(
            "SELECT COALESCE(SUM(input_tokens+output_tokens),0) FROM llm_call WHERE run_id=?",
            (self.run_id,),
        ).fetchone()[0]
        if daily + reserve > self.limit("daily_tokens", 20000) or run + reserve > self.limit(
            "run_tokens", 4000
        ):
            self.db.rollback()
            return {
                "text": "",
                "note": "Token ceiling reached. Continuing with local tools; no request was sent.",
                "tokens": 0,
            }
        row = self.db.execute(
            "INSERT INTO llm_call(feature,model,job_id,run_id,input_tokens,output_tokens,status) VALUES(?,?,?,?,?,?,?)",
            (feature, model, job_id, self.run_id, reserve_input, max_output, "reserved"),
        ).lastrowid
        self.db.commit()
        try:
            with httpx.Client(transport=self.transport, timeout=60) as client:
                response = client.post(
                    url + "/chat/completions",
                    headers={"Authorization": "Bearer " + key} if key else {},
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Use only supplied source facts. Never invent experience or change numbers. Never submit applications.",
                            },
                            {"role": "user", "content": content},
                        ],
                        "max_tokens": max_output,
                        "temperature": 0,
                    },
                )
                response.raise_for_status()
                data = response.json()
            usage = data.get("usage", {})
            input_tokens = int(usage.get("prompt_tokens", reserve_input))
            output_tokens = int(usage.get("completion_tokens", max_output))
            cents = (
                0
                if not key
                else math.ceil(
                    (
                        input_tokens
                        * float(os.environ.get("FIRSTLOOK_INPUT_CENTS_PER_MILLION", "1000"))
                        + output_tokens
                        * float(os.environ.get("FIRSTLOOK_OUTPUT_CENTS_PER_MILLION", "3000"))
                    )
                    / 1000000
                )
            )
            result = {
                "text": data["choices"][0]["message"]["content"],
                "note": "Generated suggestion — review before use.",
                "tokens": input_tokens + output_tokens,
            }
            self.db.execute(
                "UPDATE llm_call SET input_tokens=?,output_tokens=?,estimated_cost_cents=?,status=? WHERE id=?",
                (input_tokens, output_tokens, cents, "complete", row),
            )
            self.db.execute(
                "INSERT INTO cache(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (cache_key, json.dumps(result)),
            )
            self.db.commit()
            return result
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            # Keep reservation when provider usage is unknown; never silently refund possible spend.
            self.db.execute("UPDATE llm_call SET status='failed_usage_unknown' WHERE id=?", (row,))
            self.db.commit()
            return {
                "text": "",
                "note": "Provider unavailable. Budget reservation retained; local tools remain available.",
                "tokens": 0,
            }


def estimate(command: str, count=1) -> dict:
    free = command.split()[0] in (
        "crawl",
        "index",
        "match",
        "jobs",
        "analytics",
        "registry",
        "render",
        "tailor-local",
    )
    return {
        "command": command,
        "jobs": count,
        "predicted_tokens": 0 if free else count * 1500,
        "requires_yes": count > 25,
        "note": "AI estimates vary with source length; the client enforces the exact configured ceiling.",
    }
