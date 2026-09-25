# Development

## Repository layout

```
skills/asciicharts/     the skill: SKILL.md, scripts/, references/, .claude-plugin/ — see docs/skill.md
spec/                   the principles (principles.md, v1.1), CHANGELOG.md, LICENSE (CC BY 4.0)
test/                   everything that checks the project as a whole:
  conformance/            the language-neutral suite every implementation must pass byte for byte (CC BY 4.0)
  evals/                  the skill's evals: prompts, programmatic graders, recorded runs
  parity/                 Go against Python: differential.py, differential_csv.py, cli_parity.py
  test_*.py               pytest: the docs, the skill folder, the evals' grader
python/                 the Python implementation: asciicharts.py (the renderer and CLI, one file, standard library
                        only, also shipped inside the skill), pyproject.toml, tests/ (its own tests only)
go/                     the Go implementation: package asciicharts, cmd/asciicharts (CLI), cmd/asciicharts-mcp (the MCP
                        server — see go/cmd/asciicharts-mcp/README.md); its tests live next to the code, as Go wants
deploy/                 Dockerfile, docker-compose (dev and prod), Caddyfile, .env.example
scripts/                sync_skill.py, package_skill.py, gallery_refresh.py, site_examples.py, og_image.py,
                        conformance_refresh.py, gen_go_*.py
site/                   asciicharts.online
docs/                   this file, gallery.md (every chart rendered), skill.md
.claude-plugin/         the Claude Code plugin marketplace (one plugin: the skill)
LICENSE  ROADMAP.md
```

## Setup

Python 3.10+ (developed and tested on 3.12) and Go 1.25+.

```sh
python -m venv .venv
.venv/bin/pip install -e "./python[dev]"      # Windows: .venv\Scripts\pip — only pytest; asciicharts.py needs nothing
```

## Run

Render a chart from JSON:

```sh
echo '{"chartType":"sparkline","series":[{"values":[1,3,2,5]}]}' | python python/asciicharts.py -
python python/asciicharts.py --list    # every chart type with an example spec
```

Run the MCP server:

```sh
cd go
go run ./cmd/asciicharts-mcp              # stdio — meant to be launched by an MCP client
PORT=8080 go run ./cmd/asciicharts-mcp    # streamable HTTP at :8080/mcp, health check at /healthz
```

## Tests

```sh
pytest python/tests test   # from the root: the Python implementation, then the project-wide checks
cd go && go test ./...     # the Go library, CLI and MCP server (they read test/conformance/ too)
```

Both implementations are held to one suite, **`test/conformance/`**: the Python tests and the Go tests read
the same files. Neither runs the other's tests; `test/parity/` compares them directly.

`python/tests/` — the Python implementation:

- `test_charts.py` — the renderers against the conformance suite: the gallery, 317 random specs and 107
  curated cases with their exact output, so every chart is pinned byte-for-byte. If you change how
  something is drawn on purpose, that is a new version of the principles: `python scripts/conformance_refresh.py`
  reports which cases change (by chart type), `--write` writes them; review the diff and add an entry to
  `spec/CHANGELOG.md`.
- `test_csv.py` — CSV input (`--csv`); `test_catalog.py` — the chart catalogue (`list_charts` / `--list`)
  against the renderers; `test_ascii_style.py`, `test_version.py`.
- `test_excsv.py` — [ExCSV](https://github.com/boligolov/excsv) input: `#chart` suggestions resolved into a
  spec (`--chart-name`/`--list-charts`, `spec_from_excsv`), checked in part against `golden/excsv_fixtures/` —
  that format's own `#chart` fixtures, copied verbatim (CC0), so it is tested against the format's ground
  truth rather than only our own assumptions about it.

`test/` — the project as a whole:

- `test_skill.py` — the skill folder: valid frontmatter, self-contained links, the commands `SKILL.md` shows
  actually run and its example output is current, the plugin manifests (and `claude plugin validate`, when
  the CLI is installed), the site's `asciicharts.skill` is the current skill.
- `test_docs.py` — the docs: every printed chart is current and rectangular, links, the generated Go files.
- `test_hand_grader.py` — the grader of the hand-drawn evals is itself right.

### The skill folder

`skills/asciicharts/` must be self-contained (it is copied, zipped or uploaded on its own), but the renderer and the licence live outside it because the tests and pip use them. So the skill holds *copies*: after editing `asciicharts.py` or `LICENSE`, run

```sh
python scripts/sync_skill.py
```

`test/test_skill.py` fails when the copies differ. `references/reference.md` is edited in place. The gallery is `docs/gallery.md` (after changing how anything is drawn or adding an example, `python scripts/gallery_refresh.py` re-renders every printed output — in the gallery and in the skill's `references/drawing.md` — and rebuilds the gallery's contents list; a test fails if either is stale) and `python scripts/sync_skill.py` copies it, and `spec/principles.md`, into the skill.

## The Go implementation

`go/` holds the Go reference implementation, byte-for-byte identical to the Python one: the library
(`go/asciicharts`), the command line (`go/cmd/asciicharts`) and the MCP server (`go/cmd/asciicharts-mcp`).

```sh
cd go && go test ./...                                   # conformance suite (corpus, curated, gallery) + robustness + CLI + MCP server
go test -run '^$' -fuzz FuzzRenderJSON -fuzztime 60s ./asciicharts/
python test/parity/differential.py 10000 [seed]         # from the root: Go vs Python on random specs
python test/parity/differential_csv.py 10000 [seed]     # … on random CSV files (--csv)
python test/parity/cli_parity.py                        # both command lines: stdout, stderr, exit code
```

Two of its files are generated from the Python implementation, so both measure text and describe charts
identically: `python scripts/gen_go_unicode.py` (display-width tables from `unicodedata`) and
`python scripts/gen_go_catalog.py` (the chart catalogue). A Python test fails if either is stale. The MCP
server's tools are defined in `go/cmd/asciicharts-mcp/tools.json`, and its answers are pinned by
`go/cmd/asciicharts-mcp/testdata/` (recorded from the Python server it replaced). A change
to how charts are drawn goes into both implementations in the same change, with the conformance suite
regenerated (`scripts/conformance_refresh.py`) and `test/parity/differential.py` run; a change to the CSV
reader or the command line, in both too, with `test/parity/differential_csv.py` and `test/parity/cli_parity.py`.

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

The image holds nothing but the static binary (`FROM scratch`), so no `curl`; `asciicharts-mcp healthcheck` is a subcommand of the server itself that GETs its own `/healthz` and exits 0/1 (used by the compose files in `deploy/`).

## Production deployment

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
- **No authentication.** The server is meant to be a public utility: both tools are stateless and bounded (see [Limits](../skills/asciicharts/references/reference.md#limits)), and it stores nothing, not even counters. If you need it private, put access control in front (Caddy `basic_auth`, an IP allow-list, or your platform's ingress).
- **DNS-rebinding protection** (the Go MCP SDK's default): a request that arrives on a loopback address must name a localhost host. Caddy reaches the server over the compose network, not loopback, so your domain works.

To try the whole stack locally without a domain, set `DOMAIN=localhost` (Caddy issues a certificate from its own CA, so clients must trust it or skip verification).

## Using it from an MCP client

Local process (`go install github.com/boligolov/asciicharts/go/cmd/asciicharts-mcp@latest` puts it on the PATH):

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

It runs in **stateless** mode: no session tracking, no server-initiated messages — the server never needs to push anything outside of answering a tool call, so there is no session state worth keeping between requests. It listens on all interfaces; a request that arrives on a loopback address must name a localhost host (the SDK's DNS-rebinding protection). Put it behind your reverse proxy/ingress and restrict access there.

