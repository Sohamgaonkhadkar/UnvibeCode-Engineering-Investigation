#!/usr/bin/env python3
"""Validate a file-patched UnvibeCode installation without monkeypatching.

Run this with the interpreter from a disposable venv after
``solution/apply_reference_patch.py``.  It first verifies that both installed
engine files contain the patch marker and that the sibling reference module
is byte-identical to ``solution/tsconfig_jsonc.py``.  It then loads the
patched engines normally and checks, with no in-memory method replacement:

* valid JSONC loads aliases and resolves the configured import on both
  engine copies, with no warning;
* strict JSON and relative imports still work;
* a malformed existing config returns ``{}`` plus a structured warning on
  both resolver copies; and
* with ``--full-pipeline``, the patched Fast Lane exports the alias edge for
  valid JSONC and exactly one graph warning for the malformed config.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPRODUCTION = ROOT / "reproduction"
for path in (ROOT, REPRODUCTION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from causal_intervention import (  # noqa: E402
    COMMENT_STRIPPED_CONFIG,
    EXPECTED_ALIASES,
    EXPECTED_RESOLUTION,
    ORIGINAL_CONFIG,
    RELATIVE_RESOLUTION,
    SOURCE_FILE,
    InterventionError,
    inspect_pipeline_output,
    load_engines,
    probe,
    require,
    run_one_pipeline,
    source_hashes,
    write_fixture,
)

PATCH_MARKER = "UNVIBECODE_JSONC_REFERENCE_PATCH"
REFERENCE_FILENAME = "_unvibecode_tsconfig_jsonc_reference.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def installed_engine_root() -> Path:
    spec = importlib.util.find_spec("shipreadyv2")
    require(spec is not None, "shipreadyv2 package is not installed", 2)
    locations = list(spec.submodule_search_locations or [])
    require(bool(locations), "shipreadyv2 package location could not be determined", 2)
    return Path(locations[0]).resolve() / "engine_sources"


def assert_file_patch() -> dict[str, Any]:
    engine_root = installed_engine_root()
    reference_source = HERE / "tsconfig_jsonc.py"
    reference_installed = engine_root / REFERENCE_FILENAME
    require(reference_installed.is_file(), "Installed reference module is missing", 2)
    require(
        sha256_file(reference_installed) == sha256_file(reference_source),
        "Installed reference module differs from solution/tsconfig_jsonc.py",
        2,
    )

    files: dict[str, Any] = {}
    for pattern in ("00a_*.py", "01_*.py"):
        candidates = sorted(engine_root.glob(pattern))
        require(len(candidates) == 1, f"Expected one engine matching {pattern}", 2)
        path = candidates[0]
        source = path.read_text(encoding="utf-8")
        require(PATCH_MARKER in source, f"Patch marker missing in {path.name}", 2)
        require(
            "_UVC_TSCONFIG_JSONC.load_tsconfig_aliases_result" in source,
            f"Reference loader call missing in {path.name}",
            2,
        )
        require(
            "_UVC_TSCONFIG_JSONC.read_tsconfig_text" in source,
            f"Strict tsconfig reader missing in {path.name}",
            2,
        )
        require(
            "self.warnings.append(resolver.tsconfig_warning)" in source,
            f"Graph-warning insertion missing in {path.name}",
            2,
        )
        files[path.name] = {"sha256": sha256_file(path), "patched": True}
    return {
        "engine_root_name": engine_root.name,
        "reference_module_sha256": sha256_file(reference_installed),
        "files": files,
    }


def expected_probe() -> dict[str, Any]:
    return {
        "aliases": EXPECTED_ALIASES,
        "resolutions": {
            "@app/util": {
                "target": EXPECTED_RESOLUTION[0],
                "strategy": EXPECTED_RESOLUTION[1],
            },
            "./local": {
                "target": RELATIVE_RESOLUTION[0],
                "strategy": RELATIVE_RESOLUTION[1],
            },
            "@app/missing": {"target": None, "strategy": None},
            "@other/util": {"target": None, "strategy": None},
            "external-pkg": {"target": None, "strategy": None},
        },
    }


def validate_resolvers(engines: list[dict[str, Any]], work_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for info in engines:
        engine = info["module"]
        repo = work_root / f"resolver-{info['label']}"
        repo.mkdir(parents=True)
        hashes = write_fixture(repo)
        config = repo / "tsconfig.json"

        observations: dict[str, Any] = {}
        for label, text in (
            ("valid_jsonc", ORIGINAL_CONFIG),
            ("strict_control", COMMENT_STRIPPED_CONFIG),
        ):
            config.write_text(text, encoding="utf-8")
            observed = probe(engine, repo)
            # A second direct instantiation exposes the warning attribute set
            # by the patched method itself; no harness patching is involved.
            resolver = engine.LanguageAwareImportResolver(
                repo, sorted(hashes)
            )
            warning = getattr(resolver, "tsconfig_warning", "missing")
            passed = observed == expected_probe() and warning is None
            observations[label] = {
                "observed": observed,
                "tsconfig_warning": warning,
                "passed": passed,
            }
            require(passed, f"{info['label']} {label} patched-resolver check failed")

        config.write_text('{"compilerOptions": }', encoding="utf-8")
        malformed_resolver = engine.LanguageAwareImportResolver(repo, sorted(hashes))
        malformed_aliases = dict(malformed_resolver.tsconfig_aliases)
        malformed_warning = getattr(malformed_resolver, "tsconfig_warning", None)
        malformed_passed = (
            malformed_aliases == {}
            and isinstance(malformed_warning, dict)
            and malformed_warning.get("code") == "tsconfig_parse_failed"
            and malformed_warning.get("path") == "tsconfig.json"
            and malformed_warning.get("line") == 1
        )
        require(malformed_passed, f"{info['label']} malformed patched-resolver check failed")
        observations["malformed"] = {
            "aliases": malformed_aliases,
            "tsconfig_warning": malformed_warning,
            "passed": malformed_passed,
        }

        # The patched loader deliberately does not reuse the engines'
        # lossy ``errors="ignore"`` source reader for tsconfig.  An existing
        # non-UTF-8 config must be a visible read failure, not an empty one.
        config.write_bytes(b"\xff\xfe{\x00}\x00")
        unreadable_resolver = engine.LanguageAwareImportResolver(repo, sorted(hashes))
        unreadable_aliases = dict(unreadable_resolver.tsconfig_aliases)
        unreadable_warning = getattr(unreadable_resolver, "tsconfig_warning", None)
        unreadable_passed = (
            unreadable_aliases == {}
            and isinstance(unreadable_warning, dict)
            and unreadable_warning.get("code") == "tsconfig_read_failed"
            and unreadable_warning.get("path") == "tsconfig.json"
        )
        require(
            unreadable_passed,
            f"{info['label']} invalid-UTF-8 patched-resolver check failed",
        )
        observations["invalid_utf8"] = {
            "aliases": unreadable_aliases,
            "tsconfig_warning": unreadable_warning,
            "passed": unreadable_passed,
        }

        results.append(
            {
                "engine": info["label"],
                "engine_file": info["file"],
                "engine_sha256_at_load": info["sha256"],
                "source_hashes_unchanged": source_hashes(repo, hashes) == hashes,
                "observations": observations,
                "passed": True,
            }
        )
    return results


def validate_full_pipeline(engine_info: dict[str, Any], work_root: Path) -> dict[str, Any]:
    engine = engine_info["module"]
    repo = work_root / "full-pipeline-repo"
    repo.mkdir(parents=True)
    hashes = write_fixture(repo)
    config = repo / "tsconfig.json"
    outputs = work_root / "full-pipeline-output"

    def observe(label: str, *, restored: bool, expect_warning: bool) -> dict[str, Any]:
        inspected = run_one_pipeline(engine, repo, outputs, label)
        summary = inspected.get("graph_summary", {})
        files = int(summary.get("files_scanned") or 0)
        without_parser = int(summary.get("nodes_without_ast_parser") or 0)
        require(
            not (files and without_parser >= files),
            "Full Fast Lane extraction is environment-blocked",
            2,
        )
        edge_pairs = {
            (row["source"], row["target"])
            for row in inspected["file_edges"]
            if row["source"] == SOURCE_FILE
        }
        expected_pairs = {(SOURCE_FILE, RELATIVE_RESOLUTION[0])}
        if restored:
            expected_pairs.add((SOURCE_FILE, EXPECTED_RESOLUTION[0]))
        selection_files = set(
            inspected.get("selection_optimal", {}).get(
                "effective_files_from_chunks_or_included", []
            )
        )
        warnings = inspected.get("warnings", [])
        if expect_warning:
            warning_passed = (
                len(warnings) == 1
                and isinstance(warnings[0], dict)
                and warnings[0].get("code") == "tsconfig_parse_failed"
                and warnings[0].get("path") == "tsconfig.json"
            )
        else:
            warning_passed = warnings == []
        passed = (
            edge_pairs == expected_pairs
            and (EXPECTED_RESOLUTION[0] in selection_files) == restored
            and warning_passed
            and source_hashes(repo, hashes) == hashes
        )
        require(passed, f"Patched full-pipeline check failed: {label}")
        return {
            "label": label,
            "expected_source_edge_pairs": sorted(expected_pairs),
            "observed_source_edge_pairs": sorted(edge_pairs),
            "graph_warnings": warnings,
            "graph_sha256": inspected.get("graph_sha256"),
            "bundle_sha256": inspected.get("bundle_sha256"),
            "passed": passed,
        }

    config.write_text(ORIGINAL_CONFIG, encoding="utf-8")
    valid = observe("valid-jsonc", restored=True, expect_warning=False)
    config.write_text('{"compilerOptions": }', encoding="utf-8")
    malformed = observe("malformed", restored=False, expect_warning=True)
    return {
        "level": "patched installed Fast Lane run_pipeline; no monkeypatching",
        "valid_jsonc": valid,
        "malformed": malformed,
        "passed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-pipeline", action="store_true")
    parser.add_argument("--expected-version", default="0.3.15")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-jsonc-patched-install-validation/v1",
        "status": "running",
    }
    code = 0
    try:
        try:
            version = importlib.metadata.version("unvibecode")
        except importlib.metadata.PackageNotFoundError as exc:
            raise InterventionError("unvibecode is not installed", 2) from exc
        require(version == args.expected_version, f"Installed version is {version}", 2)
        result["environment"] = {
            "python": sys.version.split()[0],
            "unvibecode_package_version_metadata": version,
        }
        result["file_patch"] = assert_file_patch()
        engines = load_engines()
        with tempfile.TemporaryDirectory(prefix="unvibecode-patched-validation-") as temporary:
            work_root = Path(temporary)
            result["resolver_checks"] = validate_resolvers(engines, work_root)
            if args.full_pipeline:
                result["full_pipeline"] = validate_full_pipeline(engines[0], work_root)
        result["status"] = "passed"
        result["conclusion"] = (
            "The exact reference module and file-level engine/builder changes "
            "work in a normally loaded patched installation, without the "
            "investigation harness monkeypatching any method."
        )
    except InterventionError as exc:
        result["status"] = "environment_blocked" if exc.code == 2 else "failed"
        result["error"] = str(exc)
        code = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        code = 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"PATCHED_INSTALL_VALIDATION_STATUS: {result['status']}")
        if result.get("error"):
            print(f"PATCHED_INSTALL_VALIDATION_ERROR: {result['error']}")
        for row in result.get("resolver_checks", []):
            print(f"PATCHED_RESOLVER {row['engine']}: passed")
        if "full_pipeline" in result:
            print("PATCHED_FULL_PIPELINE: passed")
        print(f"OUTPUT: {args.output}")
    else:
        print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
