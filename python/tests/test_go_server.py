"""The Go MCP server (go/cmd/asciicharts-mcp) against the Python one: the same checks over stdio and
HTTP, the same tools/list and list_charts, and the same render_chart answers on random specs.
Skipped when Go isn't installed."""

import asyncio
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from asciicharts_server.app import build_server
from asciicharts_server.store import Store

from .test_server import check_tools, free_port

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from differential import rand_spec  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("go") is None, reason="Go is not installed")


@pytest.fixture(scope="module")
def go_server():
    exe = Path(tempfile.mkdtemp()) / ("asciicharts-mcp" + (".exe" if os.name == "nt" else ""))
    subprocess.run(["go", "build", "-o", str(exe), "./cmd/asciicharts-mcp"], cwd=ROOT / "go", check=True)
    return exe


def stdio(exe):
    return StdioServerParameters(command=str(exe), args=[], env={**os.environ, "PORT": ""})


def dump(x):
    return x.model_dump(mode="json", by_alias=True, exclude_none=True)


def test_stdio(go_server):
    async def run():
        async with Client(stdio(go_server)) as c:
            await check_tools(c)
    asyncio.run(run())


def test_http_and_healthz(go_server):
    port = free_port()
    proc = subprocess.Popen([str(go_server)], env={**os.environ, "PORT": str(port)}, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                assert urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1).read() == b"ok"
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("HTTP server did not come up")

        async def run():
            async with Client(f"http://127.0.0.1:{port}/mcp") as c:
                await check_tools(c)
        asyncio.run(run())

        env = {**os.environ, "PORT": str(port)}
        assert subprocess.run([str(go_server), "healthcheck"], env=env).returncode == 0
        env["PORT"] = str(free_port())
        assert subprocess.run([str(go_server), "healthcheck"], env=env).returncode == 1
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_same_tools_and_catalogue(go_server):
    async def run():
        async with Client(build_server(stats=Store())) as py, Client(stdio(go_server)) as go:
            assert [dump(t) for t in (await go.list_tools()).tools] == [dump(t) for t in (await py.list_tools()).tools]
            a, b = await py.call_tool("list_charts", {}), await go.call_tool("list_charts", {})
            assert [c.text for c in b.content] == [c.text for c in a.content]
            assert b.structured_content == a.structured_content and not b.is_error
    asyncio.run(run())


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def schema_valid(spec):
    """Drop what the tool schema would reject, so most random specs reach the renderer."""
    enums = {"style": ("solid", "fine", "halftone", "ascii", "dotted"), "useColor": ("auto", "on", "off"),
             "border": ("none", "ascii", "light", "heavy", "double", "rounded")}
    limits = {"width": 500, "height": 200, "bins": 50}
    out = {"chartType": spec["chartType"]}
    keep = {
        "title": lambda v: isinstance(v, str), "pointChar": lambda v: isinstance(v, str),
        "stacked": lambda v: isinstance(v, bool), "showPoints": lambda v: isinstance(v, bool),
        "threshold": is_num, "labels": lambda v: all(isinstance(x, str) for x in v),
        **{k: (lambda v, k=k: v in enums[k]) for k in enums},
        **{k: (lambda v, k=k: isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= limits[k]) for k in limits},
    }
    for k, v in spec.items():
        if k in keep and keep[k](v):
            out[k] = v
        elif k == "thresholds":
            out[k] = [{"value": t} if is_num(t) else {"value": t["value"], "label": t["label"][:40]}
                      for t in v if is_num(t) or (isinstance(t, dict) and is_num(t["value"]))]
    out["series"] = [{**s, "values": [x for x in s["values"] if is_num(x)]} for s in spec["series"]]
    return out


def test_same_answers_on_random_specs(go_server):
    """Charts and chart errors byte for byte; arguments the schema rejects are rejected by both (the
    validation messages themselves differ: pydantic's and JSON Schema's)."""
    rng = random.Random(3)
    specs = [rand_spec(rng) for _ in range(150)] + [schema_valid(rand_spec(rng)) for _ in range(600)]
    specs += [{"chartType": "line", "series": [{"values": [1, 2]}], "width": 40.0},
              {"chartType": "line", "series": [{"values": [1, 2], "extra": 1}], "title": None, "more": 2},
              {"chartType": "hbar", "series": [{"name": None, "values": [1, 2]}], "labels": ["a", "b"]},
              {"chartType": "line", "series": [{"values": [1, 5]}], "thresholds": [{"value": 4, "label": None}]}]

    async def run():
        diffs = []
        async with Client(build_server(stats=Store())) as py, Client(stdio(go_server)) as go:
            for spec in specs:
                a, b = await py.call_tool("render_chart", spec), await go.call_tool("render_chart", spec)
                ta, tb = a.content[0].text, b.content[0].text
                if a.is_error != b.is_error or ("validation error" not in ta and ta != tb):
                    diffs.append((json.dumps(spec, ensure_ascii=False), ta, tb))
        return diffs
    diffs = asyncio.run(run())
    assert not diffs, f"{len(diffs)} of {len(specs)} differ; first: {diffs[0]}"
