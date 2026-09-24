Here's the chart:

```
┌────────────────────────────────────┐
│     東京オフィス チーム別人数      │
├────────────────────────────────────┤
│ 開発     │ ████████████████████ 48 │
│ 営業     │ █████████████░░░░░░░ 31 │
│ サポート │ █████████░░░░░░░░░░░ 22 │
│ デザイン │ █████░░░░░░░░░░░░░░░ 12 │
│ 人事     │ ███░░░░░░░░░░░░░░░░░ 7  │
└────────────────────────────────────┘
```

開発 is the largest team with 48 people, which is 40% of the office's 120. It is about as big as 営業 and サポート combined, and 人事 is the smallest at 7.

- **How I drew it:** I drew it by hand without running any tools. Each bar is `round(人数 / 48 × 20)` cells long, which gives 20, 13, 9, 5 and 3. The light `░` part of each bar is the rest of the scale, and the exact number is printed after each bar.
- **Widths:** I counted each Japanese character as two columns. The shorter labels have spaces added so that every `│` lines up and every line is 38 columns wide.
- **In your wiki:** paste the chart inside a code block (```) so it uses a monospace font. The right border will only be straight if that font draws Japanese characters exactly two columns wide. If some viewers see a crooked right edge, remove the frame and keep just the bars and numbers.
