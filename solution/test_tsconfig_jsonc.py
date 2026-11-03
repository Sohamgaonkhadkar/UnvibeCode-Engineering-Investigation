#!/usr/bin/env python3
"""Unit and deterministic property-style tests for the reference loader."""
from __future__ import annotations

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from solution.tsconfig_jsonc import (  # noqa: E402
    TsconfigShapeError,
    TsconfigSyntaxError,
    aliases_from_config_data,
    load_tsconfig_aliases_result,
    parse_tsconfig_jsonc,
    transform_jsonc_to_json,
)


def posix(value: str | Path) -> str:
    return str(value).replace("\\", "/")


class JsoncEmitter:
    """Emit a known Python value as valid JSONC with seeded trivia choices."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def trivia(self) -> str:
        return self.rng.choice(
            ("", " ", "\n", " /* comment */ ", "\n// comment\n", "/* multi\nline */")
        )

    def emit(self, value: object) -> str:
        if isinstance(value, dict):
            parts = ["{", self.trivia()]
            items = list(value.items())
            for index, (key, item) in enumerate(items):
                parts.append(json.dumps(key, ensure_ascii=False))
                parts.append(self.trivia())
                parts.append(":")
                parts.append(self.trivia())
                parts.append(self.emit(item))
                if index + 1 < len(items):
                    parts.append(",")
                    parts.append(self.trivia())
                elif items and self.rng.random() < 0.45:
                    parts.append(",")
                    parts.append(self.trivia())
            parts.append("}")
            return "".join(parts)
        if isinstance(value, list):
            parts = ["[", self.trivia()]
            for index, item in enumerate(value):
                parts.append(self.emit(item))
                if index + 1 < len(value):
                    parts.append(",")
                    parts.append(self.trivia())
                elif value and self.rng.random() < 0.45:
                    parts.append(",")
                    parts.append(self.trivia())
            parts.append("]")
            return "".join(parts)
        return json.dumps(value, ensure_ascii=False)


def random_value(rng: random.Random, depth: int = 0) -> object:
    strings = [
        "plain",
        "https://example.com/a/*not-a-comment*/",
        "//not-a-comment",
        "comma, brace } bracket ]",
        'quote " and slash \\',
        "@app/*",
        "**/*.ts",
        "unicode-✓",
        "",
    ]
    if depth >= 3:
        return rng.choice([*strings, 0, 1, -2.5, True, False, None])
    kind = rng.randrange(8)
    if kind == 0:
        keys = rng.sample(
            ["compilerOptions", "paths", "@app/*", "//", "x", "nested", "**/*.ts"],
            rng.randrange(0, 4),
        )
        return {key: random_value(rng, depth + 1) for key in keys}
    if kind == 1:
        return [random_value(rng, depth + 1) for _ in range(rng.randrange(0, 4))]
    return rng.choice([*strings, 0, 1, 42, -2.5, 1e10, True, False, None])


class ReferenceParserTests(unittest.TestCase):
    def test_valid_variants_and_string_safety(self) -> None:
        cases = {
            "strict": '{"a": 1}',
            "line_comment": '{\n// note\n"a": 1\n}',
            "block_comment": '{"a": /* note */ 1}',
            "trailing_object": '{"a": 1,}',
            "trailing_array": '{"a": [1, 2,]}',
            "comma_comment_close": '{"a": 1, /* note */}',
            "string_markers": '{"a": "https://x/*y*/ //z ,]}",}',
            "escaped_quote": r'{"a": "quote: \" /* still string */"}',
            "escaped_backslash_before_quote": r'{"a": "slash: \\", /* comment */ "b": 2}',
            "bom": '\ufeff{"a": 1}',
            "empty": "",
            "comment_only": "// generated config\n/* no options yet */",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                parsed = parse_tsconfig_jsonc(text)
                if name in {"empty", "comment_only"}:
                    self.assertEqual(parsed, {})
                elif name == "trailing_array":
                    self.assertEqual(parsed, {"a": [1, 2]})
                elif name == "string_markers":
                    self.assertEqual(parsed["a"], "https://x/*y*/ //z ,]}")
                elif name == "escaped_backslash_before_quote":
                    self.assertEqual(parsed, {"a": "slash: \\", "b": 2})
                else:
                    self.assertEqual(parsed["a"], 1 if name != "escaped_quote" else 'quote: " /* still string */')

    def test_line_terminators(self) -> None:
        base = '{\n// note\n"a": 1\n}'
        for ending_name, ending in [
            ("lf", "\n"),
            ("crlf", "\r\n"),
            ("cr", "\r"),
            ("ls", "\u2028"),
            ("ps", "\u2029"),
        ]:
            with self.subTest(ending=ending_name):
                self.assertEqual(parse_tsconfig_jsonc(base.replace("\n", ending)), {"a": 1})

    def test_transform_is_position_preserving(self) -> None:
        text = '{\n  // note\n  "url": "https://example.com/*x*/",\n  "a": [1,],\n}'
        transformed = transform_jsonc_to_json(text)
        self.assertEqual(len(transformed), len(text))
        self.assertEqual(json.loads(transformed)["url"], "https://example.com/*x*/")
        self.assertEqual(
            [i for i, ch in enumerate(text) if ch == '"'],
            [i for i, ch in enumerate(transformed) if ch == '"'],
        )

    def test_generated_valid_jsonc_round_trips(self) -> None:
        rng = random.Random(20261103)
        for index in range(300):
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
            with self.subTest(case=index):
                self.assertEqual(parse_tsconfig_jsonc(text), value)
                self.assertEqual(len(transform_jsonc_to_json(text)), len(text))

    def test_malformed_and_non_jsonc_syntax_is_rejected(self) -> None:
        cases = [
            '{"a": }',
            '{"a": 1',
            '{"a": 1} nope',
            '{"a": "unterminated}',
            '{"a": 1} /*',
            "{a: 1}",
            "{'a': 1}",
            '{"a": .5}',
            '{"a": 0x10}',
            '{"a": 1 "b": 2}',
            "[" * 2000 + "]" * 2000,
        ]
        for text in cases:
            with self.subTest(text=text):
                with self.assertRaises(TsconfigSyntaxError) as caught:
                    parse_tsconfig_jsonc(text)
                self.assertGreaterEqual(caught.exception.line, 1)
                self.assertGreaterEqual(caught.exception.column, 1)

    def test_alias_mapping_preserves_shipped_rules(self) -> None:
        data = {
            "compilerOptions": {
                "baseUrl": "src",
                "paths": {
                    "@app/*": ["app/*"],
                    "exact": ["lib/exact.ts"],
                    "empty": [],
                },
            }
        }
        self.assertEqual(
            aliases_from_config_data(data, posix),
            {"@app": "src/app", "exact": "src/lib/exact.ts"},
        )

    def test_invalid_alias_shapes_are_not_silently_coerced(self) -> None:
        invalid = [
            [],
            {"compilerOptions": None},
            {"compilerOptions": []},
            {"compilerOptions": {"paths": None}},
            {"compilerOptions": {"paths": []}},
            {"compilerOptions": {"baseUrl": None, "paths": {}}},
            {"compilerOptions": {"paths": {"@app/*": "src/app/*"}}},
            {"compilerOptions": {"paths": {"@app/*": [42]}}},
        ]
        for data in invalid:
            with self.subTest(data=data):
                with self.assertRaises(TsconfigShapeError):
                    aliases_from_config_data(data, posix)

    def test_loader_missing_empty_valid_and_malformed_states(self) -> None:
        def read_text(path: Path) -> str:
            return path.read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = load_tsconfig_aliases_result(root, read_text, posix)
            self.assertEqual(missing.aliases, {})
            self.assertIsNone(missing.warning)

            config = root / "tsconfig.json"
            config.write_text("// no aliases yet\n", encoding="utf-8")
            empty = load_tsconfig_aliases_result(root, read_text, posix)
            self.assertEqual(empty.aliases, {})
            self.assertIsNone(empty.warning)

            config.write_text(
                '{"compilerOptions":{"paths":{"@app/*":["src/app/*"],},},}',
                encoding="utf-8",
            )
            valid = load_tsconfig_aliases_result(root, read_text, posix)
            self.assertEqual(valid.aliases, {"@app": "src/app"})
            self.assertIsNone(valid.warning)

            config.write_text('{"compilerOptions": }', encoding="utf-8")
            malformed = load_tsconfig_aliases_result(root, read_text, posix)
            self.assertEqual(malformed.aliases, {})
            self.assertIsNotNone(malformed.warning)
            assert malformed.warning is not None
            self.assertEqual(malformed.warning.code, "tsconfig_parse_failed")
            self.assertEqual(malformed.warning.line, 1)
            self.assertGreater(malformed.warning.column or 0, 1)


if __name__ == "__main__":
    unittest.main()
