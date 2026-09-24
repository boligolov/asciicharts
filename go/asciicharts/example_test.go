package asciicharts_test

import (
	"fmt"

	"github.com/boligolov/asciicharts/go/asciicharts"
)

func ExampleRenderJSON() {
	out, err := asciicharts.RenderJSON([]byte(`{"chartType":"hbar","labels":["Chrome","Firefox","Safari"],"series":[{"values":[62,21,12]}]}`))
	if err != nil {
		panic(err)
	}
	fmt.Println(out)
	// Output:
	// ┌───────────────────────────────────────────────────────┐
	// │ Chrome  │ ████████████████████████████████████████ 62 │
	// │ Firefox │ ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░ 21 │
	// │ Safari  │ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 12 │
	// └───────────────────────────────────────────────────────┘
}
