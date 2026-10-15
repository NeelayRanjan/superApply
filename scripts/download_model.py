"""Explicit opt-in download only; never imported or invoked by application startup."""

import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen

root = Path("models")
root.mkdir(exist_ok=True)
revision = os.environ.get("FIRSTLOOK_MODEL_REVISION", "main")
base = f"https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/{revision}/"
manifest = {}
for source, target in [
    ("onnx/model_quantized.onnx", "minilm.onnx"),
    ("tokenizer.json", "tokenizer.json"),
]:
    with urlopen(base + source, timeout=120) as response:
        payload = response.read(100_000_001)
    if len(payload) > 100_000_000:
        raise SystemExit("Model exceeds the 100 MB cap; download rejected")
    (root / target).write_bytes(payload)
    manifest[target] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "source": base + source,
    }
(root / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(
    "Optional local model saved. Run firstlook index. Retain manifest.json to record the downloaded revision and hashes."
)
