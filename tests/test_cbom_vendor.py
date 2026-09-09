"""The standalone engines must remain the identified public source distribution."""

import hashlib
import json
from pathlib import Path


def test_bundled_cbom_matches_its_public_source_manifest():
    root = Path(__file__).resolve().parents[1] / "agents/CBOM"
    manifest = json.loads((root / "vendor-manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"] == "https://github.com/monurkeskin/CBOM"
    assert manifest["license"] == "GPL-3.0-only"
    assert "_vendor/cbom/model.py" in manifest["files"]
    assert "java/src/org/cbom/ConflictBasedOpponentModel.java" in manifest["files"]
    for name, expected in manifest["files"].items():
        path = root / name
        assert path.resolve().is_relative_to(root.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    namespace = {}
    # Version metadata is checked without executing either bundled engine.
    for line in (root / "_vendor/cbom/__init__.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__ = "):
            namespace["version"] = json.loads(line.split("=", 1)[1])
    assert namespace["version"] == manifest["version"]
