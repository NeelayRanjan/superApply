"""Deterministic selection, explicit suggestions, provenance-gated Typst exports."""

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from firstlook.bank import entries, expand
from firstlook.embed import tokens

LINE_BUDGET = 48


def number_tokens(text: str) -> Counter:
    return Counter(re.findall(r"\d[\d,]*(?:\.\d+)?%?", text))


def validate_line(line: dict, snapshot: dict) -> str:
    key = line.get("bank_entry_id")
    if not key or key not in snapshot:
        raise ValueError(
            f"Line {line.get('id', '?')} has no bank_entry_id provenance; export blocked"
        )
    entry = snapshot[key]
    index = line["source_index"]
    if index < 0 or index >= len(entry["bullets"]):
        raise ValueError("Invalid source bullet provenance")
    original = expand(entry["bullets"][index], entry["metrics"])
    text = expand(line["text"], entry["metrics"])
    if number_tokens(text) != number_tokens(original):
        raise ValueError("Rephrasing changes a locked metric or source number")
    return text


def get(db: sqlite3.Connection, variant_id: int) -> dict:
    row = db.execute("SELECT * FROM resume_variant WHERE id=?", (variant_id,)).fetchone()
    if not row:
        raise ValueError("Variant not found")
    result = dict(row)
    result["snapshot"] = json.loads(result.pop("bank_snapshot"))
    result["lines"] = [
        dict(r)
        for r in db.execute(
            "SELECT * FROM variant_line WHERE variant_id=? ORDER BY position,id", (variant_id,)
        )
    ]
    used_entries = {line["bank_entry_id"] for line in result["lines"]}
    used_entries.update(k for k, v in result["snapshot"].items() if v["kind"] == "identity")
    headers = sum(3 for key in used_entries if key in result["snapshot"])
    used = sum(max(1, (len(item["text"]) + 89) // 90) for item in result["lines"]) + headers
    result["remaining_lines"] = LINE_BUDGET - used
    result["overflow"] = used > LINE_BUDGET
    job = db.execute("SELECT data FROM job_extract WHERE job_id=?", (result["job_id"],)).fetchone()
    requirements = json.loads(job[0]).get("skills", []) if job else []
    bank_text = " ".join(json.dumps(v) for v in result["snapshot"].values()).lower()
    variant_text = " ".join(item["text"] for item in result["lines"]).lower()
    result["gap"] = {
        "not_surfaced": [
            s for s in requirements if s.lower() in bank_text and s.lower() not in variant_text
        ],
        "not_in_bank": [s for s in requirements if s.lower() not in bank_text],
    }
    return result


def create(db: sqlite3.Connection, job_id: int, template="classic") -> dict:
    if template not in ("classic", "compact"):
        raise ValueError("Unknown template")
    job = db.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
    if not job:
        raise ValueError("Job not found")
    db.execute("UPDATE job SET touched=1 WHERE id=?", (job_id,))
    bank = entries(db)
    key = hashlib.sha256(
        (job["content_hash"] + json.dumps(bank, sort_keys=True) + template).encode()
    ).hexdigest()
    cached = db.execute(
        "SELECT id FROM resume_variant WHERE cache_key=? AND used=0 ORDER BY id DESC LIMIT 1",
        (key,),
    ).fetchone()
    if cached:
        db.commit()
        return get(db, cached[0])
    snapshot = {e["id"]: e for e in bank}
    variant = db.execute(
        "INSERT INTO resume_variant(job_id,cache_key,template,bank_snapshot,note) VALUES(?,?,?,?,?)",
        (
            job_id,
            key,
            template,
            json.dumps(snapshot),
            "Local selection; no provider required. Every edit needs your review.",
        ),
    ).lastrowid
    query = set(tokens(job["title"] + " " + job["description"]))
    candidates = []
    for entry in bank:
        for n, bullet in enumerate(entry["bullets"]):
            text = expand(bullet, entry["metrics"])
            overlap = len(query & set(tokens(text + " " + " ".join(entry["tags"]))))
            candidates.append((-(overlap + entry["weight"]), entry["id"], n, text))
    budget = LINE_BUDGET - 3 * len(bank)
    for position, (_, entry_id, n, text) in enumerate(sorted(candidates)):
        lines = max(1, (len(text) + 89) // 90)
        if budget - lines < 0:
            continue
        budget -= lines
        db.execute(
            "INSERT INTO variant_line(variant_id,bank_entry_id,source_index,original,text,position) VALUES(?,?,?,?,?,?)",
            (variant, entry_id, n, text, text, position),
        )
    db.commit()
    return get(db, int(variant or 0))


def suggest(db: sqlite3.Connection, line_id: int, text: str) -> dict:
    line = db.execute("SELECT * FROM variant_line WHERE id=?", (line_id,)).fetchone()
    if not line:
        raise ValueError("Line not found")
    variant = get(db, line["variant_id"])
    if variant["used"]:
        raise ValueError("A variant used on an application is immutable")
    validate_line(dict(line, text=text), variant["snapshot"])
    db.execute("UPDATE variant_line SET suggestion=?,status='pending' WHERE id=?", (text, line_id))
    db.execute("UPDATE resume_variant SET ready=0 WHERE id=?", (line["variant_id"],))
    db.commit()
    return get(db, line["variant_id"])


def decide(db: sqlite3.Connection, line_id: int, accept: bool) -> dict:
    line = db.execute("SELECT * FROM variant_line WHERE id=?", (line_id,)).fetchone()
    if not line:
        raise ValueError("Line not found")
    variant = get(db, line["variant_id"])
    if variant["used"]:
        raise ValueError("A variant used on an application is immutable")
    if line["suggestion"] is None:
        raise ValueError("No pending suggestion")
    text = line["suggestion"] if accept else line["text"]
    validate_line(dict(line, text=text), variant["snapshot"])
    db.execute(
        "UPDATE variant_line SET text=?,suggestion=NULL,status=? WHERE id=?",
        (text, "accepted" if accept else "rejected", line_id),
    )
    db.execute("UPDATE resume_variant SET ready=0 WHERE id=?", (line["variant_id"],))
    db.commit()
    return get(db, line["variant_id"])


def parse_back(pdf: Path, required: list[str]) -> bool:
    text = " ".join((page.extract_text() or "") for page in PdfReader(pdf).pages)

    def normalize(x):
        return re.sub(r"\s+", "", x).casefold().replace("–", "-").replace("—", "-")

    return all(normalize(value) in normalize(text) for value in required if value)


def render(
    db: sqlite3.Connection, variant_id: int, output: Path = Path("exports"), compiler=None
) -> dict:
    variant = get(db, variant_id)
    if variant["used"]:
        return variant
    if not variant["lines"]:
        raise ValueError("Add your own experience to the bank before exporting")
    if variant["overflow"]:
        raise ValueError("Layout budget exceeded; remove lines before rendering")
    for line in variant["lines"]:
        validate_line(line, variant["snapshot"])
        if line["suggestion"] is not None:
            raise ValueError("Accept or reject every pending suggestion before exporting")
    identity = [v for v in variant["snapshot"].values() if v["kind"] == "identity"]
    if not identity:
        raise ValueError(
            "Add an identity bank entry with your name and contact details before export"
        )
    output.mkdir(parents=True, exist_ok=True)
    target = output.resolve() / f"resume-{variant_id}.pdf"

    def text(s):
        return "#text(" + json.dumps(s) + ")"

    sections = [
        '#set page(paper: "us-letter", margin: 0.65in)',
        '#set text(font: "Libertinus Serif", size: 10pt)',
        "#set par(leading: 0.65em)",
    ]
    required = []
    order = list(
        dict.fromkeys(
            [e["id"] for e in identity] + [line["bank_entry_id"] for line in variant["lines"]]
        )
    )
    for key in order:
        entry = variant["snapshot"][key]
        required.extend([entry["title"], entry["organisation"], entry["dates"]])
        sections.extend(
            [
                "#v(6pt)",
                "#strong[" + text(entry["title"]) + "]",
                text(entry["organisation"] + " | " + entry["dates"]),
            ]
        )
        for line in variant["lines"]:
            if line["bank_entry_id"] == key:
                sections.append("- " + text(validate_line(line, variant["snapshot"])))
    source = target.with_suffix(".typ")
    source.write_text("\n\n".join(sections))
    if compiler is None:
        binary = shutil.which("typst")
        if not binary:
            note = "Typst is not installed. Source is saved; install Typst to export and verify the PDF."
            db.execute("UPDATE resume_variant SET ready=0,note=? WHERE id=?", (note, variant_id))
            db.commit()
            return dict(get(db, variant_id), source_path=str(source))
        subprocess.run(
            [binary, "compile", str(source), str(target)], check=True, capture_output=True
        )
    else:
        compiler(source, target)
    ready = parse_back(target, required) and len(PdfReader(target).pages) == 1
    db.execute(
        "UPDATE resume_variant SET ready=?,pdf_path=?,note=? WHERE id=?",
        (
            int(ready),
            str(target),
            "Parse-back passed: identity, organisations, titles and dates verified."
            if ready
            else "Parse-back or single-page layout failed; export not ready.",
            variant_id,
        ),
    )
    db.commit()
    return get(db, variant_id)


def draft_answer(db: sqlite3.Connection, job_id: int, question: str) -> list[dict]:
    variant = create(db, job_id)
    query = set(tokens(question))
    lines = sorted(variant["lines"], key=lambda x: -len(set(tokens(x["text"])) & query))[:5]
    return [{"text": item["text"], "bank_entry_id": item["bank_entry_id"]} for item in lines]
