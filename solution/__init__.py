"""Reference-solution package for the JSONC tsconfig investigation."""

from .tsconfig_jsonc import (
    TsconfigLoadError,
    TsconfigLoadResult,
    TsconfigSyntaxError,
    TsconfigWarning,
    load_tsconfig_aliases,
    load_tsconfig_aliases_result,
    parse_tsconfig_jsonc,
)

__all__ = [
    "TsconfigLoadError",
    "TsconfigLoadResult",
    "TsconfigSyntaxError",
    "TsconfigWarning",
    "load_tsconfig_aliases",
    "load_tsconfig_aliases_result",
    "parse_tsconfig_jsonc",
]
