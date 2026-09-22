"""ExCSV input (#chart): https://github.com/boligolov/excsv, docs/charts.md.

Parses enough of the format — the #!excsv header, #column, #chart — to resolve a chart
suggestion into a render_chart spec, per that repo's own asciicharts mapping table. Not a full
ExCSV implementation: no sidecar/zip/pack, #@/#$/#%, checksum=, computed columns, or JSON form.

`tests/golden/excsv_fixtures/` holds the #chart-related fixtures copied verbatim (CC0) from that
repo's own shared fixture corpus (`fixtures/plain/{valid,invalid}/*chart*.excsv`); the
expectations below (chart counts/types/engines, warnings, error_kind) are adapted from that
repo's `fixtures/fixtures.yaml`, so this is checked against the format's own ground truth.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from asciicharts import (
    ChartError, list_excsv_charts, parse_excsv, render_chart, resolve_excsv_chart, spec_from_excsv,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "golden" / "excsv_fixtures"
SCRIPT = str(ROOT / "asciicharts.py")


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def run(args, stdin=None):
    return subprocess.run([sys.executable, SCRIPT, *args], input=stdin, capture_output=True,
                          encoding="utf-8", env={"PYTHONIOENCODING": "utf-8", "PATH": ""})


# --- the format's own fixtures --------------------------------------------

VALID = {
    "valid_071_chart_bar.excsv": {"count": 1, "types": ["bar"]},
    "valid_072_chart_arc_multiple.excsv": {"count": 2, "types": ["arc", "arc"]},
    "valid_073_chart_all_marks.excsv": {"count": 11, "types": ["line", "area", "sparkline", "point", "point",
                                                                "circle", "tick", "text", "bar", "rect", "boxplot"]},
    "valid_074_chart_vega_escape.excsv": {"count": 1, "engines": ["vega"]},
    "valid_075_chart_unknown_type_warn.excsv": {"count": 1, "warnings": ["chart_unknown_type"]},
    "valid_076_chart_unknown_channel_warn.excsv": {"count": 1, "types": ["bar"], "warnings": ["chart_unknown_channel"]},
    "valid_077_chart_duplicate_name_warn.excsv": {"count": 2, "types": ["bar", "arc"], "warnings": ["chart_duplicate_name"]},
}


@pytest.mark.parametrize("name,expect", VALID.items())
def test_official_valid_fixtures_parse_as_the_spec_says(name, expect):
    doc = parse_excsv(fixture(name))
    compact = [c for c in doc["charts"] if c["kind"] == "compact"]
    vega = [c for c in doc["charts"] if c["kind"] == "vega"]
    assert len(doc["charts"]) == expect["count"]
    if "types" in expect:
        assert [c["type"] for c in compact] == expect["types"]
    if "engines" in expect:
        assert [c["engine"] for c in vega] == expect["engines"]
    for code in expect.get("warnings", []):
        assert any(code in w for w in doc["warnings"]), (code, doc["warnings"])
    if not expect.get("warnings"):
        assert doc["warnings"] == []


OFFICIAL_INVALID = {
    "invalid_040_chart_unknown_column.excsv": "chart_unknown_column",
    "invalid_041_chart_missing_required_channel.excsv": "chart_missing_required_channel",
    "invalid_042_chart_vega_invalid_json.excsv": "chart_vega_invalid_json",
    "invalid_043_chart_missing_name.excsv": "chart_missing_name",
    "invalid_044_chart_missing_type.excsv": "chart_missing_type",
}


@pytest.mark.parametrize("name,code", OFFICIAL_INVALID.items())
def test_official_invalid_fixtures_fail_with_the_documented_error_kind(name, code):
    with pytest.raises(ChartError, match=code):
        doc = parse_excsv(fixture(name))
        resolve_excsv_chart(doc)


def test_bar_fixture_renders_a_sensible_chart():
    """071: widgets appears twice (120 + 80) — the aggregate, not a stray extra bar, is what
    must show up. sort=desc limit=10 ranks by the aggregated total."""
    spec = resolve_excsv_chart(parse_excsv(fixture("valid_071_chart_bar.excsv")))
    assert spec["chartType"] == "vbar"
    assert dict(zip(spec["labels"], spec["series"][0]["values"])) == {
        "gadgets": 300.5, "widgets": 200.0, "gizmos": 45.0}
    assert spec["labels"] == ["gadgets", "widgets", "gizmos"]  # ranked by value, descending
    assert spec["title"] == "Top categories by spend"
    assert render_chart(spec)


def test_arc_fixture_renders_a_pie_with_correct_percentages():
    doc = parse_excsv(fixture("valid_072_chart_arc_multiple.excsv"))
    spec = resolve_excsv_chart(doc, "spend_by_category")
    assert spec["chartType"] == "pie" and spec["title"] == "Spend by category"
    assert {s["name"]: s["values"][0] for s in spec["series"]} == {"widgets": 120.0, "gadgets": 300.5, "gizmos": 45.0}
    out = render_chart(spec)
    assert "64.6%" in out  # 300.50 / 465.50


def test_all_marks_fixture_every_implemented_mark_renders():
    doc = parse_excsv(fixture("valid_073_chart_all_marks.excsv"))
    expected = {
        "amount_over_time": "line", "amount_area": "area", "amount_trend": "sparkline",
        "amount_vs_discount": "scatter",         # point, both channels
        "amount_distribution": "dotplot",        # point, one channel
        "amount_vs_discount_circle": "scatter",
        "amount_histogram": "histogram", "amount_by_category_over_time": "heatmap",
        "amount_by_category": "boxplot",
    }
    for name, chart_type in expected.items():
        spec = resolve_excsv_chart(doc, name)
        assert spec["chartType"] == chart_type, name
        assert render_chart(spec)
    for name in ("amount_ticks", "category_labels"):  # tick, text: no asciicharts equivalent
        with pytest.raises(ChartError, match="no asciicharts equivalent"):
            resolve_excsv_chart(doc, name)


def test_vega_escape_is_recognized_but_not_renderable():
    doc = parse_excsv(fixture("valid_074_chart_vega_escape.excsv"))
    assert doc["charts"][0]["parsed"]["mark"] == "arc"
    with pytest.raises(ChartError, match="no ASCII renderer"):
        resolve_excsv_chart(doc)


def test_unknown_type_warns_but_is_not_a_parse_failure_and_the_renderer_declines_cleanly():
    doc = parse_excsv(fixture("valid_075_chart_unknown_type_warn.excsv"))
    assert doc["charts"]  # parsed fine, unlike the FAIL-severity cases
    with pytest.raises(ChartError, match="no asciicharts equivalent"):
        resolve_excsv_chart(doc)


def test_unknown_channel_warns_but_still_renders():
    doc = parse_excsv(fixture("valid_076_chart_unknown_channel_warn.excsv"))
    assert render_chart(resolve_excsv_chart(doc))


def test_duplicate_name_warns_and_the_later_line_wins_for_addressing():
    doc = parse_excsv(fixture("valid_077_chart_duplicate_name_warn.excsv"))
    assert resolve_excsv_chart(doc, "amount_by_category")["chartType"] == "pie"  # the arc, not the bar


# --- parsing ----------------------------------------------------------------

def test_non_excsv_text_is_rejected_by_parse_excsv():
    with pytest.raises(ChartError, match="not an ExCSV file"):
        parse_excsv("a,b\n1,2\n")


def test_header_only_stub_has_no_data_section():
    doc = parse_excsv("#!excsv version=0.5 rows=0\n")
    assert doc["data_text"] == ""


def test_human_comments_and_unknown_meta_lines_are_ignored():
    doc = parse_excsv(
        "#!excsv version=0.5 header=1 rows=1\n"
        "## a note to a human, not a parser\n"
        "#@source: somewhere\n"
        "#% sum: ,1\n"
        "#column name=a type=int\n"
        "#chart type=sparkline name=s y=a\n"
        "a\n1\n"
    )
    assert doc["warnings"] == []
    assert list(doc["columns"]) == ["a"]


def test_quoted_values_with_escaped_quotes_and_embedded_spaces():
    doc = parse_excsv(
        '#!excsv version=0.5 header=1 rows=1\n'
        '#column name=a type=int\n'
        '#chart type=sparkline name=s y=a title="say ""hi"" to spaces"\n'
        'a\n1\n'
    )
    assert doc["charts"][0]["attrs"]["title"] == 'say "hi" to spaces'


def test_crlf_line_endings_and_a_bom_are_both_accepted():
    text = "﻿#!excsv version=0.5 header=1 rows=1\r\n#column name=a type=int\r\n" \
           "#chart type=sparkline name=s y=a\r\na\r\n1\r\n"
    spec = resolve_excsv_chart(parse_excsv(text))
    assert spec == {"chartType": "sparkline", "series": [{"values": [1.0]}]}


# --- dialect ------------------------------------------------------------

def test_semicolon_delimiter_and_decimal_comma():
    doc = parse_excsv(
        "#!excsv version=0.5 delim=semicolon header=1 rows=2\n"
        "#column name=category type=string role=dimension\n"
        "#column name=amount type=decimal role=measure agg=sum\n"
        "#chart type=bar name=b x=category y=amount\n"
        "category;amount\na;10,5\nb;20,25\n"
    )
    spec = resolve_excsv_chart(doc)
    assert dict(zip(spec["labels"], spec["series"][0]["values"])) == {"a": 10.5, "b": 20.25}


def test_null_marker_excludes_the_value_from_aggregation():
    doc = parse_excsv(
        "#!excsv version=0.5 header=1 rows=3 null=NA\n"
        "#column name=category type=string role=dimension\n"
        "#column name=amount type=decimal role=measure agg=sum\n"
        "#chart type=bar name=b x=category y=amount\n"
        "category,amount\na,10\nb,NA\na,5\n"
    )
    spec = resolve_excsv_chart(doc)
    assert dict(zip(spec["labels"], spec["series"][0]["values"])) == {"a": 15.0, "b": 0.0}


def test_multi_character_delimiter_is_a_clear_unsupported_error():
    doc = parse_excsv(
        "#!excsv version=0.5 delim=:: header=1 rows=1\n"
        "#column name=a type=string role=dimension\n#column name=b type=int role=measure\n"
        "#chart type=bar name=c x=a y=b\na::b\nx::1\n"
    )
    with pytest.raises(ChartError, match="multi-character delimiters"):
        resolve_excsv_chart(doc)


def test_header_0_resolves_columns_by_declared_index():
    doc = parse_excsv(
        "#!excsv version=0.5 header=0 rows=2\n"
        "#column name=category type=string index=0\n"
        "#column name=amount type=decimal role=measure index=1\n"
        "#chart type=bar name=b x=category y=amount\n"
        "widgets,120\ngadgets,300.5\n"
    )
    spec = resolve_excsv_chart(doc)
    assert dict(zip(spec["labels"], spec["series"][0]["values"])) == {"widgets": 120.0, "gadgets": 300.5}


# --- marks and modifiers, beyond the official fixtures --------------------

def _doc(header_extra, columns, chart_line, csv_body):
    text = f"#!excsv version=0.5 header=1 rows={csv_body.count(chr(10))} {header_extra}\n"
    text += "".join(f"#column {c}\n" for c in columns)
    text += f"#chart {chart_line}\n{csv_body}"
    return parse_excsv(text)


def test_bar_orientation_follows_which_side_the_dimension_is_on():
    v = resolve_excsv_chart(_doc("", ["name=cat type=string role=dimension", "name=n type=int role=measure"],
                                 "type=bar name=c x=cat y=n", "cat,n\na,1\nb,2\n"))
    assert v["chartType"] == "vbar"
    h = resolve_excsv_chart(_doc("", ["name=cat type=string role=dimension", "name=n type=int role=measure"],
                                 "type=bar name=c x=n y=cat", "cat,n\na,1\nb,2\n"))
    assert h["chartType"] == "hbar"


def test_bar_with_color_groups_into_one_series_per_color_and_stack_1_sets_stacked():
    spec = resolve_excsv_chart(_doc(
        "", ["name=region type=string role=dimension", "name=product type=string role=dimension",
             "name=amount type=decimal role=measure agg=sum"],
        "type=bar name=g x=region y=amount color=product stack=1",
        "region,product,amount\nEMEA,widgets,40\nEMEA,gadgets,15\nAPAC,widgets,25\n"))
    assert spec["stacked"] is True
    assert spec["labels"] == ["EMEA", "APAC"]
    assert {s["name"]: s["values"] for s in spec["series"]} == {"widgets": [40.0, 25.0], "gadgets": [15.0, 0.0]}


def test_bar_y_count_without_bin_counts_rows_per_category():
    spec = resolve_excsv_chart(_doc(
        "", ["name=cat type=string role=dimension"], "type=bar name=c x=cat y=count()",
        "cat\na\na\nb\n"))
    assert dict(zip(spec["labels"], spec["series"][0]["values"])) == {"a": 2.0, "b": 1.0}


def test_bar_bin_and_y_count_makes_a_histogram():
    spec = resolve_excsv_chart(_doc(
        "", ["name=amount type=decimal role=measure"], "type=bar name=h bin=3 x=amount y=count()",
        "amount\n10\n12\n30\n32\n55\n58\n"))
    assert spec["chartType"] == "histogram" and spec["bins"] == 3
    assert spec["series"][0]["values"] == [10.0, 12.0, 30.0, 32.0, 55.0, 58.0]


def test_aggregate_override_beats_the_columns_own_agg():
    spec = resolve_excsv_chart(_doc(
        "", ["name=cat type=string role=dimension", "name=n type=int role=measure agg=sum"],
        "type=bar name=c x=cat y=n aggregate=max", "cat,n\na,3\na,9\na,1\n"))
    assert spec["series"][0]["values"] == [9.0]


def test_count_distinct_aggregate():
    spec = resolve_excsv_chart(_doc(
        "", ["name=cat type=string role=dimension", "name=cust type=string role=id"],
        "type=bar name=c x=cat y=cust aggregate=count_distinct",
        "cat,cust\na,c1\na,c1\na,c2\nb,c3\n"))
    assert dict(zip(spec["labels"], spec["series"][0]["values"])) == {"a": 2.0, "b": 1.0}


def test_line_sorts_by_category_not_value_so_a_trend_is_not_scrambled():
    spec = resolve_excsv_chart(_doc(
        "", ["name=day type=string role=dimension", "name=n type=int role=measure"],
        "type=line name=t x=day y=n sort=asc", "day,n\nc,1\na,9\nb,4\n"))
    assert spec["labels"] == ["a", "b", "c"]  # alphabetical, not ranked by n


def test_line_with_color_pivots_into_one_series_per_color_filling_gaps_with_zero():
    spec = resolve_excsv_chart(_doc(
        "", ["name=day type=string role=dimension", "name=who type=string role=dimension",
             "name=n type=int role=measure"],
        "type=line name=t x=day y=n color=who",
        "day,who,n\nmon,a,1\nmon,b,2\ntue,a,3\n"))  # (tue, b) never occurs
    by_name = {s["name"]: s["values"] for s in spec["series"]}
    assert spec["labels"] == ["mon", "tue"]
    assert by_name == {"a": [1.0, 3.0], "b": [2.0, 0.0]}


def test_area_stack_1_sets_stacked_but_line_ignores_stack():
    area = resolve_excsv_chart(_doc(
        "", ["name=day type=string role=dimension", "name=who type=string role=dimension",
             "name=n type=int role=measure"],
        "type=area name=t x=day y=n color=who stack=1", "day,who,n\na,x,1\na,y,2\n"))
    assert area.get("stacked") is True
    line = resolve_excsv_chart(_doc(
        "", ["name=day type=string role=dimension", "name=who type=string role=dimension",
             "name=n type=int role=measure"],
        "type=line name=t x=day y=n color=who stack=1", "day,who,n\na,x,1\na,y,2\n"))
    assert "stacked" not in line


def test_scatter_needs_both_axes_and_groups_by_color():
    spec = resolve_excsv_chart(_doc(
        "", ["name=x type=decimal role=measure", "name=y type=decimal role=measure",
             "name=g type=string role=dimension"],
        "type=point name=p x=x y=y color=g", "x,y,g\n1,2,a\n3,4,b\n"))
    assert spec["chartType"] == "scatter"
    assert {s["name"] for s in spec["series"]} == {"a", "b"}


def test_scatter_one_axis_only_is_a_dotplot_of_row_values():
    spec = resolve_excsv_chart(_doc(
        "", ["name=x type=decimal role=measure"], "type=point name=p x=x", "x\n3\n1\n2\n"))
    assert spec["chartType"] == "dotplot"
    assert spec["series"][0]["values"] == [3.0, 1.0, 2.0]
    assert spec["labels"] == ["1", "2", "3"]


def test_point_or_circle_needs_at_least_one_axis():
    doc = _doc("", ["name=g type=string role=dimension"], "type=point name=p color=g", "g\na\n")
    with pytest.raises(ChartError, match="chart_missing_required_channel"):
        resolve_excsv_chart(doc)


def test_arc_slice_prefers_color_then_x_then_y():
    spec = resolve_excsv_chart(_doc(
        "", ["name=cat type=string role=dimension", "name=amount type=decimal role=measure"],
        "type=arc name=p theta=amount color=cat", "cat,amount\na,1\nb,2\n"))
    assert {s["name"] for s in spec["series"]} == {"a", "b"}


def test_arc_with_no_slice_column_makes_one_slice_per_row():
    spec = resolve_excsv_chart(_doc(
        "", ["name=amount type=decimal role=measure"], "type=arc name=p theta=amount", "amount\n5\n7\n"))
    assert [s["values"][0] for s in spec["series"]] == [5.0, 7.0]


def test_rect_builds_a_heatmap_matrix_aggregated_per_cell():
    spec = resolve_excsv_chart(_doc(
        "", ["name=day type=string role=dimension", "name=hour type=string role=dimension",
             "name=n type=int role=measure agg=avg"],
        "type=rect name=r x=day y=hour color=n aggregate=avg",
        "day,hour,n\nmon,9am,10\nmon,9am,20\ntue,9am,5\n"))
    assert spec["chartType"] == "heatmap"
    assert spec["labels"] == ["mon", "tue"]
    row = next(s for s in spec["series"] if s["name"] == "9am")
    assert row["values"] == [15.0, 5.0]  # avg(10, 20), 5


def test_boxplot_groups_raw_samples_per_category_not_aggregated_to_one_number():
    spec = resolve_excsv_chart(_doc(
        "", ["name=cat type=string role=dimension", "name=n type=decimal role=measure"],
        "type=boxplot name=b x=cat y=n", "cat,n\na,1\na,2\na,3\nb,10\n"))
    assert {s["name"]: sorted(s["values"]) for s in spec["series"]} == {"a": [1.0, 2.0, 3.0], "b": [10.0]}


def test_sparkline_ignores_x_if_given():
    spec = resolve_excsv_chart(_doc(
        "", ["name=day type=string role=dimension", "name=n type=int role=measure"],
        "type=sparkline name=s x=day y=n", "day,n\na,1\nb,3\nc,2\n"))
    assert spec == {"chartType": "sparkline", "series": [{"values": [1.0, 3.0, 2.0]}]}


def test_role_inferred_from_numeric_type_when_role_is_not_declared():
    # no role= at all: numeric column -> measure, text column -> dimension (same rule --chart's
    # own CSV-guessing heuristic uses, just sourced from #column type= instead of sniffing)
    spec = resolve_excsv_chart(_doc(
        "", ["name=cat type=string", "name=n type=int"], "type=bar name=c x=cat y=n", "cat,n\na,1\nb,2\n"))
    assert spec["chartType"] == "vbar"


# --- errors -----------------------------------------------------------------

def test_channel_referencing_a_column_without_a_column_declaration_fails():
    doc = _doc("", ["name=cat type=string role=dimension"], "type=bar name=c x=cat y=amount", "cat,amount\na,1\n")
    with pytest.raises(ChartError, match="chart_unknown_column"):
        resolve_excsv_chart(doc)


def test_channel_referencing_a_column_missing_from_the_data_section_fails():
    doc = _doc("", ["name=cat type=string role=dimension", "name=n type=int role=measure"],
              "type=bar name=c x=cat y=n", "cat\na\nb\n")  # header row has no "n" column
    with pytest.raises(ChartError, match='"n"'):
        resolve_excsv_chart(doc)


def test_resolving_by_a_name_that_does_not_exist_lists_the_available_ones():
    doc = parse_excsv(fixture("valid_072_chart_arc_multiple.excsv"))
    with pytest.raises(ChartError, match="spend_by_category, spend_by_category_donut"):
        resolve_excsv_chart(doc, "nope")


def test_a_file_with_no_chart_suggestions_at_all_is_a_clear_error():
    doc = parse_excsv("#!excsv version=0.5 header=1 rows=1\n#column name=a type=int\na\n1\n")
    with pytest.raises(ChartError, match="no #chart suggestions"):
        resolve_excsv_chart(doc)


def test_several_suggestions_with_no_name_given_lists_all_of_them():
    doc = parse_excsv(fixture("valid_073_chart_all_marks.excsv"))
    with pytest.raises(ChartError, match="suggests 11 charts"):
        resolve_excsv_chart(doc)


# --- spec_from_excsv / list_excsv_charts (library API) ----------------------

def test_spec_from_excsv_applies_set_style_options_on_top():
    spec = spec_from_excsv(fixture("valid_071_chart_bar.excsv"), options={"border": "none", "width": 30})
    assert spec["border"] == "none" and spec["width"] == 30
    assert spec["title"] == "Top categories by spend"  # untouched: not overridden


def test_spec_from_excsv_rejects_an_unknown_option():
    with pytest.raises(ChartError, match="unknown option"):
        spec_from_excsv(fixture("valid_071_chart_bar.excsv"), options={"nope": 1})


def test_list_excsv_charts_matches_parse_excsv_and_includes_vega_entries():
    charts = list_excsv_charts(fixture("valid_074_chart_vega_escape.excsv"))
    assert charts == [{"name": None, "type": "chart-vega", "title": None}]
    charts = list_excsv_charts(fixture("valid_072_chart_arc_multiple.excsv"))
    assert [c["name"] for c in charts] == ["spend_by_category", "spend_by_category_donut"]
    assert charts[0]["title"] == "Spend by category"


# --- CLI ----------------------------------------------------------------

def test_cli_auto_picks_the_files_only_chart():
    r = run(["--csv", str(FIXTURES / "valid_071_chart_bar.excsv")])
    assert r.returncode == 0 and "Top categories by spend" in r.stdout


def test_cli_list_charts():
    r = run(["--csv", str(FIXTURES / "valid_072_chart_arc_multiple.excsv"), "--list-charts"])
    assert r.returncode == 0
    assert 'spend_by_category  type=arc — "Spend by category"' in r.stdout
    assert "spend_by_category_donut  type=arc" in r.stdout


def test_cli_list_charts_needs_an_excsv_file():
    r = run(["--csv", "-", "--list-charts"], stdin="a,b\n1,2\n")
    assert r.returncode == 1 and "--list-charts needs an ExCSV file" in r.stderr


def test_cli_chart_name_selects_one_of_several():
    r = run(["--csv", str(FIXTURES / "valid_072_chart_arc_multiple.excsv"), "--chart-name",
             "spend_by_category_donut", "--print-spec"])
    assert r.returncode == 0
    assert json.loads(r.stdout)["series"]  # a real, non-empty spec


def test_cli_ambiguous_auto_pick_names_the_choices():
    r = run(["--csv", str(FIXTURES / "valid_072_chart_arc_multiple.excsv")])
    assert r.returncode == 1 and "spend_by_category, spend_by_category_donut" in r.stderr


def test_cli_chart_and_chart_name_together_is_rejected():
    r = run(["--csv", str(FIXTURES / "valid_071_chart_bar.excsv"), "--chart", "hbar",
             "--chart-name", "top_categories"])
    assert r.returncode == 1 and "mutually exclusive" in r.stderr


def test_cli_manual_chart_on_an_excsv_file_uses_role_hints_and_ignores_chart_suggestions():
    r = run(["--csv", str(FIXTURES / "valid_071_chart_bar.excsv"), "--chart", "hbar",
             "--print-spec"])
    assert r.returncode == 0
    spec = json.loads(r.stdout)
    assert spec["chartType"] == "hbar"
    assert "title" not in spec  # the #chart suggestion's title= is not used in manual mode
    assert spec["labels"] == ["widgets", "gadgets", "gizmos", "widgets"]  # raw rows, not aggregated


def test_cli_plain_csv_still_requires_chart():
    r = run(["--csv", "-"], stdin="a,b\n1,2\n3,4\n")
    assert r.returncode == 1 and "--chart TYPE is required" in r.stderr


def test_cli_stdin_excsv():
    r = run(["--csv", "-", "--chart-name", "top_categories"], stdin=fixture("valid_071_chart_bar.excsv"))
    assert r.returncode == 0 and "gadgets" in r.stdout


def test_cli_print_spec_on_an_excsv_chart():
    r = run(["--csv", str(FIXTURES / "valid_071_chart_bar.excsv"), "--print-spec"])
    spec = json.loads(r.stdout)
    assert spec["chartType"] == "vbar" and spec["title"] == "Top categories by spend"
