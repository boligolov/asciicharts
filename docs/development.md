# Development

## Build & run

Requires Go 1.27+.

```sh
go build -o ascii-charts-mcp .
./ascii-charts-mcp
```

By default the server speaks MCP over stdio, so it's meant to be launched by an MCP client (Claude Desktop, Claude Code, etc.), not run interactively by hand. Setting the `PORT` environment variable switches it to a long-running HTTP server instead — see [HTTP transport](#http-transport) below.

Run the example gallery (used to generate the examples in the README):

```sh
go run ./cmd/gallery
```

Run the tests:

```sh
go test ./...
```

## Docker

Build the image:

```sh
docker build -t ascii-charts-mcp .
```

This produces a ~9 MB image (`FROM scratch`, statically linked, no libc). Run it manually with `-i` so the MCP client's stdio actually reaches the container:

```sh
docker run -i --rm ascii-charts-mcp
```

## Using it from an MCP client

Point your client's MCP server config at the built binary:

```json
{
  "mcpServers": {
    "ascii-charts": {
      "command": "/path/to/ascii-charts-mcp"
    }
  }
}
```

Or run it through Docker instead of a local binary:

```json
{
  "mcpServers": {
    "ascii-charts": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ascii-charts-mcp"]
    }
  }
}
```

If it's running as the HTTP server described below, point a client that supports the streamable-HTTP MCP transport at its URL instead of launching a process:

```json
{
  "mcpServers": {
    "ascii-charts": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

## HTTP transport

Setting the `PORT` environment variable (e.g. `PORT=8080`) switches the server from its default stdio mode to a long-running HTTP server, so one running instance can serve multiple clients over the network instead of a client launching its own process per session:

- `/mcp` — the [streamable-HTTP MCP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#streamable-http); both `render_chart` and `feedback` work exactly the same as over stdio
- `/healthz` — plain 200 OK, for container/orchestrator health checks

The handler runs in `Stateless` mode (see [`StreamableHTTPOptions`](https://pkg.go.dev/github.com/modelcontextprotocol/go-sdk/mcp#StreamableHTTPOptions)): no `Mcp-Session-Id` tracking, no server-initiated requests — this server never needs to push anything to a client outside of answering a tool call, so there's no session state worth keeping between requests. stdio mode is unaffected either way; `PORT` unset (the default) still gets you the original per-process stdio server.

The image has no shell (`FROM scratch`), so its own `docker healthcheck` can't run `curl`/`wget` — instead, `ascii-charts-mcp healthcheck` is a subcommand of the same binary that GETs its own `/healthz` and exits 0/1 accordingly (see `docker-compose.yml`'s `web` service).

## Statistics database (optional)

If the `DATABASE_URL` environment variable is set (a standard Postgres DSN, e.g. `postgres://user:pass@host:5432/dbname?sslmode=disable`), the server connects to Postgres on startup, creates its schema if missing (`chart_events`, `feedback` — see `internal/store/store.go`), and records:

- one row per `render_chart` call: chart type, style, mode, border, color on/off, series count, bucketed point-count and output-size, success/failure, and the error message on failure
- one row per `feedback` call: the message text

It never records the actual data you chart — no `values`, `labels`, or `title` content. If `DATABASE_URL` is unset, or the database is unreachable at startup, the server logs a warning and runs exactly the same without it — a database is always optional, never required.

`docker-compose.yml` brings up the full stack — Postgres plus the HTTP server from above, both on one named network (`ascii-charts-mcp`) so `web` reaches `db` by service name — with sensible defaults (copy `.env.example` to `.env` to override the Postgres credentials):

```sh
docker compose up -d
```

That publishes `db` on `localhost:5432` and `web` on `localhost:8080` (`/mcp`, `/healthz`), and `web`'s `DATABASE_URL` is already wired to `db`. Point an HTTP-capable MCP client at `http://localhost:8080/mcp` (see above) and it's fully working, stats included — nothing else to configure.

If you'd rather run the server yourself (native binary, or your own `docker run -i` in stdio mode) against just the database, bring up `db` on its own and set `DATABASE_URL` to its published `localhost:5432`:

```sh
docker compose up -d db
```
