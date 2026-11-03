Title: [Bug] Connected Code Map — comments/trailing commas in a valid JSONC tsconfig silently discard all root path aliases

## 1. Problem summary
UnvibeCode loads TypeScript path aliases from the repository-root `tsconfig.json` with strict `json.loads`, inside a bare `except: pass`. A `tsconfig.json` is JSONC, however: TypeScript accepts `//` and `/* */` comments and trailing commas. If the file uses any of those legal features, UnvibeCode silently discards the **entire `compilerOptions.paths` table**, records imports through non-hardcoded aliases as `external_or_unresolved`, and emits no config warning.

This is not only a missing-edge count. On `meta/lexical`, five comment lines suppress 4,256 verified internal file relationships, and comparing the actual exported context bundles shows that **2,707 direct dependencies are absent from Optimal selections** (3,345 in Wider) until only those comments are removed. A developer therefore cannot tell that apparently disconnected or thin context is really “the config never loaded.” The same loader AST is present in every published PyPI wheel from 0.3.0 through 0.3.15, and a bounded public-config sample confirms that this syntax/alias combination occurs outside the two pinned benchmark repositories.

### Evidence at a glance

| Layer checked | Result |
|---|---|
| Independent compiler expectation | TypeScript 5.9.3 accepts the JSONC configs; its resolver matches **4,256/4,256** lexical relationship rows with **0 mismatches** |
| Isolated mechanism | Strict JSON loads `{'@app': 'src/app'}`; each legal JSONC variant returns `{}` and no resolution, while lexical import extraction is unchanged at **9,562 = 9,562** records |
| Public-repository graphs | Lexical rises **1,263 → 5,519** internal file edges after removing only five comments; independent ng-matero rises **130 → 241** after removing only two block comments |
| Exported context | **2,707** verified direct dependencies are restored in lexical Optimal selections and **3,345** in Wider; for `ReactExtension.tsx`, five named direct dependencies absent as-is are present in the control |
| Reversible correction | On both resolver copies: original **fails → comments removed restores → original restored fails → in-memory reference loader restores → stock restored fails**. On untouched lexical, that loader also restores the actual Fast Lane graph/context |
| Published-release scope | All **106** PyPI wheels for 0.3.0–0.3.15 were digest-verified; all **212** engine copies contain the same vulnerable loader AST |
| Public-config exposure | In a bounded first-returned GitHub code-search sample, **35 unique affected root-config contents** (174 path entries) were TypeScript-verified among 139 eligible unique contents; this is not a prevalence estimate |
| Reference solution | A dependency-free JSONC loader agrees with TypeScript 5.9.3 on **514/514** curated/generated valid documents and returns a structured warning for malformed existing configs |
| Clean automation | Ordinary-install GitHub Actions passes the fixture, CLI, full causal-sequence, lexical stock/control, and in-memory-corrected lexical checks |

## 2. Test environment
- UnvibeCode: **0.3.15** from PyPI (`unvibecode==0.3.15`)
- Clean verification: GitHub Actions `ubuntu-latest`, Python 3.12, ordinary pip installation
- Local replication: Linux x86_64, Python 3.11.2
- Independent compiler oracle: TypeScript **5.9.3**; Microsoft `jsonc-parser` **3.3.1** is used only as a second differential oracle for the reference solution
- Public repositories:
  - https://github.com/meta/lexical @ `164af6a4df7114f35724c472152ca74877b6bd04`
  - https://github.com/ng-matero/ng-matero @ `d351bf5957d8c6dc9eca79d0c9b260c5b8d07822`
- Command: `python -m unvibecode review --repository "<path>"`
- Evidence/fixtures: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/02aed1bf04988478c49f6e15257d00b25dbc0b35 (commit-pinned snapshot containing the scripts and machine-readable evidence; the clean-CI run record is indexed in `evidence/tsconfig-jsonc/CI_VERIFICATION.md`. Evidence-repo PR #1 contains the original verified investigation, and follow-up PR #2 at https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/2 contains the reversible-intervention strengthening and its current check rollup.)

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

1. Check out the commit-pinned evidence snapshot linked above, then install the tested version:
   ```bash
   python -m pip install unvibecode==0.3.15
   ```
2. Run the one-command verifier:
   ```bash
   python reproduction/verify.py
   ```
   This checks the Python/package environment, runs the strict control and all JSONC variants, and then runs the original post-fix regression `python reproduction/repro_unit.py --expect-fixed`. On 0.3.15 it reports the defect only if that regression fails in exactly the four JSONC cases with `aliases={}` and `resolution=(None, None)`; the strict control gives `{'@app': 'src/app'}` and `@app/util -> src/app/util.ts`. The same verifier also runs the reference-solution Python corpus and integration check, the reversible A/B/C/D/E intervention and targeted boundaries on both shipped resolver copies, and checks the committed lexical/ng-matero, reference-validation, release-scope, and exposure-sample counts.
3. For the full graph/context form of that intervention, run:
   ```bash
   python reproduction/causal_intervention.py --full-pipeline --output causal-intervention.json
   ```
4. Run the CLI on `reproduction/minimal_strict` and `reproduction/minimal_jsonc` (or `python reproduction/ci_cli_comparison.py --output-root ./cli-comparison-output`) and compare `[STAGE 1 COMPLETE]`, `connections.jsonl`, and `unresolved_relationships.jsonl`.
5. Real-repository check: run lexical at the pinned commit, then delete only lines 9–13 (five `//` comments) from its root `tsconfig.json` and run again.

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

Representative exported-context case — `packages/lexical-react/src/ReactExtension.tsx`, Optimal scope:

| Exported Optimal selection | Original JSONC | Only comments removed |
|---|---:|---:|
| Included files | 4 | 28 |
| Estimated tokens recorded in the bundle | 7,325 | 37,769 |
| Verified direct configured dependencies absent, then restored | — | 5 |

The restored five are not anonymous neighbours:

- `LexicalContentEditable.tsx` — defines the actual `<ContentEditable />` placed in the extension's default config, including its placeholder/context behaviour;
- `LexicalComposerContext.ts` — defines the `[editor, {getTheme}]` composer-context tuple that `ReactExtension.build()` constructs and returns;
- `ReactProviderExtension.tsx` — defines the provider peer whose presence `build()` checks before constructing the React component;
- `invariant.ts` — implements the assertion used when that provider peer is missing; and
- `packages/lexical/src/index.ts` — the core public entry for `defineExtension`, `declarePeerDependency`, and `shallowMergeConfig`, the APIs used to define and configure this extension.

A sixth configured direct dependency, `LexicalErrorBoundary.tsx`, is present in both selections. The important observation is therefore not simply that the control is larger—more tokens are not automatically better context—but that chunks from five TypeScript-verified direct dependencies become available. This establishes an observable difference in the exported context; it does not by itself prove that any particular LLM answer will improve. The chunk-level record is [`selection_case_react_extension.json`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/02aed1bf04988478c49f6e15257d00b25dbc0b35/evidence/tsconfig-jsonc/selection_case_react_extension.json).

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

The earlier prefix-based count was re-audited rather than assumed. `analyze_alias_oracle.py` parses lexical's actual 220 `paths` patterns (184 exact, 36 wildcard), applies TypeScript-style exact/longest-prefix matching and file probing, and checks every control-only edge. **All 4,256 match the oracle-identified target; there are 0 as-is-only edges.** Independently, TypeScript 5.9.3's `resolveModuleName` was run over all 4,218 unique source/specifier pairs and again matched all 4,256 rows with zero mismatches. The import records are preserved with source file, line, specifier, target, pattern, and strategy in [`lost_relationships.jsonl`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/02aed1bf04988478c49f6e15257d00b25dbc0b35/evidence/tsconfig-jsonc/lost_relationships.jsonl).

The downstream count is likewise measured in the emitted bundles, not inferred from edges alone. Of the 4,218 lexical direct pairs at Optimal: 2,707 are absent as-is/restored in control, 434 are present in both via other links, 1,062 are absent in both, and 15 are present only as-is. At Wider: 3,345 restored, 472 in both, 398 in neither, 3 only as-is. Selection files change for 1,494 of 2,044 files in at least one scope. Narrow (radius 0) is not claimed as impact.

Reversible causal intervention ([`causal_intervention.py`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/02aed1bf04988478c49f6e15257d00b25dbc0b35/reproduction/causal_intervention.py), machine-readable record in [`causal_intervention.json`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/02aed1bf04988478c49f6e15257d00b25dbc0b35/evidence/tsconfig-jsonc/causal_intervention.json)): on a temporary repository whose TypeScript source hashes never change, **A** original JSONC + stock loader fails; **B** removing only the comments restores `@app/util`; **C** restoring the exact original config reproduces the failure; **D** keeping that original config but patching only `_load_tsconfig_aliases` in memory with the string-aware reference loader restores resolution; **E** restoring the stock method reproduces the failure again. The full sequence passes on both duplicated resolver implementations. The intervention fixture also contains a relative import and missing/unconfigured/external specifiers: the relative import works in every state and the three negatives remain unresolved in every state, so the correction restores only the configured relationship.

The levels are kept distinct. The A–E sequence above is resolver-level evidence. In clean CI, the same sequence was also run through the installed Fast Lane `run_pipeline()` on the minimal repository: A/C/E have only the relative file edge and no alias `file_import`/selected target, while B/D restore the alias edge, bundle connection, and Optimal-selected target. Separately, patching only the Fast Lane loader in memory while leaving lexical's original `tsconfig.json` bytes unchanged restored **5,519** file edges, all **4,256** verified relationships, an exactly matching `ReactExtension.tsx` Optimal selection, and **2,707 Optimal / 3,345 Wider** direct-dependency recoveries versus stock. That is actual Fast Lane graph/context evidence, not a claim about later hosted stages. The loader used in D is the tested reference implementation in `solution/tsconfig_jsonc.py`; it proves causation and provides a maintainer-adaptable correction, but it is not a shipped fix.

Targeted boundaries: both engine copies were checked against the strict control, line/block/trailing/combined JSONC, string-safety, and no-alias fixtures (14 engine/fixture combinations). TypeScript 5.9.3 accepts the valid fixtures; comment-like sequences inside string literals remain byte-for-byte values after parsing; strict JSON still works; and the no-alias config remains empty with relative resolution intact. For six malformed shapes (missing value/brace, extra token, unterminated string/block comment, and non-object root), the reference parser reports a precise error and its product-style loader returns `{}` **plus one structured warning** on both engines, whereas the stock loader returns `{}` with no warning. A missing or comment-only config returns `{}` without a warning, so genuine absence and degraded parsing remain distinguishable.

Reference-solution differential validation: the candidate was also run against 14 curated valid cases and 500 deterministically generated valid JSONC documents whose expected values are known before serialization. It agrees with TypeScript 5.9.3's `parseConfigFileTextToJson` on all 514 valid documents. Microsoft `jsonc-parser` 3.3.1 agrees on 510; the four differences are empty/comment-only and U+2028/U+2029 cases, where the candidate follows TypeScript. Eight malformed or TypeScript-diagnosed JSON5-only cases are rejected by the candidate and diagnosed by both Node oracles. The corpus includes comment markers and commas inside strings, escaped quote/backslash boundaries, BOM, LF/CRLF/CR/LS/PS, comments before closing brackets after trailing commas, and deep-nesting failure. One explicit boundary is recorded rather than hidden: TypeScript's expression-based config parser also accepts JavaScript numeric spellings such as `.5` and `0x10`; like `jsonc-parser`, the reference implements the JSONC subset relevant here rather than cloning that full expression grammar.

Clean-environment verification: GitHub Actions on a pinned ordinary install passed TypeScript fixture acceptance, unified affected-version verification, the full minimal causal sequence, the minimal CLI comparison, the lexical stock/control rerun, and the in-memory-corrected lexical Fast Lane run. In that PR check, green means the defect and intervention were reproduced exactly and the raw `--expect-fixed` regression failed only for the documented empty-alias symptom; it does not mean expected JSONC behaviour already works in the shipped package. The raw regression remains available as an explicitly manual post-fix workflow. See [`CI_VERIFICATION.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/02aed1bf04988478c49f6e15257d00b25dbc0b35/evidence/tsconfig-jsonc/CI_VERIFICATION.md); graph/bundle hashes and pinned inputs are in [`ARTIFACT_MANIFEST.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/02aed1bf04988478c49f6e15257d00b25dbc0b35/evidence/tsconfig-jsonc/ARTIFACT_MANIFEST.md).

## 7. Impact and scope
This is a silent wrong-answer defect when a JS/TS repository's supported root `tsconfig.json` uses comments or trailing commas together with non-hardcoded path aliases. In lexical, 4,256 relationships are about 77% of the control's attainable internal file edges; source files with at least one outgoing file edge fall from 1,426 to 479. More importantly, thousands of real implementations become ineligible in exported Optimal/Wider context. Even after excluding tests/examples/playground, 446 package-source→package-source direct pairs are absent as-is and restored in at least one non-trivial scope.

The failure is masked in three ways: there is no parse warning, hardcoded `@/`/`~/`/relative resolution still works, and unique-symbol fallback can create some symbol links without the missing file relationship. The result is an apparently usable but materially incomplete Connected Code Map/context export.

Published-release scope: I verified downloaded bytes against PyPI SHA-256 metadata for every published wheel from 0.3.0 through 0.3.15. The scan covers 16 releases, 106 wheels, and 212 engine copies; all contain exactly one `_load_tsconfig_aliases` AST, and executing that extracted function reproduces strict-JSON success versus JSONC `{}`. This is a statement about published PyPI wheels in that snapshot, not source branches or non-PyPI builds.

Public exposure check: using one exact GitHub code-search query for root `tsconfig.json` files mentioning `compilerOptions` and `paths`, the first three result pages produced 210 unique public root configs. Of 184 repository configs with a non-empty resolvable `paths` table, TypeScript verified 44 strict-JSON-rejected configs containing 211 path entries. After deduplicating identical contents, the conservative count is **35 affected unique config contents among 139 eligible**, containing 174 path entries. GitHub code search is best-match/index ordered, so I am explicitly **not** converting this sample into an ecosystem- or user-prevalence percentage; it shows that real public root configs combine the trigger and aliases beyond the two fully measured repositories.

Confirmed scope: deterministic on the fixtures, lexical, and ng-matero; both engine copies and all scanned 0.3.0–0.3.15 wheels share the defective loader. This report does not claim nested-tsconfig discovery, `extends`, Vite aliases, every `paths` pattern shape, or hosted business findings. Separate already-loaded alias-pattern limitations remain out of scope.

## 8. Suspected cause / suggested fix (if known)
Cause: `_load_tsconfig_aliases` treats a JSONC file as strict JSON and converts every parse error into an empty alias table with no diagnostic.

Suggested fix direction:

1. Parse the supported root `tsconfig.json` as JSONC through one shared loader (or the same correction in both engine copies). The evidence repo contains a dependency-free reference implementation: position-preserving, string-aware blanking of comments and trailing commas, followed by strict `json.loads`, then the existing alias-mapping rules unchanged. A maintained parser could replace that transform if it passes the same string-safety, BOM/line-terminator, empty-config, and diagnostic tests; a regex stripper should not be used.
2. Return both aliases and degradation state. Missing or empty/comment-only config → `{}`, no warning. Existing unreadable/malformed/invalid-shape config → `{}`, plus one structured warning containing code/path/message and line/column/offset when known.
3. Append that warning once to each graph builder's existing top-level `warnings` list after constructing `LanguageAwareImportResolver`, so users can distinguish “aliases could not be loaded” from “this project declares no aliases.”

Validation: `python reproduction/verify.py --expect-fixed` (which runs the retained raw `repro_unit.py --expect-fixed`) should pass all JSONC fixtures including string-safety cases on both resolver copies; the reference corpus should retain 514/514 TypeScript valid-document agreements; malformed existing configs should produce exactly one visible warning rather than a silent empty table; missing/empty configs should produce no warning; the minimal JSONC CLI fixture should produce the file edge; lexical should reach 5,519 internal file edges with its config untouched; and the direct-dependency selection omissions should disappear relative to the comment-stripped control. The reversible intervention's B/D states are the expected restored behaviour, while its A/C/E states document the current stock failure.

## 9. Duplicate check
Re-searched on 2026-11-03 through the GitHub issue-search API (open + closed; 346 issues through #442):

- `jsonc` → 0; `"trailing comma"` → 0; `"compilerOptions.paths"` → #153, #272, and #374.
- `tsconfig` / `alias tsconfig` → #153, #272, #374, and new #442; `_load_tsconfig_aliases` → #442 only, read in full.

Closest issues differ by mechanism:

- **#153/#272:** `@/` imports are recorded `hard_path_skipped` by the later linker. Here the Stage-1 resolver's alias table is empty before resolution, records are `external_or_unresolved`, and resolution returns immediately when config comments are removed.
- **#374:** the alias is only in `vite.config.ts`/a non-root setup. Here it is in the supported repository-root `tsconfig.json`.
- **#442:** a loaded target pattern such as `packages/*/src` loses its `*` instead of substituting the captured segment. That is a later post-load wildcard-substitution mechanism. Here the whole config fails to load because of JSONC lexical syntax; removing only comments restores the table without changing wildcard semantics. Fixing either defect would not fix the other.
- **#320:** `_js_import_symbols` extracts local binding names incorrectly. Here extraction is identical between as-is and control.
- **#428:** an exported local binding (`Select = SelectPrimitive.Root`) is `symbol_not_found` although the module and sibling exports resolve. Here the configured module file relationship itself is absent because the alias table was never loaded.
- **#262/#84:** a separate `../` path-normalization defect, excluded from this report.

No existing issue reports legal JSONC syntax in `tsconfig.json` silently emptying UnvibeCode's root path-alias table.
