import json
import sqlite3
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, model_validator

from firstlook.embed import Encoder, bm25, tokens


class Profile(BaseModel):
    titles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    remote: Literal["any", "remote", "hybrid", "onsite"] = "any"
    seniorities: list[str] = Field(
        default_factory=lambda: ["intern", "junior", "mid", "senior", "lead", "executive"]
    )
    must_skills: list[str] = Field(default_factory=list)
    nice_skills: list[str] = Field(default_factory=list)
    dealbreakers: list[str] = Field(default_factory=list)
    compensation_floor_cents: int = Field(default=0, ge=0)
    currency: str = "USD"
    needs_sponsorship: bool = False
    has_clearance: bool = False
    strong_threshold: float = Field(default=0.65, ge=0, le=1)
    possible_threshold: float = Field(default=0.3, ge=0, le=1)
    exploration_share: float = Field(default=0.1, ge=0, le=0.5)
    contact: dict[str, str] = Field(default_factory=dict)
    explicit_answers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_thresholds(self):
        if self.possible_threshold > self.strong_threshold:
            raise ValueError("Possible threshold must not exceed strong threshold")
        return self


def save_profile(db: sqlite3.Connection, profile: Profile) -> None:
    db.execute(
        "INSERT INTO profile(id,data) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
        (profile.model_dump_json(),),
    )
    db.commit()


def get_profile(db: sqlite3.Connection) -> Profile:
    row = db.execute("SELECT data FROM profile WHERE id=1").fetchone()
    return Profile.model_validate_json(row[0]) if row else Profile()


def require_targets(db: sqlite3.Connection) -> None:
    profile = get_profile(db)
    if not profile.titles or not profile.locations:
        raise ValueError("Choose target job titles and areas in Settings before crawling.")


def rank(
    db: sqlite3.Connection,
    profile: Profile | None = None,
    encoder: Encoder | None = None,
    include_filtered=False,
) -> list[dict]:
    profile = profile or get_profile(db)
    encoder = encoder or Encoder()
    rows = db.execute("""SELECT j.*,c.name company,c.tags,c.size,c.platform,e.data extraction FROM job j
        JOIN company c ON c.id=j.company_id LEFT JOIN job_extract e ON e.job_id=j.id
        WHERE j.closed_detected_at IS NULL AND (j.duplicate_of IS NULL OR NOT EXISTS(SELECT 1 FROM job p WHERE p.id=j.duplicate_of AND p.closed_detected_at IS NULL)) ORDER BY j.id""").fetchall()
    query = " ".join(profile.titles + profile.must_skills + profile.nice_skills)
    lexical = bm25(query, [r["title"] + " " + r["description"] for r in rows])
    vector = encoder.encode(query)
    model = db.execute("SELECT value FROM setting WHERE key='reranker'").fetchone()
    reranker = json.loads(model[0]) if model else None
    result = []
    for row, lex in zip(rows, lexical):
        item = dict(row)
        ex = json.loads(item.pop("extraction") or "{}")
        skillset = {s.lower() for s in ex.get("skills", []) + ex.get("preferred_skills", [])}
        matched = [s for s in profile.must_skills + profile.nice_skills if s.lower() in skillset]
        missing = [
            s
            for s in ex.get("skills", [])
            if s.lower() not in {v.lower() for v in profile.must_skills + profile.nice_skills}
        ]
        fired = []
        for term in profile.dealbreakers:
            if term.lower() in item["description"].lower():
                fired.append("Dealbreaker: " + term)
        if ex.get("seniority", "mid") not in profile.seniorities:
            fired.append("Seniority outside selected range")
        if profile.remote != "any" and ex.get("remote", "unknown") not in (
            profile.remote,
            "unknown",
        ):
            fired.append("Remote preference differs")
        locations = json.loads(item["locations"])
        if (
            profile.locations
            and not any(area.lower() in " ".join(locations).lower() for area in profile.locations)
            and "anywhere" not in [x.lower() for x in profile.locations]
        ):
            fired.append("Location outside target areas")
        if profile.needs_sponsorship and ex.get("visa") == "no":
            fired.append("Sponsorship unavailable")
        if ex.get("clearance") and not profile.has_clearance:
            fired.append("Clearance required")
        comp = ex.get("compensation", {})
        if (
            comp.get("max_cents", float("inf")) < profile.compensation_floor_cents
            and comp.get("currency", "USD") == profile.currency
            and comp.get("period", "year") == "year"
        ):
            fired.append("Compensation below floor")
        overlap = len(matched) / max(1, len(profile.must_skills + profile.nice_skills))
        title_overlap = max(
            (
                len(set(tokens(title)) & set(tokens(item["title"])))
                / max(1, len(set(tokens(title))))
                for title in profile.titles
            ),
            default=0,
        )
        semantic = lex
        cached = db.execute(
            "SELECT vector,model FROM job_embedding WHERE job_id=?", (item["id"],)
        ).fetchone()
        if vector is not None and cached and cached["model"] == encoder.model:
            semantic = float(np.dot(vector, json.loads(cached["vector"])))
        features = [lex, overlap, title_overlap, semantic]
        score = 0.3 * lex + 0.35 * overlap + 0.25 * title_overlap + 0.1 * semantic
        if reranker and reranker["count"] >= 50:
            learned = 1 / (
                1
                + np.exp(
                    -np.clip(np.dot(reranker["coef"], features) + reranker["intercept"], -30, 30)
                )
            )
            score = 0.7 * score + 0.3 * float(learned)
        band = (
            "filtered"
            if fired or score < profile.possible_threshold
            else "strong"
            if score >= profile.strong_threshold
            else "possible"
        )
        if band == "filtered" and not include_filtered:
            continue
        item.update(
            locations=locations,
            tags=json.loads(item["tags"]),
            extraction=ex,
            score=round(score, 4),
            band=band,
            matched=matched,
            missing=missing,
            dealbreakers=fired,
            features=features,
            exploration=False,
            mode=encoder.note,
        )
        duplicates = db.execute(
            "SELECT locations FROM job WHERE duplicate_of=? AND closed_detected_at IS NULL",
            (item["id"],),
        ).fetchall()
        item["locations"] = sorted(
            set(locations + [x for d in duplicates for x in json.loads(d[0])])
        )
        result.append(item)
    result.sort(key=lambda x: (-x["score"], x["id"]))
    eligible = [r for r in result if r["band"] == "possible" and not r["dealbreakers"]]
    share = min(len(eligible), int(len(result) * profile.exploration_share))
    for item in eligible[-share:] if share else []:
        item["exploration"] = True
        result.remove(item)
        result.insert(min(9, len(result)), item)
    return result


def feedback(db: sqlite3.Connection, job_id: int, label: int) -> None:
    job = next((x for x in rank(db, include_filtered=True) if x["id"] == job_id), None)
    if job is None:
        raise ValueError("Job not found")
    db.execute("DELETE FROM match_feedback WHERE job_id=?", (job_id,))
    db.execute(
        "INSERT INTO match_feedback(job_id,label,features) VALUES(?,?,?)",
        (job_id, int(label > 0), json.dumps(job["features"])),
    )
    db.commit()
    count = db.execute("SELECT count(*) FROM match_feedback").fetchone()[0]
    if count >= 50 and count % 10 == 0:
        train(db)


def train(db: sqlite3.Connection) -> dict:
    from sklearn.linear_model import LogisticRegression

    rows = db.execute("SELECT label,features FROM match_feedback ORDER BY id").fetchall()
    if len(rows) < 50 or len({r["label"] for r in rows}) < 2:
        return {
            "active": False,
            "count": len(rows),
            "note": "At least 50 labelled jobs, including positive and negative feedback, are needed.",
        }
    model = LogisticRegression(random_state=0).fit(
        [json.loads(r["features"]) for r in rows], [r["label"] for r in rows]
    )
    data = {
        "count": len(rows),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
    }
    db.execute(
        "INSERT INTO setting(key,value) VALUES('reranker',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (json.dumps(data),),
    )
    db.commit()
    return dict(data, active=True)
