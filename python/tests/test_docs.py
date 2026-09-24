"""Documentation hygiene: the charts shown on landing pages must look right in common default fonts."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]  # the repository

# Fractional block glyphs that Consolas, Courier New and Lucida Console (the default monospace fonts on
# Windows, hence GitHub and most IDEs there) do not contain. When a font lacks a glyph the OS substitutes
# another font with a different width, and the right border of an otherwise rectangular chart goes crooked.
# (Verified against those fonts' character maps.) The gallery is exempt: its job is to show every glyph.
NOT_IN_COMMON_FONTS = "▁▂▃▅▆▇▉▊▋▍▎▏"

LANDING_PAGES = ["README.md", "docs/development.md", "docs/skill.md",
                 "skills/asciicharts/SKILL.md", "skills/asciicharts/references/reference.md"]


@pytest.mark.parametrize("page", LANDING_PAGES)
def test_landing_page_charts_avoid_glyphs_missing_from_common_fonts(page):
    text = (ROOT / page).read_text(encoding="utf-8")
    for i, m in enumerate(re.finditer(r"```[^\n]*\n(.*?)```", text, re.S)):
        offenders = sorted({c for c in m.group(1) if c in NOT_IN_COMMON_FONTS})
        assert not offenders, (
            f"{page}, code block {i}: uses {''.join(offenders)}, which Consolas lacks; pick data whose bars end on "
            f"whole cells, or use style 'ascii'/'halftone', so the chart doesn't render with a ragged border")


def test_every_framed_chart_in_the_docs_is_rectangular():
    checked = 0
    for page in LANDING_PAGES + ["docs/gallery.md"]:
        text = (ROOT / page).read_text(encoding="utf-8")
        for i, m in enumerate(re.finditer(r"```[^\n]*\n(.*?)```", text, re.S)):
            lines = [l for l in m.group(1).split("\n") if l.strip()]
            if lines and lines[0][0] in "┌╭╔┏+" and lines[-1][0] in "└╰╚┗+":
                assert len({len(l) for l in lines}) == 1, f"{page}, block {i}: lines differ in length"
                checked += 1
    assert checked > 25


# --- the gallery -----------------------------------------------------------

def test_gallery_contents_links_resolve_to_headings():
    text = (ROOT / "docs" / "gallery.md").read_text(encoding="utf-8")
    toc = text[text.index("<!-- toc -->"):text.index("<!-- /toc -->")]
    anchors = {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-") for h in re.findall(r"^### (.+)$", text, re.M)}
    linked = re.findall(r"\]\(#([^)]+)\)", toc)
    assert len(linked) == len(anchors) >= 25 and set(linked) == anchors


def test_gallery_shows_every_chart_type():
    text = (ROOT / "docs" / "gallery.md").read_text(encoding="utf-8")
    for chart_type in ("sparkline", "vbar", "hbar", "line", "area", "scatter", "dual_axis", "pie", "histogram",
                       "heatmap", "boxplot", "dotplot"):
        assert f'"chartType": "{chart_type}"' in text, chart_type


def test_readme_links_to_the_gallery_right_under_the_title():
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# ")
    assert "docs/gallery.md" in "\n".join(lines[1:4]), "the gallery link should be the first thing under the title"


def test_the_skills_copy_of_the_gallery_is_the_docs_gallery():
    assert (ROOT / "docs" / "gallery.md").read_bytes() == (ROOT / "skills" / "asciicharts" / "references" / "gallery.md").read_bytes()


def _fenced(text):
    blocks, cur, lang = [], None, None
    for line in text.split("\n"):
        if line.startswith("```"):
            if cur is None:
                cur, lang = [], line[3:].strip()
            else:
                blocks.append((lang, "\n".join(cur)))
                cur = None
        elif cur is not None:
            cur.append(line)
    return blocks


def test_site_examples_are_current():
    """site/src/data/charts.json is checked in; it must be what the renderer produces today."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "site_examples.py"), "--check"], capture_output=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("script", ["gen_go_unicode.py", "gen_go_catalog.py"])
def test_the_go_implementations_generated_files_are_current(script):
    """The Go implementation's Unicode tables and chart catalogue are generated from this one."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--check"], capture_output=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def test_every_gallery_output_is_current():
    """In the gallery and in the skill's hand-drawing guide, the printed output under each spec is
    exactly what the renderer produces today, and the gallery's contents list matches its headings."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gallery_refresh.py"), "--check"], capture_output=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def test_the_doc_gallery_shows_exactly_the_golden_examples():
    import json
    from asciicharts import render_chart
    blocks = _fenced((ROOT / "docs" / "gallery.md").read_text(encoding="utf-8"))
    printed = [c for lang, c in blocks if lang != "json"]
    golden = json.loads((ROOT / "spec" / "conformance" / "gallery.json").read_text(encoding="utf-8"))
    assert sorted(render_chart(x["spec"]) for x in golden) == sorted(printed)  # same examples (the doc groups them by chart type)
