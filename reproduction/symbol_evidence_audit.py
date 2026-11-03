#!/usr/bin/env python3
"""Audit imported-symbol definition lines across exported context bundles.

The six-task answerability audit is deliberately representative.  This
companion scales the same final-artifact question across every verified lost
module relationship:

1. start from the independently verified source/specifier/target rows;
2. use the comment-stripped control graph's per-import ``symbol_resolutions``
   to identify the file that defines each imported symbol;
3. identify a concrete declaration/export line for that symbol in the full
   control bundle; and
4. for each exported bundle and scope, ask whether that declaration line is
   present in the chunks selected for the importing source file.

Only symbol tasks whose declaration can be identified in the full control
bundle are counted.  Tasks with no symbol resolution or no recognizable
declaration pattern are reported separately rather than silently treated as
failures.  This measures definition-evidence availability in the exported
artifact; it does not invoke an LLM or claim answer correctness.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from answerability_audit import AuditError, Bundle, parse_bundle_arg, unnumber


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def has_definition(text: str, symbol: str) -> bool:
    """Return whether ``text`` contains a recognizable definition/export."""

    if not text:
        return False
    if symbol == "default":
        return re.search(r"\bexport\s+default\b", text) is not None

    esc = re.escape(symbol)
    patterns = (
        # function/class/interface/type/enum/value declarations, exported or not
        rf"(?m)^\s*(?:export\s+)?(?:declare\s+)?(?:abstract\s+)?"
        rf"(?:async\s+)?(?:function\s*\*?|class|interface|type|enum|const|let|var)"
        rf"\s+{esc}\b",
        # export default function Foo / export default Foo
        rf"(?m)^\s*export\s+default\s+(?:(?:async\s+)?function\s*\*?\s+|class\s+)?{esc}\b",
        # export { Foo }, export { local as Foo }, including multi-line lists
        rf"(?s)\bexport\s*\{{[^}}]*\b{esc}\b[^}}]*\}}",
        # CommonJS / namespace-style assignments and object-literal definitions
        rf"(?m)^\s*(?:exports\.|module\.exports\.)?{esc}\s*=\s*"
        rf"(?:async\s+)?(?:function|class|\()",
    )
    return any(re.search(pattern, text) is not None for pattern in patterns)


def all_chunk_text(bundle: Bundle, wanted_files: set[str]) -> dict[str, str]:
    by_file: dict[str, list[str]] = defaultdict(list)
    for chunk in bundle.chunks.values():
        file = chunk.get("file")
        if file in wanted_files:
            by_file[file].append(unnumber(chunk.get("numbered_code", "")))
    return {file: "\n".join(parts) for file, parts in by_file.items()}


def scope_for(bundle: Bundle, source_file: str, radius: int) -> dict[str, Any] | None:
    selection = bundle.selections.get(source_file)
    if selection is None:
        return None
    for scope in selection.get("scopes", {}).values():
        if scope.get("radius") == radius:
            return scope
    return None


def selected_texts(
    bundle: Bundle,
    source_file: str,
    radius: int,
    wanted_files: set[str],
) -> dict[str, str]:
    scope = scope_for(bundle, source_file, radius)
    if scope is None:
        return {}
    by_file: dict[str, list[str]] = defaultdict(list)
    for chunk_id in scope.get("chunk_ids", []):
        chunk = bundle.chunks.get(chunk_id)
        if chunk is None:
            raise AuditError(
                f"{bundle.label}: selection references missing chunk {chunk_id}", 2
            )
        if chunk.get("file") in wanted_files:
            by_file[chunk["file"]].append(unnumber(chunk.get("numbered_code", "")))
    return {file: "\n".join(parts) for file, parts in by_file.items()}


def build_symbol_tasks(
    graph: dict[str, Any], relationships: Iterable[dict[str, Any]]
) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Derive symbol-definition tasks from control-graph symbol resolutions."""

    imports_by_key: dict[tuple[str, str, Any], dict[str, Any]] = {}
    for node in graph.get("nodes", []):
        source = node.get("file")
        if not source:
            continue
        for imp in node.get("imports", []):
            raw = str(imp.get("raw") or imp.get("module") or "")
            imports_by_key[(source, raw, imp.get("line"))] = imp

    symbol_edges_by_key: dict[tuple[str, str, Any], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for edge in graph.get("symbol_edges", []):
        if edge.get("type") != "imports_symbol":
            continue
        key = (
            str(edge.get("source") or ""),
            str(edge.get("raw") or ""),
            edge.get("line"),
        )
        symbol_edges_by_key[key].append(edge)

    tasks_by_key: dict[tuple[str, str, Any, str, str], dict[str, Any]] = {}
    exclusions: Counter[str] = Counter()

    for row in relationships:
        if row.get("verification_status") != "verified_paths_target":
            exclusions["relationship_not_verified"] += 1
            continue
        source = row["source_file"]
        specifier = row["import_specifier"]
        line = row.get("source_line")
        module_target = row["target_file"]
        key = (source, specifier, line)
        imp = imports_by_key.get(key)

        resolutions: list[dict[str, Any]] = []
        if imp is not None:
            for item in imp.get("symbol_resolutions", []) or []:
                resolutions.append(
                    {
                        "symbol": str(item.get("symbol") or ""),
                        "definition_file": item.get("resolved_path"),
                        "confidence": item.get("confidence"),
                        "strategy": item.get("strategy"),
                        "reason": item.get("reason"),
                        "provenance": "graph_import_symbol_resolutions",
                    }
                )
        if not resolutions:
            for edge in symbol_edges_by_key.get(key, []):
                resolutions.append(
                    {
                        "symbol": str(edge.get("symbol") or ""),
                        "definition_file": edge.get("target"),
                        "confidence": edge.get("confidence"),
                        "strategy": edge.get("resolution_strategy"),
                        "reason": None,
                        "provenance": "graph_symbol_edges",
                    }
                )

        if imp is None and not resolutions:
            exclusions["relationship_without_graph_import_record"] += 1
            continue
        if not resolutions:
            exclusions["import_without_symbol_resolutions"] += 1
            continue

        for item in resolutions:
            symbol = item["symbol"]
            definition_file = item["definition_file"]
            if not symbol:
                exclusions["symbol_resolution_without_symbol"] += 1
                continue
            if not definition_file:
                exclusions["symbol_without_definition_file"] += 1
                continue
            task_key = (source, specifier, line, symbol, str(definition_file))
            tasks_by_key[task_key] = {
                "source_file": source,
                "import_specifier": specifier,
                "source_line": line,
                "module_target_file": module_target,
                "symbol": symbol,
                "definition_file": str(definition_file),
                "symbol_confidence": item.get("confidence"),
                "symbol_strategy": item.get("strategy"),
                "symbol_provenance": item.get("provenance"),
            }

    return list(tasks_by_key.values()), exclusions


def compare_states(
    tasks: list[dict[str, Any]],
    baseline: dict[tuple[str, str, Any, str, str], bool],
    candidate: dict[tuple[str, str, Any, str, str], bool],
) -> dict[str, Any]:
    states: Counter[str] = Counter()
    recovered_sources: set[str] = set()
    recovered_symbols: set[tuple[str, str]] = set()
    recovered_confidence: Counter[str] = Counter()
    for task in tasks:
        key = (
            task["source_file"],
            task["import_specifier"],
            task["source_line"],
            task["symbol"],
            task["definition_file"],
        )
        before = baseline[key]
        after = candidate[key]
        if before and after:
            state = "definition_available_both"
        elif after:
            state = "definition_recovered"
            recovered_sources.add(task["source_file"])
            recovered_symbols.add((task["definition_file"], task["symbol"]))
            recovered_confidence[str(task.get("symbol_confidence"))] += 1
        elif before:
            state = "definition_available_baseline_only"
        else:
            state = "definition_available_neither"
        states[state] += 1
    return {
        "states": dict(states),
        "recovered_source_files": len(recovered_sources),
        "recovered_distinct_definition_symbols": len(recovered_symbols),
        "recovered_by_symbol_confidence": dict(recovered_confidence),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-control", required=True, type=Path)
    parser.add_argument("--lost-relationships", required=True, type=Path)
    parser.add_argument("--bundle", required=True, action="append")
    parser.add_argument("--radius", action="append", type=int, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--details-output", type=Path)
    parser.add_argument("--minimum-recovered", type=int, default=1)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-symbol-evidence-audit/v1",
        "status": "running",
    }
    code = 0
    bundles: list[Bundle] = []
    details: list[dict[str, Any]] = []

    try:
        radii = sorted(set(args.radius or [1, 2]))
        graph = json.loads(args.graph_control.read_text(encoding="utf-8"))
        relationships = load_jsonl(args.lost_relationships)
        candidate_tasks, derivation_exclusions = build_symbol_tasks(
            graph, relationships
        )
        if not candidate_tasks:
            raise AuditError("No symbol-definition candidate tasks were derived", 2)

        bundles_by_label: dict[str, Bundle] = {}
        for raw_bundle in args.bundle:
            label, location = parse_bundle_arg(raw_bundle)
            if label in bundles_by_label:
                raise AuditError(f"Duplicate bundle label: {label}", 2)
            if not location.exists():
                raise AuditError(f"Bundle not found for {label}: {location}", 2)
            bundle = Bundle(label, location)
            bundles.append(bundle)
            bundles_by_label[label] = bundle
        for label in ("as_is", "control"):
            if label not in bundles_by_label:
                raise AuditError(f"Required bundle label missing: {label}", 2)

        definition_files = {task["definition_file"] for task in candidate_tasks}
        control_all_text = all_chunk_text(bundles_by_label["control"], definition_files)
        eligible_tasks: list[dict[str, Any]] = []
        pattern_exclusions = 0
        missing_definition_files = 0
        for task in candidate_tasks:
            text = control_all_text.get(task["definition_file"])
            if text is None:
                missing_definition_files += 1
            elif has_definition(text, task["symbol"]):
                eligible_tasks.append(task)
            else:
                pattern_exclusions += 1
        if not eligible_tasks:
            raise AuditError("No symbol tasks have an identifiable definition line")

        tasks_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for task in eligible_tasks:
            tasks_by_source[task["source_file"]].append(task)

        task_key = lambda task: (  # noqa: E731
            task["source_file"],
            task["import_specifier"],
            task["source_line"],
            task["symbol"],
            task["definition_file"],
        )
        availability: dict[int, dict[str, dict[tuple[str, str, Any, str, str], bool]]] = {}
        for radius in radii:
            availability[radius] = {}
            for label, bundle in bundles_by_label.items():
                values: dict[tuple[str, str, Any, str, str], bool] = {}
                for source, source_tasks in tasks_by_source.items():
                    wanted = {task["definition_file"] for task in source_tasks}
                    texts = selected_texts(bundle, source, radius, wanted)
                    for task in source_tasks:
                        values[task_key(task)] = has_definition(
                            texts.get(task["definition_file"], ""), task["symbol"]
                        )
                availability[radius][label] = values

        radius_summaries: dict[str, Any] = {}
        for radius in radii:
            per_bundle = {
                label: sum(values.values())
                for label, values in availability[radius].items()
            }
            comparisons: dict[str, Any] = {}
            for label in bundles_by_label:
                if label == "as_is":
                    continue
                comparisons[f"as_is_to_{label}"] = compare_states(
                    eligible_tasks,
                    availability[radius]["as_is"],
                    availability[radius][label],
                )
            radius_summaries[str(radius)] = {
                "symbol_tasks": len(eligible_tasks),
                "definition_available_by_bundle": per_bundle,
                "comparisons": comparisons,
            }
            for label, comparison in comparisons.items():
                recovered = comparison["states"].get("definition_recovered", 0)
                if recovered < args.minimum_recovered:
                    raise AuditError(
                        f"Radius {radius} {label}: only {recovered} recovered "
                        f"symbol definitions, below {args.minimum_recovered}"
                    )

        for task in eligible_tasks:
            detail = dict(task)
            detail["availability"] = {
                str(radius): {
                    label: availability[radius][label][task_key(task)]
                    for label in bundles_by_label
                }
                for radius in radii
            }
            details.append(detail)

        result.update(
            {
                "status": "passed",
                "graph_control_name": args.graph_control.name,
                "lost_relationships_name": args.lost_relationships.name,
                "radii": radii,
                "task_derivation": {
                    "verified_relationship_rows": sum(
                        row.get("verification_status") == "verified_paths_target"
                        for row in relationships
                    ),
                    "candidate_symbol_tasks": len(candidate_tasks),
                    "eligible_symbol_tasks": len(eligible_tasks),
                    "distinct_source_files": len(tasks_by_source),
                    "distinct_definition_files": len(
                        {task["definition_file"] for task in eligible_tasks}
                    ),
                    "derivation_exclusions": dict(derivation_exclusions),
                    "definition_file_missing_from_control_bundle": missing_definition_files,
                    "definition_pattern_not_identified": pattern_exclusions,
                },
                "bundles": {
                    label: {
                        "name": bundle.location.name,
                        "manifest": bundle.manifest,
                    }
                    for label, bundle in bundles_by_label.items()
                },
                "by_radius": radius_summaries,
                "conclusion": (
                    "Across the eligible imported-symbol tasks, the audit "
                    "counts how often a recognizable declaration/export line "
                    "for the symbol's defining file is present in the chunks "
                    "selected for the importing source. It complements the "
                    "representative answerability tasks and makes no LLM-output claim."
                ),
            }
        )
    except AuditError as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        code = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        code = 1
    finally:
        for bundle in bundles:
            bundle.close()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"SYMBOL_EVIDENCE_AUDIT_STATUS: {result['status']}")
        if result.get("error"):
            print(f"SYMBOL_EVIDENCE_AUDIT_ERROR: {result['error']}")
        derivation = result.get("task_derivation", {})
        if derivation:
            print(
                "SYMBOL_EVIDENCE_TASKS: "
                f"candidate={derivation.get('candidate_symbol_tasks')} "
                f"eligible={derivation.get('eligible_symbol_tasks')} "
                f"sources={derivation.get('distinct_source_files')} "
                f"definition_files={derivation.get('distinct_definition_files')}"
            )
        for radius, summary in result.get("by_radius", {}).items():
            available = summary.get("definition_available_by_bundle", {})
            comparisons = summary.get("comparisons", {})
            recovered = {
                label: value.get("states", {}).get("definition_recovered", 0)
                for label, value in comparisons.items()
            }
            print(
                f"SYMBOL_EVIDENCE radius={radius}: "
                f"available={available} recovered={recovered}"
            )
        print(f"OUTPUT: {args.output}")
    else:
        print(json.dumps(result, indent=2))

    if args.details_output:
        args.details_output.parent.mkdir(parents=True, exist_ok=True)
        with args.details_output.open("w", encoding="utf-8") as handle:
            for row in details:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        print(f"DETAILS_OUTPUT: {args.details_output}")

    return code


if __name__ == "__main__":
    raise SystemExit(main())
