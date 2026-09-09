"""The standalone engines must remain the identified public source distribution."""

import hashlib
import json
from pathlib import Path


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_bundled_cbom_matches_its_public_source_manifest():
    root = Path(__file__).resolve().parents[1] / "agents/CBOM"
    manifest = json.loads((root / "vendor-manifest.json").read_text(encoding="utf-8"))
    _expect(manifest["source"] == "https://github.com/monurkeskin/CBOM", "Unexpected vendor source URL")
    _expect(manifest["license"] == "GPL-3.0-only", "Unexpected vendor license")
    _expect("_vendor/cbom/model.py" in manifest["files"], "Missing vendored model")
    _expect("java/src/org/cbom/ConflictBasedOpponentModel.java" in manifest["files"], "Missing vendored Java source")
    for name, expected in manifest["files"].items():
        path = root / name
        _expect(path.resolve().is_relative_to(root.resolve()), f"Manifest path escapes CBOM root: {name}")
        _expect(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"Manifest hash mismatch: {name}")
    namespace = {}
    # Version metadata is checked without executing either bundled engine.
    for line in (root / "_vendor/cbom/__init__.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__ = "):
            namespace["version"] = json.loads(line.split("=", 1)[1])
    _expect(namespace["version"] == manifest["version"], "Version metadata mismatch")
