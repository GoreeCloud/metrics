"""Require immutable GitHub Actions commits; no floating action tags."""
import re
from pathlib import Path


def test_ci_workflow_pins_every_external_action():
    text = (Path(__file__).resolve().parents[1]
            / ".github/workflows/ci.yml").read_text()
    found = re.findall(r"^\s*-\s+uses:\s+(\S+)", text, flags=re.MULTILINE)
    assert len(found) >= 8
    for action in found:
        name, separator, sha = action.partition("@")
        assert separator and re.fullmatch(r"[0-9a-f]{40}", sha), action
        assert name.startswith(("actions/", "subosito/")), action
    assert len(found) == len(re.findall(r"^\s*-\s+uses:", text, flags=re.MULTILINE))
