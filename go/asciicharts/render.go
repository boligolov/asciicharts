// Package asciicharts renders numbers as text charts: the Go reference implementation of
// asciicharts principles v1.1 (spec/principles.md in https://github.com/boligolov/asciicharts).
//
// A spec is the JSON object of the principles (§9.1). The output is deterministic and matches the
// conformance suite (spec/conformance/) byte for byte, error messages included.
//
//	out, err := asciicharts.RenderJSON([]byte(`{"chartType":"hbar","labels":["a","b"],"series":[{"values":[3,5]}]}`))
package asciicharts

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math"
	"strconv"
	"strings"
)

// Version is the version of the implementation; it follows the Python reference implementation.
const Version = "1.0.0"

// PrinciplesVersion is the version of the principles this implementation conforms to.
const PrinciplesVersion = "1.1"

// RenderJSON renders a chart from a JSON spec.
func RenderJSON(data []byte) (string, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	var spec any
	if err := dec.Decode(&spec); err != nil {
		return "", errorf("invalid JSON: %v", err)
	}
	return Render(spec)
}

// Render renders a chart from a decoded JSON spec: a map[string]any whose numbers are json.Number
// (as from a json.Decoder with UseNumber) or float64/int.
func Render(spec any) (string, error) {
	in, err := normalize(spec)
	if err != nil {
		return "", err
	}
	if len(in.series) == 0 {
		return "", errorf("series must contain at least one entry")
	}
	if _, ok := borders[in.border]; !ok && in.border != "" && in.border != "none" {
		return "", errorf("invalid border %s (expected one of: none, ascii, light, heavy, double, rounded)", quote(in.border))
	}
	switch in.style {
	case "", "solid", "fine", "halftone", "ascii", "dotted":
	default:
		return "", errorf("invalid style %s (expected one of: solid, fine, halftone, ascii, dotted)", quote(in.style))
	}
	switch in.useColor {
	case "", "auto", "on", "off":
	default:
		return "", errorf("invalid useColor %s (expected one of: auto, on, off)", quote(in.useColor))
	}
	renderer, ok := renderers[in.chartType]
	if !ok {
		return "", errorf("unknown chartType %s (expected one of: %s)", quote(in.chartType), strings.Join(ChartTypes(), ", "))
	}
	body, err := renderer(in)
	if err != nil {
		return "", err
	}
	return wrapBorder(body, in.title, in.border), nil
}

var renderers = map[string]func(*input) (string, error){
	"sparkline": renderSparkline,
	"vbar":      renderBar,
	"hbar":      renderBar,
	"line":      renderLine,
	"area":      renderArea,
	"dotplot":   renderDotplot,
	"scatter":   renderScatter,
	"dual_axis": renderDualAxis,
	"pie":       renderPie,
	"histogram": renderHistogram,
	"heatmap":   renderHeatmap,
	"boxplot":   renderBoxplot,
}

// --- glyphs (spec/principles.md §2) ------------------------------------------------------------

var (
	eighthsUp     = []string{" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"}
	eighthsLeft   = []string{" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"}
	shades        = []string{" ", "░", "▒", "▓", "█"}
	fills         = []string{"█", "▓", "▒", "░", "▌", "▄", "▐", "▀"}
	halftoneFills = []string{"▓", "▒", "░", "▌", "▄", "▐", "▀", ":"}
	asciiFills    = []string{"#", "@", "%", "&", "$", "W", "M", "N", "H", "D", "G", "U", "O", "S", "Z", "X", "=", "/", "\\", ":", ";", "!", "'"}
	asciiMarkers  = []string{"o", "x", "*", "+", "^", "v", "@", "%", "&", "$"}
	areaASCII     = []string{"#", ":", "%", "&", "$", "W", "M", "N", "H", "D", "G", "U", "O", "S", "Z", "X", "=", "/", "\\", "@", ";", "!", "'"}
	markers       = []string{"●", "○", "▲", "■", "□", "▼", "♦", "◊", "►", "◄"}
	sparkTicks    = []string{"▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"}
	dualGlyphs    = []string{"█", "▒"}
	palette256    = []int{39, 208, 40, 201, 51, 226}
	heatRamp      = []int{21, 27, 33, 39, 45, 51, 87, 123, 159, 195, 226, 220, 214, 208, 202, 196}
)

const (
	trackFill      = "░"
	trackFillAlt   = "▒"
	asciiTrackFill = ","
	overlapMarker  = "*"
	overlapNote    = overlapMarker + " overlap"
	thresholdColor = 244
	heatCellWidth  = 3
	pieAspect      = 2.0
	maxLegendWidth = 100
)

// A ramp is identified by its first slices element, as Python compares list identity.
type ramp []string

func isASCIIRamp(r ramp) bool {
	return len(r) > 0 && (&r[0] == &asciiFills[0] || &r[0] == &areaASCII[0])
}

func trackGlyph(barCh string, asciiStyle bool) string {
	if asciiStyle {
		return asciiTrackFill
	}
	if barCh == trackFill {
		return trackFillAlt
	}
	return trackFill
}

func seriesColor(i int) int { return palette256[i%len(palette256)] }

func colorize(s string, color int, enabled bool) string {
	if !enabled || color < 0 || s == "" {
		return s
	}
	return "\x1b[38;5;" + strconv.Itoa(color) + "m" + s + "\x1b[0m"
}

func colorOf(s int, on bool) int {
	if on {
		return seriesColor(s)
	}
	return -1
}

// --- frame ----------------------------------------------------------------------------------------

// (top-left, top-right, bottom-left, bottom-right, horizontal, vertical, left-T, right-T)
var borders = map[string][8]string{
	"ascii":   {"+", "+", "+", "+", "-", "|", "+", "+"},
	"light":   {"┌", "┐", "└", "┘", "─", "│", "├", "┤"},
	"heavy":   {"┏", "┓", "┗", "┛", "━", "┃", "┣", "┫"},
	"double":  {"╔", "╗", "╚", "╝", "═", "║", "╠", "╣"},
	"rounded": {"╭", "╮", "╰", "╯", "─", "│", "├", "┤"},
}

func wrapBorder(body, title, style string) string {
	lines := strings.Split(body, "\n")
	if style == "" {
		style = "light"
	}
	if style == "none" {
		if title == "" {
			return body
		}
		return title + "\n" + body
	}
	g, ok := borders[style]
	if !ok {
		g = borders["light"]
	}
	tl, tr, bl, br, h, v, lt, rt := g[0], g[1], g[2], g[3], g[4], g[5], g[6], g[7]
	w := visibleWidth(title)
	for _, l := range lines {
		w = maxInt(w, visibleWidth(l))
	}
	var out []string
	rule := func(left, right string) { out = append(out, left+repeat(h, w+2)+right) }
	row := func(text string) { out = append(out, v+" "+text+repeat(" ", w-visibleWidth(text))+" "+v) }
	rule(tl, tr)
	if title != "" {
		p := w - visibleWidth(title)
		lp := p / 2
		row(repeat(" ", lp) + title + repeat(" ", p-lp))
		rule(lt, rt)
	}
	for _, l := range lines {
		row(l)
	}
	rule(bl, br)
	return strings.Join(out, "\n")
}

// --- scales and axes (spec/principles.md §4, §5) --------------------------------------------------

func xPixel(i, n, span int) int {
	if n <= 1 || span <= 1 {
		return 0
	}
	return i * (span - 1) / (n - 1)
}

func yPixel(v, lo, hi float64, span int) int {
	if span <= 1 {
		return 0
	}
	if hi == lo {
		return span - 1
	}
	frac := (v - lo) / (hi - lo)
	return round((1 - frac) * float64(span-1))
}

func seriesMinMax(ss []series) (float64, float64) {
	lo, hi := math.Inf(1), math.Inf(-1)
	for _, s := range ss {
		for _, v := range s.values {
			lo = pyMin(lo, v)
			hi = pyMax(hi, v)
		}
	}
	if math.IsInf(lo, 1) {
		return 0, 1
	}
	return scaleRange(lo, hi)
}

// scaleRange centres all-equal data on its value.
func scaleRange(lo, hi float64) (float64, float64) {
	if hi == lo {
		return lo - 1, hi + 1
	}
	return lo, hi
}

// zeroOnRow widens a range that spans zero just enough that 0 falls exactly on a row.
func zeroOnRow(lo, hi float64, height int) (float64, float64) {
	if !(lo < 0 && 0 < hi) || height < 3 {
		return lo, hi
	}
	bestStep, bestRow := math.Inf(1), 0
	for r := 1; r < height-1; r++ {
		step := pyMax(hi/float64(r), -lo/float64(height-1-r))
		if step < bestStep {
			bestStep, bestRow = step, r
		}
	}
	return -bestStep * float64(height-1-bestRow), bestStep * float64(bestRow)
}

func seriesMaxLen(ss []series) int {
	n := 0
	for _, s := range ss {
		n = maxInt(n, len(s.values))
	}
	return n
}

func leftAxisLabels(lo, hi float64, height int) ([]string, int) {
	labels := make([]string, height)
	w := 0
	for row := 0; row < height; row++ {
		frac := 1.0
		if height > 1 {
			frac = 1 - float64(row)/float64(height-1)
		}
		labels[row] = fmtValue(roundSig12(lo + frac*(hi-lo)))
		w = maxInt(w, len([]rune(labels[row])))
	}
	return labels, w
}

// padLeft is Python's f"{s:>{w}}" (width in code points); padRight is f"{s:<{w}}".
func padLeft(s string, w int) string  { return repeat(" ", w-len([]rune(s))) + s }
func padRight(s string, w int) string { return s + repeat(" ", w-len([]rune(s))) }

func xAxisLabels(labels []string, n, plotWidth, leftPad int) string {
	if len(labels) != n || n == 0 || plotWidth <= 0 {
		return ""
	}
	row := make([]string, plotWidth)
	for i := range row {
		row[i] = " "
	}
	type placedLabel struct {
		start int
		cell  string
	}
	placed := make([]placedLabel, n)
	for i, lbl := range labels {
		cell := truncate(lbl, 8)
		start := clamp(xPixel(i, n, plotWidth)-width(cell)/2, 0, maxInt(plotWidth-width(cell), 0))
		placed[i] = placedLabel{start, cell}
	}
	keep := make([]bool, n)
	keep[0], keep[n-1] = true, true
	end := placed[0].start + width(placed[0].cell)
	lastStart := placed[n-1].start
	for i := 1; i < n-1; i++ {
		start, cell := placed[i].start, placed[i].cell
		if start > end && start+width(cell) < lastStart {
			keep[i] = true
			end = start + width(cell)
		}
	}
	for i, p := range placed {
		if keep[i] {
			for j, r := range cells(p.cell) {
				if p.start+j < plotWidth {
					row[p.start+j] = r
				}
			}
		}
	}
	return repeat(" ", leftPad) + strings.TrimRight(strings.Join(row, ""), " ")
}

func sep(r ramp) string {
	if isASCIIRamp(r) {
		return "|"
	}
	return "│"
}

func seriesLabel(s series, i int) string {
	if s.name != "" {
		return s.name
	}
	return fmt.Sprintf("series %d", i+1)
}

func legendSwatch(i int, colorOn bool, r ramp) string {
	return colorize(r[i%len(r)], seriesColor(i), colorOn)
}

func joinLegend(parts []string) string {
	var lines []string
	cur := ""
	for _, part := range parts {
		if cur != "" && visibleWidth(cur)+3+visibleWidth(part) > maxLegendWidth {
			lines = append(lines, cur)
			cur = part
		} else if cur != "" {
			cur = cur + "   " + part
		} else {
			cur = part
		}
	}
	lines = append(lines, cur)
	return strings.Join(lines, "\n")
}

func namedLegend(names []string, colorOn bool, r ramp) string {
	parts := make([]string, len(names))
	for i, n := range names {
		parts[i] = legendSwatch(i, colorOn, r) + " " + n
	}
	return joinLegend(parts)
}

// level is which of n equal-width buckets norm (0..1) falls in, the maximum in the top one.
func level(norm float64, n int) int {
	return minInt(n-1, int(norm*float64(n)))
}

// --- canvas (line, scatter, dual_axis) ------------------------------------------------------------

type canvas struct {
	width, height int
	char          [][]string
	color         [][]int
}

func newCanvas(w, h int) *canvas {
	c := &canvas{width: w, height: h, char: make([][]string, h), color: make([][]int, h)}
	for y := 0; y < h; y++ {
		c.char[y] = make([]string, w)
		c.color[y] = make([]int, w)
		for x := range c.color[y] {
			c.color[y][x] = -1
		}
	}
	return c
}

func (c *canvas) setDot(x, y int, ch string, color int) {
	if x < 0 || y < 0 || x >= c.width || y >= c.height {
		return
	}
	if ch == "" {
		ch = "█"
	}
	c.char[y][x] = ch
	if color >= 0 {
		c.color[y][x] = color
	}
}

func (c *canvas) setMarker(x, y int, ch string, color int) {
	if x < 0 || y < 0 || x >= c.width || y >= c.height {
		return
	}
	c.char[y][x] = ch
	if color >= 0 {
		c.color[y][x] = color
	}
}

// line draws a Bresenham segment; dotted lights every other cell (and the end).
func (c *canvas) line(x0, y0, x1, y1 int, ch string, color int, dotted bool) {
	dx, dy := absInt(x1-x0), -absInt(y1-y0)
	sx, sy := 1, 1
	if x0 > x1 {
		sx = -1
	}
	if y0 > y1 {
		sy = -1
	}
	err := dx + dy
	x, y, step := x0, y0, 0
	for {
		if !dotted || step%2 == 0 || (x == x1 && y == y1) {
			c.setDot(x, y, ch, color)
		}
		if x == x1 && y == y1 {
			break
		}
		e2 := 2 * err
		if e2 >= dy {
			err += dy
			x += sx
		}
		if e2 <= dx {
			err += dx
			y += sy
		}
		step++
	}
}

func (c *canvas) render(colorOn bool) []string {
	rows := make([]string, c.height)
	for y := 0; y < c.height; y++ {
		var b strings.Builder
		for x := 0; x < c.width; x++ {
			ch := c.char[y][x]
			if ch == "" {
				ch = " "
			}
			b.WriteString(colorize(ch, c.color[y][x], colorOn))
		}
		rows[y] = b.String()
	}
	return rows
}

func absInt(a int) int {
	if a < 0 {
		return -a
	}
	return a
}

// grid is a character grid with a color per cell, joined into rows.
type grid struct {
	ch    [][]string
	color [][]int
}

func newGrid(w, h int) *grid {
	g := &grid{ch: make([][]string, h), color: make([][]int, h)}
	for y := 0; y < h; y++ {
		g.ch[y] = make([]string, w)
		g.color[y] = make([]int, w)
		for x := 0; x < w; x++ {
			g.ch[y][x] = " "
			g.color[y][x] = -1
		}
	}
	return g
}

func (g *grid) row(y int, colorOn bool) string {
	var b strings.Builder
	for x := range g.ch[y] {
		b.WriteString(colorize(g.ch[y][x], g.color[y][x], colorOn))
	}
	return b.String()
}
