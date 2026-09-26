# asciicharts

**[asciicharts.online](https://asciicharts.online)** · [the gallery](docs/gallery.md) · [the principles](docs/spec/principles.md)

**An agent skill for charts made of text characters — drawn right.** Ask Claude for a chart in a reply, a PR
description, a commit message or a terminal, and you get bars, lines, sparklines, histograms, pies or heatmaps
with lengths that match the values, frames that stay straight in any font, and series you can tell apart
without color.

## Install

**Claude Code** — from this repository, which is a plugin marketplace:

```
/plugin marketplace add boligolov/asciicharts
/plugin install asciicharts@asciicharts
```

**Claude.ai and Claude Desktop** — download **[asciicharts.skill](https://asciicharts.online/asciicharts.skill)**
and upload it under *Settings → Capabilities → Skills* (skills need code execution enabled).

**Any other agent that reads skill folders** — copy the folder:

```sh
git clone https://github.com/boligolov/asciicharts
cp -r asciicharts/skills/asciicharts ~/.claude/skills/
```

Then just ask — *"chart the p99 of these services"*, *"sparkline of the last 14 days"* — or give it a CSV
file. Scopes, the API, updating: [docs/skill.md](docs/skill.md).

## What it does

```
┌───────────────────────────────────────────────────────────┐
│                 Slowest endpoints, p99 ms                 │
├───────────────────────────────────────────────────────────┤
│ /upload   │ ████████████████████████████████████████ 4200 │
│ /search   │ ██████████████████░░░░░░░░░░░░░░░░░░░░░░ 1900 │
│ /checkout │ █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 950  │
└───────────────────────────────────────────────────────────┘
```

The skill picks the chart for the question, then uses an exact renderer if one is at hand — the
`asciicharts` command, the bundled Python script or the MCP server — and otherwise **draws by hand** from a
recipe per chart type: compute the lengths first, build each row from counted runs of glyphs, then check.
It needs nothing installed.

It is measured, not assumed ([`test/evals`](test/evals/)): drawing by hand with no code allowed, a
small model went from 68% to 89% of the checks with the skill — code blocks, bar lengths, axes that come
from the data, pies turned into proportional bars; a strong model was right with or without it, and with it
drew smaller charts and showed its working.

## The principles behind it

What the skill knows is written down in [`docs/spec/principles.md`](docs/spec/principles.md) — *asciicharts
principles v1.2*, for a person, an agent, or a port to another language:

- **The medium** (§1–3): a grid of equal cells; which glyphs survive every font (WGL4, not "Unicode");
  ink density; how series stay distinct without color.
- **The arithmetic** (§4): `cells = round(v / max × W)`, half away from zero; a non-zero value never
  disappears; stacks split by the largest remainder; the zero line is an axis owned by no bar.
- **Layout and text** (§5–6): frames, legends, axis labels that are the rows' real values; display width
  (CJK counts two columns, combining marks none).
- **Each chart type, style and limit** (§7–9), **the mistakes that made the rules** (§11), **drawing by hand**
  (§13), a **porting checklist** (§14) and **the requirements** (§15, MUST/SHOULD).

A chart conforms when it meets §15; a renderer conforms when it reproduces the
[conformance suite](test/conformance/) — 317 random specs, 110 curated cases, 31 documented examples —
byte for byte. Changes are versioned in [`docs/spec/CHANGELOG.md`](docs/spec/CHANGELOG.md). The principles and the
suite are CC BY 4.0: use them, adapt them, build on them — with credit.

## The renderers

Two reference implementations of the principles, byte for byte the same; the skill uses whichever is there,
and they work on their own too.


**The `asciicharts` command** — one static binary for Linux, macOS and Windows
([releases](https://github.com/boligolov/asciicharts/releases), or
`go install github.com/boligolov/asciicharts/go/cmd/asciicharts@latest`):

```sh
asciicharts spec.json                             # a JSON spec from a file, - for stdin, or --json '{...}'
asciicharts --csv latency.csv --chart hbar --values p99 --sort -p99 --limit 3 --set title="Slowest endpoints, p99 ms"
asciicharts --list                                # every chart type, how to fill it, an example
```

`--csv` reads a header row, detects `,` `;` tab or `|`, parses dirty numbers (`$1,200`, `12%`, decimal commas)
and reports a bad cell by row and column instead of dropping it. Negative values grow both ways from a
zero axis, stacked ones too:

```
┌────────────────────────────────────────────────────────┐
│                   Revenue vs refunds                   │
├────────────────────────────────────────────────────────┤
│ EMEA     │   ▓▓▓▓▓▓▓▓¦█████████████████████         25 │
│ APAC     │ ▓▓▓▓▓▓▓▓▓▓¦█████████████                 5  │
│ Americas │       ▓▓▓▓¦█████████████████████████████ 47 │
│                                                        │
│ █ Product   ▓ Refunds                                  │
└────────────────────────────────────────────────────────┘
```

**Python** — [`python/asciicharts.py`](python/asciicharts.py), one file of standard-library Python (3.10+):
copy it anywhere. The same command line (`python asciicharts.py …`, plus
[ExCSV](https://github.com/boligolov/excsv) files with their own `#chart` suggestions), and a library:

```python
from asciicharts import render_chart            # raises ChartError, a ValueError, with a one-line message
print(render_chart({"chartType": "sparkline", "series": [{"values": [4, 6, 5, 9, 3]}]}))
```

**Go library** — `github.com/boligolov/asciicharts/go/asciicharts`, standard library only:
`asciicharts.RenderJSON(spec)`. See [go/README.md](go/README.md).

**MCP server** — two tools, `list_charts` (the catalogue, with an example call per chart) and
`render_chart`, over stdio or stateless streamable HTTP; one static binary or a `FROM scratch` image:

```sh
go install github.com/boligolov/asciicharts/go/cmd/asciicharts-mcp@latest
claude mcp add asciicharts -- asciicharts-mcp
```

Client setup, HTTP, Docker and production (Caddy, HTTPS):
[go/cmd/asciicharts-mcp/README.md](go/cmd/asciicharts-mcp/README.md).

All of them are deterministic — a pure function of the spec: same input, same bytes, safe to snapshot and
diff — validate and bound their input (width ≤ 500, height ≤ 200, 50,000 values), and answer bad input
with one line that says what to fix.

## Charts

| `chartType` | use it for |
|---|---|
| `sparkline` | a trend inside a sentence or a log line |
| `hbar`, `vbar` | rankings and comparisons: single, grouped, stacked, diverging |
| `line`, `area` | time series, labelled thresholds, filled volume, stacked bands |
| `scatter`, `dotplot` | two numbers against each other; close values on an axis that needn't start at 0 |
| `dual_axis` | two series on different scales |
| `histogram`, `boxplot` | distributions from raw samples — bins and quartiles computed for you |
| `pie` | shares of a whole |
| `heatmap` | a matrix, e.g. hour × weekday |

Styles `solid`, `halftone`, `ascii`, `dotted` (line) and `fine`; six borders; an optional title; ANSI
colour on request. **[The gallery](docs/gallery.md)** shows every one — real output — and
**[the reference](skills/asciicharts/references/reference.md)** lists every option. Where the text may land
anywhere, `"style": "ascii", "border": "ascii"` uses nothing but plain characters:

```
+------------------------------------------------------------+
|                       Tests by suite                       |
+------------------------------------------------------------+
| unit        | ######################################## 480 |
| integration | ##########,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 120 |
| e2e         | ###,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 30  |
+------------------------------------------------------------+
```

## Fonts

Default output survives any font: whole `█` blocks, light box lines, glyphs that Consolas and Courier New
have. Two things need a fuller font — the eighth blocks of `"style": "fine"` and of sparklines — and fonts
without them (Consolas, Courier New, Lucida Console) borrow those glyphs from another font, which makes an
otherwise straight right border look crooked. Every line really has the same width; a ragged wall means the
font. GitHub and most terminals are fine; otherwise Cascadia Code, JetBrains Mono, Noto Sans Mono or DejaVu
Sans Mono.

## Development

```sh
pip install -e "./python[dev]" && pytest python/tests test
cd go && go test ./...
```

Both implementations are pinned by the conformance suite and compared with each other on random specs, CSV
files and command lines; a change to how anything is drawn is a new version of the principles. How it all
fits together: [docs/development.md](docs/development.md); the plan: [ROADMAP.md](ROADMAP.md).

## License

The principles in [`docs/spec/`](docs/spec/) and the conformance suite in [`test/conformance/`](test/conformance/) are [CC BY 4.0](docs/spec/LICENSE): use and adapt
them freely, with credit. The code — the skill, both implementations, the tools — is [MIT](LICENSE).

## Credits

The `halftone`/`ascii` bar styles and the `dotted` line style were reverse-engineered from Bloomberg
Businessweek's [**The Year Ahead 2016: 50 Companies to Watch**](https://www.bloomberg.com/graphics/year-ahead-2016/),
a scrollytelling piece that renders all of its charts as styled ASCII/Unicode art. For what a text chart
can look like, start there.
