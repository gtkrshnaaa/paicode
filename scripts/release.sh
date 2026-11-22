#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
rm -rf dist
"$PYTHON" -m build
"$PYTHON" - <<'PY'
import hashlib
import json
from pathlib import Path

import paicode

dist = Path("dist")
artifacts = sorted([*dist.glob("*.whl"), *dist.glob("*.tar.gz")])
lines = []
for path in artifacts:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f"{digest}  {path.name}")
(dist / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")

sbom = {
    "format": "paicode-sbom-1",
    "packages": [
        {"name": "paicode", "version": paicode.__version__},
        {"name": "openai", "version": "3.57.0"},
        {"name": "textual", "version": "8.2.8"},
        {"name": "rich", "version": "15.0.0"},
        {"name": "Pygments", "version": "2.21.0"},
    ],
}
(dist / "sbom.json").write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {len(artifacts)} artifacts with checksums and SBOM")
PY
