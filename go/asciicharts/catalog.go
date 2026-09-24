package asciicharts

import (
	"bytes"
	"encoding/json"
)

// ChartInfo describes one chart type: what it draws, how its series are read, the options that
// matter for it, and a minimal spec that renders.
type ChartInfo struct {
	Type    string         `json:"type"`
	Summary string         `json:"summary"`
	Series  string         `json:"series"`
	Options []string       `json:"options"`
	Example map[string]any `json:"example"`
}

// ListCharts returns the chart catalogue, in order. The result is a fresh copy.
func ListCharts() []ChartInfo {
	var out []ChartInfo
	dec := json.NewDecoder(bytes.NewReader([]byte(catalogJSON)))
	dec.UseNumber()
	if err := dec.Decode(&out); err != nil {
		panic("asciicharts: bad generated catalogue: " + err.Error())
	}
	return out
}

// ChartTypes returns the chart type names, in catalogue order.
func ChartTypes() []string {
	charts := ListCharts()
	names := make([]string, len(charts))
	for i, c := range charts {
		names[i] = c.Type
	}
	return names
}
