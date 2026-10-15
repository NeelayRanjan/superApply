"""Local statistics with explicit sample gates and censoring."""

import csv
import io
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return 0.0, 1.0
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0, center - radius), min(1, center + radius)


def summary(rows: list[dict], minimum=12) -> dict:
    n = len(rows)
    responses = sum(bool(r["response_at"]) for r in rows)
    minutes = sum(r.get("minutes", 0) for r in rows)
    result = {
        "applications": n,
        "responses": responses,
        "minutes": round(minutes, 2),
        "rate": None,
        "low": None,
        "high": None,
        "responses_per_hour": None,
        "needed": max(0, minimum - n),
    }
    if n >= minimum:
        result.update(
            rate=responses / n,
            low=wilson(responses, n)[0],
            high=wilson(responses, n)[1],
            responses_per_hour=responses / (minutes / 60) if minutes > 0 else None,
        )
    return result


def survival(durations: list[float], events: list[bool]) -> list[dict]:
    if len(durations) != len(events):
        raise ValueError("Durations and events must align")
    values = np.asarray(durations, dtype=float)
    if np.any(values < 0):
        raise ValueError("Durations must not be negative")
    observed = np.asarray(events, dtype=bool)
    probability = 1.0
    greenwood = 0.0
    curve = [
        {"day": 0.0, "survival": 1.0, "low": 1.0, "high": 1.0, "at_risk": len(values), "events": 0}
    ]
    for day in np.unique(values):
        risk = int(np.sum(values >= day))
        occurred = int(np.sum((values == day) & observed))
        if occurred:
            probability *= 1 - occurred / risk
            if risk > occurred:
                greenwood += occurred / (risk * (risk - occurred))
        se = probability * math.sqrt(greenwood)
        curve.append(
            {
                "day": float(day),
                "survival": probability,
                "low": max(0, probability - 1.96 * se),
                "high": min(1, probability + 1.96 * se),
                "at_risk": risk,
                "events": occurred,
            }
        )
    return curve


def date(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def extra_samples(p1: float, p2: float, n1: int, n2: int) -> int | None:
    gap = abs(p1 - p2)
    if gap < 1e-9:
        return None
    pooled = (p1 + p2) / 2
    needed = math.ceil(2 * 1.96**2 * pooled * (1 - pooled) / (gap * gap))
    return max(0, needed - min(n1, n2))


def report(db: sqlite3.Connection, as_of: str | None = None) -> dict:
    setting = db.execute("SELECT value FROM setting WHERE key='minimum_sample'").fetchone()
    minimum = max(1, int(json.loads(setting[0]))) if setting else 12
    rows = [
        dict(r)
        for r in db.execute("""SELECT a.*,j.first_seen,c.tags,c.size,c.platform,e.data extraction FROM application a
        JOIN job j ON j.id=a.job_id JOIN company c ON c.id=j.company_id LEFT JOIN job_extract e ON e.job_id=j.id WHERE a.applied_at IS NOT NULL""")
    ]
    end = date(as_of) if as_of else datetime.now(timezone.utc)
    groups: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        ex = json.loads(row["extraction"] or "{}")
        lag = max(0, (date(row["applied_at"]) - date(row["first_seen"])).total_seconds() / 86400)
        row["lead_time"] = "0–1 days" if lag < 2 else "2–7 days" if lag < 8 else "8+ days"
        row["variant"] = str(row["variant_id"] or "unassigned")
        row["referral"] = "Referred" if row["referral"] else "No referral"
        row["seniority"] = ex.get("seniority", "unknown")
        row["remote"] = ex.get("remote", "unknown")
        tags = json.loads(row["tags"]) or ["Uncategorised"]
        for tag in tags:
            groups["category"][tag].append(row)
            groups["variant_within_category"][tag + " / variant " + row["variant"]].append(row)
        for dimension in [
            "size",
            "platform",
            "seniority",
            "remote",
            "referral",
            "variant",
            "lead_time",
        ]:
            groups[dimension][str(row[dimension])].append(row)
    tables = {
        dimension: [
            dict(segment=key, **summary(value, minimum)) for key, value in sorted(segments.items())
        ]
        for dimension, segments in groups.items()
    }
    for table in tables.values():
        gated = [r for r in table if r["rate"] is not None]
        for row in table:
            row["comparison_note"] = "Counts only until the minimum sample is reached."
            row["additional_to_distinguish"] = None
            if row["rate"] is not None:
                others = [r for r in gated if r is not row]
                if others:
                    other = others[0]
                    row["additional_to_distinguish"] = extra_samples(
                        row["rate"], other["rate"], row["applications"], other["applications"]
                    )
                    row["comparison_note"] = (
                        "Worth noticing; observational data, not a causal claim. Sample estimate uses the current gap and a normal approximation."
                    )
    durations = [
        max(
            0,
            (
                (date(r["response_at"]) if r["response_at"] else end) - date(r["applied_at"])
            ).total_seconds()
            / 86400,
        )
        for r in rows
    ]
    events = [bool(r["response_at"]) for r in rows]
    curve = survival(durations, events) if len(rows) >= minimum else []
    # Conditional response over observed follow-up only; never extrapolate to "ever".
    if curve:
        for point in curve:
            point["response_within_observed_window"] = (
                1 - curve[-1]["survival"] / point["survival"] if point["survival"] else None
            )
    median = next((math.ceil(p["day"]) for p in curve if p["survival"] <= 0.5), None)
    return {
        "overall": summary(rows, minimum),
        "tables": tables,
        "survival": curve,
        "minimum_sample": minimum,
        "suggested_reminder_days": max(7, min(60, median)) if median is not None else 14,
        "survival_note": "Kaplan–Meier probability of still waiting for a response. Unanswered applications are right-censored at the analysis date; estimates do not predict beyond observed follow-up.",
    }


def export_csv(data: dict, table: str) -> str:
    rows = (
        data["survival"]
        if table == "survival"
        else [data["overall"]]
        if table == "overall"
        else data["tables"].get(table, [])
    )
    output = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v)
                for k, v in row.items()
            }
        )
    return output.getvalue()
