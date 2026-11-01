Title: [Bug] Connected Code Map (tsconfig alias loading) — tsconfig.json with comments or trailing commas (valid JSONC) is silently ignored, dropping all path-alias edges

## 1. Problem summary
UnvibeCode loads TypeScript path aliases from the repository-root `tsconfig.json` with strict `json.loads`, inside a bare `except: pass`. But `tsconfig.json` is **JSONC** — the TypeScript compiler accepts `//` / `/* */` comments and trailing commas, and real projects use them. If the file contains any JSONC feature, the **entire alias table is silently discarded** (no warning anywhere), so every import through a custom path alias is recorded as `external_or_unresolved` and loses its Connected Code Map / context-bundle edges, while the review still presents the map as ready. On meta/lexical, five comment lines in `tsconfig.json` suppress 4,256 internal file edges (details in §5–§7). Because nothing signals the dropped configuration, a developer cannot distinguish "genuinely disconnected codebase" from "config never loaded".

## 2. Test environment
- UnvibeCode version: **0.3.15** (PyPI wheel; engine `shipreadyv2`, runner `shipreadyv2.customer_mvp.v10`)
- Operating system / Python version: Linux x86_64 (kernel 6.1.158), Python **3.11.2**
- Public repository URL and commit: https://github.com/meta/lexical @ `164af6a4df7114f35724c472152ca74877b6bd04`, plus 2-file minimal fixtures (§3)
- Relevant command: `python -m unvibecode review --repository "<path>"`
- Environment note (full record in evidence repo): my sandbox blocks GitHub release-asset downloads, so `tree-sitter-language-pack` cannot fetch grammars there (direct error: `DownloadError: Failed to fetch manifest from https://github.com/xberg-io/tree-sitter-language-pack/releases/download/v1.22.1/parsers.json`). For CLI-scale runs I therefore supplied grammars via the engine's own documented fallback slot (`tree_sitter_languages.get_parser`, backed by the official PyPI grammar wheels; validated by reproducing `docs/GO_SUPPORT.md`'s chi reference run exactly: 89 files / 1,050 / 58). The mechanism reported here is pure-Python config parsing: on a **vanilla install with no workaround**, the unit reproducer in §3 reproduces the defect, and extracted imports are provably identical between the compared runs (§6), so grammar sourcing cannot manufacture the delta. On an unrestricted machine the CLI steps apply as-is.

## 3. Steps to reproduce
Minimal fixture (variants differ **only** inside `tsconfig.json`):

```
repo/
  tsconfig.json
  src/app/util.ts        →  export function util(){ return 1; }
  src/feature/comp.ts    →  import { util } from "@app/util";
                             export function comp(){ return util(); }
```
Variant A (strict JSON): `{"compilerOptions": {"baseUrl": ".", "paths": {"@app/*": ["src/app/*"]}}}` — Variant B: same + one `// project configuration` line. (`/* */` comments and trailing commas reproduce identically; all fixture variants are in the evidence repo under `reproduction/`.)

1. `python -m pip install --upgrade unvibecode`
2. Fastest check (no CLI, no network): `python reproduction/repro_unit.py` from the evidence repo. It loads the installed resolver, asserts alias-table contents and resolution per fixture, and exits 0 with `BUG REPRODUCED` on 0.3.15 (`--expect-fixed` runs it as a post-fix regression test). Observed per-fixture: strict → `{'@app': 'src/app'}`, `@app/util → src/app/util.ts`; each JSONC variant → `{}`, `(None, None)`; negative control (no alias declared) correctly unresolved in both.
3. CLI check: run the review command on each variant; compare the `STAGE 1 COMPLETE` line in `technical-logs/connected_code_map.log` and `connections.jsonl` in the emitted `*-repository-context.zip` (§5).
4. Real repository: clone meta/lexical at the commit above, run the review; then delete only the five `//` comment lines (lines 9–13) from its root `tsconfig.json` and re-run.

## 4. Expected behavior
Comments/trailing commas must not change alias loading: `tsconfig.json` is parsed by TypeScript as JSONC. Verified against the actual compiler — TypeScript 5.9.3 `tsc --showConfig -p tsconfig.json` accepts the comment and trailing-comma variants and reports the `@app/*` mapping. UnvibeCode itself resolves these aliases correctly when the file is strict JSON (Variant A), so identical resolution is expected for Variant B, and lexical's full edge set is expected without modifying its config.

## 5. Actual behavior
- Minimal, Variant B: `[STAGE 1 COMPLETE] 2 files, 0 internal file edges, 1 unresolved/external imports`; the graph records `@app/util` as `external_or_unresolved`, `warnings` stays empty. The bundle keeps at most a fallback `imports_symbol` edge (unique-symbol search) with no `file_import` edge — and **zero** connections once a second file exports the same symbol name. Variant A produces both edges and `1 internal file edges, 0 unresolved`.
- meta/lexical as-is: `2,044 files, 1,263 internal file edges, 8,298 unresolved/external imports`. Identical tree with only the 5 comment lines removed: **`5,519` edges, `4,042` unresolved**. Repeated runs are byte-identical (deterministic).

## 6. Evidence
- Responsible code (installed wheel): `shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py`, `LanguageAwareImportResolver._load_tsconfig_aliases`, **lines 1913–1931** (duplicated in `01_shipreadyv2_merged_graph_pipeline_5chunks.py:1870`, so both lanes are affected):
  ```python
  try:
      data = json.loads(safe_read_text(tsconfig))   # strict JSON only
      ...
  except Exception:
      pass                                            # alias table silently stays {}
  ```
  Chain: `tsconfig.json` → `safe_read_text` → strict parse throws on first comment/comma → exception swallowed → `tsconfig_aliases = {}` → `_resolve_node_ts` has no alias candidates → edge never enters the graph. This config-read step is the earliest point where valid information is lost; extraction downstream is correct (next bullet).
- Specificity at graph-record level (lexical as-is vs control, script + output in evidence repo): scanned file sets **identical** (2,044 = 2,044) and extracted import records **identical** (9,562 = 9,562 file/specifier/line tuples) — the control changes no analyzer input besides config parseability. File edges present only in control: **4,256, 100% alias-prefixed specifiers** (`lexical`, `@lexical/…`), 100% via `node_ts_module_resolution`; edges lost in control: **0**. Secondary propagation: +10,091 symbol edges (100% alias-class). Unresolved in *both* runs (unrelated): 2,448 bare/external, 1,592 relative/absolute (incl. the known `../` class #262), 2 alias imports failing for other pattern reasons (§8 scope note).
- Oracle: `tsc --showConfig` (TypeScript 5.9.3) on the JSONC fixtures prints the `paths` mapping.
- Correction proof-of-concept: a string-aware tolerant parse (comments/trailing commas stripped only outside string literals) applied in memory — package unmodified — restores resolution on all fixtures including a string-safety case (`https://…/*…*/` inside quotes). It demonstrates causation/feasibility; it is not proposed as the production implementation.
- Evidence repository (fixtures, assertions-based reproducers, comparison script/output, graph excerpts, experiment log incl. negative results): https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation (branch `arena/a5a17da4-unvibecode-engineering-investi`).

## 7. Impact and scope
Silent wrong-answer defect affecting any JS/TS repository whose root `tsconfig.json` uses JSONC features — legal and common (hand-maintained configs; meta/lexical and pmndrs/zustand both ship commented tsconfigs today). Directly lost: all custom path-alias **file** edges (lexical: 4,256 of the control's 5,519, i.e. ~77% of attainable file edges; source files with ≥1 file edge drop from 1,426 to 479), plus 10,091 downstream symbol edges that connected-context selections and later stages build on. The hardcoded `@/` → `src/` branch keeps working, so partial alias support masks the failure. Deterministic; reproduced on 1 pinned real repository + 5 controlled fixture variants; both engine lanes share the defective function. Hosted/LLM stages are not needed to reproduce and are not part of this claim (lexical exceeds the 2M-token business-review threshold, so its runs exercise exactly the local pipeline at issue).

## 8. Suspected cause / suggested fix (if known)
Cause: `_load_tsconfig_aliases` treats `tsconfig.json` as strict JSON and swallows all parse failures, returning an empty alias table with no diagnostic. Suggested direction: (1) parse tsconfig with a JSONC-tolerant loader (a maintained JSONC parser, or careful string-aware stripping), (2) emit a visible warning (graph `warnings`/log) when a tsconfig exists but cannot be parsed, so degraded runs are distinguishable. Validation: `repro_unit.py --expect-fixed` must pass all fixtures, and lexical must reach the control counts (5,519 file edges) with its config untouched. Scope note: separate alias-*pattern* limitations exist (e.g. exact-file targets like `"zustand": ["./src/index.ts"]`, incl. the 2 still-unresolved lexical alias imports) — observed during testing, intentionally **excluded** from this single-defect report.

## 9. Duplicate check
Re-searched 2026-11-02 via the GitHub search API (open+closed, 322 issues to #417): `tsconfig` → only #153/#272/#374; `jsonc` → 0; `trailing comma` → 0; `_load_tsconfig_aliases` → 0. Closest reports read at body/mechanism level:
- **#153** (0.3.3) and **#272** (0.3.15): `@/` imports recorded `resolution_status: hard_path_skipped` (`detail: alias_prefix_@/`) — a Stage-2 **linker** hard-skip of alias-prefixed specifiers. Here the alias table never loads at Stage-1 **resolver** construction and records show `external_or_unresolved`; different function, stage, trigger (config file lexical syntax), and fix.
- **#374**: same `hard_path_skipped` family; alias defined only in `vite.config.ts` (never in a root tsconfig). Here the alias is in the supported root `tsconfig.json` and resolves correctly the moment comments are removed.
- **#320**: `_js_import_symbols` mis-extracts local binding names (extraction stage). Here extraction is provably correct — identical import records in both runs (§6).
- **#262/#84** (`../` normalization): distinct resolver defect, also reproduced during this investigation and deliberately not filed.
