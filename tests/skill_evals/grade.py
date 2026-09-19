#!/usr/bin/env python3
"""Programmatic grading for the skill evals (see evals.json).

    python tests/skill_evals/grade.py <run_dir> <eval_name>

<run_dir> holds outputs/reply.md, the agent's final reply. Writes grading.json in
the format the skill-creator viewer expects: expectations[] of {text, passed, evidence}.
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
BLOCK_GLYPHS = re.compile("[▀-▟]")


def code_blocks(text):
    return [m.group(1) for m in FENCE.finditer(text)]


def outside_code(text):
    return FENCE.sub("", text)


def chart_block(text):
    """The fenced block most likely to be the chart: the longest one."""
    blocks = code_blocks(text)
    return max(blocks, key=len) if blocks else text


def framed_and_rectangular(block):
    lines = [l for l in block.splitlines() if l.strip()]
    if not lines or lines[0][0] not in "┌╭╔┏+":
        return True, "not framed: n/a"
    widths = {len(l) for l in lines}
    return len(widths) == 1, f"line widths: {sorted(widths)}"


def first_positions(block, needles):
    pos = {}
    for n in needles:
        m = re.search(re.escape(n) + r"(?![\w/])", block)
        if m:
            pos[n] = m.start()
    return pos


def check_top8(reply, run_dir):
    rows = list(csv.DictReader(open(HERE / "api_latency.csv", encoding="utf-8")))
    rows.sort(key=lambda r: -int(r["p99_ms"]))
    top = rows[:8]
    names = [r["endpoint"] for r in top]
    others = [r["endpoint"] for r in rows[8:]]
    block = chart_block(reply)
    out = []
    out.append(("The chart is in a fenced code block (so it stays aligned in markdown)", bool(code_blocks(reply)) and len(block.strip()) > 50,
                f"{len(code_blocks(reply))} fenced block(s), {len(block)} chars in the longest"))
    present = [n for n in names if re.search(re.escape(n) + r"(?![\w/])", block)]
    out.append(("The chart shows all 8 slowest endpoints by p99", len(present) == 8, f"present: {present}"))
    extra = [n for n in others if re.search(re.escape(n) + r"(?![\w/])", block)]
    out.append(("The chart shows no endpoint outside the top 8", not extra, f"extra: {extra}"))
    pos = first_positions(block, names)
    order = [n for n, _ in sorted(pos.items(), key=lambda kv: kv[1])]
    out.append(("Bars are ordered from slowest to fastest p99", order == names, f"order in chart: {order}"))
    missing_vals = [str(r["p99_ms"]) for r in top if not re.search(r"(?<!\d)" + r["p99_ms"] + r"(?!\d)", block)]
    out.append(("Each of the 8 p99 values is printed in the chart", not missing_vals, f"missing: {missing_vals}"))
    prose = outside_code(reply)
    out.append(("A sentence outside the chart says what stands out (mentions the slowest endpoint, /feed)",
                "/feed" in prose and len(prose.strip()) > 30, prose.strip()[:160]))
    ok, ev = framed_and_rectangular(block)
    out.append(("If the chart has a frame, every line has the same width", ok, ev))
    return out


def check_trend(reply, run_dir):
    block = chart_block(reply)
    out = []
    out.append(("The chart is in a fenced code block (so it stays aligned in markdown)", bool(code_blocks(reply)) and len(block.strip()) > 20,
                f"{len(code_blocks(reply))} fenced block(s), {len(block)} chars"))
    both = "12.4" in reply and "21.9" in reply
    out.append(("The lowest (12.4) and highest (21.9) values are visible", both,
                f"12.4 in reply: {'12.4' in reply}, 21.9 in reply: {'21.9' in reply}"))
    months = "Jan" in reply and "Dec" in reply
    out.append(("Months are labelled (Jan ... Dec)", months, f"Jan: {'Jan' in reply}, Dec: {'Dec' in reply}"))
    in_chart = "Jan" in block and "Dec" in block
    out.append(("The chart's own time axis labels the first and last month (Jan ... Dec)", in_chart,
                f"Jan in chart: {'Jan' in block}, Dec in chart: {'Dec' in block}"))
    ok, ev = framed_and_rectangular(block)
    out.append(("If the chart has a frame, every line has the same width", ok, ev))
    images = [p.name for p in (run_dir / "outputs").glob("*") if p.suffix.lower() in (".png", ".svg", ".jpg", ".pdf")]
    out.append(("No image files were produced (plain text was requested)", not images, f"images: {images}"))
    return out


def check_email(reply, run_dir):
    block = chart_block(reply)
    out = []
    out.append(("The reply contains a chart (a fence is not needed in a plain-text email)", len(block.strip()) > 50 and "2024" in block,
                f"{len(block)} chars"))
    bad = sorted(set(BLOCK_GLYPHS.findall(block)))
    out.append(("The chart uses no block or shade characters (font-safe)", not bad and len(block) > 50,
                f"offending glyphs: {''.join(bad) or 'none'}"))
    cats = [c for c in ("Support", "Billing", "Onboarding", "Docs") if c in block]
    out.append(("All four categories appear in the chart", len(cats) == 4, f"found: {cats}"))
    out.append(("Both years are named (2024 and 2025) so the two can be told apart", "2024" in block and "2025" in block,
                f"2024: {'2024' in block}, 2025: {'2025' in block}"))
    vals = ["78", "64", "71", "52", "82", "61", "79", "58"]
    missing = [v for v in vals if not re.search(r"(?<!\d)" + v + r"(?!\d)", block)]
    out.append(("All eight values are printed in the chart", not missing, f"missing: {missing}"))
    # the two series must use different glyphs: in a grouped hbar each category has two bar rows with different fill chars
    fills = set(re.findall(r"[#XHW=:|.@%&$MNDOUSGZ/\\!█▓▒░*+o0-]{4,}", block))
    kinds = {Counter(f).most_common(1)[0][0] for f in fills}
    out.append(("The two years are drawn with different bar characters", len(kinds) >= 2, f"bar fill characters seen: {sorted(kinds)}"))
    ok, ev = framed_and_rectangular(block)
    out.append(("If the chart has a frame, every line has the same width", ok, ev))
    return out


def legend_glyphs(block, names):
    """{'Refunds': 'X', ...} from a legend such as '# Product   X Services   H Refunds'."""
    out = {}
    for n in names:
        m = re.search(r"(\S)\s+" + re.escape(n) + r"(?!\w)", block)
        if m:
            out[n] = m.group(1)
    return out


def check_stacked(reply, run_dir):
    block = chart_block(reply)
    names = ["Product", "Services", "Refunds"]
    lines = [l for l in block.splitlines()]
    out = []
    out.append(("The chart is in a fenced code block (so it stays aligned in markdown)", bool(code_blocks(reply)) and len(block.strip()) > 50,
                f"{len(code_blocks(reply))} fenced block(s)"))
    glyphs = legend_glyphs(block, names)
    out.append(("A legend maps each of the three series to its own distinct symbol",
                len(glyphs) == 3 and len(set(glyphs.values())) == 3, f"legend: {glyphs}"))
    out.append(("All four quarters (Q1 ... Q4) are labelled", all(q in block for q in ("Q1", "Q2", "Q3", "Q4")),
                f"found: {[q for q in ('Q1','Q2','Q3','Q4') if q in block]}"))
    below = False
    ev = "legend missing"
    if len(glyphs) == 3:
        # rows of the plot itself: those above the row that carries the quarter labels
        label_row = next((i for i, l in enumerate(lines) if "Q1" in l and "Q2" in l), len(lines))
        plot = lines[:label_row]
        def rows_with(g):
            return [i for i, l in enumerate(plot) if g in l]
        pos = [i for n in ("Product", "Services") for i in rows_with(glyphs[n])]
        neg = rows_with(glyphs["Refunds"])
        below = bool(pos) and bool(neg) and min(neg) > max(pos) - 0 and min(neg) >= min(pos)
        ev = f"positive-series rows {min(pos) if pos else None}-{max(pos) if pos else None}, refund rows {min(neg) if neg else None}-{max(neg) if neg else None}"
    out.append(("Refunds are drawn below the inflows, growing downward from a shared zero line", below, ev))
    ok, e2 = framed_and_rectangular(block)
    out.append(("If the chart has a frame, every line has the same width", ok, e2))
    return out


def check_pie(reply, run_dir):
    block = chart_block(reply)
    expected = {"North America": 40.4, "Europe": 26.4, "Asia Pacific": 22.1, "Latin America": 5.1, "Oceania": 3.6, "Africa": 2.3}
    excluded = ["Middle East", "Antarctica"]
    out = []
    out.append(("The chart is in a fenced code block (so it stays aligned in markdown)", bool(code_blocks(reply)) and len(block.strip()) > 50,
                f"{len(code_blocks(reply))} fenced block(s)"))
    missing = [r for r in expected if r not in reply]
    out.append(("All six regions with a revenue figure are shown", not missing, f"missing: {missing}"))
    wrong = []
    for region, pct in expected.items():
        m = re.search(re.escape(region) + r"[^\n]{0,40}?(\d+(?:\.\d+)?)\s*%", reply)
        if not m or abs(float(m.group(1)) - pct) > 0.6:
            wrong.append((region, m.group(1) if m else None, pct))
    out.append(("Each region's share of revenue is correct to within 0.6 points", not wrong, f"wrong or missing percentages: {wrong}"))
    present = [r for r in excluded if r in block]
    out.append(("Regions with no revenue value (Middle East, Antarctica Research) are left out of the chart", not present, f"present: {present}"))
    rows = [l for l in block.splitlines() if l.strip()]
    out.append(("The chart is a pie: at least 8 rows tall with a legend", len(rows) >= 10, f"{len(rows)} non-empty lines"))
    ok, e2 = framed_and_rectangular(block)
    out.append(("If the chart has a frame, every line has the same width", ok, e2))
    return out


CHECKS = {"top8-p99-from-csv": check_top8, "monthly-trend-readme": check_trend, "plain-text-email-survey": check_email,
          "stacked-refunds-neg": check_stacked, "messy-csv-pie": check_pie}


def main(run_dir, eval_name):
    run_dir = Path(run_dir)
    reply_path = run_dir / "outputs" / "reply.md"
    if not reply_path.exists():
        results = [("The agent saved its reply to outputs/reply.md", False, "file missing")]
    else:
        results = CHECKS[eval_name](reply_path.read_text(encoding="utf-8"), run_dir)
    expectations = [{"text": t, "passed": bool(p), "evidence": e} for t, p, e in results]
    passed = sum(e["passed"] for e in expectations)
    summary = {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations),
               "pass_rate": passed / len(expectations)}
    (run_dir / "grading.json").write_text(json.dumps({"expectations": expectations, "summary": summary}, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    print(f"{run_dir.parent.name}/{run_dir.name}: {passed}/{len(expectations)}")
    for e in expectations:
        print(("  PASS " if e["passed"] else "  FAIL ") + e["text"] + "  --  " + e["evidence"][:110])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
