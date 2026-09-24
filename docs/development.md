# Development

## Repository layout

```
python/                 the Python implementation: asciicharts.py (the renderer, one file, standard library only,
                        also shipped inside the skill), server/, pyproject.toml, tests/
python/server/          the MCP server (installed as the `asciicharts_server` package) — see python/server/README.md
skills/asciicharts/     the skill: SKILL.md, scripts/, references/ — see docs/skill.md
deploy/                 Dockerfile, docker-compose (dev and prod), Caddyfile, .env.example
spec/                   the principles (principles.md, v1.0), CHANGELOG.md, LICENSE (CC BY 4.0), conformance/ — the
                        language-neutral suite every implementation must pass byte for byte
python/tests/           pytest suite (runs spec/conformance/); tests/golden/excsv_fixtures/
skills/evals/           the skill's evals (prompts, programmatic graders, recorded runs)
scripts/                sync_skill.py, package_skill.py, gallery_refresh.py, site_examples.py, og_image.py,
                        conformance_refresh.py
docs/                   this file, gallery.md (every chart rendered), skill.md
LICENSE  ROADMAP.md
```

## Setup

Python 3.10+ (developed and tested on 3.12).

```sh
python -m venv .venv
.venv/bin/pip install -e "./python[stats,dev]"      # Windows: .venv\Scripts\pip
```

`asciicharts.py` itself needs nothing but the standard library — the dependencies (`mcp`, optionally `asyncpg`) are only for the server.

## Run

Render a chart from JSON:

```sh
echo '{"chartType":"sparkline","series":[{"values":[1,3,2,5]}]}' | python python/asciicharts.py -
python python/asciicharts.py --list    # every chart type with an example spec
```

Run the MCP server:

```sh
python -m asciicharts_server              # stdio — meant to be launched by an MCP client (same: asciicharts-mcp)
PORT=8080 python -m asciicharts_server    # streamable HTTP at :8080/mcp, health check at /healthz
```

## Tests

```sh
pytest
```

- `tests/test_charts.py` — the renderers. They run the conformance suite in `spec/conformance/` — first captured from the original Go implementation this project was ported from: the gallery plus a corpus of 317 random specs and their exact output — so every chart is pinned byte-for-byte. If you change how something is drawn on purpose, that is a new version of the principles: `python scripts/conformance_refresh.py` reports which cases change (by chart type), `--write` writes them; review the diff and add an entry to `spec/CHANGELOG.md`.
- `tests/test_server.py` — the MCP server (`python/server/`) in-process, over real stdio, and over real HTTP. The tests import the installed `asciicharts_server` package, so run `pip install -e "./python[stats,dev]"` first (`tests/conftest.py` says so if you forget).
- `tests/test_store.py` — the optional statistics store.
- `tests/test_csv.py` — CSV input (`--csv`).
- `tests/test_excsv.py` — [ExCSV](https://github.com/boligolov/excsv) input: `#chart` suggestions resolved into a spec (`--chart-name`/`--list-charts`, `spec_from_excsv`), checked in part against `tests/golden/excsv_fixtures/` — that spec's own `#chart` fixtures, copied verbatim (CC0) from its shared fixture corpus, so this is tested against the format's ground truth rather than only our own assumptions about it.
- `tests/test_catalog.py` — the chart catalogue (`list_charts` / `--list`) against the renderers.
- `tests/test_skill.py` — the skill folder: valid frontmatter, self-contained links, the commands `SKILL.md` shows actually run, and its example output is current.

### The skill folder

`skills/asciicharts/` must be self-contained (it is copied, zipped or uploaded on its own), but the renderer and the licence live at the repository root because the MCP server, the tests and pip use them. So the skill holds *copies*: after editing `asciicharts.py` or `LICENSE`, run

```sh
python scripts/sync_skill.py
```

`tests/test_skill.py` fails when the copies differ. `references/reference.md` is edited in place. The gallery is `docs/gallery.md` (after changing how anything is drawn or adding an example, `python scripts/gallery_refresh.py` re-renders every printed output — in the gallery and in the skill's `references/drawing.md` — and rebuilds the gallery's contents list; a test fails if either is stale) and `python scripts/sync_skill.py` copies it, and `spec/principles.md`, into the skill.

## Docker

```sh
docker build -f deploy/Dockerfile -t asciicharts .    # from the repository root
```

Stdio (default) — run with `-i` so the client's stdio reaches the container:

```sh
docker run -i --rm asciicharts
```

HTTP — set `PORT`:

```sh
docker run --rm -e PORT=8080 -p 8080:8080 asciicharts
curl localhost:8080/healthz          # ok  (on Windows prefer 127.0.0.1: the server listens on IPv4,
                                     #      and "localhost" tries IPv6 first — ~200 ms per request)
```

The image has no `curl`; `asciicharts-mcp healthcheck` is a subcommand of the server itself that GETs its own `/healthz` and exits 0/1 (used by the compose files in `deploy/`).

## Production deployment

`deploy/docker-compose.prod.yml` + `deploy/Caddyfile` run the server behind HTTPS on your own domain:

```
internet ──80/443──▶ Caddy ──▶ web (MCP server, :8080 internal) ─ ─▶ db (Postgres, internal; only if statistics are on)
```

1. Point your domain's DNS record at the host (ports 80 and 443 must be reachable from the internet).
2. `cp deploy/.env.example deploy/.env` and set `DOMAIN`. Compose refuses to start without it.
3. `docker compose -f deploy/docker-compose.prod.yml up -d --build` (from the repository root)
4. Your MCP endpoint is `https://<DOMAIN>/mcp` (health: `https://<DOMAIN>/healthz`).

To deploy a prebuilt image instead of building on the host, push it to your registry, set `IMAGE=registry.example.com/asciicharts:1.0.0` in `deploy/.env`, and run `docker compose -f deploy/docker-compose.prod.yml pull && docker compose -f deploy/docker-compose.prod.yml up -d`.

What it sets up, and why:

- **Only Caddy is published** (80/443). The server (and Postgres, if you enable [statistics](#statistics-optional-off-by-default)) live on the internal network. This is the main difference from the dev `deploy/docker-compose.yml`, which publishes Postgres on `:5432` with a default password.
- **Automatic certificates.** Caddy obtains and renews the Let's Encrypt certificate itself; keep the `caddy-data` volume so it isn't re-issued on every deploy. Plain HTTP redirects to HTTPS.
- **Only `/mcp` and `/healthz` are forwarded**; any other path is a 404 at the proxy. Request bodies over 1 MB get a 413 (the server logs a harmless "client disconnected" when the proxy cuts such a request off).
- **Hardened container:** read-only filesystem, all Linux capabilities dropped, `no-new-privileges`, non-root user.
- **No authentication.** The server is meant to be a public utility: both tools are stateless and bounded (see [Limits](../skills/asciicharts/references/reference.md#limits)), and it stores nothing you send — only anonymous usage counters, and only if you configure a database. If you need it private, put access control in front (Caddy `basic_auth`, an IP allow-list, or your platform's ingress).
- **Host header check off.** The MCP SDK's DNS-rebinding check only makes sense for a server bound to localhost; a public server is reached under your domain name, so it is not enabled.

To try the whole stack locally without a domain, set `DOMAIN=localhost` (Caddy issues a certificate from its own CA, so clients must trust it or skip verification).

## Using it from an MCP client

Local process (needs the package installed, e.g. `pip install ./python` or `uvx --from ./python asciicharts-mcp`):

```json
{ "mcpServers": { "asciicharts": { "command": "asciicharts-mcp" } } }
```

Through Docker:

```json
{ "mcpServers": { "asciicharts": { "command": "docker", "args": ["run", "-i", "--rm", "asciicharts"] } } }
```

Against a running HTTP server:

```json
{ "mcpServers": { "asciicharts": { "url": "http://localhost:8080/mcp" } } }
```

## HTTP transport

Setting `PORT` switches the server from stdio to a long-running HTTP server, so one instance can serve many clients:

- `/mcp` — the [streamable-HTTP MCP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#streamable-http); `list_charts` and `render_chart` behave exactly as over stdio
- `/healthz` — plain `200 ok`, for container/orchestrator probes

It runs in **stateless** mode: no session tracking, no server-initiated messages — the server never needs to push anything outside of answering a tool call, so there is no session state worth keeping between requests. It binds `0.0.0.0` and does not enable the SDK's DNS-rebinding (Host header) check, which assumes a localhost-only server; put it behind your reverse proxy/ingress and restrict access there.

## Statistics (optional, off by default)

The server can record anonymous usage statistics in Postgres. **It does nothing of the kind unless you turn it on**, and it needs both settings:

| variable | value |
|---|---|
| `ASCIICHARTS_STATS` | `on` (also `1`, `true`, `yes`) — anything else, or unset, means off |
| `DATABASE_URL` | a standard Postgres DSN, e.g. `postgres://user:pass@host:5432/db` |

With both set, the server connects on startup, creates its schema if missing (`chart_events` — see `server/store.py`) and records one row per `render_chart` call: chart type, style, border, color on/off, series count, bucketed point count and output size, success/failure, and the error message on failure.

It never records the data you chart — no `values`, `labels` or `title`. Statistics can never stop the server from working: if the flag is on but `DATABASE_URL` is missing, `asyncpg` isn't installed, or the database is unreachable, the server logs a warning and runs without them; a failed insert is logged and ignored. The startup log says which way it went (`usage statistics: enabled` / `disabled`).

```sh
ASCIICHARTS_STATS=on DATABASE_URL=postgres://user:pass@localhost:5432/db python -m asciicharts_server
```

**Local dev stack.** `deploy/docker-compose.yml` exists to exercise this, so it starts Postgres and turns statistics **on** (set `ASCIICHARTS_STATS=off` to run it without). Copy `deploy/.env.example` to `deploy/.env` to override the Postgres credentials:

```sh
docker compose -f deploy/docker-compose.yml up -d --build
```

That publishes `db` on `localhost:5432` and `web` on `localhost:8080` (`/mcp`, `/healthz`), with `web`'s `DATABASE_URL` already wired to `db`. To run the server yourself against just the database: `docker compose -f deploy/docker-compose.yml up -d db`, then set the two variables above.

**Production stack.** `deploy/docker-compose.prod.yml` starts only Caddy and the server by default — no database, no statistics. To enable them, set in `deploy/.env`:

```
ASCIICHARTS_STATS=on
COMPOSE_PROFILES=stats        # starts the db service
POSTGRES_PASSWORD=<strong secret>
```
