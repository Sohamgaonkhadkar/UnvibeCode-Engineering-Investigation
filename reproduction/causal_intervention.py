#!/usr/bin/env python3
"""Reversible causal intervention for the JSONC tsconfig alias defect.

The default run is deliberately lightweight and uses the resolver classes from
both engine copies shipped in the installed UnvibeCode 0.3.15 wheel:

    A  original JSONC config, stock loader       -> alias resolution fails
    B  only the comments removed, stock loader   -> alias resolution returns
    C  exact original config restored            -> failure returns
    D  original config + reference loader patched -> alias resolution returns
       in memory only
    E  stock loader restored                      -> failure returns

It also runs targeted boundary checks (valid fixtures on both engines,
string-literal preservation, no-alias normality, explicit parser errors plus
product-style warnings for malformed input, and no unrelated resolutions).

``--full-pipeline`` additionally performs A-E through the installed Fast Lane
``run_pipeline()`` on the same temporary minimal repository and inspects the
actual resolved graph and complete-repository-context ZIP.  That mode needs a
working tree-sitter environment; if extraction is unavailable it exits 2 and
labels the result environment-blocked rather than treating it as evidence.

``--lexical-root`` runs one in-memory-corrected Fast Lane pipeline against an
unmodified lexical checkout and checks the graph and ReactExtension Optimal
selection.  It never writes to the lexical checkout.

Examples:
    python -m pip install unvibecode==0.3.15
    python reproduction/causal_intervention.py --output causal.json
    python reproduction/causal_intervention.py --full-pipeline --keep-work
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable, Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solution.tsconfig_jsonc import (  # noqa: E402
    JsoncSyntaxError,
    TsconfigLoadError,
    aliases_from_config_data,
    load_tsconfig_aliases_result,
    parse_jsonc,
)

EVIDENCE = ROOT / "evidence" / "tsconfig-jsonc"
EXPECTED_VERSION = "0.3.15"
EXPECTED_ALIASES = {"@app": "src/app"}
EXPECTED_RESOLUTION = ("src/app/util.ts", "node_ts_module_resolution")
RELATIVE_RESOLUTION = ("src/feature/local.ts", "node_ts_module_resolution")
SOURCE_FILE = "src/feature/comp.ts"
SPECIFIERS = ("@app/util", "./local", "@app/missing", "@other/util", "external-pkg")

ORIGINAL_CONFIG = """{
  // Reversible-intervention fixture.
  "x-note": "literal text, not syntax: // /* */ ,",
  "compilerOptions": {
    "baseUrl": ".", /* custom aliases are declared below */
    "paths": {
      "@app/*": ["src/app/*"]
    }
  }
}
"""

# The same bytes with only the two comments removed.  The string literal and
# every semantic value are unchanged; there are deliberately no trailing
# commas in this A/B/C intervention, because step B removes comments only.
COMMENT_STRIPPED_CONFIG = """{

  "x-note": "literal text, not syntax: // /* */ ,",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@app/*": ["src/app/*"]
    }
  }
}
"""

SOURCE_FILES = {
    "src/app/util.ts": "export function util(): number { return 1; }\n",
    # A second definition of the same exported name prevents a unique-symbol
    # fallback from masking the missing file relationship in full-output runs.
    "src/duplicate/util.ts": "export function util(): number { return 99; }\n",
    "src/feature/local.ts": "export function localValue(): number { return 2; }\n",
    SOURCE_FILE: """import { util } from "@app/util";
import { localValue } from "./local";
import { missingValue } from "@app/missing";
import { notConfiguredValue } from "@other/util";
import { externalValue } from "external-pkg";

export function comp(): number {
  return util() + localValue() + missingValue() + notConfiguredValue() + externalValue();
}
""",
}

STRING_FIXTURE_NOTES = {
    "minimal_stringsafety": "docs at https://example.com/a/*not-a-comment*/,",
    "minimal_combined_jsonc": "literal text, not syntax: // /* */ ,",
}


class InterventionError(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def require(condition: bool, message: str, code: int = 1) -> None:
    if not condition:
        raise InterventionError(message, code)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_hashes(root: Path, relative_paths: Iterable[str]) -> dict[str, str]:
    return {rel: sha256_file(root / rel) for rel in relative_paths}


def load_engine(label: str, pattern: str) -> tuple[Any, Path]:
    shipreadyv2 = importlib.import_module("shipreadyv2")
    engine_root = Path(shipreadyv2.__file__).resolve().parent / "engine_sources"
    candidates = sorted(engine_root.glob(pattern))
    require(bool(candidates), f"Installed engine matching {pattern} was not found", 2)
    engine_path = candidates[0]
    module_name = f"unvibecode_causal_{label}"
    spec = importlib.util.spec_from_file_location(module_name, engine_path)
    require(spec is not None and spec.loader is not None, f"Cannot load {engine_path.name}", 2)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, engine_path


def load_engines() -> list[dict[str, Any]]:
    engines = []
    for label, pattern in (
        ("fast_lane_00a", "00a_*.py"),
        ("merged_graph_01", "01_*.py"),
    ):
        module, path = load_engine(label, pattern)
        engines.append(
            {
                "label": label,
                "module": module,
                "file": path.name,
                "sha256": sha256_file(path),
            }
        )
    return engines


@contextlib.contextmanager
def corrected_loader(engine: Any):
    """Temporarily replace one resolver method in memory; always restore it."""
    resolver_class = engine.LanguageAwareImportResolver
    original = resolver_class.__dict__["_load_tsconfig_aliases"]

    def reference_loader(self):  # noqa: ANN001 - mirrors the shipped method
        result = load_tsconfig_aliases_result(
            self.workspace_root,
            engine.safe_read_text,
            engine.to_posix_rel,
        )
        # Product integration would copy this structured record into the
        # graph builder's existing ``warnings`` list after constructing the
        # resolver.  Keeping it on the instance lets this harness assert the
        # exact degraded-input behaviour without modifying the package.
        self.tsconfig_warning = (
            result.warning.as_dict() if result.warning is not None else None
        )
        return result.aliases

    resolver_class._load_tsconfig_aliases = reference_loader
    try:
        yield
    finally:
        resolver_class._load_tsconfig_aliases = original


@contextlib.contextmanager
def reference_graph_integration(engine: Any):
    """Apply the reference loader and builder-warning integration in memory.

    This mirrors the proposed production change without modifying installed
    files: the resolver records ``tsconfig_warning`` while loading aliases,
    and the active graph builder's existing ``warnings`` list receives that
    structured record during ``build()``.  All patched methods are restored.
    """

    resolver_class = engine.LanguageAwareImportResolver
    builder_class = engine.ShipReadyV2DeepGraphBuilder
    original_resolver_init = resolver_class.__dict__["__init__"]
    original_builder_build = builder_class.__dict__["build"]
    active_warnings: list[dict[str, Any]] | None = None

    def reference_resolver_init(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        original_resolver_init(self, *args, **kwargs)
        warning = getattr(self, "tsconfig_warning", None)
        if (
            isinstance(warning, dict)
            and active_warnings is not None
            and warning not in active_warnings
        ):
            active_warnings.append(warning)

    def reference_builder_build(self):  # noqa: ANN001
        nonlocal active_warnings
        previous = active_warnings
        active_warnings = self.warnings
        try:
            return original_builder_build(self)
        finally:
            active_warnings = previous

    with corrected_loader(engine):
        resolver_class.__init__ = reference_resolver_init
        builder_class.build = reference_builder_build
        try:
            yield
        finally:
            resolver_class.__init__ = original_resolver_init
            builder_class.build = original_builder_build


def resolver_is_corrected(engine: Any, stock_method: Callable) -> bool:
    return engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"] is not stock_method


def source_file_list(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx"}
    )


def probe(engine: Any, root: Path, specifiers: Iterable[str] = SPECIFIERS) -> dict[str, Any]:
    resolver = engine.LanguageAwareImportResolver(root, source_file_list(root))
    resolutions = {}
    for specifier in specifiers:
        target, strategy = resolver._resolve_node_ts(SOURCE_FILE, specifier)
        resolutions[specifier] = {"target": target, "strategy": strategy}
    return {
        "aliases": dict(resolver.tsconfig_aliases),
        "resolutions": resolutions,
    }


def expected_probe(restored: bool) -> dict[str, Any]:
    return {
        "aliases": EXPECTED_ALIASES if restored else {},
        "resolutions": {
            "@app/util": {
                "target": EXPECTED_RESOLUTION[0] if restored else None,
                "strategy": EXPECTED_RESOLUTION[1] if restored else None,
            },
            "./local": {"target": RELATIVE_RESOLUTION[0], "strategy": RELATIVE_RESOLUTION[1]},
            "@app/missing": {"target": None, "strategy": None},
            "@other/util": {"target": None, "strategy": None},
            "external-pkg": {"target": None, "strategy": None},
        },
    }


def write_fixture(root: Path) -> dict[str, str]:
    for relative, content in SOURCE_FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return source_hashes(root, SOURCE_FILES)


def run_unit_sequence(engine_info: dict[str, Any], work_root: Path) -> dict[str, Any]:
    engine = engine_info["module"]
    repo = work_root / f"unit-{engine_info['label']}"
    repo.mkdir(parents=True)
    hashes_before = write_fixture(repo)
    stock_method = engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"]
    steps: list[dict[str, Any]] = []

    def observe(step: str, description: str, restored: bool, patched: bool) -> None:
        observed = probe(engine, repo)
        expected = expected_probe(restored)
        current_hashes = source_hashes(repo, SOURCE_FILES)
        passed = observed == expected and current_hashes == hashes_before
        steps.append(
            {
                "step": step,
                "description": description,
                "loader": "in_memory_reference_solution" if patched else "stock",
                "loader_patched_during_probe": resolver_is_corrected(engine, stock_method),
                "tsconfig_sha256": sha256_file(repo / "tsconfig.json"),
                "source_hashes_unchanged": current_hashes == hashes_before,
                "observed": observed,
                "expected": expected,
                "passed": passed,
            }
        )
        require(passed, f"{engine_info['label']} step {step} did not match expectations")

    config_path = repo / "tsconfig.json"
    config_path.write_text(ORIGINAL_CONFIG, encoding="utf-8")
    observe("A", "original valid JSONC, stock loader", False, False)

    config_path.write_text(COMMENT_STRIPPED_CONFIG, encoding="utf-8")
    observe("B", "only comments removed, stock loader", True, False)

    config_path.write_text(ORIGINAL_CONFIG, encoding="utf-8")
    observe("C", "exact original JSONC restored, stock loader", False, False)

    with corrected_loader(engine):
        observe("D", "original JSONC, reference loader patched in memory", True, True)
    require(
        engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"] is stock_method,
        f"{engine_info['label']} stock loader was not restored after step D",
    )
    observe("E", "correction removed and stock loader restored", False, False)

    return {
        "engine": engine_info["label"],
        "engine_file": engine_info["file"],
        "engine_sha256": engine_info["sha256"],
        "source_hashes": hashes_before,
        "config_hashes": {
            "original_jsonc": sha256_bytes(ORIGINAL_CONFIG.encode()),
            "comments_removed": sha256_bytes(COMMENT_STRIPPED_CONFIG.encode()),
        },
        "steps": steps,
        "passed": True,
    }


def check_existing_fixtures(engines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    alias_fixtures = (
        "minimal_strict",
        "minimal_jsonc",
        "minimal_blockcomment",
        "minimal_trailingcomma",
        "minimal_stringsafety",
        "minimal_combined_jsonc",
    )
    for info in engines:
        engine = info["module"]
        for fixture in (*alias_fixtures, "minimal_noalias"):
            root = (HERE / fixture).resolve()
            stock = probe(engine, root, ("@app/util", "./local"))
            with corrected_loader(engine):
                corrected = probe(engine, root, ("@app/util", "./local"))

            if fixture == "minimal_noalias":
                stock_ok = stock["aliases"] == {} and stock["resolutions"]["@app/util"]["target"] is None
                corrected_ok = (
                    corrected["aliases"] == {}
                    and corrected["resolutions"]["@app/util"]["target"] is None
                    and corrected["resolutions"]["./local"]["target"] == RELATIVE_RESOLUTION[0]
                )
            else:
                stock_ok = (
                    stock == {
                        "aliases": EXPECTED_ALIASES,
                        "resolutions": {
                            "@app/util": {"target": EXPECTED_RESOLUTION[0], "strategy": EXPECTED_RESOLUTION[1]},
                            "./local": {"target": None, "strategy": None},
                        },
                    }
                    if fixture == "minimal_strict"
                    else stock["aliases"] == {} and stock["resolutions"]["@app/util"]["target"] is None
                )
                corrected_ok = (
                    corrected["aliases"] == EXPECTED_ALIASES
                    and corrected["resolutions"]["@app/util"]
                    == {"target": EXPECTED_RESOLUTION[0], "strategy": EXPECTED_RESOLUTION[1]}
                )

            note_ok = True
            if fixture in STRING_FIXTURE_NOTES:
                parsed = parse_jsonc((root / "tsconfig.json").read_text(encoding="utf-8"))
                note_ok = parsed.get("x-note") == STRING_FIXTURE_NOTES[fixture]

            passed = stock_ok and corrected_ok and note_ok
            checks.append(
                {
                    "engine": info["label"],
                    "fixture": fixture,
                    "stock": stock,
                    "corrected": corrected,
                    "string_literal_preserved": note_ok if fixture in STRING_FIXTURE_NOTES else None,
                    "passed": passed,
                }
            )
            require(passed, f"Existing-fixture boundary check failed: {info['label']}/{fixture}")
    return checks


def check_parser_boundaries(engines: list[dict[str, Any]], work_root: Path) -> dict[str, Any]:
    inline = r"""{
  // valid comment
  "x-note": "quote: \" slash: \\ comment-looking: // /* */ closers: ,]} ",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {"@app/*": ["src/app/*",],},
  },
}
"""
    parsed_inline = parse_jsonc(inline)
    expected_note = 'quote: " slash: \\ comment-looking: // /* */ closers: ,]} '
    require(parsed_inline.get("x-note") == expected_note, "Inline string literal was not preserved")
    require(
        parsed_inline["compilerOptions"]["paths"] == {"@app/*": ["src/app/*"]},
        "Inline JSONC paths were not parsed as expected",
    )

    semantic_pairs = []
    for original_name, control_name in (
        ("lexical_tsconfig_original.jsonc", "lexical_tsconfig_control.json"),
        ("ng-matero/tsconfig_as_is.json", "ng-matero/tsconfig_control.json"),
    ):
        original = EVIDENCE / original_name
        control = EVIDENCE / control_name
        equal = parse_jsonc(original.read_text(encoding="utf-8")) == json.loads(
            control.read_text(encoding="utf-8")
        )
        semantic_pairs.append(
            {
                "original": original_name,
                "control": control_name,
                "original_sha256": sha256_file(original),
                "control_sha256": sha256_file(control),
                "semantically_equal_after_tolerant_parse": equal,
            }
        )
        require(equal, f"Committed config pair is not semantically equal: {original_name}")

    malformed = {
        "missing_value": '{"compilerOptions": }',
        "missing_closing_brace": '{"compilerOptions": {"paths": {}}',
        "extra_token_after_root": '{"compilerOptions":{}} nope',
        "unterminated_string": '{"x-note":"abc}',
        "unterminated_block_comment": '{"compilerOptions":{}} /*',
        "root_not_object": "[]",
    }
    malformed_results = []
    boundary_root = work_root / "malformed"
    boundary_root.mkdir(parents=True)
    write_fixture(boundary_root)
    for name, text in malformed.items():
        parse_error = None
        try:
            parsed = parse_jsonc(text)
            # A syntactically valid non-object JSON value is still not a
            # successful tsconfig for the reference loader.
            aliases_from_config_data(parsed, lambda value: Path(value).as_posix())
        except TsconfigLoadError as exc:
            parse_error = str(exc)
        require(parse_error is not None, f"Reference parser accepted malformed case {name}")

        (boundary_root / "tsconfig.json").write_text(text, encoding="utf-8")
        per_engine = {}
        for info in engines:
            engine = info["module"]
            stock_resolver = engine.LanguageAwareImportResolver(
                boundary_root, source_file_list(boundary_root)
            )
            stock_aliases = dict(stock_resolver.tsconfig_aliases)
            stock_warning = getattr(stock_resolver, "tsconfig_warning", None)

            with corrected_loader(engine):
                corrected_resolver = engine.LanguageAwareImportResolver(
                    boundary_root, source_file_list(boundary_root)
                )
            corrected_aliases = dict(corrected_resolver.tsconfig_aliases)
            corrected_warning = getattr(corrected_resolver, "tsconfig_warning", None)
            require(
                stock_aliases == {}
                and stock_warning is None
                and corrected_aliases == {}
                and isinstance(corrected_warning, dict)
                and corrected_warning.get("code")
                in {"tsconfig_parse_failed", "tsconfig_invalid_shape"},
                f"Malformed handling mismatch for {name}/{info['label']}",
            )
            per_engine[info["label"]] = {
                "stock_aliases": stock_aliases,
                "stock_warning": stock_warning,
                "stock_silently_empty": True,
                "corrected_aliases": corrected_aliases,
                "corrected_warning": corrected_warning,
            }
        malformed_results.append(
            {"case": name, "parser_error": parse_error, "engines": per_engine, "passed": True}
        )

    missing_root = work_root / "missing-config"
    missing_root.mkdir()
    write_fixture(missing_root)
    missing_results = {}
    for info in engines:
        engine = info["module"]
        with corrected_loader(engine):
            result = probe(engine, missing_root, ("@app/util", "./local"))
        passed = result["aliases"] == {} and result["resolutions"]["./local"]["target"] == RELATIVE_RESOLUTION[0]
        require(passed, f"Missing-config corrected check failed for {info['label']}")
        missing_results[info["label"]] = {"observed": result, "passed": passed}

    return {
        "inline_string_literal_preserved": True,
        "committed_semantic_config_pairs": semantic_pairs,
        "malformed": malformed_results,
        "missing_config_is_empty_not_error": missing_results,
        "passed": True,
    }


def read_jsonl_bytes(data: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


def inspect_pipeline_output(
    resolved_graph_path: Path,
    selection_source: str = SOURCE_FILE,
) -> dict[str, Any]:
    graph = json.loads(resolved_graph_path.read_text(encoding="utf-8"))
    run_dir = resolved_graph_path.parent
    bundle_path = run_dir / "shipready_complete_repository_context.zip"
    file_edges = []
    for edge in graph.get("edges", []):
        file_edges.append(
            {
                "source": edge.get("source"),
                "target": edge.get("target"),
                "raw": edge.get("raw"),
                "line": edge.get("line"),
                "resolution_strategy": edge.get("resolution_strategy"),
            }
        )
    file_edges.sort(key=lambda row: (str(row["source"]), str(row["target"]), str(row["raw"]), row["line"] or 0))

    result: dict[str, Any] = {
        "graph_summary": graph.get("summary", {}),
        "graph_sha256": sha256_file(resolved_graph_path),
        "file_edges": file_edges,
        "warnings": graph.get("warnings", []),
        "bundle_present": bundle_path.is_file(),
    }
    if bundle_path.is_file():
        result["bundle_sha256"] = sha256_file(bundle_path)
        with zipfile.ZipFile(bundle_path) as archive:
            names = set(archive.namelist())
            result["bundle_members"] = sorted(names)
            if "connections.jsonl" in names:
                connections = read_jsonl_bytes(archive.read("connections.jsonl"))
                result["connections_from_selection_source"] = [
                    row for row in connections if row.get("source_file") == selection_source
                ]
            if "unresolved_relationships.jsonl" in names:
                unresolved = read_jsonl_bytes(archive.read("unresolved_relationships.jsonl"))
                result["unresolved_from_selection_source"] = [
                    row for row in unresolved if row.get("source_file") == selection_source
                ]
            if "selections.jsonl" in names and "chunks.jsonl" in names:
                chunks = {row["chunk_id"]: row for row in read_jsonl_bytes(archive.read("chunks.jsonl"))}
                selections = {row["file"]: row for row in read_jsonl_bytes(archive.read("selections.jsonl"))}
                row = selections.get(selection_source)
                if row:
                    scope = row.get("scopes", {}).get("1", {})
                    included = set(scope.get("included_files", []))
                    chunk_files = {
                        chunks[chunk_id]["file"]
                        for chunk_id in scope.get("chunk_ids", [])
                        if chunk_id in chunks
                    }
                    result["selection_optimal"] = {
                        "source_file": selection_source,
                        "estimated_tokens": scope.get("estimated_tokens"),
                        "included_files": sorted(included),
                        "chunk_ids": scope.get("chunk_ids", []),
                        "effective_files_from_chunks_or_included": sorted(included | chunk_files),
                    }
    return result


def run_one_pipeline(engine: Any, repo: Path, output_root: Path, label: str) -> dict[str, Any]:
    engine.FAST_LANE_ONLY = True
    engine.AUTO_OPEN_FAST_LANE_GRAPHS = False
    destination = output_root / label
    destination.mkdir(parents=True, exist_ok=True)
    log_path = destination / "pipeline.log"
    with log_path.open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            resolved = Path(engine.run_pipeline(repo, destination)).resolve()
    inspected = inspect_pipeline_output(resolved)
    inspected["pipeline_log_name"] = log_path.name
    return inspected


def assert_pipeline_extraction_available(step: dict[str, Any]) -> None:
    summary = step.get("graph_summary", {})
    files = int(summary.get("files_scanned") or 0)
    without_parser = int(summary.get("nodes_without_ast_parser") or 0)
    if files and without_parser >= files:
        raise InterventionError(
            "Full Fast Lane extraction is environment-blocked: every scanned file lacks an AST parser",
            2,
        )


def run_full_pipeline_sequence(engine_info: dict[str, Any], work_root: Path) -> dict[str, Any]:
    engine = engine_info["module"]
    repo = work_root / "full-pipeline-repo"
    repo.mkdir(parents=True)
    hashes_before = write_fixture(repo)
    config_path = repo / "tsconfig.json"
    stock_method = engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"]
    outputs = work_root / "full-pipeline-output"
    steps: list[dict[str, Any]] = []

    def observe(step_name: str, restored: bool, patched: bool) -> None:
        inspected = run_one_pipeline(engine, repo, outputs, f"step-{step_name.lower()}")
        assert_pipeline_extraction_available(inspected)
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
        file_import_targets = {
            row.get("target_file")
            for row in inspected.get("connections_from_selection_source", [])
            if row.get("relationship") == "file_import"
        }
        passed = (
            edge_pairs == expected_pairs
            and (EXPECTED_RESOLUTION[0] in selection_files) == restored
            and (EXPECTED_RESOLUTION[0] in file_import_targets) == restored
            and inspected.get("warnings") == []
            and source_hashes(repo, SOURCE_FILES) == hashes_before
        )
        steps.append(
            {
                "step": step_name,
                "loader": "in_memory_reference_solution" if patched else "stock",
                "loader_patched_during_pipeline": resolver_is_corrected(engine, stock_method),
                "tsconfig_sha256": sha256_file(config_path),
                "source_hashes_unchanged": source_hashes(repo, SOURCE_FILES) == hashes_before,
                "expected_source_file_edge_pairs": sorted(expected_pairs),
                "observed": inspected,
                "passed": passed,
            }
        )
        require(passed, f"Full Fast Lane step {step_name} did not match expectations")

    config_path.write_text(ORIGINAL_CONFIG, encoding="utf-8")
    observe("A", False, False)
    config_path.write_text(COMMENT_STRIPPED_CONFIG, encoding="utf-8")
    observe("B", True, False)
    config_path.write_text(ORIGINAL_CONFIG, encoding="utf-8")
    observe("C", False, False)
    with reference_graph_integration(engine):
        observe("D", True, True)
    require(
        engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"] is stock_method,
        "Stock Fast Lane loader was not restored after full-pipeline step D",
    )
    observe("E", False, False)

    # A valid JSONC config must produce no warning in D (asserted above).  An
    # existing malformed config is the complementary product boundary: the
    # pipeline may continue with relative imports, but the exported graph
    # must disclose that configured aliases were not loaded.
    malformed_config = '{"compilerOptions": }'
    config_path.write_text(malformed_config, encoding="utf-8")

    def observe_malformed(label: str, expect_warning: bool) -> dict[str, Any]:
        inspected = run_one_pipeline(engine, repo, outputs, label)
        assert_pipeline_extraction_available(inspected)
        edge_pairs = {
            (row["source"], row["target"])
            for row in inspected["file_edges"]
            if row["source"] == SOURCE_FILE
        }
        warnings = inspected.get("warnings", [])
        if expect_warning:
            warning_passed = (
                len(warnings) == 1
                and isinstance(warnings[0], dict)
                and warnings[0].get("code") == "tsconfig_parse_failed"
                and warnings[0].get("path") == "tsconfig.json"
                and warnings[0].get("line") == 1
                and (warnings[0].get("column") or 0) > 1
            )
        else:
            warning_passed = warnings == []
        passed = (
            edge_pairs == {(SOURCE_FILE, RELATIVE_RESOLUTION[0])}
            and warning_passed
            and source_hashes(repo, SOURCE_FILES) == hashes_before
        )
        require(passed, f"Full Fast Lane malformed-warning check failed: {label}")
        return {
            "label": label,
            "loader": (
                "in_memory_reference_graph_integration"
                if expect_warning
                else "stock"
            ),
            "tsconfig_sha256": sha256_file(config_path),
            "source_hashes_unchanged": (
                source_hashes(repo, SOURCE_FILES) == hashes_before
            ),
            "observed_source_file_edge_pairs": sorted(edge_pairs),
            "graph_warnings": warnings,
            "graph_sha256": inspected.get("graph_sha256"),
            "bundle_sha256": inspected.get("bundle_sha256"),
            "passed": passed,
        }

    malformed_warning_checks = [observe_malformed("malformed-stock", False)]
    with reference_graph_integration(engine):
        malformed_warning_checks.append(
            observe_malformed("malformed-reference", True)
        )
    require(
        engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"] is stock_method,
        "Stock Fast Lane loader was not restored after malformed-warning check",
    )

    return {
        "level": "installed Fast Lane run_pipeline: resolved graph + complete context ZIP",
        "engine": engine_info["label"],
        "source_hashes": hashes_before,
        "steps": steps,
        "malformed_graph_warning_checks": malformed_warning_checks,
        "passed": True,
    }


def run_lexical_corrected(
    engine_info: dict[str, Any],
    lexical_root: Path,
    output_root: Path,
    lost_relationships: Path,
    selection_case: Path,
) -> dict[str, Any]:
    engine = engine_info["module"]
    lexical_root = lexical_root.resolve()
    require((lexical_root / "tsconfig.json").is_file(), "Lexical root tsconfig not found", 2)
    config_before = sha256_file(lexical_root / "tsconfig.json")
    require(
        config_before == "58840d3690f0a5e6917693cedc6a93cee6af4d06b883a0022abf2689f936059b",
        "Lexical tsconfig does not match the pinned original evidence hash",
    )
    react_source = "packages/lexical-react/src/ReactExtension.tsx"
    react_hash_before = sha256_file(lexical_root / react_source)
    stock_method = engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"]

    with reference_graph_integration(engine):
        inspected = run_one_pipeline(engine, lexical_root, output_root, "lexical-corrected")
        # run_one_pipeline uses the minimal source as its default selection
        # source, so rebuild the relevant inspection from its graph location.
        # The graph hash lets us locate the only resolved graph under output.
        candidates = sorted(output_root.rglob("shipreadyv2_resolved_graph.json"))
        require(len(candidates) == 1, "Expected exactly one lexical corrected resolved graph", 2)
        inspected = inspect_pipeline_output(candidates[0], react_source)

    require(
        engine.LanguageAwareImportResolver.__dict__["_load_tsconfig_aliases"] is stock_method,
        "Stock loader was not restored after lexical corrected run",
    )
    require(sha256_file(lexical_root / "tsconfig.json") == config_before, "Lexical tsconfig changed")
    require(sha256_file(lexical_root / react_source) == react_hash_before, "ReactExtension source changed")

    summary = inspected["graph_summary"]
    require(summary.get("files_scanned") == 2044, "Corrected lexical file count changed")
    require(summary.get("edges") == 5519, "Corrected lexical Fast Lane did not restore 5,519 file edges")
    require(
        inspected.get("warnings") == [],
        "Corrected lexical graph unexpectedly contains a tsconfig warning",
    )

    corrected_edges = {
        (row["source"], row["target"], row["raw"], row["line"])
        for row in inspected["file_edges"]
    }
    lost_rows = [
        json.loads(line)
        for line in lost_relationships.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    missing = [
        row
        for row in lost_rows
        if (
            row["source_file"],
            row["target_file"],
            row["import_specifier"],
            row.get("source_line"),
        )
        not in corrected_edges
    ]
    require(not missing, f"Corrected lexical graph is missing {len(missing)} verified relationships")

    case = json.loads(selection_case.read_text(encoding="utf-8"))
    expected_scope = case["scopes"]["1"]["control"]
    observed_scope = inspected.get("selection_optimal", {})
    expected_files = sorted(expected_scope.get("included_files", []))
    observed_files = observed_scope.get("effective_files_from_chunks_or_included", [])
    recovered = [
        target
        for target, presence in case["scopes"]["1"]["direct_verified_dependency_presence"].items()
        if not presence["as_is"] and presence["control"]
    ]
    selection_passed = (
        observed_files == expected_files
        and observed_scope.get("chunk_ids") == expected_scope.get("chunk_ids")
        and observed_scope.get("estimated_tokens") == expected_scope.get("estimated_tokens")
        and all(target in observed_files for target in recovered)
    )
    require(selection_passed, "Corrected lexical ReactExtension Optimal selection differs from control")

    return {
        "level": "installed Fast Lane run_pipeline on unmodified lexical checkout",
        "lexical_tsconfig_sha256_before": config_before,
        "lexical_tsconfig_sha256_after": sha256_file(lexical_root / "tsconfig.json"),
        "react_extension_sha256_before": react_hash_before,
        "react_extension_sha256_after": sha256_file(lexical_root / react_source),
        "loader_restored_after_run": True,
        "graph_summary": summary,
        "graph_sha256": inspected["graph_sha256"],
        "bundle_sha256": inspected.get("bundle_sha256"),
        "verified_relationships_checked": len(lost_rows),
        "verified_relationships_present": len(lost_rows) - len(missing),
        "react_extension_optimal": observed_scope,
        "react_extension_recovered_direct_dependencies": sorted(recovered),
        "matches_comment_stripped_control_selection_exactly": selection_passed,
        "passed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="write the machine-readable result JSON here")
    parser.add_argument("--work-root", help="directory for temporary intervention repositories")
    parser.add_argument("--keep-work", action="store_true", help="keep --work-root (required with it)")
    parser.add_argument("--full-pipeline", action="store_true", help="also run A-E through Fast Lane")
    parser.add_argument("--lexical-root", help="also run corrected Fast Lane on this lexical checkout")
    parser.add_argument("--lexical-output-root", help="output root for --lexical-root")
    parser.add_argument(
        "--lost-relationships",
        default=str(EVIDENCE / "lost_relationships.jsonl"),
        help="verified lexical relationships JSONL",
    )
    parser.add_argument(
        "--selection-case",
        default=str(EVIDENCE / "selection_case_react_extension.json"),
        help="committed ReactExtension selection case",
    )
    parser.add_argument("--expected-version", default=EXPECTED_VERSION)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-jsonc-causal-intervention/v1",
        "status": "running",
    }
    exit_code = 0

    def execute(work_root: Path) -> None:
        nonlocal exit_code
        try:
            version = importlib.metadata.version("unvibecode")
        except importlib.metadata.PackageNotFoundError as exc:
            raise InterventionError("unvibecode is not installed", 2) from exc
        require(version == args.expected_version, f"Installed version is {version}", 2)
        result["environment"] = {
            "python": sys.version.split()[0],
            "unvibecode": version,
        }
        engines = load_engines()
        result["engines"] = [
            {"label": info["label"], "file": info["file"], "sha256": info["sha256"]}
            for info in engines
        ]

        result["unit_reversible_sequence"] = [
            run_unit_sequence(info, work_root) for info in engines
        ]
        result["existing_fixture_boundary_checks"] = check_existing_fixtures(engines)
        result["parser_boundary_checks"] = check_parser_boundaries(engines, work_root)

        if args.full_pipeline:
            result["full_fastlane_minimal_sequence"] = run_full_pipeline_sequence(
                engines[0], work_root
            )
        if args.lexical_root:
            require(bool(args.lexical_output_root), "--lexical-output-root is required", 2)
            result["lexical_corrected_fastlane"] = run_lexical_corrected(
                engines[0],
                Path(args.lexical_root),
                Path(args.lexical_output_root),
                Path(args.lost_relationships),
                Path(args.selection_case),
            )
        result["status"] = "passed"
        result["conclusion"] = (
            "A/C/E fail and B/D restore under the stated level(s); source hashes are invariant; "
            "the correction is the reference solution patched in memory only, not a shipped fix."
        )

    try:
        if args.work_root:
            require(args.keep_work, "--work-root requires --keep-work so outputs are not deleted", 2)
            work = Path(args.work_root)
            work.mkdir(parents=True, exist_ok=True)
            execute(work)
        else:
            with tempfile.TemporaryDirectory(prefix="unvibecode-jsonc-intervention-") as temporary:
                execute(Path(temporary))
    except InterventionError as exc:
        result["status"] = "environment_blocked" if exc.code == 2 else "failed"
        result["error"] = str(exc)
        exit_code = exc.code
    except Exception as exc:  # preserve a machine-readable failure state
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 1

    rendered = json.dumps(result, indent=2, sort_keys=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        # Keep CI logs readable; the complete machine-readable record is in
        # the requested output file/artifact.
        print(f"CAUSAL_INTERVENTION_STATUS: {result['status']}")
        if result.get("error"):
            print(f"CAUSAL_INTERVENTION_ERROR: {result['error']}")
        for sequence in result.get("unit_reversible_sequence", []):
            states = ",".join(
                f"{step['step']}={'restored' if step['observed']['aliases'] else 'failed'}"
                for step in sequence["steps"]
            )
            print(f"UNIT_SEQUENCE {sequence['engine']}: {states}")
        fixture_checks = result.get("existing_fixture_boundary_checks", [])
        if fixture_checks:
            print(f"EXISTING_FIXTURE_CHECKS: {len(fixture_checks)} passed")
        malformed = result.get("parser_boundary_checks", {}).get("malformed", [])
        if malformed:
            print(f"MALFORMED_BOUNDARY_CHECKS: {len(malformed)} passed")
        if "full_fastlane_minimal_sequence" in result:
            print("FULL_FASTLANE_MINIMAL_SEQUENCE: passed")
            malformed_full = result["full_fastlane_minimal_sequence"].get(
                "malformed_graph_warning_checks", []
            )
            if malformed_full:
                print(
                    "FULL_FASTLANE_MALFORMED_GRAPH_WARNING_CHECKS: "
                    f"{len(malformed_full)} passed"
                )
        if "lexical_corrected_fastlane" in result:
            lexical = result["lexical_corrected_fastlane"]
            print(
                "LEXICAL_CORRECTED_FASTLANE: "
                f"edges={lexical['graph_summary'].get('edges')} "
                f"verified={lexical['verified_relationships_present']}/"
                f"{lexical['verified_relationships_checked']}"
            )
        print(f"OUTPUT: {output}")
    else:
        print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
