package chart

import (
	"fmt"
	"math"
	"strings"
	"unicode/utf8"
)

// heatRamp is a blue-to-red ANSI 256-color ramp used for colored heatmap
// cells, from low to high value.
var heatRamp = []int{21, 27, 33, 39, 45, 51, 87, 123, 159, 195, 226, 220, 214, 208, 202, 196}

const heatCellWidth = 3

func renderHeatmap(in Input) (string, error) {
	if len(in.Series) == 0 {
		return "", fmt.Errorf("series must contain at least one row")
	}
	numCols := len(in.Series[0].Values)
	if numCols == 0 {
		return "", fmt.Errorf("each row must contain at least one value")
	}
	for i, s := range in.Series {
		if len(s.Values) != numCols {
			return "", fmt.Errorf("all rows must have the same number of values (row 0 has %d, row %d has %d)", numCols, i, len(s.Values))
		}
	}
	if len(in.Labels) > 0 && len(in.Labels) != numCols {
		return "", fmt.Errorf("labels length (%d) must match each row's values length (%d)", len(in.Labels), numCols)
	}

	lo, hi := in.Series[0].Values[0], in.Series[0].Values[0]
	for _, s := range in.Series {
		for _, v := range s.Values {
			lo = math.Min(lo, v)
			hi = math.Max(hi, v)
		}
	}
	if hi == lo {
		hi = lo + 1
	}

	colorOn := in.UseColor.enabled()

	rowLabelW := 0
	for _, s := range in.Series {
		rowLabelW = max(rowLabelW, utf8.RuneCountInString(s.Name))
	}

	var sb strings.Builder
	if len(in.Labels) > 0 {
		sb.WriteString(strings.Repeat(" ", rowLabelW+1))
		for _, c := range in.Labels {
			sb.WriteString(padCenter(c, heatCellWidth))
			sb.WriteByte(' ')
		}
		sb.WriteByte('\n')
	}

	for ri, s := range in.Series {
		sb.WriteString(s.Name)
		sb.WriteString(strings.Repeat(" ", rowLabelW-utf8.RuneCountInString(s.Name)))
		sb.WriteByte(' ')
		for _, v := range s.Values {
			norm := (v - lo) / (hi - lo)
			var cell string
			if colorOn {
				idx := int(norm * float64(len(heatRamp)-1))
				cell = colorize(strings.Repeat("█", heatCellWidth), heatRamp[idx], true)
			} else {
				idx := int(norm * float64(len(shades)-1))
				cell = strings.Repeat(string(shades[idx]), heatCellWidth)
			}
			sb.WriteString(cell)
			sb.WriteByte(' ')
		}
		if ri < len(in.Series)-1 {
			sb.WriteByte('\n')
		}
	}

	return sb.String(), nil
}
