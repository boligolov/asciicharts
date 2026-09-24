package asciicharts

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
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

// ListText is the chart catalogue as the command line's --list prints it.
func ListText() string {
	all, err := DecodeOrdered([]byte(catalogJSON))
	if err != nil {
		panic("asciicharts: bad generated catalogue: " + err.Error())
	}
	var b strings.Builder
	for _, c := range all.([]any) {
		o := c.(*Object)
		get := func(k string) any { v, _ := o.Get(k); return v }
		var opts []string
		for _, x := range get("options").([]any) {
			opts = append(opts, x.(string))
		}
		optText := strings.Join(opts, ", ")
		if optText == "" {
			optText = "-"
		}
		fmt.Fprintf(&b, "%s\n  %s\n  series:  %s\n  options: %s\n  example: %s\n\n",
			get("type"), get("summary"), get("series"), optText, PyJSONCompact(get("example")))
	}
	b.WriteString("Every chart also accepts: title, border, useColor.\n")
	return b.String()
}
