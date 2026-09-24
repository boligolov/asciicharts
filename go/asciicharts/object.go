package asciicharts

// Object is a JSON object that keeps its keys in order, as Python's dicts do. Specs built from a CSV
// file and values given on the command line are Objects, so --print-spec writes them exactly as the
// Python reference does.

import (
	"bytes"
	"encoding/json"
	"io"
	"strconv"
	"strings"
)

// Object is an ordered JSON object.
type Object struct {
	keys []string
	vals map[string]any
}

// NewObject returns an empty Object.
func NewObject() *Object { return &Object{vals: map[string]any{}} }

// Set sets a key, keeping its position if it already exists.
func (o *Object) Set(key string, v any) {
	if _, ok := o.vals[key]; !ok {
		o.keys = append(o.keys, key)
	}
	o.vals[key] = v
}

// Get returns the value of a key.
func (o *Object) Get(key string) (any, bool) {
	v, ok := o.vals[key]
	return v, ok
}

// Keys returns the keys in order.
func (o *Object) Keys() []string { return append([]string(nil), o.keys...) }

// Plain converts a value holding Objects into plain maps, for Render.
func Plain(v any) any {
	switch x := v.(type) {
	case *Object:
		m := make(map[string]any, len(x.keys))
		for _, k := range x.keys {
			m[k] = Plain(x.vals[k])
		}
		return m
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = Plain(e)
		}
		return out
	}
	return v
}

// DecodeOrdered parses one JSON value, keeping object key order and number literals (json.Number).
// It fails if anything but whitespace follows the value, like Python's json.loads.
func DecodeOrdered(data []byte) (any, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	v, err := decodeValue(dec)
	if err != nil {
		return nil, err
	}
	if _, err := dec.Token(); err != io.EOF {
		return nil, errorf("extra data after the JSON value")
	}
	return v, nil
}

func decodeValue(dec *json.Decoder) (any, error) {
	tok, err := dec.Token()
	if err != nil {
		return nil, err
	}
	switch t := tok.(type) {
	case json.Delim:
		switch t {
		case '{':
			o := NewObject()
			for dec.More() {
				kt, err := dec.Token()
				if err != nil {
					return nil, err
				}
				v, err := decodeValue(dec)
				if err != nil {
					return nil, err
				}
				o.Set(kt.(string), v)
			}
			_, err := dec.Token() // }
			return o, err
		case '[':
			list := []any{}
			for dec.More() {
				v, err := decodeValue(dec)
				if err != nil {
					return nil, err
				}
				list = append(list, v)
			}
			_, err := dec.Token() // ]
			return list, err
		}
	}
	return tok, nil
}

// PyJSON writes a value as Python's json.dumps(v, ensure_ascii=False) does: ", " and ": "
// separators, floats in repr form (480.0), only the escapes JSON requires.
func PyJSON(v any) string {
	var b strings.Builder
	writePyJSON(&b, v, ", ", ": ")
	return b.String()
}

// PyJSONCompact is PyJSON with separators=(",", ":").
func PyJSONCompact(v any) string {
	var b strings.Builder
	writePyJSON(&b, v, ",", ":")
	return b.String()
}

func writePyJSON(b *strings.Builder, v any, itemSep, keySep string) {
	switch x := v.(type) {
	case nil:
		b.WriteString("null")
	case bool:
		if x {
			b.WriteString("true")
		} else {
			b.WriteString("false")
		}
	case string:
		b.WriteString(jsonString(x))
	case json.Number:
		if isIntLiteral(string(x)) {
			b.WriteString(pyRepr(x))
		} else {
			f, _ := strconv.ParseFloat(string(x), 64)
			writePyFloat(b, f)
		}
	case float64:
		writePyFloat(b, x)
	case int:
		b.WriteString(strconv.Itoa(x))
	case []any:
		b.WriteByte('[')
		for i, e := range x {
			if i > 0 {
				b.WriteString(itemSep)
			}
			writePyJSON(b, e, itemSep, keySep)
		}
		b.WriteByte(']')
	case *Object:
		b.WriteByte('{')
		for i, k := range x.keys {
			if i > 0 {
				b.WriteString(itemSep)
			}
			b.WriteString(jsonString(k))
			b.WriteString(keySep)
			writePyJSON(b, x.vals[k], itemSep, keySep)
		}
		b.WriteByte('}')
	case map[string]any:
		o := NewObject()
		for _, k := range orderedKeys(x) {
			o.Set(k, x[k])
		}
		writePyJSON(b, o, itemSep, keySep)
	default:
		b.WriteString("null")
	}
}

func writePyFloat(b *strings.Builder, f float64) {
	switch s := pyFloatRepr(f); s {
	case "inf":
		b.WriteString("Infinity")
	case "-inf":
		b.WriteString("-Infinity")
	case "nan":
		b.WriteString("NaN")
	default:
		b.WriteString(s)
	}
}

// MarshalJSON writes the object with its keys in order.
func (o *Object) MarshalJSON() ([]byte, error) {
	return []byte(PyJSONCompact(o)), nil
}

// PyJSONIndent is json.dumps(v, ensure_ascii=False, indent=indent): one item per line, "[]" and "{}"
// for empty containers.
func PyJSONIndent(v any, indent int) string {
	var b strings.Builder
	writePyJSONIndent(&b, v, strings.Repeat(" ", indent), "\n")
	return b.String()
}

func writePyJSONIndent(b *strings.Builder, v any, step, nl string) {
	inner := nl + step
	switch x := v.(type) {
	case []any:
		if len(x) == 0 {
			b.WriteString("[]")
			return
		}
		b.WriteByte('[')
		for i, e := range x {
			if i > 0 {
				b.WriteByte(',')
			}
			b.WriteString(inner)
			writePyJSONIndent(b, e, step, inner)
		}
		b.WriteString(nl + "]")
	case *Object:
		if len(x.keys) == 0 {
			b.WriteString("{}")
			return
		}
		b.WriteByte('{')
		for i, k := range x.keys {
			if i > 0 {
				b.WriteByte(',')
			}
			b.WriteString(inner + jsonString(k) + ": ")
			writePyJSONIndent(b, x.vals[k], step, inner)
		}
		b.WriteString(nl + "}")
	default:
		writePyJSON(b, v, ", ", ": ")
	}
}

// Catalog returns the chart catalogue as ordered objects (type, summary, series, options, example),
// the keys and examples in the order the Python reference lists them.
func Catalog() []*Object {
	all, err := DecodeOrdered([]byte(catalogJSON))
	if err != nil {
		panic("asciicharts: bad generated catalogue: " + err.Error())
	}
	var out []*Object
	for _, c := range all.([]any) {
		out = append(out, c.(*Object))
	}
	return out
}
