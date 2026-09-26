# asciicharts

Charts made of text characters, drawn right. Ask Claude to plot, chart or visualize some numbers — a
ranking, a trend, a distribution, shares of a whole — and it answers with a chart that works anywhere
text does: a chat reply, a terminal, a pull request, a commit message, a code comment.

```
┌───────────────────────────────────────────────────────────┐
│                 Slowest endpoints, p99 ms                 │
├───────────────────────────────────────────────────────────┤
│ /upload   │ ████████████████████████████████████████ 4200 │
│ /search   │ ██████████████████░░░░░░░░░░░░░░░░░░░░░░ 1900 │
│ /checkout │ █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 950  │
└───────────────────────────────────────────────────────────┘
```

Hand-drawn text charts usually go wrong in the same way: characters are eyeballed, not counted. This
skill teaches Claude to compute every length from the values, keep bars starting at zero, tell series
apart without color, print the numbers where the grid is approximate, and use only glyphs present in
common monospace fonts, so frames stay straight in Consolas and Courier as well as in a modern terminal.

## Charts

Horizontal and vertical bars (grouped, stacked, diverging), line, area, sparkline, histogram, boxplot,
heatmap, pie, scatter, dot plot and dual-axis — from numbers in the conversation or from a CSV file.

## What it runs

Without any tool, Claude draws the chart by hand, following the skill's step-by-step recipes and
self-check. When one is available, it renders exactly instead, trying in order: a connected
`asciicharts` MCP server, the `achart` command on your PATH, or the bundled Python script
(`scripts/asciicharts.py`, standard library only). The script only reads the chart spec or the CSV file
you point it to and prints the chart. Nothing is installed, and the plugin sends no data anywhere.

## Learn more

- Website: https://asciicharts.online
- Source, the principles behind every rule, and the `achart` command: https://github.com/boligolov/asciicharts
- License: MIT
