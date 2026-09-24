# Roadmap: knowledge first

This file is the working plan for turning the repository around. It is written so that work can resume
from it alone, in a new session, without the conversation that produced it. Update the **Status** of a
step (and the log at the bottom) in the same commit that finishes it.

## The concept

The cornerstone of this repository is **knowledge**: the principles of building charts out of text
characters — the cell model, the glyph alphabet and ink density, the arithmetic, the layout rules, and
the mistakes behind them (`spec/principles.md`). Everything else serves it:

- **The specification** — the principles, made normative and versioned: *asciicharts principles v1.0*.
- **The conformance suite** — specs with their exact expected output (the golden corpus), language
  neutral. It is what makes the specification real: every implementation must pass it byte for byte.
- **The skill** — teaches an agent to draw a text chart itself from the principles, and to use a tool
  when one is available. Drawing by hand becomes the main path, not the fallback.
- **Two reference implementations** — Python (library, as today) and Go (library + a CLI binary).
- **The MCP server** — moves to Go.

We still love and maintain the Python library; we just no longer lead with it.

## Decisions (made 2026-09-24)

| # | question | decision |
|---|---|---|
| 1 | Monorepo layout | **Yes**: Python moves to `python/`, Go lives in `go/`, the spec in `spec/` |
| 2 | MCP server | **Moves to Go**; the Python server stays until the Go one reaches parity, then is retired |
| 3 | Licence of the knowledge | **CC BY 4.0** for `spec/` (principles, conformance data); code stays **MIT** |
| 4 | Name and version | **asciicharts principles v1.0** |
| 5 | Order of work | **skill + no-script evals → spec + conformance → Python to `python/` → Go library → Go CLI → Go MCP server → positioning (README, site)** |

## Target layout

```
spec/                     CC BY 4.0
  principles.md           the normative principles, v1.0 (MUST / SHOULD)
  CHANGELOG.md            versions of the principles
  LICENSE                 CC BY 4.0
  conformance/            corpus.json, gallery.json, gallery.txt + README (format)
python/                   MIT — asciicharts.py, pyproject.toml, tests/
go/                       MIT — go.mod, package asciicharts, cmd/asciicharts (CLI), cmd/asciicharts-mcp (MCP server)
skills/asciicharts/       the skill (draw first, tool when available)
site/                     the landing page
scripts/                  repository tooling (gallery, site examples, skill sync/package, og image)
docs/                     gallery.md, development.md, skill.md
deploy/                   Docker/compose of the Go MCP server (FROM scratch), Caddy for production
```

## Working rules (apply to every step)

- One logical change per commit. Commit messages end with the `Co-Authored-By` line.
- Work on a branch, not on `master`; the owner merges.
- Run the full test suite before every commit and read its last line: **a pipe (`| tail`) hides the exit
  code** — this already let a broken test into a commit once.
- A deliberate change in rendering: regenerate goldens, and check that every changed case is one the
  change is about (count them by chart type) before writing them.
- Examples in docs are generated from specs, never hand-edited (`scripts/gallery_refresh.py`,
  `scripts/site_examples.py`, `scripts/sync_skill.py`, each with `--check`).
- On Windows, Python writes CRLF by default: write files with `newline="\n"`. Heredocs mangle `\n` inside
  Python strings — put non-trivial edit scripts in a file.

---

## Phase 1 — The skill: draw first, tool when available

Goal: an agent with the skill and **no** way to run code produces correct charts for the common cases,
and knows when to use a tool (or warn) for the rest. Proven by evals, not assumed.

A key insight to design around: **models are bad at counting characters.** A bar of 17 `█` next to one of
6, a right border at column 60 — that is where hand-drawn charts go wrong. So the recipes reduce drawing
to arithmetic written out first (cells per bar, rows per column), then strings built by repetition,
then an explicit count-and-compare self-check.

Hand-drawability tiers (to be confirmed by the evals):

| tier | charts | guidance |
|---|---|---|
| A — reliable by hand | sparkline, hbar (≤ 10 bars, width 10–20), small vbar, dotplot | draw it |
| B — careful by hand | line (small grid), area, histogram (compute bins first), boxplot (compute quartiles first), small heatmap, scatter with a few points | draw it, keep it small, self-check |
| C — use a tool | pie (→ a 100% stacked bar), dual_axis (→ two small line charts), anything large | tool if available; else the simpler equivalent, and say so |

Steps:

- [x] **1.1** `skills/asciicharts/references/drawing.md` — a recipe for each of the 12 chart types,
      ordered by tier: inputs, the numbers to compute (with formulas from the principles), the strings to
      build, a worked example with real renderer output, and the specific self-check.
- [x] **1.2** `skills/asciicharts/references/glyphs.md` — a one-screen cheat sheet: safe alphabet (tiers,
      WGL4 box drawing), density ramp, series glyphs, glyph roles, borders, the ASCII style.
- [x] **1.3** Rewrite `SKILL.md` around the flow: choose the chart → is a tool available (MCP
      `asciicharts` → `asciicharts` binary → `python asciicharts.py`)? → otherwise follow `drawing.md`
      → self-check → answer in a fenced block. Stay under 500 lines; principles/drawing/glyphs are
      references, loaded on demand.
- [x] **1.4** No-script evals in `tests/skill_evals/`: prompts that forbid running code; a programmatic
      grader that checks a rectangular frame **by display width** (the current `grade.py` uses `len()` —
      the same bug we fixed in the renderer), bar lengths within ±1 cell of `round(v / max × W)`, glyph
      safety, legend-glyph agreement, value labels.
- [x] **1.5** Run the evals (with the skill / without it, several prompts, independent agents), record
      the results in `tests/skill_evals/README.md`, and adjust the tiers and recipes to what the numbers
      show.

- [x] **1.6** The harder test 1.5 pointed to: the same seven prompts with a **weaker model** (e.g. Haiku), plus
      harder prompts where counting fails — 10+ bars, stacked with negatives, a requested frame, CJK labels,
      a line on a larger grid. Only there can the principles show what they are worth for correctness.

Done when: tier-A charts pass the no-script evals reliably; tier C is routed to tools or clearly flagged.

## Phase 2 — The specification and the conformance suite

- [x] **2.1** Create `spec/`: move `docs/principles.md` → `spec/principles.md`; mark it
      *asciicharts principles v1.0*; turn rules into MUST / SHOULD language where they are normative;
      keep the rationale, mistakes and examples.
- [x] **2.2** `spec/CHANGELOG.md` (v1.0: the rules as of the fixes of 2026-09-24).
- [x] **2.3** `spec/LICENSE` — CC BY 4.0; README and site state the split (knowledge CC BY 4.0, code MIT).
- [x] **2.4** Move `tests/golden/{corpus.json, gallery.json, gallery.txt}` → `spec/conformance/`, with a
      `README.md` describing the format (`{spec, out}` or `{spec, err}`; gallery = named specs; exact
      bytes, `\n` line endings, no trailing newline) and how an implementation runs it. Python tests read
      from the new place. The ExCSV fixtures stay with the Python tests (input parsing, not rendering).
- [x] **2.5** Update every reference: `scripts/sync_skill.py` (skill copy of the principles), links in
      README / docs / SKILL.md, `docs/development.md`.

Done when: `spec/` stands on its own, the Python suite passes against `spec/conformance/`.

## Phase 3 — Python moves to `python/`

- [x] **3.1** `git mv` `asciicharts.py`, `pyproject.toml`, `server/`, `tests/` → `python/`. Repository
      tooling stays in `scripts/` and imports the renderer from `python/`.
- [x] **3.2** Fix every path: `pyproject.toml` (package dirs, readme), `deploy/Dockerfile` (build context),
      `scripts/*` (ROOT / import path), skill sync (`python/asciicharts.py` → skill copy), README install
      instructions (`pip install ./python`), `docs/development.md`, `site/README.md`.
- [x] **3.3** Verify: fresh venv, `pip install -e "./python[stats,dev]"`, full test suite, `docker build`,
      skill package build, site examples `--check`.

Done when: everything that worked from the root works from `python/`, and the repo root holds no Python
package files.

## Phase 4 — The Go library

- [x] **4.1** `go/go.mod` (module `github.com/boligolov/asciicharts/go`), package `asciicharts`:
      `Render(spec Spec) (string, error)`, `ListCharts()`, typed `Spec`/`Series`, `ChartError`.
- [x] **4.2** Port chart by chart, following the principles; a conformance test runs
      `spec/conformance/` and must match **byte for byte, including error messages**.
- [x] **4.3** Parity details (see principles §14): half-away-from-zero rounding; left-to-right sums; stable
      sort in the largest-remainder method; `%.0f`/`%.2f` and the significant-digit rule; 12-significant-digit
      axis labels; display width — pin the Unicode version and test CJK/emoji/combining against Python's
      `unicodedata` results; limits and text sanitising identical.
- [x] **4.4** Go tests beyond conformance: property tests (rectangular frames, no panics on hostile specs —
      the stress set from the MCP stress test).

Done when: 100% of `spec/conformance/` passes in Go.

## Phase 5 — The Go CLI

- [x] **5.1** `go/cmd/asciicharts`: JSON spec (file / stdin / `--json`), `--list`, `--csv` with the same
      options and messages as the Python CLI (ExCSV: decided — later, step 5.4).
- [x] **5.2** Release: static binaries for linux/macOS/windows (amd64/arm64), e.g. goreleaser + GitHub
      Releases; install instructions. (Done as a plain workflow, `release-go.yml`, on tags `go/vX.Y.Z`;
      **first real run pending** — it happens on the first tag push.)
- [x] **5.3** The skill learns the binary as a tool option (phase 1 flow already names it).
- [ ] **5.4** ExCSV in Go (`#!excsv` files: `#column` roles, `#chart` suggestions, `--chart-name`,
      `--list-charts`), checked against the Python reader on `python/tests/golden/excsv_fixtures`. Until
      then the Go CLI refuses an ExCSV file with a message that points to the Python CLI.

## Phase 6 — The MCP server in Go

- [x] **6.1** Go MCP server with the official Go SDK: tools `list_charts` and `render_chart`, the same
      schema (strict types, limits), stdio and stateless streamable HTTP, `/healthz`.
- [x] **6.2** Parity with the Python server's tests (in-process, stdio, HTTP) and the MCP stress test.
- [x] **6.3** Optional anonymous usage statistics (Postgres) — port or drop; decide in this step. (Dropped.)
- [x] **6.4** `deploy/` switches to the Go image; the Python server is retired (removed from `python/`).

## Phase 7 — Positioning

- [x] **7.1** README: lead with the principles (what text charts are and how to build them right), then
      the skill, then the implementations (Go CLI, Python, Go library, MCP).
- [x] **7.2** Site: the principles as the hero; the gallery; "reference implementations" section; the
      licence split.
- [x] **7.3** Package metadata and descriptions (pyproject, Go module README, skill description).

---

## Status log

| date | step | note |
|---|---|---|
| 2026-09-24 | plan | this roadmap written; decisions 1–5 recorded |
| 2026-09-24 | 1.1 | `drawing.md`: protocol, recipes for all 12 types by tier (A/B/C), worked arithmetic, frames, self-check; its 17 examples are checked against the renderer by `gallery_refresh.py --check` |
| 2026-09-24 | 1.2 | `glyphs.md`: safe alphabet by tier (WGL4), density ramp, series glyphs, roles, frames, widths; a test pins its glyph sets to the renderer's constants |
| 2026-09-24 | 1.3 | `SKILL.md` rewritten around the flow (pick → tool if available → else draw by hand → self-check → code block); chart table with hand-drawability tiers; the core rules; the script, CSV and ExCSV sections kept; `docs/skill.md` updated (no requirement to draw) |
| 2026-09-24 | 1.4 | `hand_evals.json` (7 prompts, tiers A/B/C) + `hand_grade.py` (lengths ±1, display-width frames, safe glyphs, series identity, shared zero line, sparkline order, percentages); `test_hand_grader.py` proves the grader on perfect and broken replies — it found a renderer bug (stacked bars dropped small segments, fixed in its own commit); `grade.py` measures display width too |
| 2026-09-24 | 1.5 | 14 runs (7 prompts × with/without skill, same model): 37/37 both. A strong model draws small charts right without the skill; the skill's effects were smaller charts, tier-C routing, visible self-checks, at ~+40% tokens. The grader was fixed to be layout-agnostic (4 correct baseline charts had failed it); the skill's glyph rule was made consistent. Next: weaker model + harder prompts (1.6) |
| 2026-09-24 | 2.1–2.5 | `spec/`: principles.md is *asciicharts principles v1.0* (§0 status, RFC 2119 key words, two kinds of conformance; §15 = requirements R1–R15), CHANGELOG.md, LICENSE (CC BY 4.0); goldens moved to `spec/conformance/` with a README of the exact format; `scripts/conformance_refresh.py` (report / `--write`); every reference updated; README and site footer state the licence split. 1.6 postponed (tokens) |
| 2026-09-24 | 3.1–3.3 | `asciicharts.py`, `pyproject.toml`, `server/`, `tests/` → `python/` (with `python/README.md` and a synced `python/LICENSE`); the skill's evals → `skills/evals/`; repository scripts import from `python/`; `sync_skill.py` keeps (source, copy) pairs; Dockerfile, `.dockerignore`, README, docs, site updated. Verified: a fresh venv `pip install -e ./python[stats,dev]` passes 675/675, skill package builds, derived files current, site builds. **Not verified: `docker build`** (Docker daemon was not running) — run it before relying on the image |
| 2026-09-24 | 4.1–4.4 | `go/` (module `github.com/boligolov/asciicharts/go`, package `asciicharts`, stdlib only): RenderJSON/Render/ListCharts/ChartTypes/ChartError. Passes the whole conformance suite byte for byte — 317 corpus + 104 curated (new: `spec/conformance/curated.json`, text in any script, controls, number formatting, every validation message) + 31 gallery — and 30 000/30 000 random specs against Python (`scripts/differential.py`). Unicode tables and catalogue generated from Python (`gen_go_unicode.py`, `gen_go_catalog.py`, checked by a test). Robustness: hostile specs, 1 000 random specs rectangular, 8.8M fuzz executions without a panic |
| 2026-09-24 | 5.1 | `go/cmd/asciicharts` (exit codes 0/1/2 as Python's) + in the library `SpecFromCSV`, `ParseSet`, `ListText`, an ordered `Object` with `PyJSON` (Python's `json.dumps`). The CSV reader ports CPython's `csv.Sniffer` (its backreference regexes by hand) and `_csv` state machine, Python's `float()` (underscores, Unicode digits), `str.lower()` (final sigma, İ). Checked: `scripts/differential_csv.py` 100 000/100 000 random CSV files (spec text and chart), `scripts/cli_parity.py` 42/42 command lines (stdout, stderr, exit code). Found a real divergence in the library: Go's `math.Log10` is an ulp off next to a power of ten (a histogram edge printed `-0.10` for Python's `-0.100`) → correctly rounded `floorLog10`; principles §4.13 clarified, curated case `number/next to a power of ten` (105). ExCSV → 5.4 |
| 2026-09-24 | 5.2 | `.github/workflows/release-go.yml`: on a `go/v*` tag — `go test`, tag = `asciicharts --version`, six static binaries (CGO off, `-trimpath -s -w`, ~3.3 MB) as tar.gz/zip with README + LICENSE, `checksums.txt`, `gh release create`. Not goreleaser: its free version can't read the `go/`-prefixed tags a Go module in a subdirectory needs. Verified locally: the build script (all six targets, archives, checksums) and `go test` on Go 1.22 (the workflow's toolchain, from go.mod). **Not verified: the workflow on GitHub** (needs a tag push) |
| 2026-09-24 | 5.3 | `SKILL.md`: the `asciicharts` command is its own step of the flow (after MCP, before Python: `asciicharts --version` works → same arguments and bytes as the script, ExCSV only in the script); frontmatter `compatibility`/`description` and `docs/skill.md` name it. 782/782 Python tests, skill package rebuilt |
| 2026-09-24 | 6.1–6.2 | `go/cmd/asciicharts-mcp` on the official Go SDK (v1.8.0): stdio, stateless streamable HTTP at `/mcp`, `/healthz`, `healthcheck` subcommand. Tool definitions generated from the Python server (`scripts/gen_go_mcp_tools.py`, staleness checked by a test) and served verbatim; arguments validated against that schema (jsonschema-go) plus pydantic's strictness (`40.0` is not an integer), then shaped as the Python server does (known fields only, nulls dropped, values as floats). `python/tests/test_go_server.py`: the Python server's own `check_tools` over Go stdio and HTTP; identical `tools/list` and `list_charts`; 750 random `render_chart` calls (498 charts and 115 chart errors byte for byte, 137 invalid calls rejected by both) plus 4 edge cases (float width, extra fields, nulls). The module now needs Go 1.25 (the SDK); the library package still imports only the standard library. Stats: the Go server ignores `ASCIICHARTS_STATS` with a warning until 6.3 is decided |
| 2026-09-24 | 6.3–6.4 | Decided by the owner: statistics dropped, the Python server retired (no production existed). Before deleting it, its answers were recorded as the Go server's tests: `go/cmd/asciicharts-mcp/testdata/` (754 `render_chart` calls, `list_charts`); the tool definitions became `tools.json` (embedded, edited by hand from now on); stdio, HTTP and `healthcheck` are tested in Go (the test binary re-runs itself as the server). Removed: `python/server/`, its tests and the stats store, `mcp`/`asyncpg` dependencies (the Python package now depends on nothing), `gen_go_mcp_tools.py`, Postgres from `deploy/`. `deploy/Dockerfile` builds the Go server into a `FROM scratch` image; release archives carry both binaries. New `go/cmd/asciicharts-mcp/README.md` (the old server guide, for Go); README, docs, site updated. Checked: `go test ./...`, 746 Python tests, site build. **Not verified: `docker build`** (Docker daemon not running) |
| 2026-09-24 | 1.6 | Haiku on all 11 prompts (the 7 of 1.5 + 4 harder: 14 framed bars, stacked with negatives, CJK labels in a frame, a 14-point line 12 rows tall) and the strong model on the 4 harder ones, with/without the skill, 30 independent agents. Haiku: **59/66 (89%) with the skill, 45/66 (68%) without** — the skill fixed code blocks (6 of 11 baseline replies had none), bar lengths, data-driven axes, tier-C routing. Strong model: 29/29 vs 28/29 — it draws even the harder charts right without the skill. What the skill did not fix for Haiku: column counting (5 of its 7 misses: an axis one column off in one row, frames broken by a long or CJK label) → two new self-check items in `drawing.md`. The grader was wrong three times first (unfenced charts cascaded to zeros, numbered rows and `░` as a named series unread, `"" in "┌╭╔┏"` making blank lines frame corners) — each fix is a test; 1.5's replies still grade 37/37. Open for the principles: stacked bars with negatives draw no zero line (the renderer) while §4.5 says the zero line stays visible on every row. Results: `skills/evals/README.md`; replies: `skills/evals/runs/2026-09-24-hand-1.6/` |
| 2026-09-24 | v1.1 | Decided by the owner: stacked bars with negatives draw their zero axis (`¦`/`+` in hbar, a `-` row in vbar), owned by no bar — the renderer now meets its own R6. Both implementations, principles §4.6, CHANGELOG, 6 corpus + 2 new curated cases (107), gallery, site, the MCP server's recorded answers (3); Go = Python on 20 000 random specs |
| 2026-09-24 | skill | Leaner skill: `SKILL.md` 1 920 → 1 279 words (same workflow, table, rules, commands, CSV/ExCSV); `drawing.md` trimmed of what `SKILL.md` already says, the "for reference" renders of pie and dual_axis dropped, the self-check merged, the v1.1 stacked-negatives recipe added (3 613 → 3 397 words); hand drawing now reads only `drawing.md` + `glyphs.md` (`principles.md`, ~10k words, only for the why). Re-run: Haiku on the four hard prompts 25/29 (was 24/29), stacked 8/8 (was 6/8) |
| 2026-09-24 | 7.1–7.3 | README leads with the principles (what they cover, the suite, CC BY), then the skill (with the eval numbers), then the implementations: the `asciicharts` binary, Python, the Go library, the MCP server; all examples rendered (the stale v1.0 stacked example replaced). Site: hero "How to build charts out of text characters — right", a Principles section, "the reference implementations", four ways in (skill, command line, library, MCP), stats v1.1 / 455 conformance cases / 2 implementations / 12 chart types. pyproject description, keywords, principle/gallery URLs. **Not checked by eye:** the site below the hero (the browser froze; the build and the HTML are fine) |
