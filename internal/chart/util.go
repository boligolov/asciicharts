package chart

import (
	"math"
	"strconv"
	"strings"
	"unicode/utf8"
)

func padCenter(s string, width int) string {
	w := utf8.RuneCountInString(s)
	if w >= width {
		return truncateRunes(s, width)
	}
	left := (width - w) / 2
	right := width - w - left
	return strings.Repeat(" ", left) + s + strings.Repeat(" ", right)
}

func formatValue(v float64) string {
	if math.Abs(v-math.Trunc(v)) < 1e-9 {
		return strconv.FormatFloat(v, 'f', 0, 64)
	}
	return strconv.FormatFloat(v, 'f', 2, 64)
}

func clampInt(v, lo, hi int) int {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func truncateRunes(s string, max int) string {
	if max <= 0 {
		return ""
	}
	r := []rune(s)
	if len(r) <= max {
		return s
	}
	return string(r[:max])
}
