#!/usr/bin/env python3
"""Differential test of the Go implementation against the Python reference, on random specs.

Python generates N random specs — every chart type and option, values from tiny to 1e15, zeros and
negative zeros, text in several scripts with control characters, options of the wrong type — renders
each (output or error message), writes them to a file, and runs the Go test TestDifferential on it.
Any byte difference is a divergence between the two implementations.

    python scripts/differential.py            # 3000 specs, seed 1
    python scripts/differential.py 20000 7    # N specs, seed
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
from asciicharts import CHART_TYPES, ChartError, render_chart  # noqa: E402

WORDS = ["a", "Long label", "東京", "🍕 pizza", "été", "שלום", "x\ty", "ＡＢＣ", "", "Q1", "a\nb",
         "\x1b[2J", "👨‍👩‍👧", "́x", "ok"]


def rand_value(rng):
    r = rng.random()
    if r < 0.05:
        return 0
    if r < 0.07:
        return -0.0
    if r < 0.12:
        return rng.choice([1e15, -1e15, 1e-9, 3e-7, 0.001, 123456789.5, 1e15 + 1, 1e308])
    if r < 0.14:
        return rng.choice(["1", True, None, [1], {"a": 1}])  # wrong types: errors
    if r < 0.5:
        return rng.randint(-50, 100)
    return round(rng.gauss(20, 40), rng.choice([0, 1, 2, 3, 6]))


def rand_spec(rng):
    n = rng.randint(1, 9)
    spec = {"chartType": rng.choice(CHART_TYPES)}
    for key, choices in (("style", ["", "solid", "fine", "halftone", "ascii", "dotted"]),
                         ("border", ["", "none", "ascii", "light", "heavy", "double", "rounded"]),
                         ("useColor", ["", "on", "off", "auto"])):
        if rng.random() < 0.6:
            spec[key] = rng.choice(choices)
    if rng.random() < 0.5:
        spec["title"] = rng.choice(WORDS) + " " + rng.choice(WORDS)
    for key, hi in (("width", 90), ("height", 25), ("bins", 12)):
        if rng.random() < 0.5:
            spec[key] = rng.choice([rng.randint(0, hi), rng.randint(0, hi), rng.randint(0, hi), float(rng.randint(1, hi)),
                                    -3, "40", 2.5])
    for key in ("stacked", "showPoints"):
        if rng.random() < 0.3:
            spec[key] = rng.choice([True, False, 1, 0, "yes", ""])
    if rng.random() < 0.2:
        spec["threshold"] = rand_value(rng)
    if rng.random() < 0.2:
        spec["thresholds"] = [rng.choice([rand_value(rng), {"value": rand_value(rng), "label": rng.choice(WORDS)}])
                              for _ in range(rng.randint(1, 3))]
    if rng.random() < 0.2:
        spec["pointChar"] = rng.choice(["*", "é", "🔴", "ab", ""])
    if rng.random() < 0.7:
        spec["labels"] = [rng.choice(WORDS) + str(i) if rng.random() < 0.9 else rng.choice([1, 2.5, True, None])
                          for i in range(n + (1 if rng.random() < 0.05 else 0))]
    series = []
    for s in range(rng.randint(1, 4)):
        entry = {"values": [rand_value(rng) if rng.random() < 0.03 else
                            (rng.choice([0, rng.randint(-50, 100), round(rng.gauss(20, 40), 2)]))
                            for _ in range(n)]}
        if rng.random() < 0.8:
            entry["name"] = rng.choice(WORDS)
        if spec["chartType"] == "scatter":
            entry["points"] = [{"x": round(rng.gauss(0, 10), 2), "y": round(rng.gauss(0, 10), 2)} for _ in range(n)]
        if spec["chartType"] == "pie":
            entry["values"] = [abs(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
                               for v in entry["values"][:1]]
        series.append(entry)
    spec["series"] = series
    return spec


def main(argv):
    n = int(argv[0]) if argv else 3000
    seed = int(argv[1]) if len(argv) > 1 else 1
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        spec = rand_spec(rng)
        try:
            case = {"spec": spec, "out": render_chart(spec)}
        except ChartError as e:
            case = {"spec": spec, "err": str(e)}
        cases.append(case)
    errors = sum("err" in c for c in cases)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8", newline="\n") as f:
        json.dump(cases, f, ensure_ascii=False)
        path = f.name
    print(f"{n} random specs (seed {seed}): {n - errors} charts, {errors} errors; comparing with Go ...")
    env = {**os.environ, "ASCIICHARTS_DIFF_FILE": path}
    r = subprocess.run(["go", "test", "-count=1", "-v", "-run", "TestDifferential", "./asciicharts/"], cwd=ROOT / "go",
                       env=env, capture_output=True, encoding="utf-8")
    print((r.stdout + r.stderr).strip()[-4000:])
    os.unlink(path)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
