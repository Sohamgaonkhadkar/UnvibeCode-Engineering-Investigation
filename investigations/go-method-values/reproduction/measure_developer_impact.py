"""Measure answer-relevant implementation evidence, not model answer accuracy."""
import argparse
import json
from pathlib import Path
import zipfile
from helpers import records, sha
from explain_context import describe

QUESTIONS = [
    ("autopipeline_cluster_fd.go","processPipelineRetries",
     "When a full-duplex child reroutes a pipeline, how many execution attempts does the supplied retry bound allow?",
     "The implementation loops while attempt <= maxRedirects, with backoff after the first attempt; callback installation alone does not establish that loop.",
     ["attempt <= maxRedirects", "if attempt > 0"]),
    ("himport_cluster.go","ForEachMaster",
     "Does eager HIMPORT master fan-out run callbacks concurrently, wait for completion, and return an error?",
     "ForEachMaster enumerates declared masters, launches goroutines, waits for all work, and returns an error buffered from a callback. This is not evidence that its error is earliest in wall-clock time.",
     ["state.declaredMasters()", "go func", "wg.Wait()", "return err"]),
    ("himport_cluster.go","ForEachShard",
     "Does ring HIMPORT fan-out invoke the callback on shards currently marked down?",
     "ForEachShard skips IsDown shards before starting callback goroutines; the call site alone cannot establish this filter.",
     ["if shard.IsDown()", "continue"]),
    ("multidb.go","processPipeline",
     "Which configured retry bound does the MultiDB pipeline hook pass to its retry implementation?",
     "processPipeline forwards c.opts.CommandRetries to processPipelineRetries. This three-line method establishes delegation, not all retry or delivery semantics.",
     ["c.processPipelineRetries(ctx, cmds, c.opts.CommandRetries)"]),
]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--artifacts",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    verification=json.loads((root/"evidence/verification.json").read_text(encoding="utf-8"))
    targets=verification["public"]["complete_target_audit"]
    result={"engine_version":"0.3.15","repository":"https://github.com/redis/go-redis",
        "commit":"5cba5e182946cf18a757718938bc43910e589466",
        "method":"Exact nonblank method-definition source lines in actual selected chunks at original scope budgets",
        "boundary":"Measures availability of answer-relevant source. No model was asked these questions; no incorrect-answer or accuracy improvement is claimed.",
        "bundle_sha256":{},"questions":[]}
    states={}
    for state in ("stock","corrected","restored"):
        path=a.artifacts/state/"run/shipready_complete_repository_context.zip"
        with zipfile.ZipFile(path) as z:
            states[state]=(records(z,"chunks.jsonl"),records(z,"selections.jsonl"))
        result["bundle_sha256"][state]=sha(path)
    for source,symbol,question,consequence,anchors in QUESTIONS:
        matches=[t for t in targets if t["source"]==source and t["symbol"]==symbol]
        assert len(matches)==1
        target=matches[0];start,end=target["definition_lines"]
        lines=(a.repo/target["target"]).read_text(encoding="utf-8").splitlines()
        method="\n".join(lines[start-1:end])
        assert all(anchor in method for anchor in anchors)
        row={"question":question,"source":source,"target":target["target"],"owner":target["owner"],
            "symbol":symbol,"definition_lines":[start,end],"implementation_excerpt":method,
            "source_supported_consequence":consequence,"question_anchors":anchors,"scopes":{}}
        for scope in ("1","2"):
            row["scopes"][scope]={}
            for state,(chunks,selections) in states.items():
                selection=next(s for s in selections if s["file"]==source)["scopes"][scope]
                observation=describe(chunks,selection,target["target"],start,end,lines)
                assert observation["coverage"]==("complete" if state=="corrected" else "absent")
                row["scopes"][scope][state]=observation
        result["questions"].append(row)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PASS four source-backed developer questions: absent -> complete -> absent in both original-budget scopes")


if __name__=="__main__":main()
