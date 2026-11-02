#!/usr/bin/env python3
"""Measure downstream Connected Code selection impact between two context bundles.

Inputs may be extracted bundle directories or the emitted repository-context ZIPs.
When supplied with the verified lost-relationship list from analyze_alias_oracle.py,
this separates downstream selection changes in general from *direct dependencies*
that are absent from a selection as-is and recovered in the control.

Example:
  python reproduction/compare_selections.py \
    --bundle-as-is /path/to/as-is-repository-context.zip \
    --bundle-control /path/to/control-repository-context.zip \
    --lost-relationships evidence/tsconfig-jsonc/lost_relationships.jsonl \
    --summary-output evidence/tsconfig-jsonc/selection_impact_summary.json \
    --omissions-output evidence/tsconfig-jsonc/direct_selection_omissions.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


SCOPE_NAMES = {0: "Narrow", 1: "Optimal", 2: "Wider"}


class Bundle:
    def __init__(self, location: Path):
        self.location = location
        self.zip = zipfile.ZipFile(location) if location.suffix.lower() == ".zip" else None

    def text(self, name: str) -> str:
        if self.zip is not None:
            return self.zip.read(name).decode("utf-8")
        return (self.location / name).read_text(encoding="utf-8")

    def jsonl(self, name: str) -> list[dict]:
        return [json.loads(line) for line in self.text(name).splitlines() if line.strip()]

    def close(self):
        if self.zip is not None:
            self.zip.close()


def source_category(path: str) -> str:
    parts = Path(path).parts
    if "__tests__" in parts or path.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
        return "test"
    if parts and parts[0] in {"examples", "dev-examples"}:
        return "example"
    if "lexical-playground" in parts:
        return "playground"
    if len(parts) > 2 and parts[0] == "packages" and parts[2] == "src":
        return "package_source"
    return "other"


def bundle_identity(path: Path) -> dict:
    identity = {"name": path.name, "sha256": None}
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        identity["sha256"] = digest.hexdigest()
    return identity


def production_source(path: str) -> bool:
    return source_category(path) == "package_source"


def scope_label(scope_key: str, scope: dict) -> str:
    radius = scope.get("radius")
    name = SCOPE_NAMES.get(radius)
    return f"{name}(radius={radius},key={scope_key})" if name else f"scope(radius={radius},key={scope_key})"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-as-is", required=True)
    parser.add_argument("--bundle-control", required=True)
    parser.add_argument("--lost-relationships")
    parser.add_argument("--summary-output")
    parser.add_argument("--omissions-output")
    parser.add_argument("--candidates-output")
    args = parser.parse_args()

    bundle_a = Bundle(Path(args.bundle_as_is))
    bundle_b = Bundle(Path(args.bundle_control))
    try:
        chunks_a = {row["chunk_id"]: row for row in bundle_a.jsonl("chunks.jsonl")}
        chunks_b = {row["chunk_id"]: row for row in bundle_b.jsonl("chunks.jsonl")}
        selections_a = {row["file"]: row for row in bundle_a.jsonl("selections.jsonl")}
        selections_b = {row["file"]: row for row in bundle_b.jsonl("selections.jsonl")}
        manifest_a = json.loads(bundle_a.text("manifest.json"))
        manifest_b = json.loads(bundle_b.text("manifest.json"))

        direct_targets: dict[str, set[str]] = defaultdict(set)
        direct_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
        if args.lost_relationships:
            for line in Path(args.lost_relationships).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("verification_status") != "verified_paths_target":
                    continue
                source, target = row["source_file"], row["target_file"]
                if source != target:
                    direct_targets[source].add(target)
                    direct_rows[(source, target)].append(row)

        common_files = sorted(set(selections_a) & set(selections_b))
        per_scope: dict[str, dict] = {}
        altered_files: set[str] = set()
        direct_recovered: list[dict] = []
        direct_state: Counter[str] = Counter()

        for source in common_files:
            scopes_a = selections_a[source].get("scopes", {})
            scopes_b = selections_b[source].get("scopes", {})
            for key in sorted(set(scopes_a) | set(scopes_b), key=lambda value: int(value)):
                sa = scopes_a.get(key, {})
                sb = scopes_b.get(key, {})
                label = scope_label(key, sb or sa)
                stats = per_scope.setdefault(
                    label,
                    {
                        "source_files_compared": 0,
                        "altered_source_files": 0,
                        "gained_included_file_instances": 0,
                        "lost_included_file_instances": 0,
                        "gained_chunk_instances": 0,
                        "lost_chunk_instances": 0,
                        "direct_dependency_recovered_instances": 0,
                        "direct_dependency_recovered_source_files": set(),
                    },
                )
                stats["source_files_compared"] += 1

                included_a = set(sa.get("included_files", []))
                included_b = set(sb.get("included_files", []))
                # Cross-check the file view against chunk IDs actually selected.
                chunk_files_a = {
                    chunks_a[chunk_id]["file"]
                    for chunk_id in sa.get("chunk_ids", [])
                    if chunk_id in chunks_a
                }
                chunk_files_b = {
                    chunks_b[chunk_id]["file"]
                    for chunk_id in sb.get("chunk_ids", [])
                    if chunk_id in chunks_b
                }
                effective_a = included_a | chunk_files_a
                effective_b = included_b | chunk_files_b
                gained_files = effective_b - effective_a
                lost_files = effective_a - effective_b
                gained_chunks = set(sb.get("chunk_ids", [])) - set(sa.get("chunk_ids", []))
                lost_chunks = set(sa.get("chunk_ids", [])) - set(sb.get("chunk_ids", []))
                if gained_files or lost_files or gained_chunks or lost_chunks:
                    stats["altered_source_files"] += 1
                    altered_files.add(source)
                stats["gained_included_file_instances"] += len(gained_files)
                stats["lost_included_file_instances"] += len(lost_files)
                stats["gained_chunk_instances"] += len(gained_chunks)
                stats["lost_chunk_instances"] += len(lost_chunks)

                for target in sorted(direct_targets.get(source, set())):
                    in_a = target in effective_a
                    in_b = target in effective_b
                    state = (
                        "present_both" if in_a and in_b else
                        "omitted_as_is_recovered_control" if in_b else
                        "present_as_is_only" if in_a else
                        "omitted_both"
                    )
                    direct_state[f"{label}:{state}"] += 1
                    if state == "omitted_as_is_recovered_control":
                        stats["direct_dependency_recovered_instances"] += 1
                        stats["direct_dependency_recovered_source_files"].add(source)
                        relationship = sorted(
                            direct_rows[(source, target)],
                            key=lambda row: (row.get("source_line") or 0, row["import_specifier"]),
                        )[0]
                        direct_recovered.append(
                            {
                                "source_file": source,
                                "scope": label,
                                "scope_key": key,
                                "radius": (sb or sa).get("radius"),
                                "missing_implementation_file": target,
                                "import_specifier": relationship["import_specifier"],
                                "source_line": relationship.get("source_line"),
                                "tsconfig_pattern": relationship.get("tsconfig_pattern"),
                                "resolution_strategy": relationship.get("resolution_strategy"),
                                "source_category": source_category(source),
                                "target_category": source_category(target),
                                "production_source": production_source(source),
                                "production_target": production_source(target),
                            }
                        )

        serializable_scopes = {}
        for label, stats in per_scope.items():
            value = dict(stats)
            value["direct_dependency_recovered_source_files"] = len(
                value["direct_dependency_recovered_source_files"]
            )
            serializable_scopes[label] = value

        recovered_direct_sources = {
            row["source_file"] for row in direct_recovered
        }
        recovered_direct_pairs = {
            (row["source_file"], row["missing_implementation_file"])
            for row in direct_recovered
        }
        candidates = []
        by_candidate_key: dict[tuple[str, str, str], dict] = {}
        for row in direct_recovered:
            if row["radius"] != 1:
                continue
            if not (row["production_source"] and row["production_target"]):
                continue
            by_candidate_key[
                (row["source_file"], row["missing_implementation_file"], row["import_specifier"])
            ] = row
        source_candidate_counts = Counter(
            row["source_file"] for row in by_candidate_key.values()
        )
        for row in by_candidate_key.values():
            item = dict(row)
            item["recovered_direct_targets_for_source_in_optimal"] = source_candidate_counts[
                row["source_file"]
            ]
            candidates.append(item)
        candidates.sort(
            key=lambda row: (
                row["recovered_direct_targets_for_source_in_optimal"],
                row["source_file"],
                row["missing_implementation_file"],
            )
        )

        summary = {
            "inputs": {
                "bundle_as_is": bundle_identity(Path(args.bundle_as_is)),
                "bundle_control": bundle_identity(Path(args.bundle_control)),
                "manifest_as_is": manifest_a,
                "manifest_control": manifest_b,
                "verified_direct_relationship_pairs": len(direct_rows),
            },
            "selection_files": {
                "as_is": len(selections_a),
                "control": len(selections_b),
                "common_compared": len(common_files),
                "altered_in_any_scope": len(altered_files),
            },
            "per_scope": serializable_scopes,
            "direct_dependency_selection_states": direct_state,
            "direct_dependency_recovered": {
                "source_files_any_scope": len(recovered_direct_sources),
                "distinct_source_target_pairs_any_scope": len(recovered_direct_pairs),
                "instances_by_scope": Counter(row["scope"] for row in direct_recovered),
                "production_to_production_instances": sum(
                    1
                    for row in direct_recovered
                    if row["production_source"] and row["production_target"]
                ),
                "production_to_production_pairs": len(
                    {
                        (row["source_file"], row["missing_implementation_file"])
                        for row in direct_recovered
                        if row["production_source"] and row["production_target"]
                    }
                ),
            },
            "representative_optimal_candidates": candidates[:25],
        }

        if args.omissions_output:
            output = Path(args.omissions_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", encoding="utf-8") as handle:
                for row in direct_recovered:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
        if args.candidates_output:
            output = Path(args.candidates_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(candidates[:100], indent=2) + "\n", encoding="utf-8")
        if args.summary_output:
            output = Path(args.summary_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(summary, indent=2, default=dict) + "\n", encoding="utf-8")

        print(json.dumps(summary, indent=2, default=dict))
        return 0
    finally:
        bundle_a.close()
        bundle_b.close()


if __name__ == "__main__":
    raise SystemExit(main())
