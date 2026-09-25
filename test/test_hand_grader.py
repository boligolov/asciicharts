"""The grader of the hand-drawn skill evals is itself right: a perfect reply (the renderer's own chart)
passes every check, and the typical mistakes of a hand-drawn chart fail the check meant to catch them."""

import importlib.util
from pathlib import Path

import pytest

from asciicharts import render_chart

HERE = Path(__file__).resolve().parent / "evals"
spec = importlib.util.spec_from_file_location("hand_grade", HERE / "hand_grade.py")
hand_grade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hand_grade)
DATA = {name: e["data"] for name, e in hand_grade.EVALS.items()}


def fenced(chart, prose="Here it is."):
    return f"{prose}\n\n```\n{chart}\n```\n"


def perfect(name):
    d = DATA[name]
    if name == "hand-hbar-ranking":
        return fenced(render_chart({"chartType": "hbar", "title": "Repos by language", "width": 20,
                                    "labels": d["labels"], "series": [{"values": d["values"]}]}))
    if name == "hand-hbar-grouped":
        return fenced(render_chart({"chartType": "hbar", "border": "none", "width": 16, "labels": d["labels"],
                                    "series": [{"name": n, "values": v} for n, v in d["series"].items()]}))
    if name == "hand-sparkline":
        return "Signups " + render_chart({"chartType": "sparkline", "border": "none",
                                          "series": [{"values": d["values"]}]}) + " — up and to the right.\n"
    if name == "hand-vbar":
        return fenced(render_chart({"chartType": "vbar", "title": "Revenue, $M", "height": 8, "width": 19,
                                    "labels": d["labels"], "series": [{"values": d["values"]}]}))
    if name == "hand-diverging":
        return fenced(render_chart({"chartType": "hbar", "width": 21, "labels": d["labels"],
                                    "series": [{"values": d["values"]}]}))
    if name == "hand-line":
        return fenced(render_chart({"chartType": "line", "height": 6, "width": 21, "labels": d["labels"],
                                    "series": [{"values": d["values"]}]}))
    if name == "hand-pie":
        bar = render_chart({"chartType": "hbar", "stacked": True, "border": "none", "width": 20, "labels": ["share"],
                            "series": [{"name": n, "values": [v]} for n, v in zip(d["labels"], d["values"])]})
        shares = ", ".join(f"{n} {v}%" for n, v in zip(d["labels"], d["values"]))
        return fenced(bar, "A pie is hard to draw in text, so here is a 100% stacked bar: " + shares + ".")
    if name == "hand-hbar-many":
        return fenced(render_chart({"chartType": "hbar", "title": "Open incidents", "width": 20,
                                    "labels": d["labels"], "series": [{"values": d["values"]}]}))
    if name == "hand-cjk-framed":
        return fenced(render_chart({"chartType": "hbar", "width": 20, "labels": d["labels"],
                                    "series": [{"values": d["values"]}]}))
    if name == "hand-stacked-negative":
        return fenced(render_chart({"chartType": "hbar", "stacked": True, "width": 30, "labels": d["labels"],
                                    "series": [{"name": n, "values": v} for n, v in d["series"].items()]}))
    if name == "hand-line-large":
        return fenced(render_chart({"chartType": "line", "height": 12, "width": 40, "labels": d["labels"],
                                    "series": [{"values": d["values"]}]}))
    raise KeyError(name)


def failed(reply, name):
    return [text for text, ok, _ in hand_grade.grade(reply, name) if not ok]


@pytest.mark.parametrize("name", list(DATA))
def test_the_renderers_own_chart_passes_every_check(name):
    assert failed(perfect(name), name) == []


@pytest.mark.parametrize("name", ["hand-hbar-ranking", "hand-hbar-grouped", "hand-vbar", "hand-diverging",
                                  "hand-hbar-many", "hand-stacked-negative"])
def test_correct_charts_in_other_layouts_pass(name):
    """Real replies from the eval baseline, drawn correctly but not in the renderer's layout: no separator,
    ░ as a series, a value axis and values over the columns, the zero axis as the only vertical line.
    An early grader failed all four — it must judge the chart, not its resemblance to ours. From the 1.6 run:
    numbered rows ("1. auth"), and refunds drawn in ░ (a series, named in the legend, not a track) next to
    "40 + 15 − 8 = net 47"."""
    reply = (HERE / "formats" / f"{name}.md").read_text(encoding="utf-8")
    assert failed(reply, name) == []


def test_a_miscounted_bar_is_caught():
    reply = perfect("hand-hbar-ranking").replace("█" * 6 + "░", "█" * 9 + "░", 1)  # Go's 6... bar made longer
    assert any("proportional" in t for t in failed(reply, "hand-hbar-ranking"))


def test_a_ragged_frame_is_caught_by_display_width():
    lines = perfect("hand-hbar-ranking").split("\n")
    i = next(k for k, l in enumerate(lines) if "Rust" in l)
    lines[i] = lines[i].replace("Rust  ", "Rust 東")  # same number of characters, one column wider
    assert any("display width" in t for t in failed("\n".join(lines), "hand-hbar-ranking"))


def test_unsafe_glyphs_are_caught():
    reply = perfect("hand-hbar-ranking").replace("█", "▉")
    assert any("font-safe" in t for t in failed(reply, "hand-hbar-ranking"))


def test_years_that_cannot_be_told_apart_are_caught():
    chart = "\n".join(["Payments │ ████████████ 42", "Payments │ ████████████████ 57", "Search   │ ██████████ 35",
                       "Search   │ █████████ 31", "Mobile   │ █████ 18", "Mobile   │ ████████ 29"])
    assert any("told apart" in t for t in failed(fenced(chart), "hand-hbar-grouped"))


def test_a_sparkline_out_of_order_is_caught():
    reply = perfect("hand-sparkline")
    run = next(w for w in reply.split() if set(w) <= set(hand_grade.SPARK))
    assert failed(reply.replace(run, run[::-1]), "hand-sparkline")


def test_bars_not_sharing_a_zero_line_are_caught():
    chart = "\n".join(["North │ ████████████ 12", "South │ █████ -5", "East  │ ████████ 8", "West  │ █████████ -9"])
    assert any("zero line" in t for t in failed(fenced(chart), "hand-diverging"))


def test_wrong_percentages_are_caught():
    reply = perfect("hand-pie").replace("Chrome 64%", "Chrome 60%")
    assert any("percentage" in t for t in failed(reply, "hand-pie"))


# --- the harder set (roadmap 1.6) ----------------------------------------------------------------

def test_a_missing_frame_is_caught():
    chart = render_chart({"chartType": "hbar", "border": "none", "width": 20, "labels": DATA["hand-hbar-many"]["labels"],
                          "series": [{"values": DATA["hand-hbar-many"]["values"]}]})
    assert any("box frame" in t for t in failed(fenced(chart), "hand-hbar-many"))


def test_cjk_labels_padded_by_characters_not_columns_are_caught():
    """The classic CJK mistake: labels padded to the same number of characters, each CJK one being two
    columns wide, so the frame's right edge is ragged."""
    d = DATA["hand-cjk-framed"]
    rows = [f"│ {lab:<4} │ {'█' * round(v / 48 * 20):<20} {v:<2} │" for lab, v in zip(d["labels"], d["values"])]
    width = len(rows[0])
    chart = chr(10).join(["┌" + "─" * (width - 2) + "┐", *rows, "└" + "─" * (width - 2) + "┘"])
    fails = failed(fenced(chart), "hand-cjk-framed")
    assert any("display width" in t for t in fails) and not any("proportional" in t for t in fails)


def test_stacked_segments_in_one_glyph_are_caught():
    reply = perfect("hand-stacked-negative").replace("▓", "█")
    assert any("told apart" in t for t in failed(reply, "hand-stacked-negative"))


def test_refunds_on_the_wrong_side_are_caught():
    d = DATA["hand-stacked-negative"]
    flipped = {**d["series"], "refunds": [-v for v in d["series"]["refunds"]]}
    chart = render_chart({"chartType": "hbar", "stacked": True, "width": 30, "labels": d["labels"],
                          "series": [{"name": n, "values": v} for n, v in flipped.items()]})
    assert any("zero line" in t for t in failed(fenced(chart), "hand-stacked-negative"))


def test_a_line_too_short_is_caught():
    d = DATA["hand-line-large"]
    chart = render_chart({"chartType": "line", "height": 6, "width": 40, "labels": d["labels"], "series": [{"values": d["values"]}]})
    assert any("12 rows" in t for t in failed(fenced(chart), "hand-line-large"))


def test_a_chart_outside_a_code_block_fails_only_that_check():
    """Without a fence the chart is still graded (a real 1.6 reply): one mistake, not a cascade of zeros."""
    reply = (HERE / "formats" / "hand-hbar-grouped-unfenced.md").read_text(encoding="utf-8")
    assert failed(reply, "hand-hbar-grouped") == ["The chart is in a fenced code block (so it stays aligned)"]


def test_one_misaligned_zero_is_caught_and_the_segments_are_still_judged():
    lines = perfect("hand-stacked-negative").split(chr(10))
    i = next(k for k, l in enumerate(lines) if "Apr" in l)
    lines[i] = lines[i].replace("Apr │ ", "Apr │", 1) + " "  # the whole row one column left
    fails = failed(chr(10).join(lines), "hand-stacked-negative")
    assert any("same column" in t for t in fails) and not any("proportional" in t for t in fails)


def test_a_blank_line_is_not_a_frame_corner():
    """`"" in "┌╭╔┏"` is true in Python, so blank lines once looked like a frame's corners: an unfenced
    reply was cut down to what lay between two of them (a real 1.6 reply lost its chart that way)."""
    fence = "```" + chr(10)
    reply = chr(10) + perfect("hand-pie").replace(fence, "").replace(chr(10) + "```", "") + chr(10) + "The end." + chr(10)
    assert failed(reply, "hand-pie") == ["The chart is in a fenced code block (so it stays aligned)"]

