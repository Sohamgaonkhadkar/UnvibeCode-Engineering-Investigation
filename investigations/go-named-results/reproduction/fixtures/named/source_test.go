package namedresult

import "testing"

func TestOpen(t *testing.T) {
	if !Open().Saved { t.Fatal("Open must call Store.Save") }
	if Imported() != "remote" { t.Fatal("package-qualified control changed") }
}
