package fixture

type Store struct {
	Saved int
	Job func()
}

func (s *Store) Save() {
	s.Saved++
}
