#!/usr/bin/env python3
"""Audit answer-bearing implementation lines in exported context bundles.

This is a deterministic final-artifact complement to the graph and selection
counts.  For a fixed source file and exported scope, each task names:

* a concrete maintenance question;
* the file that answers it; and
* exact evidence fragments that must occur in selected chunks **from that
  answer file**.

Searching only chunks from the answer file is deliberate: an import or call
site in the source file cannot make a task pass.  The result measures whether
the exported context contains the implementation lines needed to answer the
question.  It does not use an LLM and does not claim that a particular model
will answer correctly.

Example (as run by the lexical clean-environment workflow):

    python reproduction/answerability_audit.py \
      --tasks reproduction/answerability_tasks.json \
      --bundle as_is=/path/to/as-is-repository-context.zip \
      --bundle control=/path/to/control-repository-context.zip \
      --bundle corrected=/path/to/corrected-repository-context.zip \
      --output lexical-ci-evidence/answerability_audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

NUMBER_PREFIX = re.compile(r"^\s*\d+\s\|\s?")


class AuditError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Bundle:
    def __init__(self, label: str, location: Path) -> None:
        self.label = label
        self.location = location
        self.archive = (
            zipfile.ZipFile(location) if location.suffix.lower() == ".zip" else None
        )
        self.chunks = {
            row["chunk_id"]: row for row in self.jsonl("chunks.jsonl")
        }
        self.selections = {
            row["file"]: row for row in self.jsonl("selections.jsonl")
        }
        self.manifest = json.loads(self.text("manifest.json"))

    def close(self) -> None:
        if self.archive is not None:
            self.archive.close()

    def text(self, name: str) -> str:
        if self.archive is not None:
            return self.archive.read(name).decode("utf-8")
        return (self.location / name).read_text(encoding="utf-8")

    def jsonl(self, name: str) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in self.text(name).splitlines()
            if line.strip()
        ]

    def scope(self, source_file: str, radius: int) -> dict[str, Any]:
        selection = self.selections.get(source_file)
        if selection is None:
            raise AuditError(f"{self.label}: no selection row for {source_file}", 2)
        for scope in selection.get("scopes", {}).values():
            if scope.get("radius") == radius:
                return scope
        raise AuditError(f"{self.label}: no scope with radius {radius}", 2)


def unnumber(numbered_code: str) -> str:
    return "\n".join(
        NUMBER_PREFIX.sub("", line, count=1)
        for line in numbered_code.splitlines()
    )


def audit_bundle(bundle: Bundle, task_file: dict[str, Any]) -> dict[str, Any]:
    source_file = task_file["source_file"]
    radius = int(task_file["scope_radius"])
    scope = bundle.scope(source_file, radius)
    selected_chunk_ids = list(scope.get("chunk_ids", []))
    selected_chunks = [
        bundle.chunks[chunk_id]
        for chunk_id in selected_chunk_ids
        if chunk_id in bundle.chunks
    ]
    if len(selected_chunks) != len(selected_chunk_ids):
        raise AuditError(f"{bundle.label}: selection references a missing chunk", 2)

    by_file: dict[str, list[dict[str, Any]]] = {}
    for chunk in selected_chunks:
        by_file.setdefault(chunk["file"], []).append(chunk)

    task_results: list[dict[str, Any]] = []
    for task in task_file["tasks"]:
        answer_file = task["answer_file"]
        answer_chunks = by_file.get(answer_file, [])
        answer_text = "\n".join(
            unnumber(chunk.get("numbered_code", "")) for chunk in answer_chunks
        )
        fragment_results = [
            {"fragment": fragment, "present": fragment in answer_text}
            for fragment in task["evidence_fragments"]
        ]
        task_results.append(
            {
                "id": task["id"],
                "category": task["category"],
                "question": task["question"],
                "expected_answer": task["expected_answer"],
                "answer_file": answer_file,
                "answer_file_selected": bool(answer_chunks),
                "selected_answer_chunk_ids": [
                    chunk["chunk_id"] for chunk in answer_chunks
                ],
                "selected_answer_line_ranges": [
                    chunk.get("line_range") for chunk in answer_chunks
                ],
                "evidence": fragment_results,
                "answerable": bool(fragment_results)
                and all(row["present"] for row in fragment_results),
            }
        )

    def count(category: str, answerable: bool) -> int:
        return sum(
            row["category"] == category and row["answerable"] is answerable
            for row in task_results
        )

    return {
        "label": bundle.label,
        "bundle_name": bundle.location.name,
        "bundle_sha256": sha256_file(bundle.location)
        if bundle.location.is_file()
        else None,
        "manifest": bundle.manifest,
        "source_file": source_file,
        "scope_radius": radius,
        "scope_name": task_file.get("scope_name"),
        "estimated_tokens": scope.get("estimated_tokens"),
        "selected_files": sorted(by_file),
        "selected_chunk_ids": selected_chunk_ids,
        "tasks": task_results,
        "summary": {
            "impact_answerable": count("impact", True),
            "impact_total": sum(
                row["category"] == "impact" for row in task_results
            ),
            "negative_control_answerable": count("negative_control", True),
            "negative_control_total": sum(
                row["category"] == "negative_control" for row in task_results
            ),
        },
    }


def parse_bundle_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise AuditError(f"Bundle must be LABEL=/path/to/bundle: {value}", 2)
    label, raw_path = value.split("=", 1)
    if not label or not raw_path:
        raise AuditError(f"Bundle must be LABEL=/path/to/bundle: {value}", 2)
    return label, Path(raw_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument(
        "--bundle",
        required=True,
        action="append",
        help="LABEL=/path/to/repository-context.zip (repeatable)",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-lexical-answerability-audit/v1",
        "status": "running",
    }
    code = 0
    bundles: list[Bundle] = []

    try:
        task_file = json.loads(args.tasks.read_text(encoding="utf-8"))
        result.update(
            {
                "repository": task_file.get("repository"),
                "commit": task_file.get("commit"),
                "source_file": task_file.get("source_file"),
                "scope_name": task_file.get("scope_name"),
                "scope_radius": task_file.get("scope_radius"),
                "method_note": task_file.get("method_note"),
            }
        )
        audited: list[dict[str, Any]] = []
        for raw_bundle in args.bundle:
            label, location = parse_bundle_arg(raw_bundle)
            if not location.exists():
                raise AuditError(f"Bundle not found for {label}: {location}", 2)
            bundle = Bundle(label, location)
            bundles.append(bundle)
            audited.append(audit_bundle(bundle, task_file))
        result["bundles"] = audited
        by_label = {row["label"]: row for row in audited}

        # The labels are part of the experiment design.  Keep these assertions
        # explicit so a future bundle change cannot silently turn the audit
        # into a narrative-only comparison.
        for label in ("as_is", "control"):
            if label not in by_label:
                raise AuditError(f"Required bundle label missing: {label}", 2)
        summaries = {
            label: row["summary"] for label, row in by_label.items()
        }
        impact_total = summaries["as_is"]["impact_total"]
        negative_total = summaries["as_is"]["negative_control_total"]
        if summaries["as_is"]["impact_answerable"] != 0:
            raise AuditError("Expected zero impact tasks answerable as-is")
        if summaries["control"]["impact_answerable"] != impact_total:
            raise AuditError("Expected every impact task answerable in control")
        if "corrected" in summaries and (
            summaries["corrected"]["impact_answerable"] != impact_total
        ):
            raise AuditError("Expected every impact task answerable after correction")
        for label, summary in summaries.items():
            if summary["negative_control_answerable"] != negative_total:
                raise AuditError(f"Negative control failed for bundle {label}")

        result["summary"] = summaries
        result["status"] = "passed"
        result["conclusion"] = (
            "None of the impact tasks has all required answer-bearing lines in "
            "the as-is Optimal exported chunks; every impact task is answerable "
            "in the comment-stripped control and, when supplied, in the "
            "in-memory-corrected original-config bundle. The negative control "
            "is answerable in every supplied bundle. This is an evidence-"
            "availability measurement, not an LLM-output claim."
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
        print(f"ANSWERABILITY_AUDIT_STATUS: {result['status']}")
        for label, summary in result.get("summary", {}).items():
            print(
                f"ANSWERABILITY {label}: "
                f"impact={summary['impact_answerable']}/{summary['impact_total']} "
                f"negative_control="
                f"{summary['negative_control_answerable']}/"
                f"{summary['negative_control_total']}"
            )
        if result.get("error"):
            print(f"ANSWERABILITY_AUDIT_ERROR: {result['error']}")
        print(f"OUTPUT: {args.output}")
    else:
        print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
