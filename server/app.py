"""MCP server exposing asciicharts as tools.

Two tools:

* ``list_charts``  — the catalogue of chart types: what each draws, how to fill
                     ``series``, which options apply, and a minimal example.
* ``render_chart`` — render numeric data as an ASCII/Unicode text chart.

Transport is chosen by the environment:

* default        — MCP over stdio, for a client that launches its own process
                   (Claude Desktop, Claude Code, ...).
* ``PORT`` set   — a long-running HTTP server: streamable-HTTP MCP at ``/mcp``
                   and a plain ``/healthz`` for container probes.

Anonymous usage statistics are OFF by default. Set ``ASCIICHARTS_STATS=on`` and
``DATABASE_URL`` (a Postgres DSN) to record them (see store.py); the
server behaves identically either way.

Usage::

    python -m asciicharts_server                 # stdio (or the `asciicharts-mcp` command)
    PORT=8080 python -m asciicharts_server       # HTTP
    python -m asciicharts_server healthcheck     # exit 0/1 by probing its own /healthz
"""

from __future__ import annotations

import logging
import os
import sys
import urllib.request
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import PlainTextResponse

import asciicharts
from .store import ChartEvent, Store, bucket

VERSION = asciicharts.__version__
DEFAULT_PORT = "8080"

log = logging.getLogger("asciicharts")

ChartType = Literal[
    "sparkline", "vbar", "hbar", "line", "area", "scatter",
    "dual_axis", "pie", "histogram", "heatmap", "boxplot", "dotplot",
]


class Point(BaseModel):
    x: float
    y: float


class Series(BaseModel):
    name: Annotated[str | None, Field(description="optional series/category/row name, used in legends and axis labels")] = None
    values: Annotated[list[float] | None, Field(description="numeric values; meaning depends on chartType, see list_charts")] = None
    points: Annotated[list[Point] | None, Field(description="(x, y) samples, used only by scatter charts")] = None


class ChartInfo(BaseModel):
    type: Annotated[str, Field(description="the chartType value to pass to render_chart")]
    summary: Annotated[str, Field(description="what the chart draws and when to use it")]
    series: Annotated[str, Field(description="how to fill `series` for this chart type")]
    options: Annotated[list[str], Field(description="render_chart options that affect this chart, beyond title/border/useColor which every chart accepts")]
    example: Annotated[dict[str, Any], Field(description="a minimal valid render_chart call")]


LIST_CHARTS_DESCRIPTION = (
    "List every chart type this server can draw: what it draws, how to fill `series` for it, which options apply, "
    "and a minimal example call for render_chart. Call this first when you are unsure which chart fits the data or "
    "how to shape `series`."
)

RENDER_CHART_DESCRIPTION = (
    "Render numeric data as an ASCII/Unicode text chart. Supports sparkline, vbar, hbar, line, area, scatter, "
    "dual_axis, pie, histogram, heatmap, boxplot and dotplot, with an optional title, border frame (none/ascii/light/"
    "heavy/double/rounded), sub-character resolution for line/scatter/dual_axis (cell/quad/braille), bar/area fill "
    "style (solid/halftone/ascii) and line style (solid/dotted), a dashed threshold line and configurable per-point "
    "markers for line charts, a target chart width (vbar/hbar scale to fill it), automatic diverging bars for "
    "negative values (including stacked), and optional ANSI 256-color output. Returns the chart as plain text — put "
    "it in a code block so it stays aligned. Use list_charts to see how `series` is filled for each chartType."
)


TRUTHY = {"1", "true", "yes", "on"}


def stats_enabled(env=None) -> bool:
    """Usage statistics are opt-in: ASCIICHARTS_STATS must be 1/true/yes/on (default: off)."""
    env = os.environ if env is None else env
    return env.get("ASCIICHARTS_STATS", "").strip().lower() in TRUTHY


async def open_stats(env=None) -> Store:
    """Open the statistics store as configured by the environment.

    Off unless ASCIICHARTS_STATS is set; when on it also needs DATABASE_URL. A
    misconfiguration or an unreachable database degrades to "off" with a
    warning — statistics never stop the server from starting."""
    env = os.environ if env is None else env
    if not stats_enabled(env):
        log.info("usage statistics: disabled (set ASCIICHARTS_STATS=on and DATABASE_URL to enable)")
        return Store()
    dsn = env.get("DATABASE_URL", "").strip()
    if not dsn:
        log.warning("usage statistics: ASCIICHARTS_STATS is on but DATABASE_URL is not set — disabled")
        return Store()
    store = await Store.open(dsn, VERSION)
    if store.enabled:
        log.info("usage statistics: enabled")
    return store


def total_points(spec: dict) -> int:
    return sum(len(s.get("values") or []) + len(s.get("points") or []) for s in spec.get("series") or [])


def build_server(stats: Store | None = None) -> MCPServer:
    """Create the MCP server. ``stats`` is bound late by the lifespan when omitted."""
    holder = {"stats": stats or Store()}

    @asynccontextmanager
    async def lifespan(_: MCPServer):
        if stats is None:  # not injected (tests): open from the environment
            holder["stats"] = await open_stats()
        try:
            yield
        finally:
            if stats is None:
                await holder["stats"].close()

    server = MCPServer("asciicharts", version=VERSION, lifespan=lifespan)

    @server.tool(name="list_charts", description=LIST_CHARTS_DESCRIPTION)
    async def list_charts() -> list[ChartInfo]:
        return [ChartInfo(**c) for c in asciicharts.list_charts()]

    @server.tool(name="render_chart", description=RENDER_CHART_DESCRIPTION)
    async def render_chart(
        chartType: Annotated[ChartType, Field(description="chart type; see list_charts")],
        series: Annotated[list[Series], Field(description="one or more data series/rows/slices to plot; see list_charts for how each chartType reads them")],
        labels: Annotated[list[str] | None, Field(description="category labels for vbar/hbar/histogram/dotplot bars, x-axis labels for line/area, or column headers for a heatmap")] = None,
        title: Annotated[str | None, Field(description="optional title shown above the chart")] = None,
        width: Annotated[int | None, Field(ge=0, le=asciicharts.MAX_WIDTH, description="chart width in characters (default depends on chart type)")] = None,
        height: Annotated[int | None, Field(ge=0, le=asciicharts.MAX_HEIGHT, description="chart height in rows (default depends on chart type)")] = None,
        border: Annotated[Literal["none", "ascii", "light", "heavy", "double", "rounded"] | None, Field(description="border style (default: light)")] = None,
        mode: Annotated[Literal["cell", "quad", "braille"] | None, Field(description="sub-character resolution for line/scatter/dual_axis: cell (1 point per character), quad (2x2 via quadrant blocks) or braille (2x4 via braille dots); default: cell")] = None,
        style: Annotated[Literal["solid", "halftone", "ascii", "dotted"] | None, Field(description="visual style. vbar/hbar/histogram/area: solid (default; flat blocks, sub-character precision on bars), halftone (lighter stippled Unicode shades per series) or ascii (plain-ASCII characters per series — #, X, H, W, =, :, |, . then @ % & $ M N D O U S G Z / \\ ! — that render identically in any monospace font). line: solid (default) or dotted (sparse plotted-dot trend line)")] = None,
        stacked: Annotated[bool | None, Field(description="for vbar/hbar/area with multiple series, stack them (cumulative from zero; negative values stack the other way) instead of grouping/overlaying")] = None,
        bins: Annotated[int | None, Field(ge=0, le=asciicharts.MAX_BINS, description="number of buckets for histogram charts (default: 10)")] = None,
        useColor: Annotated[Literal["auto", "on", "off"] | None, Field(description="ANSI 256-color output (default: auto, which is equivalent to off since tool output is plain text for an agent, not a terminal)")] = None,
        threshold: Annotated[float | None, Field(description="line charts only: draw a dashed horizontal reference line at this y-value")] = None,
        showPoints: Annotated[bool | None, Field(description="line charts only: mark each individual data point with a glyph on top of the connecting line")] = None,
        pointChar: Annotated[str | None, Field(description="line charts only, with showPoints: single character used to mark points on every series (default: a large circle for the first series, with a distinct shape per additional series)")] = None,
    ) -> str:
        args = dict(
            chartType=chartType, labels=labels, title=title, width=width, height=height, border=border,
            mode=mode, style=style, stacked=stacked, bins=bins, useColor=useColor, threshold=threshold,
            showPoints=showPoints, pointChar=pointChar,
        )
        spec = {k: v for k, v in args.items() if v is not None}
        spec["series"] = [s.model_dump(exclude_none=True) for s in series]

        event = ChartEvent(
            chart_type=chartType, style=style or "", mode=mode or "", border=border or "",
            use_color=useColor == "on", series_count=len(series),
        )
        try:
            chart = asciicharts.render_chart(spec)
        except asciicharts.ChartError as e:
            event.success = False
            event.error_message = str(e)[:200]
            await holder["stats"].record_chart_event(event)
            raise ToolError(str(e)) from e

        event.point_count_bucket = bucket(total_points(spec), 10, 100, 1000)
        event.output_size_bucket = bucket(len(chart.encode("utf-8")), 500, 2000, 8000)
        await holder["stats"].record_chart_event(event)
        return chart

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(_: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    return server


def healthcheck_self() -> int:
    """GET our own /healthz; 0 if healthy, 1 if not (for `docker healthcheck`)."""
    port = os.environ.get("PORT") or DEFAULT_PORT
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3) as r:
            return 0 if r.status == 200 else 1
    except Exception:  # noqa: BLE001
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["healthcheck"]:
        return healthcheck_self()

    # stdio owns stdout for the protocol: logs must go to stderr.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")
    server = build_server()

    if port := os.environ.get("PORT"):
        log.info("serving MCP over HTTP at :%s/mcp", port)
        # Stateless: this server never pushes anything to a client outside of
        # answering a tool call, so there is no per-session state worth keeping.
        server.run("streamable-http", host="0.0.0.0", port=int(port), stateless_http=True)
    else:
        server.run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
