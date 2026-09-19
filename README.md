# asciicharts

Turn numbers into a text chart — ASCII/Unicode, no image, no plotting library, just a string an agent can drop straight into a reply.

```
┌───────────────────────────────────────────────────────┐
│                     Browser share                     │
├───────────────────────────────────────────────────────┤
│ Chrome  │ ████████████████████████████████████████ 62 │
│ Firefox │ █████████████▌                           21 │
│ Safari  │ ███████▋                                 12 │
│ Other   │ ███▏                                     5  │
└───────────────────────────────────────────────────────┘
```

One renderer, three ways to use it:

| | for | needs |
|---|---|---|
| **[Skill](skills/asciicharts/SKILL.md)** (`skills/asciicharts/`) | an agent (Claude Code, etc.) with a shell and Python | nothing but Python 3 |
| **`asciicharts.py`** as a library / CLI | your own scripts | nothing but Python 3 |
| **[MCP server](server/README.md)** (`server/`, Docker) | any MCP client, or a shared always-on deployment | the `mcp` package |

Everything is hand-rolled — line drawing, quadrant/braille sub-character packing, bar scaling, pie rasterization, box-and-whisker math — so `asciicharts.py` is a single dependency-free file you can copy anywhere.

## Charts

12 chart types: `sparkline`, `vbar`, `hbar`, `line`, `area`, `scatter`, `dual_axis`, `pie`, `histogram`, `heatmap`, `boxplot`, `dotplot`.

- **vbar / hbar / area**: single, grouped or stacked. Negative values automatically **diverge** — bars grow both ways from a zero baseline, stacked ones too.
- **line / scatter / dual_axis**: `cell`, `quad` (2×2 dots) or `braille` (2×4 dots) resolution; line adds threshold and per-point markers.
- **Styles**: `halftone` (stippled shades), `ascii` (plain `# X H W = : | .` and 15 more for up to 23 series, renders in any font), `dotted` line trend.
- **6 border styles** with a centered title; optional ANSI 256-color.
- **Safe to expose**: input is validated and size-limited (width ≤ 500, height ≤ 200, 50k values), errors are readable one-liners.

See **[the gallery](skills/asciicharts/references/gallery.md)** for every chart rendered, and **[the reference](skills/asciicharts/references/reference.md)** for every option.

## Use as a skill

The skill is the self-contained folder [`skills/asciicharts/`](skills/asciicharts/): `SKILL.md`, the one-file script in `scripts/`, and `references/` (every option; every chart rendered). There is no registry to register it with — an agent finds a skill by looking in a folder, so installing means copying the folder there:

```sh
cp -r skills/asciicharts ~/.claude/skills/      # Claude Code, personal (project: .claude/skills/ in the repo)
python scripts/package_skill.py                 # dist/asciicharts.skill, for uploading to Claude.ai
```

The agent reads `SKILL.md` (which chart to pick, how to feed it data, how to make the result read well) and runs `python scripts/asciicharts.py`. Nothing to install but Python. Full instructions for Claude Code, Claude.ai and the API: **[docs/skill.md](docs/skill.md)**.

## Use as a library or CLI

```python
from asciicharts import render_chart

print(render_chart({
    "chartType": "vbar",
    "title": "Revenue by quarter",
    "border": "rounded",
    "height": 10,
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "series": [
        {"name": "2025", "values": [30, 45, 40, 60]},
        {"name": "2026", "values": [35, 50, 55, 70]},
    ],
}))
```

```
╭────────────────────╮
│ Revenue by quarter │
├────────────────────┤
│           ▓        │
│          █▓        │
│        ▓ █▓        │
│     ▓  ▓ █▓        │
│    █▓ █▓ █▓        │
│  ▓ █▓ █▓ █▓        │
│ █▓ █▓ █▓ █▓        │
│ █▓ █▓ █▓ █▓        │
│ █▓ █▓ █▓ █▓        │
│ █▓ █▓ █▓ █▓        │
│ Q1 Q2 Q3 Q4        │
│                    │
│ █ 2025   ▓ 2026    │
╰────────────────────╯
```

The same JSON from the command line: `python asciicharts.py spec.json`, `... -` (stdin) or `... --json '{…}'`. Invalid input raises `ChartError` (a `ValueError`) / prints `error: …` and exits 1.

Straight from a CSV file (header row required; `,` `;` tab or `|` delimited; `$`, `%` and thousands separators are understood):

```sh
python asciicharts.py --csv latency.csv --chart hbar --values p99 --sort -p99 --limit 10 --set title="Slowest endpoints"
```

`--label`, `--values`, `--sort`, `--limit`, `--set key=value` and `--print-spec` are documented in the [skill](skills/asciicharts/SKILL.md#from-a-csv); `python asciicharts.py --list` prints every chart type with an example.

## Run the MCP server

Two tools: **`list_charts`** (the catalogue: every chart type, how to fill `series` for it, which options apply, and an example call) and **`render_chart`** (the renderer above). Full description — tools, arguments, transports, configuration, client setup, limits: **[server/README.md](server/README.md)**.

```sh
pip install .                # or: pip install ".[stats]" for Postgres statistics
asciicharts-mcp              # MCP over stdio
PORT=8080 asciicharts-mcp    # streamable HTTP: /mcp, plus /healthz
claude mcp add asciicharts -- asciicharts-mcp     # e.g. register it with Claude Code
```

### Docker

```sh
docker build -f deploy/Dockerfile -t asciicharts .
docker run -i --rm asciicharts                                # stdio
docker run --rm -e PORT=8080 -p 8080:8080 asciicharts         # HTTP → http://localhost:8080/mcp
docker compose -f deploy/docker-compose.yml up -d --build          # local dev: HTTP server + Postgres (statistics on)
```

**Production** — HTTPS on your own domain (automatic certificates via Caddy; Postgres and the server are not exposed):

```sh
cp deploy/.env.example deploy/.env        # set DOMAIN
docker compose -f deploy/docker-compose.prod.yml up -d --build      # → https://<DOMAIN>/mcp
```

Anonymous usage statistics (chart type, style, size buckets, success/failure — never your data) are **off by default**; set `ASCIICHARTS_STATS=on` and `DATABASE_URL` to record them in Postgres. The server behaves identically either way. Details, HTTP transport notes and client configs: **[docs/development.md](docs/development.md)**.

## Fonts

The block (`▏▎▍▌`), quadrant (`▘▝▖▗`) and braille (`⠀`–`⣿`) glyphs need a font that covers them. GitHub and most terminals (iTerm2, Windows Terminal, Ghostty, …) do; some editors' **default** monospace fonts — Consolas in VS Code and PyCharm on Windows — silently substitute a fallback for just those characters, which makes the right border of an otherwise rectangular chart look crooked (worst with `mode: "braille"`). Every line really has the same number of characters (the tests check it) — a ragged wall means the viewer, not the generator. Use a font with full coverage (Cascadia Code, JetBrains Mono, Noto Sans Mono, DejaVu Sans Mono), or `"style": "ascii"` / `"border": "ascii"`, which use only plain characters.

## Development

```sh
pip install -e ".[stats,dev]" && pytest
```

The renderers are pinned byte-for-byte by golden files (see [docs/development.md](docs/development.md#tests)). After editing `asciicharts.py` run `python scripts/sync_skill.py` to refresh the copy inside the skill folder (a test fails if you forget). The project began as a Go MCP server; it was ported to Python (fixing a crash on stacked charts with negative values and adding real support for them along the way), and the Go source lives in this repository's git history.

## License

[MIT](LICENSE).

## Credits

The `halftone`/`ascii` bar styles and the `dotted` line style were reverse-engineered from Bloomberg Businessweek's [**The Year Ahead 2016: 50 Companies to Watch**](https://www.bloomberg.com/graphics/year-ahead-2016/) — a scrollytelling piece that renders all of its charts as styled ASCII/Unicode art. If you're looking for inspiration for what a text chart can look like, start there.
