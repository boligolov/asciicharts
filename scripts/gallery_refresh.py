#!/usr/bin/env python3
"""Keep docs/gallery.md honest: re-render every example from the JSON spec printed above it, and
rebuild the table of contents from the headings.

    python scripts/gallery_refresh.py           # rewrite the output blocks and the contents
    python scripts/gallery_refresh.py --check   # exit 1 if either is stale

Each example is a ```json spec block immediately followed by its output block; the output is
replaced by what asciicharts.render_chart() produces for that spec today. The contents block sits
between <!-- toc --> and <!-- /toc -->: every "###" heading, grouped by the chart type it starts
with (the first word). Run it (then scripts/sync_skill.py) after changing how anything is drawn or
adding an example.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
from asciicharts import render_chart  # noqa: E402

GALLERY = ROOT / "docs" / "gallery.md"
# Every document whose examples are a ```json spec followed by its output. Only the gallery has a
# table of contents (the <!-- toc --> block); the others just get their outputs checked.
DOCS = [GALLERY, ROOT / "skills" / "asciicharts" / "references" / "drawing.md"]
START, END = "<!-- toc -->", "<!-- /toc -->"


def anchor(heading: str) -> str:
    """GitHub's heading id: lowercase, drop punctuation (keep - and _), spaces to hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def headings(text: str):
    return re.findall(r"^### (.+)$", text, re.M)


def build_toc(text: str) -> str:
    groups = {}
    for h in headings(text):
        m = re.match(r"^(\w+)\s*(?:\((.*)\))?$", h)
        kind, detail = (m.group(1), m.group(2)) if m else (h, None)
        groups.setdefault(kind, []).append((detail or "default", h))
    lines = []
    for kind, items in groups.items():
        links = " · ".join(f"[{detail}](#{anchor(h)})" for detail, h in items)
        lines.append(f"- **{kind}**: {links}" if len(items) > 1 or items[0][0] != "default"
                     else f"- **[{kind}](#{anchor(items[0][1])})**")
    return "\n".join(lines)


def updated(text: str) -> str:
    a, b = text.index(START) + len(START), text.index(END)
    return text[:a] + "\n" + build_toc(text) + "\n" + text[b:]


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
    status = 0
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        new, stale = refreshed(text)
        has_toc = START in text
        if has_toc:
            new = updated(new)
        toc_stale = has_toc and updated(text) != text
        name = doc.relative_to(ROOT).as_posix()
        if "--check" in argv:
            problems = (["stale examples: " + ", ".join(stale)] if stale else []) + (["stale contents"] if toc_stale else [])
            if problems:
                print(f"{name}: " + "; ".join(problems) + " (run python scripts/gallery_refresh.py)", file=sys.stderr)
                status = 1
            continue
        if new != text:
            doc.write_text(new, encoding="utf-8", newline="\n")
        print(f"{name}: {len(stale)} example(s) refreshed" + (": " + ", ".join(stale) if stale else "")
              + (f"; contents {'rebuilt' if toc_stale else 'up to date'} ({len(headings(new))} examples)" if has_toc else ""))
    return status

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
