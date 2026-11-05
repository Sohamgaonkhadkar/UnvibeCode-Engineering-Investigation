#!/usr/bin/env python3
"""Offline consistency check for the investigation's documentation claims.

This repository's documents carry exact numeric and provenance claims (the
duplicate-sweep scope, the CI runs that produced indexed artifacts, and
permalink pins). Those claims can silently go stale in ways a test suite would
normally never see: the upstream tracker moves daily, a new branch head changes
which runs are current, and a renamed file breaks a permalink. This script
turns the two claims that actually went stale once already - the duplicate-sweep
scope and the CI run index - into machine-checked correspondence between the
documents and two committed machine-readable records.

Checks performed (all offline, standard library only):

1. every relative Markdown link resolves to an existing file;
2. every fragment link resolves to a real heading in its target document;
3. every permalink into this repository pins a commit that is recorded in
   ``evidence/ci_status.json`` and points at a path that still exists;
4. every ``actions/runs/<id>`` cited in a document is recorded in
   ``evidence/ci_status.json`` (no unverifiable run citations);
5. every run recorded in ``evidence/ci_status.json`` is cited in
   ``evidence/tsconfig-jsonc/CI_VERIFICATION.md`` (the index is not orphaned);
6. the duplicate-sweep scope in ``evidence/duplicate_sweep.json`` - total
   issues, newest issue, same-mechanism issues, and distinct neighbours - is
   stated consistently in ``DUPLICATE_CHECK.md``, ``README.md``, and
   ``submission/GITHUB_ISSUE.md``;
7. no document claims a sweep scope newer than the recorded sweep, and no
   document revives the superseded "no upstream duplicate" position without
   also citing the issue that superseded it.

Usage:
    python reproduction/check_docs.py
    python reproduction/check_docs.py --json out.json

Exit codes:
    0  every check passed
    1  at least one documented claim is inconsistent
    2  a record or document needed by the checker is missing/unreadable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVIDENCE = ROOT / "evidence"
SWEEP_JSON = EVIDENCE / "duplicate_sweep.json"
CI_JSON = EVIDENCE / "ci_status.json"
CI_DOC = EVIDENCE / "tsconfig-jsonc" / "CI_VERIFICATION.md"
SWEEP_DOCS = (
    ROOT / "DUPLICATE_CHECK.md",
    ROOT / "README.md",
    ROOT / "submission" / "GITHUB_ISSUE.md",
)
REPO_PERMALINK = re.compile(
    r"https://github\.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/"
    r"(?:blob|tree)/([0-9a-f]{7,40})(?:/([^\s)\"']+))?"
)
RUN_LINK = re.compile(r"actions/runs/(\d+)")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```")
SUPERSEDED_CLAIM = re.compile(r"no upstream issue", re.IGNORECASE)


class DocCheckError(Exception):
    """A record or document required by the checker is unusable."""


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise DocCheckError(f"missing record: {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DocCheckError(f"unreadable record {path.relative_to(ROOT)}: {exc}") from exc


def markdown_files() -> list[Path]:
    files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
    if not files:
        raise DocCheckError("no Markdown documents found")
    return sorted(files)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocCheckError(f"unreadable document {path}: {exc}") from exc


def without_code_fences(text: str) -> str:
    """Drop fenced code blocks so examples are not parsed as live links."""
    kept: list[str] = []
    inside = False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            inside = not inside
            continue
        if not inside:
            kept.append(line)
    return "\n".join(kept)


def heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for line in without_code_fences(text).splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not match:
            continue
        slug = re.sub(r"[`*_]", "", match.group(2).strip().lower())
        slug = re.sub(r"[^\w\s\-]", "", slug)
        anchors.add(slug.replace(" ", "-"))
    return anchors


class Report:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def ok(self, message: str) -> None:
        self.passed.append(message)
        print(f"PASS  {message}")

    def bad(self, message: str) -> None:
        self.failed.append(message)
        print(f"FAIL  {message}")

    def check(self, condition: bool, message: str) -> bool:
        if condition:
            self.ok(message)
        else:
            self.bad(message)
        return condition


def check_relative_links(report: Report, files: list[Path]) -> None:
    anchors = {path: heading_anchors(read_text(path)) for path in files}
    broken: list[str] = []
    total = 0
    for path in files:
        for target in MD_LINK.findall(without_code_fences(read_text(path))):
            if target.startswith("mailto:") or re.match(r"^https?://", target):
                continue
            total += 1
            relative, _, fragment = target.partition("#")
            if not relative:
                if fragment not in anchors[path]:
                    broken.append(f"{path.relative_to(ROOT)} -> {target} (missing anchor)")
                continue
            resolved = (path.parent / relative).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target} (missing file)")
                continue
            if fragment and resolved.suffix == ".md":
                owner = next((p for p in files if p.resolve() == resolved), None)
                if owner is None or fragment not in anchors[owner]:
                    broken.append(f"{path.relative_to(ROOT)} -> {target} (missing anchor)")
    report.check(
        not broken,
        f"{total} relative Markdown links and anchors resolve across {len(files)} documents"
        + ("" if not broken else "; " + "; ".join(broken[:6])),
    )


def check_permalinks(report: Report, files: list[Path], ci: dict) -> None:
    pinned = {str(entry.get("commit", "")) for entry in ci.get("pinned_documentation_commits", [])}
    pinned |= {str(snap.get("commit", "")) for snap in ci.get("indexed_snapshots", [])}
    bad: list[str] = []
    count = 0
    for path in files:
        for sha, subpath in REPO_PERMALINK.findall(read_text(path)):
            count += 1
            if not any(p.startswith(sha) or sha.startswith(p[:7]) for p in pinned):
                bad.append(f"{path.relative_to(ROOT)} pins unrecorded commit {sha[:10]}")
                continue
            if subpath and not (ROOT / subpath.split("#")[0]).exists():
                bad.append(f"{path.relative_to(ROOT)} permalink path missing: {subpath}")
    report.check(
        not bad,
        f"{count} repository permalinks pin recorded commits and existing paths"
        + ("" if not bad else "; " + "; ".join(bad[:6])),
    )


def recorded_run_ids(ci: dict) -> set[str]:
    ids: set[str] = set()
    for snap in ci.get("indexed_snapshots", []):
        for run in snap.get("runs", []):
            ids.add(str(run.get("run_id")))
    history = ci.get("macos_acquisition_history", {})
    for job in history.get("cancelled_jobs", []):
        ids.add(str(job.get("run_id")))
    return ids


def check_run_citations(report: Report, files: list[Path], ci: dict) -> None:
    recorded = recorded_run_ids(ci)
    cited: dict[str, list[str]] = {}
    for path in files:
        for run_id in RUN_LINK.findall(read_text(path)):
            cited.setdefault(run_id, []).append(path.relative_to(ROOT).as_posix())
    unknown = sorted(rid for rid in cited if rid not in recorded)
    report.check(
        not unknown,
        f"{len(cited)} cited Actions run IDs are all recorded in evidence/ci_status.json"
        + ("" if not unknown else "; unrecorded: " + ", ".join(f"{u} ({', '.join(cited[u][:2])})" for u in unknown[:5])),
    )

    indexed = {str(run.get("run_id")) for snap in ci.get("indexed_snapshots", []) for run in snap.get("runs", [])}
    doc = read_text(CI_DOC)
    missing = sorted(rid for rid in indexed if rid not in doc)
    report.check(
        not missing,
        f"all {len(indexed)} indexed runs are cited in CI_VERIFICATION.md"
        + ("" if not missing else "; missing: " + ", ".join(missing[:6])),
    )


def check_sweep_scope(report: Report, sweep: dict) -> None:
    tracker = sweep.get("tracker", {})
    newest = tracker.get("newest_issue")
    total = tracker.get("total_issues")
    if not isinstance(newest, int) or not isinstance(total, int):
        report.bad("duplicate_sweep.json has no integer newest_issue/total_issues")
        return

    texts = {}
    for path in SWEEP_DOCS:
        if not path.is_file():
            report.bad(f"missing sweep document: {path.relative_to(ROOT)}")
            return
        texts[path] = read_text(path)

    stale = [
        f"{path.relative_to(ROOT)} does not mention #{newest}"
        for path, text in texts.items()
        if f"#{newest}" not in text
    ]
    report.check(not stale, f"sweep scope #{newest} is stated in all three sweep documents"
                 + ("" if not stale else "; " + "; ".join(stale)))

    total_docs = (ROOT / "DUPLICATE_CHECK.md", ROOT / "README.md")
    totals = [
        f"{path.relative_to(ROOT)} does not state {total} issues"
        for path in total_docs
        if str(total) not in texts[path]
    ]
    report.check(not totals, f"recorded issue total {total} is stated in DUPLICATE_CHECK.md and README.md"
                 + ("" if not totals else "; " + "; ".join(totals)))

    same = [int(i) for i in sweep.get("classification", {}).get("same_mechanism", [])]
    missing_same = [
        f"#{i} absent from {path.relative_to(ROOT)}"
        for i in same
        for path, text in texts.items()
        if f"#{i}" not in text
    ]
    report.check(
        not missing_same,
        f"same-mechanism issue(s) {', '.join('#' + str(i) for i in same)} are cited in every sweep document"
        + ("" if not missing_same else "; " + "; ".join(missing_same[:6])),
    )

    duplicate_doc = texts[ROOT / "DUPLICATE_CHECK.md"]
    distinct = [int(d.get("issue")) for d in sweep.get("classification", {}).get("distinct", [])]
    missing_distinct = [i for i in distinct if f"#{i}" not in duplicate_doc]
    report.check(
        not missing_distinct,
        f"all {len(distinct)} distinct-neighbour issues are classified in DUPLICATE_CHECK.md"
        + ("" if not missing_distinct else "; missing: " + ", ".join(f"#{i}" for i in missing_distinct[:8])),
    )

    over = []
    for path, text in texts.items():
        for claimed in (int(m) for m in re.findall(r"through #(\d+)", text)):
            if claimed > newest:
                over.append(f"{path.relative_to(ROOT)} claims scope #{claimed} > recorded #{newest}")
    report.check(not over, "no document claims a sweep scope newer than the recorded sweep"
                 + ("" if not over else "; " + "; ".join(over[:4])))

    revived = []
    for path in markdown_files():
        text = read_text(path)
        if SUPERSEDED_CLAIM.search(text) and not any(f"#{i}" in text for i in same):
            revived.append(path.relative_to(ROOT).as_posix())
    report.check(
        not revived,
        "no document states a no-duplicate position without citing the superseding issue"
        + ("" if not revived else "; offenders: " + ", ".join(revived[:4])),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="also write a machine-readable report here")
    args = parser.parse_args()

    report = Report()
    print("=== Documentation and claim consistency ===")
    try:
        sweep = load_json(SWEEP_JSON)
        ci = load_json(CI_JSON)
        if not CI_DOC.is_file():
            raise DocCheckError(f"missing document: {CI_DOC.relative_to(ROOT)}")
        files = markdown_files()
        check_relative_links(report, files)
        check_permalinks(report, files, ci)
        check_run_citations(report, files, ci)
        check_sweep_scope(report, sweep)
    except DocCheckError as exc:
        print(f"FATAL: {exc}")
        return 2

    summary = {
        "status": "passed" if not report.failed else "failed",
        "checks_passed": len(report.passed),
        "checks_failed": len(report.failed),
        "failures": report.failed,
        "sweep": {
            "sweep_date": sweep.get("sweep_date"),
            "total_issues": sweep.get("tracker", {}).get("total_issues"),
            "newest_issue": sweep.get("tracker", {}).get("newest_issue"),
            "same_mechanism": sweep.get("classification", {}).get("same_mechanism"),
        },
        "indexed_snapshots": [
            {
                "commit": snap.get("commit"),
                "checks_successful": snap.get("checks_successful"),
                "checks_total": snap.get("checks_total"),
                "runs": [run.get("run_id") for run in snap.get("runs", [])],
            }
            for snap in ci.get("indexed_snapshots", [])
        ],
    }
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"OUTPUT: {out}")

    print(f"DOCUMENTATION_CONSISTENCY_STATUS: {summary['status']}")
    print(
        f"DOCUMENTATION_CONSISTENCY sweep={summary['sweep']['sweep_date']}"
        f"/issues={summary['sweep']['total_issues']}"
        f"/newest=#{summary['sweep']['newest_issue']}"
        f"/same_mechanism={summary['sweep']['same_mechanism']}"
        f"; indexed_snapshots={len(summary['indexed_snapshots'])}"
    )
    return 0 if not report.failed else 1


if __name__ == "__main__":
    sys.exit(main())
