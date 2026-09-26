# asciicharts — Go

The Go reference implementation of [asciicharts principles v1.2](../docs/spec/principles.md): numbers in, a text
chart out. The library has no dependencies beyond the standard library.

It is byte-for-byte identical to the Python implementation: it passes the whole
[conformance suite](../test/conformance/) — 317 corpus cases, 116 curated cases (text in any script,
control characters, number formatting, every validation message), the 31 gallery examples — and agrees
with Python on tens of thousands of random specs (`test/parity/differential.py`).

```go
// the output below is checked by ExampleRenderJSON in asciicharts/example_test.go
import "github.com/boligolov/asciicharts/go/asciicharts"

out, err := asciicharts.RenderJSON([]byte(`{"chartType":"hbar","labels":["Chrome","Firefox","Safari"],"series":[{"values":[62,21,12]}]}`))
if err != nil {
	log.Fatal(err) // a *asciicharts.ChartError: one line that says what to fix
}
fmt.Println(out)
```

```
┌───────────────────────────────────────────────────────┐
│ Chrome  │ ████████████████████████████████████████ 62 │
│ Firefox │ ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░ 21 │
│ Safari  │ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 12 │
└───────────────────────────────────────────────────────┘
```

- `RenderJSON(data []byte) (string, error)` — a JSON spec (§9.1 of the principles).
- `Render(spec any) (string, error)` — a decoded spec: `map[string]any` with `json.Number` (or `float64`)
  numbers.
- `ListCharts() []ChartInfo`, `ChartTypes() []string` — the chart catalogue.
- `SpecFromCSV(text, chartType, CSVOptions)` — a spec straight from a CSV file (§9.5), exactly as the
  Python reference builds it: the same delimiter sniffing, quoting, number decorations (`1,234.5`, `3,14`,
  `$5`, `12%`), column matching and messages. The spec is an ordered `*Object`; `PyJSON` prints it as
  Python's `json.dumps` does, `Plain` turns it into a map for `Render`.
- `ChartError`, the limits (`MaxWidth`, `MaxValues`, …), `Version`, `PrinciplesVersion`, `UnicodeVersion`.

## Command line

`achart` (`cmd/achart`) is the command line: a static binary for Linux, macOS or Windows (amd64/arm64) in
the [releases](https://github.com/boligolov/asciicharts/releases) (tags `go/v…`), one zip per platform
(`achart-<os>-<arch>.zip`, checksums in `SHA256SUMS.txt`):

```sh
# macOS / Linux: pick darwin-arm64, darwin-amd64, linux-amd64 or linux-arm64
curl -LO https://github.com/boligolov/asciicharts/releases/latest/download/achart-darwin-arm64.zip
unzip achart-darwin-arm64.zip achart && sudo mv achart /usr/local/bin/
```

```powershell
# Windows (amd64; arm64: achart-windows-arm64.zip)
Invoke-WebRequest https://github.com/boligolov/asciicharts/releases/latest/download/achart-windows-amd64.zip -OutFile achart.zip
Expand-Archive achart.zip $env:LOCALAPPDATA\achart; $env:PATH += ";$env:LOCALAPPDATA\achart"
```

On macOS the binary is not notarized: downloaded with `curl` it runs, but a copy downloaded in a browser is
blocked by Gatekeeper ("cannot be opened", "damaged") until you clear the flag once,
`xattr -d com.apple.quarantine achart`.

Or build it: `go install github.com/boligolov/asciicharts/go/cmd/achart@latest`.

```sh
achart spec.json                      # a JSON spec from a file, - for stdin, or --json '{...}'
achart --list                         # every chart type, how to fill series, an example
achart --csv data.csv --chart hbar --sort -p99 --limit 10 --set title=Slowest
achart --csv data.csv --chart line --print-spec   # the JSON spec it built
```

It is the Python command line (`python asciicharts.py`) in one static binary: the same charts, error
messages and exit codes (0 ok, 1 error, 2 bad usage), `--csv` with the same options. Only the help texts
differ. ExCSV files (`#!excsv`) are not read yet; the Python command line reads them.

## MCP server

`cmd/asciicharts-mcp` is the MCP server (not in the releases; build it with `go install`): the tools `list_charts` and `render_chart` over stdio, or over
stateless streamable HTTP at `/mcp` (with `/healthz`) when `PORT` is set.

```sh
go install github.com/boligolov/asciicharts/go/cmd/asciicharts-mcp@latest
claude mcp add asciicharts -- asciicharts-mcp          # stdio, for a client that launches it
PORT=8080 asciicharts-mcp                              # HTTP
asciicharts-mcp healthcheck                            # exit 0/1: probes its own /healthz
```

Tools, arguments, clients, deployment: [cmd/asciicharts-mcp/README.md](cmd/asciicharts-mcp/README.md). It
uses the official Go MCP SDK; the library package itself has no dependencies.

## Tests

```sh
go test ./...                                          # conformance (corpus, curated, gallery) + robustness
go test -run '^$' -fuzz FuzzRenderJSON -fuzztime 60s ./asciicharts/
python ../test/parity/differential.py 10000                # compare with the Python reference on random specs
python ../test/parity/differential_csv.py 10000            # … on random CSV files
python ../test/parity/cli_parity.py                        # both command lines: stdout, stderr, exit code
```

## Releasing

Set `Version` in `asciicharts/render.go`, then push a tag `go/vX.Y.Z` with the same version:
`.github/workflows/release-go.yml` tests, checks the tag against `achart --version`, builds `achart` for six
platforms, each in its own zip, and publishes them with `SHA256SUMS.txt` as a GitHub release.

## Generated files

`asciicharts/unicode_tables.go` (display widths, from Python's `unicodedata`) and
`asciicharts/catalog_data.go` (the chart catalogue) are generated by `scripts/gen_go_unicode.py` and
`scripts/gen_go_catalog.py`, so both implementations measure text and describe charts identically; a test
on the Python side fails if they are stale.

License: MIT.
