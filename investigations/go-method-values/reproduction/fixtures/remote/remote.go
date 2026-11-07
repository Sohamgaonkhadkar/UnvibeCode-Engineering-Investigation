package remote

var Saved int

func Save() { Saved++ }

type Unrelated struct{}

func (s *Unrelated) Job() {}
