package namedresult

import r "example.test/namedresult/remote"

func Imported() string { return r.Save() }

func Open() (r *Store) {
	r = &Store{}
	r.Save()
	return
}
