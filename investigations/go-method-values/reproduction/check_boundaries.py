"""Compiler/runtime-backed receiver, field and interface regression controls."""
import argparse
import contextlib
import json
from pathlib import Path
import subprocess
import sys
from helpers import load_engine, pipeline, sha

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"solution"))
from method_values import corrected

FILES = {
    "go.mod": "module example.com/boundary\n\ngo 1.25\n",
    "store.go": "package boundary\ntype Store struct { Saved int }\nfunc (s *Store) Save() { s.Saved++ }\n",
    "other.go": "package boundary\ntype Other struct { Saved int }\nfunc (s *Other) Save() { s.Saved += 10 }\n",
    "field.go": "package boundary\ntype FieldStore struct { Save func() }\ntype Saver interface { Save() }\n",
    "remote/remote.go": "package remote\nfunc Save() {}\n",
    "source.go": '''package boundary
import "example.com/boundary/remote"
func Bound(s *Store) func() { callback := s.Save; return callback }
func Local() func() { s := &Store{}; callback := s.Save; return callback }
func OtherBound(s *Other) func() { callback := s.Save; return callback }
func Field(s *FieldStore) func() { callback := s.Save; return callback }
func Interface(s Saver) func() { callback := s.Save; return callback }
func Package() func() { callback := remote.Save; return callback }
func Direct(s *Store) { s.Save() }
func Wrapper(s *Store) func() { return func(receiver *Store) func() { return func() { receiver.Save() } }(s) }
''',
    "source_test.go": '''package boundary
import "testing"
func TestFormationAndSavedReceiver(t *testing.T) {
    for _, form := range []func(*Store) func(){Bound, Wrapper} {
        first, second := &Store{}, &Store{}
        receiver := first
        callback := form(receiver)
        receiver = second
        if first.Saved != 0 || second.Saved != 0 { t.Fatal("formation invoked method") }
        callback()
        if first.Saved != 1 || receiver.Saved != 0 { t.Fatal("receiver was not saved") }
    }
}
func TestFieldInterfaceAndSameName(t *testing.T) {
    n := 0
    Field(&FieldStore{Save:func(){n++}})()
    s, other := &Store{}, &Other{}
    Interface(s)()
    OtherBound(other)()
    Package()()
    if n != 1 || s.Saved != 1 || other.Saved != 10 { t.Fatal("wrong callback target") }
}
''',
}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    fixture=a.work/"fixture"
    for name,text in FILES.items():
        path=fixture/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding="utf-8")
    runtime=subprocess.run(["go","test","-mod=readonly","-count=1","-v","./..."],cwd=fixture,text=True,capture_output=True)
    (a.work/"go-test.log").write_text(runtime.stdout+runtime.stderr,encoding="utf-8")
    assert runtime.returncode==0,runtime.stdout+runtime.stderr
    result={"runtime":"passed","cases":[],"boundary":"Interface method declarations may be referenced; no concrete implementation is inferred."}
    for pattern in ("00a_*.py","01_*.py"):
        engine,path=load_engine(pattern)
        before=sha(path)
        first=None
        for phase in ("stock","corrected","restored"):
            with corrected(engine) if phase=="corrected" else contextlib.nullcontext():
                if pattern.startswith("00a"):
                    graph,_=pipeline(engine,fixture,a.work/pattern[:3]/phase)
                else:
                    g=engine.ShipReadyV2DeepGraphBuilder(str(fixture)).build()
                    linker=engine.LinkerResolutionModule(graph_documents=[g])
                    linker.resolve_to(a.work/pattern[:3]/phase/"resolved.json")
                    graph=linker.resolved_document
            edges=[e for e in graph["symbol_edges"] if e["source"]=="source.go" and e.get("symbol")=="Save"]
            by_line=lambda n:[e for e in edges if e.get("line")==n]
            for line,owner in ((3,"Store"),(4,"Store"),(5,"Other")):
                selected=by_line(line)
                assert len(selected)==int(phase=="corrected"),(pattern,phase,line,selected)
                if selected:
                    assert selected[0].get("owner")==owner
                    assert selected[0]["type"]=="imports_symbol" and selected[0]["import_style"]=="go_method_value"
            assert not by_line(6),"Function-valued field acquired a method edge"
            assert not any(e.get("owner") in {"Store","Other"} for e in by_line(7)),"Concrete implementation invented for interface"
            assert any(e["target"]=="remote/remote.go" for e in by_line(8)),"Package function value lost"
            assert any(e["type"]=="method_call" and e.get("owner")=="Store" for e in by_line(9))
            normalized=sorted(json.dumps(e,sort_keys=True) for e in edges)
            if phase=="stock":first=normalized
            if phase=="restored":assert normalized==first
            result["cases"].append({"engine":path.name,"phase":phase,"edges":edges,
                "field_not_promoted":True,"interface_concrete_target_not_invented":True})
        assert sha(path)==before
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PASS both engines: bound/local/same-name references, fields/interfaces, package values, invocation distinction and restoration")


if __name__=="__main__":
    main()
