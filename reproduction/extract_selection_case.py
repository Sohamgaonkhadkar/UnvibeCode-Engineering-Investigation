#!/usr/bin/env python3
"""Extract one auditable Connected Code selection case from two context bundles.

This is a focused companion to compare_selections.py. It does not infer impact from
graph edges alone: for the selected source file, it records the files/chunks present
in each exported scope, identifies the direct `paths`-verified dependencies, and
links them to control-graph symbol edges.
"""
from __future__ import annotations

import argparse
import json
import zipfile
from collections import defaultdict
from pathlib import Path


def load_bundle(path: Path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            chunks = [
                json.loads(line)
                for line in archive.read("chunks.jsonl").decode("utf-8").splitlines()
                if line.strip()
            ]
            selections = [
                json.loads(line)
                for line in archive.read("selections.jsonl").decode("utf-8").splitlines()
                if line.strip()
            ]
    else:
        chunks = [
            json.loads(line)
            for line in (path / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        selections = [
            json.loads(line)
            for line in (path / "selections.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return {row["chunk_id"]: row for row in chunks}, {row["file"]: row for row in selections}


def effective_files(scope: dict, chunks: dict[str, dict]) -> set[str]:
    return set(scope.get("included_files", [])) | {
        chunks[chunk_id]["file"]
        for chunk_id in scope.get("chunk_ids", [])
        if chunk_id in chunks
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-as-is", required=True)
    parser.add_argument("--bundle-control", required=True)
    parser.add_argument("--graph-control", required=True)
    parser.add_argument("--lost-relationships", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    chunks_a, selections_a = load_bundle(Path(args.bundle_as_is))
    chunks_b, selections_b = load_bundle(Path(args.bundle_control))
    graph = json.loads(Path(args.graph_control).read_text(encoding="utf-8"))
    relationships = []
    for line in Path(args.lost_relationships).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["source_file"] == args.source and row["verification_status"] == "verified_paths_target":
            relationships.append(row)

    node = next((n for n in graph["nodes"] if n["file"] == args.source), None)
    imports = [] if node is None else node.get("imports", [])
    symbol_edges = [edge for edge in graph.get("symbol_edges", []) if edge.get("source") == args.source]
    direct_targets = sorted({row["target_file"] for row in relationships})

    scopes = {}
    scopes_a = selections_a[args.source].get("scopes", {})
    scopes_b = selections_b[args.source].get("scopes", {})
    for key in sorted(set(scopes_a) | set(scopes_b), key=int):
        sa, sb = scopes_a.get(key, {}), scopes_b.get(key, {})
        files_a, files_b = effective_files(sa, chunks_a), effective_files(sb, chunks_b)
        target_presence = {}
        for target in direct_targets:
            target_chunks_a = [
                chunk_id
                for chunk_id in sa.get("chunk_ids", [])
                if chunk_id in chunks_a and chunks_a[chunk_id]["file"] == target
            ]
            target_chunks_b = [
                chunk_id
                for chunk_id in sb.get("chunk_ids", [])
                if chunk_id in chunks_b and chunks_b[chunk_id]["file"] == target
            ]
            target_presence[target] = {
                "as_is": target in files_a,
                "control": target in files_b,
                "as_is_chunks": target_chunks_a,
                "control_chunks": target_chunks_b,
            }
        scopes[key] = {
            "radius": (sb or sa).get("radius"),
            "as_is": {
                "estimated_tokens": sa.get("estimated_tokens"),
                "included_files": sorted(files_a),
                "chunk_ids": sa.get("chunk_ids", []),
            },
            "control": {
                "estimated_tokens": sb.get("estimated_tokens"),
                "included_files": sorted(files_b),
                "chunk_ids": sb.get("chunk_ids", []),
            },
            "files_gained_in_control": sorted(files_b - files_a),
            "files_lost_in_control": sorted(files_a - files_b),
            "direct_verified_dependency_presence": target_presence,
        }

    output = {
        "source_file": args.source,
        "graph_imports": imports,
        "direct_verified_relationships": relationships,
        "control_symbol_edges_from_source": symbol_edges,
        "scopes": scopes,
    }
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
