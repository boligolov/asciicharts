package chart

import (
	"fmt"
	"math"
)

func renderHistogram(in Input) (string, error) {
	if len(in.Series) != 1 {
		return "", fmt.Errorf("histogram expects exactly one series, got %d", len(in.Series))
	}
	values := in.Series[0].Values
	if len(values) == 0 {
		return "", fmt.Errorf("series must contain at least one value")
	}

	bins := in.Bins
	if bins <= 0 {
		bins = 10
	}

	min, max := values[0], values[0]
	for _, v := range values {
		min = math.Min(min, v)
		max = math.Max(max, v)
	}
	if max == min {
		max = min + 1
	}
	binWidth := (max - min) / float64(bins)

	counts := make([]float64, bins)
	for _, v := range values {
		idx := int((v - min) / binWidth)
		idx = clampInt(idx, 0, bins-1)
		counts[idx]++
	}

	labels := make([]string, bins)
	for i := range labels {
		lo := min + float64(i)*binWidth
		hi := lo + binWidth
		labels[i] = fmt.Sprintf("%s..%s", formatValue(lo), formatValue(hi))
	}

	return renderHorizontalBars(labels, counts, in.Width, barFillRamp(in.Style)), nil
}
