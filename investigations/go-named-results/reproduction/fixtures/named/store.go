package namedresult

type Store struct{ Saved bool }

func (s *Store) Save() { s.Saved = true }
