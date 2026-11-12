"""Explain line coverage and bounded selection independently of graph recovery.

Read actual stock/corrected/restored ZIPs. Optional budget control rebuilds the
installed product's selector and changes only a scope's maximum token budget.
No public source, installed file, or primary correction is modified.
"""
import argparse
import json
import re
import zipfile
from pathlib import Path
from helpers import load_engine, records, sha


def indexed_lines(chunks, target):
    result = {}
    for chunk in chunks:
        if chunk["file"] == target:
            for line in chunk["numbered_code"].splitlines():
                match = re.match(r"^\s*(\d+)\s\|\s?(.*)$", line)
                if match:
                    result[int(match[1])] = match[2]
    return result


def describe(chunks, selection, target, start, end, source):
    needed = {n: source[n-1] for n in range(start, end+1) if source[n-1].strip()}
    selected = set(selection["chunk_ids"])
    actual = indexed_lines([c for c in chunks if c["chunk_id"] in selected], target)
    found = [n for n, text in needed.items() if actual.get(n) == text]
    return {
        "matching_nonblank_lines": len(found), "required_nonblank_lines": len(needed),
        "coverage": "complete" if len(found) == len(needed) else "absent" if not found else "partial",
        "missing_lines": sorted(set(needed)-set(found)),
        "estimated_tokens": selection["estimated_tokens"],
        "maximum_tokens": selection["maximum_tokens"],
        "target_file_in_selection": any(c["file"] == target and c["chunk_id"] in selected for c in chunks),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-control-work", type=Path)
    args = parser.parse_args()
    verification = json.loads(args.verification.read_text(encoding="utf-8"))
    targets = verification["public"]["complete_target_audit"]
    states, result = {}, {"basis": "Actual exported ZIPs; exact nonblank source-line equality", "targets": []}
    for phase in ("stock", "corrected", "restored"):
        path = args.artifacts / phase / "run/shipready_complete_repository_context.zip"
        with zipfile.ZipFile(path) as archive:
            states[phase] = (records(archive, "chunks.jsonl"), records(archive, "selections.jsonl"), records(archive, "connections.jsonl"))
        result.setdefault("bundle_sha256", {})[phase] = sha(path)
    for target in targets:
        source = (args.repo / target["target"]).read_text(encoding="utf-8").splitlines()
        row = {k: target[k] for k in ("source", "target", "symbol", "owner", "definition_lines")}
        row["scopes"] = {}
        for scope in ("1", "2"):
            observations = {}
            for index, phase in enumerate(("stock", "corrected", "restored")):
                chunks, selections, edges = states[phase]
                selection = next(s for s in selections if s["file"] == target["source"])["scopes"][scope]
                observations[phase] = describe(chunks, selection, target["target"], *target["definition_lines"], source)
                refs = [e for e in edges if e["source_file"] == target["source"] and e["target_file"] == target["target"] and e.get("symbol") == target["symbol"]]
                observations[phase]["reference_edges"] = refs
                if phase == "corrected":
                    assert refs, "Corrected method relationship missing"
                assert (observations[phase]["coverage"] == "complete") == target["availability"][scope][index]
            row["scopes"][scope] = observations
        result["targets"].append(row)
    if args.budget_control_work:
        engine, path = load_engine("00a_*.py")
        before = sha(path)
        graph = json.loads((args.artifacts / "corrected/run/shipreadyv2_resolved_graph.json").read_text(encoding="utf-8"))
        builder = engine.FastLaneContextDownloadBuilder(args.repo, graph)
        args.budget_control_work.mkdir(parents=True, exist_ok=True)
        builder.build(args.budget_control_work / "baseline.html")
        baseline = next(s for s in states["corrected"][1] if s["file"] == "multidb.go")
        result["budget_control"] = []
        for scope, setting in (("1", "DIRECT_CONTEXT_MAX_TOKENS"), ("2", "EXTENDED_CONTEXT_MAX_TOKENS")):
            native = builder._selection("multidb.go", int(scope))
            assert native["chunk_ids"] == baseline["scopes"][scope]["chunk_ids"]
            original = getattr(engine, setting)
            try:
                setattr(engine, setting, 200000)
                expanded = builder._selection("multidb.go", int(scope))
            finally:
                setattr(engine, setting, original)
            # Export schema uses numbered_code; use the actual ZIP chunk text.
            chunks = states["corrected"][0]
            for target in targets:
                if target["symbol"] not in ("process", "processTxPipeline"):
                    continue
                source = (args.repo / target["target"]).read_text(encoding="utf-8").splitlines()
                result["budget_control"].append({
                    "scope": scope, "changed_setting": setting, "stock_maximum": original,
                    "control_maximum": 200000, "symbol": target["symbol"],
                    "result": describe(chunks, expanded, target["target"], *target["definition_lines"], source),
                })
        assert all(row["result"]["coverage"] == "complete" for row in result["budget_control"]), "Budget-only recovery did not reproduce"
        assert sha(path) == before
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS: all seven targets agree with saved complete-definition measurements; actual line coverage explained.")
    if "budget_control" in result:
        print("Budget control:", [(r["scope"], r["symbol"], r["result"]["coverage"]) for r in result["budget_control"]])


if __name__ == "__main__":
    main()
