#!/usr/bin/env python3
"""Execute installed stock/reference loaders on the public-config sample.

``ecosystem_exposure.py`` establishes the bounded sample and asks whether
strict JSON rejects a TypeScript-valid config.  This companion removes the
remaining proxy step for every eligible record in that committed sample:

* fetch the exact Git blob recorded in the sample and verify its SHA-256;
* instantiate both installed UnvibeCode 0.3.15 resolver copies with that
  config as the root ``tsconfig.json``;
* record the stock alias table;
* instantiate the same resolvers with the reference loader patched in
  memory; and
* compare both results with the aliases obtained by applying the shipped
  mapping rules to the reference-parsed config.

Config bodies and alias values are not copied into the output.  The sample
remains explicitly non-random and must not be described as a prevalence
estimate.
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import importlib.metadata
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from causal_intervention import corrected_loader, load_engines  # noqa: E402
from ecosystem_exposure import ExposureError, gh_api, sha256_bytes  # noqa: E402
from solution.tsconfig_jsonc import aliases_from_config_data, parse_tsconfig_jsonc  # noqa: E402

DEFAULT_SAMPLE = ROOT / "evidence/tsconfig-jsonc/ecosystem_exposure_sample.json"


class BehaviorError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def require(condition: bool, message: str, code: int = 1) -> None:
    if not condition:
        raise BehaviorError(message, code)


def fetch_blob(record: dict[str, Any]) -> bytes:
    repository = record["repository"]
    blob_sha = record["blob_sha"]
    try:
        blob = gh_api(f"repos/{repository}/git/blobs/{blob_sha}")
    except ExposureError as exc:
        raise BehaviorError(str(exc), exc.code) from exc
    require(blob.get("encoding") == "base64", f"Unexpected blob encoding: {repository}", 2)
    content = base64.b64decode(blob.get("content", ""))
    require(len(content) == record["content_bytes"], f"Blob byte count changed: {repository}")
    require(
        sha256_bytes(content) == record["content_sha256"],
        f"Blob SHA-256 changed: {repository}",
    )
    return content


def audit_record(
    record: dict[str, Any],
    content: bytes,
    engines: list[dict[str, Any]],
    work_root: Path,
) -> dict[str, Any]:
    analysis = record["analysis"]
    affected = bool(analysis.get("affected_typescript_verified"))
    data = parse_tsconfig_jsonc(content.decode("utf-8"), source="tsconfig.json")

    root = work_root / record["record_id"]
    root.mkdir(parents=True)
    (root / "tsconfig.json").write_bytes(content)

    engine_results: dict[str, Any] = {}
    all_passed = True
    expected_alias_count: int | None = None
    for info in engines:
        engine = info["module"]
        expected = aliases_from_config_data(data, engine.to_posix_rel)
        expected_alias_count = len(expected)

        stock_resolver = engine.LanguageAwareImportResolver(root, [])
        stock_aliases = dict(stock_resolver.tsconfig_aliases)
        stock_warning = getattr(stock_resolver, "tsconfig_warning", None)

        with corrected_loader(engine):
            corrected_resolver = engine.LanguageAwareImportResolver(root, [])
        corrected_aliases = dict(corrected_resolver.tsconfig_aliases)
        corrected_warning = getattr(corrected_resolver, "tsconfig_warning", None)

        stock_expected_behavior = stock_aliases == ({} if affected else expected)
        corrected_expected_behavior = corrected_aliases == expected
        warning_expected_behavior = stock_warning is None and corrected_warning is None
        passed = (
            stock_expected_behavior
            and corrected_expected_behavior
            and warning_expected_behavior
        )
        all_passed = all_passed and passed
        engine_results[info["label"]] = {
            "expected_alias_count": len(expected),
            "stock_alias_count": len(stock_aliases),
            "stock_empty": stock_aliases == {},
            "stock_matches_expected": stock_aliases == expected,
            "stock_expected_behavior": stock_expected_behavior,
            "corrected_alias_count": len(corrected_aliases),
            "corrected_matches_expected": corrected_expected_behavior,
            "corrected_warning_code": (
                corrected_warning.get("code") if isinstance(corrected_warning, dict) else None
            ),
            "passed": passed,
        }

    return {
        "record_id": record["record_id"],
        "repository": record["repository"],
        "blob_sha": record["blob_sha"],
        "content_sha256": record["content_sha256"],
        "affected_typescript_verified": affected,
        "strict_json": analysis["strict_json"],
        "paths_entries": analysis["paths_entries"],
        "expected_alias_count": expected_alias_count,
        "engines": engine_results,
        "passed": all_passed,
    }


def summarize(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = list(rows)
    affected = [row for row in records if row["affected_typescript_verified"]]
    unaffected = [row for row in records if not row["affected_typescript_verified"]]

    def count(subset: list[dict[str, Any]], predicate) -> int:
        return sum(bool(predicate(row)) for row in subset)

    def all_engines(row: dict[str, Any], field: str) -> bool:
        return all(engine[field] for engine in row["engines"].values())

    return {
        "eligible_records": len(records),
        "passed_records": count(records, lambda row: row["passed"]),
        "affected_records": len(affected),
        "affected_stock_empty_both_engines": count(
            affected, lambda row: all_engines(row, "stock_empty")
        ),
        "affected_corrected_exact_both_engines": count(
            affected, lambda row: all_engines(row, "corrected_matches_expected")
        ),
        "affected_expected_aliases": sum(
            row["expected_alias_count"] or 0 for row in affected
        ),
        "unaffected_records": len(unaffected),
        "unaffected_stock_exact_both_engines": count(
            unaffected, lambda row: all_engines(row, "stock_matches_expected")
        ),
        "unaffected_corrected_exact_both_engines": count(
            unaffected, lambda row: all_engines(row, "corrected_matches_expected")
        ),
        "unaffected_expected_aliases": sum(
            row["expected_alias_count"] or 0 for row in unaffected
        ),
    }


def first_by_content(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        if row["content_sha256"] not in seen:
            seen.add(row["content_sha256"])
            unique.append(row)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int, help="audit only the first N eligible records")
    parser.add_argument("--expected-version", default="0.3.15")
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-tsconfig-jsonc-ecosystem-loader-behavior/v1",
        "status": "running",
        "generated_on": _dt.date.today().isoformat(),
        "method": {
            "sample": "Eligible records from ecosystem_exposure_sample.json only.",
            "blob_integrity": "Each Git blob is fetched by recorded SHA and checked against the committed byte count and SHA-256.",
            "stock": "Both installed resolver copies are instantiated without modification.",
            "reference": "The same resolver copies are instantiated with solution/tsconfig_jsonc.py patched in memory.",
            "expected": "Reference-parsed data passed through the shipped alias-mapping rules with each engine's to_posix_rel.",
        },
        "limitations": [
            "The underlying GitHub code-search sample is first-returned and non-random; these are exact sample counts, not ecosystem prevalence.",
            "Only records already classified eligible in the committed exposure sample are behaviorally audited here.",
            "Config bodies and alias values are not copied into this output.",
        ],
    }
    code = 0

    try:
        try:
            version = importlib.metadata.version("unvibecode")
        except importlib.metadata.PackageNotFoundError as exc:
            raise BehaviorError("unvibecode is not installed", 2) from exc
        require(version == args.expected_version, f"Installed version is {version}", 2)
        result["environment"] = {
            "python": sys.version.split()[0],
            "unvibecode": version,
        }

        sample = json.loads(args.sample.read_text(encoding="utf-8"))
        require(sample.get("status") == "completed", "Exposure sample is not completed", 2)
        eligible = [
            record
            for record in sample.get("records", [])
            if record.get("analysis", {}).get("eligible")
        ]
        if args.limit is not None:
            require(args.limit > 0, "--limit must be positive", 2)
            eligible = eligible[: args.limit]
        require(bool(eligible), "No eligible sample records found", 2)

        engines = load_engines()
        result["engines"] = [
            {"label": info["label"], "file": info["file"], "sha256": info["sha256"]}
            for info in engines
        ]

        rows: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="unvibecode-public-configs-") as temporary:
            work_root = Path(temporary)
            for index, record in enumerate(eligible, start=1):
                content = fetch_blob(record)
                rows.append(audit_record(record, content, engines, work_root))
                if index % 25 == 0 or index == len(eligible):
                    print(f"Audited {index}/{len(eligible)} eligible public configs")

        result["records"] = rows
        result["summaries"] = {
            "all_unique_repositories": summarize(rows),
            "unique_config_contents": summarize(first_by_content(rows)),
        }
        require(
            all(row["passed"] for row in rows),
            "At least one public-config loader-behavior record failed",
        )
        result["status"] = "completed"
        result["conclusion"] = (
            "For every eligible record in the bounded committed sample, the "
            "installed stock loaders produce the predicted behavior: an empty "
            "alias table for TypeScript-verified affected JSONC and the exact "
            "expected table for strict-JSON controls. The reference loader "
            "produces the exact expected table in both groups on both engines."
        )
    except BehaviorError as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        code = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        code = 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"ECOSYSTEM_LOADER_BEHAVIOR_STATUS: {result['status']}")
        summary = result.get("summaries", {}).get("all_unique_repositories", {})
        if summary:
            print(
                "PUBLIC_CONFIG_LOADER_BEHAVIOR: "
                f"eligible={summary['eligible_records']} "
                f"affected={summary['affected_records']} "
                f"affected_stock_empty={summary['affected_stock_empty_both_engines']} "
                f"affected_corrected_exact={summary['affected_corrected_exact_both_engines']} "
                f"unaffected_stock_exact={summary['unaffected_stock_exact_both_engines']}/"
                f"{summary['unaffected_records']}"
            )
        if result.get("error"):
            print(f"ECOSYSTEM_LOADER_BEHAVIOR_ERROR: {result['error']}")
        print(f"OUTPUT: {args.output}")
    else:
        print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
