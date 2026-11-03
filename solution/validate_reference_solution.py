#!/usr/bin/env python3
"""Validate the reference JSONC loader against ground truth and oracles.

Default mode is dependency-free apart from this repository: it checks curated
boundaries and 500 deterministically generated valid JSONC documents against
the Python values used to generate them.

For the committed differential evidence, install TypeScript/jsonc-parser in a
separate Node environment and run, for example:

    TSCONFIG_ORACLE_PACKAGE_JSON=/path/to/package.json \
      python solution/validate_reference_solution.py \
      --oracle-package-json /path/to/package.json \
      --output evidence/tsconfig-jsonc/reference_solution_validation.json

That compares the candidate with TypeScript's own
``parseConfigFileTextToJson`` and Microsoft's ``jsonc-parser`` configured with
``allowTrailingComma: true``.  If the Python ``json-with-comments`` and/or
``json5`` packages are importable, their behaviour on the same corpus is also
recorded; absence is reported as a skip rather than treated as a pass/fail.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib
import importlib.metadata
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from solution.test_tsconfig_jsonc import JsoncEmitter, random_value  # noqa: E402
from solution.tsconfig_jsonc import (  # noqa: E402
    TsconfigSyntaxError,
    parse_tsconfig_jsonc,
    transform_jsonc_to_json,
)

VALID_CASES: list[dict[str, Any]] = [
    {"name": "strict", "text": '{"a": 1}', "expected": {"a": 1}, "jsonc_parser": "valid"},
    {"name": "line_comment", "text": '{\n// note\n"a": 1\n}', "expected": {"a": 1}, "jsonc_parser": "valid"},
    {"name": "block_comment", "text": '{"a": /* note */ 1}', "expected": {"a": 1}, "jsonc_parser": "valid"},
    {"name": "trailing_commas", "text": '{"a": [1, 2,],}', "expected": {"a": [1, 2]}, "jsonc_parser": "valid"},
    {"name": "comma_comment_close", "text": '{"a": 1, /* note */}', "expected": {"a": 1}, "jsonc_parser": "valid"},
    {
        "name": "comment_markers_in_string",
        "text": '{"a": "https://x/*y*/ //z ,]}",}',
        "expected": {"a": "https://x/*y*/ //z ,]}"},
        "jsonc_parser": "valid",
    },
    {
        "name": "escaped_backslash_before_quote",
        "text": r'{"a": "slash: \\", /* comment */ "b": 2}',
        "expected": {"a": "slash: \\", "b": 2},
        "jsonc_parser": "valid",
    },
    {"name": "bom", "text": '\ufeff{"a": 1}', "expected": {"a": 1}, "jsonc_parser": "valid"},
    {"name": "cr_line_comment", "text": '{\r// note\r"a": 1\r}', "expected": {"a": 1}, "jsonc_parser": "valid"},
    {"name": "crlf_line_comment", "text": '{\r\n// note\r\n"a": 1\r\n}', "expected": {"a": 1}, "jsonc_parser": "valid"},
    {
        "name": "unicode_line_separator_comment",
        "text": '{\u2028// note\u2028"a": 1\u2028}',
        "expected": {"a": 1},
        "jsonc_parser": "invalid",  # TypeScript accepts LS; jsonc-parser 3.3.1 does not.
    },
    {
        "name": "unicode_paragraph_separator_comment",
        "text": '{\u2029// note\u2029"a": 1\u2029}',
        "expected": {"a": 1},
        "jsonc_parser": "invalid",
    },
    {"name": "empty", "text": "", "expected": {}, "jsonc_parser": "invalid"},
    {"name": "comment_only", "text": "// generated\n/* empty */", "expected": {}, "jsonc_parser": "invalid"},
]

INVALID_CASES: list[dict[str, str]] = [
    {"name": "missing_value", "text": '{"a": }'},
    {"name": "missing_closing_brace", "text": '{"a": 1'},
    {"name": "extra_token", "text": '{"a": 1} nope'},
    {"name": "unterminated_string", "text": '{"a": "unterminated}'},
    {"name": "unterminated_block_comment", "text": '{"a": 1} /*'},
    {"name": "missing_comma", "text": '{"a": 1 "b": 2}'},
    {"name": "json5_unquoted_key", "text": "{a: 1}"},
    {"name": "json5_single_quote", "text": "{'a': 1}"},
    {"name": "leading_object_comma", "text": "{,}"},
    {"name": "leading_array_comma", "text": '{"a":[,]}'},
    {"name": "python_nan_constant", "text": '{"a": NaN}'},
    {"name": "python_infinity_constant", "text": '{"a": Infinity}'},
    {"name": "python_negative_infinity_constant", "text": '{"a": -Infinity}'},
]

# TypeScript's expression-based config parser accepts these JavaScript numeric
# spellings without a diagnostic.  They are not JSONC comments/trailing commas,
# Microsoft's jsonc-parser rejects them, and the reference deliberately keeps
# that narrower, auditable grammar instead of adopting all of JSON5.
OUT_OF_SCOPE_NUMERIC_CASES: list[dict[str, Any]] = [
    {"name": "typescript_leading_decimal", "text": '{"a": .5}', "expected": {"a": 0.5}},
    {"name": "typescript_hex_number", "text": '{"a": 0x10}', "expected": {"a": 16}},
    {"name": "typescript_binary_number", "text": '{"a": 0b101}', "expected": {"a": 5}},
    {"name": "typescript_numeric_separator", "text": '{"a": 1_000}', "expected": {"a": 1000}},
]


class ValidationError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def require(condition: bool, message: str, code: int = 1) -> None:
    if not condition:
        raise ValidationError(message, code)


def generated_cases(count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    for index in range(count):
        value = {
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {"@app/*": ["src/app/*"]},
                "value": random_value(rng),
            },
            "case": index,
        }
        text = JsoncEmitter(rng).emit(value)
        if index % 11 == 0:
            text = text.replace("\n", "\r\n")
        elif index % 13 == 0:
            text = text.replace("\n", "\r")
        cases.append({"name": f"generated_{index}", "text": text, "expected": value})
    return cases


def run_oracle(
    cases: list[dict[str, Any]], package_json: Path
) -> dict[str, Any]:
    env = os.environ.copy()
    env["TSCONFIG_ORACLE_PACKAGE_JSON"] = str(package_json)
    payload = {
        "cases": [{"name": case["name"], "text": case["text"]} for case in cases]
    }
    try:
        completed = subprocess.run(
            ["node", str(HERE / "typescript_oracle.mjs")],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=300,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ValidationError(f"TypeScript oracle could not run: {exc}", 2) from exc
    if completed.returncode != 0:
        raise ValidationError(
            f"TypeScript oracle failed ({completed.returncode}): {completed.stderr.strip()}",
            2,
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"TypeScript oracle returned invalid JSON: {exc}", 2) from exc


def package_version(*names: str) -> str | None:
    for name in names:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def compare_python_libraries(
    valid_cases: list[dict[str, Any]], invalid_cases: list[dict[str, str]]
) -> dict[str, Any]:
    results: dict[str, Any] = {}

    try:
        json_with_comments = importlib.import_module("jsonc")
    except ImportError:
        results["json_with_comments"] = {"status": "skipped_not_installed"}
    else:
        valid_agreements = 0
        valid_failures: list[str] = []
        for case in valid_cases:
            try:
                parsed = json_with_comments.loads(case["text"])
            except Exception:
                valid_failures.append(case["name"])
            else:
                if parsed == case["expected"]:
                    valid_agreements += 1
                else:
                    valid_failures.append(case["name"])
        invalid_accepted: list[str] = []
        for case in invalid_cases:
            try:
                json_with_comments.loads(case["text"])
            except Exception:
                pass
            else:
                invalid_accepted.append(case["name"])
        results["json_with_comments"] = {
            "status": "checked",
            "version": package_version("json-with-comments"),
            "valid_agreements": valid_agreements,
            "valid_cases": len(valid_cases),
            "valid_failure_cases": valid_failures[:20],
            "invalid_cases_accepted": invalid_accepted,
        }

    try:
        json5 = importlib.import_module("json5")
    except ImportError:
        results["python_json5"] = {"status": "skipped_not_installed"}
    else:
        valid_agreements = 0
        valid_failures: list[str] = []
        for case in valid_cases:
            try:
                parsed = json5.loads(case["text"])
            except Exception:
                valid_failures.append(case["name"])
            else:
                if parsed == case["expected"]:
                    valid_agreements += 1
                else:
                    valid_failures.append(case["name"])
        invalid_accepted: list[str] = []
        for case in invalid_cases:
            try:
                json5.loads(case["text"])
            except Exception:
                pass
            else:
                invalid_accepted.append(case["name"])
        results["python_json5"] = {
            "status": "checked",
            "version": package_version("json5", "pyjson5"),
            "valid_agreements": valid_agreements,
            "valid_cases": len(valid_cases),
            "valid_failure_cases": valid_failures[:20],
            "invalid_cases_accepted": invalid_accepted,
        }
    return results


def benchmark() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []

    def measure(label: str, text: str, iterations: int) -> None:
        parse_tsconfig_jsonc(text)
        samples: list[float] = []
        for _ in range(5):
            started = time.perf_counter()
            for _ in range(iterations):
                parse_tsconfig_jsonc(text)
            samples.append((time.perf_counter() - started) * 1000 / iterations)
        entries.append(
            {
                "input": label,
                "bytes_utf8": len(text.encode("utf-8")),
                "iterations_per_sample": iterations,
                "median_ms_per_parse": round(statistics.median(samples), 4),
            }
        )

    lexical = ROOT / "evidence/tsconfig-jsonc/lexical_tsconfig_original.jsonc"
    if lexical.is_file():
        measure("committed lexical root tsconfig", lexical.read_text(encoding="utf-8"), 100)
    ng_matero = ROOT / "evidence/tsconfig-jsonc/ng-matero/tsconfig_as_is.json"
    if ng_matero.is_file():
        measure("committed ng-matero root tsconfig", ng_matero.read_text(encoding="utf-8"), 100)

    synthetic_entries = []
    for index in range(5000):
        synthetic_entries.append(
            f'    "@pkg{index}/*": ["src/pkg{index}/*"], // generated entry {index}'
        )
    synthetic = (
        '{\n  // generated size/performance input\n  "compilerOptions": {\n'
        '    "baseUrl": ".",\n    "paths": {\n'
        + "\n".join(synthetic_entries)
        + '\n    }\n  }\n}\n'
    )
    measure("synthetic 5,000-entry JSONC tsconfig", synthetic, 3)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "entries": entries,
        "note": "Timing is environment-specific; the transform is a single lexical pass before stdlib json parsing.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--oracle-package-json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-tsconfig-jsonc-reference-validation/v1",
        "status": "running",
        "generated_on": _dt.date.today().isoformat(),
        "candidate": {
            "module": "solution/tsconfig_jsonc.py",
            "method": "position-preserving string-aware JSONC transform + stdlib json",
            "python": platform.python_version(),
        },
    }
    code = 0
    generated: list[dict[str, Any]] = []

    try:
        generated = generated_cases(args.generated_count, args.seed)
        valid_cases = [*VALID_CASES, *generated]

        for case in valid_cases:
            parsed = parse_tsconfig_jsonc(case["text"])
            require(parsed == case["expected"], f"Candidate mismatch on valid case {case['name']}")
            require(
                len(transform_jsonc_to_json(case["text"])) == len(case["text"]),
                f"Transform changed length on {case['name']}",
            )
        for case in [*INVALID_CASES, *OUT_OF_SCOPE_NUMERIC_CASES]:
            try:
                parse_tsconfig_jsonc(case["text"])
            except TsconfigSyntaxError:
                pass
            else:
                raise ValidationError(f"Candidate accepted rejected-syntax case {case['name']}")

        result["candidate_corpus"] = {
            "seed": args.seed,
            "curated_valid_cases": len(VALID_CASES),
            "generated_valid_cases": len(generated),
            "invalid_cases_rejected": len(INVALID_CASES),
            "out_of_scope_typescript_numeric_cases_rejected": len(
                OUT_OF_SCOPE_NUMERIC_CASES
            ),
            "passed": True,
        }

        all_oracle_cases = [
            *valid_cases,
            *[{"name": case["name"], "text": case["text"]} for case in INVALID_CASES],
            *[
                {"name": case["name"], "text": case["text"]}
                for case in OUT_OF_SCOPE_NUMERIC_CASES
            ],
        ]
        if args.oracle_package_json:
            package_json = args.oracle_package_json.resolve()
            require(package_json.is_file(), f"Oracle package.json not found: {package_json}", 2)
            oracle = run_oracle(all_oracle_cases, package_json)
            by_name = {row["name"]: row for row in oracle["results"]}
            require(len(by_name) == len(all_oracle_cases), "Oracle did not return every case")

            typescript_valid_agreements = 0
            jsonc_valid_agreements = 0
            jsonc_expected_disagreements: list[str] = []
            for case in valid_cases:
                row = by_name[case["name"]]
                require(
                    row["typescript"]["error"] is None and row["typescript"]["config"] == case["expected"],
                    f"TypeScript oracle mismatch on valid case {case['name']}",
                )
                typescript_valid_agreements += 1
                expectation = case.get("jsonc_parser", "valid")
                errors = row["jsonc_parser"]["errors"]
                value = row["jsonc_parser"].get("value")
                if expectation == "valid":
                    require(
                        not errors and value == case["expected"],
                        f"jsonc-parser mismatch on valid case {case['name']}",
                    )
                    jsonc_valid_agreements += 1
                else:
                    require(bool(errors), f"Expected jsonc-parser disagreement on {case['name']}")
                    jsonc_expected_disagreements.append(case["name"])

            typescript_invalid_diagnostics = 0
            jsonc_invalid_diagnostics = 0
            for case in INVALID_CASES:
                row = by_name[case["name"]]
                require(row["typescript"]["error"] is not None, f"TypeScript accepted invalid case {case['name']}")
                require(bool(row["jsonc_parser"]["errors"]), f"jsonc-parser accepted invalid case {case['name']}")
                typescript_invalid_diagnostics += 1
                jsonc_invalid_diagnostics += 1

            numeric_cases_confirmed: list[str] = []
            for case in OUT_OF_SCOPE_NUMERIC_CASES:
                row = by_name[case["name"]]
                require(
                    row["typescript"]["error"] is None
                    and row["typescript"]["config"] == case["expected"],
                    f"TypeScript numeric-spelling expectation changed on {case['name']}",
                )
                require(
                    bool(row["jsonc_parser"]["errors"]),
                    f"Expected jsonc-parser to reject numeric spelling {case['name']}",
                )
                numeric_cases_confirmed.append(case["name"])

            result["node_oracles"] = {
                "typescript_version": oracle["typescript_version"],
                "jsonc_parser_version": oracle["jsonc_parser_version"],
                "typescript_valid_agreements": typescript_valid_agreements,
                "typescript_invalid_diagnostics": typescript_invalid_diagnostics,
                "jsonc_parser_valid_agreements": jsonc_valid_agreements,
                "jsonc_parser_invalid_diagnostics": jsonc_invalid_diagnostics,
                "jsonc_parser_expected_disagreements": jsonc_expected_disagreements,
                "jsonc_parser_disagreement_note": (
                    "TypeScript accepts empty/comment-only configs and U+2028/U+2029 "
                    "line terminators; jsonc-parser 3.3.1 reports errors for those "
                    "curated cases. The candidate follows TypeScript for tsconfig input."
                ),
                "candidate_stricter_than_typescript_numeric_spellings": numeric_cases_confirmed,
                "numeric_spelling_note": (
                    "TypeScript also accepts JavaScript numeric spellings such as "
                    ".5, 0x10, 0b101, and 1_000. The candidate and jsonc-parser "
                    "reject them; this is an explicit JSONC-subset boundary, not "
                    "a claim of equivalence to TypeScript's full expression-based "
                    "config grammar."
                ),
                "passed": True,
            }
        else:
            result["node_oracles"] = {"status": "skipped_not_requested"}

        result["python_library_comparison"] = compare_python_libraries(valid_cases, INVALID_CASES)
        result["performance"] = benchmark()
        result["status"] = "passed"
        result["conclusion"] = (
            "The candidate accepts the JSONC subset relevant to this defect "
            "(comments/trailing commas, plus TypeScript empty-config and line-"
            "terminator behaviour), rejects malformed and diagnosed JSON5-only "
            "syntax, and preserves string contents and source positions. It "
            "does not claim equivalence to TypeScript's JavaScript numeric-"
            "literal spellings."
        )
    except ValidationError as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        code = exc.code
    except Exception as exc:  # keep a machine-readable failure
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        code = 1

    if args.output:
        output = args.output
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"REFERENCE_SOLUTION_STATUS: {result['status']}")
        corpus = result.get("candidate_corpus", {})
        if corpus:
            print(
                "CANDIDATE_CORPUS: "
                f"curated={corpus.get('curated_valid_cases')} "
                f"generated={corpus.get('generated_valid_cases')} "
                f"invalid_rejected={corpus.get('invalid_cases_rejected')}"
            )
        oracles = result.get("node_oracles", {})
        if oracles.get("passed"):
            print(
                "NODE_ORACLES: "
                f"typescript_valid={oracles['typescript_valid_agreements']} "
                f"typescript_invalid={oracles['typescript_invalid_diagnostics']} "
                f"jsonc_valid={oracles['jsonc_parser_valid_agreements']} "
                f"jsonc_invalid={oracles['jsonc_parser_invalid_diagnostics']}"
            )
        if result.get("error"):
            print(f"REFERENCE_SOLUTION_ERROR: {result['error']}")
        print(f"OUTPUT: {output}")
    else:
        print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
