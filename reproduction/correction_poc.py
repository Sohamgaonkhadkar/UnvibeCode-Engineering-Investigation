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

HERE = Path(__file__).resolve().parent
shipreadyv2 = importlib.import_module("shipreadyv2")
engine_path = sorted((Path(shipreadyv2.__file__).resolve().parent / "engine_sources").glob("00a_*.py"))[0]
spec = importlib.util.spec_from_file_location("unvibecode_fastlane_engine", engine_path)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)

def strip_jsonc(text: str) -> str:
    out, i, n, in_str, esc = [], 0, len(text), False, False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            i += 1; continue
        if ch == '"':
            in_str = True; out.append(ch); i += 1; continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n": i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"): i += 1
            i += 2; continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n": j += 1
            if j < n and text[j] in "}]":  # trailing comma -> drop it
                i += 1; continue
        out.append(ch); i += 1
    return "".join(out)

def load_aliases_fixed(resolver) -> dict:
    tsconfig = resolver.workspace_root / "tsconfig.json"
    if not tsconfig.exists():
        return {}
    data = json.loads(strip_jsonc(engine.safe_read_text(tsconfig)))
    paths = data.get("compilerOptions", {}).get("paths", {})
    base_url = data.get("compilerOptions", {}).get("baseUrl", ".")
    aliases = {}
    for alias, targets in paths.items():
        if not targets: continue
        aliases[alias.replace("/*", "").rstrip("/")] = engine.to_posix_rel(
            Path(base_url) / str(targets[0]).replace("/*", "").rstrip("/"))
    return aliases

EXPECTED = ("src/app/util.ts", "node_ts_module_resolution")
failures = 0
for fixture in ("minimal_strict", "minimal_jsonc", "minimal_blockcomment", "minimal_trailingcomma", "minimal_stringsafety"):
    root = (HERE / fixture).resolve()
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.ts"))
    resolver = engine.LanguageAwareImportResolver(root, files)
    before = (dict(resolver.tsconfig_aliases), resolver._resolve_node_ts("src/feature/comp.ts", "@app/util"))
    resolver.tsconfig_aliases = load_aliases_fixed(resolver)
    after = resolver._resolve_node_ts("src/feature/comp.ts", "@app/util")
    ok = after == EXPECTED
    failures += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {fixture}: stock={before}  corrected aliases={resolver.tsconfig_aliases} resolution={after}")

print("RESULT:", "PASS — tolerant parse restores resolution (proof of concept)" if not failures else f"FAIL ({failures})")
sys.exit(0 if not failures else 1)
