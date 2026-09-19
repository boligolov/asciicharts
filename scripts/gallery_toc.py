#!/usr/bin/env python3
"""Keep the table of contents at the top of docs/gallery.md in step with its headings.

    python scripts/gallery_toc.py            # rewrite the contents block
    python scripts/gallery_toc.py --check    # exit 1 if it is out of date

The block sits between <!-- toc --> and <!-- /toc -->. Every "###" heading is listed, grouped by the
chart type it starts with (the first word).
"""
import re
import sys
from pathlib import Path

GALLERY = Path(__file__).resolve().parent.parent / "docs" / "gallery.md"
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


def main(argv):
    text = GALLERY.read_text(encoding="utf-8")
    new = updated(text)
    if "--check" in argv:
        if new != text:
            print("docs/gallery.md contents are out of date; run python scripts/gallery_toc.py", file=sys.stderr)
            return 1
        return 0
    GALLERY.write_text(new, encoding="utf-8", newline="\n")
    print(f"updated {GALLERY.name}: {len(headings(new))} examples")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
