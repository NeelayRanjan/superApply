"""Mark a milestone complete only after the caller has run make check."""

import re
import sys
from pathlib import Path

number = int(sys.argv[1])
path = Path("PLAN.md")
text = path.read_text()
pattern = rf"(## M{number} .*?)(?=\n## M|\Z)"
text = re.sub(pattern, lambda m: m[0].replace("- [ ]", "- [x]"), text, flags=re.S)
text = re.sub(
    r"Current task: .*",
    f"Current task: M{number + 1}." if number < 10 else "Current task: Complete — v0.1.0.",
    text,
)
path.write_text(text)
