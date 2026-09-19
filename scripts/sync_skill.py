#!/usr/bin/env python3
"""Keep the skill folder's copies of shared files in step with the repository.

The skill (skills/asciicharts/) must be self-contained so it can be copied,
zipped or uploaded on its own, but the renderer and the licence live at the
repository root (the MCP server, the tests and pip use them) and the gallery in
docs/ (where readers of the repository look for it). This script
copies them in; the test suite fails if they ever differ.

    python scripts/sync_skill.py           # copy
    python scripts/sync_skill.py --check   # exit 1 if out of date, change nothing
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "asciicharts"
SHARED = {
    ROOT / "asciicharts.py": SKILL / "scripts" / "asciicharts.py",
    ROOT / "LICENSE": SKILL / "LICENSE",
    ROOT / "docs" / "gallery.md": SKILL / "references" / "gallery.md",
}


def stale():
    return [dst for src, dst in SHARED.items() if not dst.exists() or dst.read_bytes() != src.read_bytes()]


def main(argv):
    out_of_date = stale()
    if "--check" in argv:
        for dst in out_of_date:
            print(f"out of date: {dst.relative_to(ROOT)} (run python scripts/sync_skill.py)", file=sys.stderr)
        return 1 if out_of_date else 0
    for src, dst in SHARED.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"{src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
