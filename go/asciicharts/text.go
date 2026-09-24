package asciicharts

// Text is measured in terminal columns, not code points (spec/principles.md §6).

import (
	"regexp"
	"sort"
	"strings"
	"unicode/utf8"
)

type runeRange struct{ lo, hi rune }

func inRanges(r rune, rs []runeRange) bool {
	i := sort.Search(len(rs), func(i int) bool { return rs[i].hi >= r })
	return i < len(rs) && rs[i].lo <= r
}

// charWidth is the number of columns one code point takes: 0 for combining marks and invisible
// format characters, 2 for East Asian wide and fullwidth, 1 otherwise.
func charWidth(r rune) int {
	if inRanges(r, zeroWidthRanges) {
		return 0
	}
	if inRanges(r, wideRanges) {
		return 2
	}
	return 1
}

func isASCII(s string) bool {
	for i := 0; i < len(s); i++ {
		if s[i] >= 0x80 {
			return false
		}
	}
	return true
}

// cells splits s into terminal columns: a wide character is followed by an empty cell (its right
// half), a zero-width one joins the column before it.
func cells(s string) []string {
	if isASCII(s) {
		out := make([]string, len(s))
		for i := 0; i < len(s); i++ {
			out[i] = s[i : i+1]
		}
		return out
	}
	var out []string
	for _, r := range s {
		w := charWidth(r)
		switch {
		case w == 0 && len(out) > 0:
			i := len(out) - 1
			if out[i] == "" {
				i--
			}
			out[i] += string(r)
		case w == 2:
			out = append(out, string(r), "")
		default:
			out = append(out, string(r))
		}
	}
	return out
}

// width is len(cells(s)).
func width(s string) int {
	if isASCII(s) {
		return len(s)
	}
	n := 0
	first := true
	for _, r := range s {
		w := charWidth(r)
		if first && w == 0 {
			n++ // a leading zero-width character gets a column of its own
		}
		first = false
		n += w
	}
	return n
}

var ansiRE = regexp.MustCompile("\x1b\\[[0-9;]*m")

func visibleWidth(s string) int {
	if strings.Contains(s, "\x1b") {
		return width(ansiRE.ReplaceAllString(s, ""))
	}
	return width(s)
}

// pad left-aligns s in w columns.
func pad(s string, w int) string {
	return s + repeat(" ", w-width(s))
}

// truncate keeps the first n columns of s; a wide character that would be cut in half becomes a space.
func truncate(s string, n int) string {
	if n <= 0 {
		return ""
	}
	cs := cells(s)
	if len(cs) <= n {
		return s
	}
	cut := append([]string(nil), cs[:n]...)
	if cs[n] == "" {
		cut[n-1] = " "
	}
	return strings.Join(cut, "")
}

func padCenter(s string, w int) string {
	sw := width(s)
	if sw >= w {
		return truncate(s, w)
	}
	left := (w - sw) / 2
	return repeat(" ", left) + s + repeat(" ", w-sw-left)
}

// clean bounds user text and replaces control characters with spaces.
func clean(s, where string) (string, error) {
	if n := utf8.RuneCountInString(s); n > maxText {
		return "", errorf("%s must be at most %d characters, got %d", where, maxText, n)
	}
	if !strings.ContainsFunc(s, isControl) {
		return s, nil
	}
	return strings.Map(func(r rune) rune {
		if isControl(r) {
			return ' '
		}
		return r
	}, s), nil
}

func isControl(r rune) bool { return inRanges(r, controlRanges) }

// firstRune is Python's s[:1].
func firstRune(s string) string {
	for _, r := range s {
		return string(r)
	}
	return ""
}
