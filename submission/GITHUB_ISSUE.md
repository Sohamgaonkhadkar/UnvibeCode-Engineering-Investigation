> **STATUS — DO NOT FILE UNCHANGED (checked 2026-11-04):** upstream
> [#451](https://github.com/FinanceFlash/unvibecode/issues/451) now reports
> the same strict-JSON/JSONC empty-alias mechanism. This nine-section text is
> retained as independently derived corroborating evidence (the personal
> evidence repository predates #451) and as source material for a
> maintainer/organizer-directed comment or explicitly linked supplementary
> submission. Do not paste it as a new upstream issue without first revising
> the title/body to cite #451 and state the independent chronology.

Title: [Bug] Connected Code Map — comments/trailing commas in a valid JSONC tsconfig silently discard all root path aliases

## 1. Problem summary
UnvibeCode loads TypeScript path aliases from the repository-root `tsconfig.json` with strict `json.loads`, inside a swallowing `except Exception: pass`. A `tsconfig.json` is JSONC, however: TypeScript accepts `//` and `/* */` comments and trailing commas. If the file uses any of those legal features, UnvibeCode silently discards the **entire `compilerOptions.paths` table**, records imports through non-hardcoded aliases as `external_or_unresolved`, and emits no config warning.

This is not only a missing-edge count. On `meta/lexical`, five comment lines suppress 4,256 verified internal file relationships, and comparing the actual exported context bundles shows that **2,707 direct dependencies are absent from Optimal selections** (3,345 in Wider) until only those comments are removed. In a deterministic audit of the actual Optimal ZIPs, none of six predeclared `ReactExtension.tsx` maintenance questions has all required answer-bearing implementation lines as-is, while all six do in both the control and reference-corrected bundles. Scaling that check across all verified relationships gives 10,703 eligible source-specific imported-symbol tasks: only 726 have the required definition/export evidence in as-is Optimal selections, versus 8,826 in both control and corrected bundles. Independent ng-matero reproduces the graph, selection, corrected-output, and 0/3→3/3 answerability pattern under an ordinary install. A developer therefore cannot tell that apparently disconnected or thin context is really “the config never loaded.” The same loader AST is present in every published PyPI wheel from 0.3.0 through 0.3.15, and direct execution on a bounded public-config sample confirms that both installed loaders empty every affected sampled table outside the two pinned benchmark repositories.

### Evidence at a glance

| Layer checked | Result |
|---|---|
| Independent compiler expectation | TypeScript 5.9.3 accepts the JSONC configs; its resolver matches **4,256/4,256** lexical relationship rows with **0 mismatches** |
| Isolated mechanism | Strict JSON loads `{'@app': 'src/app'}`; each legal JSONC variant returns `{}` and no resolution, while lexical import extraction is unchanged at **9,562 = 9,562** records |
| Public-repository graphs | Lexical rises **1,263 → 5,519** internal file edges after removing only five comments; independent ng-matero rises **130 → 241** after removing only two block comments |
| Exported context | **2,707** verified direct dependencies are restored in lexical Optimal selections and **3,345** in Wider; lexical tasks score **0/6 as-is** and **6/6** control/corrected, ng-matero scores **0/3→3/3**, and 10,703 exhaustive source-specific symbol tasks recover **8,163** Optimal definition/export instances (9,182 Wider) |
| Reversible correction | On both resolver copies: original **fails → comments removed restores → original restored fails → in-memory reference loader restores → stock restored fails**. On untouched lexical, that loader also restores the actual Fast Lane graph/context |
| Published-release scope | All **106** PyPI wheels for 0.3.0–0.3.15 were digest-verified; all **212** engine copies contain the same vulnerable loader AST |
| Public-config exposure | In a bounded first-returned GitHub code-search sample, **35 unique affected root-config contents** (174 path entries) were TypeScript-verified among 139 eligible unique contents. Executing both installed loaders on all 184 eligible repository configs gives **44/44 affected empty stock/corrected-exact** and **140/140 strict controls exact**; still not a prevalence estimate |
| Reference solution | A dependency-free JSONC loader agrees with TypeScript 5.9.3 on **514/514** curated/generated valid documents and has zero critical divergences on a separate **2,277-case** adversarial boundary/mutation probe; its builder-level warning path exports exactly one `tsconfig_parse_failed` record for a malformed config and none for valid JSONC. A reversible file-level patched-install rehearsal then passes both unmonkeypatched engine copies (including invalid-UTF-8 read failure), the full graph, and the raw post-fix regression before restoring stock hashes |
| Clean automation | Ordinary-install GitHub Actions passes the fixture/CLI, differential oracle, adversarial boundary/mutation probe, full causal sequence, lexical and ng-matero stock/control/corrected runs, both answerability audits, the exhaustive symbol audit, and the patched-install rehearsal; the exact symptom also reproduces on CPython 3.11–3.14 (Ubuntu) and 3.12 (Windows/macOS) |

## 2. Test environment
- UnvibeCode: **0.3.15** from PyPI (`unvibecode==0.3.15`)
- Clean verification: GitHub Actions ordinary pip installation; principal jobs on `ubuntu-latest`/Python 3.12, plus CPython 3.11–3.14 on Ubuntu and CPython 3.12 on Windows/macOS
- Local replication: Linux x86_64, Python 3.11.2
- Independent compiler oracle: TypeScript **5.9.3**; Microsoft `jsonc-parser` **3.3.1** is used only as a second differential oracle for the reference solution
- Public repositories:
  - https://github.com/meta/lexical @ `164af6a4df7114f35724c472152ca74877b6bd04`
  - https://github.com/ng-matero/ng-matero @ `d351bf5957d8c6dc9eca79d0c9b260c5b8d07822`
- Command: `python -m unvibecode review --repository "<path>"`
- Evidence/fixtures: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb (commit-pinned snapshot containing the scripts and machine-readable evidence; the clean-CI run record is indexed in `evidence/tsconfig-jsonc/CI_VERIFICATION.md`. Evidence-repo PR #1 contains the original verified investigation, and follow-up PR #2 at https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/2 contains the reversible intervention, reference solution, release/exposure scope, and its current check rollup.)

Environment note: my local investigation sandbox blocks tree-sitter grammar downloads, so the locally captured large-repo artifacts used a disclosed fallback grammar environment. That workaround is no longer the sole basis for the claim: the minimal CLI comparison, full lexical original/control/corrected comparison, full ng-matero original/control/corrected comparison, and disposable patched-install rehearsal were rerun under ordinary installs in GitHub Actions with the same counts. The resolver defect itself also reproduces in pure Python with no grammar or hosted service. Full provenance is in `evidence/tsconfig-jsonc/CI_VERIFICATION.md` and `STANDARD_INSTALL_ATTEMPT.md` in the evidence repo.

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
   This checks the Python/package environment, runs the strict control and all JSONC variants, and then runs the original post-fix regression `python reproduction/repro_unit.py --expect-fixed`. On 0.3.15 it reports the defect only if that regression fails in exactly the four JSONC cases with `aliases={}` and `resolution=(None, None)`; the strict control gives `{'@app': 'src/app'}` and `@app/util -> src/app/util.ts`. The same verifier also runs the reference-solution Python corpus and integration check, the reversible A/B/C/D/E intervention and targeted boundaries on both shipped resolver copies, and checks the committed lexical/ng-matero, reference-validation, release-scope, exposure-sample, direct public-config loader-behavior, and both answerability-task specifications.
3. For the full graph/context form of that intervention, including the exported-graph warning boundary, run:
   ```bash
   python reproduction/causal_intervention.py --full-pipeline --output causal-intervention.json
   ```
4. Run the CLI on `reproduction/minimal_strict` and `reproduction/minimal_jsonc` (or `python reproduction/ci_cli_comparison.py --output-root ./cli-comparison-output`) and compare `[STAGE 1 COMPLETE]`, `connections.jsonl`, and `unresolved_relationships.jsonl`.
5. Real-repository check: run lexical at the pinned commit, then delete only lines 9–13 (five `//` comments) from its root `tsconfig.json` and run again. The clean-environment workflows apply `reproduction/answerability_audit.py` to actual as-is/control/corrected ZIPs for both lexical and ng-matero, and `reproduction/symbol_evidence_audit.py` exhaustively across lexical's verified relationships.
6. Optional disposable-venv rehearsal of the exact reference integration (never against a shared install):
   ```bash
   python solution/apply_reference_patch.py --backup-dir ./stock-backup \
     --i-understand-this-modifies-site-packages
   python solution/validate_patched_install.py --full-pipeline
   python reproduction/verify.py --expect-fixed --skip-evidence
   python solution/apply_reference_patch.py --restore ./stock-backup \
     --i-understand-this-modifies-site-packages
   ```

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

A sixth configured direct dependency, `LexicalErrorBoundary.tsx`, is present in both selections. The important observation is therefore not simply that the control is larger—more tokens are not automatically better context—but that chunks from five TypeScript-verified direct dependencies become available. This establishes an observable difference in the exported context; it does not by itself prove that any particular LLM answer will improve. The chunk-level record is [`selection_case_react_extension.json`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/selection_case_react_extension.json).

Final-artifact answerability makes that difference task-specific. Six predeclared questions ask, for example, what accessibility prop a `ContentEditable` placeholder requires and how it is rendered; what the two composer-context tuple elements are and how `getTheme` falls back; what name `ReactProviderExtension` declares; what `invariant` does on a false condition; whether `defineExtension` transforms its argument; and when `shallowMergeConfig` returns the original object versus a copy. The audit requires every named answer-bearing fragment to occur in selected Optimal chunks from the answering implementation file, so call sites inside `ReactExtension.tsx` cannot pass a task. In the actual exported ZIPs the result is **0/6 as-is, 6/6 in the comment-stripped control, and 6/6 with the original config plus the reference loader**; the `LexicalErrorBoundary` negative control is 1/1 in every bundle. This measures whether answer-bearing evidence is present, not whether a particular model will answer correctly. Method and machine-readable task definitions are [`ANSWERABILITY_AUDIT.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/ANSWERABILITY_AUDIT.md) and [`answerability_tasks.json`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/reproduction/answerability_tasks.json).

An exhaustive companion scales beyond that one source. Joining all 4,256 verified lexical relationships to the control graph's resolved imported-symbol edges yields 10,715 candidate tasks; 10,703 have a recognizable declaration/export line in the symbol-defining file's full control bundle. At Optimal, that evidence is selected for only 726 tasks as-is versus 8,826 in both control and corrected bundles (**8,163 recovered**); at Wider, 711 versus 9,883 (**9,182 recovered**). These are source-specific import instances across 1,239 importing files—not unique symbols—and the audit counts evidence availability, not model answers. See [`SYMBOL_EVIDENCE_AUDIT.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/SYMBOL_EVIDENCE_AUDIT.md).

The same mechanism reproduces on ng-matero: removing only two leading block comments changes 130 → 241 internal file edges, restoring 111 verified relationships and 107 direct dependencies in both Optimal and Wider selections. Its corrected-original Fast Lane run also reaches 241 edges/warning-free, and three predeclared `src/app/app.config.ts` answerability tasks score 0/3 as-is versus 3/3 in both control and corrected bundles under an ordinary install.

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

The earlier prefix-based count was re-audited rather than assumed. `analyze_alias_oracle.py` parses lexical's actual 220 `paths` patterns (184 exact, 36 wildcard), applies TypeScript-style exact/longest-prefix matching and file probing, and checks every control-only edge. **All 4,256 match the oracle-identified target; there are 0 as-is-only edges.** Independently, TypeScript 5.9.3's `resolveModuleName` was run over all 4,218 unique source/specifier pairs and again matched all 4,256 rows with zero mismatches. The import records are preserved with source file, line, specifier, target, pattern, and strategy in [`lost_relationships.jsonl`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/lost_relationships.jsonl). A distinct-pair concentration audit further shows that only 38 instances are duplicate source→target pairs beyond the first, while retaining the important caveat that the 4,218 pairs concentrate in 101 direct targets: [`RELATIONSHIP_CONCENTRATION_AUDIT.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/RELATIONSHIP_CONCENTRATION_AUDIT.md).

The downstream count is likewise measured in the emitted bundles, not inferred from edges alone. Of the 4,218 lexical direct pairs at Optimal: 2,707 are absent as-is/restored in control, 434 are present in both via other links, 1,062 are absent in both, and 15 are present only as-is. At Wider: 3,345 restored, 472 in both, 398 in neither, 3 only as-is. Selection files change for 1,494 of 2,044 files in at least one scope. Narrow (radius 0) is not claimed as impact.

Reversible causal intervention ([`causal_intervention.py`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/reproduction/causal_intervention.py), machine-readable record in [`causal_intervention.json`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/causal_intervention.json)): on a temporary repository whose TypeScript source hashes never change, **A** original JSONC + stock loader fails; **B** removing only the comments restores `@app/util`; **C** restoring the exact original config reproduces the failure; **D** keeping that original config but patching only `_load_tsconfig_aliases` in memory with the string-aware reference loader restores resolution; **E** restoring the stock method reproduces the failure again. The full sequence passes on both duplicated resolver implementations. The intervention fixture also contains a relative import and missing/unconfigured/external specifiers: the relative import works in every state and the three negatives remain unresolved in every state, so the correction restores only the configured relationship.

The levels are kept distinct. The A–E sequence above is resolver-level evidence. In clean CI, the same sequence was also run through the installed Fast Lane `run_pipeline()` on the minimal repository: A/C/E have only the relative file edge and no alias `file_import`/selected target, while B/D restore the alias edge, bundle connection, and Optimal-selected target. The valid-JSONC graphs all expose `warnings: []`. For a separate malformed existing config (`{"compilerOptions": }`), the stock full pipeline still exports no config warning; with the reference loader and its builder-level warning wiring applied in memory, the actual exported graph contains exactly one `tsconfig_parse_failed` record with path/line/column/offset while the relative edge still resolves. Separately, patching only the Fast Lane loader in memory while leaving lexical's original `tsconfig.json` bytes unchanged restored **5,519** file edges, all **4,256** verified relationships, an exactly matching `ReactExtension.tsx` Optimal selection, and **2,707 Optimal / 3,345 Wider** direct-dependency recoveries versus stock. That is actual Fast Lane graph/context evidence, not a claim about later hosted stages. A stronger, separate disposable-environment rehearsal then applies the exact reference module and builder warning insertion at file level to both installed engine copies: with no monkeypatching, both patched resolvers and the full Fast Lane graph pass valid/malformed/invalid-UTF-8 checks, the raw `verify.py --expect-fixed --skip-evidence` regression passes, and restoration returns the recorded stock hashes. The loader used in D is the tested reference implementation in `solution/tsconfig_jsonc.py`; it proves causation and provides a maintainer-adaptable correction, but neither rehearsal is a shipped fix.

Targeted boundaries: both engine copies were checked against the strict control, line/block/trailing/combined JSONC, string-safety, and no-alias fixtures (14 engine/fixture combinations). TypeScript 5.9.3 accepts the valid fixtures; comment-like sequences inside string literals remain byte-for-byte values after parsing; strict JSON still works; and the no-alias config remains empty with relative resolution intact. For six malformed shapes (missing value/brace, extra token, unterminated string/block comment, and non-object root), the reference parser reports a precise error and its product-style loader returns `{}` **plus one structured warning** on both engines, whereas the stock loader returns `{}` with no warning. A missing or comment-only config returns `{}` without a warning, so genuine absence and degraded parsing remain distinguishable.

Reference-solution differential validation: the candidate was also run against 14 curated valid cases and 500 deterministically generated valid JSONC documents whose expected values are known before serialization. It agrees with TypeScript 5.9.3's `parseConfigFileTextToJson` on all 514 valid documents. Microsoft `jsonc-parser` 3.3.1 agrees on 510; the four differences are empty/comment-only and U+2028/U+2029 cases, where the candidate follows TypeScript. Thirteen malformed or TypeScript-diagnosed cases—including leading/elision commas and Python's non-JSON `NaN`/`Infinity` constants—are rejected by the candidate and diagnosed by both Node oracles. A separate adversarial probe adds 121 enumerated grammar boundaries and 2,156 unique seeded mutations: 865 cases are accepted by all three parsers with equal values, 1,316 are rejected by all three, and there are zero candidate-only acceptances, zero candidate-only rejections, and zero all-accept value mismatches. The corpus includes comment markers and commas inside strings, escaped quote/backslash boundaries, BOM, LF/CRLF/CR/LS/PS, comments before closing brackets after trailing commas, and deep-nesting failure. Explicit boundaries are recorded rather than hidden: TypeScript's expression-based config parser also accepts JavaScript numeric/string spellings and broader Unicode trivia; like `jsonc-parser` with errors inspected, the reference implements the JSONC subset relevant here rather than cloning that full expression grammar. The design/integration record is [`solution/README.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/solution/README.md); the machine-readable differential results are [`reference_solution_validation.json`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/reference_solution_validation.json) and [`differential_probe.json`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/differential_probe.json).

Clean-environment verification: GitHub Actions on a pinned ordinary install passed TypeScript fixture acceptance, unified affected-version verification, the TypeScript/`jsonc-parser` differential and adversarial-probe reproduction, the full minimal causal sequence and graph-warning boundary, the minimal CLI comparison, lexical and ng-matero stock/control/corrected reruns, both final-artifact answerability audits, the exhaustive lexical symbol-evidence audit, and the disposable file-level patched-install rehearsal/restore. Six ordinary-install scope jobs also reproduced the lightweight exact symptom on CPython 3.11–3.14 (Ubuntu) and CPython 3.12 on Windows/macOS. In that PR check, green means the defect and intervention were reproduced exactly and the raw `--expect-fixed` regression failed only for the documented empty-alias symptom; it does not mean expected JSONC behaviour already works in the shipped package. The raw regression remains available as an explicitly manual post-fix workflow. The successful runs for the pinned evidence snapshot are the main verification run https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913945, lexical run https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913810, and ng-matero run https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913798. See [`CI_VERIFICATION.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/CI_VERIFICATION.md); graph/bundle hashes and pinned inputs are in [`ARTIFACT_MANIFEST.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/ARTIFACT_MANIFEST.md).

## 7. Impact and scope
This is a silent wrong-answer defect when a JS/TS repository's supported root `tsconfig.json` uses comments or trailing commas together with non-hardcoded path aliases. In lexical, 4,256 relationships are about 77% of the control's attainable internal file edges; source files with at least one outgoing file edge fall from 1,426 to 479. More importantly, thousands of real implementations become ineligible in exported Optimal/Wider context; all nine predeclared cross-repository maintenance tasks lose their required answer-bearing evidence as-is, and 8,163 of 10,703 eligible lexical symbol-definition instances are recovered at Optimal by correcting only the parse. Even after excluding tests/examples/playground, 446 package-source→package-source direct pairs are absent as-is and restored in at least one non-trivial scope.

The failure is masked in three ways: there is no parse warning, hardcoded `@/`/`~/`/relative resolution still works, and unique-symbol fallback can create some symbol links without the missing file relationship. The result is an apparently usable but materially incomplete Connected Code Map/context export.

Published-release scope: I verified downloaded bytes against PyPI SHA-256 metadata for every published wheel from 0.3.0 through 0.3.15. The scan covers 16 releases, 106 wheels, and 212 engine copies; all contain exactly one `_load_tsconfig_aliases` AST, and executing that extracted function reproduces strict-JSON success versus JSONC `{}`. This is a statement about published PyPI wheels in that snapshot, not source branches or non-PyPI builds. Ordinary-install CI complements that static scan behaviorally for 0.3.15 across CPython 3.11–3.14 on Ubuntu and CPython 3.12 on Windows/macOS. Method, denominators, and limits for both scope checks are in [`SCOPE_AND_EXPOSURE.md`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb/evidence/tsconfig-jsonc/SCOPE_AND_EXPOSURE.md).

Public exposure check: using one exact GitHub code-search query for root `tsconfig.json` files mentioning `compilerOptions` and `paths`, the first three result pages produced 210 unique public root configs. Of 184 repository configs with a non-empty resolvable `paths` table, TypeScript verified 44 strict-JSON-rejected configs containing 211 path entries. After deduplicating identical contents, the conservative count is **35 affected unique config contents among 139 eligible**, containing 174 path entries. I also re-fetched every eligible blob by its recorded Git SHA, verified its bytes/hash, and executed both installed 0.3.15 loaders: all 44 affected repository configs return `{}` on both stock engines and the exact expected 163 mapped alias-table entries with the reference loader, while all 140 unaffected controls are exact under stock and reference. GitHub code search is best-match/index ordered, so I am explicitly **not** converting this sample into an ecosystem- or user-prevalence percentage; it shows that real public root configs combine the trigger and aliases beyond the two fully measured repositories.

Confirmed scope: deterministic on the fixtures, lexical, and ng-matero; both engine copies and all scanned 0.3.0–0.3.15 wheels share the defective loader. This report does not claim nested-tsconfig discovery, `extends`, Vite aliases, every `paths` pattern shape, or hosted business findings. Separate already-loaded alias-pattern limitations remain out of scope.

## 8. Suspected cause / suggested fix (if known)
Cause: `_load_tsconfig_aliases` treats a JSONC file as strict JSON and converts every parse error into an empty alias table with no diagnostic.

Suggested fix direction:

1. Parse the supported root `tsconfig.json` as JSONC through one shared loader (or the same correction in both engine copies), reading that config as strict UTF-8 rather than with a lossy `errors="ignore"` helper. The evidence repo contains a dependency-free reference implementation: position-preserving, string-aware blanking of comments and *true* trailing commas, followed by strict `json.loads` with Python's non-JSON constants rejected, then the existing alias-mapping rules unchanged. A maintained parser could replace that transform if it passes the same string-safety, BOM/line-terminator, empty-config, leading-comma, and diagnostic tests; a regex stripper should not be used.
2. Return both aliases and degradation state. Missing or empty/comment-only config → `{}`, no warning. Existing unreadable/malformed/invalid-shape config → `{}`, plus one structured warning containing code/path/message and line/column/offset when known.
3. Append that warning once to each graph builder's existing top-level `warnings` list after constructing `LanguageAwareImportResolver`, so users can distinguish “aliases could not be loaded” from “this project declares no aliases.”

Validation: `python reproduction/verify.py --expect-fixed` (which runs the retained raw `repro_unit.py --expect-fixed`) should pass all JSONC fixtures including string-safety cases on both resolver copies; the reference corpus should retain 514/514 TypeScript valid-document agreements; malformed existing configs should produce exactly one visible warning in the exported graph rather than a silent empty table; valid and missing/empty configs should produce no warning; the minimal JSONC CLI fixture should produce the file edge; lexical should reach 5,519 internal file edges with its config untouched and ng-matero 241; the direct-dependency selection omissions should disappear relative to the comment-stripped controls; the answerability audits should reach 6/6 and 3/3 without changing their negative controls; and the lexical symbol-evidence audit should recover the same 8,163 Optimal / 9,182 Wider instances as its control. The reversible intervention's B/D states are the expected restored behaviour, while its A/C/E states document the current stock failure.

## 9. Duplicate check
Re-searched on 2026-11-05 through the GitHub issue-search API (open + closed; 434 issues through #532):

- `jsonc` → #451, #455; `"trailing comma"` → #451, #455.
- `_load_tsconfig_aliases` → #442, #451, #452, #455.
- `tsconfig` → #153, #272, #374, #442, #451, #452, #455, #501.
- `"compilerOptions.paths"` → #153, #272, #374, #455.

All 58 issues added since the previous sweep (#474–#532) were also body-scanned for `jsonc`, `trailing comma`, `json.loads`, `tsconfig`, `compilerOptions`, `path alias`, `strict json`, and `comments`; every keyword match was read in context and none reports a config-parse failure that empties an alias table.

Mechanism classification:

- **#451 — same mechanism / filing duplicate.** It reports that both engines parse a valid JSONC root `tsconfig.json` with strict `json.loads`, swallow the error, and load zero path mappings. This evidence was independently derived and was already public in the personal evidence repository (PR #1 created 2026-11-01 and merged 2026-11-02; PR #2 created 2026-11-02) before #451 was filed on 2026-11-03, but #451 is now the first upstream report. This text should therefore be used only as corroborating evidence or after explicit revision to cite #451.
- **#452 — distinct.** Its strict-JSON config parses; ordinary imports are not resolved through `baseUrl` when there is no explicit `paths` table. This report is limited to JSONC syntax preventing a declared root `paths` table from loading.
- **#455 — distinct.** Its strict-JSON configs parse; aliases inherited through `extends` or declared in non-root effective configs are not discovered. This report does not claim `extends`, nested-config discovery, or effective-config merging.
- **#153/#272:** `@/` imports are recorded `hard_path_skipped` by the later linker. Here the Stage-1 resolver's alias table is empty before resolution, records are `external_or_unresolved`, and resolution returns immediately when config comments are removed.
- **#374:** the alias is only in `vite.config.ts`/a non-root setup. Here it is in the supported repository-root `tsconfig.json`.
- **#442:** a loaded target pattern such as `packages/*/src` loses its `*` instead of substituting the captured segment. That is a later post-load wildcard-substitution mechanism. Here the whole config fails to load because of JSONC lexical syntax; removing only comments restores the table without changing wildcard semantics. Fixing either defect would not fix the other.
- **#444:** a Python `route_handler` entity kind is overwritten during linker entity merging. It does not involve TypeScript config parsing or alias loading.
- **#320:** `_js_import_symbols` extracts local binding names incorrectly. Here extraction is identical between as-is and control.
- **#428:** an exported local binding (`Select = SelectPrimitive.Root`) is `symbol_not_found` although the module and sibling exports resolve. Here the configured module file relationship itself is absent because the alias table was never loaded.
- **#262/#84/#501:** a separate `../` path-normalization defect, excluded from this report. #501 (filed 2026-11-05) is the newest such report; its only `tsconfig` mention cross-references #455's `extends` defect, and it parses no config.
- **#532:** conditional `require`/`import` calls lose alternative module paths during JS/TS import extraction. Its `json.loads` occurrences are inside its own verification harness reading generated JSON, not config parsing.

Historical note: the 2026-11-03 sweep through #444 found no JSONC-empty-alias report; that result was superseded later the same day by #451. The 2026-11-04 sweep through #473 and the 2026-11-05 sweep through #532 both confirm #451 as the single upstream report of this mechanism. Earlier totals must not be quoted as the current tracker state, and the sweep should be repeated immediately before any public filing.
