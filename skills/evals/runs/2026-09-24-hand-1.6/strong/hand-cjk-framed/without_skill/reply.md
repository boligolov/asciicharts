Here's the chart. Each █ stands for 2 people, rounded to the nearest whole block:

```
┌──────────────────────────────────────┐
│ 東京オフィス チーム別人数            │
├──────────────────────────────────────┤
│ 開発     ████████████████████████ 48 │
│ 営業     ████████████████         31 │
│ サポート ███████████              22 │
│ デザイン ██████                   12 │
│ 人事     ████                      7 │
└──────────────────────────────────────┘
```

合計 120名

The layout counts each Japanese character as two columns wide, which is how CJK text normally displays in a monospace font. The box-drawing characters and █ count as one column each.

Be careful with fonts on a Japanese wiki. Some Japanese fonts, such as MS Gothic, and some terminals set to treat ambiguous-width characters as wide, draw ─ │ █ at full width. The right edge of the frame then won't line up. Put the chart in a code block with a font like Consolas, Menlo or Source Han Code JP, where those characters are one column wide.
