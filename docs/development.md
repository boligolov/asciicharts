# Development

## Repository layout

```
skills/asciicharts/     the skill — the main product: SKILL.md, references/, scripts/, .claude-plugin/ (see below)
docs/                   the documentation (this folder; an index: docs/README.md)
  spec/                   the principles (principles.md, v1.1), CHANGELOG.md, LICENSE (CC BY 4.0)
  skill.md                installing the skill
  gallery.md              every chart rendered, with its spec
  development.md          this file
test/                   everything that checks the project as a whole
  conformance/            the language-neutral suite every implementation must pass byte for byte (CC BY 4.0)
  evals/                  the skill's evals: prompts, programmatic graders, recorded runs
  parity/                 Go against Python: differential.py, differential_csv.py, cli_parity.py
  test_*.py               pytest: the docs, the skill folder, the evals' grader
python/                 the Python renderer: asciicharts.py (renderer and CLI, one stdlib-only file, also shipped
                        inside the skill), pyproject.toml, tests/ (its own tests)
go/                     the Go renderer: package asciicharts, cmd/asciicharts (CLI), cmd/asciicharts-mcp (the MCP
                        server); its tests live next to the code, as Go wants
site/                   asciicharts.online (Astro); serves the skill's download, site/public/asciicharts.skill
deploy/                 Dockerfile, docker-compose (local and production), Caddyfile — see the MCP server's README
scripts/                sync_skill.py, package_skill.py, gallery_refresh.py, site_examples.py, og_image.py,
                        conformance_refresh.py, gen_go_*.py
.claude-plugin/         the Claude Code plugin marketplace (one plugin: the skill)
LICENSE  ROADMAP.md  pytest.ini
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
  `docs/spec/CHANGELOG.md`.
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

## The skill

`skills/asciicharts/` must be self-contained — it is copied, zipped or uploaded on its own — so it holds
*copies* of files that live elsewhere: `scripts/asciicharts.py` (from `python/`), `LICENSE`,
`references/principles.md` (from `docs/spec/`) and `references/gallery.md` (from `docs/`). After editing an
original:

```sh
python scripts/sync_skill.py        # refresh the copies (a test fails while one differs)
python scripts/gallery_refresh.py   # after a rendering change: re-render every printed example, in docs/gallery.md
                                    # and in references/drawing.md (a test fails while one is stale)
```

`references/drawing.md`, `glyphs.md` and `reference.md` are edited in place; `drawing.md`'s examples are
still printed by `gallery_refresh.py`. How much the skill helps is measured in `test/evals/` (see its
README): run those before and after a change to what the skill tells the agent. Every change to the skill is a new version of it: see [Releasing](#a-new-version-of-the-skill).

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

The MCP server — running it, Docker, production behind Caddy, connecting clients, the HTTP transport — is
documented in [go/cmd/asciicharts-mcp/README.md](../go/cmd/asciicharts-mcp/README.md).

## Releasing

### A new version of the skill

The skill has a version in two places that must agree (a test checks): `metadata.version` in
`SKILL.md`'s frontmatter and `version` in `skills/asciicharts/.claude-plugin/plugin.json`. Claude Code offers
plugin users an update only when that version goes up, so **every change to `skills/asciicharts/` bumps it**
(semver: `0.0.2` for a fix or a wording change, `0.1.0` for something new). Then, one command:

```sh
python scripts/package_skill.py --site      # rebuilds dist/asciicharts.skill and site/public/asciicharts.skill
```

and commit the result with the change. The site's download is committed, so a test fails while it is older
than the skill; deploy the site afterwards so asciicharts.online serves the new package.

### The site

asciicharts.online is built from `site/` (`npm run build`; see [site/README.md](../site/README.md)) and deployed
by the owner. Its charts come from `scripts/site_examples.py` (committed as `site/src/data/charts.json`, a test
fails while it is stale) and its download is the committed `site/public/asciicharts.skill`. Deploy after a
change to either.

### The Go binaries

Set `Version` in `go/asciicharts/render.go`, then push a tag `go/vX.Y.Z` with the same version:
`.github/workflows/release-go.yml` tests, checks the tag against `asciicharts --version`, builds the command
line and the MCP server for Linux, macOS and Windows (amd64/arm64), and publishes them with `checksums.txt`
as a GitHub release.

### Listing it in Claude's plugin directories

Anthropic runs two public marketplaces: `claude-plugins-official` (curated by Anthropic, no application) and
`claude-community` (third-party plugins, after review). To submit this plugin to the community one, the
repository must be public on GitHub and pass `claude plugin validate .` (a test runs it); then submit the
repository link through the Console form, [platform.claude.com/plugins/submit](https://platform.claude.com/plugins/submit)
(or, for a Team or Enterprise organization, the claude.ai directory form). Once approved it is pinned to a
commit in [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) and
follows new commits automatically; users then install it with
`/plugin install asciicharts@claude-community`.
