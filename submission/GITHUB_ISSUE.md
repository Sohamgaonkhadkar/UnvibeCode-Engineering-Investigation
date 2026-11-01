Title: [Bug] Connected Code Map (tsconfig alias loading) — a tsconfig.json containing comments or trailing commas (valid JSONC) is silently ignored, dropping all path-alias edges

## 1. Problem summary
UnvibeCode loads TypeScript path aliases from the repository-root `tsconfig.json` using strict `json.loads`. Real `tsconfig.json` files are **JSONC**: the TypeScript compiler accepts `//` and `/* */` comments and trailing commas, and many projects/scaffolds use them. If the file contains any JSONC feature, UnvibeCode silently discards the **entire alias table** (the parse error is swallowed, no warning is emitted), so imports through custom path aliases (e.g. `@app/util`, `@lexical/code`) are recorded as `external_or_unresolved` and lose their Connected Code Map / repository-context edges — while the run still reports the Connected Code Map as ready. On `facebook/lexical`, five comment lines in `tsconfig.json` alone cost **4,256 of 5,519 internal file edges (~77%)**. A developer trusting the map (or feeding the context bundle to an LLM) gets a repository graph in which most cross-package links are missing, with nothing indicating that configuration was dropped.

## 2. Test environment
- UnvibeCode version: **0.3.15** (PyPI wheel; engine `shipreadyv2`, runner `shipreadyv2.customer_mvp.v10`)
- Operating system / Python version: Linux x86_64 (kernel 6.1.158), Python **3.11.2**
- Public repository URL and commit: https://github.com/facebook/lexical @ `164af6a4df7114f35724c472152ca74877b6bd04` (plus a 2-file minimal fixture, section 3)
- Relevant command: `python -m unvibecode review --repository "<path>"`
- Environment note (transparency): my sandbox blocks release-asset downloads, so `tree-sitter-language-pack` could not fetch grammars there (cf. #378). For CLI runs I supplied grammars through the engine's own documented fallback slot (`tree_sitter_languages.get_parser`, backed by the official PyPI grammar wheels + tree-sitter 0.26). This was validated against your own reference numbers: go-chi/chi @ `9f8adb1` reproduced `docs/GO_SUPPORT.md` exactly (89 files, 1,050 file edges, 58 package edges). The defect itself is pure-Python config parsing, and the unit reproducer in section 3 needs no grammar and no network. On a normal installation (grammar download succeeds) the CLI steps below apply as-is.

## 3. Steps to reproduce
Minimal fixture (two variants; the **only** difference is inside `tsconfig.json`):

```
repo/
  tsconfig.json
  src/app/util.ts        →  export function util(){ return 1; }
  src/feature/comp.ts    →  import { util } from "@app/util";
                             export function comp(){ return util(); }
```
- Variant A (strict JSON): `{"compilerOptions": {"baseUrl": ".", "paths": {"@app/*": ["src/app/*"]}}}`
- Variant B (JSONC): same, plus one `// project configuration` comment line (a trailing comma instead of the comment reproduces identically).

1. `python -m pip install --upgrade unvibecode`
2. `python -m unvibecode review --repository "<repo>"` for each variant.
3. Compare `technical-logs/connected_code_map.log` (`STAGE 1 COMPLETE` line) and `connections.jsonl` inside the emitted `*-repository-context.zip`.

Unit-level equivalent (seconds, no CLI): instantiate `LanguageAwareImportResolver` from `shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py` on each fixture root and call `_resolve_node_ts("src/feature/comp.ts", "@app/util")`. Observed: A → `tsconfig_aliases={'@app': 'src/app'}`, resolves to `src/app/util.ts`; B → `tsconfig_aliases={}`, returns `(None, None)`.

Real repository: clone `facebook/lexical` at the commit above, run the same command, and note the Stage-1 line. Then delete only the five `//` comment lines (lines 9–13) from its root `tsconfig.json` and re-run.

## 4. Expected behavior
`tsconfig.json` is a JSONC format: comments and trailing commas are legal and must not affect alias loading. Verified with the actual compiler — TypeScript 5.9.3 `tsc --showConfig -p tsconfig.json` accepts both variants (and the trailing-comma variant) and reports the `@app/*` paths mapping. UnvibeCode already resolves these aliases correctly when the file is strict JSON (Variant A), so the expected behavior is identical resolution for Variant B, and the full Stage-1 edge set on lexical without modifying its config.

## 5. Actual behavior
- Variant B (minimal): `STAGE 1 COMPLETE: 2 files, 0 internal file edges, 1 unresolved/external imports`. The resolved graph lists `@app/util` under `external_or_unresolved`; `warnings` is empty. The context bundle keeps at most a fallback `imports_symbol` edge (global unique-symbol match) with **no `file_import` edge**; adding a second file that also exports `util` reduces the result to **zero connections**, while the strict-JSON control still resolves correctly.
- facebook/lexical as-is: `2,044 files, 1,263 internal file edges, 8,298 unresolved/external imports`; bundle contains 1,254 `file_import` records and only 479 source files have any file edge.
- Same tree with only the 5 comment lines removed: **`5,519` internal file edges, `4,042` unresolved**; 5,472 `file_import` records; 1,426 source files with edges. (Remaining unresolved imports in the control are externals/other limitations, not this defect.)

## 6. Evidence
- File/function: `shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py`, `LanguageAwareImportResolver._load_tsconfig_aliases` (lines 1913–1931); duplicated in `01_shipreadyv2_merged_graph_pipeline_5chunks.py` (line 1870), so both lanes are affected:
  ```python
  try:
      data = json.loads(safe_read_text(tsconfig))   # strict JSON only
      ...
  except Exception:
      pass                                            # alias table silently stays {}
  ```
- Causal isolation: import extraction is correct (the import appears in unresolved records with right file/line); only alias-table loading fails. Parsing the same file with comments stripped (in-memory, nothing else changed) restores `@app/util → src/app/util.ts`.
- Oracle output: `tsc --showConfig` (TypeScript 5.9.3) on Variant B prints the `paths` mapping — the config is valid input for the toolchain whose semantics are being reimplemented.
- Full experiment log, fixtures, verifier, and the lexical Stage-1 comparison: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation (`evidence/EXPERIMENT_LOG.md`, `evidence/tsconfig-jsonc/`, `reproduction/`).

## 7. Impact and scope
Wrong-answer (silent data loss), not a crash. Any JS/TS repository whose root `tsconfig.json` uses comments/trailing commas — legal, common in hand-maintained configs (lexical, zustand, VS Code-scaffolded configs, etc.) — loses **every** custom path-alias file edge in the Connected Code Map and context bundle, degrading connected-code downloads and any downstream workflow/risk reasoning built on the graph. Measured blast radius on lexical: ~77% of internal file edges missing; 947 additional source files gain edges once comments are removed. The hardcoded `@/` → `src/` branch still works, which makes the failure easy to miss: some aliases resolve, custom ones silently do not. Reproduced on 1 real repository at pinned commit + 4 minimal fixture variants (comment-only, trailing-comma-only, ambiguous-symbol pair); deterministic across repeated runs.

## 8. Suspected cause / suggested fix (if known)
Cause: `_load_tsconfig_aliases` treats `tsconfig.json` as strict JSON and swallows all parse failures, returning an empty alias table with no warning. Suggested fix: parse with a JSONC-tolerant loader (strip `//`/`/* */` comments and trailing commas outside string literals, or use a JSONC parser), and record a warning in the graph/logs when a `tsconfig.json` exists but cannot be parsed, so silent degradation becomes visible. Validation: the fixtures above — after the fix, Variants A and B must produce identical resolution, and lexical's Stage-1 edge count should reach the control value (5,519) without touching its config. (Separate alias-pattern limitations observed while testing, e.g. exact-file targets like `"zustand": ["./src/index.ts"]`, are intentionally **not** part of this report.)

## 9. Duplicate check
Searched all open+closed issues (322, to #417) by symptom, component, function name, and mechanism (`tsconfig` and `jsonc` return zero issues). Closest reports, read in full:
- **#374** (`@/` aliases `hard_path_skipped` although defined in `vite.config.ts`): different stage/mechanism — linker hard-skip when the alias is *not* in a root tsconfig at all. Here the alias is in the supported root `tsconfig.json` but the file fails strict-JSON parsing in `_load_tsconfig_aliases`, recorded as `external_or_unresolved`.
- **#272 / #153** (`@/` aliases skipped): predate the current alias support; 0.3.15 resolves `@/` and tsconfig aliases when the config is strict JSON (control above).
- **#320** (`_js_import_symbols` alias collection): import-clause symbol extraction, unrelated to config loading; our imports extract correctly.
- **#262 / #84** (`../` normalization): a distinct resolver defect I also reproduced during this investigation and am deliberately not filing, to show the check was done at cause level.
