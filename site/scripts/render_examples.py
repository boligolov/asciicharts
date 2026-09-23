"""Renders the chart examples shown on the landing page, in both a plain (mono) and a colored
variant, and writes them to src/data/charts.json as ready-to-embed HTML strings.

Static, checked-in output on purpose: the site is plain HTML/CSS/JS and its build (`astro build`,
on GitHub Pages/Vercel/Netlify) never needs Python installed. Re-run this after changing the specs
below or after any renderer change that affects their output:

    python site/scripts/render_examples.py
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from asciicharts import render_chart  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "src" / "data" / "charts.json"

_ANSI_RUN = re.compile(r"\x1b\[38;5;(\d+)m(.*?)\x1b\[0m", re.S)


def _xterm256_hex(code: int) -> str:
    """The standard xterm 256-color palette formula (6x6x6 cube + grayscale ramp), so any color
    code the renderer emits (PALETTE256, HEAT_RAMP, THRESHOLD_COLOR, ...) maps to an exact hex."""
    if code < 16:
        basic = ["000000", "cd0000", "00cd00", "cdcd00", "0000ee", "cd00cd", "00cdcd", "e5e5e5",
                 "7f7f7f", "ff0000", "00ff00", "ffff00", "5c5cff", "ff00ff", "00ffff", "ffffff"]
        return basic[code]
    if code < 232:
        code -= 16
        levels = [0, 95, 135, 175, 215, 255]
        r, g, b = levels[code // 36], levels[(code // 6) % 6], levels[code % 6]
        return f"{r:02x}{g:02x}{b:02x}"
    gray = 8 + (code - 232) * 10
    return f"{gray:02x}{gray:02x}{gray:02x}"


def ansi_to_html(s: str) -> str:
    """Turns `render_chart(..., useColor="on")` output into an HTML string: ANSI 256-color runs
    become <span style="color:#hex">, everything else is escaped plain text."""
    out, last = [], 0
    for m in _ANSI_RUN.finditer(s):
        out.append(html.escape(s[last:m.start()]))
        color = _xterm256_hex(int(m.group(1)))
        out.append(f'<span style="color:#{color}">{html.escape(m.group(2))}</span>')
        last = m.end()
    out.append(html.escape(s[last:]))
    return "".join(out)


# --- the examples shown on the site ------------------------------------------------------------
# Real specs, not invented numbers — the same ones from README.md/docs/gallery.md, so the site
# never claims a shape the library doesn't actually produce.

EXAMPLES = [
    {
        "id": "hero",
        "spec": {
            "chartType": "hbar", "border": "rounded", "title": "Build time by stage (s)", "width": 46,
            "labels": ["Compile", "Test", "Lint", "Package"],
            "series": [
                {"name": "before caching", "values": [64, 32, 16, 8]},
                {"name": "after caching", "values": [40, 22, 10, 5]},
            ],
        },
    },
    {
        "id": "ranking",
        "spec": {
            "chartType": "hbar", "border": "light", "title": "Slowest endpoints, p99 ms", "width": 34,
            "labels": ["/upload", "/search", "/checkout"],
            "series": [{"values": [4200, 1900, 950]}],
        },
    },
    {
        "id": "diverging",
        "spec": {
            "chartType": "hbar", "stacked": True, "border": "rounded", "title": "Revenue vs refunds",
            "width": 36,
            "labels": ["EMEA", "APAC", "Americas"],
            "series": [
                {"name": "Product", "values": [40, 25, 55]},
                {"name": "Refunds", "values": [-15, -20, -8]},
            ],
        },
    },
    {
        "id": "vbar",
        "spec": {
            "chartType": "vbar", "border": "heavy", "title": "Revenue by quarter", "height": 12,
            "width": 44,
            "labels": ["Q1", "Q2", "Q3", "Q4"],
            "series": [
                {"name": "2025", "values": [42, 55, 61, 58]},
                {"name": "2026", "values": [50, 60, 66, 70]},
            ],
        },
    },
    {
        "id": "pie",
        "spec": {
            "chartType": "pie", "border": "rounded", "title": "Browser share", "width": 36,
            "series": [
                {"name": "Chrome", "values": [62]},
                {"name": "Safari", "values": [21]},
                {"name": "Firefox", "values": [12]},
                {"name": "Other", "values": [5]},
            ],
        },
    },
    {
        "id": "heatmap",
        "spec": {
            "chartType": "heatmap", "border": "double", "title": "Requests by hour x day", "width": 44,
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "series": [
                {"name": "00h", "values": [2, 1, 1, 2, 3, 5, 4]},
                {"name": "08h", "values": [8, 9, 9, 8, 7, 3, 2]},
                {"name": "16h", "values": [6, 7, 8, 9, 9, 6, 4]},
                {"name": "22h", "values": [3, 3, 4, 5, 8, 9, 6]},
            ],
        },
    },
    {
        "id": "line",
        "spec": {
            "chartType": "line", "border": "light", "title": "Response time vs SLA", "height": 10, "width": 96,
            "threshold": 50, "showPoints": True,
            "series": [{"values": [20, 25, 22, 30, 45, 38, 55, 60, 48, 35, 30, 28]}],
        },
    },
    {
        "id": "dual_axis",
        "spec": {
            "chartType": "dual_axis", "border": "rounded", "title": "Temperature (left) vs humidity (right)",
            "height": 10, "width": 92,
            "series": [
                {"name": "Temp °C", "values": [10, 12, 15, 14, 18, 20, 19]},
                {"name": "Humidity %", "values": [80, 78, 65, 70, 60, 55, 58]},
            ],
        },
    },
    {
        "id": "sparkline",
        "spec": {
            "chartType": "sparkline", "border": "light", "title": "Latency",
            "series": [{"name": "latency", "values": [4, 6, 5, 9, 3, 7, 8, 2, 6, 9, 4]}],
        },
    },
    {
        "id": "ascii",
        "spec": {
            "chartType": "hbar", "style": "ascii", "border": "ascii", "title": "Tests by suite", "width": 32,
            "labels": ["unit", "integration", "e2e"],
            "series": [{"values": [480, 120, 30]}],
        },
    },
]


def main():
    out = []
    for ex in EXAMPLES:
        mono = render_chart(ex["spec"])
        color_spec = {**ex["spec"], "useColor": "on"}
        color = render_chart(color_spec)
        out.append({
            "id": ex["id"],
            "spec": ex["spec"],
            "mono_html": html.escape(mono),
            "color_html": ansi_to_html(color),
        })
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} example(s) to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
