#!/usr/bin/env python3
"""Audit concentration and spread in the *verified recovered-edge subgraph*.

The headline Lexical/ng-matero counts are import instances whose expected
``paths`` targets were verified independently.  A fair reviewer should ask
whether those instances are mostly repeated source→target pairs, and how
concentrated they are in a few barrel/hub files.  This script answers that
question from the committed relationship and direct-selection-omission JSONL
files only.

It deliberately does **not** claim to reconstruct the whole repository graph:
edges that already resolved as-is are not inputs.  All topology language here
therefore refers to the verified recovered subgraph—the edges absent as-is
and restored in the strict-JSON control.

Outputs use distinct source→target pairs as the primary basis.  Import-
instance counts are retained as a secondary view so duplicate pair instances
cannot silently inflate the pair-level conclusion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVIDENCE = ROOT / "evidence" / "tsconfig-jsonc"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def area(path: str) -> str:
    """Return the repository area used only for spread accounting.

    Lexical is a package monorepo, so ``packages/<name>`` is the natural
    boundary.  ng-matero is an application tree, so the first component under
    ``src/app`` (and ``src/environments``) is more informative than treating
    the whole ``src`` tree as one area.
    """

    parts = Path(path).parts
    if len(parts) >= 2 and parts[0] == "packages":
        return f"packages/{parts[1]}"
    if len(parts) >= 3 and parts[:2] == ("src", "app"):
        return f"src/app/{parts[2]}"
    if len(parts) >= 2 and parts[:2] == ("src", "environments"):
        return "src/environments"
    return parts[0] if parts else ""


def percentile(values: Iterable[int], fraction: float) -> int:
    """Nearest-rank percentile for a non-empty degree multiset."""

    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    index = min(len(ordered) - 1, max(0, int(fraction * len(ordered))))
    return ordered[index]


def degree_summary(counter: Counter[str]) -> dict[str, float | int]:
    values = list(counter.values())
    return {
        "nodes": len(values),
        "min": min(values),
        "p50_median": statistics.median(values),
        "p90_nearest_rank": percentile(values, 0.90),
        "p95_nearest_rank": percentile(values, 0.95),
        "p99_nearest_rank": percentile(values, 0.99),
        "max": max(values),
        "mean": round(statistics.fmean(values), 6),
    }


def ranked(counter: Counter[Any]) -> list[tuple[Any, int]]:
    """Rank by descending count, then key, so ties are deterministic."""

    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def top_share(counter: Counter[str], total: int, k: int) -> float:
    return round(sum(value for _, value in ranked(counter)[:k]) / total, 6)


def analyze_dataset(
    *,
    label: str,
    relationships_path: Path,
    selections_path: Path,
) -> dict[str, Any]:
    relationships = load_jsonl(relationships_path)
    selection_rows = load_jsonl(selections_path)
    failures: list[str] = []

    if not relationships:
        failures.append("relationship input is empty")
    unverified = [
        row
        for row in relationships
        if row.get("verification_status") != "verified_paths_target"
    ]
    if unverified:
        failures.append(f"{len(unverified)} relationship rows are not verified")

    instance_pairs = [
        (str(row["source_file"]), str(row["target_file"])) for row in relationships
    ]
    distinct_pairs = set(instance_pairs)
    if any(source == target for source, target in distinct_pairs):
        failures.append("recovered subgraph unexpectedly contains a self-edge")

    instance_source_degree = Counter(source for source, _ in instance_pairs)
    instance_target_degree = Counter(target for _, target in instance_pairs)
    pair_source_degree = Counter(source for source, _ in distinct_pairs)
    pair_target_degree = Counter(target for _, target in distinct_pairs)

    pair_total = len(distinct_pairs)
    squared_share_sum = (
        sum((value / pair_total) ** 2 for value in pair_target_degree.values())
        if pair_total
        else 0.0
    )

    area_pairs = Counter(
        (area(source), area(target)) for source, target in distinct_pairs
    )
    cross_area_pairs = sum(
        value for (source_area, target_area), value in area_pairs.items()
        if source_area != target_area
    )

    selection_by_radius: dict[str, Any] = {}
    all_selection_pairs: set[tuple[str, str]] = set()
    radii = sorted({row.get("radius") for row in selection_rows})
    for radius in radii:
        rows = [row for row in selection_rows if row.get("radius") == radius]
        pairs = {
            (str(row["source_file"]), str(row["missing_implementation_file"]))
            for row in rows
        }
        all_selection_pairs.update(pairs)
        outside = pairs - distinct_pairs
        if outside:
            failures.append(
                f"radius {radius} has {len(outside)} selection pairs outside "
                "the verified recovered subgraph"
            )
        selection_by_radius[str(radius)] = {
            "selection_omission_rows": len(rows),
            "distinct_recovered_pairs": len(pairs),
            "distinct_source_files": len({source for source, _ in pairs}),
            "distinct_target_files": len({target for _, target in pairs}),
            "verified_pair_coverage": round(len(pairs & distinct_pairs) / pair_total, 6)
            if pair_total
            else 0.0,
            "pairs_outside_verified_subgraph": len(outside),
        }

    outside_all = all_selection_pairs - distinct_pairs
    if outside_all:
        failures.append(
            f"{len(outside_all)} any-scope selection pairs are outside the "
            "verified recovered subgraph"
        )

    patterns = Counter(str(row.get("tsconfig_pattern")) for row in relationships)

    return {
        "label": label,
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "inputs": {
            "relationships": {
                "path": relative(relationships_path),
                "sha256": sha256(relationships_path),
                "rows": len(relationships),
            },
            "direct_selection_omissions": {
                "path": relative(selections_path),
                "sha256": sha256(selections_path),
                "rows": len(selection_rows),
            },
        },
        "recovered_subgraph": {
            "import_instances": len(instance_pairs),
            "distinct_source_target_pairs": pair_total,
            "duplicate_pair_instances_beyond_first": len(instance_pairs) - pair_total,
            "distinct_pair_retention_of_instances": round(
                pair_total / len(instance_pairs), 6
            )
            if instance_pairs
            else 0.0,
            "distinct_source_files": len(pair_source_degree),
            "distinct_target_files": len(pair_target_degree),
            "distinct_tsconfig_patterns": len(patterns),
        },
        "degree_on_distinct_pairs": {
            "source_out_degree": degree_summary(pair_source_degree),
            "target_in_degree": degree_summary(pair_target_degree),
        },
        "degree_on_import_instances": {
            "source_out_degree": degree_summary(instance_source_degree),
            "target_in_degree": degree_summary(instance_target_degree),
        },
        "target_concentration_on_distinct_pairs": {
            "top_1_share": top_share(pair_target_degree, pair_total, 1) if pair_total else 0.0,
            "top_5_share": top_share(pair_target_degree, pair_total, 5) if pair_total else 0.0,
            "top_10_share": top_share(pair_target_degree, pair_total, 10) if pair_total else 0.0,
            "sum_of_squared_target_shares": round(squared_share_sum, 6),
            "effective_target_count_reciprocal_squared_shares": round(
                1.0 / squared_share_sum, 6
            )
            if squared_share_sum
            else 0.0,
            "top_targets": [
                {
                    "target_file": target,
                    "distinct_source_files": pair_target_degree[target],
                    "import_instances": instance_target_degree[target],
                    "distinct_pair_share": round(pair_target_degree[target] / pair_total, 6)
                    if pair_total
                    else 0.0,
                }
                for target, _ in ranked(pair_target_degree)[:10]
            ],
        },
        "area_spread_on_distinct_pairs": {
            "distinct_source_areas": len({area(source) for source, _ in distinct_pairs}),
            "distinct_target_areas": len({area(target) for _, target in distinct_pairs}),
            "distinct_source_target_area_pairs": len(area_pairs),
            "cross_area_pairs": cross_area_pairs,
            "cross_area_share": round(cross_area_pairs / pair_total, 6) if pair_total else 0.0,
            "top_area_pairs": [
                {
                    "source_area": source_area,
                    "target_area": target_area,
                    "distinct_source_target_pairs": value,
                }
                for (source_area, target_area), value in ranked(area_pairs)[:10]
            ],
        },
        "direct_selection_recovery_overlay": {
            "by_radius": selection_by_radius,
            "any_scope": {
                "distinct_recovered_pairs": len(all_selection_pairs),
                "distinct_source_files": len(
                    {source for source, _ in all_selection_pairs}
                ),
                "distinct_target_files": len(
                    {target for _, target in all_selection_pairs}
                ),
                "verified_pair_coverage": round(
                    len(all_selection_pairs & distinct_pairs) / pair_total, 6
                )
                if pair_total
                else 0.0,
                "pairs_outside_verified_subgraph": len(outside_all),
            },
        },
        "top_tsconfig_patterns_by_import_instance": [
            {"pattern": pattern, "import_instances": value}
            for pattern, value in ranked(patterns)[:10]
        ],
    }


def build_report() -> dict[str, Any]:
    datasets = [
        analyze_dataset(
            label="Lexical",
            relationships_path=EVIDENCE / "lost_relationships.jsonl",
            selections_path=EVIDENCE / "direct_selection_omissions.jsonl",
        ),
        analyze_dataset(
            label="ng-matero",
            relationships_path=EVIDENCE / "ng-matero" / "lost_relationships.jsonl",
            selections_path=EVIDENCE
            / "ng-matero"
            / "direct_selection_omissions.jsonl",
        ),
    ]
    return {
        "schema_version": 1,
        "status": "passed"
        if all(dataset["status"] == "passed" for dataset in datasets)
        else "failed",
        "method": {
            "primary_basis": "distinct source→target pairs in the verified recovered subgraph",
            "secondary_basis": "individual verified import instances",
            "area_definition": (
                "packages/<package> for Lexical; src/app/<area> or "
                "src/environments for ng-matero; otherwise the first path "
                "component"
            ),
            "concentration_metric": (
                "sum of squared distinct-pair target shares; its reciprocal "
                "is reported as an effective target count"
            ),
            "selection_overlay": (
                "committed direct-selection omission pairs by exported "
                "Connected Code radius, checked as a subset of the verified "
                "recovered subgraph"
            ),
        },
        "datasets": datasets,
        "limits": [
            "This is not a whole-repository graph reconstruction; already-resolved edges are not inputs.",
            "Distinct pairs remove duplicate-pair inflation but do not make hub/barrel targets independent questions or independent user impact.",
            "Area spread is descriptive repository accounting, not a prevalence or user-impact estimate.",
            "Selection coverage is limited to the exported bundle selections and radii already committed as evidence.",
        ],
        "conclusion": (
            "The recovered-edge counts are highly hub-concentrated, but distinct-pair "
            "accounting separates that concentration from duplicate-pair inflation and "
            "shows how widely the affected sources and repository areas are spread."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=EVIDENCE / "relationship_concentration_audit.json",
    )
    args = parser.parse_args()

    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"RELATIONSHIP_CONCENTRATION_STATUS: {report['status']}")
    for dataset in report["datasets"]:
        graph = dataset["recovered_subgraph"]
        concentration = dataset["target_concentration_on_distinct_pairs"]
        print(
            f"RELATIONSHIP_CONCENTRATION {dataset['label']}: "
            f"instances={graph['import_instances']} "
            f"distinct_pairs={graph['distinct_source_target_pairs']} "
            f"sources={graph['distinct_source_files']} "
            f"targets={graph['distinct_target_files']} "
            f"top10_target_share={concentration['top_10_share']}"
        )
    print(f"OUTPUT: {args.output.resolve()}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
