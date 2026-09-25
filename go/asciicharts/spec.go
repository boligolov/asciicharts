package asciicharts

// Validating a JSON-shaped spec and turning it into the input the renderers use
// (docs/spec/principles.md §9). The checks run in the same order, with the same messages, as the Python
// reference implementation, so both reject an invalid spec with the same words.

import (
	"encoding/json"
	"fmt"
	"math"
	"math/big"
	"strconv"
	"unicode/utf8"
)

// Limits on a single request (docs/spec/principles.md §9.2).
const (
	MaxWidth          = 500
	MaxHeight         = 200
	MaxBins           = 500
	MaxSeries         = 100
	MaxThresholds     = 20
	MaxThresholdLabel = 40
	MaxValues         = 50_000 // values + points across all series
	MaxMagnitude      = 1e15
	maxText           = 200 // title, labels, series names: characters
)

// ChartError is returned for a spec that can't be rendered; its message is one line that says what
// to fix.
type ChartError struct{ Msg string }

func (e *ChartError) Error() string { return e.Msg }

func errorf(format string, args ...any) error {
	return &ChartError{Msg: fmt.Sprintf(format, args...)}
}

type series struct {
	name   string
	values []float64
	points [][2]float64
}

type threshold struct {
	value float64
	label string
}

type input struct {
	chartType  string
	series     []series
	labels     []string
	title      string
	width      int
	height     int
	border     string
	style      string
	stacked    bool
	bins       int
	color      bool
	useColor   string
	threshold  *float64
	thresholds []threshold
	showPoints bool
	pointChar  string
}

// number reads a JSON number (json.Number, float64 or int); ok is false for anything else,
// booleans included.
func number(v any) (f float64, isInt bool, ok bool) {
	switch x := v.(type) {
	case json.Number:
		f, err := strconv.ParseFloat(string(x), 64)
		if err != nil && !math.IsInf(f, 0) {
			return 0, false, false
		}
		return f, isIntLiteral(string(x)), true
	case float64:
		return x, false, true
	case float32:
		return float64(x), false, true
	case int:
		return float64(x), true, true
	case int64:
		return float64(x), true, true
	}
	return 0, false, false
}

func num(v any, where string) (float64, error) {
	f, _, ok := number(v)
	if !ok {
		return 0, errorf("%s must be a number, got %s", where, quote(v))
	}
	if math.IsInf(f, 0) || math.IsNaN(f) {
		return 0, errorf("%s must be a finite number, got %s", where, pyStr(v))
	}
	if math.Abs(f) > MaxMagnitude {
		return 0, errorf("%s must be at most 1e15 in magnitude, got %s", where, pyFormatG(f, 6))
	}
	return f, nil
}

// intOption is an optional non-negative integer option; absent or 0 means "use the default".
func intOption(spec map[string]any, key string, limit int) (int, error) {
	v, present := spec[key]
	if !present || v == nil {
		return 0, nil
	}
	f, isInt, ok := number(v)
	if !ok || (!isInt && (f != math.Trunc(f) || math.IsInf(f, 0))) {
		return 0, errorf("%s must be an integer, got %s", key, quote(v))
	}
	var n *big.Int
	if lit, isNum := v.(json.Number); isNum && isInt {
		n, _ = new(big.Int).SetString(string(lit), 10)
	}
	if n == nil {
		n, _ = new(big.Float).SetFloat64(f).Int(nil)
	}
	if n.Cmp(big.NewInt(int64(limit))) > 0 {
		return 0, errorf("%s must be at most %d, got %s", key, limit, n.String())
	}
	if n.Sign() < 0 {
		return 0, nil
	}
	return int(n.Int64()), nil
}

func text(spec map[string]any, key string) (string, error) {
	v, present := spec[key]
	if !present || v == nil {
		return "", nil
	}
	s, ok := v.(string)
	if !ok {
		return "", errorf("%s must be a string, got %s", key, quote(v))
	}
	return clean(s, key)
}

// truthy is Python's bool() of a JSON value.
func truthy(v any) bool {
	switch x := v.(type) {
	case nil:
		return false
	case bool:
		return x
	case string:
		return x != ""
	case []any:
		return len(x) > 0
	case map[string]any:
		return len(x) > 0
	}
	f, _, ok := number(v)
	return !ok || f != 0
}

// orEmpty is Python's `v or []`.
func orEmpty(v any) any {
	if !truthy(v) {
		return []any{}
	}
	return v
}

func parseThresholds(raw any) ([]threshold, error) {
	if raw == nil {
		return nil, nil
	}
	list, ok := raw.([]any)
	if !ok {
		return nil, errorf("thresholds must be an array of numbers or {value, label} objects")
	}
	if len(list) > MaxThresholds {
		return nil, errorf("thresholds must have at most %d entries, got %d", MaxThresholds, len(list))
	}
	var out []threshold
	for i, t := range list {
		obj, isObj := t.(map[string]any)
		if !isObj {
			v, err := num(t, fmt.Sprintf("thresholds %d", i))
			if err != nil {
				return nil, err
			}
			out = append(out, threshold{value: v})
			continue
		}
		label, err := text(obj, "label")
		if err != nil {
			return nil, err
		}
		if n := utf8.RuneCountInString(label); n > MaxThresholdLabel {
			return nil, errorf("thresholds %d: label must be at most %d characters, got %d", i, MaxThresholdLabel, n)
		}
		v, err := num(obj["value"], fmt.Sprintf("thresholds %d value", i))
		if err != nil {
			return nil, err
		}
		out = append(out, threshold{value: v, label: label})
	}
	return out, nil
}

func pointChar(spec map[string]any) (string, error) {
	s, err := text(spec, "pointChar")
	if err != nil {
		return "", err
	}
	ch := firstRune(s)
	if ch != "" {
		r, _ := utf8.DecodeRuneInString(ch)
		if charWidth(r) != 1 {
			return "", errorf("pointChar must be a single-width character, got %s (wide characters such as emoji "+
				"take two columns)", quote(ch))
		}
	}
	return ch, nil
}

func normalize(raw any) (*input, error) {
	spec, ok := raw.(map[string]any)
	if !ok {
		return nil, errorf("chart spec must be a JSON object")
	}
	rawSeries := spec["series"]
	if rawSeries == nil {
		rawSeries = []any{}
	}
	list, ok := rawSeries.([]any)
	if !ok {
		return nil, errorf("series must be an array")
	}
	if len(list) > MaxSeries {
		return nil, errorf("series must have at most %d entries, got %d", MaxSeries, len(list))
	}

	in := &input{}
	total := 0
	for i, s := range list {
		obj, ok := s.(map[string]any)
		if !ok {
			return nil, errorf("series %d must be an object", i)
		}
		values, vOK := orEmpty(obj["values"]).([]any)
		points, pOK := orEmpty(obj["points"]).([]any)
		if !vOK || !pOK {
			return nil, errorf("series %d: values and points must be arrays", i)
		}
		total += len(values) + len(points)
		if total > MaxValues {
			return nil, errorf("too much data: at most %d values/points in total", MaxValues)
		}
		var pts [][2]float64
		for _, p := range points {
			po, ok := p.(map[string]any)
			if !ok {
				return nil, errorf("series %d points must be {x, y} objects", i)
			}
			x, err := num(po["x"], fmt.Sprintf("series %d point x", i))
			if err != nil {
				return nil, err
			}
			y, err := num(po["y"], fmt.Sprintf("series %d point y", i))
			if err != nil {
				return nil, err
			}
			pts = append(pts, [2]float64{x, y})
		}
		name, err := text(obj, "name")
		if err != nil {
			return nil, err
		}
		vals := make([]float64, 0, len(values))
		for _, v := range values {
			f, err := num(v, fmt.Sprintf("series %d value", i))
			if err != nil {
				return nil, err
			}
			vals = append(vals, f)
		}
		in.series = append(in.series, series{name: name, values: vals, points: pts})
	}

	labels, ok := orEmpty(spec["labels"]).([]any)
	if !ok {
		return nil, errorf("labels must be an array of strings")
	}
	useColor, err := text(spec, "useColor")
	if err != nil {
		return nil, err
	}

	if in.chartType, err = text(spec, "chartType"); err != nil {
		return nil, err
	}
	for i, l := range labels {
		s, err := clean(pyStr(l), fmt.Sprintf("labels %d", i))
		if err != nil {
			return nil, err
		}
		in.labels = append(in.labels, s)
	}
	if in.title, err = text(spec, "title"); err != nil {
		return nil, err
	}
	if in.width, err = intOption(spec, "width", MaxWidth); err != nil {
		return nil, err
	}
	if in.height, err = intOption(spec, "height", MaxHeight); err != nil {
		return nil, err
	}
	if in.border, err = text(spec, "border"); err != nil {
		return nil, err
	}
	if in.style, err = text(spec, "style"); err != nil {
		return nil, err
	}
	in.stacked = truthy(spec["stacked"])
	if in.bins, err = intOption(spec, "bins", MaxBins); err != nil {
		return nil, err
	}
	in.color = useColor == "on"
	in.useColor = useColor
	if t, present := spec["threshold"]; present && t != nil {
		v, err := num(t, "threshold")
		if err != nil {
			return nil, err
		}
		in.threshold = &v
	}
	if in.thresholds, err = parseThresholds(spec["thresholds"]); err != nil {
		return nil, err
	}
	in.showPoints = truthy(spec["showPoints"])
	if in.pointChar, err = pointChar(spec); err != nil {
		return nil, err
	}
	return in, nil
}
