#!/usr/bin/env python3
"""Compare two UnvibeCode resolved graphs (shipreadyv2_resolved_graph.json) and attribute
edge differences to import-specifier classes. Used to prove that the lexical as-is vs
comment-stripped delta is specific to tsconfig path-alias resolution.

Usage:
  python3 compare_graphs.py GRAPH_AS_IS.json GRAPH_CONTROL.json \
      --alias-prefixes "lexical,@lexical/"
Inputs are explicit paths (works on any machine where the runs were produced).
Graph files live during a run at <temp>/uvc-*/c/run/shipreadyv2_resolved_graph.json
(see technical-logs/analysis-status.json -> lanes.FAST_LANE.artifacts.resolved_graph;
the work directory is deleted after a fully successful run, so copy it during the run).
"""
import argparse, json
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("as_is"); ap.add_argument("control")
ap.add_argument("--alias-prefixes", default="", help="comma-separated import-specifier prefixes declared in tsconfig paths")
args = ap.parse_args()
PREFIXES = tuple(p for p in args.alias_prefixes.split(",") if p)

def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)

A, B = load(args.as_is), load(args.control)

def node_files(g): return sorted(n["file"] for n in g["nodes"])
def extracted_imports(g):
    out = []
    for n in g["nodes"]:
        for imp in n.get("imports", []):
            out.append((n["file"], str(imp.get("raw") or imp.get("module") or ""), imp.get("line")))
    return sorted(out)
def edge_key(e): return (e["source"], e["target"], e.get("raw", ""), e.get("line"))
def sym_key(e): return (e["source"], e["target"], e.get("symbol", ""), e.get("raw", ""), e.get("line"))
def unres_key(u): return (u.get("source"), u.get("raw"), u.get("line"))
def klass(raw):
    if PREFIXES and str(raw).startswith(PREFIXES): return "alias_prefix"
    if str(raw).startswith((".", "/")): return "relative_or_absolute"
    return "bare_external_or_other"

na, nb = node_files(A), node_files(B)
ia, ib = extracted_imports(A), extracted_imports(B)
ea = {edge_key(e): e for e in A["edges"]}; eb = {edge_key(e): e for e in B["edges"]}
sa = {sym_key(e): e for e in A.get("symbol_edges", [])}; sb = {sym_key(e): e for e in B.get("symbol_edges", [])}
ua = {unres_key(u): u for u in A["unresolved_imports"]}; ub = {unres_key(u): u for u in B["unresolved_imports"]}

print(f"workspace A={A.get('workspace_root')}  B={B.get('workspace_root')}")
print(f"[scan] node file sets identical: {na == nb}  (A={len(na)}, B={len(nb)}; only-A={len(set(na)-set(nb))}, only-B={len(set(nb)-set(na))})")
print(f"[extract] extracted import records identical: {ia == ib}  (A={len(ia)}, B={len(ib)})")
only_b = [eb[k] for k in eb.keys() - ea.keys()]
only_a = [ea[k] for k in ea.keys() - eb.keys()]
print(f"[file edges] A={len(ea)} B={len(eb)}  only-in-control={len(only_b)}  only-in-asis={len(only_a)}")
print("  only-in-control by specifier class:", Counter(klass(e.get("raw", "")) for e in only_b))
print("  only-in-control by strategy:", Counter(e.get("resolution_strategy") for e in only_b))
print("  only-in-asis by specifier class:", Counter(klass(e.get("raw", "")) for e in only_a))
only_b_sym = [sb[k] for k in sb.keys() - sa.keys()]
print(f"[symbol edges] A={len(sa)} B={len(sb)}  only-in-control={len(only_b_sym)}  by class:", Counter(klass(e.get("raw", "")) for e in only_b_sym))
rescued = [ua[k] for k in ua.keys() - ub.keys()]
print(f"[unresolved imports] A={len(ua)} B={len(ub)}  resolved-only-in-control={len(rescued)}  by class:", Counter(klass(u.get("raw", "")) for u in rescued))
print("[unresolved in BOTH, by class]", Counter(klass(u.get("raw", "")) for k, u in ua.items() if k in ub))
print("[unresolved only in control (new)]", len(ub.keys() - ua.keys()))
for e in only_b[:3]:
    print("  sample gained file edge:", e["source"], "->", e["target"], "| raw=", e.get("raw"), "| line=", e.get("line"), "| strategy=", e.get("resolution_strategy"))
