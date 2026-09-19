"""The chart catalogue (list_charts / --list) can't drift from the renderers."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from asciicharts import CHART_TYPES, CHARTS, list_charts, render_chart

ROOT = Path(__file__).resolve().parent.parent
KNOWN_OPTIONS = {"labels", "width", "height", "mode", "style", "stacked", "bins", "threshold", "showPoints", "pointChar"}


def test_catalogue_covers_exactly_the_chart_types_in_order():
    assert CHART_TYPES == tuple(CHARTS)
    assert len(CHART_TYPES) == 12
    assert [c["type"] for c in list_charts()] == list(CHART_TYPES)


@pytest.mark.parametrize("chart", list_charts(), ids=lambda c: c["type"])
def test_entry_is_complete_and_its_example_renders(chart):
    assert set(chart) == {"type", "summary", "series", "options", "example"}
    assert chart["summary"] and chart["series"]
    assert set(chart["options"]) <= KNOWN_OPTIONS and len(set(chart["options"])) == len(chart["options"])
    assert chart["example"]["chartType"] == chart["type"]
    out = render_chart(chart["example"])
    assert out.strip()


@pytest.mark.parametrize("chart", list_charts(), ids=lambda c: c["type"])
def test_example_also_renders_bordered_and_without_border(chart):
    for border in ("none", "ascii", "rounded"):
        assert render_chart({**chart["example"], "border": border}).strip()


def test_listed_options_are_the_ones_that_change_the_output():
    """For each chart, an option it lists visibly changes the output, and the docs
    don't advertise options that do nothing for that chart."""
    variants = {
        "labels": ["x", "y", "z", "w", "v", "u"],
        "width": 25, "height": 7, "mode": "braille", "style": "ascii", "stacked": True, "bins": 3,
        "threshold": 20, "showPoints": True, "pointChar": "*",
    }
    for chart in list_charts():
        example = {**chart["example"], "border": "none"}
        if chart["type"] in ("vbar", "hbar", "area"):
            # stacking only means something with more than one series
            example["series"] = example["series"] + [{**example["series"][0], "name": "second"}]
        base = render_chart(example)
        for opt in KNOWN_OPTIONS:
            if opt in ("labels", "pointChar"):  # labels must match the data length; pointChar needs showPoints
                continue
            value = "dotted" if (chart["type"] == "line" and opt == "style") else variants[opt]
            changed = render_chart({**example, opt: value}) != base
            if opt in chart["options"]:
                assert changed, f"{chart['type']}: option {opt} is listed but changes nothing"
            else:
                assert not changed, f"{chart['type']}: option {opt} changes the output but is not listed"


def test_list_charts_returns_independent_copies():
    a = list_charts()
    a[0]["options"].append("junk")  # a caller mutating its copy must not corrupt the catalogue
    a[0]["example"]["series"].clear()
    assert "junk" not in CHARTS["sparkline"]["options"] and "junk" not in list_charts()[0]["options"]
    assert CHARTS["sparkline"]["example"]["series"] and list_charts()[0]["example"]["series"]


def test_cli_list():
    out = subprocess.run([sys.executable, str(ROOT / "asciicharts.py"), "--list"], capture_output=True,
                         encoding="utf-8", check=True, env={"PYTHONIOENCODING": "utf-8", "PATH": ""}).stdout
    for t in CHART_TYPES:
        assert f"\n{t}\n" in "\n" + out
    # every printed example is a valid one-line JSON spec
    for line in out.splitlines():
        if line.strip().startswith("example:"):
            spec = json.loads(line.split("example:", 1)[1])
            assert render_chart(spec)
