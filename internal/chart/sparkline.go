package chart

import (
	"fmt"
	"strings"
)

var sparkTicks = []rune{'▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'}

func renderSparkline(in Input) (string, error) {
	colorOn := in.UseColor.enabled()
	lines := make([]string, len(in.Series))
	for i, s := range in.Series {
		if len(s.Values) == 0 {
			return "", fmt.Errorf("series %d %q must contain at least one value", i, s.Name)
		}
		spark := colorize(sparklineFor(s.Values), seriesColor(i), colorOn)
		if s.Name != "" {
			lines[i] = fmt.Sprintf("%s %s", s.Name, spark)
		} else {
			lines[i] = spark
		}
	}
	return strings.Join(lines, "\n"), nil
}

func sparklineFor(values []float64) string {
	min, max := values[0], values[0]
	for _, v := range values {
		if v < min {
			min = v
		}
		if v > max {
			max = v
		}
	}
	span := max - min

	var sb strings.Builder
	for _, v := range values {
		idx := 0
		if span > 0 {
			idx = int((v - min) / span * float64(len(sparkTicks)-1))
		}
		sb.WriteRune(sparkTicks[idx])
	}
	return sb.String()
}
