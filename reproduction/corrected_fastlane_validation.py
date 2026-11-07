#!/usr/bin/env python3
"""Run one corrected Fast Lane pipeline on an unmodified repository.

This generic companion to ``causal_intervention.py`` is used for the
ng-matero clean-environment workflow.  It loads the installed Fast Lane
engine, applies the reference loader and builder-warning integration **in
memory only**, and asserts that:

* the repository's original ``tsconfig.json`` bytes do not change;
* an optional representative source file does not change;
* the stock installed loader object is restored afterwards;
* the exported graph has the expected file/edge counts and no tsconfig
  warning for the valid original JSONC; and
* every verified relationship in the supplied JSONL is present.

It does not modify the installed package or target repository.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from causal_intervention import (  # noqa: E402
    InterventionError,
    inspect_pipeline_output,
    load_engines,
    reference_graph_integration,
    require,
    run_one_pipeline,
    sha256_file,
)


def load_relationships(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--lost-relationships", required=True, type=Path)
    parser.add_argument("--expected-config-sha256", required=True)
    parser.add_argument("--expected-files", required=True, type=int)
    parser.add_argument("--expected-edges", required=True, type=int)
    parser.add_argument(
        "--selection-source",
        default="src/app/app.config.ts",
        help="source file whose Optimal selection should be inspected",
    )
    parser.add_argument(
        "--representative-source",
        default="src/app/app.config.ts",
        help="source file whose hash must remain unchanged (empty to skip)",
    )
    parser.add_argument("--expected-version", default="0.3.15")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-corrected-fastlane-validation/v1",
        "status": "running",
    }
    code = 0
    try:
        try:
            version = importlib.metadata.version("unvibecode")
        except importlib.metadata.PackageNotFoundError as exc:
            raise InterventionError("unvibecode is not installed", 2) from exc
        require(version == args.expected_version, f"Installed version is {version}", 2)

        repository = args.repository.resolve()
        config = repository / "tsconfig.json"
        require(config.is_file(), f"Root tsconfig.json not found: {config}", 2)
        config_before = sha256_file(config)
        require(
            config_before == args.expected_config_sha256,
            "Original tsconfig hash does not match the pinned evidence hash",
        )

        representative = args.representative_source.strip()
        representative_before: str | None = None
        if representative:
            path = repository / representative
            require(path.is_file(), f"Representative source not found: {path}", 2)
            representative_before = sha256_file(path)

        engines = load_engines()
        engine_info = engines[0]
        engine = engine_info["module"]
        stock_method = engine.LanguageAwareImportResolver.__dict__[
            "_load_tsconfig_aliases"
        ]

        output_root = args.output_root.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        with reference_graph_integration(engine):
            initial = run_one_pipeline(
                engine, repository, output_root, "corrected"
            )
            candidates = sorted(
                (output_root / "corrected").rglob("shipreadyv2_resolved_graph.json")
            )
            require(
                len(candidates) == 1,
                f"Expected exactly one corrected resolved graph, found {len(candidates)}",
                2,
            )
            inspected = inspect_pipeline_output(
                candidates[0], args.selection_source
            )
            require(
                inspected.get("graph_sha256") == initial.get("graph_sha256"),
                "Re-inspected corrected graph differs from the produced graph",
            )

        require(
            engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"]
            is stock_method,
            "Installed stock loader object was not restored after the run",
        )
        require(sha256_file(config) == config_before, "Repository tsconfig changed")
        if representative:
            require(
                sha256_file(repository / representative) == representative_before,
                "Representative source changed",
            )

        summary = inspected["graph_summary"]
        require(
            summary.get("files_scanned") == args.expected_files,
            f"Corrected files_scanned={summary.get('files_scanned')}, "
            f"expected {args.expected_files}",
        )
        require(
            summary.get("edges") == args.expected_edges,
            f"Corrected edges={summary.get('edges')}, expected {args.expected_edges}",
        )
        require(
            inspected.get("warnings") == [],
            "Corrected valid-JSONC graph unexpectedly contains warnings",
        )
        require(
            int(summary.get("nodes_without_ast_parser") or 0)
            < int(summary.get("files_scanned") or 0),
            "Full pipeline extraction is environment-blocked",
            2,
        )

        corrected_edges = {
            (row["source"], row["target"], row["raw"], row["line"])
            for row in inspected["file_edges"]
        }
        relationships = load_relationships(args.lost_relationships)
        verified = [
            row
            for row in relationships
            if row.get("verification_status") == "verified_paths_target"
        ]
        require(bool(verified), "No verified relationships were supplied", 2)
        missing = [
            row
            for row in verified
            if (
                row["source_file"],
                row["target_file"],
                row["import_specifier"],
                row.get("source_line"),
            )
            not in corrected_edges
        ]
        require(
            not missing,
            f"Corrected graph is missing {len(missing)} verified relationships",
        )

        result.update(
            {
                "status": "passed",
                "environment": {
                    "python": sys.version.split()[0],
                    "unvibecode": version,
                },
                "engine": {
                    "label": engine_info["label"],
                    "file": engine_info["file"],
                    "sha256": engine_info["sha256"],
                },
                "repository_name": repository.name,
                "tsconfig_sha256_before": config_before,
                "tsconfig_sha256_after": sha256_file(config),
                "representative_source": representative or None,
                "representative_source_sha256_before": representative_before,
                "representative_source_sha256_after": (
                    sha256_file(repository / representative)
                    if representative
                    else None
                ),
                "loader_restored_after_run": True,
                "graph_summary": summary,
                "graph_sha256": inspected["graph_sha256"],
                "bundle_sha256": inspected.get("bundle_sha256"),
                "graph_warnings": inspected.get("warnings", []),
                "verified_relationships_checked": len(verified),
                "verified_relationships_present": len(verified) - len(missing),
                "selection_source": args.selection_source,
                "selection_optimal": inspected.get("selection_optimal", {}),
                "conclusion": (
                    "The reference loader, applied only in memory to the "
                    "installed Fast Lane engine, restores the verified graph "
                    "on the repository's original JSONC bytes and leaves the "
                    "target repository and stock loader object restored."
                ),
            }
        )
    except InterventionError as exc:
        result["status"] = "environment_blocked" if exc.code == 2 else "failed"
        result["error"] = str(exc)
        code = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        code = 1

    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"CORRECTED_FASTLANE_VALIDATION_STATUS: {result['status']}")
        if result.get("error"):
            print(f"CORRECTED_FASTLANE_VALIDATION_ERROR: {result['error']}")
        if result.get("status") == "passed":
            print(
                "CORRECTED_FASTLANE: "
                f"files={result['graph_summary'].get('files_scanned')} "
                f"edges={result['graph_summary'].get('edges')} "
                f"verified={result['verified_relationships_present']}/"
                f"{result['verified_relationships_checked']}"
            )
        print(f"OUTPUT: {args.output}")
    else:
        print(rendered, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
