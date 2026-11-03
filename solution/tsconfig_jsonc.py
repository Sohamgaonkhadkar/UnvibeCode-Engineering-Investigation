#!/usr/bin/env python3
"""Reference JSONC loader for TypeScript ``tsconfig.json`` files.

This module is intentionally small and dependency-free.  It does **not** use a
regex comment stripper (which can corrupt string literals) and it does **not**
delegate to JSON5 (which accepts syntax TypeScript rejects, such as unquoted
keys and single-quoted strings).  Instead, it performs one string-aware lexical
transform:

* a leading UTF-8 BOM is blanked;
* ``//`` and ``/* ... */`` comments outside string literals are blanked;
* a comma whose next non-whitespace token is ``}`` or ``]`` is blanked;
* LF, CRLF, CR, U+2028, and U+2029 line terminators are handled;
* every replacement is one character, so offsets and line/column positions in
  the transformed text still identify the corresponding input position; and
* the actual JSON grammar is then enforced by Python's standard ``json``
  parser.

The parser raises a structured :class:`TsconfigSyntaxError`.  The product-style
loader catches syntax/shape/read failures for an existing config, returns the
same empty alias table the product needs in order to continue, and returns a
structured warning alongside it.  A missing or genuinely empty/comment-only
config is *not* a warning, matching TypeScript's empty-config behaviour.

Scope is deliberately the JSONC subset at issue—JSON plus comments and
trailing commas—rather than every JavaScript expression spelling that
TypeScript's expression-based config parser happens to accept (for example
``.5`` or ``0x10`` numeric literals).  Like Microsoft's ``jsonc-parser``, this
reference reports those numeric spellings instead of silently broadening the
grammar to JSON5.

This is a reference implementation for maintainer adaptation; importing it in
the investigation harness does not modify the installed UnvibeCode package.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

_LINE_TERMINATORS = frozenset("\n\r\u2028\u2029")
_JSON_WHITESPACE = frozenset(" \t\r\n")
# A comma is a *trailing* comma only after a complete JSON value/member.
# Numbers end in a digit; strings in a quote; containers in ``}``/``]``;
# ``true``/``false`` end in ``e`` and ``null`` in ``l``.  Tracking this
# prevents an elision/leading comma such as ``[,]`` or ``{,}`` from being
# silently rewritten into an empty container.
_VALUE_END_CHARS = frozenset('"0123456789el}]')


def _line_column(text: str, offset: int) -> tuple[int, int]:
    """Return one-based line/column for ``offset`` in ``text``."""

    offset = max(0, min(offset, len(text)))
    line = 1
    line_start = 0
    i = 0
    while i < offset:
        ch = text[i]
        if ch == "\r":
            line += 1
            if i + 1 < offset and text[i + 1] == "\n":
                i += 1
            line_start = i + 1
        elif ch in _LINE_TERMINATORS:
            line += 1
            line_start = i + 1
        i += 1
    return line, offset - line_start + 1


class _InvalidConstantError(ValueError):
    """Internal signal for Python-json's non-JSON NaN/Infinity extensions."""

    def __init__(self, constant: str) -> None:
        super().__init__(constant)
        self.constant = constant


def _reject_constant(constant: str) -> Any:
    raise _InvalidConstantError(constant)


def _parse_json_int(value: str) -> int | float:
    """Parse a JSON integer without leaking CPython's digit-limit error.

    Normal integers remain exact Python ints.  If CPython's
    integer-string conversion guard fires, the token is far beyond the
    finite IEEE-754 range used for JavaScript/TypeScript numbers, so use
    signed infinity rather than crashing or falsely reporting syntax.
    """

    try:
        return int(value)
    except ValueError:
        return -math.inf if value.startswith("-") else math.inf


def _find_token_outside_strings(text: str, token: str) -> int:
    """Find ``token`` outside a JSON string, or return 0 if not found."""

    i = 0
    in_string = False
    escaped = False
    while i < len(text):
        ch = text[i]
        if in_string:
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
            i += 1
            continue
        if text.startswith(token, i):
            return i
        i += 1
    return 0


class TsconfigLoadError(ValueError):
    """Base class for failures while loading an existing tsconfig."""


class TsconfigSyntaxError(TsconfigLoadError):
    """A JSONC syntax error with a stable source position."""

    def __init__(
        self,
        message: str,
        *,
        source: str = "tsconfig.json",
        offset: int = 0,
        line: Optional[int] = None,
        column: Optional[int] = None,
        text: Optional[str] = None,
    ) -> None:
        if (line is None or column is None) and text is not None:
            line, column = _line_column(text, offset)
        self.message = message
        self.source = source
        self.offset = offset
        self.line = 1 if line is None else line
        self.column = 1 if column is None else column
        super().__init__(f"{source}:{self.line}:{self.column}: {message}")


class TsconfigShapeError(TsconfigLoadError):
    """The parsed value cannot supply a valid root alias table."""


@dataclass(frozen=True)
class TsconfigWarning:
    """A graph/log warning for a degraded alias table."""

    code: str
    path: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    offset: Optional[int] = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }
        if self.line is not None:
            result["line"] = self.line
        if self.column is not None:
            result["column"] = self.column
        if self.offset is not None:
            result["offset"] = self.offset
        return result


@dataclass(frozen=True)
class TsconfigLoadResult:
    """Alias table plus the warning that explains any degradation."""

    aliases: dict[str, str]
    warning: Optional[TsconfigWarning] = None


def blank_comments(text: str, *, source: str = "tsconfig.json") -> str:
    """Blank JSONC comments without changing text length or string content.

    A leading BOM is also blanked and U+2028/U+2029 outside strings are
    normalized to LF (one character each), because TypeScript treats them as
    line terminators while strict JSON does not treat them as whitespace.
    """

    if not isinstance(text, str):
        raise TypeError("tsconfig text must be str")

    chars = list(text)
    if chars and chars[0] == "\ufeff":
        chars[0] = " "

    i = 0
    n = len(text)
    in_string = False
    escaped = False
    string_start = -1

    while i < n:
        ch = text[i]

        if in_string:
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
            escaped = False
            string_start = i
            i += 1
            continue

        if ch in "\u2028\u2029":
            chars[i] = "\n"
            i += 1
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            chars[i] = chars[i + 1] = " "
            i += 2
            while i < n and text[i] not in _LINE_TERMINATORS:
                chars[i] = " "
                i += 1
            if i < n:
                # Preserve CRLF/CR/LF exactly.  LS/PS become LF so the strict
                # JSON parser sees JSON whitespace at the same offset.
                if text[i] in "\u2028\u2029":
                    chars[i] = "\n"
                    i += 1
                elif text[i] == "\r" and i + 1 < n and text[i + 1] == "\n":
                    i += 2
                else:
                    i += 1
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            comment_start = i
            chars[i] = chars[i + 1] = " "
            i += 2
            closed = False
            while i < n:
                if text[i] == "*" and i + 1 < n and text[i + 1] == "/":
                    chars[i] = chars[i + 1] = " "
                    i += 2
                    closed = True
                    break
                if text[i] in "\u2028\u2029":
                    chars[i] = "\n"
                elif text[i] not in "\n\r":
                    chars[i] = " "
                i += 1
            if not closed:
                raise TsconfigSyntaxError(
                    "unterminated block comment",
                    source=source,
                    offset=comment_start,
                    text=text,
                )
            continue

        i += 1

    if in_string:
        raise TsconfigSyntaxError(
            "unterminated string literal",
            source=source,
            offset=max(0, string_start),
            text=text,
        )
    return "".join(chars)


def blank_trailing_commas(text: str, *, source: str = "tsconfig.json") -> str:
    """Blank commas immediately before ``}``/``]`` outside strings."""

    chars = list(text)
    i = 0
    n = len(text)
    in_string = False
    escaped = False
    string_start = -1
    previous_significant: str | None = None

    while i < n:
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
                previous_significant = '"'
            i += 1
            continue

        if ch == '"':
            in_string = True
            escaped = False
            string_start = i
            i += 1
            continue

        if ch in _JSON_WHITESPACE:
            i += 1
            continue

        if ch == ",":
            j = i + 1
            while j < n and text[j] in _JSON_WHITESPACE:
                j += 1
            if (
                j < n
                and text[j] in "}]"
                and previous_significant in _VALUE_END_CHARS
            ):
                chars[i] = " "
        previous_significant = ch
        i += 1

    if in_string:
        raise TsconfigSyntaxError(
            "unterminated string literal",
            source=source,
            offset=max(0, string_start),
            text=text,
        )
    return "".join(chars)


def transform_jsonc_to_json(text: str, *, source: str = "tsconfig.json") -> str:
    """Convert TypeScript's tsconfig JSONC subset to strict JSON text.

    The result has exactly the same length as the input.  Comments are
    handled before trailing commas so ``..., /* comment */}`` is accepted.
    """

    without_comments = blank_comments(text, source=source)
    return blank_trailing_commas(without_comments, source=source)


# Compatibility-friendly descriptive alias.
strip_jsonc = transform_jsonc_to_json


def parse_tsconfig_jsonc(text: str, *, source: str = "tsconfig.json") -> Any:
    """Parse a tsconfig document, raising with a precise source position.

    TypeScript treats an empty or comment-only tsconfig as an empty config,
    so that special case returns ``{}``.  Every non-empty result must satisfy
    strict JSON after the position-preserving JSONC transform.
    """

    transformed = transform_jsonc_to_json(text, source=source)
    if not transformed.strip():
        return {}
    try:
        # Python's json module otherwise accepts the non-JSON constants
        # NaN/Infinity/-Infinity by default.  Both TypeScript and
        # Microsoft's jsonc-parser diagnose those tokens, so reject them
        # explicitly instead of inheriting that Python-specific extension.
        return json.loads(
            transformed,
            parse_constant=_reject_constant,
            parse_int=_parse_json_int,
        )
    except _InvalidConstantError as exc:
        offset = _find_token_outside_strings(transformed, exc.constant)
        raise TsconfigSyntaxError(
            f"invalid JSON constant {exc.constant!r}",
            source=source,
            offset=offset,
            text=text,
        ) from exc
    except json.JSONDecodeError as exc:
        raise TsconfigSyntaxError(
            exc.msg,
            source=source,
            offset=exc.pos,
            line=exc.lineno,
            column=exc.colno,
        ) from exc
    except RecursionError as exc:
        raise TsconfigSyntaxError(
            "JSON nesting is too deep",
            source=source,
        ) from exc
    except ValueError as exc:
        # Defensive: keep any remaining plain ValueError from the stdlib
        # decoder inside the structured error contract.
        raise TsconfigSyntaxError(
            str(exc),
            source=source,
        ) from exc


# The investigation's older diagnostic harness used this shorter name.
parse_jsonc = parse_tsconfig_jsonc
JsoncSyntaxError = TsconfigSyntaxError


def aliases_from_config_data(
    data: Any,
    to_posix_rel: Callable[[str | Path], str],
) -> dict[str, str]:
    """Apply the shipped loader's existing alias-mapping rules.

    Only the parse step changes.  In particular, this deliberately preserves
    the shipped ``replace("/*", "")`` mapping behaviour; separate TypeScript
    ``paths`` pattern-semantics limitations are outside this correction.
    """

    if not isinstance(data, dict):
        raise TsconfigShapeError("tsconfig root value is not an object")

    options = data.get("compilerOptions", {})
    if not isinstance(options, dict):
        raise TsconfigShapeError("tsconfig compilerOptions is not an object")

    paths = options.get("paths", {})
    if not isinstance(paths, dict):
        raise TsconfigShapeError("tsconfig compilerOptions.paths is not an object")

    base_url = options.get("baseUrl", ".")
    if not isinstance(base_url, str):
        raise TsconfigShapeError("tsconfig compilerOptions.baseUrl is not a string")

    aliases: dict[str, str] = {}
    for alias, targets in paths.items():
        # Validate type before the empty-list skip: a falsy non-list such as
        # ``""``/``None``/``0`` is an invalid shape, not an absent mapping.
        if not isinstance(targets, list) or not all(
            isinstance(target, str) for target in targets
        ):
            raise TsconfigShapeError(
                f"tsconfig paths target for {alias!r} is not a list of strings"
            )
        if not targets:
            continue
        alias_prefix = str(alias).replace("/*", "").rstrip("/")
        target_prefix = targets[0].replace("/*", "").rstrip("/")
        try:
            aliases[alias_prefix] = to_posix_rel(Path(base_url) / target_prefix)
        except (OSError, ValueError) as exc:
            raise TsconfigShapeError(
                f"tsconfig paths target for {alias!r} cannot be normalized: {exc}"
            ) from exc
    return aliases


def read_tsconfig_text(path: str | Path) -> str:
    """Read a tsconfig as strict UTF-8, preserving a leading BOM character.

    Product integration should use this reader—or an equivalent strict
    UTF-8 reader—for the config file.  The shipped engines' general
    ``safe_read_text(..., errors="ignore")`` is appropriate for lossy source
    scanning, but for a config file it can silently delete invalid bytes
    and turn an existing unreadable config into an apparently empty one.
    Letting ``UnicodeDecodeError`` reach ``load_tsconfig_aliases_result``
    makes that state produce ``tsconfig_read_failed`` instead.
    """

    return Path(path).read_text(encoding="utf-8")


def load_tsconfig_aliases_result(
    workspace_root: str | Path,
    read_text: Callable[[Path], str],
    to_posix_rel: Callable[[str | Path], str],
) -> TsconfigLoadResult:
    """Load root tsconfig aliases without silently hiding degradation.

    Missing file -> ``({}, None)``.  Existing but unreadable/unparseable or
    structurally invalid file -> ``({}, TsconfigWarning(...))``.
    """

    tsconfig = Path(workspace_root) / "tsconfig.json"
    if tsconfig.is_symlink() and not tsconfig.exists():
        return TsconfigLoadResult(
            {},
            TsconfigWarning(
                code="tsconfig_read_failed",
                path="tsconfig.json",
                message="could not read tsconfig.json: broken symlink",
            ),
        )
    if not tsconfig.exists():
        return TsconfigLoadResult({})
    if not tsconfig.is_file():
        return TsconfigLoadResult(
            {},
            TsconfigWarning(
                code="tsconfig_read_failed",
                path="tsconfig.json",
                message="could not read tsconfig.json: not a regular file",
            ),
        )

    try:
        text = read_text(tsconfig)
        if not isinstance(text, str):
            raise TypeError(
                f"tsconfig reader returned {type(text).__name__}, expected str"
            )
    except FileNotFoundError:
        return TsconfigLoadResult({})
    except (OSError, TypeError, UnicodeDecodeError) as exc:
        return TsconfigLoadResult(
            {},
            TsconfigWarning(
                code="tsconfig_read_failed",
                path="tsconfig.json",
                message=f"could not read tsconfig.json: {exc}",
            ),
        )

    try:
        data = parse_tsconfig_jsonc(text, source="tsconfig.json")
        return TsconfigLoadResult(aliases_from_config_data(data, to_posix_rel))
    except TsconfigSyntaxError as exc:
        return TsconfigLoadResult(
            {},
            TsconfigWarning(
                code="tsconfig_parse_failed",
                path="tsconfig.json",
                message=(
                    "could not parse tsconfig.json; TypeScript path aliases "
                    f"were not loaded ({exc})"
                ),
                line=exc.line,
                column=exc.column,
                offset=exc.offset,
            ),
        )
    except TsconfigLoadError as exc:
        return TsconfigLoadResult(
            {},
            TsconfigWarning(
                code="tsconfig_invalid_shape",
                path="tsconfig.json",
                message=(
                    "could not load TypeScript path aliases from "
                    f"tsconfig.json: {exc}"
                ),
            ),
        )


def load_tsconfig_aliases(
    workspace_root: str | Path,
    read_text: Callable[[Path], str],
    to_posix_rel: Callable[[str | Path], str],
    *,
    on_warning: Optional[Callable[[TsconfigWarning], None]] = None,
) -> dict[str, str]:
    """Compatibility wrapper returning only aliases.

    Product integration should prefer :func:`load_tsconfig_aliases_result`
    or pass ``on_warning`` so the graph can disclose the degraded input.
    """

    result = load_tsconfig_aliases_result(workspace_root, read_text, to_posix_rel)
    if result.warning is not None and on_warning is not None:
        on_warning(result.warning)
    return result.aliases


__all__ = [
    "JsoncSyntaxError",
    "TsconfigLoadError",
    "TsconfigLoadResult",
    "TsconfigShapeError",
    "TsconfigSyntaxError",
    "TsconfigWarning",
    "aliases_from_config_data",
    "blank_comments",
    "blank_trailing_commas",
    "load_tsconfig_aliases",
    "load_tsconfig_aliases_result",
    "parse_jsonc",
    "parse_tsconfig_jsonc",
    "read_tsconfig_text",
    "strip_jsonc",
    "transform_jsonc_to_json",
]
