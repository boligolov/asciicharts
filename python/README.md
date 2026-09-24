# asciicharts — Python

The Python reference implementation of [asciicharts principles v1.0](../spec/principles.md): numbers in, a
text chart out. It passes the [conformance suite](../spec/conformance/) byte for byte.

- **`asciicharts.py`** — the renderer and CLI: one file, standard library only (Python 3.10+). Copy it
  anywhere; nothing to install.
- **`tests/`** — the test suite, including the conformance suite.

```sh
python asciicharts.py --json '{"chartType":"hbar","labels":["a","b"],"series":[{"values":[3,5]}]}'
python asciicharts.py --csv data.csv --chart hbar --sort -latency --limit 10
python asciicharts.py --list

pip install -e ".[dev]" && pytest            # from this directory
```

```python
from asciicharts import render_chart
print(render_chart({"chartType": "sparkline", "series": [{"values": [4, 6, 5, 9, 3]}]}))
```

The MCP server and a single-binary command line are in [Go](../go/). The project, the skill and the
documentation: [the repository README](https://github.com/boligolov/asciicharts).
License: MIT.
