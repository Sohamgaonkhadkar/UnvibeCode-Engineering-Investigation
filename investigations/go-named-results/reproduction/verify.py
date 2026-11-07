"""Assert the exact stock defect, controls, reference correction, and exported impact.

python verify.py --output result.json [--real-repo /path/to/goleveldb]
Runs only local installed-product stages. No hosted analysis or application DB needed.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "solution"))
from named_results import corrected

REAL_SHA = "126854af5e6d8295ef8e8bee3040dd8380ae72e8"
REAL_EDGES = {
    ("leveldb/session.go", "leveldb/options.go", 89, "setOptions", "session"),
    ("leveldb/session.go", "leveldb/session_util.go", 93, "refLoop", "session"),
    ("leveldb/session.go", "leveldb/session_util.go", 94, "setVersion", "session"),
    ("leveldb/session.go", "leveldb/session_util.go", 95, "log", "session"),
    ("leveldb/db_write.go", "leveldb/db_state.go", 78, "decref", "memDB"),
    ("leveldb/db_write.go", "leveldb/db_state.go", 105, "decref", "memDB"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_engine(pattern):
    import shipreadyv2
    path = next((Path(shipreadyv2.__file__).parent / "engine_sources").glob(pattern))
    spec = importlib.util.spec_from_file_location("named_" + pattern[:3], path)
    engine = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = engine
    spec.loader.exec_module(engine)
    engine.AUTO_OPEN_FAST_LANE_GRAPHS = False
    return engine, path


CASES = {
    "named": ("func Open() (r *Store) { r = &Store{}; r.Save(); return }", None, "Store"),
    "local_control": ("func Open() *Store { var r *Store; r = &Store{}; r.Save(); return r }", "Store", "Store"),
    "parameter_control": ("func Open(r *Store) { r.Save() }", "Store", "Store"),
    "named_method": ("func (x *Other) Open() (r *Store) { r = &Store{}; r.Save(); return }", None, "Store"),
    "named_closure": ("func Open() (r *Store) { r = &Store{}; func(){ r.Save() }(); return }", None, "Store"),
    "grouped_results": ("func Open() (r, s *Store) { r = &Store{}; s = &Store{}; r.Save(); s.Save(); return }", None, "Store"),
    "shadow_control": ("func Open() (r *Store) { r = &Store{}; { r := &Other{}; r.Save() }; return }", "Other", "Other"),
    "unnamed_control": ("func Open() *Store { r := &Store{}; r.Save(); return r }", "Store", "Store"),
    "unknown_control": ("func Open(r interface{ Save() }) { r.Save() }", None, None),
}


def extraction_checks(engine):
    out = []
    for fixed in (False, True, False):
        with corrected(engine) if fixed else contextlib.nullcontext():
            adapter = engine.TreeSitterAstAdapter()
            for name, (body, stock, repaired) in CASES.items():
                code = "package fixture\n" + body
                parsed = adapter.parse("go", "source.go", Path("source.go"), code)
                assert parsed["parser_confidence"] == "high", parsed["parse_errors"]
                calls = [u for u in parsed["usages"] if u.get("symbol") == "Save"]
                assert len(calls) == (2 if name == "grouped_results" else 1), calls
                owners = [(u.get("receiver_type") or {}).get("name") for u in calls]
                expected = repaired if fixed else stock
                assert owners == [expected] * len(calls), (name, fixed, calls)
                if expected is not None:
                    assert all(u["kind"] == "method_call" for u in calls)
                out.append({"case": name, "corrected": fixed, "owners": owners,
                            "kinds": [u["kind"] for u in calls]})
    return out


def neighbor_boundaries(engine):
    """The named-result correction does not repair adjacent reported mechanisms."""
    observations = []
    for fixed in (False, True):
        with corrected(engine) if fixed else contextlib.nullcontext():
            adapter = engine.TreeSitterAstAdapter()
            global_case = adapter.parse("go", "x.go", Path("x.go"),
                "package p\nvar r *Store\nfunc f(){ r.Save() }")
            calls = [u for u in global_case['usages'] if u.get('symbol') == 'Save']
            assert len(calls) == 1 and calls[0]['kind'] == 'selector'
            factory_case = adapter.parse("go", "x.go", Path("x.go"),
                "package p\nfunc f(){ NewStore().Save() }")
            assert not any(u.get('symbol') == 'Save' for u in factory_case['usages'])
            observations.append({'corrected':fixed,'package_global_still_selector':True,
                                 'factory_expression_still_omitted':True})
    return observations


def records(z, name):
    return [json.loads(line) for line in z.read(name).decode("utf-8").splitlines() if line.strip()]


def pipeline(engine, repo, output):
    path = engine.run_pipeline(repo, output)
    graph = json.loads(path.read_text(encoding="utf-8"))
    with zipfile.ZipFile(path.parent / "shipready_complete_repository_context.zip") as z:
        bundle = {name: records(z, name) for name in ("chunks.jsonl", "connections.jsonl", "selections.jsonl")}
    return graph, bundle


def key(e):
    return (e["source"], e["target"], e.get("line"), e.get("symbol"), e.get("owner"))


def selections(bundle, file, scope="1"):
    row = next(r for r in bundle["selections.jsonl"] if r["file"] == file)
    ids = set(row["scopes"][scope]["chunk_ids"])
    return [r for r in bundle["chunks.jsonl"] if r["chunk_id"] in ids]


def minimal(engine, work):
    fixture = work / "fixture"
    shutil.copytree(HERE / "fixtures/named", fixture)
    source = fixture / "source.go"
    original = source.read_text(encoding="utf-8")
    control = original.replace("func Open() (r *Store) {", "func Open() *Store {\n\tvar r *Store").replace("\treturn\n", "\treturn r\n")
    rows = []
    for label in ("A", "B", "C", "D", "E"):
        source.write_text(control if label == "B" else original, encoding="utf-8")
        with corrected(engine) if label == "D" else contextlib.nullcontext():
            graph, bundle = pipeline(engine, fixture, work / label)
        edges = [e for e in graph["symbol_edges"] if e["source"] == "source.go" and e.get("line") == (10 if label == "B" else 9)]
        assert len(edges) == 1, edges
        target = "store.go" if label in {"B", "D"} else "remote/remote.go"
        assert edges[0]["target"] == target, edges
        selected = selections(bundle, "source.go")
        files = {c["file"] for c in selected}
        assert ("store.go" in files) == (label in {"B", "D"}), files
        package_control = [e for e in graph["symbol_edges"] if e["source"] == "source.go" and e.get("line") == 5]
        assert len(package_control) == 1 and package_control[0]["target"] == "remote/remote.go"
        connections = [e for e in bundle["connections.jsonl"] if e["source_file"] == "source.go" and e["target_file"] == target]
        assert connections, target
        rows.append({"state": label, "call_target": target, "owner": edges[0].get("owner"),
                     "selected_files": sorted(files), "package_control": "remote/remote.go",
                     "graph_call": edges[0], "exported_connections": connections})
    source.write_text(original, encoding="utf-8")
    return rows


def real(engine, repo, work):
    git = lambda *args: subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    assert git("rev-parse", "HEAD") == REAL_SHA, "Wrong public-repository commit"
    assert not git("status", "--porcelain"), "Public source must be unchanged"
    tracked = git("ls-files").splitlines()
    before = {f: sha(repo / f) for f in tracked}
    graphs, bundles = [], []
    for label in ("stock", "corrected", "restored"):
        with corrected(engine) if label == "corrected" else contextlib.nullcontext():
            g, b = pipeline(engine, repo, work / label)
        graphs.append(g); bundles.append(b)
    sets = [{key(e) for e in g["symbol_edges"]} for g in graphs]
    assert sets[0] == sets[2]
    assert sets[1] - sets[0] == REAL_EDGES, sets[1] - sets[0]
    assert not sets[0] - sets[1]
    assert len(sets[0]) == 1858 and len(sets[1]) == 1864
    tasks = []
    # Predeclared maintenance question: how does newSession initialize options,
    # comparer/filter wrappers, and option caches? Require actual implementation.
    fragments = ["func (s *session) setOptions", "no := dupOptions(o)",
                 "s.icmp = &iComparer{o.GetComparer()}", "no.Filter = &iFilter{filter}", "s.o.cache()"]
    for label, bundle in zip(("stock", "corrected", "restored"), bundles):
        for scope in ("1", "2"):
            chunks = selections(bundle, "leveldb/session.go", scope)
            code = "\n".join(c["numbered_code"] for c in chunks if c["file"] == "leveldb/options.go")
            available = all(f in code for f in fragments)
            assert available == (label == "corrected"), (label, scope)
            tasks.append({"state": label, "scope": scope, "options_implementation_available": available,
                          "options_chunks": [c["chunk_id"] for c in chunks if c["file"] == "leveldb/options.go"]})
    assert before == {f: sha(repo / f) for f in tracked}
    assert not git("status", "--porcelain")
    return {"repository": "https://github.com/syndtr/goleveldb", "commit": REAL_SHA,
            "source_files": len(graphs[0]["nodes"]), "source_hashes": {f: before[f] for f in
                ("leveldb/session.go", "leveldb/options.go", "leveldb/session_util.go", "leveldb/db_write.go", "leveldb/db_state.go")},
            "symbol_edges": [len(s) for s in sets], "gained_edges": [list(k) for k in sorted(REAL_EDGES)],
            "lost_edges": [], "distinct_gained_file_pairs": len({(k[0], k[1]) for k in REAL_EDGES}),
            "answer_evidence": tasks, "tracked_source_unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--real-repo", type=Path)
    parser.add_argument("--work", type=Path)
    args = parser.parse_args()
    assert importlib.metadata.version("unvibecode") == "0.3.15"
    result = {"unvibecode": "0.3.15", "python": platform.python_version(), "platform": platform.platform(),
              "dependencies": {n: importlib.metadata.version(n) for n in
                  ("tree-sitter", "tree-sitter-language-pack", "tiktoken", "pyvis")}, "engines": []}
    temp = tempfile.TemporaryDirectory(prefix="uvc-named-results-") if args.work is None else contextlib.nullcontext(str(args.work))
    with temp as directory:
        work = Path(directory); work.mkdir(parents=True, exist_ok=True)
        for pattern in ("00a_*.py", "01_*.py"):
            engine, path = load_engine(pattern)
            digest = sha(path)
            cases = extraction_checks(engine)
            boundaries = neighbor_boundaries(engine)
            assert sha(path) == digest
            result["engines"].append({"file": path.name, "sha256": digest, "extraction": cases,
                                      "neighbor_boundaries": boundaries})
            if pattern.startswith("00a"):
                result["minimal_pipeline"] = minimal(engine, work / "minimal")
                if args.real_repo:
                    result["real_repository"] = real(engine, args.real_repo.resolve(), work / "real")
            assert sha(path) == digest, "Installed source changed"
    result["status"] = "passed"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("::notice::Named results: both engines, 54 extraction checks, A/B/C/D/E exports passed; "
          + ("LevelDB 1858 -> 1864 -> 1858; options implementation absent -> present -> absent" if args.real_repo else "real-repository run not requested"))


if __name__ == "__main__":
    main()
