// Command asciicharts-mcp is the asciicharts MCP server: the tools list_charts and render_chart, over
// stdio (the default, for a client that launches its own process) or, when PORT is set, over
// stateless streamable HTTP at /mcp with a plain /healthz for container probes.
//
//	asciicharts-mcp                  # stdio
//	PORT=8080 asciicharts-mcp        # HTTP
//	asciicharts-mcp healthcheck      # exit 0/1 by probing its own /healthz
//
// The tools, their descriptions and JSON schemas are in tools.json, served as they are; the answers
// are pinned by testdata/ (recorded from the Python server this one replaced).
package main

import (
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"time"

	"github.com/boligolov/asciicharts/go/asciicharts"
	"github.com/google/jsonschema-go/jsonschema"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const defaultPort = "8080"

//go:embed tools.json
var toolsJSON []byte

type toolDef struct {
	Name         string          `json:"name"`
	Description  string          `json:"description"`
	InputSchema  json.RawMessage `json:"inputSchema"`
	OutputSchema json.RawMessage `json:"outputSchema"`
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "healthcheck" {
		os.Exit(healthcheck())
	}
	// stdio owns stdout for the protocol: logs go to stderr
	log.SetOutput(os.Stderr)
	log.SetFlags(0)
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	server := newServer()
	if port := os.Getenv("PORT"); port != "" {
		log.Printf("INFO asciicharts: serving MCP over HTTP at :%s/mcp", port)
		if err := serveHTTP(ctx, server, ":"+port); err != nil {
			log.Fatal(err)
		}
		return
	}
	if err := server.Run(ctx, &mcp.StdioTransport{}); err != nil && !errors.Is(err, context.Canceled) {
		log.Fatal(err)
	}
}

func serveHTTP(ctx context.Context, server *mcp.Server, addr string) error {
	mux := http.NewServeMux()
	// Stateless: the server never pushes anything to a client outside of answering a tool call.
	mux.Handle("/mcp", mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Stateless: true}))
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		fmt.Fprint(w, "ok")
	})
	srv := &http.Server{Addr: addr, Handler: mux, ReadHeaderTimeout: 10 * time.Second}
	go func() {
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		srv.Shutdown(shutdown)
	}()
	if err := srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

// healthcheck GETs our own /healthz: 0 if healthy, 1 if not (for a container healthcheck).
func healthcheck() int {
	port := os.Getenv("PORT")
	if port == "" {
		port = defaultPort
	}
	client := http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get("http://127.0.0.1:" + port + "/healthz")
	if err != nil {
		return 1
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return 1
	}
	return 0
}

func newServer() *mcp.Server {
	var defs []toolDef
	if err := json.Unmarshal(toolsJSON, &defs); err != nil {
		panic("asciicharts-mcp: bad tools.json: " + err.Error())
	}
	server := mcp.NewServer(&mcp.Implementation{Name: "asciicharts", Version: asciicharts.Version}, nil)
	for _, d := range defs {
		var schema jsonschema.Schema
		if err := json.Unmarshal(d.InputSchema, &schema); err != nil {
			panic("asciicharts-mcp: bad input schema of " + d.Name + ": " + err.Error())
		}
		resolved, err := schema.Resolve(nil)
		if err != nil {
			panic("asciicharts-mcp: input schema of " + d.Name + ": " + err.Error())
		}
		tool := &mcp.Tool{Name: d.Name, Description: d.Description, InputSchema: d.InputSchema, OutputSchema: d.OutputSchema}
		handle := renderChart
		if d.Name == "list_charts" {
			handle = listCharts
		}
		name := d.Name
		server.AddTool(tool, func(_ context.Context, req *mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			raw := []byte(req.Params.Arguments)
			if len(raw) == 0 || string(raw) == "null" {
				raw = []byte("{}")
			}
			var instance any
			if err := json.Unmarshal(raw, &instance); err != nil {
				return toolError(name, "invalid arguments: "+err.Error()), nil
			}
			if err := resolved.Validate(instance); err != nil {
				return toolError(name, "invalid arguments: "+err.Error()), nil
			}
			args, err := asciicharts.DecodeOrdered(raw)
			if err != nil {
				return toolError(name, "invalid arguments: "+err.Error()), nil
			}
			return handle(args.(*asciicharts.Object)), nil
		})
	}
	return server
}

// toolError is the answer when a tool fails (the Python server's wording, kept).
func toolError(tool, msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{IsError: true,
		Content: []mcp.Content{&mcp.TextContent{Text: "Error executing tool " + tool + ": " + msg}}}
}

func listCharts(*asciicharts.Object) *mcp.CallToolResult {
	catalog := asciicharts.Catalog()
	result := &mcp.CallToolResult{}
	items := make([]any, len(catalog))
	for i, c := range catalog {
		result.Content = append(result.Content, &mcp.TextContent{Text: asciicharts.PyJSONIndent(c, 2)})
		items[i] = c
	}
	out := asciicharts.NewObject()
	out.Set("result", items)
	result.StructuredContent = out
	return result
}

// renderChart builds the spec the way the Python server's typed arguments did: only the known fields,
// nulls dropped, numbers typed (values and thresholds are floats, width/height/bins integers written
// as integers), then renders it.
func renderChart(args *asciicharts.Object) *mcp.CallToolResult {
	spec := map[string]any{}
	for _, key := range []string{"chartType", "labels", "title", "border", "style", "stacked", "useColor",
		"showPoints", "pointChar"} {
		if v, ok := args.Get(key); ok && v != nil {
			spec[key] = v
		}
	}
	for _, key := range []string{"width", "height", "bins"} {
		if v, ok := args.Get(key); ok && v != nil {
			if n, isNum := v.(json.Number); isNum && strings.ContainsAny(string(n), ".eE") {
				return toolError("render_chart", "invalid arguments: "+key+" must be an integer, got "+string(n))
			}
			spec[key] = v
		}
	}
	if v, ok := args.Get("threshold"); ok && v != nil {
		spec["threshold"] = toFloat(v)
	}
	if v, ok := args.Get("thresholds"); ok && v != nil {
		var ts []any
		for _, t := range v.([]any) {
			o := t.(*asciicharts.Object)
			m := map[string]any{}
			if val, ok := o.Get("value"); ok {
				m["value"] = toFloat(val)
			}
			if label, ok := o.Get("label"); ok && label != nil {
				m["label"] = label
			}
			ts = append(ts, m)
		}
		spec["thresholds"] = orEmpty(ts)
	}
	var series []any
	if v, ok := args.Get("series"); ok && v != nil {
		for _, s := range v.([]any) {
			o := s.(*asciicharts.Object)
			m := map[string]any{}
			if name, ok := o.Get("name"); ok && name != nil {
				m["name"] = name
			}
			if values, ok := o.Get("values"); ok && values != nil {
				var fs []any
				for _, x := range values.([]any) {
					fs = append(fs, toFloat(x))
				}
				m["values"] = orEmpty(fs)
			}
			if points, ok := o.Get("points"); ok && points != nil {
				var ps []any
				for _, p := range points.([]any) {
					po := p.(*asciicharts.Object)
					x, _ := po.Get("x")
					y, _ := po.Get("y")
					ps = append(ps, map[string]any{"x": toFloat(x), "y": toFloat(y)})
				}
				m["points"] = orEmpty(ps)
			}
			series = append(series, m)
		}
	}
	spec["series"] = orEmpty(series)

	chart, err := asciicharts.Render(spec)
	if err != nil {
		return toolError("render_chart", err.Error())
	}
	out := asciicharts.NewObject()
	out.Set("result", chart)
	return &mcp.CallToolResult{Content: []mcp.Content{&mcp.TextContent{Text: chart}}, StructuredContent: out}
}

// toFloat makes a JSON number a float, as a Python float field holds it (1 becomes 1.0).
func toFloat(v any) any {
	if n, ok := v.(json.Number); ok {
		f, err := n.Float64()
		if err == nil || errors.Is(err, strconv.ErrRange) {
			return f
		}
	}
	return v
}

func orEmpty(xs []any) []any {
	if xs == nil {
		return []any{}
	}
	return xs
}
