package asciicharts

// The primitives whose exact behaviour the conformance suite pins down: rounding, number
// formatting, min/max, and the text of error messages. They follow the Python reference
// implementation to the byte (see spec/principles.md §4.1, §4.13, §14).

import (
	"encoding/json"
	"math"
	"math/big"
	"sort"
	"strconv"
	"strings"
)

// floorLog10 is floor(log10(a)) for a > 0 as Python computes it, from a correctly rounded log10. Go's
// math.Log10 is off by an ulp at times, which matters only next to a power of ten: Python's log10 of
// 0.09999999999999996 is -1.0000000000000002 (floor -2), Go's is -1. There the logarithm is rebuilt
// from the exact distance to the power of ten and rounded once.
func floorLog10(a float64) int {
	l := math.Log10(a)
	k := math.Round(l)
	if math.Abs(l-k) > 1e-9 || math.Abs(k) > 300 {
		return int(math.Floor(l))
	}
	// log10(a) = k + log10(1+d) with d = a/10^k - 1, tiny here: log10(1+d) = d/ln10 to double precision.
	p := new(big.Float).SetPrec(2048).SetInt(new(big.Int).Exp(big.NewInt(10), big.NewInt(int64(math.Abs(k))), nil))
	x := new(big.Float).SetPrec(2048).SetFloat64(a)
	if k < 0 {
		x.Mul(x, p)
	} else {
		x.Quo(x, p)
	}
	d, _ := x.Sub(x, big.NewFloat(1)).Float64()
	return int(math.Floor(k + d/math.Ln10))
}

// round rounds half away from zero (not to even).
func round(x float64) int {
	t := math.Trunc(x)
	if math.Abs(x-t) >= 0.5 {
		if x > 0 {
			t++
		} else {
			t--
		}
	}
	return int(t)
}

// fmtValue prints a value: integers without decimals, from 1 up with two decimals, below 1 with two
// significant digits (below 1e-7 in exponent form); never a negative zero.
func fmtValue(v float64) string {
	if math.Abs(v-math.Trunc(v)) < 1e-9 {
		s := strconv.FormatFloat(v, 'f', 0, 64)
		if math.Abs(v) < 1 {
			s = strings.ReplaceAll(s, "-0", "0")
		}
		return s
	}
	if math.Abs(v) >= 1 {
		return strconv.FormatFloat(v, 'f', 2, 64)
	}
	digits := 1 - floorLog10(math.Abs(v))
	if digits < 2 {
		digits = 2
	}
	if digits <= 8 {
		return strconv.FormatFloat(v, 'f', digits, 64)
	}
	return pyFormatG(v, 2)
}

// pyFormatG is Python's format(v, ".<prec>g").
func pyFormatG(v float64, prec int) string {
	if prec == 0 {
		prec = 1
	}
	if v == 0 {
		if math.Signbit(v) {
			return "-0"
		}
		return "0"
	}
	e := strconv.FormatFloat(v, 'e', prec-1, 64) // d.ddde±XX, correctly rounded
	mant, expStr, _ := strings.Cut(e, "e")
	exp, _ := strconv.Atoi(expStr)
	if exp < -4 || exp >= prec {
		mant = trimFraction(mant)
		sign := "+"
		if exp < 0 {
			sign, exp = "-", -exp
		}
		return mant + "e" + sign + pad2(exp)
	}
	return trimFraction(strconv.FormatFloat(v, 'f', prec-1-exp, 64))
}

func trimFraction(s string) string {
	if strings.Contains(s, ".") {
		s = strings.TrimRight(s, "0")
		s = strings.TrimSuffix(s, ".")
	}
	return s
}

func pad2(n int) string {
	if n < 10 {
		return "0" + strconv.Itoa(n)
	}
	return strconv.Itoa(n)
}

// roundSig12 is float(f"{x:.12g}"): 12 significant digits, dropping the float noise of arithmetic.
func roundSig12(x float64) float64 {
	v, _ := strconv.ParseFloat(strconv.FormatFloat(x, 'g', 12, 64), 64)
	return v
}

// pyFloatRepr is Python's repr(float): the shortest round-tripping digits, in fixed notation from
// 1e-4 up to (but excluding) 1e16, with at least one decimal; otherwise d.ddde±XX.
func pyFloatRepr(v float64) string {
	switch {
	case math.IsInf(v, 1):
		return "inf"
	case math.IsInf(v, -1):
		return "-inf"
	case math.IsNaN(v):
		return "nan"
	case v == 0:
		if math.Signbit(v) {
			return "-0.0"
		}
		return "0.0"
	}
	e := strconv.FormatFloat(v, 'e', -1, 64)
	mant, expStr, _ := strings.Cut(e, "e")
	exp, _ := strconv.Atoi(expStr)
	if exp < -4 || exp >= 16 {
		sign := "+"
		if exp < 0 {
			sign, exp = "-", -exp
		}
		return mant + "e" + sign + pad2(exp)
	}
	s := strconv.FormatFloat(v, 'f', -1, 64)
	if !strings.Contains(s, ".") {
		s += ".0"
	}
	return s
}

// pyMin and pyMax are Python's min(a, b) and max(a, b): the first argument unless the second is
// strictly smaller (larger) — which matters for -0.0 against 0.0.
func pyMin(a, b float64) float64 {
	if b < a {
		return b
	}
	return a
}

func pyMax(a, b float64) float64 {
	if b > a {
		return b
	}
	return a
}

func minInt(a, b int) int {
	if b < a {
		return b
	}
	return a
}

func maxInt(a, b int) int {
	if b > a {
		return b
	}
	return a
}

func clamp(v, lo, hi int) int {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

// floorDiv is Python's // on ints.
func floorDiv(a, b int) int {
	q := a / b
	if (a%b != 0) && ((a < 0) != (b < 0)) {
		q--
	}
	return q
}

// pyMod1 is Python's x % 1.0: the result takes the sign of the divisor.
func pyMod1(x float64) float64 {
	m := math.Mod(x, 1)
	if m < 0 {
		m++
	}
	return m
}

// sum adds left to right.
func sum(xs []float64) float64 {
	t := 0.0
	for _, x := range xs {
		t += x
	}
	return t
}

func sumInts(xs []int) int {
	t := 0
	for _, x := range xs {
		t += x
	}
	return t
}

// repeat is Python's s * n: empty for n <= 0.
func repeat(s string, n int) string {
	if n <= 0 {
		return ""
	}
	return strings.Repeat(s, n)
}

// stableOrderByDescending returns the indexes 0..n-1 sorted by key descending, ties in index order
// (Python's sorted(range(n), key=lambda i: -key[i])).
func stableOrderByDescending(key []float64) []int {
	order := make([]int, len(key))
	for i := range order {
		order[i] = i
	}
	sort.SliceStable(order, func(a, b int) bool { return -key[order[a]] < -key[order[b]] })
	return order
}

// --- the text of error messages ----------------------------------------------------------------

// quote is Python's json.dumps(str(v), ensure_ascii=False): the Python str() of a JSON value, as a
// JSON string literal.
func quote(v any) string {
	return jsonString(pyStr(v))
}

// jsonString writes s as Python's json.dumps does with ensure_ascii=False: only ", \ and control
// characters are escaped; nothing else (Go's encoder also escapes <, >, &, U+2028 and U+2029).
func jsonString(s string) string {
	var b strings.Builder
	b.WriteByte('"')
	for _, r := range s {
		switch r {
		case '"':
			b.WriteString(`\"`)
		case '\\':
			b.WriteString(`\\`)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		case '\b':
			b.WriteString(`\b`)
		case '\f':
			b.WriteString(`\f`)
		default:
			if r < 0x20 {
				b.WriteString(`\u00`)
				b.WriteString(strconv.FormatInt(int64(r)>>4, 16))
				b.WriteString(strconv.FormatInt(int64(r)&15, 16))
			} else {
				b.WriteRune(r)
			}
		}
	}
	b.WriteByte('"')
	return b.String()
}

// pyStr is Python's str() of a value decoded from JSON.
func pyStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return pyRepr(v)
}

// pyRepr is Python's repr() of a value decoded from JSON.
func pyRepr(v any) string {
	switch x := v.(type) {
	case nil:
		return "None"
	case bool:
		if x {
			return "True"
		}
		return "False"
	case string:
		return pyStringRepr(x)
	case json.Number:
		if isIntLiteral(string(x)) {
			n, ok := new(big.Int).SetString(string(x), 10)
			if ok {
				return n.String()
			}
		}
		f, _ := strconv.ParseFloat(string(x), 64)
		return pyFloatRepr(f)
	case float64:
		return pyFloatRepr(x)
	case int:
		return strconv.Itoa(x)
	case []any:
		parts := make([]string, len(x))
		for i, e := range x {
			parts[i] = pyRepr(e)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case map[string]any:
		keys := orderedKeys(x)
		parts := make([]string, len(keys))
		for i, k := range keys {
			parts[i] = pyStringRepr(k) + ": " + pyRepr(x[k])
		}
		return "{" + strings.Join(parts, ", ") + "}"
	}
	return "?"
}

// orderedKeys returns a map's keys sorted — Go maps don't keep JSON order, so a repr of an object is
// the one place the Go output may list keys differently from Python.
func orderedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// pyStringRepr is Python's repr() of a str: single quotes unless the text holds a single quote and
// no double quote.
func pyStringRepr(s string) string {
	q := byte('\'')
	if strings.Contains(s, "'") && !strings.Contains(s, `"`) {
		q = '"'
	}
	var b strings.Builder
	b.WriteByte(q)
	for _, r := range s {
		switch {
		case r == rune(q) || r == '\\':
			b.WriteByte('\\')
			b.WriteRune(r)
		case r == '\n':
			b.WriteString(`\n`)
		case r == '\r':
			b.WriteString(`\r`)
		case r == '\t':
			b.WriteString(`\t`)
		case r < 0x20 || r == 0x7F:
			b.WriteString(`\x`)
			b.WriteString(strconv.FormatInt(int64(r)>>4, 16))
			b.WriteString(strconv.FormatInt(int64(r)&15, 16))
		default:
			b.WriteRune(r)
		}
	}
	b.WriteByte(q)
	return b.String()
}

func isIntLiteral(s string) bool {
	return !strings.ContainsAny(s, ".eE")
}
