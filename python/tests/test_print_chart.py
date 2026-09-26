"""print_chart: a chart printed as UTF-8 whatever the stream's own encoding."""
import io
import subprocess
import sys
from pathlib import Path

import pytest

from asciicharts import ChartError, print_chart, render_chart

PYTHON_DIR = Path(__file__).resolve().parent.parent
SPEC = {"chartType": "hbar", "labels": ["Хром", "東京"], "series": [{"values": [3, 1]}]}


def test_a_legacy_code_page_on_the_pipe_does_not_matter():
    """What an agent on Windows gets: stdout is a pipe, its encoding cp1252. print() of the chart
    raises there; print_chart writes UTF-8 bytes."""
    code = f"from asciicharts import print_chart; print_chart({SPEC!r})"
    r = subprocess.run([sys.executable, "-c", code], cwd=PYTHON_DIR, capture_output=True,
                       env={"PYTHONIOENCODING": "cp1252", "PATH": ""})
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert r.stdout.decode("utf-8").replace("\r\n", "\n") == render_chart(SPEC) + "\n"


def test_a_text_stream_gets_the_text():
    out = io.StringIO()
    print_chart(SPEC, file=out)
    assert out.getvalue() == render_chart(SPEC) + "\n"


def test_bad_input_raises_before_writing():
    out = io.StringIO()
    with pytest.raises(ChartError):
        print_chart({"chartType": "nope", "series": [{"values": [1]}]}, file=out)
    assert out.getvalue() == ""
