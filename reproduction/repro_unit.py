#!/usr/bin/env python3
"""Unit-level reproduction for: tsconfig.json with JSONC features is silently ignored
by UnvibeCode's path-alias loading (LanguageAwareImportResolver._load_tsconfig_aliases).

Needs: Python 3.11+ and an installed `unvibecode` package. No network, no tree-sitter,
no hosted service. Works on Windows/macOS/Linux.

    python -m pip install --upgrade unvibecode
    python reproduction/repro_unit.py                # BUG-REPRO mode (default)
    python reproduction/repro_unit.py --expect-fixed # REGRESSION mode

Modes:
  * BUG-REPRO (default): asserts the *buggy* behavior observed in 0.3.15.
    Exit 0 and "BUG REPRODUCED" mean the defect is present in the installed version.
  * REGRESSION (--expect-fixed): asserts the *correct* behavior (JSONC configs load
    exactly like strict JSON, per TypeScript semantics). Exit 0 only once fixed;
    on 0.3.15 it FAILS (exit 1) — that failure is the expected pre-fix state.

Fixtures (subdirs of this folder): minimal_strict / minimal_jsonc (// comment) /
minimal_blockcomment (/* */) / minimal_trailingcomma / minimal_noalias (negative control).
"""
import importlib, importlib.metadata, importlib.util, sys
from pathlib import Path

EXPECT_FIXED = "--expect-fixed" in sys.argv
HERE = Path(__file__).resolve().parent

# --- locate the installed distribution (no hardcoded paths) ---
try:
    version = importlib.metadata.version("unvibecode")
except importlib.metadata.PackageNotFoundError:
    sys.exit("FATAL: unvibecode is not installed. Run: python -m pip install --upgrade unvibecode")
shipreadyv2 = importlib.import_module("shipreadyv2")
pkg_root = Path(shipreadyv2.__file__).resolve().parent
engine_candidates = sorted((pkg_root / "engine_sources").glob("00a_*.py"))
if not engine_candidates:
    sys.exit(f"FATAL: Fast Lane engine source not found under {pkg_root / 'engine_sources'}")
engine_path = engine_candidates[0]

# --- load the real resolver implementation from the installed wheel ---
spec = importlib.util.spec_from_file_location("unvibecode_fastlane_engine", engine_path)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)
Resolver = engine.LanguageAwareImportResolver

print(f"unvibecode version : {version}")
print(f"engine under test  : {engine_path}")
print(f"mode               : {'REGRESSION (expect correct JSONC handling)' if EXPECT_FIXED else 'BUG-REPRO (expect 0.3.15 defect)'}")
print("-" * 78)

failures = []
def check(name, condition, detail):
    print(f"{'PASS' if condition else 'FAIL'}  {name}: {detail}")
    if not condition:
        failures.append(name)

def probe(fixture):
    root = (HERE / fixture).resolve()
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.ts"))
    resolver = Resolver(root, files)
    return resolver.tsconfig_aliases, resolver._resolve_node_ts("src/feature/comp.ts", "@app/util")

# Correct semantics (TypeScript: tsconfig is JSONC; verified with tsc --showConfig):
EXPECTED_ALIASES = {"@app": "src/app"}
EXPECTED_RESOLUTION = ("src/app/util.ts", "node_ts_module_resolution")

for fixture in ("minimal_strict", "minimal_jsonc", "minimal_blockcomment", "minimal_trailingcomma"):
    aliases, resolution = probe(fixture)
    if EXPECT_FIXED:
        check(fixture, aliases == EXPECTED_ALIASES and resolution == EXPECTED_RESOLUTION,
              f"aliases={aliases} resolution={resolution} (expected aliases={EXPECTED_ALIASES}, resolution={EXPECTED_RESOLUTION})")
    elif fixture == "minimal_strict":
        check(fixture, aliases == EXPECTED_ALIASES and resolution == EXPECTED_RESOLUTION,
              f"strict-JSON control resolves: aliases={aliases} resolution={resolution}")
    else:
        check(fixture, aliases == {} and resolution == (None, None),
              f"JSONC defect present: aliases={aliases} resolution={resolution} (config silently discarded)")

# Negative control: fixture without the alias in paths must NOT resolve in any mode/version.
root = (HERE / "minimal_noalias").resolve()
files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.ts"))
resolver = Resolver(root, files)
neg = resolver._resolve_node_ts("src/feature/comp.ts", "@app/util")
rel = resolver._resolve_node_ts("src/feature/comp.ts", "./local")
check("minimal_noalias (negative control)",
      resolver.tsconfig_aliases == {} and neg == (None, None) and rel == ("src/feature/local.ts", "node_ts_module_resolution"),
      f"aliases={resolver.tsconfig_aliases} absent-alias={neg} relative-import-still-works={rel}")

print("-" * 78)
if failures:
    print(f"RESULT: FAIL ({len(failures)} check(s)): {failures}")
    sys.exit(1)
print("RESULT:", "PASS — correct JSONC handling confirmed" if EXPECT_FIXED
      else "PASS — BUG REPRODUCED (JSONC tsconfig silently discarded; strict-JSON control resolves)")
sys.exit(0)
