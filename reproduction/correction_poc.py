#!/usr/bin/env python3
"""Correction proof-of-concept (NOT a submitted patch, does not modify the package):
replaces the alias-table loading *in memory* with a JSONC-tolerant parse and shows that
resolution is restored for every JSONC fixture.

The tolerant loader below is a character-level state machine: comments and trailing
commas are removed only *outside* string literals, so values containing '//', '/*' or
',' inside quotes survive (fixture minimal_stringsafety covers this). It is a tested
proof-of-concept demonstrating causation and fix feasibility — a production fix should
prefer a maintained JSONC parser and must additionally surface a warning on parse failure.

Run:  python reproduction/correction_poc.py    (exit 0 = correction validated)
"""
import importlib, importlib.util, json, sys
from pathlib import Path

from jsonc_tolerant import load_tsconfig_aliases, strip_jsonc

HERE = Path(__file__).resolve().parent
shipreadyv2 = importlib.import_module("shipreadyv2")
engine_path = sorted((Path(shipreadyv2.__file__).resolve().parent / "engine_sources").glob("00a_*.py"))[0]
spec = importlib.util.spec_from_file_location("unvibecode_fastlane_engine", engine_path)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)


def load_aliases_fixed(resolver) -> dict:
    return load_tsconfig_aliases(
        resolver.workspace_root,
        engine.safe_read_text,
        engine.to_posix_rel,
    )

EXPECTED = ("src/app/util.ts", "node_ts_module_resolution")
EXPECTED_NOTES = {
    "minimal_stringsafety": "docs at https://example.com/a/*not-a-comment*/,",
    "minimal_combined_jsonc": "literal text, not syntax: // /* */ ,",
}
failures = 0
for fixture in ("minimal_strict", "minimal_jsonc", "minimal_blockcomment", "minimal_trailingcomma", "minimal_stringsafety", "minimal_combined_jsonc"):
    root = (HERE / fixture).resolve()
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.ts"))
    resolver = engine.LanguageAwareImportResolver(root, files)
    before = (dict(resolver.tsconfig_aliases), resolver._resolve_node_ts("src/feature/comp.ts", "@app/util"))
    resolver.tsconfig_aliases = load_aliases_fixed(resolver)
    after = resolver._resolve_node_ts("src/feature/comp.ts", "@app/util")
    note_ok = True
    if fixture in EXPECTED_NOTES:
        parsed = json.loads(strip_jsonc(engine.safe_read_text(root / "tsconfig.json")))
        note_ok = parsed.get("x-note") == EXPECTED_NOTES[fixture]
    ok = after == EXPECTED and note_ok
    failures += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {fixture}: stock={before}  corrected aliases={resolver.tsconfig_aliases} resolution={after}")

print("RESULT:", "PASS — tolerant parse restores resolution (proof of concept)" if not failures else f"FAIL ({failures})")
sys.exit(0 if not failures else 1)
