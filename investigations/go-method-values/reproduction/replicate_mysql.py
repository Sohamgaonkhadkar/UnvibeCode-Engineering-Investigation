"""Independent installed-engine replication on the complete pinned MySQL driver."""
import argparse
import contextlib
import json
from pathlib import Path
import subprocess
import sys
from helpers import load_engine,pipeline,key,sha,coverage,selections
from explain_context import describe
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"solution"))
from method_values import corrected

PIN="4cdf75e9037ffccf63a981d10f5c2e669edbfc49"
EXPECTED={("packets.go","connection.go",33,"readWithTimeout","mysqlConn"),
          ("packets.go","connection.go",133,"writeWithTimeout","mysqlConn")}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();repo=a.repo.resolve()
    git=["git","-c","safe.directory="+repo.as_posix(),"-C",str(repo)]
    assert subprocess.check_output(git+["rev-parse","HEAD"],text=True).strip()==PIN
    assert not subprocess.check_output(git+["status","--porcelain"],text=True).strip()
    tracked=subprocess.check_output(git+["ls-files"],text=True).splitlines()
    before={f:sha(repo/f) for f in tracked if (repo/f).is_file()}
    result={"repository":"https://github.com/go-sql-driver/mysql","commit":PIN,"engines":[],
        "boundary":"Independent 0.3.15 installed-engine replication; not a 0.4.0 hosted result. Existing direct calls can already retain target bodies."}
    for pattern in ("00a_*.py","01_*.py"):
        engine,path=load_engine(pattern);digest=sha(path);graphs=[];bundles=[]
        for phase in ("stock","corrected","restored"):
            with corrected(engine) if phase=="corrected" else contextlib.nullcontext():
                if pattern.startswith("00a"):
                    graph,bundle=pipeline(engine,repo,a.work/pattern[:3]/phase);bundles.append(bundle)
                else:
                    g=engine.ShipReadyV2DeepGraphBuilder(str(repo)).build()
                    linker=engine.LinkerResolutionModule(graph_documents=[g]);linker.resolve_to(a.work/pattern[:3]/phase/"resolved.json")
                    graph=linker.resolved_document
            graphs.append(graph)
        sets=[{key(e) for e in g["symbol_edges"]} for g in graphs]
        assert sets[0]==sets[2] and not sets[0]-sets[1]
        production={e for e in sets[1]-sets[0] if not e[0].endswith("_test.go")}
        assert production==EXPECTED,production
        row={"engine":path.name,"source_sha256":digest,"relationships":[len(s) for s in sets],
             "gained_production_references":[list(x) for x in sorted(production)],"lost":0,"coverage":[]}
        if bundles:
            for source,target,line,symbol,owner in sorted(EXPECTED):
                defs=[d for d in graphs[1]["global_symbol_index"][symbol] if d["source_file"]==target and d.get("owner")==owner]
                assert len(defs)==1
                span=defs[0]["line_range"];lines=(repo/target).read_text(encoding="utf-8").splitlines()
                row["coverage"].append({"source":source,"target":target,"symbol":symbol,"definition_lines":span,
                    "complete_body":{scope:[coverage(selections(b,source,scope),target,span["start_line"],span["end_line"],lines) for b in bundles] for scope in ("1","2")},
                    "line_coverage":{scope:[describe(b["chunks.jsonl"],next(s for s in b["selections.jsonl"] if s["file"]==source)["scopes"][scope],target,span["start_line"],span["end_line"],lines) for b in bundles] for scope in ("1","2")}})
        assert sha(path)==digest
        result["engines"].append(row)
    assert before=={f:sha(repo/f) for f in before}
    result["tracked_source_unchanged"]=True
    result["source_hashes"]={f:before[f] for f in ("packets.go","connection.go","go.mod")}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    cases=[dict(zip(("source","target","line","symbol","owner"),x)) for x in sorted(EXPECTED)]
    a.output.with_name(a.output.stem+"-compiler-cases.json").write_text(json.dumps(cases,indent=2)+"\n",encoding="utf-8")
    print("PASS independent MySQL replication: two production method references, both engines, zero losses and restoration")


if __name__=="__main__":main()
