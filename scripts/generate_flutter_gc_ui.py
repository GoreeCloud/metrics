#!/usr/bin/env python3
"""Offline deterministic Dart color bridge from pinned GoreeCloud UI tokens."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps/native/design/gc.tokens.json"
OUTPUT = ROOT / "apps/native/lib/gc_ui_colors.dart"
SOURCE_SHA256 = "d3226033ba50d601fcabbb01eadc2fdff8eb1be6cde6f6ebe8b0b47f1041e8e0"

ROLES = {
    "canvas": "canvas",
    "surface": "surface",
    "surfaceTonal": "surface-tonal",
    "text": "text",
    "textSoft": "text-soft",
    "outline": "outline",
    "outlineSoft": "outline-soft",
    "positive": "positive",
    "onPositive": "on-positive",
    "warning": "warning",
    "onWarning": "on-warning",
    "negative": "negative",
    "onNegative": "on-negative",
    "focusRing": "focus-ring",
    "brand": "brand",
    "onBrand": "on-brand",
    "brandContainer": "brand-container",
    "onBrandContainer": "on-brand-container",
}


def render() -> str:
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Canonical token snapshot checksum changed; requires independent review")
    data = json.loads(raw)
    if (data["meta"]["name"] != "GoreeCloud UI"
        or data["meta"]["format"] != "goreecloud-ui-alpha-1"
        or data["meta"]["license"] != "MIT"):
        raise ValueError("Unreviewed or mismatched GoreeCloud UI authority")
    radius = data["foundations"]["radius"]["md"]
    if not re.fullmatch(r"[0-9]+px", radius):
        raise ValueError("Unexpected GC UI radius unit")
    values = {}
    for mode in ("light", "dark"):
        merged = data["semantic"][mode] | data["accents"]["lagoon"][mode]
        values[mode] = {}
        for prop, token_name in ROLES.items():
            hex_value = merged[token_name]
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_value):
                raise ValueError("Unexpected non-opaque color: " + token_name)
            values[mode][prop] = "0xFF" + hex_value[1:].upper()
    lines = [
        "// GENERATED from canonical GoreeCloud/gc-ui alpha tokens. DO NOT EDIT.",
        "// Immutable source commit: be8b819748d1ef0f6b2d3e786f4b22864cb3d07d",
        "// Generator: scripts/generate_flutter_gc_ui.py",
        "// License: MIT. Candidate values pending founder visual acceptance.",
        "import 'package:flutter/material.dart';",
        "",
        "@immutable",
        "class GCUIColorRoles {",
    ]
    for prop in ROLES:
        lines.append("  final Color " + prop + ";")
    lines.extend(["", "  const GCUIColorRoles({"])
    for prop in ROLES:
        lines.append("    required this." + prop + ",")
    lines.extend(["  });", "}", "", "abstract final class GoreeCloudUIColors {",
                  "  static const double radiusMedium = " + radius[:-2] + ".0;", ""])
    for mode in ("light", "dark"):
        lines.append("  static const GCUIColorRoles " + mode + " = GCUIColorRoles(")
        for prop, color in values[mode].items():
            lines.append("    " + prop + ": Color(" + color + "),")
        lines.extend(["  );", ""])
    lines.extend([
        "  static GCUIColorRoles forBrightness(Brightness brightness) =>",
        "      brightness == Brightness.dark ? dark : light;",
        "}",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.write:
        OUTPUT.write_text(expected, encoding="utf-8")
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
        raise SystemExit("Generated GC UI native color bridge is stale")
    print("GC UI native Dart tokens match immutable source snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
