# Roadmap: knowledge first

This file is the working plan for turning the repository around. It is written so that work can resume
from it alone, in a new session, without the conversation that produced it. Update the **Status** of a
step (and the log at the bottom) in the same commit that finishes it.

## The concept

The cornerstone of this repository is **knowledge**: the principles of building charts out of text
characters — the cell model, the glyph alphabet and ink density, the arithmetic, the layout rules, and
the mistakes behind them (`docs/principles.md` today). Everything else serves it:

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
go/                       MIT — go.mod, package asciicharts, cmd/asciicharts (CLI), MCP server
skills/asciicharts/       the skill (draw first, tool when available)
site/                     the landing page
scripts/                  repository tooling (gallery, site examples, skill sync/package, og image)
docs/                     gallery.md, development.md, skill.md
deploy/                   Docker/compose (switches to the Go server in phase 6)
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
- [ ] **1.5** Run the evals (with the skill / without it, several prompts, independent agents), record
      the results in `tests/skill_evals/README.md`, and adjust the tiers and recipes to what the numbers
      show.

Done when: tier-A charts pass the no-script evals reliably; tier C is routed to tools or clearly flagged.

## Phase 2 — The specification and the conformance suite

- [ ] **2.1** Create `spec/`: move `docs/principles.md` → `spec/principles.md`; mark it
      *asciicharts principles v1.0*; turn rules into MUST / SHOULD language where they are normative;
      keep the rationale, mistakes and examples.
- [ ] **2.2** `spec/CHANGELOG.md` (v1.0: the rules as of the fixes of 2026-09-24).
- [ ] **2.3** `spec/LICENSE` — CC BY 4.0; README and site state the split (knowledge CC BY 4.0, code MIT).
- [ ] **2.4** Move `tests/golden/{corpus.json, gallery.json, gallery.txt}` → `spec/conformance/`, with a
      `README.md` describing the format (`{spec, out}` or `{spec, err}`; gallery = named specs; exact
      bytes, `\n` line endings, no trailing newline) and how an implementation runs it. Python tests read
      from the new place. The ExCSV fixtures stay with the Python tests (input parsing, not rendering).
- [ ] **2.5** Update every reference: `scripts/sync_skill.py` (skill copy of the principles), links in
      README / docs / SKILL.md, `docs/development.md`.

Done when: `spec/` stands on its own, the Python suite passes against `spec/conformance/`.

## Phase 3 — Python moves to `python/`

- [ ] **3.1** `git mv` `asciicharts.py`, `pyproject.toml`, `server/`, `tests/` → `python/`. Repository
      tooling stays in `scripts/` and imports the renderer from `python/`.
- [ ] **3.2** Fix every path: `pyproject.toml` (package dirs, readme), `deploy/Dockerfile` (build context),
      `scripts/*` (ROOT / import path), skill sync (`python/asciicharts.py` → skill copy), README install
      instructions (`pip install ./python`), `docs/development.md`, `site/README.md`.
- [ ] **3.3** Verify: fresh venv, `pip install -e "./python[stats,dev]"`, full test suite, `docker build`,
      skill package build, site examples `--check`.

Done when: everything that worked from the root works from `python/`, and the repo root holds no Python
package files.

## Phase 4 — The Go library

- [ ] **4.1** `go/go.mod` (module `github.com/boligolov/asciicharts/go`), package `asciicharts`:
      `Render(spec Spec) (string, error)`, `ListCharts()`, typed `Spec`/`Series`, `ChartError`.
- [ ] **4.2** Port chart by chart, following the principles; a conformance test runs
      `spec/conformance/` and must match **byte for byte, including error messages**.
- [ ] **4.3** Parity details (see principles §14): half-away-from-zero rounding; left-to-right sums; stable
      sort in the largest-remainder method; `%.0f`/`%.2f` and the significant-digit rule; 12-significant-digit
      axis labels; display width — pin the Unicode version and test CJK/emoji/combining against Python's
      `unicodedata` results; limits and text sanitising identical.
- [ ] **4.4** Go tests beyond conformance: property tests (rectangular frames, no panics on hostile specs —
      the stress set from the MCP stress test).

Done when: 100% of `spec/conformance/` passes in Go.

## Phase 5 — The Go CLI

- [ ] **5.1** `go/cmd/asciicharts`: JSON spec (file / stdin / `--json`), `--list`, `--csv` with the same
      options and messages as the Python CLI (ExCSV: decide in this step — port, or later).
- [ ] **5.2** Release: static binaries for linux/macOS/windows (amd64/arm64), e.g. goreleaser + GitHub
      Releases; install instructions.
- [ ] **5.3** The skill learns the binary as a tool option (phase 1 flow already names it).

## Phase 6 — The MCP server in Go

- [ ] **6.1** Go MCP server with the official Go SDK: tools `list_charts` and `render_chart`, the same
      schema (strict types, limits), stdio and stateless streamable HTTP, `/healthz`.
- [ ] **6.2** Parity with the Python server's tests (in-process, stdio, HTTP) and the MCP stress test.
- [ ] **6.3** Optional anonymous usage statistics (Postgres) — port or drop; decide in this step.
- [ ] **6.4** `deploy/` switches to the Go image; the Python server is retired (removed from `python/`).

## Phase 7 — Positioning

- [ ] **7.1** README: lead with the principles (what text charts are and how to build them right), then
      the skill, then the implementations (Go CLI, Python, Go library, MCP).
- [ ] **7.2** Site: the principles as the hero; the gallery; "reference implementations" section; the
      licence split.
- [ ] **7.3** Package metadata and descriptions (pyproject, Go module README, skill description).

---

## Status log

| date | step | note |
|---|---|---|
| 2026-09-24 | plan | this roadmap written; decisions 1–5 recorded |
| 2026-09-24 | 1.1 | `drawing.md`: protocol, recipes for all 12 types by tier (A/B/C), worked arithmetic, frames, self-check; its 17 examples are checked against the renderer by `gallery_refresh.py --check` |
| 2026-09-24 | 1.2 | `glyphs.md`: safe alphabet by tier (WGL4), density ramp, series glyphs, roles, frames, widths; a test pins its glyph sets to the renderer's constants |
| 2026-09-24 | 1.3 | `SKILL.md` rewritten around the flow (pick → tool if available → else draw by hand → self-check → code block); chart table with hand-drawability tiers; the core rules; the script, CSV and ExCSV sections kept; `docs/skill.md` updated (no requirement to draw) |
| 2026-09-24 | 1.4 | `hand_evals.json` (7 prompts, tiers A/B/C) + `hand_grade.py` (lengths ±1, display-width frames, safe glyphs, series identity, shared zero line, sparkline order, percentages); `test_hand_grader.py` proves the grader on perfect and broken replies — it found a renderer bug (stacked bars dropped small segments, fixed in its own commit); `grade.py` measures display width too |
