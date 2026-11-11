package fixture

import (
	"testing"
	"example.com/method-values/remote"
)

func TestCallbacks(t *testing.T) {
	jobs := 0
	s := &Store{Job: func() { jobs++ }}
	Run(s)
	PackageControl()
	FieldControl(s)
	if s.Saved != 1 || remote.Saved != 1 || jobs != 1 {
		t.Fatalf("callbacks: %d %d %d", s.Saved, remote.Saved, jobs)
	}
}
