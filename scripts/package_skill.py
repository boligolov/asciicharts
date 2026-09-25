#!/usr/bin/env python3
"""Package skills/asciicharts/ as an uploadable .skill file (a zip archive).

    python scripts/package_skill.py                 # -> dist/asciicharts.skill
    python scripts/package_skill.py --site          # -> dist/ and site/public/asciicharts.skill (the download)
    python scripts/package_skill.py --out my.skill

The archive holds one top-level folder, asciicharts/, with SKILL.md directly inside,
which is the layout skill uploaders expect. It refuses to build if the copies of the
shared files inside the skill are out of date (see scripts/sync_skill.py).

The same files always give the same bytes (fixed timestamps and permissions, sorted
entries), so the copy the site offers for download, site/public/asciicharts.skill, can
be checked against a fresh build (a test does). After changing the skill: bump its version (SKILL.md
metadata.version and .claude-plugin/plugin.json), then `python scripts/package_skill.py --site`.
"""
import argparse
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_skill import ROOT, SKILL, stale  # noqa: E402

SKIP_DIRS = {"__pycache__", ".claude-plugin"}  # the plugin manifest is for Claude Code, not for uploads
SKIP_SUFFIXES = {".pyc", ".pyo"}
CRLF, LF = bytes([13, 10]), bytes([10])


def files():
    for path in sorted(SKILL.rglob("*")):
        if path.is_file() and not (SKIP_DIRS & set(path.relative_to(SKILL).parts)) and path.suffix not in SKIP_SUFFIXES:
            yield path


def version() -> str:
    """The skill's version, from .claude-plugin/plugin.json (the test keeps SKILL.md's metadata.version equal)."""
    import json
    return json.loads((SKILL / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def build() -> bytes:
    """The archive, deterministic: sorted entries, a fixed date, fixed permissions."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files():
            info = zipfile.ZipInfo(f"{SKILL.name}/{path.relative_to(SKILL).as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, path.read_bytes().replace(CRLF, LF))  # the same bytes on every OS
    return buf.getvalue()


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default=str(ROOT / "dist" / f"{SKILL.name}.skill"))
    p.add_argument("--site", action="store_true", help="also write site/public/asciicharts.skill, the download")
    args = p.parse_args(argv)

    if stale():
        print("the skill's copies are out of date; run python scripts/sync_skill.py first", file=sys.stderr)
        return 1
    if not (SKILL / "SKILL.md").is_file():
        print(f"{SKILL / 'SKILL.md'} is missing", file=sys.stderr)
        return 1

    data = build()
    outs = [Path(args.out)] + ([ROOT / "site" / "public" / f"{SKILL.name}.skill"] if args.site else [])
    for out in outs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(f"{out}  (version {version()}, {len(data)} bytes, {sum(1 for _ in files())} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
