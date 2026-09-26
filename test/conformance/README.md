# Conformance suite — asciicharts principles v1.2

Specs with their exact expected output. An implementation of the principles — in any language — conforms
when it produces these outputs **byte for byte**, including the text of every error message. The suite is
what makes the principles a specification rather than a description: two implementations that pass it
draw every chart the same way.

| file | contents |
|---|---|
| `corpus.json` | 317 cases, mostly randomly generated specs covering every chart type, style, border and option; each is `{"spec": {...}, "out": "..."}` or, when the spec must be rejected, `{"spec": {...}, "err": "..."}` |
| `curated.json` | 110 named cases for what random specs barely reach — text in any script (CJK, emoji, combining marks, RTL), control characters, number formatting, each rule of v1.0, and **every validation message** (48 of the cases are errors): `[{"name": "...", "spec": ..., "out": "..."}]` or with `"err"` |
| `gallery.json` | the 31 documented examples: `[{"name": "...", "spec": {...}}]` |
| `gallery.txt` | their expected output, concatenated: for each example, `=== <name> ===\n<output>\n\n` |

## Exact format

- UTF-8, `\n` line endings. Outputs have **no trailing newline**; lines inside an output may end in spaces,
  and those spaces are part of the expected bytes.
- `out` is exactly what `render(spec)` returns. `err` is exactly the error message (in the Python
  reference implementation, `str(ChartError)`), without an `error:` prefix.
- A spec is the JSON object described in the principles (§9.1). Some specs carry fields a chart type
  ignores (for example `bins` on a line chart); ignoring them is part of conforming.
- Colored cases (`"useColor": "on"`) contain ANSI escape sequences (`ESC[38;5;<n>m … ESC[0m`), as bytes.

## Running it

Read `corpus.json` and `curated.json`, render each `spec`, and compare with `out` (or check that rendering
fails with exactly `err`); render each spec of `gallery.json` and compare the concatenation with
`gallery.txt`. In Python: `test_corpus_matches_golden`, `test_curated_matches_golden` and
`test_gallery_matches_golden` in `python/tests/test_charts.py`; in Go: `TestCorpus`, `TestCurated` and
`TestGallery` in `go/asciicharts/conformance_test.go`.

## Changing it

The suite changes only when the principles change on purpose. From the repository root:

```sh
python scripts/conformance_refresh.py           # report: how many cases change, by chart type and style
python scripts/conformance_refresh.py --write   # then write them
```

Check that every changed case is one the change is about before writing, record the change in
`../../docs/spec/CHANGELOG.md`, and regenerate the documentation examples (`scripts/gallery_refresh.py`,
`scripts/site_examples.py`, `scripts/sync_skill.py`).

## Licence

Like the principles in `docs/spec/`, this suite is licensed under CC BY 4.0 (see `LICENSE`).
