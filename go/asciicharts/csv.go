package asciicharts

// A chart spec straight from a CSV file (spec/principles.md §9.5), as the Python reference builds it:
// the same delimiter sniffing (a port of CPython's csv.Sniffer), the same record parsing (a port of
// CPython's _csv reader state machine), the same number parsing and column matching, and the same
// error messages.

import (
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode"
)

// CSVSettable are the options --set may give.
var CSVSettable = []string{"title", "width", "height", "border", "style", "stacked", "bins", "useColor",
	"threshold", "thresholds", "showPoints", "pointChar"}

var (
	numThousands    = regexp.MustCompile(`^-?\p{Nd}{1,3}(,\p{Nd}{3})+(\.\p{Nd}+)?$`)
	numDecimalComma = regexp.MustCompile(`^-?\p{Nd}+,\p{Nd}+$`)
	pyFloatSyntax   = regexp.MustCompile(`(?i)^[+-]?(((\d(_?\d)*)?\.\d(_?\d)*|\d(_?\d)*\.?)(e[+-]?\d(_?\d)*)?|inf|infinity|nan)$`)
)

// pyIsSpace is Python's str.isspace() for one character.
func pyIsSpace(r rune) bool { return unicode.IsSpace(r) || (r >= 0x1c && r <= 0x1f) }

// pyStrip is Python's str.strip().
func pyStrip(s string) string { return strings.TrimFunc(s, pyIsSpace) }

// pyFloat is Python's float(s): its syntax (underscores between digits, inf/nan), not Go's.
func pyFloat(s string) (float64, bool) {
	s = asciiDigits(pyStrip(s))
	if !pyFloatSyntax.MatchString(s) {
		return 0, false
	}
	f, err := strconv.ParseFloat(strings.ReplaceAll(s, "_", ""), 64)
	if err != nil {
		if ne, ok := err.(*strconv.NumError); !ok || ne.Err != strconv.ErrRange {
			return 0, false
		}
	}
	return f, true
}

// asciiDigits replaces every Unicode decimal digit ("１２", "٣") with its ASCII digit, as Python's
// float() and int() read them. Decimal digits are encoded in runs of whole 0-9 blocks, so a digit's
// value is its distance from the start of its run, modulo 10.
func asciiDigits(s string) string {
	if !strings.ContainsFunc(s, func(r rune) bool { return r > 127 && unicode.Is(unicode.Nd, r) }) {
		return s
	}
	return strings.Map(func(r rune) rune {
		if r <= 127 || !unicode.Is(unicode.Nd, r) {
			return r
		}
		start := r
		for unicode.Is(unicode.Nd, start-1) {
			start--
		}
		return '0' + (r-start)%10
	}, s)
}

// parseCell reads a number from a CSV cell, tolerating decorations: spaces (also non-breaking), a
// leading currency sign, a trailing %, thousands separators, and a decimal comma when the file is
// not comma-separated.
func parseCell(cell string, delimiter rune) (float64, bool) {
	s := strings.ReplaceAll(strings.ReplaceAll(pyStrip(cell), string(rune(0xA0)), ""), " ", "")
	s = strings.TrimLeft(s, "$€£")
	s = strings.TrimRight(s, "%")
	if s == "" {
		return 0, false
	}
	if delimiter != ',' && numDecimalComma.MatchString(s) {
		s = strings.ReplaceAll(s, ",", ".")
	} else if numThousands.MatchString(s) {
		s = strings.ReplaceAll(s, ",", "")
	}
	v, ok := pyFloat(s)
	if !ok || v != v || v > 1.7976931348623157e308 || v < -1.7976931348623157e308 {
		return 0, false
	}
	return v, true
}

// --- delimiter sniffing: CPython's csv.Sniffer, restricted to the delimiters , ; tab | -----------

func isPyWord(r rune) bool { return r == '_' || unicode.IsLetter(r) || unicode.IsNumber(r) }

func isQuoteRune(r rune) bool { return r == '"' || r == '\'' }

func delimClass(r rune) bool { return !isPyWord(r) && r != '\n' && r != '"' && r != '\'' }

type sniffMatch struct {
	quote, delim     rune
	hasDelim, spaced bool
}

// sniffQuoted runs CPython's four quote-and-delimiter regular expressions (findall, in order, the
// first that matches wins), written out by hand because Go's regexp has no backreferences.
func sniffQuoted(s []rune) []sniffMatch {
	n := len(s)
	lineStart := func(i int) bool { return i == 0 || s[i-1] == '\n' }
	atLineEnd := func(k int) bool { return k+1 == n || s[k+1] == '\n' }
	// pattern 1: (delim)( ?)(quote).*?(quote)(delim)    pattern 3: (delim)( ?)(quote).*?(quote)(?:$|\n)
	delimQuoted := func(closeAtLineEnd bool) []sniffMatch {
		var out []sniffMatch
		for i := 0; i < n; {
			if delimClass(s[i]) {
				j, spaced := i+1, false
				if j < n && s[j] == ' ' {
					j, spaced = j+1, true
				}
				if j < n && isQuoteRune(s[j]) {
					q := s[j]
					for k := j + 1; k < n; k++ {
						if s[k] != q {
							continue
						}
						if closeAtLineEnd && atLineEnd(k) {
							out = append(out, sniffMatch{quote: q, delim: s[i], hasDelim: true, spaced: spaced})
							i = k + 1
							goto next
						}
						if !closeAtLineEnd && k+1 < n && s[k+1] == s[i] {
							out = append(out, sniffMatch{quote: q, delim: s[i], hasDelim: true, spaced: spaced})
							i = k + 2
							goto next
						}
					}
				}
			}
			i++
		next:
		}
		return out
	}
	// pattern 2: (?:^|\n)(quote).*?(quote)(delim)( ?)    pattern 4: (?:^|\n)(quote).*?(quote)(?:$|\n)
	lineQuoted := func(withDelim bool) []sniffMatch {
		var out []sniffMatch
		for i := 0; i < n; {
			var starts []int
			if lineStart(i) {
				starts = append(starts, i)
			}
			if s[i] == '\n' {
				starts = append(starts, i+1)
			}
			matched := false
			for _, p := range starts {
				if p >= n || !isQuoteRune(s[p]) {
					continue
				}
				q := s[p]
				for k := p + 1; k < n; k++ {
					if s[k] != q {
						continue
					}
					if withDelim && k+1 < n && delimClass(s[k+1]) {
						end := k + 2
						spaced := end < n && s[end] == ' '
						if spaced {
							end++
						}
						out = append(out, sniffMatch{quote: q, delim: s[k+1], hasDelim: true, spaced: spaced})
						i, matched = end, true
						break
					}
					if !withDelim && atLineEnd(k) {
						out = append(out, sniffMatch{quote: q})
						i, matched = k+1, true
						break
					}
				}
				if matched {
					break
				}
			}
			if !matched {
				i++
			}
		}
		return out
	}
	for _, try := range []func() []sniffMatch{
		func() []sniffMatch { return delimQuoted(false) },
		func() []sniffMatch { return lineQuoted(true) },
		func() []sniffMatch { return delimQuoted(true) },
		func() []sniffMatch { return lineQuoted(false) },
	} {
		if m := try(); len(m) > 0 {
			return m
		}
	}
	return nil
}

func firstMax(order []rune, count map[rune]int) rune {
	best := order[0]
	for _, r := range order[1:] {
		if count[r] > count[best] {
			best = r
		}
	}
	return best
}

func guessQuoteAndDelimiter(s []rune, delimiters string) rune {
	matches := sniffQuoted(s)
	if len(matches) == 0 {
		return 0
	}
	delims := map[rune]int{}
	var order []rune
	for _, m := range matches {
		if m.hasDelim && m.delim != 0 && strings.ContainsRune(delimiters, m.delim) {
			if _, seen := delims[m.delim]; !seen {
				order = append(order, m.delim)
			}
			delims[m.delim]++
		}
	}
	if len(order) == 0 {
		return 0
	}
	return firstMax(order, delims)
}

type freqCount struct{ freq, count int }

func guessDelimiter(sample string, delimiters string) rune {
	var data []string
	for _, l := range strings.Split(sample, "\n") {
		if l != "" {
			data = append(data, l)
		}
	}
	chunkLength := minInt(10, len(data))
	iteration := 0
	charFrequency := map[rune][]freqCount{} // per char: (frequency, rows) in first-seen order
	modes := map[rune]freqCount{}
	var modeOrder []rune
	delims := map[rune]freqCount{}
	var delimOrder []rune
	start, end := 0, chunkLength
	for start < len(data) {
		iteration++
		for _, line := range data[start:minInt(end, len(data))] {
			for c := rune(0); c < 127; c++ {
				freq := strings.Count(line, string(c))
				meta := charFrequency[c]
				found := false
				for i := range meta {
					if meta[i].freq == freq {
						meta[i].count++
						found = true
						break
					}
				}
				if !found {
					meta = append(meta, freqCount{freq, 1})
				}
				charFrequency[c] = meta
			}
		}
		for c := rune(0); c < 127; c++ {
			items, ok := charFrequency[c]
			if !ok || (len(items) == 1 && items[0].freq == 0) {
				continue
			}
			var mode freqCount
			if len(items) > 1 {
				best := 0
				for i := 1; i < len(items); i++ {
					if items[i].count > items[best].count {
						best = i
					}
				}
				others := 0
				for i := range items {
					if i != best {
						others += items[i].count
					}
				}
				mode = freqCount{items[best].freq, items[best].count - others}
			} else {
				mode = items[0]
			}
			if _, seen := modes[c]; !seen {
				modeOrder = append(modeOrder, c)
			}
			modes[c] = mode
		}
		total := float64(minInt(chunkLength*iteration, len(data)))
		consistency := 1.0
		for len(delims) == 0 && consistency >= 0.9 {
			for _, k := range modeOrder {
				v := modes[k]
				if v.freq > 0 && v.count > 0 && float64(v.count)/total >= consistency && strings.ContainsRune(delimiters, k) {
					if _, seen := delims[k]; !seen {
						delimOrder = append(delimOrder, k)
					}
					delims[k] = v
				}
			}
			consistency -= 0.01
		}
		if len(delims) == 1 {
			return delimOrder[0]
		}
		start = end
		end += chunkLength
	}
	if len(delims) == 0 {
		return 0
	}
	for _, d := range []rune{',', '\t', ';', ' ', ':'} {
		if _, ok := delims[d]; ok {
			return d
		}
	}
	sort.SliceStable(delimOrder, func(a, b int) bool {
		va, vb := delims[delimOrder[a]], delims[delimOrder[b]]
		if va.freq != vb.freq {
			return va.freq < vb.freq
		}
		if va.count != vb.count {
			return va.count < vb.count
		}
		return delimOrder[a] < delimOrder[b]
	})
	return delimOrder[len(delimOrder)-1]
}

// sniffDelimiter is csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter, "," when it can't tell.
func sniffDelimiter(text string) rune {
	sample := []rune(text)
	if len(sample) > 4096 {
		sample = sample[:4096]
	}
	if d := guessQuoteAndDelimiter(sample, ",;\t|"); d != 0 {
		return d
	}
	if d := guessDelimiter(string(sample), ",;\t|"); d != 0 {
		return d
	}
	return ','
}

// --- records: CPython's _csv reader (excel dialect, strict off) ---------------------------------

const (
	stStartRecord = iota
	stStartField
	stInField
	stInQuotedField
	stQuoteInQuotedField
	stEatCRNL
)

func readCSVRecords(text string, delimiter rune) ([][]string, error) {
	var records [][]string
	var fields []string
	var field []rune
	state := stStartRecord
	fieldLen := 0
	save := func() {
		fields = append(fields, string(field))
		field, fieldLen = field[:0], 0
	}
	add := func(c rune) {
		field = append(field, c)
		fieldLen++
	}
	const eol = rune(-2)
	process := func(c rune) error {
		switch state {
		case stStartRecord:
			if c == eol {
				return nil
			}
			if c == '\n' || c == '\r' {
				state = stEatCRNL
				return nil
			}
			state = stStartField
			fallthrough
		case stStartField:
			switch {
			case c == '\n' || c == '\r' || c == eol:
				save()
				if c == eol {
					state = stStartRecord
				} else {
					state = stEatCRNL
				}
			case c == '"':
				state = stInQuotedField
			case c == delimiter:
				save()
			default:
				add(c)
				state = stInField
			}
		case stInField:
			switch {
			case c == '\n' || c == '\r' || c == eol:
				save()
				if c == eol {
					state = stStartRecord
				} else {
					state = stEatCRNL
				}
			case c == delimiter:
				save()
				state = stStartField
			default:
				add(c)
			}
		case stInQuotedField:
			switch {
			case c == eol:
			case c == '"':
				state = stQuoteInQuotedField
			default:
				add(c)
			}
		case stQuoteInQuotedField:
			switch {
			case c == '"':
				add(c)
				state = stInQuotedField
			case c == delimiter:
				save()
				state = stStartField
			case c == '\n' || c == '\r' || c == eol:
				save()
				if c == eol {
					state = stStartRecord
				} else {
					state = stEatCRNL
				}
			default:
				add(c)
				state = stInField
			}
		case stEatCRNL:
			switch {
			case c == '\n' || c == '\r':
			case c == eol:
				state = stStartRecord
			default:
				return errorf("new-line character seen in unquoted field - do you need to open the file with newline=''?")
			}
		}
		return nil
	}
	lines := strings.SplitAfter(text, "\n")
	for li, line := range lines {
		if line == "" && li == len(lines)-1 {
			break
		}
		for _, c := range line {
			if err := process(c); err != nil {
				return nil, err
			}
		}
		if err := process(eol); err != nil {
			return nil, err
		}
		if state == stStartRecord {
			records = append(records, fields)
			fields = nil
		}
	}
	if fieldLen != 0 || state == stInQuotedField {
		save()
		records = append(records, fields)
	}
	return records, nil
}

func readCSV(text string) (header []string, rows [][]string, delimiter rune, err error) {
	text = strings.TrimLeft(text, string(rune(0xFEFF)))
	if pyStrip(text) == "" {
		return nil, nil, 0, errorf("the CSV is empty")
	}
	delimiter = sniffDelimiter(text)
	records, err := readCSVRecords(text, delimiter)
	if err != nil {
		return nil, nil, 0, err
	}
	var kept [][]string
	for _, r := range records {
		for _, c := range r {
			if pyStrip(c) != "" {
				kept = append(kept, r)
				break
			}
		}
	}
	if len(kept) < 2 {
		return nil, nil, 0, errorf("the CSV needs a header row and at least one data row")
	}
	for _, h := range kept[0] {
		header = append(header, pyStrip(h))
	}
	for _, r := range kept[1:] {
		row := append([]string(nil), r...)
		for len(row) < len(header) {
			row = append(row, "")
		}
		rows = append(rows, row)
	}
	return header, rows, delimiter, nil
}

// column resolves a column reference: exact name, case-insensitive name, 1-based index, unique
// prefix, unique substring.
func column(header []string, ref, what string) (int, error) {
	ref = pyStrip(ref)
	for i, h := range header {
		if h == ref {
			return i, nil
		}
	}
	lowered := make([]string, len(header))
	for i, h := range header {
		lowered[i] = pyLower(h)
	}
	low := pyLower(ref)
	idx, count := -1, 0
	for i, h := range lowered {
		if h == low {
			if idx < 0 {
				idx = i
			}
			count++
		}
	}
	if count == 1 {
		return idx, nil
	}
	if isDigits(ref) {
		if n, err := strconv.Atoi(asciiDigits(ref)); err == nil && n >= 1 && n <= len(header) {
			return n - 1, nil
		}
	}
	for _, test := range []func(string) bool{
		func(h string) bool { return strings.HasPrefix(h, low) },
		func(h string) bool { return strings.Contains(h, low) },
	} {
		var matches []int
		for i, h := range lowered {
			if test(h) {
				matches = append(matches, i)
			}
		}
		if len(matches) == 1 && low != "" {
			return matches[0], nil
		}
		if len(matches) > 1 {
			names := make([]string, len(matches))
			for i, m := range matches {
				names[i] = header[m]
			}
			return 0, errorf(`%s column "%s" is ambiguous; it matches: %s`, what, ref, strings.Join(names, ", "))
		}
	}
	return 0, errorf(`%s column "%s" not found; the columns are: %s`, what, ref, strings.Join(header, ", "))
}

func isDigits(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		if !unicode.Is(unicode.Nd, r) {
			return false
		}
	}
	return true
}

func splitColumns(header []string, spec, what string) ([]int, error) {
	for i, h := range header {
		if h == pyStrip(spec) {
			return []int{i}, nil
		}
	}
	var out []int
	for _, part := range strings.Split(spec, ",") {
		if pyStrip(part) == "" {
			continue
		}
		i, err := column(header, part, what)
		if err != nil {
			return nil, err
		}
		out = append(out, i)
	}
	return out, nil
}

// CSVOptions are the choices SpecFromCSV takes besides the text and the chart type.
type CSVOptions struct {
	Label, Values, Sort string
	Limit               *int
	Set                 *Object // extra spec fields (title, width, ...), in order
}

// SpecFromCSV turns CSV text into a chart spec, as the Python reference's spec_from_csv does.
func SpecFromCSV(text, chart string, opt CSVOptions) (*Object, error) {
	known := false
	for _, t := range ChartTypes() {
		known = known || t == chart
	}
	if !known {
		return nil, errorf("unknown chartType %s (expected one of: %s)", quote(chart), strings.Join(ChartTypes(), ", "))
	}
	header, rows, delim, err := readCSV(text)
	if err != nil {
		return nil, err
	}
	var numeric []int
	isNumeric := map[int]bool{}
	for ci := range header {
		any, all := false, true
		for _, r := range rows {
			if pyStrip(r[ci]) == "" {
				continue
			}
			any = true
			if _, ok := parseCell(r[ci], delim); !ok {
				all = false
			}
		}
		if any && all {
			numeric = append(numeric, ci)
			isNumeric[ci] = true
		}
	}

	labelIdx := -1
	if chart == "scatter" {
		switch {
		case opt.Label != "":
			if labelIdx, err = column(header, opt.Label, "label (x)"); err != nil {
				return nil, err
			}
		case len(numeric) > 0:
			labelIdx = numeric[0]
		default:
			return nil, errorf("scatter needs a numeric x column; none of the columns is numeric")
		}
	} else {
		if opt.Label != "" {
			if labelIdx, err = column(header, opt.Label, "label"); err != nil {
				return nil, err
			}
		} else {
			for ci := range header {
				if !isNumeric[ci] {
					labelIdx = ci
					break
				}
			}
		}
	}

	var valIdx []int
	if opt.Values != "" {
		if valIdx, err = splitColumns(header, opt.Values, "values"); err != nil {
			return nil, err
		}
	} else {
		for _, ci := range numeric {
			if ci != labelIdx {
				valIdx = append(valIdx, ci)
			}
		}
	}
	if len(valIdx) == 0 {
		return nil, errorf("no numeric columns to plot; the columns are: %s (use --values to pick columns explicitly)",
			strings.Join(header, ", "))
	}

	if opt.Sort != "" {
		srt := opt.Sort
		desc := false
		if i := strings.LastIndex(srt, ":"); i > 0 && (pyLower(srt[i+1:]) == "asc" || pyLower(srt[i+1:]) == "desc") {
			desc = pyLower(srt[i+1:]) == "desc"
			srt = srt[:i]
		} else {
			desc = strings.HasPrefix(srt, "-")
		}
		ref := strings.TrimLeft(srt, "-+")
		for _, h := range header {
			if h == pyStrip(srt) {
				ref = pyStrip(srt)
			}
		}
		si, err := column(header, ref, "sort")
		if err != nil {
			return nil, err
		}
		less := func(a, b []string) bool {
			x, xok := parseCell(a[si], delim)
			y, yok := parseCell(b[si], delim)
			if isNumeric[si] {
				if xok != yok {
					return xok // numbers first
				}
				return x < y
			}
			return pyLower(pyStrip(a[si])) < pyLower(pyStrip(b[si]))
		}
		sorted := append([][]string(nil), rows...)
		sort.SliceStable(sorted, func(i, j int) bool {
			if desc {
				return less(sorted[j], sorted[i])
			}
			return less(sorted[i], sorted[j])
		})
		rows = sorted
	}
	if opt.Limit != nil {
		if *opt.Limit < 1 {
			return nil, errorf("limit must be at least 1")
		}
		if *opt.Limit < len(rows) {
			rows = rows[:*opt.Limit]
		}
	}

	number := func(ri, ci int) (float64, error) {
		v, ok := parseCell(rows[ri][ci], delim)
		if !ok {
			raw := pyStrip(rows[ri][ci])
			why := "is empty"
			if raw != "" {
				why = "is not a number: " + quote(raw)
			}
			return 0, errorf(`row %d, column "%s" %s`, ri+2, header[ci], why)
		}
		return v, nil
	}
	labelsForRows := func() []any {
		out := make([]any, len(rows))
		for i := range rows {
			s := pyStrip(rows[i][labelIdx])
			if s == "" {
				s = strconv.Itoa(i + 1)
			}
			out[i] = s
		}
		return out
	}
	rowNames := func() []any {
		if labelIdx >= 0 {
			return labelsForRows()
		}
		out := make([]any, len(rows))
		for i := range rows {
			out[i] = strconv.Itoa(i + 1)
		}
		return out
	}

	spec := NewObject()
	spec.Set("chartType", chart)
	var ss []any
	switch chart {
	case "pie":
		names := rowNames()
		for i := range rows {
			v, err := number(i, valIdx[0])
			if err != nil {
				return nil, err
			}
			s := NewObject()
			s.Set("name", names[i])
			s.Set("values", []any{v})
			ss = append(ss, s)
		}
		spec.Set("series", ss)
	case "heatmap":
		names := rowNames()
		labels := make([]any, len(valIdx))
		for i, ci := range valIdx {
			labels[i] = header[ci]
		}
		spec.Set("labels", labels)
		for i := range rows {
			vals := make([]any, len(valIdx))
			for j, ci := range valIdx {
				v, err := number(i, ci)
				if err != nil {
					return nil, err
				}
				vals[j] = v
			}
			s := NewObject()
			s.Set("name", names[i])
			s.Set("values", vals)
			ss = append(ss, s)
		}
		spec.Set("series", ss)
	case "scatter":
		for _, ci := range valIdx {
			if ci == labelIdx {
				continue
			}
			var pts []any
			for i := range rows {
				x, err := number(i, labelIdx)
				if err != nil {
					return nil, err
				}
				y, err := number(i, ci)
				if err != nil {
					return nil, err
				}
				p := NewObject()
				p.Set("x", x)
				p.Set("y", y)
				pts = append(pts, p)
			}
			s := NewObject()
			s.Set("name", header[ci])
			s.Set("points", orEmptySlice(pts))
			ss = append(ss, s)
		}
		if len(ss) == 0 {
			return nil, errorf("scatter needs at least one y column besides the x column")
		}
		spec.Set("series", ss)
	default:
		if labelIdx >= 0 && (chart == "vbar" || chart == "hbar" || chart == "dotplot" || chart == "line" || chart == "area") {
			spec.Set("labels", labelsForRows())
		}
		for _, ci := range valIdx {
			vals := make([]any, len(rows))
			for i := range rows {
				v, err := number(i, ci)
				if err != nil {
					return nil, err
				}
				vals[i] = v
			}
			s := NewObject()
			s.Set("name", header[ci])
			s.Set("values", vals)
			ss = append(ss, s)
		}
		spec.Set("series", ss)
	}
	if opt.Set != nil {
		for _, k := range opt.Set.keys {
			settable := false
			for _, s := range CSVSettable {
				settable = settable || s == k
			}
			if !settable {
				return nil, errorf("unknown option %s (settable: %s)", quote(k), strings.Join(CSVSettable, ", "))
			}
			spec.Set(k, opt.Set.vals[k])
		}
	}
	return spec, nil
}

func orEmptySlice(xs []any) []any {
	if xs == nil {
		return []any{}
	}
	return xs
}

// ParseSet reads --set key=value pairs: a value is JSON if it parses as JSON (Python's json.loads,
// which also takes NaN and Infinity), else the raw text.
func ParseSet(pairs []string) (*Object, error) {
	out := NewObject()
	for _, pair := range pairs {
		key, raw, ok := strings.Cut(pair, "=")
		if !ok {
			return nil, errorf("--set expects key=value, got %s", quote(pair))
		}
		var v any = raw
		switch strings.Trim(raw, " \t\n\r") {
		case "NaN":
			v = math.NaN()
		case "Infinity":
			v = math.Inf(1)
		case "-Infinity":
			v = math.Inf(-1)
		default:
			if parsed, err := DecodeOrdered([]byte(raw)); err == nil {
				v = parsed
			}
		}
		out.Set(pyStrip(key), v)
	}
	return out, nil
}

// pyLower is Python's str.lower(): full case mapping, so "İ" becomes "i̇" and a capital sigma at the
// end of a word becomes "ς".
func pyLower(s string) string {
	if !strings.ContainsAny(s, "İΣ") {
		return strings.ToLower(s)
	}
	rs := []rune(s)
	var b strings.Builder
	for i, r := range rs {
		switch r {
		case 'İ':
			b.WriteString("i̇")
		case 'Σ':
			if finalSigma(rs, i) {
				b.WriteRune('ς')
			} else {
				b.WriteRune('σ')
			}
		default:
			b.WriteRune(unicode.ToLower(r))
		}
	}
	return b.String()
}

func isCased(r rune) bool {
	return unicode.IsUpper(r) || unicode.IsLower(r) || unicode.IsTitle(r) ||
		unicode.Is(unicode.Other_Lowercase, r) || unicode.Is(unicode.Other_Uppercase, r)
}

func isCaseIgnorable(r rune) bool {
	return unicode.In(r, unicode.Mn, unicode.Me, unicode.Cf, unicode.Lm, unicode.Sk) ||
		strings.ContainsRune("'.:·՟״‘’․‧︓﹒﹕＇．：", r)
}

func finalSigma(rs []rune, i int) bool {
	j := i - 1
	for j >= 0 && isCaseIgnorable(rs[j]) {
		j--
	}
	if j < 0 || !isCased(rs[j]) {
		return false
	}
	j = i + 1
	for j < len(rs) && isCaseIgnorable(rs[j]) {
		j++
	}
	return j == len(rs) || !isCased(rs[j])
}
