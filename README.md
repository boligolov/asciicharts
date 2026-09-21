# asciicharts

**[See the gallery →](docs/gallery.md)** every chart type and style, rendered: bars (grouped, stacked, diverging), lines, areas, pies, heatmaps, box plots, Unicode and pure-ASCII looks. All real output.

**Charts for the places images can't go.** PR descriptions, incident channels, CI logs, commit messages, ssh sessions — and the replies of LLM agents. Numbers in, a monospace string out. One file, standard library only, nothing to install.

```sh
$ cat latency.csv
endpoint,p50,p99,errors
/login,120,480,3
/search,340,1900,12
/checkout,210,950,7
/health,5,9,0
/upload,800,4200,21

$ python asciicharts.py --csv latency.csv --chart hbar --values p99 --sort -p99 --limit 3 --set title="Slowest endpoints, p99 ms"
```

```
┌───────────────────────────────────────────────────────────┐
│                 Slowest endpoints, p99 ms                 │
├───────────────────────────────────────────────────────────┤
│ /upload   │ ████████████████████████████████████████ 4200 │
│ /search   │ ██████████████████                       1900 │
│ /checkout │ █████████                                950  │
└───────────────────────────────────────────────────────────┘
```

Paste that into a pull request, a Slack thread or a commit body and it lines up — it is just text.

## Why it earns a place in your toolbox

- **No dependencies, no install.** `asciicharts.py` is one ~1,800-line file of standard-library Python (3.10+, developed on 3.12). Copy it into a repo, a CI step or a gist. Only the optional MCP server needs a package (`mcp`); the renderer never does.
- **Deterministic.** A pure function of the spec: no clock, no randomness, no locale, no terminal probing. Same input, same bytes — safe to snapshot, diff and commit. 500+ tests pin the output byte-for-byte, including a corpus of 300+ generated specs.
- **Built to be called by machines.** Input is validated and bounded (width ≤ 500, height ≤ 200, 50,000 values, finite numbers only) and every error is one line that says what to fix — `error: row 3, column "v" is not a number: "n/a"` — so a script or an agent can correct itself. The skill was tuned against real agent runs ([`tests/skill_evals`](tests/skill_evals)).
- **Gets the cases hand-drawn charts get wrong.** Negative values grow both ways from a zero line, stacked ones too. Dirty CSV numbers (`$1,200`, `12%`, `1,234.5`, decimal commas) are parsed, and bad cells are reported by row and column instead of silently dropped. Many series stay tellable apart: 8 Unicode fills, 23 glyphs in pure ASCII.
- **Looks right where you paste it.** Font-safe defaults (whole `█` blocks, glyphs that even Consolas has), a pure-ASCII mode for terminals and mail, no ANSI escapes unless you ask.
- **No side effects.** The renderer writes nothing and opens no sockets. The server is stateless; usage statistics are off by default and never contain what you chart.

Two of the hard cases, straight from the CLI:

```sh
python asciicharts.py --json '{"chartType":"hbar","stacked":true,"width":40,"title":"Revenue vs refunds",
  "labels":["EMEA","APAC","Americas"],"series":[{"name":"Product","values":[40,25,55]},{"name":"Refunds","values":[-15,-20,-8]}]}'
```

```
┌────────────────────────────────────────────────────────┐
│                   Revenue vs refunds                   │
├────────────────────────────────────────────────────────┤
│ EMEA     │    ▓▓▓▓▓▓▓▓█████████████████████         25 │
│ APAC     │ ▓▓▓▓▓▓▓▓▓▓▓█████████████                 5  │
│ Americas │        ▓▓▓▓█████████████████████████████ 47 │
│                                                        │
│ █ Product   ▓ Refunds                                  │
└────────────────────────────────────────────────────────┘
```

Refunds hang left of the shared zero column, products stack right, and the number at the end is the net. And for anything that isn't a UTF-8 terminal, `"style": "ascii", "border": "ascii"` gives you nothing but plain characters:

```sh
python asciicharts.py --json '{"chartType":"hbar","style":"ascii","border":"ascii","title":"Tests by suite",
  "labels":["unit","integration","e2e"],"series":[{"values":[480,120,30]}]}'
```

```
+------------------------------------------------------------+
|                       Tests by suite                       |
+------------------------------------------------------------+
| unit        | ######################################## 480 |
| integration | ##########                               120 |
| e2e         | ###                                      30  |
+------------------------------------------------------------+
```

## Where it fits

- **Pull requests and commit messages.** Before/after benchmarks, test time by suite, bundle size by package.
- **Incident channels and on-call handoffs.** Top-N slow endpoints or error counts from a Grafana or SQL export: one command, pasted in.
- **CI logs and job summaries.** Deterministic text you can diff between runs or assert on in a test.
- **READMEs and docs without image files.** Charts that live in the repo, review in diffs and never go stale as binaries.
- **Terminals and ssh sessions.** No display, no browser, no X forwarding.
- **LLM agents.** Give the model a tool (MCP) or a skill and it stops hand-drawing misaligned bars.

## Charts

| `chartType` | use it for |
|---|---|
| `sparkline` | a trend inside a sentence or a log line |
| `hbar`, `vbar` | rankings and comparisons: single, grouped, stacked, diverging |
| `line`, `area` | time series, a dashed threshold, filled volume, stacked bands |
| `scatter`, `dotplot` | relationships between two numbers; values against each other on an axis that needn't start at 0 |
| `dual_axis` | two series on different scales |
| `histogram`, `boxplot` | distributions from raw samples — bins and quartiles are computed for you |
| `pie` | shares of a whole |
| `heatmap` | a matrix, e.g. hour × weekday |

Styles: `solid` (default), `halftone`, `ascii`, `dotted` (line), `fine` (eighth-block bar ends, needs a capable font). Six borders (`none`, `ascii`, `light`, `heavy`, `double`, `rounded`), a centred title, optional ANSI 256-colour. **[The gallery](docs/gallery.md)** shows every one; **[the reference](skills/asciicharts/references/reference.md)** lists every option.

## Three ways in

| | for | get started |
|---|---|---|
| **CLI / library** | scripts, CI, notebooks | copy `asciicharts.py` — nothing else needed |
| **[Agent skill](docs/skill.md)** | Claude Code and other agents with a shell | `cp -r skills/asciicharts ~/.claude/skills/` |
| **[MCP server](server/README.md)** | any MCP client; one shared always-on deployment | `pip install .` then `asciicharts-mcp` |

### CLI and library

```sh
python asciicharts.py spec.json                               # a JSON spec from a file ...
echo '{"chartType":"hbar", ...}' | python asciicharts.py -    # ... or from stdin
python asciicharts.py --csv data.csv --chart hbar --sort -latency --limit 10 --set title="Slowest"
python asciicharts.py --list                                  # every chart type, how to fill it, an example
```

`--csv` reads a header row, sniffs `,` `;` tab or `|`, and takes `--label`, `--values`, `--sort`, `--limit`, `--set key=value` and `--print-spec` (see the [skill docs](skills/asciicharts/SKILL.md#from-a-csv)). From Python:

```python
from asciicharts import render_chart, ChartError

print(render_chart({
    "chartType": "hbar",
    "title": "Build time by stage (s)",
    "labels": ["Compile", "Test", "Lint", "Package"],
    "series": [{"values": [64, 32, 16, 8]}],
}))                     # raises ChartError (a ValueError) with a one-line message on bad input
```

### Agent skill

A self-contained folder — `SKILL.md`, the one-file script, and references — that an agent finds by scanning a directory; there is no registry. It tells the agent which chart fits the question, how to feed it a CSV, and how to make the result read well. Install for Claude Code, Claude.ai or the API: **[docs/skill.md](docs/skill.md)**. To upload it: `python scripts/package_skill.py` → `dist/asciicharts.skill`.

### MCP server

Two tools: **`list_charts`** (the catalogue: every chart type, how to fill `series`, which options apply, an example call) and **`render_chart`**. stdio or stateless streamable HTTP.

```sh
pip install .                                     # or ".[stats]" for optional Postgres statistics
claude mcp add asciicharts -- asciicharts-mcp     # e.g. register it with Claude Code
PORT=8080 asciicharts-mcp                         # or serve HTTP: /mcp and /healthz
```

Arguments, transports, configuration, client setup: **[server/README.md](server/README.md)**.

## Deploy

```sh
docker build -f deploy/Dockerfile -t asciicharts .
docker run -i --rm asciicharts                                 # stdio
docker run --rm -e PORT=8080 -p 8080:8080 asciicharts          # HTTP → http://localhost:8080/mcp
```

Production is one command — Caddy in front (automatic HTTPS for your domain), a hardened container (read-only filesystem, all capabilities dropped, non-root), and nothing but ports 80/443 exposed:

```sh
cp deploy/.env.example deploy/.env        # set DOMAIN
docker compose -f deploy/docker-compose.prod.yml up -d --build      # → https://<DOMAIN>/mcp
```

The server has no authentication by design (it is a stateless utility bounded by the limits above); put access control in front if you need it. Anonymous usage statistics — chart type, style, size buckets, success/failure, never your data — are **off by default**; set `ASCIICHARTS_STATS=on` and `DATABASE_URL` to record them in Postgres. Details: **[docs/development.md](docs/development.md#production-deployment)**.

## Fonts

Default output is built to survive any font: bars end on whole `█` blocks, frames use light box-drawing lines, series use glyphs found in Consolas and Courier New, and `"style": "ascii"` / `"border": "ascii"` use nothing but plain characters. Two things need a font that has more: the eighth blocks of `"style": "fine"` (`▏▎▍▋▊▉`) and of sparklines (`▁▂▃▅▆▇`) are missing from Consolas, Courier New and Lucida Console, the default monospace fonts of many Windows editors, which then substitute another font for just those characters and make the right border of an otherwise rectangular chart look crooked. Every line really has the same number of characters (the tests check it) — a ragged wall means the font, not the generator. GitHub and most terminals (iTerm2, Windows Terminal, Ghostty, …) are fine; otherwise use Cascadia Code, JetBrains Mono, Noto Sans Mono or DejaVu Sans Mono, or stay with the defaults.

## Development

```sh
pip install -e ".[stats,dev]" && pytest
```

The renderer is pinned byte-for-byte by golden files (see [docs/development.md](docs/development.md#tests)). After editing `asciicharts.py` run `python scripts/sync_skill.py` to refresh the copy inside the skill folder (a test fails if you forget). The project began as a Go MCP server and was ported to Python; the Go source lives in this repository's git history.

## License

[MIT](LICENSE).

## Credits

The `halftone`/`ascii` bar styles and the `dotted` line style were reverse-engineered from Bloomberg Businessweek's [**The Year Ahead 2016: 50 Companies to Watch**](https://www.bloomberg.com/graphics/year-ahead-2016/) — a scrollytelling piece that renders all of its charts as styled ASCII/Unicode art. If you're looking for inspiration for what a text chart can look like, start there.
