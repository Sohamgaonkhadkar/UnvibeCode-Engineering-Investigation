#!/usr/bin/env python3
"""Run the UnvibeCode CLI and preserve the resolved graph before its work dir is cleaned.

The CLI normally deletes its temporary work directory after a clean Fast-Lane-only run.
This helper sets a dedicated temporary root, watches for the graph belonging to the
requested repository, and copies a stable snapshot plus the customer artifacts.

Example:
  python reproduction/capture_run.py --repository /path/to/repo --output-dir /tmp/capture

Exit 0 means the resolved graph and context ZIP were captured. The CLI's own exit code
is recorded in capture_manifest.json rather than treated as this helper's result,
because a later hosted-analysis failure does not invalidate the completed local graph.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    repository = Path(args.repository).resolve()
    output = Path(args.output_dir).resolve()
    cli_cwd = output / "cli"
    temp_root = output / "temp-watch"
    cli_cwd.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)

    before = {p.name for p in temp_root.glob("uvc-*")}
    captured_graph = output / "resolved_graph.json"
    staging_graph = output / "resolved_graph.json.partial"
    state: dict[str, tuple[int, int]] = {}

    env = os.environ.copy()
    env.update(
        {
            "TMPDIR": str(temp_root),
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    log_path = output / "cli.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "unvibecode", "review", "--repository", str(repository)],
            cwd=cli_cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=(os.name == "posix"),
        )
        deadline = time.time() + args.timeout
        timed_out = False
        while process.poll() is None:
            if time.time() > deadline:
                timed_out = True
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                break

            for work in temp_root.glob("uvc-*"):
                if work.name in before:
                    continue
                graph = work / "c" / "run" / "shipreadyv2_resolved_graph.json"
                if not graph.is_file():
                    continue
                try:
                    stat = graph.stat()
                except FileNotFoundError:
                    continue
                signature = (stat.st_size, stat.st_mtime_ns)
                if state.get(str(graph)) == signature:
                    continue
                state[str(graph)] = signature
                try:
                    raw = graph.read_bytes()
                    payload = json.loads(raw)
                    workspace = Path(str(payload.get("workspace_root", ""))).resolve()
                except Exception:
                    continue
                if workspace == repository:
                    staging_graph.write_bytes(raw)
                    staging_graph.replace(captured_graph)
            time.sleep(0.5)
        cli_exit = process.poll()

    copied: dict[str, str] = {}
    results_root = cli_cwd / "unvibecode_results"
    candidates = {
        "context_zip": sorted(results_root.rglob("*-repository-context.zip")),
        "analysis_status": sorted(results_root.rglob("analysis-status.json")),
        "connected_code_log": sorted(results_root.rglob("connected_code_map.log")),
    }
    names = {
        "context_zip": "repository-context.zip",
        "analysis_status": "analysis-status.json",
        "connected_code_log": "connected_code_map.log",
    }
    for key, paths in candidates.items():
        if paths:
            destination = output / names[key]
            shutil.copy2(paths[-1], destination)
            copied[key] = str(destination)

    manifest = {
        "repository": str(repository),
        "cli_exit": cli_exit,
        "timed_out": timed_out,
        "captured": copied,
        "resolved_graph": str(captured_graph) if captured_graph.is_file() else None,
        "sha256": {},
    }
    for path in [captured_graph, *[Path(p) for p in copied.values()], log_path]:
        if path.is_file():
            manifest["sha256"][path.name] = sha256(path)
    (output / "capture_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0 if captured_graph.is_file() and "context_zip" in copied else 2


if __name__ == "__main__":
    raise SystemExit(main())
