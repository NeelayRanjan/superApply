import os
from pathlib import Path

ROOT = Path(os.environ.get("FIRSTLOOK_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "data"
FIXTURES = ROOT / "fixtures"
