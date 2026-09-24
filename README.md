# asciicharts

**[Read the principles →](spec/principles.md)** · **[See the gallery →](docs/gallery.md)** every chart type and style, rendered — real output.

**How to build charts out of text characters — right.** Bars, lines, areas, pies, heatmaps and box plots
drawn with nothing but characters, for the places images can't go: PR descriptions, incident channels, CI
logs, commit messages, terminals — and the replies of AI agents.

```
┌───────────────────────────────────────────────────────────┐
│                 Slowest endpoints, p99 ms                 │
├───────────────────────────────────────────────────────────┤
│ /upload   │ ████████████████████████████████████████ 4200 │
│ /search   │ ██████████████████░░░░░░░░░░░░░░░░░░░░░░ 1900 │
│ /checkout │ █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 950  │
└───────────────────────────────────────────────────────────┘
```

A text chart goes wrong in predictable ways: lengths are eyeballed instead of counted, a glyph missing from
the reader's font breaks the alignment, series differ only by a color the text doesn't have, a negative
value has nowhere to go. This repository is, first of all, the knowledge of how not to:

| | what | licence |
|---|---|---|
| **[The principles](spec/principles.md)** | *asciicharts principles v1.1*: the cell model, the font-safe glyph alphabet, the arithmetic, layout, text, the twelve chart types — and the mistakes behind each rule. Normative requirements in §15 | CC BY 4.0 |
| **[The conformance suite](spec/conformance/)** | 317 random specs, 107 curated cases and 31 documented examples with their exact expected output, byte for byte, language-neutral | CC BY 4.0 |
| **[The agent skill](docs/skill.md)** | teaches an agent to draw a correct text chart by hand, and to use a renderer when one is available | MIT |
| **Two reference implementations** | [Go](go/) — a single-binary command line, a library and an MCP server; [Python](python/) — one stdlib-only file, library and command line. Both pass the suite and agree byte for byte on random input | MIT |

## The principles

[`spec/principles.md`](spec/principles.md) is written so that anyone — a person, an agent, a port to another
language — can build text charts that are right:

- **The medium** (§1–3): a grid of equal cells; which glyphs survive every font (WGL4, not "Unicode");
  ink density; how series stay distinct without color.
- **The arithmetic** (§4): `cells = round(v / max × W)`, half away from zero; a non-zero value never
  disappears; stacks split by the largest remainder; the zero line is an axis owned by no bar.
- **Layout and text** (§5–6): frames, legends, axis labels that are the rows' real values; display width
  (CJK counts two columns, combining marks none).
- **Each chart type, style and limit** (§7–9), **the mistakes that made the rules** (§11), **drawing by hand**
  (§13), a **porting checklist** (§14) and **the requirements** (§15, MUST/SHOULD).

A chart conforms when it meets §15; a renderer conforms when it reproduces the
[conformance suite](spec/conformance/) byte for byte. Changes are versioned in
[`spec/CHANGELOG.md`](spec/CHANGELOG.md). The principles and the suite are CC BY 4.0: use them, adapt them,
build on them — with credit.

## The skill: an agent that draws charts right

A skill folder ([`skills/asciicharts`](skills/asciicharts/)) that an agent reads on demand. It picks the chart
for the question, uses a renderer if one is there (MCP server, `asciicharts` binary or the bundled Python
script) and otherwise **draws by hand** from a recipe per chart type: compute the lengths first, build rows
from counted runs of glyphs, then check.

```sh
cp -r skills/asciicharts ~/.claude/skills/          # Claude Code; Claude.ai and the API: docs/skill.md
```

It is measured, not assumed ([`skills/evals`](skills/evals/)): drawing by hand with no code allowed, a small
model went from 68% to 89% of the checks with the skill — code blocks, lengths, axes from the data; a strong
model was right with or without it, and with it drew smaller charts and showed its working.

## The implementations

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
pip install -e "./python[dev]" && pytest python/tests
cd go && go test ./...
```

Both implementations are pinned by the conformance suite and compared with each other on random specs, CSV
files and command lines; a change to how anything is drawn is a new version of the principles. How it all
fits together: [docs/development.md](docs/development.md); the plan: [ROADMAP.md](ROADMAP.md).

## License

The principles and the conformance suite in [`spec/`](spec/) are [CC BY 4.0](spec/LICENSE): use and adapt
them freely, with credit. The code — the skill, both implementations, the tools — is [MIT](LICENSE).

## Credits

The `halftone`/`ascii` bar styles and the `dotted` line style were reverse-engineered from Bloomberg
Businessweek's [**The Year Ahead 2016: 50 Companies to Watch**](https://www.bloomberg.com/graphics/year-ahead-2016/),
a scrollytelling piece that renders all of its charts as styled ASCII/Unicode art. For what a text chart
can look like, start there.
