package asciicharts

// Beyond conformance: no input makes the renderer panic, and every framed chart is rectangular
// (docs/spec/principles.md R1, R15).

import (
	"encoding/json"
	"errors"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The hostile specs of the MCP stress test (plus a few more): each must render or return a ChartError.
var hostile = []string{
	`{"chartType":"line"}`,
	`{"chartType":"donut","series":[{"values":[1,2]}]}`,
	`{"chartType":"line","series":[{"values":["1","2"]}]}`,
	`{"chartType":"line","series":[{"values":[true,false]}]}`,
	`{"chartType":"line","series":[{"values":[1,null,3]}]}`,
	`{"chartType":"line","width":-5,"series":[{"values":[1,2]}]}`,
	`{"chartType":"line","width":501,"series":[{"values":[1,2]}]}`,
	`{"chartType":"line","height":1000000000,"series":[{"values":[1,2]}]}`,
	`{"chartType":"line","width":2.5,"series":[{"values":[1,2]}]}`,
	`{"chartType":"line","series":{"values":[1,2]}}`,
	`{"chartType":"line","series":[{"values":[1e308,-1e308]}]}`,
	`{"chartType":"line","series":[{"values":[1e400,1]}]}`,
	`{"chartType":"line","series":[{"values":[123456789012345678901234567890,1]}]}`,
	`{"chartType":"line","width":123456789012345678901234567890,"series":[{"values":[1,2]}]}`,
	`{"chartType":"vbar","labels":["a","b"],"series":[{"values":[1e15,1e-15]}]}`,
	`{"chartType":"pie","series":[{"name":"a","values":[0]},{"name":"b","values":[0]}]}`,
	`{"chartType":"histogram","bins":500,"series":[{"values":[1,2,3]}]}`,
	`{"chartType":"boxplot","series":[{"name":"x","values":[7]}]}`,
	`{"chartType":"scatter","series":[{"name":"a"}]}`,
	`{"chartType":"heatmap","series":[{"name":"r1","values":[1,2]},{"name":"r2","values":[1]}]}`,
	`{"chartType":"vbar","labels":["a"],"series":[{"values":[1,2,3]}]}`,
	`{"chartType":"sparkline","series":[{"values":[3]}]}`,
	`{"chartType":"hbar","labels":["x"],"series":[` + strings.Repeat(`{"values":[1]},`, 100) + `{"values":[1]}]}`,
	`{"chartType":"line","title":"` + strings.Repeat("x", 10000) + `","series":[{"values":[1,2]}]}`,
	`{"chartType":"line","title":"\u001b[2J\n\t","series":[{"values":[1,2]}]}`,
	`{"chartType":"line","showPoints":true,"pointChar":"🔴","series":[{"values":[1,2]}]}`,
	`{"chartType":"line","thresholds":[{"value":2,"label":"a\nb"}],"series":[{"values":[1,3]}]}`,
	`{"chartType":"area","stacked":true,"series":[{"values":[0,0]},{"values":[-0,0]}]}`,
	`{"chartType":"vbar","stacked":true,"series":[{"values":[0,0]}]}`,
	`{"chartType":"hbar","stacked":true,"series":[{"values":[-1e15,1e15]}]}`,
	`{"chartType":"pie","width":1,"series":[{"values":[1]}]}`,
	`{"chartType":"pie","height":1,"series":[{"values":[1]},{"values":[1e15]}]}`,
	`{"chartType":"line","width":1,"height":1,"series":[{"values":[1,2]}]}`,
	`{"chartType":"area","width":1,"height":1,"series":[{"values":[1,-2]}]}`,
	`{"chartType":"dual_axis","width":1,"height":2,"series":[{"values":[1,2]},{"values":[3,-4]}]}`,
	`{"chartType":"heatmap","width":1,"labels":["a"],"series":[{"name":"r","values":[1]}]}`,
	`{"chartType":"dotplot","width":1,"series":[{"values":[1]},{"values":[2]}]}`,
	`{"chartType":"boxplot","width":1,"series":[{"values":[1,2]}]}`,
	`[1,2]`, `"text"`, `null`, `{`, ``,
}

func mustNotPanic(t *testing.T, spec []byte) (out string, err error) {
	t.Helper()
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("panic on %.200s: %v", spec, r)
		}
	}()
	return RenderJSON(spec)
}

func TestHostileSpecsNeverPanic(t *testing.T) {
	for _, spec := range hostile {
		_, err := mustNotPanic(t, []byte(spec))
		var ce *ChartError
		if err != nil && !errors.As(err, &ce) {
			t.Errorf("%.80s: error is not a ChartError: %v", spec, err)
		}
	}
}

func rectangular(out string) bool {
	lines := strings.Split(out, "\n")
	if len(lines) < 2 || !strings.ContainsAny(lines[0][:1], "┌╭╔┏+") {
		return true // not framed
	}
	w := visibleWidth(lines[0])
	for _, l := range lines[1:] {
		if visibleWidth(l) != w {
			return false
		}
	}
	return true
}

// TestRandomSpecsAreRectangularAndNeverPanic renders a thousand random specs — every chart type,
// style, border and option, with labels in several scripts — and checks R1 and R15.
func TestRandomSpecsAreRectangularAndNeverPanic(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	types := ChartTypes()
	styles := []string{"", "solid", "fine", "halftone", "ascii", "dotted"}
	bordersList := []string{"", "none", "ascii", "light", "heavy", "double", "rounded"}
	words := []string{"a", "Long label", "東京", "🍕", "été", "שלום", "x\ty", "ＡＢＣ", "", "Q1"}
	pick := func(xs []string) string { return xs[rng.Intn(len(xs))] }
	for i := 0; i < 1000; i++ {
		n := 1 + rng.Intn(8)
		nSeries := 1 + rng.Intn(4)
		spec := map[string]any{"chartType": pick(types), "style": pick(styles), "border": pick(bordersList)}
		if rng.Intn(2) == 0 {
			spec["title"] = pick(words) + " " + pick(words)
		}
		if rng.Intn(2) == 0 {
			spec["width"] = 1 + rng.Intn(80)
		}
		if rng.Intn(2) == 0 {
			spec["height"] = 1 + rng.Intn(20)
		}
		for _, k := range []string{"stacked", "showPoints"} {
			if rng.Intn(3) == 0 {
				spec[k] = true
			}
		}
		if rng.Intn(4) == 0 {
			spec["useColor"] = "on"
		}
		if rng.Intn(4) == 0 {
			spec["thresholds"] = []any{map[string]any{"value": rng.NormFloat64() * 50, "label": pick(words)}}
		}
		labels := make([]any, n)
		for j := range labels {
			labels[j] = pick(words) + fmt.Sprint(j)
		}
		if rng.Intn(3) > 0 {
			spec["labels"] = labels
		}
		var ss []any
		for s := 0; s < nSeries; s++ {
			vals := make([]any, n)
			pts := make([]any, n)
			for j := range vals {
				v := rng.NormFloat64() * 100
				if rng.Intn(10) == 0 {
					v = 0
				}
				vals[j] = v
				pts[j] = map[string]any{"x": rng.NormFloat64(), "y": rng.NormFloat64()}
			}
			ss = append(ss, map[string]any{"name": pick(words), "values": vals, "points": pts})
		}
		spec["series"] = ss
		data, _ := json.Marshal(spec)
		out, err := mustNotPanic(t, data)
		if err == nil && !rectangular(out) {
			t.Errorf("not rectangular: %s\n%s", data, out)
		}
	}
}

func FuzzRenderJSON(f *testing.F) {
	for _, spec := range hostile {
		f.Add([]byte(spec))
	}
	data, err := os.ReadFile(filepath.Join(conformanceDir, "curated.json"))
	if err == nil {
		var curated []map[string]json.RawMessage
		if json.Unmarshal(data, &curated) == nil {
			for _, c := range curated {
				f.Add([]byte(c["spec"]))
			}
		}
	}
	f.Fuzz(func(t *testing.T, spec []byte) {
		out, err := mustNotPanic(t, spec)
		if err == nil && !rectangular(out) {
			t.Errorf("not rectangular: %s", spec)
		}
	})
}
