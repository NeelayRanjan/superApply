"""Enforce the spec's coverage floor per critical package, not by global average."""

import json
from pathlib import Path

report = json.loads(Path(".firstlook/coverage.json").read_text())
for package in ["adapters", "ingest", "extract", "match", "tailor", "analytics"]:
    rows = [
        value["summary"]
        for key, value in report["files"].items()
        if f"/firstlook/{package}/" in key
    ]
    total = sum(r["num_statements"] for r in rows)
    covered = sum(r["covered_lines"] for r in rows)
    percent = 100 * covered / max(1, total)
    print(f"{package}: {percent:.1f}%")
    if not total or percent < 80:
        raise SystemExit(f"{package} coverage below 80%")
