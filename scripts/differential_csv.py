#!/usr/bin/env python3
"""Differential test of the Go CSV reader against the Python reference, on random CSV files.

Python generates N random CSV texts — every delimiter, quoting, blank lines, BOMs, CRLF, decorated
numbers ("1,234.5", "3,14", "$5", "12%", "1_000", non-breaking spaces), text in several scripts — and
random --label/--values/--sort/--limit/--set choices; it builds the spec with spec_from_csv (or the
error), prints it as --print-spec does, renders it, and runs the Go test TestCSVDifferential on the
result. Any byte difference is a divergence.

    python scripts/differential_csv.py            # 3000 files, seed 1
    python scripts/differential_csv.py 20000 7    # N files, seed
"""
import csv
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
from asciicharts import CHART_TYPES, ChartError, _parse_set, render_chart, spec_from_csv  # noqa: E402

NAMES = ["region", "Region", "p99_ms", "p99", "p50_ms", "latency", "Latency ms", "東京", "été", "ΟΔΟΣ",
         "count", "a,b", 'say "hi"', "", "  padded  ", "x", "1", "2", "İstanbul", "Σ"]
TEXTS = ["north", "South", "東京", "🍕", "été", "a;b", "x|y", "tab\there", 'q"uote', "line\nbreak", "", " ",
         "b", "B", "zeta", "Ω", "10", "n/a", "-", "ΟΔΟΣ"]


def number_cell(rng, delim):
    v = rng.choice([0, 1, -3, 42, 1234.5, -0.5, 1e15, 3.14159, 1234567, 7])
    style = rng.random()
    if style < 0.5:
        return str(v)
    if style < 0.97:  # decorated, still numbers
        return rng.choice([f"{v:,}", f"${v}", f"€{v}", f"{v}%", f" {v} ", f"{v}\u00a0", "1_000", "-0", "+5",
                           ".5", "5.", "1e3", "１２", "1,234", "12,345.67", f"£{v}%", str(v).replace(".", ",")])
    return rng.choice(["inf", "nan", "1e400", "0x10", "1__0", "3,14", "n/a", "-"])


def cell(rng, kind, delim):
    if rng.random() < 0.02:
        return rng.choice(["", " "])
    if kind == "num":
        return number_cell(rng, delim)
    return rng.choice(TEXTS)


def encode(value, delim, rng):
    must = any(ch in value for ch in (delim, '"', "\n", "\r")) or (value.startswith(" ") and rng.random() < 0.5)
    if must or rng.random() < 0.1:
        return '"' + value.replace('"', '""') + '"'
    return value


def rand_csv(rng):
    delim = rng.choice([",", ",", ";", "\t", "|"])
    ncols = rng.randint(1, 5)
    header = [rng.choice(NAMES) for _ in range(ncols)]
    kinds = [rng.choice(["num", "num", "text"]) for _ in range(ncols)]
    lines = [delim.join(encode(h, delim, rng) for h in header)]
    for _ in range(rng.randint(0, 12) if rng.random() < 0.05 else rng.randint(2, 12)):
        row = [encode(cell(rng, k, delim), delim, rng) for k in kinds]
        if rng.random() < 0.05:
            row = row[:rng.randint(0, len(row))]
        if rng.random() < 0.03:
            row.append("extra")
        lines.append(delim.join(row))
        if rng.random() < 0.05:
            lines.append("")
    eol = rng.choice(["\n", "\n", "\r\n"])
    text = eol.join(lines) + rng.choice(["", eol])
    r = rng.random()
    if r < 0.03:
        text = "\ufeff" + text
    elif r < 0.05:
        text = text + '\n"unterminated,1'
    elif r < 0.06:
        text = "a,b\r1,2\n"
    elif r < 0.07:
        text = rng.choice(["", "   \n", "only_header\n", "'a','b'\n'1','2'\n", "x\n1\n2\n3\n"])
    return text, header


def ref(rng, header):
    r = rng.random()
    h = rng.choice(header) if header else "x"
    if r < 0.7:
        return h
    if r < 0.75:
        return h.upper()
    if r < 0.8:
        return h[:2]
    if r < 0.85:
        return str(rng.randint(0, len(header) + 1))
    if r < 0.9:
        return h[1:3]
    return rng.choice(["nope", "p", "", " ", "A", "東", "σ"])


def rand_case(rng):
    text, header = rand_csv(rng)
    args = {"chart": rng.choice(list(CHART_TYPES) + ["pie", "scatter", "heatmap"]) if rng.random() < 0.98 else "bogus"}
    if rng.random() < 0.4:
        args["label"] = ref(rng, header)
    if rng.random() < 0.4:
        args["values"] = ",".join(ref(rng, header) for _ in range(rng.randint(1, 3)))
    if rng.random() < 0.4:
        args["sort"] = rng.choice(["", "-", "+"]) + ref(rng, header) + rng.choice(["", "", ":desc", ":ASC", ":x"])
    if rng.random() < 0.3:
        args["limit"] = rng.choice([1, 2, 3, 5, 100, 2, 3, 5, 100, rng.choice([0, -1])])
    if rng.random() < 0.3:
        args["set"] = rng.sample(["title=Hello", "width=40", "border=none", "stacked=true", "useColor=off",
                                  'thresholds=[1, {"value": 2, "label": "t"}]', "height=6", "style=ascii",
                                  "title= spaced ", "threshold=3", "width=30"] + (["bogus=1", "threshold=NaN", "width=abc", "novalue"]
                                  if rng.random() < 0.2 else []),
                                 rng.randint(1, 3))
    return text, args


def run_python(text, args):
    try:
        options = _parse_set(args.get("set"))
        spec = spec_from_csv(text, args["chart"], args.get("label"), args.get("values"), args.get("sort"),
                             args.get("limit"), options)
    except ChartError as e:
        return {"err": str(e)}
    except csv.Error as e:
        return {"err": str(e)}
    printed = json.dumps(spec, ensure_ascii=False)
    try:
        return {"spec": printed, "out": render_chart(spec)}
    except ChartError as e:
        return {"spec": printed, "renderErr": str(e)}


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    n = int(argv[0]) if argv else 3000
    seed = int(argv[1]) if len(argv) > 1 else 1
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        text, args = rand_case(rng)
        cases.append({"csv": text, "args": args, **run_python(text, args)})
    specs = sum("spec" in c for c in cases)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8", newline="\n") as f:
        json.dump(cases, f, ensure_ascii=False)
        path = f.name
    print(f"{n} random CSV files (seed {seed}): {specs} specs, {n - specs} errors; comparing with Go ...")
    env = {**os.environ, "ASCIICHARTS_CSV_DIFF_FILE": path}
    r = subprocess.run(["go", "test", "-count=1", "-v", "-run", "TestCSVDifferential", "./asciicharts/"],
                       cwd=ROOT / "go", env=env, capture_output=True, encoding="utf-8")
    print((r.stdout + r.stderr).strip()[-6000:])
    os.unlink(path)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
