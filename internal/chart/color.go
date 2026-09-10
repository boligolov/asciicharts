package chart

import "fmt"

// UseColor selects whether rendered charts carry ANSI 256-color escape
// codes.
type UseColor string

const (
	// ColorAuto would enable color only when output goes to a terminal.
	// An MCP tool's text result is consumed by an agent, never a TTY, so
	// auto is equivalent to off here; it exists for parity with the
	// on/off/auto vocabulary and to make that equivalence explicit rather
	// than surprising.
	ColorAuto UseColor = "auto"
	ColorOn   UseColor = "on"
	ColorOff  UseColor = "off"
)

func validUseColor(c UseColor) bool {
	switch c {
	case "", ColorAuto, ColorOn, ColorOff:
		return true
	}
	return false
}

func (c UseColor) enabled() bool {
	return c == ColorOn
}

// thresholdColor is a neutral gray used for the optional line-chart
// threshold overlay, distinct from the series palette.
const thresholdColor = 244

// seriesColor returns the ANSI 256-color code assigned to series index i,
// cycling through palette256.
func seriesColor(i int) int {
	return palette256[i%len(palette256)]
}

// colorize wraps s in an ANSI 256-color foreground escape sequence when
// enabled is true and color >= 0; otherwise it returns s unchanged.
func colorize(s string, color int, enabled bool) string {
	if !enabled || color < 0 || s == "" {
		return s
	}
	return fmt.Sprintf("\x1b[38;5;%dm%s\x1b[0m", color, s)
}
