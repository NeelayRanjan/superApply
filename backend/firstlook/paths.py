import os
from pathlib import Path

_package = Path(__file__).resolve().parent
_checkout = _package.parents[1]
ROOT = Path(
    os.environ.get(
        "FIRSTLOOK_ROOT", _checkout if (_checkout / "SPEC.md").exists() else _package / "resources"
    )
)
DATA = ROOT / "data"
FIXTURES = ROOT / "fixtures"
