"""The skill folder is self-contained, in sync with the repository, and its documented commands work."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]  # the repository
SKILL = ROOT / "skills" / "asciicharts"
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}


def frontmatter_and_body():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, "SKILL.md must start with a YAML frontmatter block"
    fields = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, m.group(2)


def test_shared_files_are_in_sync_with_the_repository():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_skill.py"), "--check"],
                       capture_output=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def test_frontmatter_is_valid():
    fields, _ = frontmatter_and_body()
    assert set(fields) <= ALLOWED_KEYS and {"name", "description"} <= set(fields)
    assert fields["name"] == SKILL.name == "asciicharts"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fields["name"]) and len(fields["name"]) <= 64
    assert 0 < len(fields["description"]) <= 1024, len(fields["description"])
    assert "<" not in fields["description"] and ">" not in fields["description"]
    assert fields["license"] == "MIT"


def test_description_says_what_it_does_and_when_to_use_and_when_not():
    desc = frontmatter_and_body()[0]["description"].lower()
    for needle in ("chart", "csv", "trigger", "even if the user never says", "not for"):
        assert needle in desc, needle


def test_body_is_lean():
    _, body = frontmatter_and_body()
    assert len(body.splitlines()) < 500


def test_every_relative_link_stays_inside_the_skill_and_exists():
    _, body = frontmatter_and_body()
    links = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", body)
    assert {"references/reference.md", "references/gallery.md", "references/principles.md",
            "references/drawing.md", "references/glyphs.md"} <= set(links)
    for link in links:
        if re.match(r"^[a-z]+://", link):
            continue
        target = (SKILL / link).resolve()
        assert SKILL.resolve() in target.parents, f"{link} points outside the skill folder"
        assert target.is_file(), f"{link} does not exist"


def test_references_do_not_link_outside_the_skill():
    for ref in (SKILL / "references").glob("*.md"):
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", ref.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+://", link):
                continue
            assert SKILL.resolve() in (ref.parent / link).resolve().parents, f"{ref.name}: {link}"


def test_skill_folder_has_only_expected_parts():
    names = {p.name for p in SKILL.iterdir()}
    assert names == {"SKILL.md", "LICENSE", "scripts", "references"}, names
    assert {p.name for p in (SKILL / "scripts").iterdir()} == {"asciicharts.py"}


# --- the commands SKILL.md shows actually work when run from the skill folder ---

def run(args, cwd=SKILL, stdin=None):
    return subprocess.run([sys.executable, *args], cwd=cwd, input=stdin, capture_output=True,
                          encoding="utf-8", env={"PYTHONIOENCODING": "utf-8", "PATH": ""})


def test_quick_start_json_on_stdin():
    spec = ('{"chartType":"hbar","title":"Browser share","labels":["Chrome","Firefox","Safari"],'
            '"series":[{"values":[62,21,12]}]}')
    r = run(["scripts/asciicharts.py", "-"], stdin=spec)
    assert r.returncode == 0 and "Browser share" in r.stdout and "Chrome" in r.stdout


def test_quick_start_csv_matches_the_example_in_the_skill(tmp_path):
    (tmp_path / "latency.csv").write_text(
        "endpoint,p50,p99,errors\n/login,120,480,3\n/search,340,1900,12\n/checkout,210,950,7\n"
        "/health,5,9,0\n/upload,800,4200,21\n", encoding="utf-8")
    r = run([str(SKILL / "scripts" / "asciicharts.py"), "--csv", "latency.csv", "--chart", "hbar", "--values", "p99",
             "--sort", "-p99", "--limit", "3", "--set", "title=Slowest endpoints, p99 ms"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout in (SKILL / "SKILL.md").read_text(encoding="utf-8"), "the example output in SKILL.md is stale"


def test_list_flag_and_error_convention():
    assert "hbar" in run(["scripts/asciicharts.py", "--list"]).stdout
    r = run(["scripts/asciicharts.py", "--json", '{"chartType":"line","series":[{"values":[1]}]}'])
    assert r.returncode == 1 and r.stdout == "" and r.stderr.startswith("error: ")


@pytest.mark.parametrize("ref", ["reference.md", "gallery.md", "principles.md", "drawing.md", "glyphs.md"])
def test_references_exist_and_are_not_empty(ref):
    assert len((SKILL / "references" / ref).read_text(encoding="utf-8")) > 1000


# --- packaging -------------------------------------------------------------

def test_package_skill_builds_an_uploadable_zip(tmp_path):
    import zipfile
    out = tmp_path / "asciicharts.skill"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "package_skill.py"), "--out", str(out)],
                       capture_output=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert z.testzip() is None
        assert "asciicharts/SKILL.md" in names, names
        assert {n.split("/")[0] for n in names} == {"asciicharts"}  # one top-level folder
        assert "asciicharts/scripts/asciicharts.py" in names and "asciicharts/LICENSE" in names
        assert not [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
        assert z.read("asciicharts/SKILL.md") == (SKILL / "SKILL.md").read_bytes()


def test_glyph_cheat_sheet_matches_the_renderer():
    """The glyph sets in references/glyphs.md are the renderer's own, in its order."""
    import asciicharts
    sheet = (SKILL / "references" / "glyphs.md").read_text(encoding="utf-8")
    for glyphs in (asciicharts.FILLS, asciicharts.HALFTONE_FILLS, asciicharts.ASCII_FILLS, asciicharts.MARKERS,
                   asciicharts.ASCII_MARKERS, asciicharts.SPARK_TICKS, asciicharts.SHADES[1:]):
        assert "`" + " ".join(glyphs) + "`" in sheet, glyphs
    assert f"`{asciicharts.ASCII_TRACK_FILL}`" in sheet and f"`{asciicharts.OVERLAP_MARKER}`" in sheet

