"""Optional MiniLM ONNX encoder; lexical BM25 is always available offline."""

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

import numpy as np


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#]+", text.lower())


def bm25(query: str, documents: list[str]) -> list[float]:
    corpus = [tokens(d) for d in documents]
    if not corpus:
        return []
    average = sum(map(len, corpus)) / len(corpus) or 1
    frequencies = Counter(t for document in corpus for t in set(document))
    result = []
    for document in corpus:
        counts = Counter(document)
        score = 0.0
        for token in set(tokens(query)):
            tf = counts[token]
            idf = math.log(
                1 + (len(corpus) - frequencies[token] + 0.5) / (frequencies[token] + 0.5)
            )
            score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * len(document) / average))
        result.append(score)
    top = max(result, default=1) or 1
    return [s / top for s in result]


class Encoder:
    def __init__(self, path: Path = Path("models/minilm.onnx")):
        self.session = None
        self.tokenizer = None
        self.model = "bm25"
        if path.exists() and path.with_name("tokenizer.json").exists():
            try:
                import onnxruntime as ort
                from tokenizers import Tokenizer

                ort.disable_telemetry_events()
                self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
                self.tokenizer = Tokenizer.from_file(str(path.with_name("tokenizer.json")))
                self.tokenizer.enable_truncation(max_length=256)
                self.tokenizer.enable_padding()
                self.model = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            except (ImportError, RuntimeError, ValueError):
                self.session = None
        self.note = (
            "Local embeddings active"
            if self.session
            else "Lexical mode — optional embedding model is not installed."
        )

    def encode(self, text: str) -> list[float] | None:
        if self.session is None or self.tokenizer is None:
            return None
        encoded = self.tokenizer.encode(text)
        inputs = {
            "input_ids": np.array([encoded.ids], dtype=np.int64),
            "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
            "token_type_ids": np.array([encoded.type_ids], dtype=np.int64),
        }
        feed = {i.name: inputs[i.name] for i in self.session.get_inputs()}
        output = self.session.run(None, feed)[0]
        mask = inputs["attention_mask"][..., None]
        vector = (
            (output * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
            if output.ndim == 3
            else output
        )
        flat = vector[0]
        return (flat / max(float(np.linalg.norm(flat)), 1e-9)).tolist()


def index(db: sqlite3.Connection, encoder: Encoder | None = None) -> str:
    from firstlook.extract import index_extract

    index_extract(db)
    encoder = encoder or Encoder()
    for row in db.execute("SELECT * FROM job").fetchall():
        existing = db.execute(
            "SELECT content_hash,model FROM job_embedding WHERE job_id=?", (row["id"],)
        ).fetchone()
        if (
            existing
            and existing["content_hash"] == row["content_hash"]
            and existing["model"] == encoder.model
        ):
            continue
        vector = encoder.encode(row["title"] + " " + row["description"])
        if vector is not None:
            db.execute(
                "INSERT INTO job_embedding(job_id,model,content_hash,vector) VALUES(?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET model=excluded.model,content_hash=excluded.content_hash,vector=excluded.vector",
                (row["id"], encoder.model, row["content_hash"], json.dumps(vector)),
            )
    db.commit()
    from datetime import datetime, timezone

    from firstlook.match import train

    row = db.execute("SELECT value FROM setting WHERE key='reranker'").fetchone()
    trained = json.loads(row[0]).get("trained_at", "") if row else ""
    if trained[:10] != datetime.now(timezone.utc).date().isoformat():
        train(db)
    return encoder.note


def clusters(db: sqlite3.Connection) -> list[dict]:
    """Small local topic clusters; lexical seniority/title buckets when weights are absent."""
    rows = db.execute(
        "SELECT j.id,j.title,e.vector FROM job j LEFT JOIN job_embedding e ON e.job_id=j.id WHERE j.closed_detected_at IS NULL ORDER BY j.id"
    ).fetchall()
    vectors = [r for r in rows if r["vector"]]
    groups: dict[str, list[int]] = {}
    if len(vectors) >= 4:
        from sklearn.cluster import KMeans

        labels = KMeans(
            n_clusters=min(8, max(2, int(math.sqrt(len(vectors))))), random_state=0, n_init=10
        ).fit_predict([json.loads(r["vector"]) for r in vectors])
        for row, label in zip(vectors, labels):
            groups.setdefault(f"Topic {int(label) + 1}", []).append(row["id"])
    else:
        for row in rows:
            title_tokens = tokens(row["title"])
            key = " ".join(title_tokens[-2:]) or "Other"
            groups.setdefault(key, []).append(row["id"])
    return [{"name": key, "job_ids": value} for key, value in sorted(groups.items())]
