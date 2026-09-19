#!/usr/bin/env python3
"""Re-render every example in docs/gallery.md from the JSON spec printed above it.

    python scripts/gallery_refresh.py           # rewrite the output blocks
    python scripts/gallery_refresh.py --check   # exit 1 if any printed output is stale

Each example is a ```json spec block immediately followed by its output block; the output is
replaced by what asciicharts.render_chart() produces for that spec today. Run it (then
scripts/gallery_toc.py and scripts/sync_skill.py) after changing how anything is drawn.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from asciicharts import render_chart  # noqa: E402

GALLERY = ROOT / "docs" / "gallery.md"


def refreshed(text: str):
    """(new_text, stale) where stale lists the titles of examples whose printed output was out of date."""
    lines = text.split("\n")
    out, stale, i = [], [], 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].startswith("```json"):
            j = i + 1
            while not lines[j].startswith("```"):
                out.append(lines[j])
                j += 1
            spec = json.loads("\n".join(lines[i + 1:j]))
            out.append(lines[j])  # closing fence of the spec
            k = j + 1
            while lines[k].strip() == "":  # blank line(s) between spec and output
                out.append(lines[k])
                k += 1
            assert lines[k].startswith("```") and not lines[k].startswith("```json"), f"no output block after {spec}"
            end = k + 1
            while not lines[end].startswith("```"):
                end += 1
            new = render_chart(spec).split("\n")
            if lines[k + 1:end] != new:
                stale.append(spec.get("title") or spec["chartType"])
            out.append(lines[k])
            out.extend(new)
            out.append(lines[end])
            i = end
        i += 1
    return "\n".join(out), stale


def main(argv):
    text = GALLERY.read_text(encoding="utf-8")
    new, stale = refreshed(text)
    if "--check" in argv:
        if stale:
            print("stale examples in docs/gallery.md: " + ", ".join(stale) + " (run python scripts/gallery_refresh.py)", file=sys.stderr)
            return 1
        return 0
    if stale:
        GALLERY.write_text(new, encoding="utf-8", newline="\n")
    print(f"{len(stale)} example(s) refreshed" + (": " + ", ".join(stale) if stale else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
