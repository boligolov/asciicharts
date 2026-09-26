#!/usr/bin/env python3
"""Regenerate the conformance suite (test/conformance/) from the Python reference renderer — only after a
deliberate change to how charts are drawn, and only after reading what it reports.

    python scripts/conformance_refresh.py           # report what would change, change nothing
    python scripts/conformance_refresh.py --write   # write the new expected outputs

The report counts the changed corpus cases by chart type and style, names the changed curated cases, and prints the first few before/after, so a
change can be checked to touch only the charts it is about. corpus.json keeps each case's spec and
replaces its "out" (or "err"); gallery.txt is rebuilt from gallery.json. The files keep their exact
formatting (see test/conformance/README.md). The MCP server's recorded answers
(go/cmd/asciicharts-mcp/testdata/render_chart.json) are charts too, and are refreshed with them.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
from asciicharts import ChartError, render_chart  # noqa: E402

CONFORMANCE = ROOT / "test" / "conformance"
MCP_ANSWERS = ROOT / "go" / "cmd" / "asciicharts-mcp" / "testdata" / "render_chart.json"


def main(argv):
    write = "--write" in argv
    corpus_path = CONFORMANCE / "corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    changed, examples = collections.Counter(), []
    for i, case in enumerate(corpus):
        try:
            new = {"out": render_chart(case["spec"])}
        except ChartError as e:
            new = {"err": str(e)}
        old = {k: case[k] for k in ("out", "err") if k in case}
        if old != new:
            changed[f'{case["spec"].get("chartType")}/{case["spec"].get("style") or "-"}'] += 1
            if len(examples) < 3:
                examples.append((i, old, new))
            case.pop("out", None)
            case.pop("err", None)
            case.update(new)
    print(f"corpus.json: {sum(changed.values())} of {len(corpus)} cases change" + (f" {dict(changed)}" if changed else ""))
    for i, old, new in examples:
        print(f"--- case {i} before\n{old.get('out', old.get('err'))}\n+++ after\n{new.get('out', new.get('err'))}")

    curated_path = CONFORMANCE / "curated.json"
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    curated_changed = []
    for case in curated:
        try:
            new = {"out": render_chart(case["spec"])}
        except ChartError as e:
            new = {"err": str(e)}
        if {k: case[k] for k in ("out", "err") if k in case} != new:
            curated_changed.append(case["name"])
            case.pop("out", None)
            case.pop("err", None)
            case.update(new)
    print(f"curated.json: {len(curated_changed)} of {len(curated)} cases change" + (f" {curated_changed}" if curated_changed else ""))

    gallery = json.loads((CONFORMANCE / "gallery.json").read_text(encoding="utf-8"))
    text = "".join(f"=== {g['name']} ===\n{render_chart(g['spec'])}\n\n" for g in gallery)
    gallery_txt = CONFORMANCE / "gallery.txt"
    gallery_stale = gallery_txt.read_bytes().decode("utf-8") != text
    print(f"gallery.txt: {'changes' if gallery_stale else 'unchanged'}")

    answers = json.loads(MCP_ANSWERS.read_text(encoding="utf-8"))
    answers_changed = collections.Counter()
    for case in answers:
        if case.get("rejected"):  # refused by the server's argument schema, before any chart
            continue
        try:
            new = {"out": render_chart(case["args"])}
        except ChartError as e:
            new = {"err": f"Error executing tool render_chart: {e}"}
        if {k: case[k] for k in ("out", "err") if k in case} != new:
            answers_changed[case["args"].get("chartType")] += 1
            case.pop("out", None)
            case.pop("err", None)
            case.update(new)
    print(f"MCP render_chart.json: {sum(answers_changed.values())} of {len(answers)} answers change"
          + (f" {dict(answers_changed)}" if answers_changed else ""))

    if write:
        MCP_ANSWERS.write_text(json.dumps(answers, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        corpus_path.write_text(json.dumps(corpus, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
        curated_path.write_text(json.dumps(curated, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        gallery_txt.write_bytes(text.encode("utf-8"))
        print("written; now also run scripts/gallery_refresh.py, scripts/site_examples.py and scripts/sync_skill.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
