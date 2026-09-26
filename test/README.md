# test/

Everything that checks the project as a whole. The two renderers keep their own unit tests next to their
code — [`python/tests/`](../python/tests/) and the `*_test.go` files in [`go/`](../go/) — and both read the
conformance suite from here.

| folder / file | what it checks | how to run |
|---|---|---|
| [`conformance/`](conformance/) | the renderers' output, byte for byte: 317 random specs, 116 curated cases and 31 documented examples with their exact expected output — the language-neutral suite of the [principles](../docs/spec/principles.md) (CC BY 4.0) | read by `python/tests/test_charts.py` and `go/asciicharts/conformance_test.go` |
| [`evals/`](evals/) | the skill: does an agent draw charts right with it, and how much better than without it — prompts, programmatic graders, recorded runs and their results | by hand: independent agents answer the prompts, then `python test/evals/hand_grade.py <run> <eval>`; see its [README](evals/README.md) |
| [`parity/`](parity/) | Go against Python: `differential.py` (random specs), `differential_csv.py` (random CSV files), `cli_parity.py` (both command lines: stdout, stderr, exit code) | `python test/parity/differential.py 10000` — each needs Go and Python |
| `test_skill.py` | the skill folder: frontmatter, links, the commands `SKILL.md` shows, its version, the plugin manifests (`claude plugin validate` when the CLI is installed), the site's `asciicharts.skill` is current | `pytest` |
| `test_docs.py` | the docs: every printed chart is current and rectangular, font-safe glyphs, links, the Go files generated from Python | `pytest` |
| `test_hand_grader.py` | the evals' grader is itself right: the renderer's own chart passes every check, each typical mistake fails the check meant for it | `pytest` |

```sh
pytest                     # from the repository root: python/tests and test/ (pytest.ini)
cd go && go test ./...     # the Go library, CLI and MCP server
```

When a check here fails after a deliberate change, the fix is usually one command:
`python scripts/sync_skill.py` (the skill's copies), `python scripts/gallery_refresh.py` (printed examples),
`python scripts/package_skill.py --site` (the site's download), or, for a change in how charts are drawn,
`python scripts/conformance_refresh.py --write` — a new version of the principles, see
[docs/development.md](../docs/development.md).
