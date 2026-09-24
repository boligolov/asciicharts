"""MCP server tests: in-process, over real stdio, and over real HTTP."""

import asyncio
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from asciicharts import CHART_TYPES
from asciicharts_server.app import build_server

ROOT = Path(__file__).resolve().parent.parent
SERVER = "asciicharts_server"  # run as `python -m asciicharts_server`
ARGS = {"chartType": "vbar", "title": "Test", "border": "light", "labels": ["a", "b", "c"],
        "series": [{"values": [1, 2, 3]}]}


async def check_tools(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {"list_charts", "render_chart"}
    props = tools["render_chart"].input_schema["properties"]
    assert set(props["chartType"]["enum"]) == set(CHART_TYPES)
    assert "chartType" in tools["render_chart"].input_schema["required"]

    ok = await client.call_tool("render_chart", ARGS)
    assert not ok.is_error and "Test" in ok.content[0].text and "┌" in ok.content[0].text

    ref = await client.call_tool("render_chart", {"chartType": "line", "series": [{"values": [1, 5]}],
                                                  "thresholds": [{"value": 4, "label": "target"}, {"value": 2}]})
    assert not ref.is_error and "target: 4" in ref.content[0].text

    for loose in ({"series": [{"values": ["1", "2"]}]}, {"series": [{"values": [True, False]}]},
                  {"series": [{"values": [1, 2]}], "width": "40"}, {"series": [{"values": [1, 2]}], "showPoints": "yes"}):
        coerced = await client.call_tool("render_chart", {"chartType": "line", **loose})
        assert coerced.is_error, f"{loose} should be rejected, not coerced"

    bad = await client.call_tool("render_chart", {"chartType": "line", "series": [{"values": [1]}]})
    assert bad.is_error and "at least two values" in bad.content[0].text

    invalid = await client.call_tool("render_chart", {"chartType": "nope", "series": [{"values": [1]}]})
    assert invalid.is_error

    listing = await client.call_tool("list_charts", {})
    assert not listing.is_error
    charts = listing.structured_content["result"]
    assert [c["type"] for c in charts] == list(CHART_TYPES)
    return charts


def test_in_process():
    async def run():
        async with Client(build_server()) as c:
            await check_tools(c)
    asyncio.run(run())


def test_every_listed_example_can_be_rendered_through_the_tool():
    """The catalogue and the tool agree: calling render_chart with each example works."""
    async def run():
        async with Client(build_server()) as c:
            for chart in (await c.call_tool("list_charts", {})).structured_content["result"]:
                assert set(chart) == {"type", "summary", "series", "options", "example"}
                r = await c.call_tool("render_chart", chart["example"])
                assert not r.is_error, (chart["type"], r.content[0].text)
                assert r.content[0].text.strip()
    asyncio.run(run())


def test_stdio_subprocess():
    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", SERVER],
                                       env={**os.environ, "PORT": "", "DATABASE_URL": "", "PYTHONIOENCODING": "utf-8"})
        async with Client(params) as c:
            await check_tools(c)
    asyncio.run(run())


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def http_server():
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", SERVER],
                            env={**os.environ, "PORT": str(port), "DATABASE_URL": "", "PYTHONIOENCODING": "utf-8"},
                            stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("HTTP server did not come up")
        yield port
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_http_transport_and_healthz(http_server):
    port = http_server
    assert urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz").read() == b"ok"

    async def run():
        async with Client(f"http://127.0.0.1:{port}/mcp") as c:
            await check_tools(c)
    asyncio.run(run())


def test_healthcheck_subcommand(http_server):
    env = {**os.environ, "PORT": str(http_server)}
    assert subprocess.run([sys.executable, "-m", SERVER, "healthcheck"], env=env).returncode == 0
    env["PORT"] = str(free_port())
    assert subprocess.run([sys.executable, "-m", SERVER, "healthcheck"], env=env).returncode == 1
