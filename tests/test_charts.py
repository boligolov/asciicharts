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


def rows(out):
    return out.split("\n")


def test_stacked_vbar_with_negatives_grows_both_ways():
    out = render_chart({"chartType": "vbar", "width": 1, "stacked": True, "height": 8, "border": "none", "labels": ["a", "b"],
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
    out = render_chart({"chartType": "vbar", "width": 1, "stacked": True, "height": 4, "border": "none", "labels": ["a"],
                        "series": [{"values": [1]}, {"values": [1]}]})
    assert rows(out)[:4] == ["▓", "▓", "█", "█"]


def test_heatmap_width_widens_cells_to_fill_the_grid():
    spec = {"chartType": "heatmap", "border": "none", "labels": ["Mon", "Tue"],
            "series": [{"name": "am", "values": [0, 10]}]}
    narrow = [r.rstrip() for r in rows(render_chart({**spec, "width": 7}))]
    assert narrow == ["   Mon Tue", "am ░░░ ███"]
    wide = [r.rstrip() for r in rows(render_chart({**spec, "width": 21}))]
    assert wide == ["      Mon        Tue", "am ░░░░░░░░░░ ██████████"]
    # never narrower than a 3-character cell, however small width is
    assert render_chart({**spec, "width": 2}) == render_chart({**spec, "width": 7})


def test_levels_are_equal_buckets_and_blank_is_never_a_value():
    """Heatmap shades and sparkline ticks split the range into equal buckets: the lowest value is
    visible (never blank, which would read as "no data") and the top level covers the top bucket,
    not the maximum alone."""
    heat = render_chart({"chartType": "heatmap", "border": "none", "labels": list("abcde"), "width": 19,
                         "series": [{"name": "r", "values": [0, 24, 26, 76, 100]}]})
    assert rows(heat)[1].split() == ["r", "░░░", "░░░", "▒▒▒", "███", "███"]
    flat = render_chart({"chartType": "heatmap", "border": "none", "series": [{"name": "r", "values": [7, 7]}]})
    assert "░" in flat
    spark = render_chart({"chartType": "sparkline", "border": "none", "series": [{"values": [0, 90, 100]}]})
    assert spark == "▁██"


def test_charts_without_width_fill_the_default_plot_width():
    heat = {"chartType": "heatmap", "border": "none", "labels": ["a", "b", "c"],
            "series": [{"name": "r", "values": [1, 2, 3]}]}
    assert render_chart(heat) == render_chart({**heat, "width": 60})
    bars = {"chartType": "vbar", "border": "none", "labels": ["a", "b"], "series": [{"values": [1, 2]}]}
    assert render_chart(bars) == render_chart({**bars, "width": 60})
    assert 58 <= max(len(r) for r in rows(render_chart(bars))) <= 60  # two bars and a gap share 60


def test_thresholds_are_dashed_and_named_right_of_the_plot():
    out = render_chart({"chartType": "line", "border": "none", "height": 5, "width": 10,
                        "thresholds": [{"value": 10, "label": "target"}, 0],
                        "series": [{"values": [2, 4, 6]}]})
    r = rows(out)
    # the scale stretches to take in both lines: 10 is the top row, 0 the bottom one
    assert r[0].lstrip().startswith("10 ┤- - - - - ") and r[0].endswith("  target: 10")
    assert r[4].lstrip().startswith("0 ┤- - - - - ") and r[4].endswith("  0")
    assert "threshold" not in out  # no footnote: every line is named on its own row


def test_thresholds_on_the_same_row_share_it():
    out = render_chart({"chartType": "line", "border": "none", "height": 3,
                        "thresholds": [{"value": 5, "label": "a"}, {"value": 5.01, "label": "b"}],
                        "series": [{"values": [0, 5]}]})
    assert rows(out)[0].endswith("  a: 5, b: 5.01")


def test_threshold_and_thresholds_combine():
    out = render_chart({"chartType": "line", "border": "none", "height": 4, "threshold": 1,
                        "thresholds": [{"value": 9, "label": "cap"}], "series": [{"values": [3, 5]}]})
    assert rows(out)[0].endswith("  cap: 9") and rows(out)[-1] == "- - threshold: 1"


def test_control_characters_in_text_become_spaces():
    out = render_chart({"chartType": "hbar", "title": "a\nb\x1b[2J", "labels": ["x\ty", "z"],
                        "series": [{"name": "s\r", "values": [1, 2]}]})
    assert "\x1b" not in out and "\t" not in out and "\r" not in out
    r = rows(out)
    assert len(r) == 6 and "a b [2J" in r[1] and r[3].startswith("│ x y │")
    assert len({len(line) for line in r}) == 1  # still a rectangle


def test_magnitude_limit_leaves_room_for_every_chart_type():
    """1e15 is accepted everywhere and never crashes the scale — the limit sits below where it breaks."""
    for chart in CHART_TYPES:
        spec = {"chartType": chart, "labels": ["a", "b"], "bins": 2,
                "series": [{"name": "s", "values": [1e15, 1e15 - 1],
                            "points": [{"x": -1e15, "y": 1e15}, {"x": 1e15, "y": -1e15}]},
                           {"name": "t", "values": [-1e15, 5], "points": [{"x": 0, "y": 0}]}]}
        if chart == "pie":
            spec["series"] = [{"name": "a", "values": [1e15]}, {"name": "b", "values": [1]}]
        for stacked in (False, True):
            try:
                render_chart({**spec, "stacked": stacked})
            except ChartError as e:  # a shape rule of that chart (e.g. histogram: one series), not the limit
                assert "magnitude" not in str(e)


def display_width(line):
    """Terminal columns, computed independently of the renderer: CJK and most emoji take two,
    combining accents and format characters none."""
    import unicodedata
    return sum(0 if unicodedata.combining(c) or unicodedata.category(c) in ("Mn", "Me", "Cf")
               else 2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in line)


WIDE_TEXT = ["東京", "🍕 pizza", "e\u0301te\u0301", "plain"]


@pytest.mark.parametrize("chart", CHART_TYPES)
@pytest.mark.parametrize("use_color", ["off", "on"])
def test_wide_and_combining_characters_keep_the_frame_rectangular(chart, use_color):
    import re
    spec = {"chartType": chart, "useColor": use_color, "title": "売上 🔥 résumé", "labels": WIDE_TEXT, "bins": 3,
            "showPoints": True, "thresholds": [{"value": 3, "label": "目標 🎯"}],
            "series": [{"name": WIDE_TEXT[i], "values": [1 + i, 4, 2, 5], "points": [{"x": 1, "y": 2}, {"x": 3, "y": 1}]}
                       for i in range(2)]}
    if chart == "histogram":
        spec["series"] = spec["series"][:1]
    if chart == "pie":
        spec["series"] = [{"name": t, "values": [i + 1]} for i, t in enumerate(WIDE_TEXT)]
    plain = re.sub(r"\x1b\[[0-9;]*m", "", render_chart(spec))
    assert len({display_width(line) for line in plain.split("\n")}) == 1


def test_a_wide_character_is_never_cut_in_half():
    out = render_chart({"chartType": "heatmap", "border": "none", "width": 18, "labels": ["月曜日", "火", "水"],
                        "series": [{"name": "朝", "values": [1, 2, 3]}]})
    header = rows(out)[0]
    assert "月曜 " in header and "月曜日" not in header  # 6 columns into a 5-column cell: the third glyph drops whole


def test_pointchar_must_be_one_column_wide():
    spec = {"chartType": "line", "showPoints": True, "series": [{"values": [1, 2]}]}
    with pytest.raises(ChartError, match="pointChar must be a single-width character"):
        render_chart({**spec, "pointChar": "🔴"})
    assert "x" in render_chart({**spec, "pointChar": "x"})


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
    ({"chartType": "line", "style": "x", "series": [{"values": [1, 2]}]}, 'invalid style "x"'),
    ({"chartType": "line", "useColor": "x", "series": [{"values": [1, 2]}]}, 'invalid useColor "x"'),
    ({"chartType": "line", "series": [{"values": [1]}]}, "at least two values"),
    ({"chartType": "line", "thresholds": 5, "series": [{"values": [1, 2]}]}, "thresholds must be an array"),
    ({"chartType": "line", "series": [{"values": [1e308, -1e308]}]}, "value must be at most 1e15 in magnitude, got 1e"),
    ({"chartType": "scatter", "series": [{"points": [{"x": 2e15, "y": 1}]}]}, "point x must be at most 1e15"),
    ({"chartType": "line", "threshold": -1e16, "series": [{"values": [1, 2]}]}, "threshold must be at most 1e15"),
    ({"chartType": "line", "title": "x" * 201, "series": [{"values": [1, 2]}]}, "title must be at most 200 characters, got 201"),
    ({"chartType": "hbar", "labels": ["ok", "y" * 201], "series": [{"values": [1, 2]}]}, "labels 1 must be at most 200"),
    ({"chartType": "hbar", "series": [{"name": "n" * 201, "values": [1]}]}, "name must be at most 200"),
    ({"chartType": "line", "thresholds": [{"label": "x"}], "series": [{"values": [1, 2]}]},
     "thresholds 0 value must be a number"),
    ({"chartType": "line", "thresholds": [{"value": 1, "label": "x" * 41}], "series": [{"values": [1, 2]}]},
     "label must be at most 40 characters"),
    ({"chartType": "line", "thresholds": list(range(21)), "series": [{"values": [1, 2]}]},
     "thresholds must have at most 20 entries"),
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
    out = render_chart({"chartType": "line", "width": 500, "height": 200,
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


# --- whole-block bars ------------------------------------------------------

FRACTIONAL_BLOCKS = "▏▎▍▋▊▉▁▂▃▅▆▇"  # eighth blocks: missing from Consolas / Courier New / Lucida Console


def bar_specs(style=None):
    extra = {"style": style} if style else {}
    return {
        "hbar": {"chartType": "hbar", "border": "none", "labels": ["a", "b", "c", "d"], "series": [{"values": [62, 21, 12, 5]}], **extra},
        "hbar grouped": {"chartType": "hbar", "border": "none", "labels": ["a", "b"], "series": [{"name": "x", "values": [62, 21.7]}, {"name": "y", "values": [12.3, 5]}], **extra},
        "vbar": {"chartType": "vbar", "border": "none", "height": 7, "labels": ["a", "b", "c", "d"], "series": [{"values": [62, 21, 12, 5]}], **extra},
        "vbar grouped": {"chartType": "vbar", "border": "none", "height": 7, "labels": ["a", "b"], "series": [{"name": "x", "values": [62, 21.7]}, {"name": "y", "values": [12.3, 5]}], **extra},
        "histogram": {"chartType": "histogram", "border": "none", "bins": 6, "series": [{"values": [12, 15, 14, 18, 20, 22, 21, 25, 30, 28, 35, 40, 55, 60, 18, 19, 22]}], **extra},
    }


@pytest.mark.parametrize("name", list(bar_specs()))
def test_default_bars_end_on_whole_blocks(name):
    out = render_chart(bar_specs()[name])
    assert not [c for c in out if c in FRACTIONAL_BLOCKS], out


# vbar with several series is drawn with a different fill glyph per series (█ ▓ ▒ ░), which has no
# fractional variants, so "fine" only changes single-series vbar; every other bar chart honours it.
@pytest.mark.parametrize("name", [n for n in bar_specs() if n != "vbar grouped"])
def test_fine_style_keeps_eighth_block_precision(name):
    out = render_chart(bar_specs("fine")[name])
    assert [c for c in out if c in FRACTIONAL_BLOCKS], name
    assert render_chart(bar_specs("fine")[name]) != render_chart(bar_specs()[name])


def test_whole_block_lengths_are_rounded_not_truncated():
    # 21/62*40 = 13.55 -> 14 cells; 12/62*40 = 7.74 -> 8; 5/62*40 = 3.2 -> 3
    lines = render_chart(bar_specs()["hbar"]).split("\n")
    assert [l.split(" │ ")[1].count("█") for l in lines] == [40, 14, 8, 3]


def test_a_nonzero_value_never_disappears_but_zero_stays_empty():
    out = render_chart({"chartType": "hbar", "border": "none", "labels": ["big", "tiny", "zero"],
                        "series": [{"values": [1000, 0.4, 0]}]})
    big, tiny, zero = out.split("\n")
    assert big.count("█") == 40 and tiny.count("█") == 1 and zero.count("█") == 0
    out = render_chart({"chartType": "vbar", "width": 1, "border": "none", "height": 5, "labels": ["a", "b", "c"],
                        "series": [{"values": [1000, 0.4, 0]}]})
    rows = out.split("\n")[:5]
    assert [sum(r[i] == "█" for r in rows) for i in (0, 2, 4)] == [5, 1, 0]


def test_style_fine_is_accepted_and_ignored_by_charts_without_bars():
    spec = {"chartType": "line", "border": "none", "series": [{"values": [1, 3, 2]}]}
    assert render_chart({**spec, "style": "fine"}) == render_chart(spec)


# --- background track (the unused part of a bar, up to the chart's own scale) --------------

def test_track_fills_the_space_after_a_short_bar():
    out = render_chart({"chartType": "hbar", "border": "none", "labels": ["a", "b"], "series": [{"values": [10, 4]}]})
    full, short = out.split("\n")
    assert full == "a │ ████████████████████████████████████████ 10"
    assert short == "b │ ████████████████░░░░░░░░░░░░░░░░░░░░░░░░ 4"
    out = render_chart({"chartType": "vbar", "width": 1, "border": "none", "height": 5, "labels": ["a", "b"], "series": [{"values": [10, 4]}]})
    rows = out.split("\n")[:5]
    assert [r[0] for r in rows] == ["█", "█", "█", "█", "█"]  # full column: no track needed
    assert [r[2] for r in rows] == ["░", "░", "░", "█", "█"]  # short column: track above the bar


def test_track_covers_the_whole_bar_for_a_zero_value():
    out = render_chart({"chartType": "hbar", "border": "none", "labels": ["nonzero", "zero"], "series": [{"values": [5, 0]}]})
    zero_line = out.split("\n")[1]
    assert "█" not in zero_line and zero_line.count("░") == 40


def test_track_is_absent_for_stacked_diverging_halftone_and_histogram():
    common = {"border": "none", "labels": ["a", "b"], "series": [{"values": [10, 4]}]}
    assert "░" not in render_chart({**common, "chartType": "hbar", "stacked": True,
                                    "series": [{"values": [10, 4]}, {"values": [3, 1]}]})
    assert "░" not in render_chart({"chartType": "hbar", "border": "none", "labels": ["a", "b"],
                                    "series": [{"values": [-10, 4]}]})
    # halftone already tiles "░" as one of its own series shades, but a lone series' unused space
    # must stay blank, not additionally shaded — there is no light-vs-track distinction to make.
    out = render_chart({**common, "chartType": "hbar", "style": "halftone"})
    assert out.split("\n")[1].endswith(" " * 24 + " 4")
    assert "░" not in render_chart({"chartType": "histogram", "border": "none", "bins": 3,
                                    "series": [{"values": [1, 2, 2, 3, 3, 3, 9]}]})


def test_ascii_style_gets_its_own_comma_track_never_the_unicode_shade():
    """style "ascii" gets a track too, but drawn with ',' (ASCII_TRACK_FILL) — a stray, low-ink
    mark that plain-ASCII output can render — instead of the Unicode '░' every other style uses."""
    out = render_chart({"chartType": "hbar", "border": "none", "labels": ["a", "b"], "style": "ascii",
                        "series": [{"values": [10, 4]}]})
    assert out == "a | ######################################## 10\nb | ################,,,,,,,,,,,,,,,,,,,,,,,, 4"
    out = render_chart({"chartType": "vbar", "width": 1, "border": "none", "height": 5, "labels": ["a", "b"], "style": "ascii",
                        "series": [{"values": [10, 4]}]})
    rows = out.split("\n")[:5]
    assert [r[0] for r in rows] == ["#", "#", "#", "#", "#"]  # full column: no track needed
    assert [r[2] for r in rows] == [",", ",", ",", "#", "#"]  # short column: track above the bar


def test_track_never_reuses_a_bars_own_fill_glyph():
    """Grouped vbar's 4th series is drawn in FILLS[3], which is the track glyph itself (░) — the
    track must fall back to a different shade there so the bar's own end is still visible."""
    out = render_chart({"chartType": "vbar", "width": 1, "border": "none", "height": 8, "labels": ["a"],
                        "series": [{"name": f"s{i}", "values": [v]} for i, v in enumerate([10, 10, 10, 4])]})
    rows = out.split("\n")[:8]
    fourth_col = [r[3] for r in rows]
    assert fourth_col[:5] == ["▒"] * 5 and fourth_col[5:] == ["░"] * 3  # ▒ track above, ░ own bar below


def test_track_glyph_is_font_safe():
    import asciicharts
    assert asciicharts.TRACK_FILL in SAFE_FILLS and asciicharts.TRACK_FILL_ALT in SAFE_FILLS
    assert asciicharts.ASCII_TRACK_FILL not in set(asciicharts.ASCII_FILLS) | set(asciicharts.ASCII_MARKERS)
    assert ord(asciicharts.ASCII_TRACK_FILL) < 128  # plain ASCII, like every other ascii-style glyph


# --- glyphs that survive default fonts ---------------------------------------
# Verified against the character maps of Consolas and Courier New (the default monospace fonts of many
# Windows editors). A glyph a font lacks is drawn from another font with a different width, which makes the
# right edge of an otherwise rectangular chart ragged.
SAFE_FILLS = set("█▓▒░▌▄▐▀")
SAFE_MARKERS = set("●○▲■□▼♦◊►◄")


def test_fill_and_marker_tables_only_contain_font_safe_glyphs():
    import asciicharts
    assert set(asciicharts.FILLS) <= SAFE_FILLS and len(set(asciicharts.FILLS)) == len(asciicharts.FILLS) >= 6
    assert set(asciicharts.HALFTONE_FILLS) <= SAFE_FILLS | {":"} and len(set(asciicharts.HALFTONE_FILLS)) >= 6
    assert set(asciicharts.MARKERS) <= SAFE_MARKERS and len(set(asciicharts.MARKERS)) >= 6


def test_default_output_uses_only_font_safe_glyphs():
    """Across the whole golden corpus, everything except sparklines and style "fine" (both use eighth
    blocks, documented as needing a capable font) stays inside ASCII, Latin-1, box drawing and the safe sets."""
    checked = 0
    for case in load("corpus.json"):
        spec = case["spec"]
        if "out" not in case or spec["chartType"] == "sparkline" or spec.get("style") == "fine":
            continue
        for ch in set(case["out"]):
            ok = ord(ch) < 0x100 or "─" <= ch <= "╿" or ch in SAFE_FILLS or ch in SAFE_MARKERS
            assert ok, f"{ch!r} (U+{ord(ch):04X}) in the output of {spec}"
        checked += 1
    assert checked > 200


def test_series_glyphs_stay_distinct_for_up_to_eight_series():
    from asciicharts import FILLS
    out = render_chart({"chartType": "hbar", "border": "none", "stacked": True, "width": 80, "labels": ["a"],
                        "series": [{"name": f"s{i}", "values": [10]} for i in range(8)]})
    row = out.split("\n")[0].split(" │ ")[1].rsplit(" ", 1)[0]
    assert row == "".join(g * 10 for g in FILLS[:8])
