#!/usr/bin/env python3
"""The Go command line against the Python one: the same arguments, the same stdout, stderr and exit code.

Builds go/cmd/asciicharts, then runs both on JSON specs (file, stdin, --json), --list, --version and
CSV files with every --csv option, errors included. Help texts and argparse usage errors may differ by
design and are not compared.

    python test/parity/cli_parity.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CSV_FILES = {
    "latency.csv": "service,p50_ms,p99_ms\napi,12,80\nauth,8,35\nsearch,25,140\nbilling,15,61\n",
    "semi.csv": "month;revenue;cost\nJan;1 234,5;900\nFeb;1 400,25;950\nMar;1 380;1 010\n",
    "decorated.csv": 'name,share\n"Chrome","62%"\n"Firefox","21 %"\n"Safari","$12"\n',
    "crlf.csv": "\ufeffx,y,z\r\n1,2,3\r\n2,4,1\r\n3,1,5\r\n",
    "bad.csv": "a,b\nx,1\ny,oops\n",
    "empty.csv": "",
    "header.csv": "a,b\n",
    "text.csv": "a,b\nx,y\n",
    "matrix.csv": "day|morning|noon|evening\nMon|3|7|2\nTue|5|9|4\nWed|1|4|8\n",
    "excsv.csv": "#!excsv v=0.5\n#column name=a type=string role=dimension\na,b\nx,1\n",
}

SPEC = '{"chartType":"hbar","labels":["Chrome","Firefox","Safari"],"series":[{"values":[62,21,12]}]}'

CASES = [
    (["--version"], None),
    (["--list"], None),
    (["spec.json"], None),
    (["-"], SPEC),
    (["--json", SPEC], None),
    (["--json", '{"chartType":"sparkline","series":[{"name":"a","values":[1,3,2,5]}],"border":"none"}'], None),
    (["--json", '{"chartType":"nope","series":[]}'], None),
    (["--json", '{"chartType":"vbar","series":[{"values":[1e16]}]}'], None),
    (["--json"], None),
    (["missing.json"], None),
    (["--csv", "latency.csv", "--chart", "hbar"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--sort", "-p99", "--limit", "2"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--sort", "p99:desc", "--values", "p99", "--set", "title=Slowest"], None),
    (["--csv", "latency.csv", "--chart", "vbar", "--print-spec"], None),
    (["--csv", "latency.csv", "--chart", "scatter", "--label", "p50", "--print-spec"], None),
    (["--csv", "latency.csv", "--chart", "pie", "--values", "p99", "--set", "width=50", "--set", "border=rounded"], None),
    (["--csv", "latency.csv", "--chart", "boxplot"], None),
    (["--csv", "latency.csv", "--chart", "line", "--set", "thresholds=[50, {\"value\": 100, \"label\": \"slo\"}]"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--values", "p9"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--label", "zzz"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--limit", "0"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--set", "bogus=1"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--set", "novalue"], None),
    (["--csv", "latency.csv", "--chart", "bogus"], None),
    (["--csv", "latency.csv"], None),
    (["--csv", "latency.csv", "--chart", "hbar", "--chart-name", "x"], None),
    (["--csv", "latency.csv", "--list-charts"], None),
    (["--csv", "semi.csv", "--chart", "vbar", "--print-spec"], None),
    (["--csv", "semi.csv", "--chart", "line"], None),
    (["--csv", "decorated.csv", "--chart", "pie"], None),
    (["--csv", "crlf.csv", "--chart", "area", "--print-spec"], None),
    (["--csv", "bad.csv", "--chart", "hbar"], None),
    (["--csv", "empty.csv", "--chart", "hbar"], None),
    (["--csv", "header.csv", "--chart", "hbar"], None),
    (["--csv", "text.csv", "--chart", "hbar"], None),
    (["--csv", "text.csv", "--chart", "scatter"], None),
    (["--csv", "matrix.csv", "--chart", "heatmap"], None),
    (["--csv", "matrix.csv", "--chart", "vbar", "--stacked"], "usage"),
    (["--csv", "-", "--chart", "hbar"], CSV_FILES["latency.csv"].replace("\n", "\r\n")),
    (["--csv", "missing.csv", "--chart", "hbar"], None),
    (["--csv", "excsv.csv", "--chart", "hbar"], None),
    (["--csv", "excsv.csv", "--list-charts"], None),
]


def run(cmd, args, stdin, cwd):
    r = subprocess.run(cmd + args, input=(stdin or "").encode("utf-8"), cwd=cwd, capture_output=True)
    return r.returncode, r.stdout.decode("utf-8").replace("\r\n", "\n"), r.stderr.decode("utf-8").replace("\r\n", "\n")


def main():
    exe = Path(tempfile.gettempdir()) / ("asciicharts-parity" + (".exe" if os.name == "nt" else ""))
    subprocess.run(["go", "build", "-o", str(exe), "./cmd/asciicharts"], cwd=ROOT / "go", check=True)
    python = [sys.executable, str(ROOT / "python" / "asciicharts.py")]
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in CSV_FILES.items():
            Path(tmp, name).write_bytes(text.encode("utf-8"))
        Path(tmp, "spec.json").write_text(SPEC, encoding="utf-8")
        for args, stdin in CASES:
            if stdin == "usage":  # exit code 2 on both; the usage text is argparse's own
                codes = run(python, args, None, tmp)[0], run([str(exe)], args, None, tmp)[0]
                if codes != (2, 2):
                    failed += 1
                    print(f"DIFF {args}: exit codes {codes}")
                continue
            py, go = run(python, args, stdin, tmp), run([str(exe)], args, stdin, tmp)
            if "missing" in " ".join(args):  # OS error texts differ
                same = py[0] == go[0] == 1
            elif "excsv" in " ".join(args):  # not ported yet: Go must say so
                same = go[0] == 1 and "ExCSV" in go[2]
            else:
                same = py == go
            if not same:
                failed += 1
                print(f"DIFF {args}\n--- python ({py[0]})\n{py[1]}{py[2]}--- go ({go[0]})\n{go[1]}{go[2]}")
    print(f"{len(CASES) - failed} of {len(CASES)} command lines agree")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
