"""Deterministic synthetic history: variant A 50%, B 25%, each n=60."""

import json
from pathlib import Path

rows = []
for i in range(120):
    variant = "A" if i < 60 else "B"
    response = i % 2 == 0 if variant == "A" else i % 4 == 0
    rows.append(
        {
            "variant": variant,
            "response": response,
            "minutes": 10 if variant == "A" else 20,
            "delay_days": 1 if variant == "A" else 5,
            "response_days": 7 if response else None,
        }
    )
Path("fixtures/history/applications.json").write_text(json.dumps(rows, indent=2))
