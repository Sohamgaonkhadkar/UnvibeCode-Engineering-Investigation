"""Offline replay of two genuine 0.4.0 client-download artifacts; no API calls."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    with zipfile.ZipFile(path) as archive:
        return {name:[json.loads(line) for line in archive.read(name).splitlines() if line.strip()]
                for name in ("chunks.jsonl","connections.jsonl","selections.jsonl")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ROOT/"evidence/latest-client-0.4.0")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    status = json.loads((args.artifacts/"run-status.json").read_text(encoding="utf-8"))
    bundles = {phase:load(args.artifacts/(phase+".zip")) for phase in ("original","wrapper")}
    source = {}
    result = {"client_version":"0.4.0", "hosted_backend_revision":"not exposed",
              "capture_date":"2026-11-12", "states":{}, "boundary":status["boundary"]}
    for phase,bundle in bundles.items():
        assert status["states"][phase]["FAST_LANE"] == "COMPLETED"
        chunks = bundle["chunks.jsonl"]
        source[phase] = {c["file"]:"\n".join(re.sub(r"^\s*\d+\s\|\s?", "", line) for line in c["numbered_code"].splitlines()) for c in chunks}
        assert len(chunks) == len(source[phase]) == 4
        edges = [e for e in bundle["connections.jsonl"] if e["source_file"]=="source.go"
                 and e["target_file"]=="store.go" and e.get("symbol")=="Save"]
        expected = phase=="wrapper"
        assert len(edges)==int(expected), edges
        row = next(s for s in bundle["selections.jsonl"] if s["file"]=="source.go")
        selected_files = {}
        for scope in ("1","2"):
            selected = set(row["scopes"][scope]["chunk_ids"])
            files = sorted(c["file"] for c in chunks if c["chunk_id"] in selected)
            assert ("store.go" in files)==expected
            selected_files[scope]=files
        path = args.artifacts/(phase+".zip")
        result["states"][phase] = {
            "bundle_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_files":len(chunks), "exported_relationship_records":len(bundle["connections.jsonl"]),
            "Store_Save_relationships":len(edges), "source_go_selected_files":selected_files,
            "recovered_source_text_sha256":{f:hashlib.sha256(code.encode()).hexdigest() for f,code in source[phase].items()},
            "overall_review_status":status["states"][phase]["overall_status"],
            "code_understanding_status":status["states"][phase]["FAST_LANE"],
            "business_analysis_status":status["states"][phase]["FULL_ANALYSIS"],
        }
    assert source["original"].keys()==source["wrapper"].keys()
    for file,code in source["original"].items():
        if file=="source.go":
            assert code.count("callback := s.Save")==1
            assert code.replace("callback := s.Save","callback := func() { s.Save() }")==source["wrapper"][file]
        else:
            assert code==source["wrapper"][file]
    result["input_difference"]="Exactly one callback expression in source.go; other uploaded source text identical"
    result["status"]="passed"
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PASS: captured current-client code maps: method value 0 links/no Store context; wrapper 1 link/Store context; one-expression source difference.")

if __name__=="__main__":
    main()
