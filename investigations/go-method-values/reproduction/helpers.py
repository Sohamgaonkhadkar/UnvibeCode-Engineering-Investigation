"""Small, standalone helpers for the Go method-value verification suite.

These are general installed-engine/ZIP reading utilities. They do not import
or apply any correction from other investigations.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_engine(pattern):
    import shipreadyv2
    root = Path(shipreadyv2.__file__).parent / "engine_sources"
    path = next(root.glob(pattern))
    spec = importlib.util.spec_from_file_location("method_value_" + pattern[:3], path)
    engine = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = engine
    spec.loader.exec_module(engine)
    engine.AUTO_OPEN_FAST_LANE_GRAPHS = False
    return engine, path


def records(archive, name):
    return [json.loads(line) for line in archive.read(name).decode("utf-8").splitlines() if line.strip()]


def pipeline(engine, repo, output):
    graph_path = engine.run_pipeline(repo, output)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    with zipfile.ZipFile(graph_path.parent / "shipready_complete_repository_context.zip") as archive:
        bundle = {
            name: records(archive, name)
            for name in ("chunks.jsonl", "connections.jsonl", "selections.jsonl")
        }
    return graph, bundle


def key(edge):
    return (
        edge["source"], edge["target"], edge.get("line"),
        edge.get("symbol"), edge.get("owner"),
    )


def selections(bundle, source_file, scope="1"):
    row = next(row for row in bundle["selections.jsonl"] if row["file"] == source_file)
    selected = set(row["scopes"][scope]["chunk_ids"])
    return [chunk for chunk in bundle["chunks.jsonl"] if chunk["chunk_id"] in selected]


def coverage(chunks, target, start, end, source):
    """Require exact source text for every nonblank line of the method body."""
    indexed = {}
    for chunk in chunks:
        if chunk["file"] != target:
            continue
        for line in chunk["numbered_code"].splitlines():
            match = re.match(r"^\s*(\d+)\s\|\s?(.*)$", line)
            if match:
                indexed[int(match[1])] = match[2]
    required = {n: source[n - 1] for n in range(start, end + 1) if source[n - 1].strip()}
    return all(indexed.get(n) == value for n, value in required.items())
