#!/usr/bin/env python3
"""Audit the lexical graph delta with TypeScript `paths` semantics, not prefix labels.

This is deliberately independent of UnvibeCode's resolver implementation. It parses the
actual JSONC tsconfig, applies TypeScript's exact/wildcard pattern precedence, performs
ordinary module-file probing against the resolved graphs' scanned file set, and checks
whether each edge gained in the comment-stripped control points to the file TypeScript's
configured mapping identifies.

Example:
  python reproduction/analyze_alias_oracle.py \
    --graph-as-is /path/to/as-is-resolved-graph.json \
    --graph-control /path/to/control-resolved-graph.json \
    --source-root /path/to/lexical \
    --tsconfig /path/to/lexical/tsconfig.json \
    --lost-output evidence/tsconfig-jsonc/lost_relationships.jsonl \
    --summary-output evidence/tsconfig-jsonc/alias_oracle_summary.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


SOURCE_EXTENSIONS = (".ts", ".tsx", ".d.ts", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strip_jsonc(text: str) -> str:
    """String-aware JSONC-to-JSON conversion for this audit's config parsing."""
    out: list[str] = []
    i, n = 0, len(text)
    in_string = escaped = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def normalize_posix(path: str) -> str:
    normalized = posixpath.normpath(path.replace("\\", "/"))
    return "" if normalized == "." else normalized.lstrip("/")


class PathsOracle:
    def __init__(self, tsconfig: Path, source_root: Path, file_set: set[str]):
        self.source_root = source_root.resolve()
        self.tsconfig = tsconfig.resolve()
        self.file_set = file_set
        try:
            config_dir = self.tsconfig.parent.relative_to(self.source_root).as_posix()
        except ValueError:
            config_dir = ""
        self.config_dir = "" if config_dir == "." else config_dir

        data = json.loads(strip_jsonc(self.tsconfig.read_text(encoding="utf-8")))
        options = data.get("compilerOptions", {})
        self.paths: dict[str, list[str]] = options.get("paths", {})
        base_url = options.get("baseUrl")
        self.base_dir = normalize_posix(
            posixpath.join(self.config_dir, str(base_url)) if base_url else self.config_dir
        )
        self.exact = {k: v for k, v in self.paths.items() if "*" not in k}
        wildcards = []
        for pattern, targets in self.paths.items():
            if "*" not in pattern:
                continue
            if pattern.count("*") != 1:
                raise ValueError(f"Unsupported paths pattern with multiple '*': {pattern}")
            prefix, suffix = pattern.split("*", 1)
            wildcards.append((prefix, suffix, pattern, targets))
        # TypeScript selects the wildcard with the longest prefix before '*'.
        self.wildcards = sorted(wildcards, key=lambda item: (-len(item[0]), item[2]))

    def _probe(self, relative: str) -> str | None:
        relative = normalize_posix(relative)
        if not relative or relative.startswith("../") or relative == "..":
            return None

        candidates: list[str] = []
        lower = relative.lower()
        if lower.endswith(".d.ts"):
            candidates.append(relative)
        elif lower.endswith((".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs")):
            if lower.endswith(".js"):
                stem = relative[:-3]
                candidates.extend([f"{stem}.ts", f"{stem}.tsx", f"{stem}.d.ts", relative])
            elif lower.endswith(".jsx"):
                stem = relative[:-4]
                candidates.extend([f"{stem}.tsx", relative])
            elif lower.endswith(".mjs"):
                candidates.extend([relative[:-4] + ".mts", relative])
            elif lower.endswith(".cjs"):
                candidates.extend([relative[:-4] + ".cts", relative])
            else:
                candidates.append(relative)
        elif PurePosixPath(relative).suffix:
            candidates.append(relative)
        else:
            candidates.extend(relative + ext for ext in SOURCE_EXTENSIONS)
            candidates.extend(f"{relative}/index{ext}" for ext in SOURCE_EXTENSIONS)

        for candidate in candidates:
            candidate = normalize_posix(candidate)
            if candidate in self.file_set:
                return candidate
        return None

    def match(self, specifier: str) -> dict | None:
        specifier = str(specifier or "")
        matched_text = ""
        if specifier in self.exact:
            pattern = specifier
            targets = self.exact[pattern]
            match_kind = "exact"
        else:
            found = None
            for prefix, suffix, pattern, targets in self.wildcards:
                if len(specifier) < len(prefix) + len(suffix):
                    continue
                if not specifier.startswith(prefix):
                    continue
                if suffix and not specifier.endswith(suffix):
                    continue
                end = len(specifier) - len(suffix) if suffix else len(specifier)
                matched_text = specifier[len(prefix) : end]
                found = (pattern, targets)
                break
            if found is None:
                return None
            pattern, targets = found
            match_kind = "wildcard"

        substitutions: list[str] = []
        expected = None
        for target in targets:
            substituted = str(target).replace("*", matched_text)
            joined = normalize_posix(posixpath.join(self.base_dir, substituted))
            substitutions.append(joined)
            if expected is None:
                expected = self._probe(joined)
        return {
            "pattern": pattern,
            "match_kind": match_kind,
            "substitutions": substitutions,
            "expected_target": expected,
        }


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def edge_key(edge: dict):
    return (
        edge.get("source"),
        edge.get("target"),
        str(edge.get("raw") or ""),
        edge.get("line"),
    )


def sym_key(edge: dict):
    return (
        edge.get("source"),
        edge.get("target"),
        str(edge.get("symbol") or ""),
        str(edge.get("raw") or ""),
        edge.get("line"),
    )


def legacy_class(specifier: str, prefixes: tuple[str, ...]) -> str:
    if prefixes and specifier.startswith(prefixes):
        return "alias_prefix"
    if specifier.startswith((".", "/")):
        return "relative_or_absolute"
    return "bare_external_or_other"


def classify_edge(edge: dict, oracle: PathsOracle, *, symbol_edge: bool = False) -> tuple[str, dict | None]:
    match = oracle.match(str(edge.get("raw") or ""))
    if match is None:
        return "no_tsconfig_paths_match", None
    if match["expected_target"] is None:
        return "paths_match_no_probed_file", match
    if match["expected_target"] == edge.get("target"):
        return "verified_paths_target", match
    if symbol_edge:
        # A symbol edge intentionally targets the defining file, which need not
        # be the module entry file returned by file-level module resolution.
        return "paths_match_symbol_target_differs_from_module_entry", match
    return "paths_match_divergent_target", match


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-as-is", required=True)
    parser.add_argument("--graph-control", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--tsconfig", required=True)
    parser.add_argument("--legacy-prefixes", default="lexical,@lexical/")
    parser.add_argument("--lost-output")
    parser.add_argument("--summary-output")
    args = parser.parse_args()

    as_is_path, control_path = Path(args.graph_as_is), Path(args.graph_control)
    source_root, tsconfig = Path(args.source_root), Path(args.tsconfig)
    graph_a, graph_b = load_json(as_is_path), load_json(control_path)

    files_a = {n["file"] for n in graph_a["nodes"]}
    files_b = {n["file"] for n in graph_b["nodes"]}
    oracle = PathsOracle(tsconfig, source_root, files_a | files_b)
    prefixes = tuple(p for p in args.legacy_prefixes.split(",") if p)

    edges_a = {edge_key(e): e for e in graph_a.get("edges", [])}
    edges_b = {edge_key(e): e for e in graph_b.get("edges", [])}
    gained = [edges_b[key] for key in sorted(edges_b.keys() - edges_a.keys())]
    lost = [edges_a[key] for key in sorted(edges_a.keys() - edges_b.keys())]

    audited = []
    status_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()
    for edge in gained:
        status, match = classify_edge(edge, oracle)
        status_counts[status] += 1
        if match:
            pattern_counts[match["pattern"]] += 1
        audited.append(
            {
                "source_file": edge.get("source"),
                "target_file": edge.get("target"),
                "import_specifier": str(edge.get("raw") or ""),
                "source_line": edge.get("line"),
                "resolution_strategy": edge.get("resolution_strategy"),
                "verification_status": status,
                "tsconfig_pattern": None if match is None else match["pattern"],
                "pattern_kind": None if match is None else match["match_kind"],
                "oracle_expected_target": None if match is None else match["expected_target"],
            }
        )

    extracted = []
    for graph in (graph_a, graph_b):
        rows = []
        for node in graph["nodes"]:
            for imp in node.get("imports", []):
                rows.append(
                    (
                        node["file"],
                        str(imp.get("raw") or imp.get("module") or ""),
                        imp.get("line"),
                    )
                )
        extracted.append(rows)

    specifiers = {row[1] for row in extracted[1]}
    configured_specifiers = {spec for spec in specifiers if oracle.match(spec)}
    false_legacy_specifiers = {
        spec
        for spec in specifiers
        if legacy_class(spec, prefixes) == "alias_prefix" and oracle.match(spec) is None
    }

    sym_a = {sym_key(e): e for e in graph_a.get("symbol_edges", [])}
    sym_b = {sym_key(e): e for e in graph_b.get("symbol_edges", [])}
    gained_sym = [sym_b[key] for key in sym_b.keys() - sym_a.keys()]
    sym_status = Counter(classify_edge(edge, oracle, symbol_edge=True)[0] for edge in gained_sym)

    summary = {
        "inputs": {
            "graph_as_is": {
                "path_name": as_is_path.name,
                "sha256": sha256(as_is_path),
                "workspace_root_name": Path(str(graph_a.get("workspace_root") or "")).name,
                "generated_at": graph_a.get("generated_at"),
                "summary": graph_a.get("summary"),
            },
            "graph_control": {
                "path_name": control_path.name,
                "sha256": sha256(control_path),
                "workspace_root_name": Path(str(graph_b.get("workspace_root") or "")).name,
                "generated_at": graph_b.get("generated_at"),
                "summary": graph_b.get("summary"),
            },
            "source_root_name": source_root.resolve().name,
            "tsconfig": {
                "path_name": tsconfig.resolve().name,
                "sha256": sha256(tsconfig),
                "pattern_count": len(oracle.paths),
                "exact_pattern_count": len(oracle.exact),
                "wildcard_pattern_count": len(oracle.wildcards),
            },
        },
        "scan_and_extraction": {
            "node_file_sets_identical": files_a == files_b,
            "nodes_as_is": len(files_a),
            "nodes_control": len(files_b),
            "extracted_import_records_identical": extracted[0] == extracted[1],
            "extracted_import_records": len(extracted[1]),
        },
        "legacy_prefix_audit": {
            "legacy_prefixes": list(prefixes),
            "gained_by_legacy_class": Counter(
                legacy_class(str(e.get("raw") or ""), prefixes) for e in gained
            ),
            "distinct_extracted_specifiers": len(specifiers),
            "distinct_specifiers_matching_tsconfig_paths": len(configured_specifiers),
            "distinct_false_legacy_prefix_specifiers": len(false_legacy_specifiers),
            "false_legacy_prefix_examples": sorted(false_legacy_specifiers)[:20],
        },
        "strong_oracle": {
            "gained_file_edges_total": len(gained),
            "classification": status_counts,
            "gained_file_edges_only_in_as_is": len(lost),
            "gained_symbol_edges_total": len(gained_sym),
            "gained_symbol_edge_classification": sym_status,
            "top_tsconfig_patterns": pattern_counts.most_common(25),
            "distinct_tsconfig_patterns_represented": len(pattern_counts),
        },
    }

    if args.lost_output:
        output = Path(args.lost_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            for row in audited:
                # Name preserved from the investigation: these relationships are
                # absent as-is and present in the comment-stripped control.
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    if args.summary_output:
        output = Path(args.summary_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, default=dict) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
