"""Renderer tests: golden outputs (captured from the original Go implementation),
behavioral regressions, validation and limits."""

import json
from pathlib import Path

import pytest

from asciicharts import CHART_TYPES, ChartError, render_chart

GOLDEN = Path(__file__).parent / "golden"


def load(name):
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


# --- golden ---------------------------------------------------------------

def test_gallery_matches_golden():
    got = "".join(f"=== {g['name']} ===\n{render_chart(g['spec'])}\n\n" for g in load("gallery.json"))
    assert got == (GOLDEN / "gallery.txt").read_bytes().decode("utf-8")


@pytest.mark.parametrize("i,case", list(enumerate(load("corpus.json"))))
def test_corpus_matches_golden(i, case):
    if "err" in case:
        with pytest.raises(ChartError) as e:
            render_chart(case["spec"])
        assert str(e.value) == case["err"]
    else:
        assert render_chart(case["spec"]) == case["out"]


def test_every_chart_type_is_covered_by_the_gallery():
    assert {g["spec"]["chartType"] for g in load("gallery.json")} == set(CHART_TYPES)


# --- behavior -------------------------------------------------------------

def body_of(out):
    return out.split("\n\n")[0]


def test_grouped_vbar_series_distinct_without_color():
    out = render_chart({"chartType": "vbar", "height": 4, "labels": ["x", "y"], "series": [
        {"name": "A", "values": [10, 10]}, {"name": "B", "values": [10, 10]}]})
    assert "█" in body_of(out) and "▓" in body_of(out)


def test_single_series_vbar_stays_solid():
    out = render_chart({"chartType": "vbar", "height": 4, "labels": ["x", "y"], "series": [{"values": [10, 10]}]})
    assert "▓" not in out


def test_multi_series_cell_line_distinct_without_color():
    out = render_chart({"chartType": "line", "height": 4, "series": [
        {"name": "A", "values": [1, 2, 1, 2]}, {"name": "B", "values": [2, 1, 2, 1]}]})
    assert "█" in body_of(out) and "▓" in body_of(out)


def test_braille_multi_series_legend_does_not_claim_shape_without_color():
    out = render_chart({"chartType": "line", "mode": "braille", "height": 4, "series": [
        {"name": "A", "values": [1, 2, 1, 2]}, {"name": "B", "values": [2, 1, 2, 1]}]})
    assert "can't be told apart" in out


def test_braille_multi_series_with_color_keeps_swatch_legend():
    out = render_chart({"chartType": "line", "mode": "braille", "useColor": "on", "height": 4, "series": [
        {"name": "A", "values": [1, 2, 1, 2]}, {"name": "B", "values": [2, 1, 2, 1]}]})
    assert "can't be told apart" not in out and "\x1b[38;5;" in out


def rows(out):
    return out.split("\n")


def test_stacked_vbar_with_negatives_grows_both_ways():
    out = render_chart({"chartType": "vbar", "stacked": True, "height": 8, "border": "none", "labels": ["a", "b"],
                        "series": [{"name": "up", "values": [10, 10]}, {"name": "down", "values": [-10, -5]}]})
    grid = rows(out)[:8]
    # first series stays above the baseline, second below it, in every column
    assert all("█" in r for r in grid[:4]) and all("▓" in r for r in grid[4:])
    assert rows(out)[8].strip() == "a b"


def test_stacked_hbar_with_negatives_puts_net_total_at_row_end():
    out = render_chart({"chartType": "hbar", "stacked": True, "width": 20, "border": "none", "labels": ["a"],
                        "series": [{"name": "p", "values": [10]}, {"name": "n", "values": [-10]}]})
    line = rows(out)[0]
    assert line.startswith("a │ ") and line.endswith(" 0")
    bar = line[4:-2]
    assert bar.index("▓") < bar.index("█")  # negative side is left of the zero column


def test_stacked_area_with_negatives_labels_span_both_signs():
    out = render_chart({"chartType": "area", "stacked": True, "height": 6, "width": 20, "border": "none", "series": [
        {"values": [1, 2, 3]}, {"values": [-1, -2, -3]}]})
    first, last = rows(out)[0], rows(out)[5]
    assert first.split("┤")[0].strip() == "3" and last.split("┤")[0].strip() == "-3"


@pytest.mark.parametrize("chart_type", ["vbar", "hbar", "area"])
def test_stacked_negative_never_crashes(chart_type):
    # the Go implementation panicked on this (negative strings.Repeat count)
    render_chart({"chartType": chart_type, "stacked": True, "labels": ["a", "b", "c"], "series": [
        {"values": [58, 1, 2]}, {"values": [-46, -3, 5]}]})


def test_all_negative_stacked_still_draws():
    out = render_chart({"chartType": "vbar", "stacked": True, "height": 4, "border": "none", "labels": ["a"],
                        "series": [{"values": [-3]}, {"values": [-2]}]})
    assert "█" in out and "▓" in out


def test_non_negative_stacked_is_unchanged_by_the_negative_support():
    out = render_chart({"chartType": "vbar", "stacked": True, "height": 4, "border": "none", "labels": ["a"],
                        "series": [{"values": [1]}, {"values": [1]}]})
    assert rows(out)[:4] == ["▓", "▓", "█", "█"]


def test_float_rounding_is_half_away_from_zero_like_go():
    # Python's round(2.5) == 2; Go's math.Round(2.5) == 3. Column 0.5 of 5 rows must round up.
    out = render_chart({"chartType": "vbar", "height": 5, "border": "none", "labels": ["a", "b"],
                        "series": [{"values": [1, 0.5]}]})
    assert rows(out)[0:5][2].startswith("█")


# --- validation & limits --------------------------------------------------

@pytest.mark.parametrize("spec,fragment", [
    ({"chartType": "line", "series": []}, "at least one entry"),
    ({"chartType": "nope", "series": [{"values": [1]}]}, 'unknown chartType "nope"'),
    ({"chartType": "vbar", "border": "wavy", "series": [{"values": [1]}]}, 'invalid border "wavy"'),
    ({"chartType": "line", "mode": "x", "series": [{"values": [1, 2]}]}, 'invalid mode "x"'),
    ({"chartType": "line", "style": "x", "series": [{"values": [1, 2]}]}, 'invalid style "x"'),
    ({"chartType": "line", "useColor": "x", "series": [{"values": [1, 2]}]}, 'invalid useColor "x"'),
    ({"chartType": "line", "series": [{"values": [1]}]}, "at least two values"),
    ({"chartType": "dual_axis", "series": [{"values": [1, 2]}]}, "exactly two series"),
    ({"chartType": "histogram", "series": [{"values": [1]}, {"values": [2]}]}, "exactly one series"),
    ({"chartType": "vbar", "series": [{"values": [1, 2]}, {"values": [1]}]}, "same number of values"),
    ({"chartType": "vbar", "labels": ["a"], "series": [{"values": [1, 2]}]}, "labels length"),
    ({"chartType": "pie", "series": [{"values": [0]}]}, "sum to more than zero"),
    ({"chartType": "pie", "series": [{"values": [-1]}, {"values": [3]}]}, "non-negative"),
    ({"chartType": "scatter", "series": [{"values": [1]}]}, "at least one point"),
    ({"chartType": "line", "series": [{"values": [1, float("nan")]}]}, "finite"),
    ({"chartType": "line", "series": [{"values": [1, "2"]}]}, "must be a number"),
    ({"chartType": "line", "series": "nope"}, "series must be an array"),
    ({"chartType": "line", "width": "wide", "series": [{"values": [1, 2]}]}, "width must be an integer"),
    ({"chartType": "line", "width": 100000, "series": [{"values": [1, 2]}]}, "width must be at most"),
    ({"chartType": "line", "height": 10 ** 6, "series": [{"values": [1, 2]}]}, "height must be at most"),
    ({"chartType": "histogram", "bins": 10 ** 6, "series": [{"values": [1, 2]}]}, "bins must be at most"),
    ("not a dict", "JSON object"),
])
def test_invalid_specs_raise_readable_errors(spec, fragment):
    with pytest.raises(ChartError, match=fragment):
        render_chart(spec)


def test_too_much_data_is_rejected():
    with pytest.raises(ChartError, match="too much data"):
        render_chart({"chartType": "sparkline", "series": [{"values": [1.0] * 60_000}]})


def test_max_size_chart_renders_quickly():
    out = render_chart({"chartType": "line", "mode": "braille", "width": 500, "height": 200,
                        "series": [{"values": list(range(1000))}]})
    assert len(out.split("\n")) == 200 + 2  # plus the top and bottom border


# --- alignment ------------------------------------------------------------

def test_framed_charts_are_rectangular():
    """Every line of a bordered chart has the same character count, so a ragged
    right edge on screen is the viewer's font, not the generator."""
    import re
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    checked = 0
    for case in load("corpus.json"):
        spec = case["spec"]
        if "out" not in case or spec.get("border") in ("none",):
            continue
        lines = [ansi.sub("", l) for l in case["out"].split("\n")]
        assert len({len(l) for l in lines}) == 1, case["out"]
        checked += 1
    assert checked > 200


# --- x-axis labels --------------------------------------------------------

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@pytest.mark.parametrize("chart_type", ["line", "area"])
@pytest.mark.parametrize("width", [40, 48, 60, 72])
def test_first_and_last_axis_labels_are_never_clipped(chart_type, width):
    """'Jan' used to render as 'an' and 'Dec' as 'De' at the plot edges."""
    out = render_chart({"chartType": chart_type, "border": "none", "width": width, "height": 4, "labels": MONTHS,
                        "series": [{"values": list(range(1, 13))}]})
    label_row = out.split("\n")[4]
    assert label_row.split()[0] == "Jan" and label_row.split()[-1] == "Dec"
    assert label_row.count("Jan") == 1 and label_row.count("Dec") == 1
    assert len(label_row) <= len(out.split("\n")[0])  # still inside the plot area


def test_axis_labels_keep_their_centering_away_from_the_edges():
    out = render_chart({"chartType": "line", "border": "none", "width": 21, "height": 3, "labels": ["a", "b", "c"],
                        "series": [{"values": [1, 2, 3]}]})
    label_row = out.split("\n")[3]
    assert label_row.index("b") - label_row.index("a") == label_row.index("c") - label_row.index("b")


def test_label_wider_than_the_plot_does_not_crash():
    out = render_chart({"chartType": "line", "border": "none", "width": 3, "height": 3, "labels": ["abcdefgh", "z"],
                        "series": [{"values": [1, 2]}]})
    assert out
