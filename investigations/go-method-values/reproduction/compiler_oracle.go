// Independently verify graph call targets with Go's standard go/types checker.
// Build once, then run with -repo, -package, -cases, and -output.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/importer"
	"go/parser"
	"go/token"
	"go/types"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

type Package struct {
	Dir, ImportPath, Export string
	GoFiles []string
}
type Case struct {
	Source string `json:"source"`
	Target string `json:"target"`
	Line int `json:"line"`
	Symbol string `json:"symbol"`
	Owner string `json:"owner"`
}
type Result struct {
	Case
	DefinitionLine int `json:"definition_line"`
	DefinitionEndLine int `json:"definition_end_line"`
	CompilerReceiver string `json:"compiler_receiver"`
}
func must(err error) { if err != nil { panic(err) } }
func main() {
	repo := flag.String("repo", "", "unchanged pinned checkout")
	pkg := flag.String("package", ".", "production package to type-check")
	casesFile := flag.String("cases", "", "expected restored production calls")
	output := flag.String("output", "", "JSON result")
	flag.Parse()
	root, err := filepath.Abs(*repo); must(err)
	cmd := exec.Command("go", "list", "-mod=readonly", "-deps", "-export", "-json", *pkg)
	cmd.Dir = root
	cmd.Stderr = os.Stderr
	raw, err := cmd.Output(); must(err)
	decoder := json.NewDecoder(bytes.NewReader(raw))
	packages := map[string]Package{}
	var target Package
	for {
		var p Package
		err := decoder.Decode(&p)
		if err == io.EOF { break }; must(err)
		packages[p.ImportPath] = p
		target = p // go list prints dependencies before the requested package.
	}
	fset := token.NewFileSet()
	files := []*ast.File{}
	for _, name := range target.GoFiles {
		f, err := parser.ParseFile(fset, filepath.Join(target.Dir, name), nil, 0); must(err)
		files = append(files, f)
	}
	lookup := func(path string) (io.ReadCloser, error) {
		p, ok := packages[path]
		if !ok || p.Export == "" { return nil, fmt.Errorf("missing compiled import %s", path) }
		return os.Open(p.Export)
	}
	info := &types.Info{Selections: map[*ast.SelectorExpr]*types.Selection{}}
	config := types.Config{Importer: importer.ForCompiler(fset, "gc", lookup), Sizes: types.SizesFor("gc", runtime.GOARCH)}
	_, err = config.Check(target.ImportPath, fset, files, info); must(err)
	data, err := os.ReadFile(*casesFile); must(err)
	var cases []Case; must(json.Unmarshal(data, &cases))
	results := []Result{}
	for _, c := range cases {
		matches := []Result{}
		for expr, selection := range info.Selections {
			position := fset.Position(expr.Sel.Pos())
			rel, err := filepath.Rel(root, position.Filename); must(err)
			if filepath.ToSlash(rel) != c.Source || position.Line != c.Line || expr.Sel.Name != c.Symbol { continue }
			fn, ok := selection.Obj().(*types.Func); if !ok { continue }
			definition := fset.Position(fn.Pos())
			definitionFile, err := filepath.Rel(root, definition.Filename); must(err)
			sig := fn.Type().(*types.Signature)
			if sig.Recv() == nil { continue }
			receiver := sig.Recv().Type()
			if pointer, ok := receiver.(*types.Pointer); ok { receiver = pointer.Elem() }
			named, ok := receiver.(*types.Named); if !ok { continue }
			if filepath.ToSlash(definitionFile) != c.Target || named.Obj().Name() != c.Owner {
				panic(fmt.Sprintf("compiler disagrees at %s:%d: %s %s", c.Source,c.Line,definitionFile,receiver))
			}
			end := 0
			for _, f := range files {
				for _, decl := range f.Decls {
					if function, ok := decl.(*ast.FuncDecl); ok && function.Name.Pos() == fn.Pos() {
						end = fset.Position(function.End()).Line
					}
				}
			}
			if end == 0 { panic("method AST missing") }
			matches = append(matches, Result{c, definition.Line, end, sig.Recv().Type().String()})
		}
		if len(matches) != 1 { panic(fmt.Sprintf("expected one compiler selection for %+v; got %d",c,len(matches))) }
		results = append(results,matches[0])
	}
	out, err := json.MarshalIndent(map[string]any{"status":"passed","go":runtime.Version(),"package":target.ImportPath,"calls_verified":len(results),"results":results},"","  "); must(err)
	must(os.WriteFile(*output, append(out,'\n'),0644))
	fmt.Printf("Go compiler verified %d/%d exact call-site/receiver/definition targets\n",len(results),len(cases))
}
