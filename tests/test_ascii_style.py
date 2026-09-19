"""The plain-ASCII per-series glyph ramp (style: "ascii") with many series."""

import re

import pytest

from asciicharts import ASCII_FILLS, AREA_ASCII_FILLS, MAX_LEGEND_WIDTH, render_chart

ORIGINAL = ["#", "X", "H", "W", "=", ":", "|", "."]
REQUESTED = ["%", "@", "\\", "/", "&", "$", "!", "M", "N", "D", "O", "U", "S", "G", "Z"]
N = len(ASCII_FILLS)
LABELS = ["A", "B", "C"]


def many_series(n=N):
    # Each series is large in one category and small in another, so every
    # series is visible somewhere in every layout.
    return [{"name": f"s{i + 1}", "values": [i + 1, n - i, (i * 3) % n + 1]} for i in range(n)]


def test_ramp_has_every_requested_glyph_and_keeps_the_original_eight_first():
    assert ASCII_FILLS[:8] == ORIGINAL
    assert set(REQUESTED) <= set(ASCII_FILLS)
    assert len(ASCII_FILLS) == len(set(ASCII_FILLS)) == 8 + len(REQUESTED)
    assert AREA_ASCII_FILLS[:8] != ORIGINAL  # area keeps its own ordering of the first eight
    assert sorted(AREA_ASCII_FILLS) == sorted(ASCII_FILLS)


def test_every_glyph_is_printable_ascii_and_not_a_space():
    for g in ASCII_FILLS:
        assert len(g) == 1 and 32 < ord(g) < 127


def test_original_eight_series_output_is_unchanged():
    out = render_chart({"chartType": "hbar", "style": "ascii", "border": "none", "labels": ["A"],
                        "series": [{"name": f"s{i}", "values": [i + 1]} for i in range(8)]})
    fills = [line.split("| ")[1][0] for line in out.split("\n")[1:9]]
    assert fills == ORIGINAL


def bar_glyphs(out):
    """Distinct non-space characters in the bars of hbar output (between '| ' and the value)."""
    found = set()
    for line in out.split("\n"):
        if " | " in line:
            bar = line.split(" | ", 1)[1].rsplit(" ", 1)[0]
            found |= set(bar) - {" "}
    return found


def test_grouped_hbar_gives_each_of_23_series_its_own_glyph():
    out = render_chart({"chartType": "hbar", "style": "ascii", "border": "none", "labels": LABELS,
                        "series": many_series()})
    assert bar_glyphs(out) == set(ASCII_FILLS)
    # and each series row uses exactly its own glyph
    rows = [l for l in out.split("\n") if l.startswith("  s")]
    assert len(rows) == 3 * N
    for i, line in enumerate(rows):
        bar = line.split(" | ", 1)[1].rsplit(" ", 1)[0].strip()
        assert set(bar) == {ASCII_FILLS[i % N]}, line


def test_stacked_hbar_uses_all_glyphs_in_series_order():
    out = render_chart({"chartType": "hbar", "style": "ascii", "border": "none", "stacked": True,
                        "labels": ["A"], "series": [{"name": f"s{i}", "values": [10]} for i in range(N)],
                        "width": 230})
    row = out.split("\n")[0].split(" | ", 1)[1].rsplit(" ", 1)[0]
    # 23 series x 10 = 230 cells: each glyph appears as one run of 10, in ramp order
    assert row == "".join(g * 10 for g in ASCII_FILLS)


def test_grouped_vbar_draws_every_glyph():
    out = render_chart({"chartType": "vbar", "style": "ascii", "border": "none", "labels": LABELS,
                        "height": 24, "series": many_series()})
    grid = "\n".join(out.split("\n")[:24])
    assert set(grid) - {" ", "\n"} == set(ASCII_FILLS)


def test_stacked_vbar_and_area_use_ascii_glyphs_only():
    series = [{"name": f"s{i}", "values": [10, 20, 15]} for i in range(N)]
    vbar = render_chart({"chartType": "vbar", "style": "ascii", "border": "none", "stacked": True,
                         "labels": LABELS, "height": N * 2, "series": series})
    area = render_chart({"chartType": "area", "style": "ascii", "border": "none", "stacked": True,
                         "width": 40, "height": N * 2, "series": series})
    for out, ramp in ((vbar, ASCII_FILLS), (area, AREA_ASCII_FILLS)):
        body = "\n".join(out.split("\n\n")[0].split("\n")[:-1])  # drop the label/axis row
        body = re.sub(r"^.*?[┤+]", "", body, flags=re.M)              # area: drop the axis labels
        assert set(body) - {" ", "\n"} == set(ramp)


def test_area_overlay_with_23_series_draws_all_glyphs():
    series = [{"name": f"s{i}", "values": [i + 1, (N - i) + 1, i + 1]} for i in range(N)]
    out = render_chart({"chartType": "area", "style": "ascii", "border": "none", "width": 40,
                        "height": 30, "series": series})
    body = re.sub(r"^.*?[┤+]", "", out.split("\n\n")[0], flags=re.M)
    assert len(set(body) - {" ", "\n"}) >= 12  # overlays hide later series behind earlier ones


def test_histogram_ascii_uses_first_glyph():
    out = render_chart({"chartType": "histogram", "style": "ascii", "border": "none", "bins": 3,
                        "series": [{"values": [1, 2, 2, 3, 3, 3]}]})
    assert set(bar_glyphs(out)) == {"#"}


def test_with_more_series_than_glyphs_the_ramp_wraps_around():
    n = N + 2
    out = render_chart({"chartType": "hbar", "style": "ascii", "border": "none", "labels": ["A"],
                        "series": [{"name": f"s{i}", "values": [i + 1]} for i in range(n)]})
    rows = [l for l in out.split("\n") if " | " in l]
    assert len(rows) == n
    assert rows[N].split(" | ")[1].strip()[0] == ASCII_FILLS[0]


def test_legend_swatches_match_bar_glyphs_in_order():
    out = render_chart({"chartType": "vbar", "style": "ascii", "border": "none", "labels": LABELS,
                        "series": many_series()})
    legend = out.split("\n\n", 1)[1]
    swatches = re.findall(r"(\S) s\d+", legend)
    assert swatches == ASCII_FILLS


def test_many_series_legend_wraps_instead_of_stretching_the_frame():
    out = render_chart({"chartType": "vbar", "style": "ascii", "border": "ascii", "labels": LABELS,
                        "series": many_series()})
    assert max(len(l) for l in out.split("\n")) <= MAX_LEGEND_WIDTH + 4
    legend = [l for l in out.split("\n") if "s1 " in l or "s23" in l or "s12" in l]
    assert len(legend) >= 2  # wrapped onto several lines
    assert len({len(l) for l in out.split("\n")}) == 1  # frame still rectangular


def test_short_legends_stay_on_one_line():
    out = render_chart({"chartType": "vbar", "border": "none", "labels": ["a"],
                        "series": [{"name": "one", "values": [1]}, {"name": "two", "values": [2]}]})
    assert out.split("\n")[-1] == "█ one   ▓ two"


def specs_for_pure_ascii(border):
    """Every chart that has an ascii style, in several layouts."""
    base = {"style": "ascii", "border": border, "labels": LABELS}
    two = [{"name": "a", "values": [3, 5, 2]}, {"name": "b", "values": [4, 1, 6]}]
    signed = [{"name": "up", "values": [3, 5, 2]}, {"name": "down", "values": [-4, -1, -6]}]
    return {
        "vbar grouped": {**base, "chartType": "vbar", "series": many_series()},
        "vbar stacked+neg": {**base, "chartType": "vbar", "stacked": True, "series": signed},
        "hbar single": {**base, "chartType": "hbar", "series": [{"values": [3, 5, 2]}]},
        "hbar grouped": {**base, "chartType": "hbar", "series": many_series()},
        "hbar stacked": {**base, "chartType": "hbar", "stacked": True, "series": two},
        "hbar stacked+neg": {**base, "chartType": "hbar", "stacked": True, "series": signed},
        "hbar diverging": {**base, "chartType": "hbar", "series": [{"values": [3, -5, 2]}]},
        "histogram": {**base, "chartType": "histogram", "series": [{"values": [1, 2, 2, 3, 3, 3, 9]}]},
        "area overlay": {**base, "chartType": "area", "series": two},
        "area stacked": {**base, "chartType": "area", "stacked": True, "series": two},
        "area stacked+neg": {**base, "chartType": "area", "stacked": True, "series": signed},
        "line": {**base, "chartType": "line", "series": [{"values": [1, 4, 2, 6]}]},
        "line multi": {**base, "chartType": "line", "series": two},
        "line points+threshold": {**base, "chartType": "line", "showPoints": True, "threshold": 3, "series": two},
    }


@pytest.mark.parametrize("border", ["none", "ascii"])
def test_ascii_style_is_pure_ascii_for_every_chart_that_has_it(border):
    """style "ascii" promises output that renders identically in any font: no box-drawing
    separators or axis ticks either (the plain "│" and "┤" used to slip through)."""
    for name, spec in specs_for_pure_ascii(border).items():
        out = render_chart(spec)
        offenders = sorted({c for c in out if ord(c) >= 128})
        assert not offenders, f"{name}: non-ASCII characters {offenders}\n{out}"


def test_ascii_style_line_uses_distinct_ascii_glyphs_per_series_and_ascii_markers():
    two = [{"name": "a", "values": [1, 4, 2, 6]}, {"name": "b", "values": [6, 2, 5, 1]}]
    out = render_chart({"chartType": "line", "style": "ascii", "border": "none", "height": 8, "series": two})
    body, legend = out.split("\n\n")
    assert "#" in body and "X" in body and "# a   X b" == legend
    out = render_chart({"chartType": "line", "style": "ascii", "border": "none", "showPoints": True, "series": two})
    assert "o" in out and "x" in out and "o a   x b" in out


def test_line_axis_tick_is_plus_in_ascii_style_and_a_box_glyph_otherwise():
    spec = {"chartType": "line", "border": "none", "height": 3, "width": 10, "series": [{"values": [1, 2, 3]}]}
    assert " ┤" in render_chart(spec) and " +" in render_chart({**spec, "style": "ascii"})


def test_non_ascii_styles_keep_their_box_drawing_separators():
    spec = {"chartType": "hbar", "border": "none", "labels": ["a"], "series": [{"values": [1]}]}
    assert " │ " in render_chart(spec) and " │ " in render_chart({**spec, "style": "halftone"})
    assert " | " in render_chart({**spec, "style": "ascii"})


def test_color_keeps_ascii_glyphs():
    out = render_chart({"chartType": "hbar", "style": "ascii", "border": "none", "useColor": "on",
                        "labels": LABELS, "series": many_series()[:9]})
    assert "\x1b[38;5;" in out and "@" in out
