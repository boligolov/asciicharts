package chart

// eighthsUp are the 0..8 eighth-block glyphs, used to give vertical bar tops
// sub-character height resolution.
var eighthsUp = []rune{' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'}

// eighthsLeft are the 0..8 eighth-block glyphs, used to give horizontal bar
// ends sub-character width resolution.
var eighthsLeft = []rune{' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█'}

// shades are the 5 shade levels (low to high) used by the heatmap when
// color is off.
var shades = []rune{' ', '░', '▒', '▓', '█'}

// fills are per-series fill glyphs, used to keep stacked/grouped bars and
// pie slices visually distinct from each other without relying on color.
var fills = []rune{'█', '▓', '▒', '░', '▚', '▞'}

// halftoneFills are per-series fill glyphs for style:"halftone" bars —
// lighter, stippled shades (no solid block) evoking the dot-matrix/printed
// look of old financial-terminal charts, instead of flat solid columns.
var halftoneFills = []rune{'▓', '▒', '░', '▚', '▞', ':'}

// asciiFills are per-series fill glyphs for style:"ascii" bars: plain
// letters/punctuation instead of Unicode block-shade characters, each
// chosen for how much of its cell it visually fills. Bloomberg Businessweek's
// "Year Ahead" ASCII graphics tile bars this way (e.g. "### Total  ::: Shell
// ||| BP", literal repeated glyphs named in the legend) — every glyph here
// is plain ASCII, so it renders identically in any monospace font, unlike
// the Unicode block/shade glyphs the other bar styles use (see the README
// note on Consolas and similar fonts missing those glyphs).
var asciiFills = []rune{'#', 'X', 'H', 'W', '=', ':', '|', '.'}

// markers are per-series point glyphs for scatter charts in cell mode.
var markers = []rune{'●', '○', '◆', '◇', '▲', '△', '■', '□', '▼', '▽'}

// palette256 holds ANSI 256-color codes assigned to series in order:
// blue, orange, green, magenta, cyan, yellow.
var palette256 = []int{39, 208, 40, 201, 51, 226}

// quadChars is the 16-entry quadrant block lookup table, indexed by a
// 4-bit mask of which quadrants of the character cell are "on":
// bit 8 = top-left, 4 = top-right, 2 = bottom-left, 1 = bottom-right.
var quadChars = []rune{
	' ', '▘', '▝', '▀',
	'▖', '▌', '▞', '▛',
	'▗', '▚', '▐', '▜',
	'▄', '▙', '▟', '█',
}

// quadBit maps a (dx, dy) sub-cell coordinate (0,0 = top-left, 1,1 =
// bottom-right of a 2x2 dot grid) to its bit in the quadChars index.
var quadBit = map[[2]int]uint8{
	{0, 0}: 8, {1, 0}: 4,
	{0, 1}: 2, {1, 1}: 1,
}

// brailleBit[dx][dy] maps a (dx, dy) sub-cell coordinate in a 2-wide,
// 4-tall dot grid to its bit in the Unicode braille pattern block
// (base codepoint U+2800).
var brailleBit = [2][4]uint16{
	{0x01, 0x02, 0x04, 0x40},
	{0x08, 0x10, 0x20, 0x80},
}

const brailleBase = 0x2800
