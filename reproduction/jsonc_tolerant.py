#!/usr/bin/env python3
"""Small string-aware JSONC parser used only by the investigation harnesses.

This is diagnostic proof-of-concept code, not a proposed production parser.
It removes ``//`` and ``/* ... */`` comments and trailing commas only outside
JSON string literals, then delegates the actual grammar to ``json.loads``.

Unlike the shipped silent fallback, malformed input raises ``JsoncSyntaxError``
instead of being presented as an empty successful configuration.  A production
fix should still prefer a maintained TypeScript-compatible JSONC parser and
surface a product-level diagnostic for an existing but unparseable config.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


class JsoncSyntaxError(ValueError):
    """Raised when text cannot be treated as well-formed JSONC for this PoC."""


def _strip_comments(text: str) -> str:
    out: list[str] = []
    i, n = 0, len(text)
    in_string = escaped = False

    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            # Drop the comment body but keep its terminating newline.
            i += 2
            while i < n and text[i] != "\n":
                i += 1
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            out.append(" ")  # retain token separation
            closed = False
            while i < n:
                if text[i] == "\n":
                    out.append("\n")
                if i + 1 < n and text[i] == "*" and text[i + 1] == "/":
                    i += 2
                    closed = True
                    break
                i += 1
            if not closed:
                raise JsoncSyntaxError("unterminated block comment")
            continue

        out.append(ch)
        i += 1

    if in_string:
        raise JsoncSyntaxError("unterminated string literal")
    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    out: list[str] = []
    i, n = 0, len(text)
    in_string = escaped = False

    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue

        out.append(ch)
        i += 1

    if in_string:
        raise JsoncSyntaxError("unterminated string literal")
    return "".join(out)


def strip_jsonc(text: str) -> str:
    """Convert the JSONC subset needed here to strict JSON text.

    Two passes also handle the valid shape ``..., /* comment */}``.
    """
    return _strip_trailing_commas(_strip_comments(text))


def parse_jsonc(text: str) -> Any:
    """Parse JSONC or raise JsoncSyntaxError; never manufacture ``{}``."""
    try:
        return json.loads(strip_jsonc(text))
    except JsoncSyntaxError:
        raise
    except json.JSONDecodeError as exc:
        raise JsoncSyntaxError(str(exc)) from exc


def aliases_from_config_data(
    data: Any,
    to_posix_rel: Callable[[str | Path], str],
) -> dict[str, str]:
    """Apply the shipped loader's alias-mapping rules to parsed config data."""
    if not isinstance(data, dict):
        raise JsoncSyntaxError("tsconfig root value is not an object")
    options = data.get("compilerOptions", {})
    if not isinstance(options, dict):
        raise JsoncSyntaxError("tsconfig compilerOptions is not an object")
    paths = options.get("paths", {})
    if not isinstance(paths, dict):
        raise JsoncSyntaxError("tsconfig compilerOptions.paths is not an object")
    base_url = options.get("baseUrl", ".")

    aliases: dict[str, str] = {}
    for alias, targets in paths.items():
        if not targets:
            continue
        if not isinstance(targets, list):
            raise JsoncSyntaxError(f"tsconfig paths target for {alias!r} is not a list")
        alias_prefix = str(alias).replace("/*", "").rstrip("/")
        target_prefix = str(targets[0]).replace("/*", "").rstrip("/")
        aliases[alias_prefix] = to_posix_rel(Path(str(base_url)) / target_prefix)
    return aliases


def load_tsconfig_aliases(
    workspace_root: str | Path,
    safe_read_text: Callable[[Path], str],
    to_posix_rel: Callable[[str | Path], str],
) -> dict[str, str]:
    """JSONC-tolerant counterpart of the shipped ``_load_tsconfig_aliases``."""
    tsconfig = Path(workspace_root) / "tsconfig.json"
    if not tsconfig.exists():
        return {}
    return aliases_from_config_data(
        parse_jsonc(safe_read_text(tsconfig)),
        to_posix_rel,
    )
