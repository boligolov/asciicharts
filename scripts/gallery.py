#!/usr/bin/env python3
"""Render one example of every chart type/style (the source of skills/asciicharts/references/gallery.md).

    python scripts/gallery.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asciicharts import ChartError, render_chart  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

for g in json.loads((ROOT / "tests" / "golden" / "gallery.json").read_text(encoding="utf-8")):
    try:
        out = render_chart(g["spec"])
    except ChartError as e:
        out = f"ERROR: {e}"
    print(f"=== {g['name']} ===\n{out}\n")
