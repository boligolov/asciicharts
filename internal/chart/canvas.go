package chart

import "strings"

// Mode selects the sub-character resolution used to rasterize line and
// scatter charts.
type Mode string

const (
	ModeCell    Mode = "cell"    // one data point per character cell
	ModeQuad    Mode = "quad"    // 2x2 dots per cell, via quadrant blocks
	ModeBraille Mode = "braille" // 2x4 dots per cell, via braille patterns
)

func validMode(m Mode) bool {
	switch m {
	case "", ModeCell, ModeQuad, ModeBraille:
		return true
	}
	return false
}

func (m Mode) subGrid() (dx, dy int) {
	switch m {
	case ModeQuad:
		return 2, 2
	case ModeBraille:
		return 2, 4
	default:
		return 1, 1
	}
}

// canvas is a character-cell grid that line, scatter and dual_axis charts
// draw onto. In quad/braille modes, points and lines are plotted in a
// finer sub-cell pixel space and packed into the character glyph that
// covers each cell.
type canvas struct {
	mode          Mode
	width, height int // character cells
	subX, subY    int // dots per cell
	bits          [][]uint16
	cellChar      [][]rune
	cellColor     [][]int
}

func newCanvas(mode Mode, width, height int) *canvas {
	subX, subY := mode.subGrid()
	c := &canvas{mode: mode, width: width, height: height, subX: subX, subY: subY}
	c.bits = make([][]uint16, height)
	c.cellChar = make([][]rune, height)
	c.cellColor = make([][]int, height)
	for y := 0; y < height; y++ {
		c.bits[y] = make([]uint16, width)
		c.cellChar[y] = make([]rune, width)
		c.cellColor[y] = make([]int, width)
		for x := 0; x < width; x++ {
			c.cellColor[y][x] = -1
		}
	}
	return c
}

func (c *canvas) pixelWidth() int  { return c.width * c.subX }
func (c *canvas) pixelHeight() int { return c.height * c.subY }

// setDot turns on a single sub-cell dot at pixel coordinates (px, py). In
// cell mode there is only one dot per cell, so this fills the whole cell
// with ch (or '█' if ch is zero).
func (c *canvas) setDot(px, py int, ch rune, color int) {
	if px < 0 || py < 0 || px >= c.pixelWidth() || py >= c.pixelHeight() {
		return
	}
	cellX, cellY := px/c.subX, py/c.subY
	dx, dy := px%c.subX, py%c.subY
	switch c.mode {
	case ModeQuad:
		c.bits[cellY][cellX] |= uint16(quadBit[[2]int{dx, dy}])
	case ModeBraille:
		c.bits[cellY][cellX] |= brailleBit[dx][dy]
	default:
		if ch == 0 {
			ch = '█'
		}
		c.cellChar[cellY][cellX] = ch
	}
	if color >= 0 {
		c.cellColor[cellY][cellX] = color
	}
}

// setMarker overrides a whole character cell with a specific glyph,
// regardless of mode. Used for scatter markers in cell mode, where a
// point is a full character rather than a sub-cell dot.
func (c *canvas) setMarker(cellX, cellY int, ch rune, color int) {
	if cellX < 0 || cellY < 0 || cellX >= c.width || cellY >= c.height {
		return
	}
	c.cellChar[cellY][cellX] = ch
	if color >= 0 {
		c.cellColor[cellY][cellX] = color
	}
}

// line draws a straight segment between two points in pixel space using
// Bresenham's algorithm.
func (c *canvas) line(x0, y0, x1, y1 int, ch rune, color int) {
	dx := absInt(x1 - x0)
	dy := -absInt(y1 - y0)
	sx, sy := 1, 1
	if x0 > x1 {
		sx = -1
	}
	if y0 > y1 {
		sy = -1
	}
	err := dx + dy
	x, y := x0, y0
	for {
		c.setDot(x, y, ch, color)
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
	}
}

// lineDotted draws a straight segment like line, but only lights every
// other pixel along the path (always including the endpoint), giving a
// sparse plotted-dot trace instead of a solid connecting stroke — the
// "+"-plotted trend line look of old dot-matrix terminal charts.
func (c *canvas) lineDotted(x0, y0, x1, y1 int, ch rune, color int) {
	dx := absInt(x1 - x0)
	dy := -absInt(y1 - y0)
	sx, sy := 1, 1
	if x0 > x1 {
		sx = -1
	}
	if y0 > y1 {
		sy = -1
	}
	err := dx + dy
	x, y := x0, y0
	step := 0
	for {
		if step%2 == 0 || (x == x1 && y == y1) {
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

func (c *canvas) charAt(x, y int) rune {
	if c.cellChar[y][x] != 0 {
		return c.cellChar[y][x]
	}
	if c.mode == ModeCell {
		return ' '
	}
	b := c.bits[y][x]
	if b == 0 {
		return ' '
	}
	if c.mode == ModeBraille {
		return rune(brailleBase + int(b))
	}
	return quadChars[b]
}

func (c *canvas) render(colorEnabled bool) []string {
	lines := make([]string, c.height)
	for y := 0; y < c.height; y++ {
		var sb strings.Builder
		for x := 0; x < c.width; x++ {
			sb.WriteString(colorize(string(c.charAt(x, y)), c.cellColor[y][x], colorEnabled))
		}
		lines[y] = sb.String()
	}
	return lines
}

func absInt(v int) int {
	if v < 0 {
		return -v
	}
	return v
}
