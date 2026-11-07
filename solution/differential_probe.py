#!/usr/bin/env python3
"""Deterministic adversarial differential probe for the reference parser.

The ordinary reference corpus proves that curated and generated *valid*
JSONC parses to the expected value.  This probe asks the complementary
question: over hand-enumerated grammar boundaries and seeded one/two-edit
mutations of valid JSONC, does the candidate ever

* accept an input that both TypeScript and Microsoft ``jsonc-parser``
  diagnose;
* reject an input that both accept; or
* produce a different value when all three accept?

Those three categories are hard failures.  Inputs on which TypeScript and
``jsonc-parser`` themselves disagree are counted and retained as explicit
grammar-boundary evidence; they are not silently treated as agreement.

This is validation tooling only.  It does not import or modify UnvibeCode.
The Node oracle environment is supplied explicitly with
``--oracle-package-json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solution.tsconfig_jsonc import parse_tsconfig_jsonc  # noqa: E402

ORACLE = HERE / "typescript_oracle.mjs"
DEFAULT_SEED = 424242
DEFAULT_MUTATION_ATTEMPTS = 3000


@dataclass(frozen=True)
class ProbeCase:
    name: str
    source: str
    group: str
    text: str


OBJECT_SEPARATOR_CASES = [
    "{}",
    "{,}",
    '{"a":1}',
    '{"a":1,}',
    '{"a":1,,}',
    '{"a":1 "b":2}',
    '{"a":1,,"b":2}',
    '{,"a":1}',
    '{"a"::1}',
    '{"a":}',
    '{"a":1, /*c*/}',
    "{/*c*/,}",
    "{ //c\n,}",
]

ARRAY_SEPARATOR_CASES = [
    '{"a":[]}',
    '{"a":[,]}',
    '{"a":[1]}',
    '{"a":[1,]}',
    '{"a":[1,,]}',
    '{"a":[1,,2]}',
    '{"a":[,1]}',
    '{"a":[/*c*/,]}',
    '{"a":[//c\n,]}',
    '{"a":[1 2]}',
    '{"a":[1, /*c*/]}',
]

SCALAR_SPELLINGS = [
    "0",
    "-0",
    "01",
    "-01",
    "1",
    "1.0",
    "1.",
    "1.e2",
    "1.0e2",
    "1e2",
    "1e+2",
    "1e-2",
    "1E2",
    ".5",
    "-.5",
    "+1",
    "-",
    "1_0",
    "1__0",
    "1_",
    "_1",
    "0x10",
    "0Xf",
    "0b101",
    "0o17",
    "0b102",
    "0x",
    "0b",
    "0o",
    "1n",
    "NaN",
    "Infinity",
    "-Infinity",
    "true",
    "false",
    "null",
    "True",
    "False",
    "Null",
    "undefined",
    "void",
    "[]",
    "{}",
    '"x"',
    '"\\x41"',
    '"\\u0041"',
    '"\\ud800"',
    '"\\u12"',
    '"a\nb"',
    '"a\rb"',
    '"a\u2028b"',
    '"a\u2029b"',
    '"a\bb"',
    '"a\fb"',
    '"a\vb"',
    '"a\\\nb"',
]

TRIVIA_SPELLINGS = [
    " ",
    "\t",
    "\n",
    "\r",
    "\u00a0",
    "\v",
    "\f",
    "\ufeff",
    "\u200b",
    "\u3000",
    "\u0085",
    "/*x*/",
    "//x\n",
]

COMMENT_POSITION_CASES = [
    '{"a"/*c*/:1}',
    '{"a":/*c*/1}',
    '{"a":1/*c*/}',
    '/*c*/{"a":1}',
    '{"a":1}/*c*/',
    '{"a":1}//c',
    '{"a":1} \u2028 //c',
    '{"a":tr/*c*/ue}',
    '{"a":1/*c*/2}',
    '{"a":"/*not*/"}',
    '{"a":"//not"}',
    '{"a":"\\"/*still*/"}',
]

ROOT_CASES = [
    "",
    " ",
    "//x",
    "/*x*/",
    "\ufeff",
    "\ufeff\ufeff{}",
    "{}x",
    "{} {}",
    "[]",
    "1",
    '"x"',
    "null",
    "{}}",
    '{"a":1},',
    '{"a":1};',
    "\ufeff/*x*/{}",
]

MUTATION_BASES = [
    '{"a":1,"b":[true,false,null],"c":{"d":"x/y /*z*/"}}',
    '{"compilerOptions":{"paths":{"@app/*":["src/app/*"]}}}',
    '{"a":[1,2,3],"b":"text"}',
    '{"a":1,}',
    '{/*c*/"a":[1,2,],}',
]

MUTATION_TOKENS = list('{}[]",:/\\*.-+eE0123456789truefalsn \n\r\t') + [
    "\u2028",
    "\ufeff",
    "\u00a0",
    "_",
    "x",
    "NaN",
    "Infinity",
    "/*",
    "*/",
    "//",
]

CLASSIFICATIONS = {
    (True, True, True): "all_accept",
    (False, False, False): "all_reject",
    (True, True, False): "candidate_and_typescript_accept_jsonc_parser_rejects",
    (True, False, True): "candidate_and_jsonc_parser_accept_typescript_rejects",
    (True, False, False): "candidate_only_accepts",
    (False, True, True): "candidate_only_rejects",
    (False, True, False): "typescript_only_accepts",
    (False, False, True): "jsonc_parser_only_accepts",
}

CRITICAL_CLASSIFICATIONS = {
    "candidate_only_accepts",
    "candidate_only_rejects",
    "all_accept_value_mismatch",
}


def boundary_cases() -> list[ProbeCase]:
    groups: list[tuple[str, list[str]]] = [
        ("object_separator", OBJECT_SEPARATOR_CASES),
        ("array_separator", ARRAY_SEPARATOR_CASES),
        ("scalar", ['{"a":' + spelling + "}" for spelling in SCALAR_SPELLINGS]),
        (
            "trivia",
            [
                "{" + trivia + '"a"' + trivia + ":" + trivia + "1" + trivia + "}"
                for trivia in TRIVIA_SPELLINGS
            ],
        ),
        ("comment_position", COMMENT_POSITION_CASES),
        ("root", ROOT_CASES),
    ]
    cases: list[ProbeCase] = []
    for group, texts in groups:
        for index, text in enumerate(texts):
            cases.append(
                ProbeCase(
                    name=f"boundary-{group}-{index:02d}",
                    source="enumerated_boundary",
                    group=group,
                    text=text,
                )
            )
    return cases


def mutation_cases(seed: int, attempts: int) -> list[ProbeCase]:
    """Generate unique one/two-edit mutants with a fixed RNG stream.

    The operation distribution is intentionally simple and auditable:
    insertion, deletion, replacement, or a second insertion.  Duplicate
    texts retain only their first attempt name, so ``attempts`` is an input
    budget rather than a claim about the number of unique cases.
    """

    rng = random.Random(seed)
    seen: set[str] = set()
    cases: list[ProbeCase] = []
    for attempt in range(attempts):
        chars = list(rng.choice(MUTATION_BASES))
        operation = rng.randrange(4)
        position = rng.randrange(len(chars) + 1) if chars else 0
        if operation == 0:
            chars.insert(position, rng.choice(MUTATION_TOKENS))
        elif operation == 1 and chars:
            chars.pop(min(position, len(chars) - 1))
        elif operation == 2 and chars:
            chars[min(position, len(chars) - 1)] = rng.choice(MUTATION_TOKENS)
        else:
            second_position = rng.randrange(len(chars) + 1)
            chars.insert(second_position, rng.choice(MUTATION_TOKENS))
        text = "".join(chars)
        if text in seen:
            continue
        seen.add(text)
        cases.append(
            ProbeCase(
                name=f"mutation-{attempt:04d}",
                source="seeded_mutation",
                group="mutation",
                text=text,
            )
        )
    return cases


def case_universe_hash(cases: list[ProbeCase]) -> str:
    digest = hashlib.sha256()
    for case in cases:
        digest.update(case.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(case.source.encode("utf-8"))
        digest.update(b"\0")
        digest.update(case.group.encode("utf-8"))
        digest.update(b"\0")
        digest.update(case.text.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def run_oracle(
    cases: list[ProbeCase], package_json: Path
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    metadata: dict[str, Any] | None = None
    results: dict[str, dict[str, Any]] = {}
    env = dict(os.environ, TSCONFIG_ORACLE_PACKAGE_JSON=str(package_json))
    for start in range(0, len(cases), 500):
        chunk = cases[start : start + 500]
        payload = {
            "cases": [{"name": case.name, "text": case.text} for case in chunk]
        }
        output = subprocess.check_output(
            ["node", str(ORACLE)],
            input=json.dumps(payload),
            text=True,
            env=env,
            cwd=ROOT,
        )
        parsed = json.loads(output)
        chunk_metadata = {
            "typescript_version": parsed["typescript_version"],
            "jsonc_parser_version": parsed["jsonc_parser_version"],
        }
        if metadata is None:
            metadata = chunk_metadata
        elif metadata != chunk_metadata:
            raise RuntimeError("Oracle versions changed between chunks")
        for row in parsed["results"]:
            results[str(row["name"])] = row
    if metadata is None or set(results) != {case.name for case in cases}:
        raise RuntimeError("Oracle did not return exactly one result per case")
    return metadata, results


def classify(case: ProbeCase, oracle: dict[str, Any]) -> dict[str, Any]:
    try:
        candidate_value = parse_tsconfig_jsonc(case.text)
        candidate_valid = True
        candidate_error = None
    except Exception as exc:  # The probe records, then the caller judges.
        candidate_value = None
        candidate_valid = False
        candidate_error = f"{type(exc).__name__}: {exc}"

    typescript = oracle["typescript"]
    jsonc_parser = oracle["jsonc_parser"]
    typescript_valid = typescript.get("error") is None
    jsonc_valid = not jsonc_parser.get("errors")
    key = (candidate_valid, typescript_valid, jsonc_valid)
    classification = CLASSIFICATIONS[key]
    value_equal: bool | None = None
    if key == (True, True, True):
        value_equal = candidate_value == typescript.get("config")
        if not value_equal:
            classification = "all_accept_value_mismatch"

    return {
        "name": case.name,
        "source": case.source,
        "group": case.group,
        "text": case.text,
        "candidate_valid": candidate_valid,
        "candidate_error": candidate_error,
        "typescript_valid": typescript_valid,
        "typescript_error": typescript.get("error"),
        "jsonc_parser_valid": jsonc_valid,
        "jsonc_parser_errors": jsonc_parser.get("errors", []),
        "all_accept_value_equal": value_equal,
        "classification": classification,
    }


def build_report(
    *,
    oracle_package_json: Path,
    seed: int,
    mutation_attempts: int,
) -> dict[str, Any]:
    cases = boundary_cases() + mutation_cases(seed, mutation_attempts)
    oracle_metadata, oracle_results = run_oracle(cases, oracle_package_json)
    rows = [classify(case, oracle_results[case.name]) for case in cases]

    total_counts = Counter(row["classification"] for row in rows)
    by_source: dict[str, dict[str, int]] = {}
    for source in ("enumerated_boundary", "seeded_mutation"):
        by_source[source] = dict(
            sorted(
                Counter(
                    row["classification"] for row in rows if row["source"] == source
                ).items()
            )
        )

    critical = {
        classification: [
            row for row in rows if row["classification"] == classification
        ]
        for classification in sorted(CRITICAL_CLASSIFICATIONS)
    }
    status = "passed" if not any(critical.values()) else "failed"

    # Keep the committed output reviewable: retain every enumerated case,
    # retain any critical mutant in full, and identify non-critical mutants
    # by deterministic attempt name (their texts are regenerated from the
    # seed/method above rather than copied into a multi-megabyte evidence
    # file).
    mutation_divergences: dict[str, list[str]] = {}
    for row in rows:
        if row["source"] != "seeded_mutation":
            continue
        if row["classification"] in {"all_accept", "all_reject"}:
            continue
        mutation_divergences.setdefault(row["classification"], []).append(row["name"])

    return {
        "schema_version": 1,
        "status": status,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            **oracle_metadata,
        },
        "method": {
            "oracle": "solution/typescript_oracle.mjs",
            "typescript_acceptance": (
                "parseConfigFileTextToJson returns no diagnostic; a partial "
                "config value beside a diagnostic is not acceptance"
            ),
            "jsonc_parser_acceptance": (
                "parse(..., allowTrailingComma=true) returns an empty errors "
                "array after stripping one leading BOM in the oracle helper"
            ),
            "candidate_acceptance": (
                "solution.tsconfig_jsonc.parse_tsconfig_jsonc returns without "
                "raising"
            ),
            "mutation_seed": seed,
            "mutation_attempt_budget": mutation_attempts,
            "mutation_operations": [
                "insert one token",
                "delete one character/token unit",
                "replace one character/token unit",
                "insert at a second sampled position",
            ],
            "critical_failure_rules": [
                "candidate accepts while both oracles reject",
                "candidate rejects while both oracles accept",
                "all three accept but candidate value differs from TypeScript",
            ],
            "oracle_disagreement_policy": (
                "Cases where TypeScript and jsonc-parser disagree are counted "
                "as explicit grammar boundaries, not as candidate failures or "
                "as agreement."
            ),
        },
        "case_counts": {
            "enumerated_boundary": sum(
                case.source == "enumerated_boundary" for case in cases
            ),
            "unique_seeded_mutations": sum(
                case.source == "seeded_mutation" for case in cases
            ),
            "total_cases": len(cases),
            "unique_texts_total": len({case.text for case in cases}),
            "case_universe_sha256": case_universe_hash(cases),
        },
        "classification_counts": {
            "total": dict(sorted(total_counts.items())),
            "by_source": by_source,
        },
        "critical_cases": critical,
        "enumerated_boundary_cases": [
            row for row in rows if row["source"] == "enumerated_boundary"
        ],
        "seeded_mutation_oracle_disagreement_names": {
            key: sorted(values)
            for key, values in sorted(mutation_divergences.items())
        },
        "conclusion": (
            "Passed only if there are no candidate-only acceptances, no "
            "candidate-only rejections of inputs both oracles accept, and no "
            "value mismatches where all three accept. Other classifications "
            "are retained as named TypeScript/jsonc-parser grammar boundaries."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--oracle-package-json",
        type=Path,
        required=True,
        help="package.json in an environment with typescript and jsonc-parser",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--mutation-attempts", type=int, default=DEFAULT_MUTATION_ATTEMPTS
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.mutation_attempts < 0:
        parser.error("--mutation-attempts must be non-negative")

    report = build_report(
        oracle_package_json=args.oracle_package_json.resolve(),
        seed=args.seed,
        mutation_attempts=args.mutation_attempts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    counts = report["case_counts"]
    critical_counts = {
        key: len(value) for key, value in report["critical_cases"].items()
    }
    print(f"DIFFERENTIAL_PROBE_STATUS: {report['status']}")
    print(
        "DIFFERENTIAL_PROBE_CASES: "
        f"boundary={counts['enumerated_boundary']} "
        f"mutations={counts['unique_seeded_mutations']} "
        f"total={counts['total_cases']} "
        f"unique_texts={counts['unique_texts_total']}"
    )
    print(f"DIFFERENTIAL_PROBE_CRITICAL: {critical_counts}")
    print(f"OUTPUT: {args.output.resolve()}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
