# asciicharts MCP server

An [MCP](https://modelcontextprotocol.io) server that draws text charts. Give it numbers, get back a
Unicode/ASCII chart as plain text that an agent can paste straight into a reply — no image, no
plotting library, no files, no network access.

It is a thin layer over the Go renderer ([`go/asciicharts`](../../asciicharts/), byte-for-byte the
[asciicharts principles](../../../docs/spec/principles.md)) built on the official
[Go MCP SDK](https://github.com/modelcontextprotocol/go-sdk). One static binary, nothing else to install.

| | |
|---|---|
| Server name | `asciicharts` |
| Tools | [`list_charts`](#list_charts), [`render_chart`](#render_chart) |
| Transports | stdio (default), streamable HTTP (`/mcp`) |
| State | none — every call is independent; runs stateless |
| Side effects | none: it records nothing, stores nothing, calls nothing |

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
`example` is a valid `render_chart` call.

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
[`skills/asciicharts/references/reference.md`](../../../skills/asciicharts/references/reference.md), and every chart
rendered is in the [gallery](../../../docs/gallery.md).

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
total; values must be finite numbers no larger than 1e15 in magnitude; `title`, `labels` and names at most 200
characters. Requests beyond that are rejected, not truncated. Control characters in text (newlines, escape
sequences) are replaced by spaces.

## Running it

```sh
go install github.com/boligolov/asciicharts/go/cmd/asciicharts-mcp@latest
asciicharts-mcp                  # MCP over stdio
PORT=8080 asciicharts-mcp        # streamable HTTP at :8080/mcp, health check at /healthz
```

Docker (image built from [`deploy/Dockerfile`](../../../deploy/Dockerfile); an empty image with the static binary):

```sh
docker build -f deploy/Dockerfile -t asciicharts .
docker run -i --rm asciicharts                                  # stdio
docker run --rm -e PORT=8080 -p 8080:8080 asciicharts           # HTTP
```

Production, with HTTPS on your own domain: [below](#production-https-on-your-own-domain).

### Configuration

| variable | meaning |
|---|---|
| `PORT` | if set, serve streamable HTTP on this port instead of stdio |

Subcommand: `asciicharts-mcp healthcheck` GETs the server's own `/healthz` and exits 0/1 (used by Docker healthchecks).

### HTTP transport

`/mcp` speaks the [streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#streamable-http)
in stateless mode (no sessions; nothing is pushed to the client outside a tool call). `/healthz` returns
`200 ok`. The server listens on all interfaces and has **no authentication**; a request that arrives on a loopback
address must name a localhost host (the SDK's DNS-rebinding protection). Put it behind a reverse proxy or
ingress for TLS and access control.

### Production: HTTPS on your own domain

`deploy/docker-compose.prod.yml` + `deploy/Caddyfile` run the server behind HTTPS on your own domain:

```
internet ──80/443──▶ Caddy ──▶ web (MCP server, :8080 internal)
```

1. Point your domain's DNS record at the host (ports 80 and 443 must be reachable from the internet).
2. `cp deploy/.env.example deploy/.env` and set `DOMAIN`. Compose refuses to start without it.
3. `docker compose -f deploy/docker-compose.prod.yml up -d --build` (from the repository root)
4. Your MCP endpoint is `https://<DOMAIN>/mcp` (health: `https://<DOMAIN>/healthz`).

To deploy a prebuilt image instead of building on the host, push it to your registry, set `IMAGE=registry.example.com/asciicharts:1.0.0` in `deploy/.env`, and run `docker compose -f deploy/docker-compose.prod.yml pull && docker compose -f deploy/docker-compose.prod.yml up -d`.

What it sets up, and why:

- **Only Caddy is published** (80/443). The server lives on the internal network (the local `deploy/docker-compose.yml` publishes it on `:8080` instead).
- **Automatic certificates.** Caddy obtains and renews the Let's Encrypt certificate itself; keep the `caddy-data` volume so it isn't re-issued on every deploy. Plain HTTP redirects to HTTPS.
- **Only `/mcp` and `/healthz` are forwarded**; any other path is a 404 at the proxy. Request bodies over 1 MB get a 413.
- **Hardened container:** an image with nothing but the binary, read-only filesystem, all Linux capabilities dropped, `no-new-privileges`, non-root user.
- **No authentication.** The server is meant to be a public utility: both tools are stateless and bounded (see [Limits](../../../skills/asciicharts/references/reference.md#limits)), and it stores nothing, not even counters. If you need it private, put access control in front (Caddy `basic_auth`, an IP allow-list, or your platform's ingress).
- **DNS-rebinding protection** (the Go MCP SDK's default): a request that arrives on a loopback address must name a localhost host. Caddy reaches the server over the compose network, not loopback, so your domain works.

To try the whole stack locally without a domain, set `DOMAIN=localhost` (Caddy issues a certificate from its own CA, so clients must trust it or skip verification).

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

If you have both this server and the [skill](../../../docs/skill.md) available, either works: the skill runs the
`asciicharts` command or the Python script directly (needs a shell), the server works from any MCP client.

## Code map

| file | what |
|---|---|
| `main.go` | the server: tools, argument validation and shaping, transports, health check |
| `tools.json` | the tool definitions: names, descriptions, JSON schemas — served exactly as written |
| `testdata/` | answers the server must give: `render_chart.json` (754 calls: charts and chart errors byte for byte, and calls to reject), `list_charts.json` |

Arguments are validated against the schema in `tools.json` strictly: `"1"` and `true` are not numbers, and
`40.0` is not an integer. Tests (`go test ./cmd/asciicharts-mcp/`) replay `testdata/` and run the server
for real over stdio and HTTP. The answers were recorded from the Python server this one replaced.
