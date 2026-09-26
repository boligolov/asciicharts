package main

// Parity with the Python command line is checked by test/parity/cli_parity.py; these tests pin the exit
// codes and the paths through run.

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/boligolov/asciicharts/go/asciicharts"
)

func runCLI(t *testing.T, stdin string, args ...string) (int, string, string) {
	t.Helper()
	var out, errOut bytes.Buffer
	code := run(args, strings.NewReader(stdin), &out, &errOut)
	return code, out.String(), errOut.String()
}

func TestRun(t *testing.T) {
	dir := t.TempDir()
	csvPath := filepath.Join(dir, "latency.csv")
	os.WriteFile(csvPath, []byte("service,p50_ms,p99_ms\napi,12,80\nauth,8,35\nsearch,25,140\n"), 0o644)
	excsvPath := filepath.Join(dir, "data.csv")
	os.WriteFile(excsvPath, []byte("#!excsv v=0.5\na,b\nx,1\n"), 0o644)
	spec := `{"chartType":"sparkline","series":[{"values":[1,3,2]}],"border":"none"}`
	chart, _ := asciicharts.RenderJSON([]byte(spec))

	for _, c := range []struct {
		name, stdin string
		args        []string
		code        int
		out, err    string // substrings
	}{
		{"version", "", []string{"--version"}, 0, asciicharts.Version + "\n", ""},
		{"help", "", nil, 0, "asciicharts --list", ""},
		{"list", "", []string{"--list"}, 0, "Every chart also accepts: title, border, useColor.\n", ""},
		{"json", "", []string{"--json", spec}, 0, chart + "\n", ""},
		{"stdin", spec, []string{"-"}, 0, chart + "\n", ""},
		{"stdin bom", "\ufeff" + spec, []string{"-"}, 0, chart + "\n", ""},
		{"csv stdin bom", "\ufeffa,b\nx,1\n", []string{"--csv", "-", "--chart", "vbar", "--print-spec"}, 0, `"labels": ["x"]`, ""},
		{"json missing", "", []string{"--json"}, 1, "", "error: --json needs a JSON string argument\n"},
		{"invalid json", "", []string{"--json", "{"}, 1, "", "error: invalid JSON: "},
		{"trailing data", "", []string{"--json", spec + " x"}, 1, "", "error: invalid JSON: "},
		{"chart error", "", []string{"--json", `{"chartType":"nope","series":[{"values":[1]}]}`}, 1, "", `error: unknown chartType "nope"`},
		{"csv", "", []string{"--csv", csvPath, "--chart", "hbar", "--sort", "-p99", "--limit", "1", "--print-spec"}, 0,
			`{"chartType": "hbar", "labels": ["search"], "series": [{"name": "p50_ms", "values": [25.0]}, {"name": "p99_ms", "values": [140.0]}]}` + "\n", ""},
		{"csv abbreviated option", "", []string{"--csv", csvPath, "--chart", "hbar", "--val", "p99", "--print"}, 0, `"name": "p99_ms"`, ""},
		{"csv stdin", "a,b\nx,1\ny,2\n", []string{"--csv", "-", "--chart", "vbar", "--print-spec"}, 0, `"labels": ["x", "y"]`, ""},
		{"csv no chart", "", []string{"--csv", csvPath}, 1, "", "error: --chart TYPE is required"},
		{"csv usage", "", []string{"--csv", csvPath, "--chart", "hbar", "--bogus"}, 2, "", "unrecognized arguments: --bogus"},
		{"csv ambiguous", "", []string{"--csv", csvPath, "--cha", "hbar"}, 2, "", "ambiguous option: --cha"},
		{"csv limit", "", []string{"--csv", csvPath, "--chart", "hbar", "--limit", "x"}, 2, "", "invalid int value: 'x'"},
		{"excsv", "", []string{"--csv", excsvPath, "--chart", "hbar"}, 1, "", "ExCSV"},
	} {
		code, out, errOut := runCLI(t, c.stdin, c.args...)
		if code != c.code || !strings.Contains(out, c.out) || !strings.Contains(errOut, c.err) {
			t.Errorf("%s: exit %d\nstdout %q\nstderr %q", c.name, code, out, errOut)
		}
	}
}
