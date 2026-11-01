#!/usr/bin/env python3
"""Ordinary-install CLI comparison for the strict/JSONC minimal fixtures.

This intentionally exercises `python -m unvibecode review`, not an internal engine
entry point. It distinguishes three outcomes:

* exit 0: the expected comparison passed;
* exit 1: the CLI produced artifacts, but expected behavior did not match;
* exit 2: the local Fast Lane could not be assessed (for example, grammar
  acquisition failed before useful extraction), which is an environmental
  limitation and is not evidence for the JSONC defect.

Default mode expects the known 0.3.15 bug: strict JSON produces an internal
file edge and the JSONC twin produces none. `--expect-fixed` expects both to
produce the file edge and therefore fails on an unpatched 0.3.15 install.

The Connected Code bundle can contain a later symbol-fallback connection even
when the Stage-1 file edge is absent. The assertions below therefore use the
Stage-1 file-edge count and record the bundle connection separately.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE_RE = re.compile(
    r"\[STAGE 1 COMPLETE\]\s+(?P<files>[\d,]+) files,\s+"
    r"(?P<file_edges>[\d,]+) internal file edges,\s+"
    r"(?P<package_edges>[\d,]+) package-level edges,\s+"
    r"(?P<unresolved>[\d,]+) unresolved/external imports"
)


def number(value: str) -> int:
    return int(value.replace(",", ""))


def newest(paths):
    paths = list(paths)
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def inspect_run(run_dir: Path) -> dict:
    result: dict = {"run_dir": str(run_dir)}
    results_root = run_dir / "unvibecode_results"
    log = newest(results_root.rglob("connected_code_map.log")) if results_root.exists() else None
    result["connected_code_log"] = str(log) if log else None
    if log:
        text = log.read_text(encoding="utf-8", errors="replace")
        match = STAGE_RE.search(text)
        if match:
            result["stage1"] = {key: number(value) for key, value in match.groupdict().items()}
        result["grammar_download_error"] = "DownloadError" in text
        result["typescript_parser_unavailable"] = (
            "[!] TypeScript/TSX unavailable" in text or "TypeScript/TSX unavailable" in text
        )

    bundle = newest(results_root.rglob("*-repository-context.zip")) if results_root.exists() else None
    result["context_bundle"] = str(bundle) if bundle else None
    if bundle:
        try:
            with zipfile.ZipFile(bundle) as archive:
                connections = [
                    json.loads(line)
                    for line in archive.read("connections.jsonl").decode("utf-8").splitlines()
                    if line.strip()
                ]
                unresolved = [
                    json.loads(line)
                    for line in archive.read("unresolved_relationships.jsonl")
                    .decode("utf-8")
                    .splitlines()
                    if line.strip()
                ]
            result["alias_file_import_connections"] = [
                row
                for row in connections
                if row.get("source_file") == "src/feature/comp.ts"
                and row.get("target_file") == "src/app/util.ts"
                and row.get("relationship") == "file_import"
            ]
            result["alias_symbol_connections"] = [
                row
                for row in connections
                if row.get("source_file") == "src/feature/comp.ts"
                and row.get("target_file") == "src/app/util.ts"
                and row.get("relationship") == "imports_symbol"
            ]
            result["alias_unresolved_relationships"] = [
                row for row in unresolved if row.get("raw") == "@app/util"
            ]
        except Exception as exc:  # preserve, rather than silently swallow
            result["bundle_read_error"] = f"{type(exc).__name__}: {exc}"
    return result


def run_cli(label: str, fixture: Path, output_root: Path, timeout: int) -> dict:
    run_dir = output_root / label
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "cli.stdout.log"
    started = time.time()
    timed_out = False
    with stdout_path.open("w", encoding="utf-8") as stdout:
        process = subprocess.Popen(
            [sys.executable, "-m", "unvibecode", "review", "--repository", str(fixture.resolve())],
            cwd=run_dir,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            start_new_session=(os.name == "posix"),
        )
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            try:
                exit_code = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                exit_code = process.wait(timeout=15)
    result = inspect_run(run_dir)
    result.update(
        {
            "fixture": str(fixture),
            "cli_exit": exit_code,
            "cli_timed_out": timed_out,
            "elapsed_seconds": round(time.time() - started, 3),
            "cli_stdout_log": str(stdout_path),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--timeout", type=int, default=420, help="per-CLI-run seconds")
    parser.add_argument("--expect-fixed", action="store_true")
    args = parser.parse_args()

    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    strict = run_cli("strict", HERE / "minimal_strict", output_root, args.timeout)
    jsonc = run_cli("jsonc", HERE / "minimal_jsonc", output_root, args.timeout)

    strict_edges = strict.get("stage1", {}).get("file_edges")
    jsonc_edges = jsonc.get("stage1", {}).get("file_edges")
    bundles_readable = all(
        run.get("context_bundle") and not run.get("bundle_read_error")
        for run in (strict, jsonc)
    )
    strict_file_import = bool(strict.get("alias_file_import_connections"))
    jsonc_file_import = bool(jsonc.get("alias_file_import_connections"))
    if strict_edges is None or jsonc_edges is None or (strict_edges == 0 and jsonc_edges == 0):
        status = "ENVIRONMENT_BLOCKED_OR_EXTRACTION_UNAVAILABLE"
        exit_code = 2
    elif args.expect_fixed:
        passed = strict_edges >= 1 and jsonc_edges >= 1
        if bundles_readable:
            passed = passed and strict_file_import and jsonc_file_import
        status = "PASS_EXPECTED_BEHAVIOR" if passed else "FAIL_EXPECTED_BEHAVIOR_NOT_MET"
        exit_code = 0 if passed else 1
    else:
        passed = strict_edges >= 1 and jsonc_edges == 0
        if bundles_readable:
            passed = passed and strict_file_import and not jsonc_file_import
        status = "PASS_KNOWN_BUG_REPRODUCED" if passed else "FAIL_KNOWN_BUG_PATTERN_NOT_OBSERVED"
        exit_code = 0 if passed else 1

    summary = {
        "mode": "expect-fixed" if args.expect_fixed else "reproduce-known-bug",
        "status": status,
        "strict": strict,
        "jsonc": jsonc,
    }
    summary_path = output_root / "cli-comparison-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"summary: {summary_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
