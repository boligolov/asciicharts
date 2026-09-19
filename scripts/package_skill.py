#!/usr/bin/env python3
"""Package skills/asciicharts/ as an uploadable .skill file (a zip archive).

    python scripts/package_skill.py                 # -> dist/asciicharts.skill
    python scripts/package_skill.py --out my.skill

The archive holds one top-level folder, asciicharts/, with SKILL.md directly inside,
which is the layout skill uploaders expect. It refuses to build if the copies of the
shared files inside the skill are out of date (see scripts/sync_skill.py).
"""
import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_skill import ROOT, SKILL, stale  # noqa: E402

SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def files():
    for path in sorted(SKILL.rglob("*")):
        if path.is_file() and not (SKIP_DIRS & set(path.relative_to(SKILL).parts)) and path.suffix not in SKIP_SUFFIXES:
            yield path


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default=str(ROOT / "dist" / f"{SKILL.name}.skill"))
    args = p.parse_args(argv)

    if stale():
        print("the skill's copies are out of date; run python scripts/sync_skill.py first", file=sys.stderr)
        return 1
    if not (SKILL / "SKILL.md").is_file():
        print(f"{SKILL / 'SKILL.md'} is missing", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files():
            z.write(path, f"{SKILL.name}/{path.relative_to(SKILL).as_posix()}")
    print(f"{out}  ({out.stat().st_size} bytes, {sum(1 for _ in files())} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
