# asciicharts MCP server

An [MCP](https://modelcontextprotocol.io) server that draws text charts. Give it numbers, get back a
Unicode/ASCII chart as plain text that an agent can paste straight into a reply — no image, no
plotting library, no files, no network access.

It is a thin layer over [`asciicharts.py`](../asciicharts.py) (the renderer, a single dependency-free
file) built on the official [`mcp`](https://pypi.org/project/mcp/) Python SDK (`>=2.2,<3`).

| | |
|---|---|
| Server name | `asciicharts` |
| Tools | [`list_charts`](#list_charts), [`render_chart`](#render_chart) |
| Transports | stdio (default), streamable HTTP (`/mcp`) |
| State | none — every call is independent; runs stateless |
| Side effects | none (optional anonymous [usage statistics](#usage-statistics), off by default) |

## Tools

### `list_charts`

The catalogue of chart types. No arguments. Returns one entry per chart type:

```json
{
  "type": "hbar",
  "summary": "Horizontal bars: single, grouped or stacked. The best choice for rankings and long labels. Negative values diverge.",
  "series": "values: one number per entry of labels. Several series are grouped (or stacked). name is the legend entry.",
  "options": ["labels", "width", "stacked", "style"],
  "example": {"chartType": "hbar", "labels": ["Chrome", "Firefox", "Safari"], "series": [{"values": [62, 21, 12]}]}
}
```

Call it first when the model is unsure which chart fits the data or how to shape `series`. Every
`example` is a valid `render_chart` call (a test renders all of them).

### `render_chart`

Renders one chart and returns it as text (put it in a code block so it stays aligned).

| argument | type | notes |
|---|---|---|
| `chartType` | enum, required | `sparkline` `vbar` `hbar` `line` `area` `scatter` `dual_axis` `pie` `histogram` `heatmap` `boxplot` `dotplot` |
| `series` | array, required | `{name?, values?, points?}` — how each is read depends on `chartType` (see `list_charts`) |
| `labels` | string[] | category labels, x-axis labels (line/area) or heatmap column headers |
| `title` | string | shown centred above the chart |
| `width`, `height` | int | characters / rows; at most 500 / 200 |
| `border` | enum | `none` `ascii` `light` (default) `heavy` `double` `rounded` |
| `style` | enum | `solid` (default; whole-block bars) `fine` (eighth-block bar ends) `halftone` `ascii` (pure-ASCII, up to 23 distinct series glyphs) `dotted` (line) |
| `stacked` | bool | stack series in vbar/hbar/area (negative values stack the other way) |
| `bins` | int | histogram buckets (default 10) |
| `useColor` | enum | `auto` `on` `off` — ANSI 256-colour; leave off for a chat reply |
| `threshold` | number | line: dashed reference line |
| `thresholds` | `{value, label?}[]` | line: several dashed reference lines, each named right of the plot |
| `showPoints`, `pointChar` | bool, string | line: mark each data point |

The complete reference (defaults, every option, limits, errors) is in
[`skills/asciicharts/references/reference.md`](../skills/asciicharts/references/reference.md), and every chart
rendered is in the [gallery](../docs/gallery.md).

Example call and result:

```json
{ "chartType": "hbar", "title": "Build time by stage (s)", "labels": ["Compile", "Test", "Lint", "Package"],
  "series": [{ "values": [64, 32, 16, 8] }] }
```

```
┌───────────────────────────────────────────────────────┐
│                Build time by stage (s)                │
├───────────────────────────────────────────────────────┤
│ Compile │ ████████████████████████████████████████ 64 │
│ Test    │ ████████████████████░░░░░░░░░░░░░░░░░░░░ 32 │
│ Lint    │ ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 16 │
│ Package │ █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 8  │
└───────────────────────────────────────────────────────┘
```

**Errors** come back as an MCP tool result with `isError: true` and a one-line message that names the
problem, so the model can correct the call — for example `series 0 "" must contain at least two values`
or `width must be at most 500, got 9999`.

**Limits:** `width` ≤ 500, `height` ≤ 200, `bins` ≤ 500, at most 100 series and 50,000 values/points in
total; values must be finite numbers. Requests beyond that are rejected, not truncated.

## Running it

```sh
pip install .                    # from the repository root; or `pip install ".[stats]"` for statistics
asciicharts-mcp                  # MCP over stdio  (same as: python -m asciicharts_server)
PORT=8080 asciicharts-mcp        # streamable HTTP at :8080/mcp, health check at /healthz
```

Docker (image built from [`deploy/Dockerfile`](../deploy/Dockerfile)):

```sh
docker build -f deploy/Dockerfile -t asciicharts .
docker run -i --rm asciicharts                                  # stdio
docker run --rm -e PORT=8080 -p 8080:8080 asciicharts           # HTTP
```

Production (HTTPS on your own domain with Caddy): see [docs/development.md](../docs/development.md#production-deployment).

### Configuration

| variable | meaning |
|---|---|
| `PORT` | if set, serve streamable HTTP on this port instead of stdio |
| `ASCIICHARTS_STATS` | `on` / `1` / `true` / `yes` to record [usage statistics](#usage-statistics); default off |
| `DATABASE_URL` | Postgres DSN for the statistics (only used when `ASCIICHARTS_STATS` is on) |

Subcommand: `asciicharts-mcp healthcheck` GETs the server's own `/healthz` and exits 0/1 (used by Docker healthchecks).

### HTTP transport

`/mcp` speaks the [streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#streamable-http)
in stateless mode (no sessions; nothing is pushed to the client outside a tool call). `/healthz` returns
`200 ok`. The server binds `0.0.0.0` and has **no authentication** and no Host-header check (that check
protects localhost-only servers): put it behind a reverse proxy or ingress for TLS and access control.

## Connecting a client

**Claude Code**

```sh
claude mcp add asciicharts -- asciicharts-mcp                       # local process (stdio)
claude mcp add --transport http asciicharts https://charts.example.com/mcp   # remote server
```

**Claude Desktop** and other clients that read a JSON config:

```json
{ "mcpServers": { "asciicharts": { "command": "asciicharts-mcp" } } }
```

Through Docker instead of a local install:

```json
{ "mcpServers": { "asciicharts": { "command": "docker", "args": ["run", "-i", "--rm", "asciicharts"] } } }
```

Against a running HTTP server (clients that support remote MCP servers):

```json
{ "mcpServers": { "asciicharts": { "url": "https://charts.example.com/mcp" } } }
```

If you have both this server and the [skill](../docs/skill.md) available, either works: the skill runs the
script directly (needs a shell and Python), the server works from any MCP client.

## Usage statistics

Off by default. With `ASCIICHARTS_STATS=on` and `DATABASE_URL` set, the server creates a `chart_events`
table and records one anonymous row per `render_chart` call: chart type, style, border, colour on/off,
series count, bucketed point count and output size, success/failure and the error message. It **never**
stores what you chart — no values, labels or titles. It can never break a request: if the flag is on but
the database is missing or unreachable, the server logs a warning and runs without statistics.
Details: [docs/development.md](../docs/development.md#statistics-optional-off-by-default).

## Code map

| file | what |
|---|---|
| `app.py` | the server: tool definitions, transports, health check, environment handling |
| `store.py` | the optional Postgres statistics store (`asyncpg`, a no-op when disabled) |
| `__main__.py` | `python -m asciicharts_server` |

The package is installed as `asciicharts_server` (this folder is mapped to it in `pyproject.toml`); the
renderer it wraps is the top-level `asciicharts` module. Tests: `tests/test_server.py` (in-process, real
stdio, real HTTP) and `tests/test_store.py`.
