# Root cause — tsconfig.json (JSONC) silently ignored during path-alias resolution

## Observation → localization chain

1. **CLI level (minimal fixture):** identical 2-file TS projects differing only inside `tsconfig.json`. Strict JSON → Stage-1 reports `1 internal file edges, 0 unresolved`; bundle contains `file_import` + `imports_symbol` for `@app/util`. Adding one `//` comment *or* one trailing comma → `0 internal file edges, 1 unresolved`; resolved graph records the import as `external_or_unresolved`; the bundle keeps at most a fallback `imports_symbol` edge (and none when the symbol name is not globally unique). No warning is emitted (`warnings: []` in the resolved graph).
2. **Real repository (facebook/lexical @ `164af6a`):** removing only the five `//` comment lines from its root `tsconfig.json` raises Stage-1 internal file edges **1,263 → 5,519** on the identical tree — the comments alone cost ~4,256 edges. (Residual unresolved imports in the control are separate limitations/externals, not this defect.)
3. **Unit level:** `LanguageAwareImportResolver.tsconfig_aliases == {}` for the JSONC fixture vs `{'@app': 'src/app'}` for strict JSON; `_resolve_node_ts('@app/util')` returns `(None, None)` vs `('src/app/util.ts', 'node_ts_module_resolution')`. A comment-stripping parse applied in-memory restores resolution — the parse step is the sole cause.
4. **Expected behavior (independent oracle):** `tsconfig.json` is **JSONC** — comments and trailing commas are legal. Verified with the actual compiler: TypeScript 5.9.3 `tsc --showConfig` accepts both fixture variants and reports the `paths` mapping.

## Responsible code (installed wheel, unvibecode 0.3.15)

`shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py`, **`LanguageAwareImportResolver._load_tsconfig_aliases`, lines 1913–1931** (duplicated in `01_shipreadyv2_merged_graph_pipeline_5chunks.py`, line 1870):

```python
try:
    data = json.loads(safe_read_text(tsconfig))   # strict JSON only
    ...
except Exception:
    pass                                            # silent: aliases stay {}
return aliases
```

Any `json.loads` failure — comment, trailing comma, or any JSONC feature — discards **the entire alias table** with no log or warning. `_resolve_node_ts` then has no alias candidates for non-hardcoded prefixes, so alias imports fall through to `external_or_unresolved`. The later linker stage may resurrect an `imports_symbol` edge by global unique-symbol search, which (a) loses the `file_import` edge/map link, and (b) disappears entirely when another file exports the same name — making the failure look inconsistent rather than systematic.

**Earliest corrupted stage:** Stage-1 resolver construction (both lanes share the code). Parsing/extraction of the import itself is correct (the import appears, correctly attributed, in unresolved records).

## Fix direction (for maintainer validation, not submitted as code)
Parse `tsconfig.json` with a JSONC-tolerant loader (strip `//`/`/* */` comments and trailing commas outside string literals, or use a JSONC parser), and record a graph `warnings` entry when a tsconfig file exists but cannot be parsed. The correction experiment in `evidence/EXPERIMENT_LOG.md` (E15) demonstrates that tolerant parsing alone restores correct resolution.
