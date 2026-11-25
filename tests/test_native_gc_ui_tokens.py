"""Immutable canonical GoreeCloud UI source ↔ native Flutter generated roles."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "apps/native/design/gc.tokens.json"
OUTPUT = ROOT / "apps/native/lib/gc_ui_colors.dart"
PROVENANCE = ROOT / "apps/native/design/provenance.json"


def test_token_snapshot_has_verified_provenance():
    meta = json.loads(PROVENANCE.read_text())
    raw = INPUT.read_bytes()
    tokens = json.loads(raw)
    assert meta["sha256"] == hashlib.sha256(raw).hexdigest()
    assert meta["license"] == tokens["meta"]["license"] == "MIT"
    assert tokens["meta"]["name"] == "GoreeCloud UI"
    assert meta["upstreamCommit"] == "be8b819748d1ef0f6b2d3e786f4b22864cb3d07d"


def test_dart_bridge_is_reproducible_and_used():
    result = subprocess.run(
        ["python3", "scripts/generate_flutter_gc_ui.py", "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    dart = OUTPUT.read_text()
    flutter_app = (ROOT / "apps/native/lib/main.dart").read_text()
    assert "GoreeCloudUIColors.forBrightness(brightness)" in flutter_app
    assert "scaffoldBackgroundColor: roles.canvas" in flutter_app
    assert "Color(0xFF00697A)" in dart
    assert "Color(0xFF8BE7F1)" in dart
    assert "0xFF0D121D" not in flutter_app
    assert "0xFFF6F7FB" not in flutter_app
