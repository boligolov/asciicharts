# Glyph cheat sheet

Everything a text chart is drawn with, on one screen. Why each rule exists: [principles.md](principles.md);
how to use them step by step: [drawing.md](drawing.md).

## Safe alphabet

| tier | glyphs | use |
|---|---|---|
| 0 — ASCII | printable ASCII | always safe; the `ascii` style uses nothing else |
| 1 — safe Unicode (default) | light and double box lines `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ═ ║ ╔ ╗ ╚ ╝`; shades `░ ▒ ▓ █`; half blocks `▌ ▄ ▐ ▀`; markers `● ○ ▲ ■ □ ▼ ♦ ◊ ► ◄`; Latin-1 such as `·` `¦` | the default: present in Consolas, Courier New, Lucida Console and everything newer |
| 2 — needs a capable font | heavy `━ ┃ ┏ ┓`, rounded `╭ ╮ ╰ ╯`, dashed box lines; eighth blocks `▁ ▂ ▃ ▄ ▅ ▆ ▇` and `▏ ▎ ▍ ▋ ▊ ▉`; braille | only when asked (heavy/rounded frames, `fine` bars) and in sparklines |

A missing glyph is borrowed from another font with a different width, and the right edge goes ragged.

## Density ramp (magnitude)

```
" "  ░  ▒  ▓  █        0%  25%  50%  75%  100% ink
```

Heatmap cells use `░ ▒ ▓ █` — never blank, because every cell holds a value.

## Series glyphs (identity)

| style | series 1, 2, 3, … |
|---|---|
| default | `█ ▓ ▒ ░ ▌ ▄ ▐ ▀` |
| halftone | `▓ ▒ ░ ▌ ▄ ▐ ▀ :` |
| ascii | `# @ % & $ W M N H D G U O S Z X = / \ : ; ! '` |
| point markers | `● ○ ▲ ■ □ ▼ ♦ ◊ ► ◄` (ascii: `o x * + ^ v @ % & $`) |

The first series is always the densest. The legend shows the exact glyph: `█ 2025   ▓ 2026`.

## Roles (one glyph, one meaning)

| role | Unicode | ASCII |
|---|---|---|
| empty rest of a bar (track) | `░` (`▒` if the bar is `░`) | `,` |
| label │ bar separator | `│` | `\|` |
| zero axis of a diverging hbar | `¦` | `+` |
| zero baseline of a diverging vbar | `-` across the row | `-` |
| y-axis tick | `┤` (left), `├` (right) | `+` |
| line stroke | `█` (series *i*: its series glyph) | `#` |
| line with point markers | `·` stroke, markers on the points | `.` stroke |
| dotted line | `+` on every other cell | `+` |
| reference line (threshold) | `-` on every other cell, behind the data | `-` |
| dotplot background | `·` | |
| two series in one cell | `*` (legend: `* overlap`) | `*` |
| boxplot | `├` min, `─` whisker, `█` box, `║` median, `┤` max | |
| sparkline heights | `▁ ▂ ▃ ▄ ▅ ▆ ▇ █` | |

## Frames

| border | corners and lines | safe? |
|---|---|---|
| `light` (default) | `┌ ┐ └ ┘ ─ │ ├ ┤` | yes |
| `double` | `╔ ╗ ╚ ╝ ═ ║ ╠ ╣` | yes |
| `ascii` | `+ + + + - \| + +` | yes, anywhere |
| `heavy` | `┏ ┓ ┗ ┛ ━ ┃ ┣ ┫` | needs a capable font |
| `rounded` | `╭ ╮ ╰ ╯ ─ │ ├ ┤` | needs a capable font |

Inside a frame: one space of padding on each side; the rules are `inner width + 2` long.

## Widths

CJK characters and most emoji take **two** columns, accents that combine with a letter take **none**.
Count columns, not characters, when you pad labels or size a frame.
