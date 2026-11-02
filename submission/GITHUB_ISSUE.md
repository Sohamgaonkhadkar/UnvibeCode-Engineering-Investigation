Title: [Bug] Connected Code Map — comments/trailing commas in a valid JSONC tsconfig silently discard all root path aliases

## 1. Problem summary
UnvibeCode loads TypeScript path aliases from the repository-root `tsconfig.json` with strict `json.loads`, inside a bare `except: pass`. A `tsconfig.json` is JSONC, however: TypeScript accepts `//` and `/* */` comments and trailing commas. If the file uses any of those legal features, UnvibeCode silently discards the **entire `compilerOptions.paths` table**, records imports through non-hardcoded aliases as `external_or_unresolved`, and emits no config warning.

This is not only a missing-edge count. On `meta/lexical`, five comment lines suppress 4,256 verified internal file relationships, and comparing the actual exported context bundles shows that **2,707 direct dependencies are absent from Optimal selections** (3,345 in Wider) until only those comments are removed. A developer therefore cannot tell that apparently disconnected or thin context is really “the config never loaded.”

## 2. Test environment
- UnvibeCode: **0.3.15** from PyPI (`unvibecode==0.3.15`)
- Clean verification: GitHub Actions `ubuntu-latest`, Python 3.12, ordinary pip installation
- Local replication: Linux x86_64, Python 3.11.2
- Independent compiler oracle: TypeScript **5.9.3**
- Public repositories:
  - https://github.com/meta/lexical @ `164af6a4df7114f35724c472152ca74877b6bd04`
  - https://github.com/ng-matero/ng-matero @ `d351bf5957d8c6dc9eca79d0c9b260c5b8d07822`
- Command: `python -m unvibecode review --repository "<path>"`
- Evidence/fixtures: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/arena/a5a17da4-unvibecode-engineering-investi (the pinned clean-CI run record is indexed in `evidence/tsconfig-jsonc/CI_VERIFICATION.md`; PR #1 shows the checks for the current branch head)

Environment note: my local investigation sandbox blocks tree-sitter grammar downloads, so the locally captured large-repo artifacts used a disclosed fallback grammar environment. That workaround is no longer the sole basis for the claim: the minimal CLI comparison and full lexical original/control comparison were rerun under the ordinary install in GitHub Actions with the same counts. The resolver defect itself also reproduces in pure Python with no grammar or hosted service. Full provenance is in `evidence/tsconfig-jsonc/CI_VERIFICATION.md` and `STANDARD_INSTALL_ATTEMPT.md` in the evidence repo.

## 3. Steps to reproduce
Minimal project (variants differ only in `tsconfig.json`):

```text
repo/
  tsconfig.json
  src/app/util.ts        -> export function util() { return 1; }
  src/feature/comp.ts    -> import { util } from "@app/util";
                            export function comp() { return util(); }
```

Strict control:

```json
{"compilerOptions": {"baseUrl": ".", "paths": {"@app/*": ["src/app/*"]}}}
```

JSONC variant: add one line comment, block comment, trailing comma, or use the combined fixture in the evidence repo. TypeScript accepts all of them. Then:

1. Check out the evidence branch linked above, then install the tested version:
   ```bash
   python -m pip install unvibecode==0.3.15
   ```
2. Run the one-command verifier:
   ```bash
   python reproduction/verify.py
   ```
   This checks the Python/package environment, runs the strict control and all JSONC variants, and then runs the original post-fix regression `python reproduction/repro_unit.py --expect-fixed`. On 0.3.15 it reports the defect only if that regression fails in exactly the four JSONC cases with `aliases={}` and `resolution=(None, None)`; the strict control gives `{'@app': 'src/app'}` and `@app/util -> src/app/util.ts`. The same verifier also runs the correction proof of concept and checks the committed lexical/ng-matero evidence counts.
3. Run the CLI on `reproduction/minimal_strict` and `reproduction/minimal_jsonc` (or `python reproduction/ci_cli_comparison.py --output-root ./cli-comparison-output`) and compare `[STAGE 1 COMPLETE]`, `connections.jsonl`, and `unresolved_relationships.jsonl`.
4. Real-repository check: run lexical at the pinned commit, then delete only lines 9–13 (five `//` comments) from its root `tsconfig.json` and run again.

## 4. Expected behavior
A comment or trailing comma must not change alias loading. TypeScript parses `tsconfig.json` as JSONC. This was verified with the actual compiler, not by inference from UnvibeCode:

- `tsc --showConfig` (5.9.3) accepts the strict and JSONC fixtures and reports `@app/*`; and
- the TypeScript compiler API parses lexical's config and resolves, for example, from `packages/lexical-react/src/ReactExtension.tsx`:
  - `lexical` → `packages/lexical/src/index.ts`
  - `@lexical/react/LexicalComposerContext` → `packages/lexical-react/src/LexicalComposerContext.ts`
  - `@lexical/react/LexicalContentEditable` → `packages/lexical-react/src/LexicalContentEditable.tsx`

UnvibeCode already resolves these aliases when the same config is strict JSON, so identical file relationships and context eligibility are expected without requiring users to rewrite a valid config.

## 5. Actual behavior
Minimal fixture:

- Strict JSON: `1 internal file edges, 0 unresolved`; bundle contains a `file_import` to `src/app/util.ts`.
- JSONC: `0 internal file edges, 1 unresolved`; `@app/util` is recorded `external_or_unresolved`. A global-symbol fallback may still create an `imports_symbol` connection, but there is no `file_import`; that fallback also disappears when the symbol name is not unique. The resolved graph has `warnings: []`.

Lexical:

| Tree | Internal file edges | Unresolved/external |
|---|---:|---:|
| as-is | 1,263 | 8,298 |
| only five comments removed | 5,519 | 4,042 |

The exported context changes materially:

| Lexical scope | Verified direct dependencies absent as-is, restored in control |
|---|---:|---:|
| Optimal (radius 1) | 2,707 |
| Wider (radius 2) | 3,345 |

For example, the as-is Optimal selection for `packages/lexical-react/src/ReactExtension.tsx` omits `LexicalComposerContext.ts`, `LexicalContentEditable.tsx`, `ReactProviderExtension.tsx`, `invariant.ts`, and lexical's entry file—all direct configured imports. The control includes chunks from each. This matters for work on the React extension's default editable surface, provider checks, or composer-context/theme behaviour.

The same mechanism reproduces on ng-matero: removing only two leading block comments changes 130 → 241 internal file edges, restoring 111 verified relationships and 107 direct dependencies in both Optimal and Wider selections.

## 6. Evidence
Responsible code in the installed wheel, `shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py:1913-1931` (duplicated at `01_shipreadyv2_merged_graph_pipeline_5chunks.py:1870-1887`):

```python
try:
    data = json.loads(safe_read_text(tsconfig))   # strict JSON only
    ...
except Exception:
    pass                                            # alias table silently stays {}
```

Causal chain: config found → strict parse throws → exception swallowed → `tsconfig_aliases = {}` → `_resolve_node_ts` has no configured alias candidates → file edge never enters Stage 1. This is the earliest point of loss. Import extraction is not the cause: lexical's scanned file sets (2,044 = 2,044) and extracted import records (9,562 = 9,562, same file/specifier/line) are identical between runs.

The earlier prefix-based count was re-audited rather than assumed. `analyze_alias_oracle.py` parses lexical's actual 220 `paths` patterns (184 exact, 36 wildcard), applies TypeScript-style exact/longest-prefix matching and file probing, and checks every control-only edge. **All 4,256 match the oracle-identified target; there are 0 as-is-only edges.** Independently, TypeScript 5.9.3's `resolveModuleName` was run over all 4,218 unique source/specifier pairs and again matched all 4,256 rows with zero mismatches. The import records are preserved with source file, line, specifier, target, pattern, and strategy in `lost_relationships.jsonl`.

The downstream count is likewise measured in the emitted bundles, not inferred from edges alone. Of the 4,218 lexical direct pairs at Optimal: 2,707 are absent as-is/restored in control, 434 are present in both via other links, 1,062 are absent in both, and 15 are present only as-is. At Wider: 3,345 restored, 472 in both, 398 in neither, 3 only as-is. Selection files change for 1,494 of 2,044 files in at least one scope. Narrow (radius 0) is not claimed as impact.

Correction check: replacing only the parse step in memory with a string-aware two-pass JSONC stripper—including `..., /* comment */}` and comment-like text inside string literals—restores all fixture resolutions without modifying the installed package (`correction_poc.py`). This is a proof of causation/feasibility, not a proposed production parser.

Clean-environment verification: GitHub Actions on a pinned ordinary install passed TypeScript fixture acceptance, unified affected-version verification, the minimal CLI comparison, and a full lexical rerun yielding 1,263 → 5,519 with 2,707 Optimal recoveries. In that PR check, green means the defect was reproduced and the raw `--expect-fixed` regression failed only for the exact documented empty-alias symptom; it does not mean expected JSONC behaviour already works. The raw regression remains available as an explicitly manual post-fix workflow. See `CI_VERIFICATION.md`; graph/bundle hashes and pinned inputs are in `ARTIFACT_MANIFEST.md`.

## 7. Impact and scope
This is a silent wrong-answer defect when a JS/TS repository's supported root `tsconfig.json` uses comments or trailing commas together with non-hardcoded path aliases. In lexical, 4,256 relationships are about 77% of the control's attainable internal file edges; source files with at least one outgoing file edge fall from 1,426 to 479. More importantly, thousands of real implementations become ineligible in exported Optimal/Wider context. Even after excluding tests/examples/playground, 446 package-source→package-source direct pairs are absent as-is and restored in at least one non-trivial scope.

The failure is masked in three ways: there is no parse warning, hardcoded `@/`/`~/`/relative resolution still works, and unique-symbol fallback can create some symbol links without the missing file relationship. The result is an apparently usable but materially incomplete Connected Code Map/context export.

Confirmed scope: deterministic on the fixtures, lexical, and ng-matero; both engine copies share the defective function. This report does not claim nested-tsconfig discovery, `extends`, Vite aliases, every `paths` pattern shape, or hosted business findings. Separate already-loaded alias-pattern limitations remain out of scope.

## 8. Suspected cause / suggested fix (if known)
Cause: `_load_tsconfig_aliases` treats a JSONC file as strict JSON and converts every parse error into an empty alias table with no diagnostic.

Suggested fix direction:

1. Parse root `tsconfig.json` with a maintained TypeScript-compatible JSONC parser (or equivalent string-aware handling), in both engine copies or through one shared loader.
2. If an existing config still cannot be parsed, emit a visible graph/log warning so a degraded alias table is distinguishable from a project that genuinely declares no aliases.

Validation: `python reproduction/verify.py --expect-fixed` (which runs the retained raw `repro_unit.py --expect-fixed`) should pass all JSONC fixtures including string-safety cases; the minimal JSONC CLI fixture should produce the file edge; lexical should reach 5,519 internal file edges with its config untouched; and the direct-dependency selection omissions should disappear relative to the comment-stripped control.

## 9. Duplicate check
Re-searched on 2026-11-02 through the GitHub issue-search API (open + closed; 322 issues through #417):

- `jsonc` → 0; `trailing comma` → 0; `_load_tsconfig_aliases` → 0; `comment tsconfig` → 0.
- `tsconfig` and `compilerOptions.paths` → only #153, #272, and #374.

Closest issues differ by mechanism:

- **#153/#272:** `@/` imports are recorded `hard_path_skipped` by the later linker. Here the Stage-1 resolver's alias table is empty before resolution, records are `external_or_unresolved`, and resolution returns immediately when config comments are removed.
- **#374:** the alias is only in `vite.config.ts`/a non-root setup. Here it is in the supported repository-root `tsconfig.json`.
- **#320:** `_js_import_symbols` extracts local binding names incorrectly. Here extraction is identical between as-is and control.
- **#262/#84:** a separate `../` path-normalization defect, excluded from this report.

No existing issue reports legal JSONC syntax in `tsconfig.json` silently emptying UnvibeCode's root path-alias table.
