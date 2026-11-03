#!/usr/bin/env python3
"""Measure exposure in a transparent GitHub code-search sample.

This optional evidence script looks for public root ``tsconfig.json`` files
through one exact GitHub code-search query, downloads the returned blobs by
their Git blob IDs, and asks a narrow question:

    Among sampled root configs that actually declare a non-empty
    ``compilerOptions.paths`` table and yield aliases under the reference
    loader, how many are rejected by strict JSON while TypeScript itself
    reports no config-syntax error?

This is **not** a random sample and the result is not an ecosystem prevalence
estimate.  GitHub code-search ordering is best-match/index dependent, search
only sees indexed public code, and the query itself selects files mentioning
``compilerOptions``/``paths``.  Its purpose is bounded exposure evidence with
auditable repository/blob identifiers, not a population percentage claim.

Requires an authenticated ``gh`` CLI.  For the committed snapshot, also supply
the TypeScript oracle environment used by the reference-solution validator:

    TSCONFIG_ORACLE_PACKAGE_JSON=/path/to/package.json \
    python reproduction/ecosystem_exposure.py --pages 3 \
      --oracle-package-json /path/to/package.json \
      --output evidence/tsconfig-jsonc/ecosystem_exposure_sample.json
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import hashlib
import json
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from solution.tsconfig_jsonc import (  # noqa: E402
    TsconfigLoadError,
    aliases_from_config_data,
    blank_comments,
    blank_trailing_commas,
    parse_tsconfig_jsonc,
)

QUERY = 'filename:tsconfig.json extension:json "compilerOptions" "paths"'


class ExposureError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def require(condition: bool, message: str, code: int = 1) -> None:
    if not condition:
        raise ExposureError(message, code)


def gh_api(endpoint: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["gh", "api", endpoint],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ExposureError(f"Could not run gh api {endpoint!r}: {exc}", 2) from exc
    if completed.returncode != 0:
        raise ExposureError(
            f"gh api {endpoint!r} failed ({completed.returncode}): {completed.stderr.strip()}",
            2,
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ExposureError(f"gh api returned invalid JSON for {endpoint!r}: {exc}", 2) from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def feature_flags(text: str) -> dict[str, bool]:
    without_comments = blank_comments(text)
    has_line_comment = False
    has_block_comment = False
    # The transform preserves indices and never blanks comment markers inside
    # strings, so changed // or /* positions identify real comments.
    for index in range(len(text) - 1):
        if without_comments[index] != text[index]:
            marker = text[index : index + 2]
            if marker == "//":
                has_line_comment = True
            elif marker == "/*":
                has_block_comment = True
    return {
        "bom": text.startswith("\ufeff"),
        "line_comment": has_line_comment,
        "block_comment": has_block_comment,
        "trailing_comma": blank_trailing_commas(without_comments) != without_comments,
    }


def paths_value(data: Any) -> Any:
    if not isinstance(data, dict):
        return None
    options = data.get("compilerOptions")
    if not isinstance(options, dict):
        return None
    return options.get("paths")


def classify(text: str) -> dict[str, Any]:
    strict_error: str | None = None
    try:
        json.loads(text)
        strict_json = True
    except Exception as exc:
        strict_json = False
        strict_error = f"{type(exc).__name__}: {exc}"

    result: dict[str, Any] = {
        "strict_json": strict_json,
        "strict_json_error": strict_error,
        "features": feature_flags(text),
        "reference_parse_error": None,
        "paths_entries": 0,
        "reference_aliases": {},
        "eligible": False,
        "classification": "ineligible",
    }
    try:
        data = parse_tsconfig_jsonc(text)
        result["reference_aliases"] = aliases_from_config_data(
            data, lambda value: Path(value).as_posix()
        )
    except TsconfigLoadError as exc:
        result["reference_parse_error"] = f"{type(exc).__name__}: {exc}"
        result["classification"] = "ineligible_reference_parse_or_shape"
        return result

    paths = paths_value(data)
    if isinstance(paths, dict):
        result["paths_entries"] = len(paths)
    if not isinstance(paths, dict) or not paths or not result["reference_aliases"]:
        result["classification"] = "ineligible_no_nonempty_resolved_paths"
        return result

    result["eligible"] = True
    result["classification"] = (
        "eligible_stock_loader_compatible" if strict_json else "eligible_strict_json_rejected"
    )
    return result


def run_oracle(
    records: list[dict[str, Any]], texts: dict[str, str], package_json: Path
) -> dict[str, Any]:
    cases = [
        {"name": record["record_id"], "text": texts[record["record_id"]]}
        for record in records
        if record["analysis"]["eligible"]
    ]
    env = dict(**__import__("os").environ)
    env["TSCONFIG_ORACLE_PACKAGE_JSON"] = str(package_json)
    try:
        completed = subprocess.run(
            ["node", str(ROOT / "solution/typescript_oracle.mjs")],
            input=json.dumps({"cases": cases}),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=600,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ExposureError(f"TypeScript oracle could not run: {exc}", 2) from exc
    if completed.returncode != 0:
        raise ExposureError(
            f"TypeScript oracle failed ({completed.returncode}): {completed.stderr.strip()}",
            2,
        )
    oracle = json.loads(completed.stdout)
    by_name = {row["name"]: row for row in oracle["results"]}
    require(len(by_name) == len(cases), "Oracle did not return every eligible case")

    for record in records:
        analysis = record["analysis"]
        if not analysis["eligible"]:
            continue
        row = by_name[record["record_id"]]
        typescript_error = row["typescript"]["error"]
        analysis["typescript_error"] = typescript_error
        analysis["typescript_paths"] = paths_value(row["typescript"].get("config"))
        analysis["typescript_paths_match_reference"] = (
            analysis["typescript_paths"]
            == paths_value(parse_tsconfig_jsonc(texts[record["record_id"]]))
        )
        if not analysis["strict_json"]:
            analysis["affected_typescript_verified"] = typescript_error is None
            if typescript_error is None:
                analysis["classification"] = "affected_typescript_verified"
            else:
                analysis["classification"] = "strict_rejected_but_typescript_error"
        else:
            analysis["affected_typescript_verified"] = False
        # Do not commit copied config values in the audit record.
        analysis.pop("typescript_paths", None)
    return {
        "typescript_version": oracle["typescript_version"],
        "jsonc_parser_version": oracle["jsonc_parser_version"],
        "eligible_cases_checked": len(cases),
    }


def aggregate(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    eligible = [row for row in rows if row["analysis"]["eligible"]]
    affected = [
        row
        for row in eligible
        if row["analysis"].get("affected_typescript_verified") is True
    ]
    strict_rejected = [row for row in eligible if not row["analysis"]["strict_json"]]
    denominator = len(eligible)
    feature_counts = {
        feature: sum(
            bool(row["analysis"]["features"][feature]) for row in affected
        )
        for feature in ("bom", "line_comment", "block_comment", "trailing_comma")
    }
    return {
        "records": len(rows),
        "eligible_with_nonempty_resolved_paths": denominator,
        "strict_json_rejected_eligible": len(strict_rejected),
        "affected_typescript_verified": len(affected),
        "affected_share_of_eligible_sample": (
            round(len(affected) / denominator, 4) if denominator else None
        ),
        "paths_entries_in_eligible": sum(
            row["analysis"]["paths_entries"] for row in eligible
        ),
        "paths_entries_in_affected": sum(
            row["analysis"]["paths_entries"] for row in affected
        ),
        "reference_aliases_in_affected_configs": sum(
            len(row["analysis"]["reference_aliases"]) for row in affected
        ),
        "affected_feature_counts": feature_counts,
    }


def first_by_content(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        digest = record["content_sha256"]
        if digest not in seen:
            seen.add(digest)
            unique.append(record)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--oracle-package-json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require(1 <= args.pages <= 10, "--pages must be between 1 and 10", 2)

    result: dict[str, Any] = {
        "schema": "unvibecode-tsconfig-jsonc-ecosystem-exposure-sample/v1",
        "status": "running",
        "retrieved_on": _dt.date.today().isoformat(),
        "query": QUERY,
        "pages_requested": args.pages,
        "method": {
            "source": "GitHub code search followed by Git blob fetch by returned blob SHA",
            "root_only": "Only items whose path is exactly tsconfig.json are retained.",
            "eligible": (
                "Reference loader parses the config, compilerOptions.paths is a "
                "non-empty object, and at least one alias is extracted."
            ),
            "affected": (
                "Strict json.loads rejects the text and TypeScript "
                "parseConfigFileTextToJson reports no error."
            ),
        },
        "limitations": [
            "Not a random or representative sample; GitHub code-search ordering and indexing determine which public files are returned first.",
            "The query selects indexed root configs containing compilerOptions and paths terms; results must not be described as ecosystem-wide prevalence.",
            "Repositories and search ordering can change after retrieval; repository, blob SHA, and content SHA-256 are retained for audit.",
            "TypeScript parseConfigFileTextToJson checks config syntax, not semantic validity of every compiler option.",
            "Config bodies are not copied into the committed evidence.",
        ],
    }
    code = 0

    try:
        items: list[dict[str, Any]] = []
        seen_repo_paths: set[tuple[str, str]] = set()
        total_count: int | None = None
        incomplete = False
        for page in range(1, args.pages + 1):
            query = urllib.parse.urlencode(
                {"q": QUERY, "per_page": 100, "page": page}
            )
            payload = gh_api(f"search/code?{query}")
            if total_count is None:
                total_count = payload.get("total_count")
            incomplete = incomplete or bool(payload.get("incomplete_results"))
            page_items = payload.get("items", [])
            if not page_items:
                break
            for item in page_items:
                if item.get("path") != "tsconfig.json":
                    continue
                repository = item.get("repository", {})
                key = (repository.get("full_name", ""), item["path"])
                if key in seen_repo_paths:
                    continue
                seen_repo_paths.add(key)
                items.append(item)

        records: list[dict[str, Any]] = []
        texts: dict[str, str] = {}
        for index, item in enumerate(items):
            repository = item.get("repository", {})
            full_name = repository.get("full_name")
            blob_sha = item.get("sha")
            require(bool(full_name and blob_sha), "Search item lacks repository/blob SHA", 2)
            blob = gh_api(f"repos/{full_name}/git/blobs/{blob_sha}")
            require(blob.get("encoding") == "base64", f"Unexpected blob encoding for {full_name}", 2)
            content = base64.b64decode(blob.get("content", ""))
            try:
                text = content.decode("utf-8")
                utf8_lossy = False
            except UnicodeDecodeError:
                text = content.decode("utf-8", errors="replace")
                utf8_lossy = True
            record_id = f"sample_{index:03d}"
            texts[record_id] = text
            records.append(
                {
                    "record_id": record_id,
                    "search_order": index,
                    "repository": full_name,
                    "repository_url": repository.get("html_url"),
                    "default_branch": repository.get("default_branch"),
                    "fork": bool(repository.get("fork")),
                    "archived": bool(repository.get("archived")),
                    "path": item.get("path"),
                    "blob_sha": blob_sha,
                    "html_url": item.get("html_url"),
                    "content_bytes": len(content),
                    "content_sha256": sha256_bytes(content),
                    "utf8_lossy_decode": utf8_lossy,
                    "analysis": classify(text),
                }
            )

        oracle_summary: dict[str, Any] = {"status": "skipped_not_requested"}
        if args.oracle_package_json:
            package_json = args.oracle_package_json.resolve()
            require(package_json.is_file(), f"Oracle package.json not found: {package_json}", 2)
            oracle_summary = run_oracle(records, texts, package_json)
        result["oracle"] = oracle_summary
        result["search_total_count_first_page"] = total_count
        result["search_incomplete_results"] = incomplete
        result["unique_root_configs_retrieved"] = len(records)
        result["records"] = records
        result["summaries"] = {
            "all_unique_repositories": aggregate(records),
            "unique_config_contents": aggregate(first_by_content(records)),
            "non_fork_repositories": aggregate(
                record for record in records if not record["fork"]
            ),
            "non_fork_non_archived_repositories": aggregate(
                record
                for record in records
                if not record["fork"] and not record["archived"]
            ),
        }
        result["status"] = "completed"
        result["conclusion"] = (
            "Within this explicitly non-random first-returned GitHub code-search "
            "sample, TypeScript-valid root configs with real path aliases are "
            "rejected by strict JSON. Report the exact sample counts and limits; "
            "do not extrapolate an ecosystem prevalence rate."
        )
    except ExposureError as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        code = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        code = 1

    if args.output:
        output = args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"ECOSYSTEM_EXPOSURE_STATUS: {result['status']}")
        summary = result.get("summaries", {}).get("all_unique_repositories", {})
        if summary:
            print(
                "ECOSYSTEM_SAMPLE: "
                f"retrieved={result['unique_root_configs_retrieved']} "
                f"eligible={summary['eligible_with_nonempty_resolved_paths']} "
                f"affected={summary['affected_typescript_verified']}"
            )
        if result.get("error"):
            print(f"ECOSYSTEM_EXPOSURE_ERROR: {result['error']}")
        print(f"OUTPUT: {output}")
    else:
        print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
