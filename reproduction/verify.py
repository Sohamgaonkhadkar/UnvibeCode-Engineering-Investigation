#!/usr/bin/env python3
"""One-command verification for the JSONC tsconfig investigation.

Default mode verifies the *affected* UnvibeCode 0.3.15 behaviour exactly:

1. Python and installed-package preflight;
2. strict-JSON control and all JSONC variants reproduce the known defect;
3. the post-fix regression (`repro_unit.py --expect-fixed`) fails, but only
   for the four JSONC fixtures and only with the exact empty-alias symptom;
4. the reference-solution corpus passes and its loader restores resolution;
5. the reversible A/B/C/D/E causal intervention and targeted boundary checks
   pass on both shipped resolver copies; and
6. committed lexical/ng-matero evidence summaries and JSONL artifacts agree
   with the numbers reported in the investigation.

This is intentionally stricter than "a command failed, therefore pass": an
installation error, traceback, missing output, extra failure, missing failure,
or an already-fixed resolver makes this wrapper fail.

Usage:
    python -m pip install unvibecode==0.3.15
    python reproduction/verify.py

Post-fix form:
    python reproduction/verify.py --expect-fixed

Exit codes:
    0  requested behaviour and evidence checks passed
    1  behavioural or evidence mismatch
    2  environment/setup problem (wrong Python/package, crash, timeout)

No network, hosted service, tree-sitter grammar, or large-repository download
is needed for this entry point.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVIDENCE = ROOT / "evidence" / "tsconfig-jsonc"
AFFECTED_VERSION = "0.3.15"
JSONC_FIXTURES = (
    "minimal_jsonc",
    "minimal_blockcomment",
    "minimal_trailingcomma",
    "minimal_combined_jsonc",
)
ALL_ALIAS_FIXTURES = ("minimal_strict", *JSONC_FIXTURES)
CORRECTION_FIXTURES = (*ALL_ALIAS_FIXTURES, "minimal_stringsafety")
EMPTY_ALIAS = "aliases={} resolution=(None, None)"

EXPECTED_CONFIG_HASHES = {
    EVIDENCE / "lexical_tsconfig_original.jsonc":
        "58840d3690f0a5e6917693cedc6a93cee6af4d06b883a0022abf2689f936059b",
    EVIDENCE / "lexical_tsconfig_control.json":
        "0f7733d055f7866c0985447bce9e739718c515a1379246ac3f210fcef81e61ad",
    EVIDENCE / "ng-matero" / "tsconfig_as_is.json":
        "d911557829a1cb7a18b8f89801b92dcaa4ff7d9a038b844207d372a0158a6a1c",
    EVIDENCE / "ng-matero" / "tsconfig_control.json":
        "49b589e011b2b9bfbab73449b670412f060d698ddd8b54ce69cdaa15f4dc39b9",
}


class VerificationError(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def require(condition: bool, message: str, code: int = 1) -> None:
    if not condition:
        raise VerificationError(message, code)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_child(
    label: str,
    script: str,
    *args: str,
    script_root: Path | None = None,
) -> tuple[int, str]:
    base = HERE if script_root is None else script_root
    script_path = base / script
    command = [sys.executable, str(script_path), *args]
    print(f"\n=== {label} ===")
    print(
        "$",
        " ".join(
            [Path(sys.executable).name, str(script_path.relative_to(ROOT)), *args]
        ),
    )
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VerificationError(f"{label} timed out after {exc.timeout}s", 2) from exc

    output = completed.stdout or ""
    for line in output.rstrip().splitlines():
        print(f"  {line}")
    print(f"  [exit {completed.returncode}]")

    if "Traceback (most recent call last)" in output:
        raise VerificationError(f"{label} crashed with a traceback", 2)
    if "FATAL:" in output:
        raise VerificationError(f"{label} reported a setup failure", 2)
    return completed.returncode, output


def fixture_line(output: str, fixture: str) -> str:
    prefix = ("PASS  ", "FAIL  ")
    matches = [
        line for line in output.splitlines()
        if line.startswith(prefix) and f"{fixture}:" in line
    ]
    require(len(matches) == 1, f"Expected exactly one result line for {fixture}")
    return matches[0]


def check_bug_reproduction(output: str, returncode: int) -> None:
    require(returncode == 0, f"Known-bug reproducer exited {returncode}, expected 0")
    strict = fixture_line(output, "minimal_strict")
    require(strict.startswith("PASS") and "aliases={'@app': 'src/app'}" in strict,
            "Strict-JSON control did not resolve exactly as expected")
    for fixture in JSONC_FIXTURES:
        line = fixture_line(output, fixture)
        require(line.startswith("PASS") and EMPTY_ALIAS in line,
                f"{fixture} did not exhibit the exact empty-alias defect")
    negative = fixture_line(output, "minimal_noalias (negative control)")
    require(negative.startswith("PASS"), "Negative control failed")
    require("PASS — BUG REPRODUCED" in output, "Known-bug final marker missing")


def check_expected_regression_failure(output: str, returncode: int) -> None:
    require(
        returncode == 1,
        "Expected the post-fix regression to fail with exit 1 on the affected "
        f"version; got exit {returncode}",
    )
    strict = fixture_line(output, "minimal_strict")
    require(strict.startswith("PASS"), "Strict control unexpectedly failed regression mode")
    for fixture in JSONC_FIXTURES:
        line = fixture_line(output, fixture)
        require(line.startswith("FAIL") and EMPTY_ALIAS in line,
                f"{fixture} failed for an unexpected reason or with an unexpected symptom")
    negative = fixture_line(output, "minimal_noalias (negative control)")
    require(negative.startswith("PASS"), "Negative control unexpectedly failed regression mode")

    match = re.search(r"RESULT: FAIL \(4 check\(s\)\): (\[.*\])", output)
    require(match is not None, "Regression summary did not report exactly four failures")
    failed = ast.literal_eval(match.group(1))
    require(failed == list(JSONC_FIXTURES),
            f"Regression failed for {failed}, expected only {list(JSONC_FIXTURES)}")


def check_expected_fixed(output: str, returncode: int) -> None:
    require(returncode == 0, f"Post-fix regression exited {returncode}, expected 0")
    for fixture in ALL_ALIAS_FIXTURES:
        line = fixture_line(output, fixture)
        require(line.startswith("PASS") and "aliases={'@app': 'src/app'}" in line,
                f"{fixture} did not load its alias table in fixed mode")
    require("PASS — correct JSONC handling confirmed" in output,
            "Post-fix final marker missing")


def check_correction(output: str, returncode: int) -> None:
    require(returncode == 0, f"Reference-loader integration check exited {returncode}, expected 0")
    for fixture in CORRECTION_FIXTURES:
        line = fixture_line(output, fixture)
        require(line.startswith("PASS") and "resolution=('src/app/util.ts'" in line,
                f"Reference loader did not restore {fixture}")
    require("RESULT: PASS" in output and "reference loader restores resolution" in output,
            "Correction harness final marker missing")


def check_reference_solution(output: str, returncode: int, result_path: Path) -> None:
    require(returncode == 0, f"Reference-solution validation exited {returncode}, expected 0")
    require("REFERENCE_SOLUTION_STATUS: passed" in output,
            "Reference-solution validation did not report a passed status")
    require(
        "CANDIDATE_CORPUS: curated=14 generated=500 invalid_rejected=8" in output,
        "Reference-solution corpus counts changed",
    )
    data = load_json(result_path)
    require(data.get("status") == "passed", "Reference-solution JSON status is not passed")
    corpus = data.get("candidate_corpus", {})
    require(corpus.get("curated_valid_cases") == 14, "Reference curated-case count changed")
    require(corpus.get("generated_valid_cases") == 500, "Reference generated-case count changed")
    require(corpus.get("invalid_cases_rejected") == 8, "Reference invalid-case count changed")
    require(
        corpus.get("out_of_scope_typescript_numeric_cases_rejected") == 4,
        "Reference numeric-boundary count changed",
    )


def check_causal_intervention(output: str, returncode: int, result_path: Path) -> None:
    require(returncode == 0, f"Causal intervention exited {returncode}, expected 0")
    require("CAUSAL_INTERVENTION_STATUS: passed" in output,
            "Causal intervention did not report a passed status")
    expected_sequence = "A=failed,B=restored,C=failed,D=restored,E=failed"
    for engine in ("fast_lane_00a", "merged_graph_01"):
        require(f"UNIT_SEQUENCE {engine}: {expected_sequence}" in output,
                f"Causal sequence mismatch for {engine}")
    require("EXISTING_FIXTURE_CHECKS: 14 passed" in output,
            "Causal intervention fixture-boundary count mismatch")
    require("MALFORMED_BOUNDARY_CHECKS: 6 passed" in output,
            "Causal intervention malformed-boundary count mismatch")

    data = load_json(result_path)
    require(data.get("status") == "passed", "Causal intervention JSON status is not passed")
    require(len(data.get("unit_reversible_sequence", [])) == 2,
            "Causal intervention JSON does not contain both engine sequences")
    require(all(sequence.get("passed") for sequence in data["unit_reversible_sequence"]),
            "A causal intervention engine sequence is not marked passed")
    require(data.get("parser_boundary_checks", {}).get("passed") is True,
            "Causal intervention parser boundaries are not marked passed")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"Missing evidence file: {path.relative_to(ROOT)}", 2) from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def load_jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise VerificationError(f"Missing evidence file: {path.relative_to(ROOT)}", 2) from exc
    try:
        return [json.loads(line) for line in lines if line.strip()]
    except json.JSONDecodeError as exc:
        raise VerificationError(f"Invalid JSONL in {path.relative_to(ROOT)}: {exc}") from exc


def check_evidence() -> None:
    print("\n=== Committed evidence consistency ===")
    for path, expected in EXPECTED_CONFIG_HASHES.items():
        require(path.is_file(), f"Missing config evidence: {path.relative_to(ROOT)}", 2)
        actual = sha256(path)
        require(actual == expected, f"SHA-256 mismatch for {path.relative_to(ROOT)}")
    print("  PASS  Lexical and ng-matero tsconfig hashes")

    lexical_rows = load_jsonl(EVIDENCE / "lost_relationships.jsonl")
    require(len(lexical_rows) == 4256, "Lexical lost-relationship count changed")
    require(all(row.get("verification_status") == "verified_paths_target" for row in lexical_rows),
            "Not every lexical relationship is marked verified")
    require(all(row.get("oracle_expected_target") == row.get("target_file") for row in lexical_rows),
            "A lexical oracle target differs from its graph target")
    require(len({(row["source_file"], row["target_file"]) for row in lexical_rows}) == 4218,
            "Lexical distinct direct-pair count changed")

    oracle = load_json(EVIDENCE / "alias_oracle_summary.json")
    require(oracle["strong_oracle"]["gained_file_edges_total"] == 4256,
            "Lexical oracle total changed")
    require(oracle["strong_oracle"]["classification"] == {"verified_paths_target": 4256},
            "Lexical oracle classification changed")
    require(oracle["inputs"]["graph_as_is"]["summary"]["edges"] == 1263,
            "Lexical as-is graph edge count changed")
    require(oracle["inputs"]["graph_control"]["summary"]["edges"] == 5519,
            "Lexical control graph edge count changed")
    require(oracle["scan_and_extraction"]["extracted_import_records"] == 9562,
            "Lexical extracted-import count changed")

    tsc = load_json(EVIDENCE / "typescript_api_verification.json")
    require(tsc["typescript_version"] == "5.9.3" and tsc["rows_checked"] == 4256
            and tsc["matched_rows"] == 4256 and tsc["mismatched_rows"] == 0,
            "Lexical TypeScript batch verification changed")

    omissions = load_jsonl(EVIDENCE / "direct_selection_omissions.jsonl")
    require(Counter(row["radius"] for row in omissions) == {1: 2707, 2: 3345},
            "Lexical Optimal/Wider omission counts changed")
    require(len({(row["source_file"], row["missing_implementation_file"]) for row in omissions}) == 3364,
            "Lexical distinct recovered-pair count changed")
    selections = load_json(EVIDENCE / "selection_impact_summary.json")
    require(selections["selection_files"]["altered_in_any_scope"] == 1494,
            "Lexical altered-selection count changed")
    print("  PASS  Lexical: 4,256 relationships; 2,707 Optimal; 3,345 Wider")

    ng_rows = load_jsonl(EVIDENCE / "ng-matero" / "lost_relationships.jsonl")
    require(len(ng_rows) == 111 and
            all(row.get("verification_status") == "verified_paths_target" for row in ng_rows),
            "ng-matero verified relationship count changed")
    ng_tsc = load_json(EVIDENCE / "ng-matero" / "typescript_api_verification.json")
    require(ng_tsc["rows_checked"] == ng_tsc["matched_rows"] == 111
            and ng_tsc["mismatched_rows"] == 0,
            "ng-matero TypeScript batch verification changed")
    ng_omissions = load_jsonl(EVIDENCE / "ng-matero" / "direct_selection_omissions.jsonl")
    require(Counter(row["radius"] for row in ng_omissions) == {1: 107, 2: 107},
            "ng-matero Optimal/Wider omission counts changed")
    print("  PASS  ng-matero: 111 relationships; 107 recovered direct dependencies")

    reference = load_json(EVIDENCE / "reference_solution_validation.json")
    require(reference.get("status") == "passed", "Reference-solution evidence is not passed")
    require(reference["candidate_corpus"]["curated_valid_cases"] == 14
            and reference["candidate_corpus"]["generated_valid_cases"] == 500
            and reference["candidate_corpus"]["invalid_cases_rejected"] == 8
            and reference["candidate_corpus"]["out_of_scope_typescript_numeric_cases_rejected"] == 4,
            "Reference-solution corpus evidence changed")
    require(reference["node_oracles"]["typescript_version"] == "5.9.3"
            and reference["node_oracles"]["typescript_valid_agreements"] == 514
            and reference["node_oracles"]["typescript_invalid_diagnostics"] == 8
            and reference["node_oracles"]["jsonc_parser_valid_agreements"] == 510
            and reference["node_oracles"]["jsonc_parser_invalid_diagnostics"] == 8,
            "Reference-solution oracle evidence changed")
    print("  PASS  Reference solution: 514 valid differential cases; 8 invalid rejected")

    scope = load_json(EVIDENCE / "version_scope.json")
    require(scope.get("status") == "completed" and scope.get("through_version") == "0.3.15",
            "Version-scope evidence status/range changed")
    require(scope["summary"]["releases_scanned"] == 16
            and scope["summary"]["wheels_scanned"] == 106
            and scope["summary"]["engine_copies_scanned"] == 212
            and scope["summary"]["unique_loader_ast_fingerprints"] == 1
            and scope["summary"]["all_scanned_releases_affected"] is True,
            "Version-scope aggregate evidence changed")
    require(scope["versions_scanned"] == [f"0.3.{minor}" for minor in range(16)],
            "Version-scope release list changed")
    print("  PASS  Version scope: 106 wheels / 212 engine copies, one vulnerable loader AST")

    exposure = load_json(EVIDENCE / "ecosystem_exposure_sample.json")
    require(exposure.get("status") == "completed" and exposure.get("pages_requested") == 3
            and exposure.get("unique_root_configs_retrieved") == 210,
            "Ecosystem exposure sample status/size changed")
    repo_summary = exposure["summaries"]["all_unique_repositories"]
    content_summary = exposure["summaries"]["unique_config_contents"]
    require(repo_summary["eligible_with_nonempty_resolved_paths"] == 184
            and repo_summary["affected_typescript_verified"] == 44
            and repo_summary["paths_entries_in_affected"] == 211,
            "Repository-level ecosystem exposure evidence changed")
    require(content_summary["eligible_with_nonempty_resolved_paths"] == 139
            and content_summary["affected_typescript_verified"] == 35
            and content_summary["paths_entries_in_affected"] == 174,
            "Unique-content ecosystem exposure evidence changed")
    require(exposure["oracle"]["typescript_version"] == "5.9.3"
            and exposure["oracle"]["eligible_cases_checked"] == 184,
            "Ecosystem exposure TypeScript oracle evidence changed")
    print("  PASS  Exposure sample: 44/184 repositories; 35/139 unique contents affected")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-fixed", action="store_true",
                        help="verify correct post-fix behaviour instead of the affected release")
    parser.add_argument("--expected-version", default=None,
                        help="require this UnvibeCode version (default: 0.3.15 in affected mode)")
    parser.add_argument("--no-version-check", action="store_true",
                        help="do not require a specific installed version")
    parser.add_argument("--skip-evidence", action="store_true",
                        help="skip committed lexical/ng-matero evidence consistency checks")
    args = parser.parse_args()

    try:
        print("=== Environment preflight ===")
        print(f"  Python: {sys.version.split()[0]} ({sys.executable})")
        require(sys.version_info >= (3, 11), "Python 3.11 or newer is required", 2)
        try:
            installed = importlib.metadata.version("unvibecode")
        except importlib.metadata.PackageNotFoundError as exc:
            raise VerificationError(
                "unvibecode is not installed. For the affected-version check run: "
                "python -m pip install unvibecode==0.3.15",
                2,
            ) from exc
        print(f"  UnvibeCode: {installed}")
        expected_version = args.expected_version
        if expected_version is None and not args.expect_fixed:
            expected_version = AFFECTED_VERSION
        if not args.no_version_check and expected_version and installed != expected_version:
            raise VerificationError(
                f"Installed UnvibeCode is {installed}, expected {expected_version}. "
                "Use the pinned affected release, --expected-version, or --no-version-check.",
                2,
            )

        if args.expect_fixed:
            code, output = run_child("Post-fix regression", "repro_unit.py", "--expect-fixed")
            check_expected_fixed(output, code)
        else:
            code, output = run_child("Known-bug reproduction", "repro_unit.py")
            check_bug_reproduction(output, code)
            code, output = run_child(
                "Post-fix regression (must fail for the exact JSONC symptom)",
                "repro_unit.py", "--expect-fixed",
            )
            check_expected_regression_failure(output, code)

        with tempfile.TemporaryDirectory(prefix="unvibecode-verify-solution-") as temporary:
            reference_output = Path(temporary) / "reference-solution-validation.json"
            code, output = run_child(
                "Reference-solution parser corpus",
                "validate_reference_solution.py",
                "--output",
                str(reference_output),
                script_root=ROOT / "solution",
            )
            check_reference_solution(output, code, reference_output)

        code, output = run_child("Reference-loader integration check", "correction_poc.py")
        check_correction(output, code)

        if not args.expect_fixed:
            # This diagnostic intentionally asserts the affected 0.3.15
            # A/C/E failure states, so it is not part of post-fix mode.
            with tempfile.TemporaryDirectory(prefix="unvibecode-verify-causal-") as temporary:
                causal_output = Path(temporary) / "causal-intervention.json"
                code, output = run_child(
                    "Reversible causal intervention and targeted boundaries",
                    "causal_intervention.py",
                    "--output",
                    str(causal_output),
                )
                check_causal_intervention(output, code, causal_output)

        if not args.skip_evidence:
            check_evidence()
    except VerificationError as exc:
        print(f"\nFINAL RESULT: FAIL — {exc}")
        return exc.code

    if args.expect_fixed:
        print("\nFINAL RESULT: PASS — correct JSONC handling and reference loader verified")
    else:
        print("\nFINAL RESULT: PASS — affected 0.3.15 defect reproduced exactly; "
              "regression failure is the expected JSONC empty-alias symptom; "
              "reference solution, reversible causal intervention, targeted boundaries, "
              "and committed evidence verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
