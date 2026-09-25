#!/usr/bin/env python3
"""Programmatic grading for the hand-drawn (no-script) skill evals in hand_evals.json.

    python test/evals/hand_grade.py <run_dir> <eval_name>

<run_dir> holds outputs/reply.md, the agent's final reply. Writes grading.json in the format the
skill-creator viewer expects: expectations[] of {text, passed, evidence}.

The checks are about what goes wrong when a chart is drawn by hand: lengths that don't match the values
(checked within one cell of round(v / max × L), L being the longest bar the agent drew), frames that are
not rectangular (measured in display columns, as a terminal counts them), glyphs a common font lacks,
series that can't be told apart.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = {e["eval_name"]: e for e in json.loads((HERE / "hand_evals.json").read_text(encoding="utf-8"))["evals"]}
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)

# The font-safe alphabet (see references/glyphs.md): ASCII, Latin-1, WGL4 box drawing, shades, half
# blocks, markers. Sparkline ticks are allowed only where a sparkline is the point.
WGL4_BOX = set("─│┌┐└┘├┤┬┴┼═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬")
SAFE = WGL4_BOX | set("█▓▒░▌▄▐▀") | set("●○▲■□▼♦◊►◄") | set("¦·")
# WGL4 characters a chart's text may use besides those: dashes, quotes, arrows, math signs (principles
# §2.1 draws with a subset of WGL4; its text may use the rest)
WGL4_TEXT = set("–—‘’“”•…‰‹›€™←↑→↓↔↕−∙√∞≈≠≡≤≥")
SPARK = "▁▂▃▄▅▆▇█"
TRACK = set(" ░,·")
SEPARATORS = "│|¦┃"
FRAME_LEFT = set("│|║┃")


def round_half_away(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def display_width(line):
    return sum(0 if unicodedata.combining(c) or unicodedata.category(c) in ("Mn", "Me", "Cf")
               else 2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in line)


def code_blocks(text):
    return [m.group(1) for m in FENCE.finditer(text)]


def starts_with(line, chars):
    """Does line start with one of chars? (Not `line[:1] in chars`: the empty string is in every string.)"""
    return bool(line) and line[0] in chars


def chart_block(text):
    """The longest fenced block; without one, the whole reply (the fence check fails on its own, and the
    other checks still judge the chart that is there)."""
    blocks = code_blocks(text)
    if blocks:
        return max(blocks, key=len)
    lines = text.splitlines()
    top = next((i for i, l in enumerate(lines) if starts_with(l.strip(), "┌╭╔┏")), None)
    bottom = next((i for i in range(len(lines) - 1, -1, -1) if starts_with(lines[i].strip(), "└╰╚┗")), None)
    if top is not None and bottom is not None and bottom > top:
        return "\n".join(lines[top:bottom + 1])
    return text


def unframe(block):
    """The chart's lines without a frame (if it has one), and whether it had one."""
    lines = [l.rstrip("\n") for l in block.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    framed = bool(lines) and starts_with(lines[0], "┌╭╔┏+") and starts_with(lines[-1], "└╰╚┗+")
    if not framed:
        return lines, False
    inner = []
    for l in lines[1:-1]:
        if l[:1] in "├╠┣+" and set(l[1:-1]) <= set("─═━-"):
            continue  # the rule under the title
        s = l.rstrip()
        if s[:1] in FRAME_LEFT:
            s = s[1:]
        if s[-1:] in FRAME_LEFT:
            s = s[:-1]
        inner.append(s[1:] if s.startswith(" ") else s)
    return inner, True


# --- generic checks ------------------------------------------------------------------------------

def check_block(reply):
    return ("The chart is in a fenced code block (so it stays aligned)", any(b.strip() for b in code_blocks(reply)),
            f"{len(code_blocks(reply))} fenced block(s)")


def check_rectangular(block):
    lines = [l for l in block.splitlines() if l.strip()]
    _, framed = unframe(block)
    if not framed:
        return ("If the chart is framed, every line has the same display width", True, "not framed: n/a")
    widths = sorted({display_width(l) for l in lines})
    return ("If the chart is framed, every line has the same display width", len(widths) == 1, f"line widths: {widths}")


def check_glyphs(block, allow_spark=False, text=""):
    """text: characters the data itself brings (e.g. CJK labels), allowed as they are."""
    allowed = SAFE | WGL4_TEXT | (set(SPARK) if allow_spark else set()) | set(text)
    # letters of any script are text (a title or label in Japanese), not glyphs a chart is drawn with
    bad = sorted({c for c in block if ord(c) > 0xFF and c not in allowed
                  and not unicodedata.category(c).startswith("L")})
    return ("Only font-safe glyphs (ASCII, Latin-1, WGL4 box drawing, shades, half blocks, markers)", not bad,
            f"unsafe: {''.join(bad) or 'none'}")


def check_values_printed(block, values):
    missing = [v for v in values if not re.search(r"(?<![\d.])[-+]?" + re.escape(str(abs(v))) + r"(?![\d])", block)]
    return ("Every value is printed in the chart", not missing, f"missing: {missing}")


# --- bars ----------------------------------------------------------------------------------------

def bar_rows(lines):
    """[(label, bar text)] for lines shaped 'label <separator> bar [value]'."""
    rows = []
    for l in lines:
        m = re.match(r"^\s*(?P<label>[^" + SEPARATORS + r"]*?)\s*[" + SEPARATORS + r"]\s?(?P<rest>.*)$", l)
        if m and m.group("label").strip():
            bar = re.sub(r"\s*[-+]?\$?\d[\d,.]*\s*[%kKmM$]*\s*$", "", m.group("rest"))
            rows.append((m.group("label").strip(), bar))
    return rows


def filled(bar):
    return sum(1 for c in bar if c not in TRACK and c not in SEPARATORS and c not in "+-")


def check_lengths(lengths, values, what):
    """lengths[i] drawn for values[i]: within one cell of round(|v| / max|v| × longest)."""
    top = max(abs(v) for v in values)
    longest = max(lengths) if lengths else 0
    wrong = []
    for n, v in zip(lengths, values):
        want = max(1, round_half_away(abs(v) / top * longest)) if v else 0
        if abs(n - want) > 1:
            wrong.append(f"{v}: drew {n}, want {want}")
    ok = bool(lengths) and len(lengths) == len(values) and longest > 0 and not wrong
    return (f"{what} are proportional to the values (±1 cell of round(v / max × longest))", ok,
            f"drawn {lengths} for {values}; " + ("; ".join(wrong) if wrong else "all within ±1"))


def find_rows(rows, label):
    exact = [bar for lab, bar in rows if lab == label]
    return exact or [bar for lab, bar in rows if re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", lab)]


# --- format-agnostic row reading -------------------------------------------------------------------
# Agents draw bars in many layouts: with or without a separator, values before or after the bar, a
# value axis, an x axis below. These helpers find a row by its label and count the glyphs that draw
# bars, instead of assuming the renderer's own layout.

ASCII_FILLS = set("#@%&$*=")
VERTICALS = set("│|¦┃")


def is_fill(c):
    return "\u2580" <= c <= "\u259f" or c in ASCII_FILLS


def uses_track(text):
    """░ is a track only when denser fills are drawn too; a series drawn in ░ alone is a fill."""
    return any(is_fill(c) and c != "░" for c in text)


def bar_cells(line, start, track):
    """Columns (indices) of bar glyphs in line from start on; numbers are not bars."""
    masked = re.sub(r"[-+]?\$?\d[\d,.]*%?", lambda m: " " * len(m.group()), line)
    return [i for i in range(start, len(masked)) if is_fill(masked[i]) and not (track and masked[i] == "░")]


def label_line(lines, label, after=0):
    """(index, end of the label) of the first line from `after` whose text starts with label."""
    for i in range(after, len(lines)):
        m = re.match(r"^\s*(?:#?\d+[.)]?\s+)?" + re.escape(label) + r"(?!\w)", lines[i])
        if m:
            return i, m.end()
    return None, None


# --- per-eval checks -----------------------------------------------------------------------------

def grade_hbar_ranking(reply, data):
    block = chart_block(reply)
    lines, _ = unframe(block)
    track = uses_track(block)
    lengths, at = [], []
    for lab in data["labels"]:
        i, end = label_line(lines, lab)
        at.append(i)
        lengths.append(len(bar_cells(lines[i], end, track)) if i is not None else 0)
    order = [lab for _, lab in sorted((i, lab) for i, lab in zip(at, data["labels"]) if i is not None)]
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            ("Every row has a bar, in ranking order", order == data["labels"], f"rows: {order}"),
            check_lengths(lengths, data["values"], "Bar lengths"),
            check_values_printed(block, data["values"])]


def grade_hbar_grouped(reply, data):
    block = chart_block(reply)
    lines, _ = unframe(block)
    rows = bar_rows(lines)
    names = list(data["series"])
    glyphs = {n: set() for n in names}
    # a row is "<year> │ bar" under a team heading, or "<team> <year> │ bar": either way the k-th row
    # that names a year belongs to the k-th team
    # decided row by row: ░ behind a denser bar is its track, but a series may be drawn in ░ alone
    per_year = {n: [] for n in names}
    for l in lines:
        for n in names:
            m = re.search(r"(?<!\d)" + n + r"(?!\d)", l)
            if m and bar_cells(l, m.end(), uses_track(l[m.end():])):
                per_year[n].append(l[m.end():])
    lengths = []
    values = []
    for i, _ in enumerate(data["labels"]):
        for n in names:
            bars = per_year[n]
            bar = bars[i] if i < len(bars) else ""
            cells = bar_cells(bar, 0, uses_track(bar))
            lengths.append(len(cells))
            values.append(data["series"][n][i])
            glyphs[n] |= {bar[c] for c in cells}
    named = all(len(per_year[n]) >= len(data["labels"]) for n in names)
    distinct = all(glyphs[n] for n in names) and not (glyphs[names[0]] & glyphs[names[1]])
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            ("Every team has a bar for each year", named, f"rows per year: { {n: len(per_year[n]) for n in names} }"),
            ("The two years can be told apart: every bar row names its year, or the years use different glyphs",
             named or distinct, f"glyphs: { {n: ''.join(sorted(g)) for n, g in glyphs.items()} }"),
            check_lengths(lengths, values, "Bar lengths"),
            check_values_printed(block, [v for s in data["series"].values() for v in s])]


def grade_sparkline(reply, data):
    vals = data["values"]
    runs = re.findall("[" + SPARK + "]{%d,}" % len(vals), reply)
    run = runs[0] if runs else ""
    levels = [SPARK.index(c) for c in run]
    order_ok = len(levels) == len(vals) and all(
        levels[i] <= levels[j] for i in range(len(vals)) for j in range(len(vals)) if vals[i] < vals[j])
    ends_ok = bool(levels) and levels[vals.index(max(vals))] == max(levels) and levels[vals.index(min(vals))] == min(levels)
    return [("A sparkline of eighth-block ticks with one glyph per value", len(run) == len(vals), f"sparkline: {run!r}"),
            ("Higher values never get a lower tick than smaller ones", order_ok, f"levels {levels} for {vals}"),
            ("The maximum gets the tallest tick and the minimum the lowest", ends_ok and max(levels or [0]) == 7 and min(levels or [7]) == 0,
             f"levels {levels}")]


def grade_vbar(reply, data):
    block = chart_block(reply)
    lines, _ = unframe(block)
    label_row = next((i for i, l in enumerate(lines) if all(lab in l for lab in data["labels"])), None)
    heights = []
    if label_row:
        grid = lines[:label_row]
        track = uses_track("\n".join(grid))
        width = max((len(l) for l in grid), default=0)
        counts = [sum(1 for l in grid if x < len(l) and is_fill(l[x]) and not (track and l[x] == "░"))
                  for x in range(width)]
        groups = []
        for x, n in enumerate(counts):
            if n and groups and x == groups[-1][-1] + 1:
                groups[-1].append(x)
            elif n:
                groups.append([x])
        heights = [max(counts[x] for x in g) for g in groups]
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            ("Every quarter is labelled under the bars", label_row is not None, f"label row: {label_row}"),
            check_lengths(heights, data["values"], "Column heights")]


def grade_diverging(reply, data):
    block = chart_block(reply)
    lines, _ = unframe(block)
    track = uses_track(block)
    rows = {}
    for lab in data["labels"]:
        i, end = label_line(lines, lab)
        if i is not None:
            rows[lab] = (lines[i], end)
    # the zero axis: a column holding a vertical line in every row, next to the bars
    axes = None
    for line, end in rows.values():
        cols = {k for k in range(end, len(line)) if line[k] in VERTICALS}
        axes = cols if axes is None else axes & cols
    axis = None
    if axes:
        def touching(k):
            return sum(1 for line, end in rows.values() for c in bar_cells(line, end, track) if abs(c - k) == 1)
        axis = max(sorted(axes), key=touching)
    spans, lengths, sides_ok = {}, [], axis is not None
    for lab, v in zip(data["labels"], data["values"]):
        line, end = rows.get(lab, ("", 0))
        cells = bar_cells(line, end, track)
        spans[lab] = (min(cells), max(cells)) if cells else None
        lengths.append(len(cells))
        if axis is not None and cells:
            sides_ok &= all(c > axis for c in cells) if v > 0 else all(c < axis for c in cells)
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            ("Losses grow left and gains right of one shared zero line", sides_ok and len(rows) == len(data["labels"]),
             f"axis column {axis}; spans {spans}"),
            check_lengths(lengths, data["values"], "Bar lengths"),
            check_values_printed(block, data["values"])]


def grade_line(reply, data):
    block = chart_block(reply)
    vals = data["values"]
    top, bottom = str(max(vals)), str(min(vals))
    lines, _ = unframe(block)
    axis = [m.group(1) for m in (re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[┤|+├]", l) for l in lines) if m]
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            ("The value axis runs from the maximum (14) at the top to the minimum (6) at the bottom",
             bool(axis) and axis[0].rstrip("0").rstrip(".") == top and axis[-1].rstrip("0").rstrip(".") == bottom,
             f"axis labels: {axis}"),
            ("The first and last releases are labelled on the x axis", "v1" in block and "v6" in block,
             f"v1: {'v1' in block}, v6: {'v6' in block}")]


def grade_pie(reply, data):
    block = chart_block(reply)
    total = sum(data["values"])
    wrong = []
    for lab, v in zip(data["labels"], data["values"]):
        pct = v / total * 100
        m = re.search(re.escape(lab) + r"[^\n]{0,40}?(\d+(?:\.\d+)?)\s*%", reply)
        if not m or abs(float(m.group(1)) - pct) > 0.6:
            wrong.append((lab, m.group(1) if m else None, round(pct, 1)))
    lines, _ = unframe(block)
    # a hand-drawn substitute: a 100% stacked bar (one row of segments); a real pie: many rows
    rows = [bar for _, bar in bar_rows(lines)]
    segs = []
    if rows:
        runs = re.findall(r"((.)\2*)", rows[0].strip())
        segs = [len(r[0]) for r in runs if r[1] not in " ,"]
    proportional = False
    if len(segs) == len(data["values"]):
        proportional = all(abs(n - v / total * sum(segs)) <= 1 for n, v in zip(segs, data["values"]))
    pie_rows = sum(1 for l in lines if re.search("[█▓▒░▌▄▐▀#@%&$]{2,}", l))
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            ("Each share is given as a correct percentage (±0.6 points)", not wrong, f"wrong or missing: {wrong}"),
            ("The shares are drawn in proportion: a 100% stacked bar with segments ±1 cell, or a pie of 6+ rows",
             proportional or pie_rows >= 6, f"bar segments {segs}; rows with fills: {pie_rows}")]


# --- the harder set (roadmap 1.6): many bars, a requested frame, CJK labels, stacked negatives, a larger line

def check_framed(block):
    _, framed = unframe(block)
    return ("The chart is inside a box frame, as asked", framed, "framed" if framed else "no frame")


def hbar_lengths(lines, labels, track):
    lengths, at = [], []
    for lab in labels:
        i, end = label_line(lines, lab)
        at.append(i)
        lengths.append(len(bar_cells(lines[i], end, track)) if i is not None else 0)
    return lengths, at


def grade_hbar_many(reply, data):
    block = chart_block(reply)
    lines, _ = unframe(block)
    lengths, at = hbar_lengths(lines, data["labels"], uses_track(block))
    order = [lab for _, lab in sorted((i, lab) for i, lab in zip(at, data["labels"]) if i is not None)]
    return [check_block(reply), check_framed(block), check_rectangular(block), check_glyphs(block),
            ("Every service has a bar, in ranking order", order == data["labels"], f"rows: {order}"),
            check_lengths(lengths, data["values"], "Bar lengths"),
            check_values_printed(block, data["values"])]


def grade_cjk_framed(reply, data):
    block = chart_block(reply)
    lines, _ = unframe(block)
    lengths, at = hbar_lengths(lines, data["labels"], uses_track(block))
    missing = [lab for lab, i in zip(data["labels"], at) if i is None]
    return [check_block(reply), check_framed(block), check_rectangular(block),
            check_glyphs(block, text="".join(data["labels"])),
            ("Every team has a bar, labelled with its Japanese name", not missing, f"missing: {missing}"),
            check_lengths(lengths, data["values"], "Bar lengths"),
            check_values_printed(block, data["values"])]


def glyph_runs(line, cells):
    """Consecutive cells drawn with the same glyph: [(glyph, length)], left to right."""
    runs = []
    for c in cells:
        if runs and line[c] == runs[-1][0] and c == runs[-1][2] + 1:
            runs[-1] = (runs[-1][0], runs[-1][1] + 1, c)
        else:
            runs.append((line[c], 1, c))
    return [(g, n) for g, n, _ in runs]


def row_zero(line, cells):
    """Where zero is in one row: an axis glyph with bar cells on both sides, or, when no glyph marks it
    (the renderer's own stacked bars), the column where the glyph first changes."""
    for k in sorted({c + 1 for c in cells} | {c - 1 for c in cells}):
        if 0 <= k < len(line) and line[k] in VERTICALS and any(c < k for c in cells) and any(c > k for c in cells):
            return k + 1, k
    for i in range(1, len(cells)):
        if line[cells[i]] != line[cells[i - 1]] or cells[i] != cells[i - 1] + 1:
            return cells[i], None
    return None, None


def run_next_to(cells, edge, step):
    """The unbroken run of cells that starts at `edge` (or one column past it) and goes in `step`."""
    have = set(cells)
    k = edge if edge in have else edge + step
    run = []
    while k in have:
        run.append(k)
        k += step
    return sorted(run)


def grade_stacked_negative(reply, data):
    block = chart_block(reply)
    lines, _ = unframe(block)
    names = list(data["series"])
    pos, neg = names[:2], names[2]
    # ░ is a series here when the legend gives it a name, not the track behind a bar
    track = uses_track(block) and not re.search(r"░\s*[=:]?\s*[A-Za-z]", reply)
    zeros, lengths, values, split_ok, found = {}, [], [], True, []
    glyphs = {n: set() for n in names}
    for m, lab in enumerate(data["labels"]):
        i, end = label_line(lines, lab)
        line = lines[i] if i is not None else ""
        cells = bar_cells(line, end, track) if i is not None else []
        z, axis = row_zero(line, cells)
        if i is not None:
            found.append(lab)
        zeros[lab] = z
        left = run_next_to(cells, (axis if axis is not None else z) - 1, -1) if z is not None else []
        right = run_next_to(cells, z, +1) if z is not None else []
        runs = glyph_runs(line, right)
        split_ok &= len(runs) == 2
        segs = [n for _, n in runs] + [0, 0]
        for k, n in enumerate(pos):
            if k < len(runs):
                glyphs[n].add(runs[k][0])
        glyphs[neg] |= {line[c] for c in left}
        lengths += [segs[0], segs[1], len(left)]
        values += [data["series"][pos[0]][m], data["series"][pos[1]][m], data["series"][neg][m]]
    shared = len(found) == len(data["labels"]) and None not in zeros.values() and len(set(zeros.values())) == 1
    sides = all(lengths[k * 3 + 2] > 0 and lengths[k * 3] > 0 for k in range(len(data["labels"])))
    apart = (split_ok and len(glyphs[pos[0]]) == 1 and len(glyphs[pos[1]]) == 1
             and not (glyphs[pos[0]] & glyphs[pos[1]]))
    legend = [n for n in names if n not in reply.lower()]
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            ("Refunds hang left and income stacks right of zero, in every month", sides,
             f"zero per month: {zeros}"),
            ("Every month's zero is at the same column (one shared zero line)", shared, f"zero per month: {zeros}"),
            ("Subscriptions and services are two segments told apart by glyph, the same glyph every month", apart,
             f"glyphs: { {n: ''.join(sorted(g)) for n, g in glyphs.items()} }"),
            check_lengths(lengths, values, "Segment lengths"),
            ("A legend names the three series", not legend, f"missing: {legend}")]


AXIS_ROW = re.compile(r"^\s*(-?\d+(?:\.\d+)?)?\s*[┤|+├│┼]")
NOT_MARKS = set(" ─-·.:┈┄╌'`")


def grade_line_large(reply, data):
    block = chart_block(reply)
    vals = data["values"]
    lines, _ = unframe(block)
    plot = []  # (axis label, the plot part of the row) for every row that carries a value label
    for l in lines:
        m = AXIS_ROW.match(l)
        if m and m.group(1):
            plot.append((m.group(1), l[m.end():]))
    axis = [v for v, _ in plot]
    top, bottom = str(max(vals)), str(min(vals))
    axis_ok = bool(axis) and axis[0].rstrip("0").rstrip(".") == top and axis[-1].rstrip("0").rstrip(".") == bottom
    width = max((len(r) for _, r in plot), default=0)

    def place(row, i):
        """Marks on this plot row, and whether one is near the horizontal position of point i."""
        if not plot or width < 2:
            return False, None
        ks = [k for k, c in enumerate(plot[row][1]) if c not in NOT_MARKS and not c.isdigit()]
        want = i / (len(vals) - 1) * (width - 1)
        return any(abs(k - want) <= 0.15 * width for k in ks), ks
    hi_ok, hi = place(0, vals.index(max(vals)))
    lo_ok, lo = place(-1, vals.index(min(vals)))
    return [check_block(reply), check_rectangular(block), check_glyphs(block),
            (f"The value axis runs from the maximum ({top}) at the top to the minimum ({bottom}) at the bottom",
             axis_ok, f"axis labels: {axis}"),
            ("The plot is about 12 rows tall, as asked (10 or more labelled rows)", len(plot) >= 10,
             f"{len(plot)} labelled rows"),
            ("The peak (d9) is on the top row and the low (d6) on the bottom row, each at its place along x",
             hi_ok and lo_ok, f"top-row marks {hi}, bottom-row marks {lo}, plot width {width}"),
            ("The first and last days are labelled on the x axis", "d1" in block and "d14" in block,
             f"d1: {'d1' in block}, d14: {'d14' in block}")]

CHECKS = {"hand-hbar-ranking": grade_hbar_ranking, "hand-hbar-grouped": grade_hbar_grouped,
          "hand-sparkline": grade_sparkline, "hand-vbar": grade_vbar, "hand-diverging": grade_diverging,
          "hand-line": grade_line, "hand-pie": grade_pie,
          "hand-hbar-many": grade_hbar_many, "hand-cjk-framed": grade_cjk_framed,
          "hand-stacked-negative": grade_stacked_negative, "hand-line-large": grade_line_large}


def grade(reply, eval_name):
    return CHECKS[eval_name](reply, EVALS[eval_name]["data"])


def main(run_dir, eval_name):
    run_dir = Path(run_dir)
    reply_path = run_dir / "outputs" / "reply.md"
    if not reply_path.exists():
        results = [("The agent saved its reply to outputs/reply.md", False, "file missing")]
    else:
        results = grade(reply_path.read_text(encoding="utf-8"), eval_name)
    expectations = [{"text": t, "passed": bool(p), "evidence": e} for t, p, e in results]
    passed = sum(e["passed"] for e in expectations)
    summary = {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations),
               "pass_rate": passed / len(expectations)}
    (run_dir / "grading.json").write_text(json.dumps({"expectations": expectations, "summary": summary}, indent=2,
                                                     ensure_ascii=False), encoding="utf-8")
    print(f"{run_dir.parent.name}/{run_dir.name}: {passed}/{len(expectations)}")
    for e in expectations:
        print(("  PASS " if e["passed"] else "  FAIL ") + e["text"] + "  --  " + str(e["evidence"])[:120])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
