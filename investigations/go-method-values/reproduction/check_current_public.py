"""Offline audit of three actual 0.4.0 go-redis code-map downloads.

No installed-engine patch or hosted request. Optional scope extracts copy actual
selection metadata and selected chunks; they are not browser-generated exports.
"""
import argparse
import json
from pathlib import Path
import re
import zipfile
from helpers import records,sha
from explain_context import describe,indexed_lines

ROOT=Path(__file__).resolve().parents[1]
TARGETS=[("himport_cluster.go","osscluster.go","ForEachMaster",3,2341,2375),
         ("himport_cluster.go","ring.go","ForEachShard",3,815,848),
         ("autopipeline_cluster_fd.go","osscluster.go","processPipelineRetries",1,2962,3040),
         ("multidb.go","multidb_pipeline.go","processPipeline",1,265,267)]


def all_lines(chunks):
    return {file:indexed_lines(chunks,file) for file in sorted({c["file"] for c in chunks})}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--artifacts",type=Path,default=ROOT/"evidence/current-public-0.4.0")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--focused-output",type=Path)
    a=p.parse_args()
    manifest=json.loads((a.artifacts/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["client_version"]=="0.4.0"
    states={};sources={}
    result={"repository":"https://github.com/redis/go-redis","commit":manifest["inputs"]["commit"],
        "client_version":"0.4.0","hosted_backend_revision":"not exposed","states":{},"targets":[],
        "boundary":"A original, B receiver-preserving direct-call wrapper, C intentionally non-equivalent no-method callback. No hosted correction or business-risk improvement claimed."}
    for phase in "ABC":
        path=a.artifacts/(phase+".zip")
        with zipfile.ZipFile(path) as archive:
            states[phase]={n:records(archive,n) for n in ("chunks.jsonl","connections.jsonl","selections.jsonl")}
        assert manifest["states"][phase]["FAST_LANE"]=="COMPLETED"
        sources[phase]=all_lines(states[phase]["chunks.jsonl"])
        inputs=manifest["inputs"]["states"][phase]
        assert inputs["go_mod_uploaded"] is False
        assert inputs["upload_paths_sha256"]==manifest["inputs"]["states"]["A"]["upload_paths_sha256"]
        result["states"][phase]={"bundle_sha256":sha(path),"chunks":len(states[phase]["chunks.jsonl"]),
            "relationships":len(states[phase]["connections.jsonl"]),"selections":len(states[phase]["selections.jsonl"]),
            **manifest["states"][phase]}
    changed={}
    for phase in "BC":
        assert sources[phase].keys()==sources["A"].keys()
        changes=[]
        for file,lines in sources["A"].items():
            assert lines.keys()==sources[phase][file].keys(),(phase,file,"source line inventory changed")
            for n,text in lines.items():
                actual=sources[phase][file][n]
                if actual==text:continue
                expected=text
                for edit in manifest["inputs"]["edits"]:
                    if edit["file"]==file:
                        expected=re.sub(re.escape(edit["selector"])+r"(?![A-Za-z0-9_])",lambda _:edit["wrapper" if phase=="B" else "negative"],expected)
                assert expected==actual,(phase,file,n,"unexplained source difference")
                changes.append({"file":file,"line":n})
        assert len(changes)==8 and len({x["file"] for x in changes})==3,changes
        changed[phase]=changes
    result["verified_source_changes"]=changed
    fields=("source_file","target_file","source_line","target_line","relationship","symbol","confidence")
    normalized={phase:{tuple(e.get(k) for k in fields) for e in bundle["connections.jsonl"]} for phase,bundle in states.items()}
    gained=normalized["B"]-normalized["A"]
    assert not normalized["A"]-normalized["B"]
    assert normalized["C"]==normalized["A"]
    kinds={kind:sum(e[4]==kind for e in gained) for kind in {e[4] for e in gained}}
    assert kinds=={"method_call":8,"file_import":7},kinds
    result["normalized_relationship_delta"]={"identity_fields":fields,"B_gained":15,"B_lost":0,"B_gained_by_kind":kinds,"C_equals_A":True,
        "boundary":"Chunk IDs change with edited text; comparison preserves file, source/target lines, relationship kind, symbol and confidence."}
    for source,target,symbol,count,start,end in TARGETS:
        # Target implementations must be identical in all three downloaded inputs.
        base=sources["A"][target]
        assert all(sources[x][target]==base for x in "BC")
        text=[base.get(n,"") for n in range(1,max(base)+1)]
        assert any("func " in base.get(n,"") and symbol in base.get(n,"") for n in range(start,min(start+5,end+1)))
        row={"source":source,"target":target,"symbol":symbol,"definition_lines":[start,end],"states":{}}
        for phase,bundle in states.items():
            edges=[e for e in bundle["connections.jsonl"] if e["source_file"]==source and e["target_file"]==target and e.get("symbol")==symbol]
            assert len(edges)==(count if phase=="B" else 0),(phase,symbol,edges)
            observations={}
            selection=next(s for s in bundle["selections.jsonl"] if s["file"]==source)
            for scope in ("1","2"):
                observations[scope]=describe(bundle["chunks.jsonl"],selection["scopes"][scope],target,start,end,text)
            row["states"][phase]={"method_relationships":len(edges),"relationship_kinds":sorted({e["relationship"] for e in edges}),"scopes":observations}
        result["targets"].append(row)
    # Core current-version outcome, independently of unrelated module edges.
    assert sum(t["states"]["B"]["method_relationships"] for t in result["targets"])==8
    for t in result["targets"]:
        for scope in ("1","2"):
            assert t["states"]["B"]["scopes"][scope]["coverage"]=="complete",(t["symbol"],scope)
            assert t["states"]["A"]["scopes"][scope]["coverage"]=="absent",(t["symbol"],scope)
            assert t["states"]["C"]["scopes"][scope]["coverage"]=="absent",(t["symbol"],scope)
    if a.focused_output:
        a.focused_output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(a.focused_output,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for phase,bundle in states.items():
                selected=next(s for s in bundle["selections.jsonl"] if s["file"]=="himport_cluster.go")
                for scope in ("1","2"):
                    metadata=selected["scopes"][scope];ids=set(metadata["chunk_ids"])
                    content={"basis":"Extracted unchanged from downloaded code-map ZIP; not a browser export",
                        "source_bundle_sha256":result["states"][phase]["bundle_sha256"],"selected_file":"himport_cluster.go",
                        "scope":scope,"selection":metadata,"chunks":[c for c in bundle["chunks.jsonl"] if c["chunk_id"] in ids]}
                    z.writestr(phase+"-himport-scope-"+scope+".json",json.dumps(content,indent=2)+"\n")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PASS current public A/B/C: eight method links and four complete bodies only in wrapper; same upload inventory; eight source edits")


if __name__=="__main__":main()
