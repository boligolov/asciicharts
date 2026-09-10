// Package border wraps a block of pre-rendered text lines in a text frame,
// optionally with a centered title row.
package border

import (
	"regexp"
	"strings"
	"unicode/utf8"
)

var ansiEscape = regexp.MustCompile("\x1b\\[[0-9;]*m")

// visibleWidth returns the rune width of s as it would display in a
// terminal, ignoring ANSI SGR (color) escape sequences.
func visibleWidth(s string) int {
	if !strings.ContainsRune(s, '\x1b') {
		return utf8.RuneCountInString(s)
	}
	return utf8.RuneCountInString(ansiEscape.ReplaceAllString(s, ""))
}

// Style selects which characters are used to draw the frame.
type Style string

const (
	None    Style = "none"
	ASCII   Style = "ascii"
	Light   Style = "light"
	Heavy   Style = "heavy"
	Double  Style = "double"
	Rounded Style = "rounded"
)

// Valid reports whether s is a known style (including the empty string,
// which callers should treat as the default).
func Valid(s Style) bool {
	switch s {
	case "", None, ASCII, Light, Heavy, Double, Rounded:
		return true
	}
	return false
}

type charset struct {
	topLeft, topRight, bottomLeft, bottomRight string
	horizontal, vertical                       string
	leftT, rightT                              string
}

var charsets = map[Style]charset{
	ASCII: {
		topLeft: "+", topRight: "+", bottomLeft: "+", bottomRight: "+",
		horizontal: "-", vertical: "|",
		leftT: "+", rightT: "+",
	},
	Light: {
		topLeft: "┌", topRight: "┐", bottomLeft: "└", bottomRight: "┘",
		horizontal: "─", vertical: "│",
		leftT: "├", rightT: "┤",
	},
	Heavy: {
		topLeft: "┏", topRight: "┓", bottomLeft: "┗", bottomRight: "┛",
		horizontal: "━", vertical: "┃",
		leftT: "┣", rightT: "┫",
	},
	Double: {
		topLeft: "╔", topRight: "╗", bottomLeft: "╚", bottomRight: "╝",
		horizontal: "═", vertical: "║",
		leftT: "╠", rightT: "╣",
	},
	Rounded: {
		topLeft: "╭", topRight: "╮", bottomLeft: "╰", bottomRight: "╯",
		horizontal: "─", vertical: "│",
		leftT: "├", rightT: "┤",
	},
}

// Wrap frames body (a block of text, possibly multiple lines) in the given
// border style, with an optional title. An empty or "none" style skips the
// frame; the title, if any, is still emitted as a plain line above the body.
func Wrap(body string, title string, style Style) string {
	lines := strings.Split(body, "\n")

	if style == "" {
		style = Light
	}

	if style == None {
		if title == "" {
			return body
		}
		return title + "\n" + body
	}

	cs, ok := charsets[style]
	if !ok {
		cs = charsets[Light]
	}

	width := visibleWidth(title)
	for _, l := range lines {
		if w := visibleWidth(l); w > width {
			width = w
		}
	}

	var sb strings.Builder

	writeRule := func(left, right string) {
		sb.WriteString(left)
		sb.WriteString(strings.Repeat(cs.horizontal, width+2))
		sb.WriteString(right)
		sb.WriteByte('\n')
	}

	writeRow := func(text string) {
		sb.WriteString(cs.vertical)
		sb.WriteByte(' ')
		sb.WriteString(text)
		sb.WriteString(strings.Repeat(" ", width-visibleWidth(text)))
		sb.WriteByte(' ')
		sb.WriteString(cs.vertical)
		sb.WriteByte('\n')
	}

	writeRule(cs.topLeft, cs.topRight)
	if title != "" {
		pad := width - visibleWidth(title)
		leftPad := pad / 2
		rightPad := pad - leftPad
		writeRow(strings.Repeat(" ", leftPad) + title + strings.Repeat(" ", rightPad))
		writeRule(cs.leftT, cs.rightT)
	}
	for _, l := range lines {
		writeRow(l)
	}
	writeRule(cs.bottomLeft, cs.bottomRight)

	return strings.TrimSuffix(sb.String(), "\n")
}
