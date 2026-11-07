package fixture

import "example.com/method-values/remote"

func Run(s *Store) {
	callback := s.Save
	callback()
}

func PackageControl() {
	callback := remote.Save
	callback()
}

func FieldControl(s *Store) {
	callback := s.Job
	callback()
}
