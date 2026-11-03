#!/usr/bin/env python3
"""Compatibility shim for the reference loader in ``solution/tsconfig_jsonc.py``.

Older investigation scripts imported this module name.  The implementation
now lives in one place so the unit tests, differential validation, correction
harness, and causal intervention all exercise exactly the same loader.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from solution.tsconfig_jsonc import (  # noqa: E402,F401
    JsoncSyntaxError,
    TsconfigLoadError,
    TsconfigLoadResult,
    TsconfigShapeError,
    TsconfigSyntaxError,
    TsconfigWarning,
    aliases_from_config_data,
    blank_comments,
    blank_trailing_commas,
    load_tsconfig_aliases,
    load_tsconfig_aliases_result,
    parse_jsonc,
    parse_tsconfig_jsonc,
    strip_jsonc,
    transform_jsonc_to_json,
)

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
    "strip_jsonc",
    "transform_jsonc_to_json",
]
