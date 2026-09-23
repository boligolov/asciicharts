#!/usr/bin/env python3
"""asciicharts — render numeric data as ASCII/Unicode text charts.

A single-file, standard-library-only chart renderer. It is the engine behind
the MCP server in server/ and can be copied and used on its own.

Library use::

    from asciicharts import render_chart
    print(render_chart({
        "chartType": "hbar",
        "title": "Browser share",
        "labels": ["Chrome", "Firefox", "Safari"],
        "series": [{"values": [62, 21, 12]}],
    }))

Command line (JSON spec from a file, stdin, or --json)::

    python asciicharts.py spec.json
    echo '{"chartType":"sparkline","series":[{"values":[1,3,2]}]}' | python asciicharts.py -
    python asciicharts.py --json '{"chartType":"sparkline","series":[{"values":[1,3,2]}]}'
    python asciicharts.py --list         # every chart type, how to fill `series`, an example
    python asciicharts.py --csv data.csv --chart hbar --sort -latency --limit 10 --set title="Slowest"
                                         # straight from a CSV; see --csv --help
    python asciicharts.py --csv data.excsv --chart-name top_categories
                                         # an ExCSV file's own #chart suggestion, by name
                                         # (https://github.com/boligolov/excsv)

Spec fields (identical to the MCP tool): chartType, series, labels, title,
width, height, border, style, stacked, bins, useColor, threshold,
thresholds, showPoints, pointChar. See skills/asciicharts/SKILL.md and its references/reference.md.
"""

from __future__ import annotations

import argparse
import copy
import csv
import functools
import io
import json
import math
import re
import sys
import unicodedata

__version__ = "1.0.0"
__all__ = ["render_chart", "list_charts", "spec_from_csv", "ChartError", "CHART_TYPES", "CHARTS", "__version__",
           "parse_excsv", "resolve_excsv_chart", "spec_from_excsv", "list_excsv_charts"]

# The catalogue of chart types: what each draws, how to fill `series`, which
# options matter, and a minimal spec that renders. It is the single source of
# truth for CHART_TYPES, for `--list` and for the MCP `list_charts` tool, and a
# test renders every `example`, so it can't drift from the renderers.
# Options every chart accepts (not repeated below): title, border, useColor.
CHARTS = {
    "sparkline": {
        "summary": "One-line trend made of block glyphs, no axes. Good inline in a sentence or log line.",
        "series": "One line per series. values: the samples in order. name (optional) is printed as a prefix.",
        "options": [],
        "example": {"chartType": "sparkline", "series": [{"name": "latency", "values": [4, 6, 5, 9, 3]}]},
    },
    "vbar": {
        "summary": "Vertical bars: single, grouped or stacked. Negative values diverge from a zero baseline (stacked too).",
        "series": "values: one number per entry of labels. Several series are grouped side by side (or stacked). name is the legend entry.",
        "options": ["labels", "width", "height", "stacked", "style"],
        "example": {"chartType": "vbar", "labels": ["Q1", "Q2", "Q3"],
                    "series": [{"name": "2025", "values": [30, 45, 40]}, {"name": "2026", "values": [35, 50, 55]}]},
    },
    "hbar": {
        "summary": "Horizontal bars: single, grouped or stacked. The best choice for rankings and long labels. Negative values diverge.",
        "series": "values: one number per entry of labels. Several series are grouped (or stacked). name is the legend entry.",
        "options": ["labels", "width", "stacked", "style"],
        "example": {"chartType": "hbar", "labels": ["Chrome", "Firefox", "Safari"], "series": [{"values": [62, 21, 12]}]},
    },
    "line": {
        "summary": "One or more lines with a value axis. Optional dashed reference lines (threshold, or several labelled thresholds) and per-point markers.",
        "series": "values: the samples in order (at least 2 per series). One line per series. labels (optional) become x-axis labels.",
        "options": ["labels", "width", "height", "style", "threshold", "thresholds", "showPoints", "pointChar"],
        "example": {"chartType": "line", "series": [{"values": [12, 18, 15, 30, 42, 38]}]},
    },
    "area": {
        "summary": "Line series filled down to a zero baseline: overlaid or stacked. Negative values fill downward.",
        "series": "values: the samples in order (at least 2 per series, all the same length). One band per series. labels (optional) become x-axis labels.",
        "options": ["labels", "width", "height", "stacked", "style"],
        "example": {"chartType": "area", "series": [{"values": [20, 10, -20, -60, -120]}]},
    },
    "scatter": {
        "summary": "(x, y) points only, one marker shape per series.",
        "series": "points: a list of {x, y} objects (values is not used). One marker set per series.",
        "options": ["width", "height"],
        "example": {"chartType": "scatter",
                    "series": [{"name": "A", "points": [{"x": 1, "y": 2}, {"x": 2, "y": 4}, {"x": 3, "y": 3}]}]},
    },
    "dual_axis": {
        "summary": "Two lines over one x-axis, each with its own y-axis (left and right) for series on different scales.",
        "series": "Exactly two series, each with values (at least 2). The first uses the left axis, the second the right.",
        "options": ["width", "height"],
        "example": {"chartType": "dual_axis", "series": [{"name": "Temp", "values": [10, 12, 15, 14]},
                                                         {"name": "Humidity", "values": [80, 78, 65, 70]}]},
    },
    "pie": {
        "summary": "Circular pie with a legend showing each slice's value and percentage.",
        "series": "One series per slice: name is the slice label, values[0] its size (non-negative, not all zero).",
        "options": ["width", "height"],
        "example": {"chartType": "pie", "series": [{"name": "Chrome", "values": [62]}, {"name": "Firefox", "values": [21]},
                                                   {"name": "Other", "values": [17]}]},
    },
    "histogram": {
        "summary": "Buckets raw samples into bins and draws the counts as horizontal bars.",
        "series": "Exactly one series whose values are the raw samples (do not pre-bucket them).",
        "options": ["bins", "width", "style"],
        "example": {"chartType": "histogram", "bins": 5, "series": [{"values": [12, 15, 14, 18, 20, 22, 21, 25, 30, 28]}]},
    },
    "heatmap": {
        "summary": "A 2-D matrix as shaded cells (or a blue-to-red color ramp with useColor).",
        "series": "One series per matrix row: name is the row label, values the cells. labels are the column headers.",
        "options": ["labels", "width"],
        "example": {"chartType": "heatmap", "labels": ["Mon", "Tue", "Wed"],
                    "series": [{"name": "9am", "values": [20, 35, 25]}, {"name": "5pm", "values": [80, 70, 90]}]},
    },
    "boxplot": {
        "summary": "Box-and-whisker per group (min, Q1, median, Q3, max), computed for you from the raw samples.",
        "series": "One series per group: name is the group label, values are the raw samples (not quartiles).",
        "options": ["width"],
        "example": {"chartType": "boxplot", "series": [{"name": "Class A", "values": [55, 60, 62, 65, 70, 72, 75, 80]}]},
    },
    "dotplot": {
        "summary": "Cleveland dot plot: one row per category with a marker per series on a shared, zoomed value axis (does not start at 0).",
        "series": "values: one number per entry of labels. Several series put one marker each on the same row. name is the legend entry.",
        "options": ["labels", "width"],
        "example": {"chartType": "dotplot", "labels": ["Oakland", "Seattle", "Denver"], "series": [{"values": [5.2, 4.4, 3.6]}]},
    },
}
CHART_TYPES = tuple(CHARTS)


def list_charts() -> list:
    """The catalogue as a list of dicts: type, summary, series, options, example.

    The result is a deep copy, so callers may modify it freely."""
    return copy.deepcopy([{"type": name, **info} for name, info in CHARTS.items()])


class ChartError(ValueError):
    """Raised for invalid chart specs (readable one-line messages)."""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _round(x: float) -> int:
    """math.Round from Go: half away from zero (Python's round is banker's)."""
    t = math.trunc(x)
    if abs(x - t) >= 0.5:
        t += 1 if x > 0 else -1
    return int(t)


def _fmt(v: float) -> str:
    """formatValue: integers without decimals, everything else with two."""
    if abs(v - math.trunc(v)) < 1e-9:
        return format(v, ".0f")
    return format(v, ".2f")


def _sum(xs) -> float:
    """Left-to-right float sum, like Go (3.12's sum() is compensated and can differ by 1ulp)."""
    t = 0.0
    for x in xs:
        t += x
    return t


def _q(s) -> str:
    """Go's %q for the error messages: double-quoted string."""
    return json.dumps(str(s), ensure_ascii=False)


def _clamp(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v


@functools.lru_cache(maxsize=4096)  # charts reuse a handful of glyphs over and over
def _char_width(ch: str) -> int:
    """Terminal columns one code point takes: 2 for East Asian wide/fullwidth (CJK, most emoji),
    0 for combining marks and invisible format characters (accents, ZWJ, variation selectors)."""
    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def _cells(s: str) -> list:
    """s split into terminal columns: a wide character is followed by an empty "" cell (its
    right half), a zero-width one joins the column before it. "".join(_cells(s)) == s, and
    len(_cells(s)) is the width s takes on screen."""
    if s.isascii():
        return list(s)
    out = []
    for ch in s:
        w = _char_width(ch)
        if w == 0 and out:
            out[-2 if out[-1] == "" else -1] += ch
        elif w == 2:
            out += [ch, ""]
        else:
            out.append(ch)
    return out


def _width(s: str) -> int:
    """len(_cells(s)), without building the list: this runs on every line of every frame."""
    if s.isascii():
        return len(s)
    lead = 1 if _char_width(s[0]) == 0 else 0  # a leading zero-width character gets a column of its own
    return sum(map(_char_width, s)) + lead


def _pad(s: str, width: int) -> str:
    """s left-aligned in width columns."""
    return s + " " * (width - _width(s))


def _truncate(s: str, n: int) -> str:
    """The first n columns of s; a wide character that would be cut in half becomes a space."""
    if n <= 0:
        return ""
    cells = _cells(s)
    if len(cells) <= n:
        return s
    cut = cells[:n]
    if cells[n] == "":  # the last kept cell is the left half of a wide character
        cut[-1] = " "
    return "".join(cut)


def _pad_center(s: str, width: int) -> str:
    w = _width(s)
    if w >= width:
        return _truncate(s, width)
    left = (width - w) // 2
    return " " * left + s + " " * (width - w - left)


# --------------------------------------------------------------------------
# Glyph tables
# --------------------------------------------------------------------------

EIGHTHS_UP = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
EIGHTHS_LEFT = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
SHADES = [" ", "░", "▒", "▓", "█"]
# Per-series fill glyphs and point markers are limited to characters that the default monospace
# fonts of Windows editors (Consolas, Courier New) actually contain; a glyph a font lacks is drawn
# from another font with a different width and makes the right edge of the chart ragged.
FILLS = ["█", "▓", "▒", "░", "▌", "▄", "▐", "▀"]
HALFTONE_FILLS = ["▓", "▒", "░", "▌", "▄", "▐", "▀", ":"]
# Background "track" for hbar/vbar bars (solid/fine/ascii styles, single-baseline, non-stacked
# only): the unused part of each bar's own cell run, up to the chart's 0..max scale, shaded like a
# progress-bar track — so a short bar's true extent against the full axis is visible instead of just
# fading into blank space. Unicode falls back to the alt (denser) shade on the rare bar whose own
# fill glyph already is the track glyph (grouped vbar's 4th series, from FILLS above), so a bar's end
# is never swallowed by a same-glyph background; ascii's track glyph never collides with a fill (see
# ASCII_TRACK_FILL) so it needs no such fallback.
TRACK_FILL = "░"
TRACK_FILL_ALT = "▒"
# A comma reads as a stray, low-ink mark — the ASCII analogue of the Unicode track's light shading —
# and, unlike every character in ASCII_FILLS/ASCII_MARKERS, is never used to draw a chart itself, so
# a track cell is never mistaken for part of a bar, a series glyph or a point marker.
ASCII_TRACK_FILL = ","


def _track_glyph(bar_ch: str, ascii_style: bool = False) -> str:
    if ascii_style:
        return ASCII_TRACK_FILL
    return TRACK_FILL_ALT if bar_ch == TRACK_FILL else TRACK_FILL


# Per-series glyphs for style "ascii": plain ASCII, so they line up in any font. One sequence
# ordered dense-to-light (heaviest ink first, thinnest strokes last), so neighbouring series stay
# visually distinct at a glance — except '#' leads regardless of its exact rank, since it plays the
# same role ASCII_FILLS[0] does everywhere else: the default single-series solid bar, the ASCII
# analogue of the Unicode '█' (and it is in fact one of the densest of the 23 anyway).
ASCII_FILLS = ["#", "@", "%", "&", "$", "W", "M", "N", "H", "D", "G", "U", "O", "S", "Z", "X", "=", "/", "\\", ":", "|", "!", "."]
# Per-series point markers for style "ascii" on line charts.
ASCII_MARKERS = ["o", "x", "*", "+", "^", "v", "@", "%", "&", "$"]
# Area charts often have thin bands stacked on a much larger first one, so ':' (much lighter than
# '@') reads better as the second glyph there — the same swap ASCII_FILLS makes for the first.
AREA_ASCII_FILLS = ["#", ":", "%", "&", "$", "W", "M", "N", "H", "D", "G", "U", "O", "S", "Z", "X", "=", "/", "\\", "@", "|", "!", "."]
MARKERS = ["●", "○", "▲", "■", "□", "▼", "♦", "◊", "►", "◄"]
PALETTE256 = [39, 208, 40, 201, 51, 226]
THRESHOLD_COLOR = 244
HEAT_RAMP = [21, 27, 33, 39, 45, 51, 87, 123, 159, 195, 226, 220, 214, 208, 202, 196]
HEAT_CELL_WIDTH = 3
SPARK_TICKS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
DUAL_AXIS_GLYPHS = ["█", "▒"]
PIE_ASPECT = 2.0

# --------------------------------------------------------------------------
# Color
# --------------------------------------------------------------------------

def _series_color(i: int) -> int:
    return PALETTE256[i % len(PALETTE256)]


def _colorize(s: str, color: int, enabled: bool) -> str:
    if not enabled or color < 0 or s == "":
        return s
    return f"\x1b[38;5;{color}m{s}\x1b[0m"


# --------------------------------------------------------------------------
# Borders
# --------------------------------------------------------------------------

_ANSI = re.compile("\x1b\\[[0-9;]*m")

# (top-left, top-right, bottom-left, bottom-right, horizontal, vertical, left-T, right-T)
_BORDERS = {
    "ascii": ("+", "+", "+", "+", "-", "|", "+", "+"),
    "light": ("┌", "┐", "└", "┘", "─", "│", "├", "┤"),
    "heavy": ("┏", "┓", "┗", "┛", "━", "┃", "┣", "┫"),
    "double": ("╔", "╗", "╚", "╝", "═", "║", "╠", "╣"),
    "rounded": ("╭", "╮", "╰", "╯", "─", "│", "├", "┤"),
}


def _visible_width(s: str) -> int:
    return _width(_ANSI.sub("", s)) if "\x1b" in s else _width(s)


def _wrap_border(body: str, title: str, style: str) -> str:
    lines = body.split("\n")
    style = style or "light"
    if style == "none":
        return body if title == "" else title + "\n" + body

    tl, tr, bl, br, h, v, lt, rt = _BORDERS.get(style, _BORDERS["light"])
    width = max([_visible_width(title)] + [_visible_width(l) for l in lines])

    out = []

    def rule(left, right):
        out.append(left + h * (width + 2) + right)

    def row(text):
        out.append(v + " " + text + " " * (width - _visible_width(text)) + " " + v)

    rule(tl, tr)
    if title != "":
        pad = width - _visible_width(title)
        lp = pad // 2
        row(" " * lp + title + " " * (pad - lp))
        rule(lt, rt)
    for l in lines:
        row(l)
    rule(bl, br)
    return "\n".join(out)


# --------------------------------------------------------------------------
# Axis / legend helpers
# --------------------------------------------------------------------------

def _x_pixel(i: int, n: int, span: int) -> int:
    if n <= 1 or span <= 1:
        return 0
    return i * (span - 1) // (n - 1)


def _y_pixel(v: float, lo: float, hi: float, span: int) -> int:
    if span <= 1:
        return 0
    if hi == lo:
        return span - 1
    frac = (v - lo) / (hi - lo)
    return _round((1 - frac) * (span - 1))


def _series_min_max(series) -> tuple[float, float]:
    lo, hi = math.inf, -math.inf
    for s in series:
        for v in s["values"]:
            lo = min(lo, v)
            hi = max(hi, v)
    if lo == math.inf:
        return 0.0, 1.0
    if lo == hi:
        hi = lo + 1
    return lo, hi


def _series_max_len(series) -> int:
    return max([0] + [len(s["values"]) for s in series])


def _left_axis_labels(lo: float, hi: float, height: int):
    labels = []
    for row in range(height):
        frac = 1.0
        if height > 1:
            frac = 1 - row / (height - 1)
        labels.append(_fmt(lo + frac * (hi - lo)))
    return labels, max([0] + [len(l) for l in labels])


def _x_axis_labels(labels, n: int, plot_width: int, left_pad: int) -> str:
    if len(labels) != n or n == 0 or plot_width <= 0:
        return ""
    row = [" "] * plot_width
    # Each label is centred under its column, but shifted inward at the edges so
    # the first and last are never cut off ("Jan" must not become "an").
    placed = []
    for i, lbl in enumerate(labels):
        cell = _truncate(lbl, 8)
        start = _clamp(_x_pixel(i, n, plot_width) - _width(cell) // 2, 0, max(plot_width - _width(cell), 0))
        placed.append((start, cell))
    # When labels don't all fit, drop the ones that would touch a neighbour rather
    # than let them run together ("JaFeb"); the first and last always stay.
    keep = [True] + [False] * (n - 2) + [True] if n > 1 else [True]
    end = placed[0][0] + _width(placed[0][1])
    last_start = placed[-1][0]
    for i in range(1, n - 1):
        start, cell = placed[i]
        if start > end and start + _width(cell) < last_start:
            keep[i] = True
            end = start + _width(cell)
    for (start, cell), k in zip(placed, keep):
        if k:
            for j, r in enumerate(_cells(cell)):
                if start + j < plot_width:
                    row[start + j] = r
    return " " * left_pad + "".join(row).rstrip(" ")


def _is_ascii_ramp(ramp) -> bool:
    return ramp is ASCII_FILLS or ramp is AREA_ASCII_FILLS


def _sep(ramp) -> str:
    """The label/bar separator: a plain | in the ascii style, a box-drawing line otherwise."""
    return "|" if _is_ascii_ramp(ramp) else "│"


def _series_label(s, i: int) -> str:
    return s["name"] if s["name"] != "" else f"series {i + 1}"


def _legend_swatch(i: int, color_on: bool, ramp) -> str:
    return _colorize(ramp[i % len(ramp)], _series_color(i), color_on)


# A legend with many series would otherwise be one enormous line that stretches
# the whole frame; past this width it wraps onto more lines.
MAX_LEGEND_WIDTH = 100


def _join_legend(parts) -> str:
    """Join legend entries with three spaces, wrapping at MAX_LEGEND_WIDTH visible columns."""
    lines, cur = [], ""
    for part in parts:
        if cur and _visible_width(cur) + 3 + _visible_width(part) > MAX_LEGEND_WIDTH:
            lines.append(cur)
            cur = part
        else:
            cur = f"{cur}   {part}" if cur else part
    lines.append(cur)
    return "\n".join(lines)


def _named_legend(names, color_on: bool, ramp=FILLS) -> str:
    return _join_legend(f"{_legend_swatch(i, color_on, ramp)} {n}" for i, n in enumerate(names))


# --------------------------------------------------------------------------
# Canvas (line / scatter / dual_axis)
# --------------------------------------------------------------------------

class _Canvas:
    """A grid of characters that line, scatter and dual_axis charts draw onto."""

    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.cell_char = [[""] * width for _ in range(height)]
        self.cell_color = [[-1] * width for _ in range(height)]

    def set_dot(self, px, py, ch, color):
        """Fill one cell with ch (a full block if ch is empty); out-of-range cells are ignored."""
        if px < 0 or py < 0 or px >= self.width or py >= self.height:
            return
        self.cell_char[py][px] = ch or "█"
        if color >= 0:
            self.cell_color[py][px] = color

    def set_marker(self, cx, cy, ch, color):
        if cx < 0 or cy < 0 or cx >= self.width or cy >= self.height:
            return
        self.cell_char[cy][cx] = ch
        if color >= 0:
            self.cell_color[cy][cx] = color

    def line(self, x0, y0, x1, y1, ch, color, dotted=False):
        """Bresenham segment; dotted lights only every other pixel."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 <= x1 else -1
        sy = 1 if y0 <= y1 else -1
        err = dx + dy
        x, y = x0, y0
        step = 0
        while True:
            if not dotted or step % 2 == 0 or (x == x1 and y == y1):
                self.set_dot(x, y, ch, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
            step += 1

    def char_at(self, x, y):
        return self.cell_char[y][x] or " "

    def render(self, color_on: bool):
        return [
            "".join(_colorize(self.char_at(x, y), self.cell_color[y][x], color_on)
                    for x in range(self.width))
            for y in range(self.height)
        ]


# --------------------------------------------------------------------------
# Input normalisation
# --------------------------------------------------------------------------

# Upper bounds on what a single call may ask for. The renderers allocate
# width x height character grids, so without a cap one request could ask for
# gigabytes; these are far above anything readable in a text reply.
MAX_WIDTH = 500
MAX_HEIGHT = 200
MAX_BINS = 500
MAX_SERIES = 100
MAX_THRESHOLDS = 20
MAX_THRESHOLD_LABEL = 40
MAX_VALUES = 50_000  # values + points across all series
# Beyond this, scale arithmetic stops being exact (lo + 1 == lo past 2**53) and extremes overflow
# to inf; no readable chart needs numbers this large.
MAX_MAGNITUDE = 1e15
MAX_TEXT = 200  # title, labels, series names: characters


def _num(v, where: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ChartError(f"{where} must be a number, got {_q(v)}")
    if not math.isfinite(v):
        raise ChartError(f"{where} must be a finite number, got {v}")
    if abs(v) > MAX_MAGNITUDE:
        raise ChartError(f"{where} must be at most 1e15 in magnitude, got {v:g}")
    return float(v)


def _int(spec: dict, key: str, limit: int) -> int:
    """Optional non-negative integer option; 0/absent means \"use the default\"."""
    v = spec.get(key)
    if v is None:
        return 0
    if isinstance(v, bool) or not isinstance(v, (int, float)) or (isinstance(v, float) and not v.is_integer()):
        raise ChartError(f"{key} must be an integer, got {_q(v)}")
    v = int(v)
    if v > limit:
        raise ChartError(f"{key} must be at most {limit}, got {v}")
    return max(v, 0)


def _clean(s: str, where: str) -> str:
    """Bounded length, and control characters (newlines, tabs, ESC and the rest of Unicode
    category Cc) replaced by spaces: a newline would break the chart's rows, and an escape
    sequence in a title that came from untrusted data would reach whatever terminal shows it."""
    if len(s) > MAX_TEXT:
        raise ChartError(f"{where} must be at most {MAX_TEXT} characters, got {len(s)}")
    if any(unicodedata.category(ch) == "Cc" for ch in s):
        s = "".join(" " if unicodedata.category(ch) == "Cc" else ch for ch in s)
    return s


def _text(spec: dict, key: str) -> str:
    v = spec.get(key)
    if v is None:
        return ""
    if not isinstance(v, str):
        raise ChartError(f"{key} must be a string, got {_q(v)}")
    return _clean(v, key)


def _thresholds(raw) -> list:
    """`thresholds`: a list of numbers or {value, label} objects -> [(value, label)]."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ChartError("thresholds must be an array of numbers or {value, label} objects")
    if len(raw) > MAX_THRESHOLDS:
        raise ChartError(f"thresholds must have at most {MAX_THRESHOLDS} entries, got {len(raw)}")
    out = []
    for i, t in enumerate(raw):
        if not isinstance(t, dict):
            out.append((_num(t, f"thresholds {i}"), ""))
            continue
        label = _text(t, "label")
        if len(label) > MAX_THRESHOLD_LABEL:
            raise ChartError(f"thresholds {i}: label must be at most {MAX_THRESHOLD_LABEL} characters, got {len(label)}")
        out.append((_num(t.get("value"), f"thresholds {i} value"), label))
    return out


def _point_char(spec: dict) -> str:
    """pointChar's first character; it fills exactly one plot cell, so it must be one column wide."""
    ch = _text(spec, "pointChar")[:1]
    if ch and _char_width(ch) != 1:
        raise ChartError(f"pointChar must be a single-width character, got {_q(ch)} (wide characters such as emoji "
                         "take two columns)")
    return ch


def _normalize(spec: dict) -> dict:
    """Validate a raw JSON-shaped spec and coerce it to the shape the renderers use."""
    if not isinstance(spec, dict):
        raise ChartError("chart spec must be a JSON object")

    raw_series = spec.get("series")
    if raw_series is None:
        raw_series = []
    if not isinstance(raw_series, list):
        raise ChartError("series must be an array")
    if len(raw_series) > MAX_SERIES:
        raise ChartError(f"series must have at most {MAX_SERIES} entries, got {len(raw_series)}")

    total = 0
    series = []
    for i, s in enumerate(raw_series):
        if not isinstance(s, dict):
            raise ChartError(f"series {i} must be an object")
        values, points = s.get("values") or [], s.get("points") or []
        if not isinstance(values, list) or not isinstance(points, list):
            raise ChartError(f"series {i}: values and points must be arrays")
        total += len(values) + len(points)
        if total > MAX_VALUES:
            raise ChartError(f"too much data: at most {MAX_VALUES} values/points in total")
        pts = []
        for p in points:
            if not isinstance(p, dict):
                raise ChartError(f"series {i} points must be {{x, y}} objects")
            pts.append((_num(p.get("x"), f"series {i} point x"), _num(p.get("y"), f"series {i} point y")))
        series.append({
            "name": _text(s, "name"),
            "values": [_num(v, f"series {i} value") for v in values],
            "points": pts,
        })

    labels = spec.get("labels") or []
    if not isinstance(labels, list):
        raise ChartError("labels must be an array of strings")
    threshold = spec.get("threshold")
    use_color = _text(spec, "useColor")

    return {
        "chartType": _text(spec, "chartType"),
        "series": series,
        "labels": [_clean(str(l), f"labels {i}") for i, l in enumerate(labels)],
        "title": _text(spec, "title"),
        "width": _int(spec, "width", MAX_WIDTH),
        "height": _int(spec, "height", MAX_HEIGHT),
        "border": _text(spec, "border"),
        "style": _text(spec, "style"),
        "stacked": bool(spec.get("stacked")),
        "bins": _int(spec, "bins", MAX_BINS),
        "color": use_color == "on",
        "useColor": use_color,
        "threshold": None if threshold is None else _num(threshold, "threshold"),
        "thresholds": _thresholds(spec.get("thresholds")),
        "showPoints": bool(spec.get("showPoints")),
        "pointChar": _point_char(spec),
    }


# --------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------

def _render_sparkline(inp):
    lines = []
    for i, s in enumerate(inp["series"]):
        vals = s["values"]
        if not vals:
            raise ChartError(f"series {i} {_q(s['name'])} must contain at least one value")
        lo, hi = min(vals), max(vals)
        span = hi - lo
        spark = "".join(SPARK_TICKS[_level((v - lo) / span, len(SPARK_TICKS)) if span > 0 else 0] for v in vals)
        spark = _colorize(spark, _series_color(i), inp["color"])
        lines.append(f"{s['name']} {spark}" if s["name"] else spark)
    return "\n".join(lines)


def _bars_matrix(inp):
    series = inp["series"]
    if not series:
        raise ChartError("series must contain at least one entry")
    n = len(series[0]["values"])
    if n == 0:
        raise ChartError("series must contain at least one value")
    for i, s in enumerate(series):
        if len(s["values"]) != n:
            raise ChartError(
                f"all series must have the same number of values (series 0 has {n}, "
                f"series {i} has {len(s['values'])})")
    labels = inp["labels"]
    if labels and len(labels) != n:
        raise ChartError(f"labels length ({len(labels)}) must match each series' values length ({n})")
    if not labels:
        labels = [str(i + 1) for i in range(n)]
    names = [_series_label(s, i) for i, s in enumerate(series)]
    return labels, names, [s["values"] for s in series]


def _bar_fill_ramp(style: str):
    return {"halftone": HALFTONE_FILLS, "ascii": ASCII_FILLS}.get(style)


def _allocate_proportional(values, total_sum: float, total: int):
    """Largest-remainder split of `total` units proportionally to values."""
    n = len(values)
    result = [0] * n
    if total_sum <= 0 or total <= 0:
        return result
    fracs = [0.0] * n
    allocated = 0
    for i, v in enumerate(values):
        exact = v / total_sum * total
        result[i] = int(exact)
        fracs[i] = exact - result[i]
        allocated += result[i]
    remainder = total - allocated
    order = sorted(range(n), key=lambda i: -fracs[i])
    for i in range(min(remainder, n)):
        result[order[i]] += 1
    return result


def _stack_extents(matrix):
    """Largest positive / negative (magnitude) per-column stack totals."""
    max_pos = max_neg = 0.0
    if not matrix:
        return max_pos, max_neg
    for c in range(len(matrix[0])):
        pos = neg = 0.0
        for row in matrix:
            v = row[c]
            if v > 0:
                pos += v
            else:
                neg -= v
        max_pos, max_neg = max(max_pos, pos), max(max_neg, neg)
    return max_pos, max_neg


def _split_rows(max_pos, max_neg, total):
    """Rows for the positive side of a diverging stack (>=1 per side that has data)."""
    if max_pos <= 0:
        return 0
    if max_neg <= 0 or total < 2:
        return total
    return _clamp(_round(max_pos / (max_pos + max_neg) * total), 1, total - 1)


def _split_stack(values, max_pos, max_neg, up_cap, down_cap):
    """Whole rows per series on each side of the baseline for one stacked column."""
    pos = [v if v > 0 else 0.0 for v in values]
    neg = [-v if v < 0 else 0.0 for v in values]
    pos_sum, neg_sum = 0.0, 0.0
    for v in values:
        if v > 0:
            pos_sum += v
        elif v < 0:
            neg_sum -= v
    up = [0] * len(values)
    down = [0] * len(values)
    if max_pos > 0:
        up = _allocate_proportional(pos, pos_sum, _round(pos_sum / max_pos * up_cap))
    if max_neg > 0:
        down = _allocate_proportional(neg, neg_sum, _round(neg_sum / max_neg * down_cap))
    return up, down


def _render_bar(inp):
    labels, names, matrix = _bars_matrix(inp)
    width = inp["width"] if inp["width"] > 0 else 40
    height = inp["height"] if inp["height"] > 0 else 10
    color_on = inp["color"]
    ramp = _bar_fill_ramp(inp["style"])

    # Bars end on whole character cells by default. The fractional block glyphs used for
    # sub-cell precision (eighths) are missing from common default fonts such as Consolas,
    # where they make the right edge of a chart ragged; style "fine" opts back in.
    fine = inp["style"] == "fine"
    # A background track (see TRACK_FILL) shows each bar's cell run against the full 0..max
    # scale. Only for the plain single-baseline styles — halftone already has its own busy
    # texture, and stacked/diverging bars have no single "rest of the axis" to shade.
    track = inp["style"] in ("", "solid", "fine", "ascii")
    ascii_style = inp["style"] == "ascii"
    if inp["chartType"] == "vbar":
        # Without width the bars thicken to fill the same default plot width as line/area.
        return _render_vbar(labels, names, matrix, inp["width"] or 60, height, inp["stacked"], color_on, ramp, fine, track, ascii_style)
    if len(names) == 1:
        return _render_horizontal_bars(labels, matrix[0], width, ramp, fine, track, ascii_style)
    if inp["stacked"]:
        return _render_hbar_stacked(labels, names, matrix, width, color_on, ramp)
    return _render_hbar_grouped(labels, names, matrix, width, color_on, ramp, fine, track, ascii_style)


def _render_vbar(labels, names, matrix, width, height, stacked, color_on, ramp, fine=False, track=False, ascii_style=False):
    num_cat, num_series = len(labels), len(matrix)
    gap = 1
    bars_per_group = 1 if stacked else num_series
    bar_width = 1
    if width > 0:
        avail = width - (num_cat - 1) * gap
        if avail > 0:
            bw = avail // (num_cat * bars_per_group)
            if bw > 1:
                bar_width = bw

    max_label_w = max(_width(l) for l in labels)
    group_w = max(bars_per_group * bar_width, max_label_w)
    bars_offset = (group_w - bars_per_group * bar_width) // 2
    total_w = max(num_cat * group_w + (num_cat - 1) * gap, 1)

    grid = [[" "] * total_w for _ in range(height)]
    cgrid = [[-1] * total_w for _ in range(height)]

    def color_of(s):
        return _series_color(s) if color_on else -1

    max_pos, max_neg = _stack_extents(matrix)
    if stacked and max_neg == 0:
        max_sum = 0.0
        for c in range(num_cat):
            max_sum = max(max_sum, _sum(matrix[s][c] for s in range(num_series)))
        if max_sum == 0:
            max_sum = 1
        seg_ramp = ramp or FILLS
        for c in range(num_cat):
            col_start = c * (group_w + gap) + bars_offset
            values = [matrix[s][c] for s in range(num_series)]
            col_sum = _sum(values)
            total_rows = _round(col_sum / max_sum * height)
            cursor = 0
            for s, seg_rows in enumerate(_allocate_proportional(values, col_sum, total_rows)):
                ch = seg_ramp[s % len(seg_ramp)]
                for r in range(seg_rows):
                    row = height - 1 - cursor - r
                    if row < 0 or row >= height:
                        continue
                    for w in range(bar_width):
                        grid[row][col_start + w] = ch
                        cgrid[row][col_start + w] = color_of(s)
                cursor += seg_rows
    elif stacked:
        # Some value is negative: positives stack up from a shared zero
        # baseline, negatives stack down from it.
        up_cap = _split_rows(max_pos, max_neg, height)
        seg_ramp = ramp or FILLS
        for c in range(num_cat):
            col_start = c * (group_w + gap) + bars_offset
            values = [matrix[s][c] for s in range(num_series)]
            up, down = _split_stack(values, max_pos, max_neg, up_cap, height - up_cap)
            for side, rows_by_series in enumerate((up, down)):
                cursor = 0
                for s, seg_rows in enumerate(rows_by_series):
                    ch = seg_ramp[s % len(seg_ramp)]
                    for r in range(seg_rows):
                        row = up_cap + cursor + r if side else up_cap - 1 - cursor - r
                        if row < 0 or row >= height:
                            continue
                        for w in range(bar_width):
                            grid[row][col_start + w] = ch
                            cgrid[row][col_start + w] = color_of(s)
                    cursor += seg_rows
    else:
        min_val = max_val = 0.0
        for s in range(num_series):
            for c in range(num_cat):
                min_val = min(min_val, matrix[s][c])
                max_val = max(max_val, matrix[s][c])
        if max_val == min_val:
            max_val = min_val + 1
        diverging = min_val < 0
        zero_row = _clamp(_y_pixel(0, min_val, max_val, height), 0, height - 1)

        effective = ramp
        if effective is None and num_series > 1:
            effective = FILLS

        for c in range(num_cat):
            for s in range(num_series):
                col_start = c * (group_w + gap) + bars_offset + s * bar_width
                v = matrix[s][c]
                color = color_of(s)

                if effective is not None or not fine:
                    ch = effective[s % len(effective)] if effective is not None else "█"
                    if not diverging:
                        rows = _round(v / max_val * height)
                        if v > 0 and rows == 0:
                            rows = 1  # a non-zero value never disappears
                        filled = min(rows, height)
                        for w in range(bar_width):
                            col = col_start + w
                            for r in range(filled):
                                grid[height - 1 - r][col] = ch
                                cgrid[height - 1 - r][col] = color
                            if track:
                                pad = _track_glyph(ch, ascii_style)
                                for r in range(filled, height):
                                    grid[height - 1 - r][col] = pad
                    else:
                        lo, hi = sorted((zero_row, _y_pixel(v, min_val, max_val, height)))
                        for w in range(bar_width):
                            for r in range(lo, hi + 1):
                                grid[r][col_start + w] = ch
                                cgrid[r][col_start + w] = color
                    continue

                if not diverging:
                    eighths = _round(v / max_val * height * 8)
                    full, frac = eighths // 8, eighths % 8
                    for w in range(bar_width):
                        col = col_start + w
                        for r in range(min(full, height)):
                            grid[height - 1 - r][col] = "█"
                            cgrid[height - 1 - r][col] = color
                        top = min(full, height)
                        if frac > 0 and full < height:
                            grid[height - 1 - full][col] = EIGHTHS_UP[frac]
                            cgrid[height - 1 - full][col] = color
                            top = full + 1
                        if track:
                            pad = _track_glyph("█", ascii_style)
                            for r in range(top, height):
                                grid[height - 1 - r][col] = pad
                else:
                    lo, hi = sorted((zero_row, _y_pixel(v, min_val, max_val, height)))
                    for w in range(bar_width):
                        for r in range(lo, hi + 1):
                            grid[r][col_start + w] = "█"
                            cgrid[r][col_start + w] = color

        if diverging and min_val < 0 < max_val:
            for x in range(total_w):
                if grid[zero_row][x] == " ":
                    grid[zero_row][x] = "-"

    out = []
    for r in range(height):
        out.append("".join(_colorize(grid[r][x], cgrid[r][x], color_on) for x in range(total_w)))
    label_row = [" "] * total_w
    for c, lbl in enumerate(labels):
        start = c * (group_w + gap) + (group_w - _width(lbl)) // 2
        for j, ch in enumerate(_cells(lbl)):
            if 0 <= start + j < total_w:
                label_row[start + j] = ch
    out.append("".join(label_row).rstrip(" "))
    body = "\n".join(out)

    if num_series > 1:
        body += "\n\n" + (_named_legend(names, color_on, ramp) if ramp else _named_legend(names, color_on))
    return body


def _zero_col(min_val, max_val, width):
    return _round((0 - min_val) / (max_val - min_val) * width)


def _diverging_bar_run(zero_col, val_col, width, fill):
    lo, hi = sorted((zero_col, val_col))
    lo, hi = _clamp(lo, 0, width), _clamp(hi, 0, width)
    row = [" "] * width
    for i in range(lo, hi):
        row[i] = fill
    if 0 <= zero_col < width and row[zero_col] == " ":
        row[zero_col] = "|"
    return "".join(row)


def _render_bar_run(length: float, max_width: int, fill, fine=False, track=False, ascii_style=False) -> str:
    length = max(length, 0)
    if fill or not fine:
        ch = fill or "█"
        full = min(_round(length), max_width)
        if length > 0 and full == 0:
            full = 1  # a non-zero value never disappears
        pad = _track_glyph(ch, ascii_style) if track else " "
        return ch * full + pad * (max_width - full)
    full = min(int(length), max_width)
    frac = length - full
    s = EIGHTHS_LEFT[8] * full
    if full < max_width:
        idx = int(frac * 8)
        if idx > 0:
            s += EIGHTHS_LEFT[idx]
            full += 1
    pad = _track_glyph("█", ascii_style) if track else " "
    return s + pad * (max_width - full)


def _render_hbar_grouped(labels, names, matrix, width, color_on, ramp, fine=False, track=False, ascii_style=False):
    min_val = max_val = 0.0
    for row in matrix:
        for v in row:
            min_val, max_val = min(min_val, v), max(max_val, v)
    if max_val == min_val:
        max_val = min_val + 1
    diverging = min_val < 0
    zero_col = _zero_col(min_val, max_val, width) if diverging else 0
    max_name_w = max(_width(n) for n in names)

    blocks = []
    for c, lbl in enumerate(labels):
        lines = [lbl]
        for s, name in enumerate(names):
            v = matrix[s][c]
            fill = ramp[s % len(ramp)] if ramp else ""
            if diverging:
                val_col = _round((v - min_val) / (max_val - min_val) * width)
                bar = _diverging_bar_run(zero_col, val_col, width, fill or "█")
            else:
                bar = _render_bar_run(v / max_val * width, width, fill, fine, track, ascii_style)
            color = _series_color(s) if color_on else -1
            lines.append(f"  {_pad(name, max_name_w)} {_sep(ramp)} {_colorize(bar, color, color_on)} {_fmt(v)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_hbar_stacked_diverging(labels, names, matrix, width, color_on, ramp, max_pos, max_neg):
    pos_cols = _split_rows(max_pos, max_neg, width)
    neg_cols = width - pos_cols
    seg_ramp = ramp or FILLS
    max_label_w = max(_width(l) for l in labels)

    def seg(s, w):
        color = _series_color(s) if color_on else -1
        return _colorize(seg_ramp[s % len(seg_ramp)] * w, color, color_on)

    lines = []
    for c, lbl in enumerate(labels):
        values = [matrix[s][c] for s in range(len(names))]
        net = _sum(values)
        up, down = _split_stack(values, max_pos, max_neg, pos_cols, neg_cols)
        bar = " " * (neg_cols - sum(down))
        for s in range(len(down) - 1, -1, -1):
            bar += seg(s, down[s])
        for s, w in enumerate(up):
            bar += seg(s, w)
        bar += " " * (pos_cols - sum(up))
        lines.append(f"{_pad(lbl, max_label_w)} {_sep(ramp)} {bar} {_fmt(net)}")

    legend = _named_legend(names, color_on, ramp) if ramp else _named_legend(names, color_on)
    return "\n".join(lines) + "\n\n" + legend


def _render_hbar_stacked(labels, names, matrix, width, color_on, ramp):
    max_pos, max_neg = _stack_extents(matrix)
    if max_neg > 0:
        return _render_hbar_stacked_diverging(labels, names, matrix, width, color_on, ramp, max_pos, max_neg)
    max_sum = 0.0
    for c in range(len(labels)):
        max_sum = max(max_sum, _sum(matrix[s][c] for s in range(len(names))))
    if max_sum == 0:
        max_sum = 1
    max_label_w = max(_width(l) for l in labels)
    seg_ramp = ramp or FILLS

    lines = []
    for c, lbl in enumerate(labels):
        values = [matrix[s][c] for s in range(len(names))]
        col_sum = _sum(values)
        total_width = _round(col_sum / max_sum * width)
        bar, used = "", 0
        for s, w in enumerate(_allocate_proportional(values, col_sum, total_width)):
            color = _series_color(s) if color_on else -1
            bar += _colorize(seg_ramp[s % len(seg_ramp)] * w, color, color_on)
            used += w
        label = _pad(lbl, max_label_w)
        lines.append(f"{label} {_sep(ramp)} {bar}{' ' * (width - used)} {_fmt(col_sum)}")

    legend = _named_legend(names, color_on, ramp) if ramp else _named_legend(names, color_on)
    return "\n".join(lines) + "\n\n" + legend


def _render_horizontal_bars(labels, values, width, ramp, fine=False, track=False, ascii_style=False):
    if width <= 0:
        width = 40
    max_label = max(_width(l) for l in labels)
    fill = ramp[0] if ramp else ""
    min_val = max_val = 0.0
    for v in values:
        min_val, max_val = min(min_val, v), max(max_val, v)
    if max_val == min_val:
        max_val = min_val + 1

    lines = []
    if min_val < 0:
        zc = _zero_col(min_val, max_val, width)
        for i, v in enumerate(values):
            pad = " " * (max_label - _width(labels[i]))
            val_col = _round((v - min_val) / (max_val - min_val) * width)
            bar = _diverging_bar_run(zc, val_col, width, fill or "█")
            lines.append(f"{labels[i]}{pad} {_sep(ramp)} {bar} {_fmt(v)}")
        return "\n".join(lines)
    for i, v in enumerate(values):
        pad = " " * (max_label - _width(labels[i]))
        lines.append(f"{labels[i]}{pad} {_sep(ramp)} {_render_bar_run(v / max_val * width, width, fill, fine, track, ascii_style)} {_fmt(v)}")
    return "\n".join(lines)


def _line_legend(series, show_points, color_on, ascii_style=False):
    names = [_series_label(s, i) for i, s in enumerate(series)]
    if show_points:
        return _named_legend(names, color_on, ASCII_MARKERS if ascii_style else MARKERS)
    return _named_legend(names, color_on, ASCII_FILLS if ascii_style else FILLS)


def _render_line(inp):
    height = inp["height"] or 10
    width = inp["width"] or 60
    series = inp["series"]
    for i, s in enumerate(series):
        if len(s["values"]) < 2:
            raise ChartError(f"series {i} {_q(s['name'])} must contain at least two values")

    lo, hi = _series_min_max(series)
    threshold = inp["threshold"]
    # every dashed reference line: the single unlabelled `threshold` plus the `thresholds` list
    refs = ([threshold] if threshold is not None else []) + [v for v, _ in inp["thresholds"]]
    if refs:
        lo, hi = min([lo] + refs), max([hi] + refs)
    color_on = inp["color"]

    c = _Canvas(width, height)
    pw, ph = width, height
    dotted = inp["style"] == "dotted"
    ascii_style = inp["style"] == "ascii"  # plain ASCII glyphs and axis
    multi = len(series) > 1

    for si, s in enumerate(series):
        color = _series_color(si) if color_on else -1
        if inp["showPoints"]:
            line_char = "." if ascii_style else "·"
        elif ascii_style:
            line_char = ASCII_FILLS[si % len(ASCII_FILLS)]
        elif multi:
            line_char = FILLS[si % len(FILLS)]
        elif dotted:
            line_char = "+"
        else:
            line_char = ""
        n = len(s["values"])
        prev = None
        for i, v in enumerate(s["values"]):
            x, y = _x_pixel(i, n, pw), _y_pixel(v, lo, hi, ph)
            if prev is not None:
                c.line(prev[0], prev[1], x, y, line_char, color, dotted)
            else:
                c.set_dot(x, y, line_char, color)
            prev = (x, y)

    tcolor = THRESHOLD_COLOR if color_on else -1
    for ref in refs:
        row = _y_pixel(ref, lo, hi, height)
        for x in range(c.width):
            if x % 2 == 0:
                c.set_marker(x, row, "-", tcolor)
    # `thresholds` are named right of the plot, on their own row, so they never cover data;
    # lines that land on the same row share it.
    notes = {}
    for v, label in inp["thresholds"]:
        notes.setdefault(_y_pixel(v, lo, hi, height), []).append(f"{label}: {_fmt(v)}" if label else _fmt(v))

    if inp["showPoints"]:
        custom = inp["pointChar"][0] if inp["pointChar"] else ""
        for si, s in enumerate(series):
            color = _series_color(si) if color_on else -1
            marker_set = ASCII_MARKERS if ascii_style else MARKERS
            marker = custom or marker_set[si % len(marker_set)]
            n = len(s["values"])
            for i, v in enumerate(s["values"]):
                x, y = _x_pixel(i, n, pw), _y_pixel(v, lo, hi, ph)
                c.set_marker(x, y, marker, color)

    axis_labels, axis_w = _left_axis_labels(lo, hi, height)
    rows = c.render(color_on)
    tick = "+" if ascii_style else "┤"
    body = "\n".join(f"{axis_labels[r]:>{axis_w}} {tick}{l}"
                     + ("  " + _colorize(", ".join(notes[r]), tcolor, color_on) if r in notes else "")
                     for r, l in enumerate(rows))

    x = _x_axis_labels(inp["labels"], _series_max_len(series), width, axis_w + 2)
    if x:
        body += "\n" + x
    if multi:
        body += "\n\n" + _line_legend(series, inp["showPoints"], color_on, ascii_style)
    if threshold is not None:
        note = f"- - threshold: {_fmt(threshold)}"
        body += ("   " + note) if len(series) > 1 else ("\n\n" + note)
    return body


def _area_fill_ramp(style: str):
    return {"halftone": HALFTONE_FILLS, "ascii": AREA_ASCII_FILLS}.get(style, FILLS)


def _interp_at(values, x: int, width: int) -> float:
    n = len(values)
    if n == 1 or width <= 1:
        return values[0]
    pos = x * (n - 1) / (width - 1)
    i0 = int(pos)
    if i0 >= n - 1:
        return values[n - 1]
    frac = pos - i0
    return values[i0] * (1 - frac) + values[i0 + 1] * frac


def _render_area(inp):
    series = inp["series"]
    if not series:
        raise ChartError("series must contain at least one entry")
    n = len(series[0]["values"])
    for i, s in enumerate(series):
        if len(s["values"]) < 2:
            raise ChartError(f"series {i} {_q(s['name'])} must contain at least two values")
        if len(s["values"]) != n:
            raise ChartError(
                f"all series must have the same number of values (series 0 has {n}, "
                f"series {i} has {len(s['values'])})")

    height = inp["height"] or 10
    width = inp["width"] or 60
    color_on = inp["color"]
    ramp = _area_fill_ramp(inp["style"])
    num_series = len(series)
    names = [_series_label(s, i) for i, s in enumerate(series)]

    grid = [[" "] * width for _ in range(height)]
    cgrid = [[-1] * width for _ in range(height)]

    stack_matrix = [[_interp_at(s["values"], x, width) for x in range(width)] for s in series]
    max_pos, max_neg = _stack_extents(stack_matrix)

    if inp["stacked"] and max_neg == 0:
        min_val, max_val = 0.0, 0.0
        for x in range(width):
            max_val = max(max_val, _sum(_interp_at(s["values"], x, width) for s in series))
        if max_val == 0:
            max_val = 1
        for x in range(width):
            values = [_interp_at(s["values"], x, width) for s in series]
            col_sum = _sum(values)
            total_rows = _round(col_sum / max_val * height)
            cursor = 0
            for si, seg_rows in enumerate(_allocate_proportional(values, col_sum, total_rows)):
                ch = ramp[si % len(ramp)]
                color = _series_color(si) if color_on else -1
                for r in range(seg_rows):
                    row = height - 1 - cursor - r
                    if 0 <= row < height:
                        grid[row][x] = ch
                        cgrid[row][x] = color
                cursor += seg_rows
    elif inp["stacked"]:
        # Some value is negative: positive bands stack up from the zero row,
        # negative bands stack down from it, on a shared axis.
        min_val, max_val = -max_neg, max_pos
        zero_row = _clamp(_y_pixel(0, min_val, max_val, height), 0, height - 1)
        if max_neg > 0 and zero_row == height - 1 and height > 1:
            zero_row = height - 2
        for x in range(width):
            values = [stack_matrix[si][x] for si in range(num_series)]
            up, down = _split_stack(values, max_pos, max_neg, zero_row + 1, height - 1 - zero_row)
            for side, rows_by_series in enumerate((up, down)):
                cursor = 0
                for si, seg_rows in enumerate(rows_by_series):
                    ch = ramp[si % len(ramp)]
                    color = _series_color(si) if color_on else -1
                    for r in range(seg_rows):
                        row = zero_row + 1 + cursor + r if side else zero_row - cursor - r
                        if 0 <= row < height:
                            grid[row][x] = ch
                            cgrid[row][x] = color
                    cursor += seg_rows
    else:
        min_val, max_val = _series_min_max(series)
        min_val, max_val = min(min_val, 0), max(max_val, 0)
        if max_val == min_val:
            max_val = min_val + 1
        zero_row = _y_pixel(0, min_val, max_val, height)
        # Paint later series first so the first series ends up on top.
        for si in range(num_series - 1, -1, -1):
            ch = ramp[si % len(ramp)]
            color = _series_color(si) if color_on else -1
            for x in range(width):
                row = _y_pixel(_interp_at(series[si]["values"], x, width), min_val, max_val, height)
                lo, hi = sorted((row, zero_row))
                for r in range(lo, hi + 1):
                    grid[r][x] = ch
                    cgrid[r][x] = color

    axis_labels, axis_w = _left_axis_labels(min_val, max_val, height)
    lines = []
    for r in range(height):
        cells = "".join(_colorize(grid[r][x], cgrid[r][x], color_on) for x in range(width))
        lines.append(f"{axis_labels[r]:>{axis_w}} {'+' if _is_ascii_ramp(ramp) else '┤'}{cells}")
    body = "\n".join(lines)

    x = _x_axis_labels(inp["labels"], _series_max_len(series), width, axis_w + 2)
    if x:
        body += "\n" + x
    if num_series > 1:
        body += "\n\n" + _named_legend(names, color_on, ramp)
    return body


def _render_dotplot(inp):
    labels, names, matrix = _bars_matrix(inp)
    width = inp["width"] or 40
    color_on = inp["color"]
    num_series = len(names)

    min_val = max_val = matrix[0][0]
    for row in matrix:
        for v in row:
            min_val, max_val = min(min_val, v), max(max_val, v)
    if max_val == min_val:
        max_val = min_val + 1
    max_label = max(_width(l) for l in labels)

    lines = []
    for c, lbl in enumerate(labels):
        row = ["·"] * width
        crow = [-1] * width
        for s in range(num_series):
            col = _clamp(_round((matrix[s][c] - min_val) / (max_val - min_val) * (width - 1)), 0, width - 1)
            row[col] = MARKERS[s % len(MARKERS)]
            if color_on:
                crow[col] = _series_color(s)
        cells = "".join(_colorize(ch, crow[i], color_on) for i, ch in enumerate(row))
        line = f"{_pad(lbl, max_label)} │ {cells}"
        if num_series == 1:
            line += " " + _fmt(matrix[0][c])
        lines.append(line)

    body = "\n".join(lines) + f"\nvalue axis: [{_fmt(min_val)}, {_fmt(max_val)}]"
    if num_series > 1:
        body += "\n" + _named_legend(names, color_on, MARKERS)
    return body


def _render_scatter(inp):
    width = inp["width"] or 60
    height = inp["height"] or 15
    series = inp["series"]

    pts = []
    for i, s in enumerate(series):
        if not s["points"]:
            raise ChartError(f"series {i} {_q(s['name'])} must contain at least one point")
        pts.extend(s["points"])

    min_x, max_x = min(p[0] for p in pts), max(p[0] for p in pts)
    min_y, max_y = min(p[1] for p in pts), max(p[1] for p in pts)
    if max_x == min_x:
        max_x = min_x + 1
    if max_y == min_y:
        max_y = min_y + 1

    color_on = inp["color"]
    c = _Canvas(width, height)
    pw, ph = width, height
    for si, s in enumerate(series):
        color = _series_color(si) if color_on else -1
        for px_, py_ in s["points"]:
            px = _round((px_ - min_x) / (max_x - min_x) * (pw - 1))
            py = ph - 1 - _round((py_ - min_y) / (max_y - min_y) * (ph - 1))
            c.set_marker(px, py, MARKERS[si % len(MARKERS)], color)

    body = "\n".join(c.render(color_on))
    body += f"\nx: [{_fmt(min_x)}, {_fmt(max_x)}]  y: [{_fmt(min_y)}, {_fmt(max_y)}]"
    if len(series) > 1:
        names = [_series_label(s, i) for i, s in enumerate(series)]
        body += "\n" + _named_legend(names, color_on, MARKERS)
    return body


def _render_dual_axis(inp):
    series = inp["series"]
    if len(series) != 2:
        raise ChartError(f"dual_axis expects exactly two series, got {len(series)}")
    for i, s in enumerate(series):
        if len(s["values"]) < 2:
            raise ChartError(f"series {i} {_q(s['name'])} must contain at least two values")

    height = inp["height"] or 10
    width = inp["width"] or 60
    color_on = inp["color"]
    c = _Canvas(width, height)
    pw, ph = width, height

    mins, maxs = [0.0, 0.0], [0.0, 0.0]
    for si, s in enumerate(series):
        mins[si], maxs[si] = _series_min_max([s])
        color = _series_color(si) if color_on else -1
        glyph = DUAL_AXIS_GLYPHS[si]
        n = len(s["values"])
        prev = None
        for i, v in enumerate(s["values"]):
            x, y = _x_pixel(i, n, pw), _y_pixel(v, mins[si], maxs[si], ph)
            if prev is not None:
                c.line(prev[0], prev[1], x, y, glyph, color)
            else:
                c.set_dot(x, y, glyph, color)
            prev = (x, y)

    left, left_w = _left_axis_labels(mins[0], maxs[0], height)
    right, right_w = _left_axis_labels(mins[1], maxs[1], height)
    rows = c.render(color_on)
    body = "\n".join(
        f"{left[r]:>{left_w}} ┤{l}├ {right[r]:<{right_w}}" for r, l in enumerate(rows))

    n0, n1 = _series_label(series[0], 0), _series_label(series[1], 1)
    legend = (f"left:  {_colorize(DUAL_AXIS_GLYPHS[0], _series_color(0), color_on)} {n0}\n"
              f"right: {_colorize(DUAL_AXIS_GLYPHS[1], _series_color(1), color_on)} {n1}")
    return body + "\n\n" + legend


def _render_pie(inp):
    values, names, total = [], [], 0.0
    for i, s in enumerate(inp["series"]):
        v = _sum(s["values"])
        if v < 0:
            raise ChartError(f"series {i} {_q(s['name'])}: pie slice values must be non-negative")
        values.append(v)
        names.append(_series_label(s, i))
        total += v
    if total <= 0:
        raise ChartError("pie slice values must sum to more than zero")

    width, height = inp["width"], inp["height"]
    if width <= 0 and height <= 0:
        width, height = 44, 22
    elif width <= 0:
        width = height * 2
    elif height <= 0:
        height = width // 2
    height = max(height, 1)

    cumulative, running = [], 0.0
    for v in values:
        running += v
        cumulative.append(running / total)

    color_on = inp["color"]
    cx, cy = width / 2, height / 2
    radius = min(width / 2, height / 2 * PIE_ASPECT)

    rows = []
    for y in range(height):
        cells = []
        for x in range(width):
            dx = x + 0.5 - cx
            dy = (y + 0.5 - cy) * PIE_ASPECT
            if math.hypot(dx, dy) > radius:
                cells.append(" ")
                continue
            angle = math.atan2(dx, -dy)
            if angle < 0:
                angle += 2 * math.pi
            frac = angle / (2 * math.pi)
            sl = len(cumulative) - 1
            for i, cum in enumerate(cumulative):
                if frac <= cum:
                    sl = i
                    break
            cells.append(_colorize(FILLS[sl % len(FILLS)], _series_color(sl), color_on))
        rows.append("".join(cells))

    legend = [
        f"{_legend_swatch(i, color_on, FILLS)} {names[i]}: {_fmt(v)} ({v / total * 100:.1f}%)"
        for i, v in enumerate(values)
    ]
    return "\n".join(rows) + "\n\n" + "\n".join(legend)


def _render_histogram(inp):
    series = inp["series"]
    if len(series) != 1:
        raise ChartError(f"histogram expects exactly one series, got {len(series)}")
    values = series[0]["values"]
    if not values:
        raise ChartError("series must contain at least one value")
    bins = inp["bins"] if inp["bins"] > 0 else 10
    lo, hi = min(values), max(values)
    if hi == lo:
        hi = lo + 1
    bin_width = (hi - lo) / bins
    counts = [0.0] * bins
    for v in values:
        counts[_clamp(int((v - lo) / bin_width), 0, bins - 1)] += 1
    labels = []
    for i in range(bins):
        b_lo = lo + i * bin_width
        labels.append(f"{_fmt(b_lo)}..{_fmt(b_lo + bin_width)}")
    return _render_horizontal_bars(labels, counts, inp["width"], _bar_fill_ramp(inp["style"]), inp["style"] == "fine")


def _level(norm: float, n: int) -> int:
    """Which of n equal-width buckets norm (0..1) falls in: 0..n-1, the maximum in the top one.
    (Scaling by n - 1 and flooring would give the top level to the maximum alone and leave the
    bottom level to a sliver of the range.)"""
    return min(n - 1, int(norm * n))


def _render_heatmap(inp):
    series = inp["series"]
    if not series:
        raise ChartError("series must contain at least one row")
    num_cols = len(series[0]["values"])
    if num_cols == 0:
        raise ChartError("each row must contain at least one value")
    for i, s in enumerate(series):
        if len(s["values"]) != num_cols:
            raise ChartError(
                f"all rows must have the same number of values (row 0 has {num_cols}, "
                f"row {i} has {len(s['values'])})")
    labels = inp["labels"]
    if labels and len(labels) != num_cols:
        raise ChartError(f"labels length ({len(labels)}) must match each row's values length ({num_cols})")

    all_vals = [v for s in series for v in s["values"]]
    lo, hi = min(all_vals), max(all_vals)
    if hi == lo:
        hi = lo + 1
    color_on = inp["color"]
    row_label_w = max(_width(s["name"]) for s in series)
    # width is the grid's width (row labels excluded), 60 by default like line/area: cells widen
    # to fill it, but never shrink below HEAT_CELL_WIDTH, so many columns just widen the grid.
    cell_w = max(HEAT_CELL_WIDTH, ((inp["width"] or 60) + 1) // num_cols - 1)

    out = []
    if labels:
        out.append(" " * (row_label_w + 1) + "".join(_pad_center(c, cell_w) + " " for c in labels))
    for s in series:
        line = _pad(s["name"], row_label_w) + " "
        for v in s["values"]:
            norm = (v - lo) / (hi - lo)
            if color_on:
                cell = _colorize("█" * cell_w, HEAT_RAMP[_level(norm, len(HEAT_RAMP))], True)
            else:
                # blank is not a level: every value is data, so the lowest one still gets ░
                cell = SHADES[1 + _level(norm, len(SHADES) - 1)] * cell_w
            line += cell + " "
        out.append(line)
    return "\n".join(out)


def _quantile(sorted_vals, q: float) -> float:
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = q * (n - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _render_boxplot(inp):
    width = inp["width"] or 40
    summaries, names = [], []
    g_min, g_max = math.inf, -math.inf
    for i, s in enumerate(inp["series"]):
        if not s["values"]:
            raise ChartError(f"series {i} {_q(s['name'])} must contain at least one value")
        sv = sorted(s["values"])
        fn = (sv[0], _quantile(sv, 0.25), _quantile(sv, 0.5), _quantile(sv, 0.75), sv[-1])
        summaries.append(fn)
        names.append(_series_label(s, i))
        g_min, g_max = min(g_min, fn[0]), max(g_max, fn[4])
    if g_max == g_min:
        g_max = g_min + 1
    max_name_w = max(_width(n) for n in names)
    color_on = inp["color"]

    def pos(v):
        return _clamp(_round((v - g_min) / (g_max - g_min) * (width - 1)), 0, width - 1)

    lines = []
    for i, (mn, q1, med, q3, mx) in enumerate(summaries):
        row = [" "] * width
        min_p, q1_p, med_p, q3_p, max_p = pos(mn), pos(q1), pos(med), pos(q3), pos(mx)
        for x in range(min_p, max_p + 1):
            row[x] = "─"
        for x in range(q1_p, q3_p + 1):
            row[x] = "█"
        row[min_p], row[max_p], row[med_p] = "├", "┤", "┃"
        body = _colorize("".join(row), _series_color(i), color_on)
        name = _pad(names[i], max_name_w)
        lines.append(f"{name} │ {body}  min={_fmt(mn)} q1={_fmt(q1)} med={_fmt(med)} "
                     f"q3={_fmt(q3)} max={_fmt(mx)}")
    return "\n".join(lines)


_RENDERERS = {
    "sparkline": _render_sparkline,
    "vbar": _render_bar,
    "hbar": _render_bar,
    "line": _render_line,
    "area": _render_area,
    "dotplot": _render_dotplot,
    "scatter": _render_scatter,
    "dual_axis": _render_dual_axis,
    "pie": _render_pie,
    "histogram": _render_histogram,
    "heatmap": _render_heatmap,
    "boxplot": _render_boxplot,
}


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def render_chart(spec: dict) -> str:
    """Render a chart spec (same JSON shape as the MCP tool) to text.

    Raises ChartError on invalid input.
    """
    inp = _normalize(spec)
    if not inp["series"]:
        raise ChartError("series must contain at least one entry")
    if inp["border"] not in ("", "none", "ascii", "light", "heavy", "double", "rounded"):
        raise ChartError(f"invalid border {_q(inp['border'])} (expected one of: none, ascii, light, heavy, double, rounded)")
    if inp["style"] not in ("", "solid", "fine", "halftone", "ascii", "dotted"):
        raise ChartError(f"invalid style {_q(inp['style'])} (expected one of: solid, fine, halftone, ascii, dotted)")
    if inp["useColor"] not in ("", "auto", "on", "off"):
        raise ChartError(f"invalid useColor {_q(inp['useColor'])} (expected one of: auto, on, off)")

    renderer = _RENDERERS.get(inp["chartType"])
    if renderer is None:
        raise ChartError(f"unknown chartType {_q(inp['chartType'])} (expected one of: {', '.join(CHART_TYPES)})")
    return _wrap_border(renderer(inp), inp["title"], inp["border"])


# --------------------------------------------------------------------------
# CSV input
# --------------------------------------------------------------------------

# Options that may be set from the command line with --set key=value.
CSV_SETTABLE = ("title", "width", "height", "border", "style", "stacked", "bins", "useColor",
                "threshold", "thresholds", "showPoints", "pointChar")

_NUM_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
_NUM_DECIMAL_COMMA = re.compile(r"^-?\d+,\d+$")


def _parse_cell(cell: str, delimiter: str):
    """A number from a CSV cell, or None if the cell is empty or not numeric.

    Tolerates the decorations people put on numbers: surrounding spaces, a
    trailing %, currency symbols, thousands separators ("1,234.5"), and a decimal
    comma when the file itself isn't comma-separated ("3,14")."""
    s = cell.strip().replace(" ", "").replace(" ", "")
    s = s.lstrip("$€£").rstrip("%")
    if not s:
        return None
    if delimiter != "," and _NUM_DECIMAL_COMMA.match(s):
        s = s.replace(",", ".")
    elif _NUM_THOUSANDS.match(s):
        s = s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _read_csv(text: str):
    """(header, rows, delimiter) — the delimiter is sniffed among , ; tab |."""
    text = text.lstrip("﻿")
    if not text.strip():
        raise ChartError("the CSV is empty")
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delimiter) if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise ChartError("the CSV needs a header row and at least one data row")
    header = [h.strip() for h in rows[0]]
    return header, [r + [""] * (len(header) - len(r)) for r in rows[1:]], delimiter


def _column(header, ref: str, what: str) -> int:
    """Resolve a column: exact name, then case-insensitive, then a 1-based index, then a
    unique prefix ("p99" finds "p99_ms"), then a unique substring."""
    ref = ref.strip()
    if ref in header:
        return header.index(ref)
    lowered = [h.lower() for h in header]
    low = ref.lower()
    if lowered.count(low) == 1:
        return lowered.index(low)
    if ref.isdigit() and 1 <= int(ref) <= len(header):
        return int(ref) - 1
    for matches in ([i for i, h in enumerate(lowered) if h.startswith(low)],
                    [i for i, h in enumerate(lowered) if low in h]):
        if len(matches) == 1 and low:
            return matches[0]
        if len(matches) > 1:
            raise ChartError(f'{what} column "{ref}" is ambiguous; it matches: '
                             + ", ".join(header[i] for i in matches))
    raise ChartError(f'{what} column "{ref}" not found; the columns are: {", ".join(header)}')


def _split_columns(header, spec: str, what: str):
    """--values "a,b" -> column indexes; a name that itself contains a comma also works."""
    if spec.strip() in header:
        return [header.index(spec.strip())]
    return [_column(header, part, what) for part in spec.split(",") if part.strip()]


def spec_from_csv(text: str, chart: str, label=None, values=None, sort=None, limit=None, options=None) -> dict:
    """Turn CSV text into a render_chart spec.

    chart   the chartType to build.
    label   the column that names rows/categories (or the x column for scatter);
            default: the first non-numeric column (first numeric one for scatter).
    values  comma-separated columns to plot; default: every numeric column.
    sort    a column to sort rows by, "-name" for descending.
    limit   keep only the first N rows (after sorting).
    options extra spec fields (title, border, width, ...).

    Mapping: for vbar/hbar/dotplot/line/area each value column is a series and
    the label column gives the category/x-axis labels; sparkline/histogram/
    boxplot/dual_axis take each value column as a series; pie makes one slice per
    row (the first value column); heatmap makes one matrix row per CSV row with
    the value columns as its columns; scatter plots each value column against
    the label (x) column."""
    if chart not in CHARTS:
        raise ChartError(f"unknown chartType {_q(chart)} (expected one of: {', '.join(CHART_TYPES)})")
    header, rows, delim = _read_csv(text)

    # numeric columns: every non-empty cell parses
    def is_numeric(ci):
        cells = [r[ci] for r in rows if r[ci].strip()]
        return bool(cells) and all(_parse_cell(c, delim) is not None for c in cells)

    numeric = [ci for ci in range(len(header)) if is_numeric(ci)]

    if chart == "scatter":
        xi = _column(header, label, "label (x)") if label else (numeric[0] if numeric else None)
        if xi is None:
            raise ChartError("scatter needs a numeric x column; none of the columns is numeric")
        label_idx = xi
    else:
        text_cols = [ci for ci in range(len(header)) if ci not in numeric]
        label_idx = _column(header, label, "label") if label else (text_cols[0] if text_cols else None)

    if values:
        val_idx = _split_columns(header, values, "values")
    else:
        val_idx = [ci for ci in numeric if ci != label_idx]
    if not val_idx:
        raise ChartError("no numeric columns to plot; the columns are: " + ", ".join(header)
                         + " (use --values to pick columns explicitly)")

    if sort:
        name, _, order = sort.rpartition(":")
        if name and order.lower() in ("asc", "desc"):
            desc, sort = order.lower() == "desc", name
        else:
            desc = sort.startswith("-")
        si = _column(header, sort.lstrip("-+") if not sort.strip() in header else sort.strip(), "sort")
        if si in numeric:
            key = lambda r: (_parse_cell(r[si], delim) is None, _parse_cell(r[si], delim) or 0.0)  # noqa: E731
        else:
            key = lambda r: r[si].strip().lower()  # noqa: E731
        rows = sorted(rows, key=key, reverse=desc)
    if limit is not None:
        if limit < 1:
            raise ChartError("limit must be at least 1")
        rows = rows[:limit]

    def number(row_i, ci):
        v = _parse_cell(rows[row_i][ci], delim)
        if v is None:
            raw = rows[row_i][ci].strip()
            why = "is empty" if not raw else f"is not a number: {_q(raw)}"
            raise ChartError(f'row {row_i + 2}, column "{header[ci]}" {why}')
        return v

    def labels_for_rows():
        return [rows[i][label_idx].strip() or str(i + 1) for i in range(len(rows))]

    spec = {"chartType": chart}
    if chart == "pie":
        names = labels_for_rows() if label_idx is not None else [str(i + 1) for i in range(len(rows))]
        spec["series"] = [{"name": names[i], "values": [number(i, val_idx[0])]} for i in range(len(rows))]
    elif chart == "heatmap":
        names = labels_for_rows() if label_idx is not None else [str(i + 1) for i in range(len(rows))]
        spec["labels"] = [header[ci] for ci in val_idx]
        spec["series"] = [{"name": names[i], "values": [number(i, ci) for ci in val_idx]} for i in range(len(rows))]
    elif chart == "scatter":
        spec["series"] = [{"name": header[ci],
                           "points": [{"x": number(i, label_idx), "y": number(i, ci)} for i in range(len(rows))]}
                          for ci in val_idx if ci != label_idx]
        if not spec["series"]:
            raise ChartError("scatter needs at least one y column besides the x column")
    else:
        if label_idx is not None and chart in ("vbar", "hbar", "dotplot", "line", "area"):
            spec["labels"] = labels_for_rows()
        spec["series"] = [{"name": header[ci], "values": [number(i, ci) for i in range(len(rows))]} for ci in val_idx]

    for key, val in (options or {}).items():
        if key not in CSV_SETTABLE:
            raise ChartError(f"unknown option {_q(key)} (settable: {', '.join(CSV_SETTABLE)})")
        spec[key] = val
    return spec


def _parse_set(pairs):
    """['title=Latency', 'width=60', 'stacked=true'] -> {'title': 'Latency', 'width': 60, 'stacked': True}."""
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ChartError(f"--set expects key=value, got {_q(pair)}")
        key, raw = pair.split("=", 1)
        try:
            out[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            out[key.strip()] = raw
    return out


def _csv_main(argv) -> int:
    p = argparse.ArgumentParser(
        prog="asciicharts.py --csv", add_help=True,
        description="Draw a chart straight from a CSV or ExCSV file (header row required).")
    p.add_argument("--csv", required=True, metavar="FILE", help="CSV/ExCSV file, or - for stdin")
    p.add_argument("--chart", metavar="TYPE", help="chart type: " + ", ".join(CHART_TYPES)
                   + " — required for plain CSV; for an ExCSV file with its own #chart "
                     "suggestion(s), omit this and use --chart-name instead")
    p.add_argument("--chart-name", metavar="NAME", help="ExCSV only: render this file's own "
                   "#chart name= suggestion instead of building one with --chart (auto-picks "
                   "the file's only suggestion if there's exactly one and this is omitted)")
    p.add_argument("--list-charts", action="store_true",
                   help="ExCSV only: list the file's #chart suggestions (name, type, title) and exit")
    p.add_argument("--label", metavar="COL", help="column naming the rows/categories (x column for scatter); default: first text column")
    p.add_argument("--values", metavar="COLS", help="comma-separated columns to plot; default: all numeric columns")
    p.add_argument("--sort", metavar="COL", help="sort rows by this column: -COL or COL:desc for descending, COL:asc (default) for ascending")
    p.add_argument("--limit", type=int, metavar="N", help="keep only the first N rows (after sorting)")
    p.add_argument("--set", action="append", metavar="KEY=VALUE", default=[],
                   help="any chart option, e.g. --set title=Latency --set border=none --set width=60 (repeatable)")
    p.add_argument("--print-spec", action="store_true", help="print the generated JSON spec instead of the chart")
    # argparse would take "--sort -p99" for two options; glue such values to their flag.
    glued, i = [], 0
    while i < len(argv):
        if argv[i] in ("--sort", "--label", "--values") and i + 1 < len(argv)                 and argv[i + 1].startswith("-") and not argv[i + 1].startswith("--"):
            glued.append(f"{argv[i]}={argv[i + 1]}")
            i += 2
        else:
            glued.append(argv[i])
            i += 1
    args = p.parse_args(glued)
    try:
        if args.csv == "-":
            text = sys.stdin.read()
        else:
            with open(args.csv, encoding="utf-8-sig", newline="") as f:
                text = f.read()

        is_excsv = _is_excsv(text)

        if args.list_charts:
            if not is_excsv:
                raise ChartError("--list-charts needs an ExCSV file (starting with #!excsv); this looks like plain CSV")
            charts = list_excsv_charts(text)
            if not charts:
                print("(no #chart suggestions in this file)")
            for c in charts:
                extra = f' — "{c["title"]}"' if c.get("title") else ""
                print(f'{c["name"] or "(unnamed)"}  type={c["type"]}{extra}')
            return 0

        if args.chart and args.chart_name:
            raise ChartError("--chart and --chart-name are mutually exclusive: --chart builds a "
                             "chart from the data yourself, --chart-name uses one the file itself suggests")

        if is_excsv and not args.chart:
            spec = spec_from_excsv(text, args.chart_name, _parse_set(args.set))
        else:
            if not args.chart:
                raise ChartError("--chart TYPE is required (see --list) — or, for an ExCSV file "
                                 "with its own #chart suggestion(s), --chart-name (see --list-charts)")
            label, values, data_text = args.label, args.values, text
            if is_excsv:
                # Manual mode on an ExCSV file: ignore its #chart suggestions and treat the data
                # section as plain CSV, but still put its #column role= to use for the defaults
                # --label/--values would otherwise have to guess (dimension -> label, measure ->
                # values) when the caller didn't pin them down explicitly.
                doc = parse_excsv(text)
                data_text = doc["data_text"]
                if not label:
                    dims = [n for n, kv in doc["columns"].items() if kv.get("role") == "dimension"]
                    label = dims[0] if dims else label
                if not values:
                    measures = [n for n, kv in doc["columns"].items() if kv.get("role") == "measure"]
                    values = ",".join(measures) if measures else values
            spec = spec_from_csv(data_text, args.chart, label, values, args.sort, args.limit, _parse_set(args.set))

        print(json.dumps(spec, ensure_ascii=False) if args.print_spec else render_chart(spec))
        return 0
    except (ChartError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


# --------------------------------------------------------------------------
# ExCSV input (#chart)
# --------------------------------------------------------------------------
#
# ExCSV (https://github.com/boligolov/excsv) is CSV that describes itself: a `#!excsv` header
# line plus `#`-prefixed meta lines — column types/roles (`#column`), and, since v0.5, chart
# suggestions (`#chart`) — sitting above an ordinary CSV data section that any ordinary CSV
# reader still reads unchanged. `#chart type=bar x=category y=amount` names two already-typed
# columns and a mark; this turns that suggestion directly into a render_chart spec, following
# the mapping this project is the documented reference renderer for (docs/charts.md in that
# repo). --csv auto-detects an ExCSV file by its first line and, when it carries #chart
# suggestions, --chart-name (or auto-pick, if there's only one) renders straight from those
# instead of you re-specifying --chart/--label/--values yourself.
#
# This reads enough of the format to resolve #chart against #column and the data section — not
# a full ExCSV implementation. Not read at all: #@ file metadata, #$ SQL, #% aggregations (used
# instead of recomputing, per the format's own advice, but we're a chart renderer, not a
# validator), checksum=, computed columns, sidecar/zip/pack containers, or the JSON form. A
# #chart-vega escape-hatch line is recognized and its JSON validated (a malformed one still
# fails the file), but nothing here speaks Vega-Lite, so it can't be rendered as ASCII.

_EXCSV_DELIM_NAMES = {"comma": ",", "tab": "\t", "pipe": "|", "semicolon": ";"}
_EXCSV_QUOTE_NAMES = {"none": "", "double": '"', "single": "'"}

# The channel/modifier vocabulary a compact #chart line may carry, beyond type= and name=
# (consumed separately below). Anything else present is an unknown-attribute warning, not a
# failure — the same "ignore what you don't recognize" posture as an unknown #column attribute.
_EXCSV_CHART_ATTRS = {
    "x", "y", "x2", "y2", "color", "size", "theta", "radius", "shape", "opacity",
    "column", "row", "detail", "order", "tooltip", "text",
    "title", "aggregate", "bin", "stack", "sort", "limit", "hole",
}
# type= -> the channels that mark requires (docs/charts.md's marks table). point/circle need at
# least one of x/y and are handled separately, since it's an "either" rather than an "and".
_EXCSV_MARK_CHANNELS = {
    "bar": ("x", "y"), "line": ("x", "y"), "area": ("x", "y"), "arc": ("theta",),
    "rect": ("x", "y", "color"), "boxplot": ("x", "y"), "sparkline": ("y",),
}
# Every mark the ExCSV format itself defines (docs/charts.md's marks table) — used to tell a
# genuinely unrecognized type= (WARN chart_unknown_type at parse time, e.g. a typo or a future
# mark) apart from one this renderer just doesn't implement yet.
_EXCSV_SPEC_MARKS = set(_EXCSV_MARK_CHANNELS) | {"point", "circle", "tick", "text"}
# Marks this renderer knows how to draw. tick/text are valid, spec-recognized suggestions this
# renderer simply can't act on (no ASCII equivalent) — resolving one of those raises a clear
# message at render time, not a parse failure; they don't warn chart_unknown_type at parse time
# the way a mark outside the spec's own vocabulary (like a typo) does.
_EXCSV_KNOWN_MARKS = set(_EXCSV_MARK_CHANNELS) | {"point", "circle"}


def _is_excsv(text: str) -> bool:
    """Whether text looks like an ExCSV file: its very first line starts with #!excsv."""
    return text.lstrip("﻿").split("\n", 1)[0].rstrip("\r").startswith("#!excsv")


def _excsv_kv(payload: str) -> dict:
    """Parse `key=value key2="a value with spaces, and a "" for a literal quote"` — the
    key=value grammar shared by #!excsv, #column and #chart lines."""
    out, i, n = {}, 0, len(payload)
    while i < n:
        while i < n and payload[i].isspace():
            i += 1
        if i >= n:
            break
        eq = payload.find("=", i)
        if eq == -1:
            break
        key = payload[i:eq].strip()
        i = eq + 1
        if i < n and payload[i] == '"':
            i += 1
            buf = []
            while i < n:
                if payload[i] == '"':
                    if i + 1 < n and payload[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(payload[i])
                i += 1
            out[key] = "".join(buf)
        else:
            j = i
            while j < n and not payload[j].isspace():
                j += 1
            out[key] = payload[i:j]
            i = j
    return out


def parse_excsv(text: str) -> dict:
    """The #!excsv header, #column and #chart meta lines, and the raw data-section text.

    Returns {"header", "columns", "charts", "warnings", "data_text"}. `columns` maps name ->
    its #column attributes (last #column for a repeated name wins). `charts` is a list of
    {"kind": "compact", "name", "type", "attrs"} or {"kind": "vega", "name": None, "engine",
    "raw", "parsed"} entries, in file order. `warnings` are advisory, human-readable strings
    ending in the spec's own error-kind name in parentheses, e.g. "(chart_duplicate_name)" —
    nothing in here is fatal. Raises ChartError for the FAIL-severity #chart conditions
    (chart_missing_type/_name, chart_vega_invalid_json) and for a file that isn't ExCSV at all."""
    text = text.lstrip("﻿")
    lines = text.split("\n")
    if not lines or not lines[0].rstrip("\r").startswith("#!excsv"):
        raise ChartError("not an ExCSV file: the first line must start with #!excsv")
    header = _excsv_kv(lines[0].rstrip("\r")[len("#!excsv"):])
    columns, charts, warnings = {}, [], []
    seen_names = set()
    body_start = len(lines)
    for i in range(1, len(lines)):
        line = lines[i].rstrip("\r")
        if not line.startswith("#"):
            body_start = i
            break
        if line.startswith("##"):
            continue
        if line.startswith("#column "):
            kv = _excsv_kv(line[len("#column "):])
            if kv.get("name"):
                columns[kv["name"]] = kv
        elif line.startswith("#chart-"):
            engine, _, payload = line[len("#chart-"):].partition(":")
            payload = payload[1:] if payload.startswith(" ") else payload
            entry = {"kind": "vega", "name": None, "engine": engine, "raw": payload}
            if engine == "vega":
                try:
                    entry["parsed"] = json.loads(payload)
                except json.JSONDecodeError as e:
                    raise ChartError(f"line {i + 1}: #chart-vega payload is not valid JSON: "
                                     f"{e} (chart_vega_invalid_json)")
            else:
                warnings.append(f'line {i + 1}: unrecognized #chart-{engine}: engine (chart_unknown_type)')
            charts.append(entry)
        elif line.startswith("#chart "):
            kv = _excsv_kv(line[len("#chart "):])
            ctype, name = kv.pop("type", None), kv.pop("name", None)
            if ctype is None:
                raise ChartError(f"line {i + 1}: #chart is missing type= (chart_missing_type)")
            if name is None:
                raise ChartError(f"line {i + 1}: #chart type={ctype} is missing name= (chart_missing_name)")
            if name in seen_names:
                warnings.append(f'#chart "{name}": duplicate name=, the later line wins (chart_duplicate_name)')
            seen_names.add(name)
            if ctype not in _EXCSV_SPEC_MARKS:
                warnings.append(f'#chart "{name}": unrecognized type={ctype} (chart_unknown_type)')
            for attr in sorted(set(kv) - _EXCSV_CHART_ATTRS):
                warnings.append(f'#chart "{name}": unrecognized attribute "{attr}" (chart_unknown_channel)')
            charts.append({"kind": "compact", "name": name, "type": ctype,
                           "attrs": {k: v for k, v in kv.items() if k in _EXCSV_CHART_ATTRS}})
        # every other "#" line (#@, #$, #%, #index, or anything unrecognized) carries no
        # chart-relevant information and is skipped, per the format's own "ignore unknown
        # meta lines" rule.
    return {"header": header, "columns": columns, "charts": charts, "warnings": warnings,
            "data_text": "\n".join(lines[body_start:])}


def _excsv_dialect(header: dict):
    """(delim, quote, has_header, null_marker) resolved from the #!excsv header fields."""
    delim_raw = header.get("delim", "comma")
    delim = _EXCSV_DELIM_NAMES.get(delim_raw, delim_raw)
    if len(delim) != 1:
        raise ChartError(f"ExCSV delimiter {_q(delim_raw)} is not one character; multi-character "
                         f"delimiters aren't supported here")
    quote_raw = header.get("quote", "none")
    quote = _EXCSV_QUOTE_NAMES.get(quote_raw, quote_raw)
    if quote and len(quote) != 1:
        raise ChartError(f"ExCSV quote {_q(quote_raw)} is not one character; multi-character "
                         f"quotes aren't supported here")
    return delim, quote, header.get("header", "1") != "0", header.get("null")


def _excsv_read_data(data_text: str, delim: str, quote: str, has_header: bool):
    """(col_names, rows) from the data section, in the file's own declared dialect. col_names is
    [] when has_header is False — the caller resolves names from #column index= instead."""
    if quote:
        reader = csv.reader(io.StringIO(data_text), delimiter=delim, quotechar=quote)
    else:
        reader = csv.reader(io.StringIO(data_text), delimiter=delim, quoting=csv.QUOTE_NONE)
    all_rows = [r for r in reader if any(c.strip() for c in r)]
    if not all_rows or (has_header and len(all_rows) < 2):
        raise ChartError("the ExCSV file has no data rows")
    col_names, rows = (all_rows[0], all_rows[1:]) if has_header else ([], all_rows)
    col_names = [h.strip() for h in col_names]
    width = max(len(r) for r in rows)
    return col_names, [r + [""] * (width - len(r)) for r in rows]


def _excsv_column_names(doc: dict, col_names: list, width: int) -> list:
    """Column names aligned to data positions. header=1 already has real ones (the CSV header
    row); header=0 builds them from #column index=/name= — only named columns are addressable,
    same restriction #chart channels have (reference by name, never by position)."""
    if col_names:
        return col_names
    names = [""] * width
    for name, kv in doc["columns"].items():
        idx = kv.get("index", "")
        if idx.lstrip("-").isdigit() and 0 <= int(idx) < width:
            names[int(idx)] = name
    return names


def _excsv_values(col_name: str, col_names: list, rows: list, null_marker):
    """Raw string values of one column, empty/null-marker cells as None. None (the return value,
    not a list of them) if the column isn't in the data at all."""
    if col_name not in col_names:
        return None
    ci = col_names.index(col_name)
    return [None if (r[ci] == "" or r[ci] == null_marker) else r[ci] for r in rows]


def _excsv_col_role(doc: dict, col: str) -> str:
    """A column's analytical role: its own #column role= if declared, else a guess from type=
    (numeric -> measure, otherwise dimension) — used to infer bar/hbar orientation."""
    meta = doc["columns"].get(col) or {}
    if meta.get("role"):
        return meta["role"]
    return "measure" if meta.get("type") in ("int", "long", "float", "double", "decimal") else "dimension"


def _excsv_channel(doc: dict, col_names: list, attrs: dict, channel: str, chart_name: str):
    """The column name a #chart channel resolves to (or the count() literal, or None if the
    channel isn't set). Raises chart_unknown_column if it names something not declared."""
    ref = attrs.get(channel)
    if ref is None or ref == "count()":
        return ref
    if ref not in doc["columns"]:
        raise ChartError(f'#chart "{chart_name}": {channel}={_q(ref)} has no #column name= '
                         f"declaration (chart_unknown_column)")
    if ref not in col_names:
        raise ChartError(f'#chart "{chart_name}": {channel}={_q(ref)} is declared with #column '
                         f"but is not a column in the data section")
    return ref


def _excsv_int_attr(attrs: dict, key: str):
    v = attrs.get(key)
    if v is None:
        return None
    try:
        return int(float(v))
    except ValueError:
        raise ChartError(f"{key}={_q(v)} is not a number")


def _excsv_agg_value(vals: list, agg: str, delim: str) -> float:
    """One aggregated number from a bucket of raw (already null-filtered-to-None) cell values."""
    non_null = [v for v in vals if v is not None]
    if agg == "count":
        return float(len(vals))
    if agg == "count_distinct":
        return float(len(set(non_null)))
    nums = [n for n in (_parse_cell(v, delim) for v in non_null) if n is not None]
    if agg == "avg":
        return _sum(nums) / len(nums) if nums else 0.0
    if agg == "min":
        return min(nums) if nums else 0.0
    if agg == "max":
        return max(nums) if nums else 0.0
    return _sum(nums)  # sum — also the default for an agg= value we don't recognize


def _excsv_aggregate(keys: list, raw_values: list, agg: str, delim: str):
    """Group raw_values by keys (equal length), in first-seen key order: [(key, aggregated), ...]."""
    order, buckets = [], {}
    for k, v in zip(keys, raw_values):
        k = "" if k is None else k
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(v)
    return [(k, _excsv_agg_value(buckets[k], agg, delim)) for k in order]


def _excsv_group2(primary_raw: list, secondary_raw: list, value_raw: list, agg: str, delim: str):
    """Two-level group-by — primary categories x secondary categories, each in first-seen order —
    aggregating value_raw per (primary, secondary) cell. Used for color-grouped bar/line/area (
    primary=x, secondary=color) and for rect/heatmap (primary=x, secondary=y). A combination that
    never occurs aggregates to None, not 0 — the caller decides how to fill that gap."""
    primaries, p_seen, secondaries, s_seen = [], set(), [], set()
    buckets = {}
    for p, s, v in zip(primary_raw, secondary_raw, value_raw):
        p = "" if p is None else p
        s = "" if s is None else s
        if p not in p_seen:
            p_seen.add(p)
            primaries.append(p)
        if s not in s_seen:
            s_seen.add(s)
            secondaries.append(s)
        buckets.setdefault((p, s), []).append(v)
    grid = {s: [_excsv_agg_value(buckets[(p, s)], agg, delim) if (p, s) in buckets else None
               for p in primaries] for s in secondaries}
    return primaries, secondaries, grid


def _excsv_order(indices, sort, limit, key):
    """Index order for a #chart's sort=/limit= modifiers: asc/desc by `key`, then a top-N cutoff."""
    indices = list(indices)
    if sort in ("asc", "desc"):
        indices.sort(key=key, reverse=(sort == "desc"))
    return indices if limit is None else indices[:limit]


def _excsv_sort_limit(pairs: list, sort, limit, by: str):
    """sort=/limit= over [(key, value), ...]. by="value" ranks by the aggregated number (bar/
    arc's usual top-N reading of sort=desc); by="key" ranks by the category label itself
    (line/area/boxplot, whose axis usually has its own natural — often chronological — order
    that reordering by value would scramble)."""
    idx = 1 if by == "value" else 0
    order = _excsv_order(range(len(pairs)), sort, limit, key=lambda i: pairs[i][idx])
    return [pairs[i] for i in order]


def _excsv_bar_spec(doc, x, y, color, attrs, sort, limit, values_of, agg_of, delim):
    bin_ = attrs.get("bin")
    if bin_ is not None and y == "count()":
        xv = [v for v in (_parse_cell(v, delim) for v in values_of(x)) if v is not None]
        if not xv:
            raise ChartError(f"column {_q(x)} has no numeric values to bin")
        spec = {"chartType": "histogram", "series": [{"values": xv}]}
        bins = _excsv_int_attr(attrs, "bin")
        if bins and bins != 1:
            spec["bins"] = bins
        return spec

    # Orientation follows which side the dimension sits on, not a separate switch: x=dimension
    # y=measure draws vertical bars, the swap draws horizontal ones.
    if _excsv_col_role(doc, x) == "measure" and _excsv_col_role(doc, y) != "measure":
        dim_col, measure_col, orientation = y, x, "hbar"
    else:
        dim_col, measure_col, orientation = x, y, "vbar"
    dim_raw = values_of(dim_col)
    measure_raw, agg = (dim_raw, "count") if measure_col == "count()" else (values_of(measure_col), agg_of(measure_col))

    if color:
        cats, cols, grid = _excsv_group2(dim_raw, values_of(color), measure_raw, agg, delim)
        totals = [_sum(v for v in (grid[c][i] for c in cols) if v is not None) for i in range(len(cats))]
        order = _excsv_order(range(len(cats)), sort, limit, key=lambda i: totals[i])
        spec = {"chartType": orientation, "labels": [cats[i] for i in order],
                "series": [{"name": c, "values": [grid[c][i] or 0.0 for i in order]} for c in cols]}
        if attrs.get("stack") in ("1", "true"):
            spec["stacked"] = True
        return spec

    pairs = _excsv_sort_limit(_excsv_aggregate(dim_raw, measure_raw, agg, delim), sort, limit, "value")
    return {"chartType": orientation, "labels": [k for k, _ in pairs], "series": [{"values": [v for _, v in pairs]}]}


def _excsv_trend_spec(mark, x, y, color, attrs, sort, limit, values_of, agg_of, delim):
    dim_raw = values_of(x)
    if color:
        cats, cols, grid = _excsv_group2(dim_raw, values_of(color), values_of(y), agg_of(y), delim)
        order = _excsv_order(range(len(cats)), sort, limit, key=lambda i: cats[i])
        spec = {"chartType": mark, "labels": [cats[i] for i in order],
                "series": [{"name": c, "values": [grid[c][i] or 0.0 for i in order]} for c in cols]}
        if mark == "area" and attrs.get("stack") in ("1", "true"):
            spec["stacked"] = True
        return spec
    pairs = _excsv_sort_limit(_excsv_aggregate(dim_raw, values_of(y), agg_of(y), delim), sort, limit, "key")
    return {"chartType": mark, "labels": [k for k, _ in pairs], "series": [{"values": [v for _, v in pairs]}]}


def _excsv_pie_spec(slice_col, theta, sort, limit, values_of, agg_of, delim):
    if theta == "count()":
        if not slice_col:
            raise ChartError("theta=count() needs a slice column (color=, x=, or y=)")
        slice_raw = values_of(slice_col)
        pairs = _excsv_aggregate(slice_raw, slice_raw, "count", delim)
    elif slice_col:
        pairs = _excsv_aggregate(values_of(slice_col), values_of(theta), agg_of(theta), delim)
    else:
        nums = [n for n in (_parse_cell(v, delim) for v in values_of(theta)) if n is not None]
        pairs = [(str(i + 1), v) for i, v in enumerate(nums)]
    pairs = _excsv_sort_limit(pairs, sort, limit, "value")
    return {"chartType": "pie", "series": [{"name": k, "values": [v]} for k, v in pairs]}


def _excsv_heatmap_spec(x, y, color, values_of, agg_of, delim):
    cats, rows_, grid = _excsv_group2(values_of(x), values_of(y), values_of(color), agg_of(color), delim)
    return {"chartType": "heatmap", "labels": cats,
            "series": [{"name": r, "values": [grid[r][i] or 0.0 for i in range(len(cats))]} for r in rows_]}


def _excsv_boxplot_spec(x, y, sort, limit, values_of, delim):
    order, groups = [], {}
    for k, v in zip(values_of(x), values_of(y)):
        if v is None:
            continue
        k = "" if k is None else k
        n = _parse_cell(v, delim)
        if n is None:
            continue
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(n)
    if sort in ("asc", "desc"):
        order = sorted(order, reverse=(sort == "desc"))
    if limit is not None:
        order = order[:limit]
    return {"chartType": "boxplot", "series": [{"name": k, "values": groups[k]} for k in order if groups[k]]}


def _excsv_scatter_spec(x, y, color, values_of, delim):
    if x and y:
        xv = [_parse_cell(v, delim) for v in values_of(x)]
        yv = [_parse_cell(v, delim) for v in values_of(y)]
        if color:
            order, groups = [], {}
            for a, b, c in zip(xv, yv, values_of(color)):
                if a is None or b is None:
                    continue
                c = c or ""
                if c not in groups:
                    groups[c] = []
                    order.append(c)
                groups[c].append((a, b))
            series = [{"name": c, "points": [{"x": a, "y": b} for a, b in groups[c]]} for c in order]
        else:
            series = [{"points": [{"x": a, "y": b} for a, b in zip(xv, yv) if a is not None and b is not None]}]
        return {"chartType": "scatter", "series": series}
    # Only one of x/y set: a one-axis distribution, not a bivariate scatter (docs/charts.md
    # "Orientation and variants"). There's no natural category axis to place these against, so
    # row position stands in for one, same fallback plain CSV uses when it has no text column.
    vals = [v for v in (_parse_cell(v, delim) for v in values_of(x or y)) if v is not None]
    return {"chartType": "dotplot", "labels": [str(i + 1) for i in range(len(vals))], "series": [{"values": vals}]}


def _find_excsv_chart(doc: dict, name: str | None):
    compacts = [c for c in doc["charts"] if c["kind"] == "compact"]
    if name is not None:
        matches = [c for c in doc["charts"] if c.get("name") == name]
        if not matches:
            available = ", ".join(c["name"] for c in compacts) or "(none)"
            raise ChartError(f"no #chart named {_q(name)} in this file; available: {available}")
        return matches[-1]  # a duplicate name=: the later line wins for addressing, same as #column
    if len(compacts) == 1:
        return compacts[0]
    if not compacts:
        if doc["charts"]:
            raise ChartError("this file only has #chart-vega suggestions, which have no ASCII "
                             "renderer here; pass --chart TYPE to build your own chart instead")
        raise ChartError("this file has no #chart suggestions to use automatically; pass --chart "
                         "TYPE (see --list) or --chart-name NAME")
    raise ChartError(f"this file suggests {len(compacts)} charts: " + ", ".join(c["name"] for c in compacts)
                     + " — pick one with --chart-name NAME (see --list-charts), or use --chart TYPE "
                       "to build your own")


def resolve_excsv_chart(doc: dict, name: str | None = None) -> dict:
    """One #chart suggestion, resolved against #column and the data section, as a render_chart
    spec — the type=/channel mapping in https://github.com/boligolov/excsv's docs/charts.md.
    name=None auto-picks the file's only suggestion, or lists the choices if it has several."""
    entry = _find_excsv_chart(doc, name)
    if entry["kind"] == "vega":
        raise ChartError("#chart-vega has no ASCII renderer here; pass --chart TYPE to build "
                         "your own chart from the data instead")
    cname, mark, attrs = entry["name"], entry["type"], entry["attrs"]
    if mark not in _EXCSV_KNOWN_MARKS:
        raise ChartError(f'#chart "{cname}": type={_q(mark)} has no asciicharts equivalent here '
                         f"(supported: bar, line, area, point, circle, arc, rect, boxplot, sparkline)")

    delim, quote, has_header, null_marker = _excsv_dialect(doc["header"])
    col_names, rows = _excsv_read_data(doc["data_text"], delim, quote, has_header)
    col_names = _excsv_column_names(doc, col_names, len(rows[0]) if rows else 0)

    channels = {c: _excsv_channel(doc, col_names, attrs, c, cname) for c in ("x", "y", "color", "theta")}
    if mark in ("point", "circle"):
        if not (channels["x"] or channels["y"]):
            raise ChartError(f'#chart "{cname}": needs at least one of x=/y= (chart_missing_required_channel)')
    else:
        for needed in _EXCSV_MARK_CHANNELS[mark]:
            if not channels[needed]:
                raise ChartError(f'#chart "{cname}": type={mark} needs {needed}= (chart_missing_required_channel)')
    x, y, color, theta = channels["x"], channels["y"], channels["color"], channels["theta"]

    def values_of(col):
        v = _excsv_values(col, col_names, rows, null_marker)
        if v is None:
            raise ChartError(f'#chart "{cname}": column {_q(col)} is declared but not present in the data')
        return v

    def agg_of(col):
        return attrs.get("aggregate") or (doc["columns"].get(col) or {}).get("agg") or "sum"

    sort, limit = attrs.get("sort"), _excsv_int_attr(attrs, "limit")

    if mark == "bar":
        spec = _excsv_bar_spec(doc, x, y, color, attrs, sort, limit, values_of, agg_of, delim)
    elif mark in ("line", "area"):
        spec = _excsv_trend_spec(mark, x, y, color, attrs, sort, limit, values_of, agg_of, delim)
    elif mark == "sparkline":
        yv = [v for v in (_parse_cell(v, delim) for v in values_of(y)) if v is not None]
        spec = {"chartType": "sparkline", "series": [{"values": yv}]}
    elif mark == "arc":
        spec = _excsv_pie_spec(color or x or y, theta, sort, limit, values_of, agg_of, delim)
    elif mark == "rect":
        spec = _excsv_heatmap_spec(x, y, color, values_of, agg_of, delim)
    elif mark == "boxplot":
        spec = _excsv_boxplot_spec(x, y, sort, limit, values_of, delim)
    else:  # point / circle
        spec = _excsv_scatter_spec(x, y, color, values_of, delim)

    if attrs.get("title"):
        spec["title"] = attrs["title"]
    return spec


def spec_from_excsv(text: str, chart_name: str | None = None, options: dict | None = None) -> dict:
    """Parse an ExCSV file and resolve one of its own #chart suggestions into a render_chart
    spec. chart_name=None auto-picks the file's only suggestion (ChartError, listing the
    choices, if it has more than one). options works exactly like spec_from_csv's: extra spec
    fields such as {"border": "none"}, applied after (and so overriding) the chart's own title=."""
    doc = parse_excsv(text)
    spec = resolve_excsv_chart(doc, chart_name)
    for key, val in (options or {}).items():
        if key not in CSV_SETTABLE:
            raise ChartError(f"unknown option {_q(key)} (settable: {', '.join(CSV_SETTABLE)})")
        spec[key] = val
    return spec


def list_excsv_charts(text: str) -> list:
    """The #chart suggestions in an ExCSV file: [{"name", "type", "title"}, ...] for compact-form
    lines (a repeated name= keeps only the last one, however it is addressed), plus one
    {"name": None, "type": "chart-vega"} entry per #chart-vega line — listed for visibility even
    though it can't be rendered here."""
    doc = parse_excsv(text)
    compacts = {}
    vegas = []
    for c in doc["charts"]:
        if c["kind"] == "compact":
            compacts[c["name"]] = {"name": c["name"], "type": c["type"], "title": c["attrs"].get("title")}
        else:
            vegas.append({"name": None, "type": f'chart-{c["engine"]}', "title": None})
    return list(compacts.values()) + vegas


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", newline="\n")

    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--version":
        print(__version__)
        return 0
    if "--csv" in argv:
        return _csv_main(argv)
    if argv[0] == "--list":
        for c in list_charts():
            opts = ", ".join(c["options"]) or "-"
            print(f"{c['type']}\n  {c['summary']}\n  series:  {c['series']}\n  options: {opts}\n"
                  f"  example: {json.dumps(c['example'], ensure_ascii=False, separators=(',', ':'))}\n")
        print("Every chart also accepts: title, border, useColor.")
        return 0

    try:
        if argv[0] == "--json":
            if len(argv) < 2:
                raise ChartError("--json needs a JSON string argument")
            raw = argv[1]
        elif argv[0] == "-":
            raw = sys.stdin.read()
        else:
            with open(argv[0], encoding="utf-8-sig") as f:
                raw = f.read()
        try:
            spec = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ChartError(f"invalid JSON: {e}")
        print(render_chart(spec))
        return 0
    except (ChartError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
