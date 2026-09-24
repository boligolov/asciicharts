package asciicharts

import "testing"

func TestFloorLog10(t *testing.T) {
	// the expected values are Python's math.floor(math.log10(a))
	for a, want := range map[float64]int{0.09999999999999996: -2, 0.09999999999999999: -1, 0.1: -1, 0.5: -1,
		0.001: -3, 0.0009999999999999998: -3, 0.00099999999999999: -4, 1e-7: -7, 0.99999999999999: -1, 1: 0,
		0.049999999999999975: -2, 9.999999999999999e-06: -5, 9.99999999999999e-06: -5} {
		if got := floorLog10(a); got != want {
			t.Errorf("floorLog10(%v) = %d, want %d", a, got, want)
		}
	}
}
