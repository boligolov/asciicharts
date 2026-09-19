"""CSV input: spec_from_csv and the --csv command line."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from asciicharts import ChartError, render_chart, spec_from_csv

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = str(ROOT / "asciicharts.py")

LATENCY = """endpoint,p50,p99,errors
/login,120,480,3
/search,340,1900,12
/checkout,210,950,7
/health,5,9,0
/upload,800,4200,21
"""


def series_values(spec):
    return {s["name"]: s["values"] for s in spec["series"]}


# --- mapping per chart type -----------------------------------------------

def test_bars_use_the_text_column_as_labels_and_numeric_columns_as_series():
    spec = spec_from_csv(LATENCY, "hbar")
    assert spec["labels"] == ["/login", "/search", "/checkout", "/health", "/upload"]
    assert series_values(spec) == {"p50": [120, 340, 210, 5, 800], "p99": [480, 1900, 950, 9, 4200],
                                   "errors": [3, 12, 7, 0, 21]}
    assert render_chart(spec)


def test_values_picks_columns_and_label_picks_the_label_column():
    spec = spec_from_csv(LATENCY, "vbar", label="endpoint", values="p99")
    assert list(series_values(spec)) == ["p99"]
    spec = spec_from_csv(LATENCY, "vbar", label="p50", values="p99,errors")
    assert spec["labels"] == ["120", "340", "210", "5", "800"]
    assert list(series_values(spec)) == ["p99", "errors"]


def test_line_and_area_get_x_axis_labels():
    for chart in ("line", "area", "dotplot"):
        spec = spec_from_csv(LATENCY, chart, values="p99")
        assert spec["labels"][0] == "/login"
        assert render_chart(spec)


def test_sparkline_histogram_boxplot_dual_axis_take_columns_as_series_without_labels():
    for chart, values in (("sparkline", "p50,p99"), ("histogram", "p99"), ("boxplot", "p50,p99"), ("dual_axis", "p50,errors")):
        spec = spec_from_csv(LATENCY, chart, values=values)
        assert "labels" not in spec
        assert [s["name"] for s in spec["series"]] == values.split(",")
        assert render_chart(spec)


def test_pie_makes_one_slice_per_row_from_the_first_value_column():
    spec = spec_from_csv(LATENCY, "pie", values="errors")
    assert [s["name"] for s in spec["series"]] == ["/login", "/search", "/checkout", "/health", "/upload"]
    assert [s["values"] for s in spec["series"]] == [[3], [12], [7], [0], [21]]
    assert render_chart(spec)


def test_heatmap_makes_one_row_per_csv_row_with_columns_as_headers():
    spec = spec_from_csv(LATENCY, "heatmap", values="p50,p99")
    assert spec["labels"] == ["p50", "p99"]
    assert spec["series"][0] == {"name": "/login", "values": [120, 480]}
    assert render_chart(spec)


def test_scatter_uses_the_first_numeric_column_as_x_by_default():
    spec = spec_from_csv(LATENCY, "scatter")
    assert [s["name"] for s in spec["series"]] == ["p99", "errors"]  # x = p50
    assert spec["series"][0]["points"][0] == {"x": 120, "y": 480}
    spec = spec_from_csv(LATENCY, "scatter", label="p99", values="errors")
    assert spec["series"][0]["points"][1] == {"x": 1900, "y": 12}
    assert render_chart(spec)


def test_every_chart_type_works_from_a_csv():
    for chart in ("sparkline", "vbar", "hbar", "line", "area", "scatter", "dual_axis", "pie", "histogram",
                  "heatmap", "boxplot", "dotplot"):
        cols = {"dual_axis": "p50,p99", "histogram": "p99"}.get(chart)  # these need exactly 2 / 1 series
        assert render_chart(spec_from_csv(LATENCY, chart, values=cols)).strip(), chart


# --- sort, limit, options -------------------------------------------------

def test_sort_descending_then_limit_gives_the_top_n():
    for sort in ("-p99", "p99:desc"):
        spec = spec_from_csv(LATENCY, "hbar", values="p99", sort=sort, limit=3)
        assert spec["labels"] == ["/upload", "/search", "/checkout"]
        assert series_values(spec) == {"p99": [4200, 1900, 950]}


def test_sort_ascending_is_the_default_and_text_columns_sort_alphabetically():
    assert spec_from_csv(LATENCY, "hbar", values="p99", sort="p99")["labels"][0] == "/health"
    assert spec_from_csv(LATENCY, "hbar", values="p99", sort="endpoint")["labels"][0] == "/checkout"
    assert spec_from_csv(LATENCY, "hbar", values="p99", sort="endpoint:desc")["labels"][0] == "/upload"


def test_numeric_sort_is_numeric_not_textual():
    csv_text = "name,n\na,9\nb,10\nc,100\nd,2\n"
    assert spec_from_csv(csv_text, "hbar", sort="-n")["labels"] == ["c", "b", "a", "d"]


def test_limit_must_be_positive():
    with pytest.raises(ChartError, match="at least 1"):
        spec_from_csv(LATENCY, "hbar", limit=0)


def test_options_are_merged_and_unknown_ones_rejected():
    spec = spec_from_csv(LATENCY, "hbar", values="p99", options={"title": "Slow", "width": 30, "border": "none"})
    assert (spec["title"], spec["width"], spec["border"]) == ("Slow", 30, "none")
    with pytest.raises(ChartError, match='unknown option "titel"'):
        spec_from_csv(LATENCY, "hbar", options={"titel": "x"})


# --- parsing --------------------------------------------------------------

@pytest.mark.parametrize("delim", [";", "\t", "|"])
def test_other_delimiters_are_detected(delim):
    text = LATENCY.replace(",", delim)
    assert series_values(spec_from_csv(text, "hbar", values="p99")) == {"p99": [480, 1900, 950, 9, 4200]}


def test_decorated_numbers():
    text = 'item,price,share\nA,"$1,200.50",12%\nB,"$980",8.5 %\nC,"1,000",  30%\n'
    spec = spec_from_csv(text, "hbar")
    assert series_values(spec) == {"price": [1200.5, 980, 1000], "share": [12, 8.5, 30]}


def test_decimal_comma_in_a_semicolon_file():
    text = "name;score\na;3,14\nb;2,5\n"
    assert series_values(spec_from_csv(text, "hbar")) == {"score": [3.14, 2.5]}


def test_bom_blank_lines_and_short_rows():
    text = "﻿name,a,b\n\nx,1,2\ny,3\n"
    with pytest.raises(ChartError, match='row 3, column "b" is empty'):
        spec_from_csv(text, "hbar", values="a,b")


def test_all_numeric_csv_has_no_label_column_so_rows_are_numbered_by_the_renderer():
    spec = spec_from_csv("a,b\n1,2\n3,4\n", "hbar", values="b")
    assert "labels" not in spec
    lines = render_chart({**spec, "border": "none"}).splitlines()
    assert lines[0].startswith("1 │") and lines[1].startswith("2 │")


def test_columns_resolve_by_case_insensitive_name_and_by_index():
    assert series_values(spec_from_csv(LATENCY, "hbar", label="ENDPOINT", values="P99"))["p99"][0] == 480
    assert series_values(spec_from_csv(LATENCY, "hbar", label="1", values="3"))["p99"][0] == 480


# --- errors ---------------------------------------------------------------

@pytest.mark.parametrize("text,kwargs,fragment", [
    ("", {}, "empty"),
    ("only,header\n", {}, "at least one data row"),
    (LATENCY, {"values": "latency"}, 'values column "latency" not found; the columns are: endpoint, p50, p99, errors'),
    (LATENCY, {"label": "nope"}, 'label column "nope" not found'),
    (LATENCY, {"sort": "nope"}, 'sort column "nope" not found'),
    ("name,note\na,x\nb,y\n", {}, "no numeric columns to plot"),
    ("k,v\na,1\nb,n/a\n", {"values": "v"}, 'row 3, column "v" is not a number: "n/a"'),
    ("k,v\na,1\nb,\n", {"values": "v"}, 'row 3, column "v" is empty'),
])
def test_helpful_errors(text, kwargs, fragment):
    with pytest.raises(ChartError, match=fragment.replace("(", r"\(").replace(")", r"\)")):
        spec_from_csv(text, "hbar", **kwargs)


def test_unknown_chart_type():
    with pytest.raises(ChartError, match='unknown chartType "pizza"'):
        spec_from_csv(LATENCY, "pizza")


def test_scatter_without_numeric_columns():
    with pytest.raises(ChartError, match="numeric x column"):
        spec_from_csv("a,b\nx,y\n", "scatter")


# --- command line ---------------------------------------------------------

def run(args, stdin=None):
    return subprocess.run([sys.executable, SCRIPT, *args], input=stdin, capture_output=True, encoding="utf-8",
                          env={"PYTHONIOENCODING": "utf-8", "PATH": ""})


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "latency.csv"
    p.write_text(LATENCY, encoding="utf-8")
    return str(p)


def test_cli_renders_from_a_file(csv_file):
    r = run(["--csv", csv_file, "--chart", "hbar", "--values", "p99", "--sort", "-p99", "--limit", "2",
             "--set", "title=Slowest", "--set", "border=none"])
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert lines[0] == "Slowest" and lines[1].startswith("/upload") and lines[2].startswith("/search")


def test_cli_reads_stdin_and_can_print_the_spec():
    r = run(["--csv", "-", "--chart", "sparkline", "--values", "p50", "--print-spec"], stdin=LATENCY)
    assert r.returncode == 0
    assert json.loads(r.stdout) == {"chartType": "sparkline", "series": [{"name": "p50", "values": [120, 340, 210, 5, 800]}]}


def test_cli_set_values_are_json_typed(csv_file):
    r = run(["--csv", csv_file, "--chart", "hbar", "--values", "p50,p99", "--set", "stacked=true", "--set", "width=20",
             "--print-spec"])
    spec = json.loads(r.stdout)
    assert spec["stacked"] is True and spec["width"] == 20


def test_cli_errors_go_to_stderr_with_exit_code_1(csv_file):
    r = run(["--csv", csv_file, "--chart", "hbar", "--values", "latency"])
    assert r.returncode == 1 and r.stdout == "" and 'values column "latency" not found' in r.stderr
    r = run(["--csv", "/no/such/file.csv", "--chart", "hbar"])
    assert r.returncode == 1 and r.stderr.startswith("error:")
    r = run(["--csv", csv_file, "--chart", "hbar", "--set", "noequals"])
    assert r.returncode == 1 and "key=value" in r.stderr


def test_cli_help_mentions_the_flags():
    r = run(["--csv", "x", "--help"])
    assert r.returncode == 0 and all(f in r.stdout for f in ("--chart", "--values", "--sort", "--limit", "--set"))


# --- column matching by prefix / substring --------------------------------

def test_a_unique_prefix_finds_the_column():
    text = "endpoint,p50_ms,p99_ms,error_rate\n/a,1,10,0.1\n/b,2,20,0.2\n"
    assert list(series_values(spec_from_csv(text, "hbar", values="p99"))) == ["p99_ms"]
    assert spec_from_csv(text, "hbar", values="p99", sort="-p99")["labels"] == ["/b", "/a"]
    assert list(series_values(spec_from_csv(text, "hbar", values="err"))) == ["error_rate"]


def test_a_unique_substring_finds_the_column_when_no_prefix_matches():
    text = "endpoint,latency_p99,latency_p50\n/a,10,1\n/b,20,2\n"
    assert list(series_values(spec_from_csv(text, "hbar", values="99"))) == ["latency_p99"]


def test_ambiguous_prefixes_are_an_error_that_lists_the_candidates():
    text = "endpoint,p50_ms,p95_ms,p99_ms\n/a,1,5,10\n"
    with pytest.raises(ChartError, match='values column "p9" is ambiguous; it matches: p95_ms, p99_ms'):
        spec_from_csv(text, "hbar", values="p9")


def test_exact_names_still_win_over_prefixes():
    text = "name,p99,p99_ms\na,1,2\nb,3,4\n"
    assert list(series_values(spec_from_csv(text, "hbar", values="p99"))) == ["p99"]
