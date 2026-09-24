// Command asciicharts renders numeric data as a text chart: a JSON spec from a file, stdin or --json,
// or a CSV file straight away. It behaves as the Python reference's command line does: the same
// charts, the same error messages, the same exit codes (0 ok, 1 error, 2 bad usage).
package main

import (
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/boligolov/asciicharts/go/asciicharts"
)

const help = `asciicharts — render numeric data as ASCII/Unicode text charts.

Command line (JSON spec from a file, stdin, or --json):

    asciicharts spec.json
    echo '{"chartType":"sparkline","series":[{"values":[1,3,2]}]}' | asciicharts -
    asciicharts --json '{"chartType":"sparkline","series":[{"values":[1,3,2]}]}'
    asciicharts --list         # every chart type, how to fill ` + "`series`" + `, an example
    asciicharts --csv data.csv --chart hbar --sort -latency --limit 10 --set title="Slowest"
                               # straight from a CSV; see --csv --help
    asciicharts --version

Spec fields: chartType, series, labels, title, width, height, border, style, stacked, bins,
useColor, threshold, thresholds, showPoints, pointChar.
The rules behind every chart: asciicharts principles v` + asciicharts.PrinciplesVersion + `
(https://github.com/boligolov/asciicharts/blob/master/spec/principles.md).
`

func main() { os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr)) }

func run(argv []string, stdin io.Reader, stdout, stderr io.Writer) int {
	if len(argv) == 0 || argv[0] == "-h" || argv[0] == "--help" {
		fmt.Fprint(stdout, help+"\n")
		return 0
	}
	if argv[0] == "--version" {
		fmt.Fprintln(stdout, asciicharts.Version)
		return 0
	}
	for _, a := range argv {
		if a == "--csv" {
			return csvMain(argv, stdin, stdout, stderr)
		}
	}
	if argv[0] == "--list" {
		fmt.Fprint(stdout, asciicharts.ListText())
		return 0
	}
	out, err := renderSpec(argv, stdin)
	if err != nil {
		fmt.Fprintf(stderr, "error: %v\n", err)
		return 1
	}
	fmt.Fprintln(stdout, out)
	return 0
}

func renderSpec(argv []string, stdin io.Reader) (string, error) {
	var raw []byte
	var err error
	switch argv[0] {
	case "--json":
		if len(argv) < 2 {
			return "", &asciicharts.ChartError{Msg: "--json needs a JSON string argument"}
		}
		raw = []byte(argv[1])
	case "-":
		raw, err = io.ReadAll(stdin)
	default:
		raw, err = os.ReadFile(argv[0])
		raw = []byte(strings.TrimPrefix(string(raw), bom))
	}
	if err != nil {
		return "", err
	}
	spec, err := asciicharts.DecodeOrdered(raw)
	if err != nil {
		return "", &asciicharts.ChartError{Msg: "invalid JSON: " + err.Error()}
	}
	return asciicharts.Render(asciicharts.Plain(spec))
}

// --- --csv --------------------------------------------------------------------------------------

const csvUsage = `usage: asciicharts --csv [-h] --csv FILE [--chart TYPE] [--label COL] [--values COLS]
                      [--sort COL] [--limit N] [--set KEY=VALUE] [--print-spec]`

const csvHelp = csvUsage + `

Draw a chart straight from a CSV file (header row required).

options:
  -h, --help       show this help message and exit
  --csv FILE       CSV file, or - for stdin
  --chart TYPE     chart type: %s
  --label COL      column naming the rows/categories (x column for scatter); default: first text column
  --values COLS    comma-separated columns to plot; default: all numeric columns
  --sort COL       sort rows by this column: -COL or COL:desc for descending, COL:asc (default) for ascending
  --limit N        keep only the first N rows (after sorting)
  --set KEY=VALUE  any chart option, e.g. --set title=Latency --set border=none --set width=60 (repeatable)
  --print-spec     print the generated JSON spec instead of the chart

ExCSV files (starting with #!excsv) are read by the Python reference only, for now.
`

type csvArgs struct {
	csv, chart, chartName, label, values, sort string
	limit                                      *int
	set                                        []string
	listCharts, printSpec, help                bool
}

var csvFlags = []string{"--csv", "--chart", "--chart-name", "--list-charts", "--label", "--values", "--sort",
	"--limit", "--set", "--print-spec", "--help"}

type usageError string

func (e usageError) Error() string { return string(e) }

// parseCSVArgs reads the options as Python's argparse does: --name value or --name=value, a unique
// prefix of a name stands for it, a later option overrides an earlier one, and a value that starts
// with "-" after --sort/--label/--values belongs to that option ("--sort -p99").
func parseCSVArgs(argv []string) (*csvArgs, error) {
	a := &csvArgs{}
	haveCSV := false
	for i := 0; i < len(argv); i++ {
		arg := argv[i]
		if arg == "-h" {
			a.help = true
			continue
		}
		if !strings.HasPrefix(arg, "--") || arg == "--" {
			return nil, usageError("unrecognized arguments: " + arg)
		}
		name, value, hasValue := strings.Cut(arg, "=")
		flag := ""
		var candidates []string
		for _, f := range csvFlags {
			if f == name {
				candidates = []string{f}
				break
			}
			if strings.HasPrefix(f, name) {
				candidates = append(candidates, f)
			}
		}
		switch len(candidates) {
		case 0:
			return nil, usageError("unrecognized arguments: " + arg)
		case 1:
			flag = candidates[0]
		default:
			return nil, usageError(fmt.Sprintf("ambiguous option: %s could match %s", name, strings.Join(candidates, ", ")))
		}
		switch flag {
		case "--help", "--list-charts", "--print-spec":
			if hasValue {
				return nil, usageError(fmt.Sprintf("argument %s: ignored explicit argument '%s'", flag, value))
			}
			a.help = a.help || flag == "--help"
			a.listCharts = a.listCharts || flag == "--list-charts"
			a.printSpec = a.printSpec || flag == "--print-spec"
			continue
		}
		if !hasValue {
			next := ""
			if i+1 < len(argv) {
				next = argv[i+1]
			}
			glue := (flag == "--sort" || flag == "--label" || flag == "--values") && strings.HasPrefix(next, "-") &&
				!strings.HasPrefix(next, "--")
			if i+1 >= len(argv) || (strings.HasPrefix(next, "-") && next != "-" && !glue && !isNegativeNumber(next)) {
				return nil, usageError(fmt.Sprintf("argument %s: expected one argument", metavar(flag)))
			}
			value = next
			i++
		}
		switch flag {
		case "--csv":
			a.csv, haveCSV = value, true
		case "--chart":
			a.chart = value
		case "--chart-name":
			a.chartName = value
		case "--label":
			a.label = value
		case "--values":
			a.values = value
		case "--sort":
			a.sort = value
		case "--set":
			a.set = append(a.set, value)
		case "--limit":
			n, err := strconv.Atoi(strings.ReplaceAll(strings.TrimSpace(value), "_", ""))
			if err != nil {
				return nil, usageError(fmt.Sprintf("argument --limit: invalid int value: '%s'", value))
			}
			a.limit = &n
		}
	}
	if !a.help && !haveCSV {
		return nil, usageError("the following arguments are required: --csv")
	}
	return a, nil
}

func isNegativeNumber(s string) bool {
	_, err := strconv.ParseFloat(s, 64)
	return err == nil && strings.HasPrefix(s, "-")
}

func metavar(flag string) string {
	m := map[string]string{"--csv": "FILE", "--chart": "TYPE", "--chart-name": "NAME", "--label": "COL",
		"--values": "COLS", "--sort": "COL", "--limit": "N", "--set": "KEY=VALUE"}
	return flag + " " + m[flag]
}

func csvMain(argv []string, stdin io.Reader, stdout, stderr io.Writer) int {
	a, err := parseCSVArgs(argv)
	if err != nil {
		fmt.Fprintf(stderr, "%s\nasciicharts --csv: error: %v\n", csvUsage, err)
		return 2
	}
	if a.help {
		fmt.Fprintf(stdout, csvHelp, strings.Join(asciicharts.ChartTypes(), ", "))
		return 0
	}
	out, err := csvRender(a, stdin)
	if err != nil {
		fmt.Fprintf(stderr, "error: %v\n", err)
		return 1
	}
	fmt.Fprintln(stdout, out)
	return 0
}

func csvRender(a *csvArgs, stdin io.Reader) (string, error) {
	var raw []byte
	var err error
	if a.csv == "-" {
		raw, err = io.ReadAll(stdin)
		// Python reads stdin in text mode, which turns \r\n and \r into \n
		raw = []byte(strings.ReplaceAll(strings.ReplaceAll(string(raw), "\r\n", "\n"), "\r", "\n"))
	} else {
		raw, err = os.ReadFile(a.csv)
		raw = []byte(strings.TrimPrefix(string(raw), bom))
	}
	if err != nil {
		return "", err
	}
	text := string(raw)
	isExCSV := strings.HasPrefix(strings.TrimSuffix(strings.SplitN(strings.TrimLeft(text, bom), "\n", 2)[0], "\r"), "#!excsv")

	if a.listCharts {
		if !isExCSV {
			return "", errors.New("--list-charts needs an ExCSV file (starting with #!excsv); this looks like plain CSV")
		}
		return "", errExCSV
	}
	if a.chart != "" && a.chartName != "" {
		return "", errors.New("--chart and --chart-name are mutually exclusive: --chart builds a " +
			"chart from the data yourself, --chart-name uses one the file itself suggests")
	}
	if isExCSV {
		return "", errExCSV
	}
	if a.chart == "" {
		return "", errors.New("--chart TYPE is required (see --list) — or, for an ExCSV file " +
			"with its own #chart suggestion(s), --chart-name (see --list-charts)")
	}
	set, err := asciicharts.ParseSet(a.set)
	if err != nil {
		return "", err
	}
	spec, err := asciicharts.SpecFromCSV(text, a.chart, asciicharts.CSVOptions{
		Label: a.label, Values: a.values, Sort: a.sort, Limit: a.limit, Set: set})
	if err != nil {
		return "", err
	}
	if a.printSpec {
		return asciicharts.PyJSON(spec), nil
	}
	return asciicharts.Render(asciicharts.Plain(spec))
}

const bom = string(rune(0xFEFF))

var errExCSV = errors.New("this is an ExCSV file (#!excsv), which this build does not read yet; " +
	"use the Python reference (python asciicharts.py --csv ...), or strip the #-lines to read it as plain CSV")
