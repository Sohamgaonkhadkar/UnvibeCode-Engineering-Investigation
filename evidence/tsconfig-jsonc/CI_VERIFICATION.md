# Clean-environment verification — GitHub Actions

The earlier sandbox could not obtain `tree-sitter-language-pack` grammars through
its restricted egress, so local large-repository CLI runs used a disclosed
fallback grammar shim. The runs below close that reproducibility gap in a normal
GitHub-hosted environment. The principal jobs install only the pinned public
package (`unvibecode==0.3.15`) with Python 3.12 on `ubuntu-latest`; no shim
is present. A separate matrix repeats the lightweight exact-symptom and
reference-loader verification across CPython/platform combinations.

The latest fully indexed functional verification below ran from investigation
commit `ae3f9c2a79f58c384db45ed3bdb5ca18dea670bf`, which contains the
reference solution, graph-warning integration check, patched-install
rehearsal, lexical and ng-matero final-artifact audits, exhaustive
symbol-evidence audit, and direct public-config loader-behavior evidence.
All 10 PR checks passed at that commit. Follow-up PR #2's check rollup
remains the authoritative status for any later branch head. (The original
investigation was merged through PR #1.)

## How to read the PR checks

- **Affected-version verification** is green only when the strict control
  resolves, the raw `repro_unit.py --expect-fixed` regression fails only for
  the four exact JSONC fixtures with `aliases={}` and
  `resolution=(None, None)`, the reference-solution corpus and loader pass,
  the TypeScript/`jsonc-parser` differential result reproduces, the
  reversible A/B/C/D/E intervention and targeted boundaries pass on both
  resolver copies, the full-pipeline malformed graph-warning boundary passes,
  and the committed evidence counts reconcile. Six additional matrix jobs
  reproduce the lightweight exact symptom on ordinary installs.
- Therefore, a green affected-version check means **the 0.3.15 defect was
  reproduced and verified exactly**. It does **not** mean correct JSONC
  behaviour already passes in the shipped package.
- The distinguishably named **Patched-install rehearsal** check is the one
  exception in scope: on its own disposable runner it file-patches both
  installed engine copies, expects correct behavior with no monkeypatching,
  passes the raw post-fix regression, and then restores/verifies the stock
  hashes. It proves the reference integration shape, not a shipped fix.
- **Manual post-fix regression** keeps the original
  `reproduction/repro_unit.py --expect-fixed` test. It is deliberately manual
  (`workflow_dispatch`) rather than a permanently red PR gate. There is no
  `continue-on-error` masking its result.

## 1. Unified affected-version verification + minimal standard CLI

- Workflow: **PR verification — JSONC defect reproduced exactly (0.3.15)**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41638056309
- Job: **Affected-version verification — exact defect, reference loader, evidence**
- Result: **success**
- Successful steps include:
  - TypeScript 5.9.3 `tsc --showConfig` on strict, line-comment, block-comment,
    trailing-comma, string-safety, and combined JSONC fixtures;
  - `python reproduction/verify.py`, which runs the known-bug reproducer,
    asserts the exact `--expect-fixed` failure shape, runs the
    reference-solution Python corpus (14 curated + 500 generated valid
    documents) and integration check, runs the resolver-level reversible
    intervention and targeted boundaries on both engine copies, and verifies
    committed lexical/ng-matero, reference-validation, version-scope,
    exposure-sample, public-config loader-behavior, and answerability-task
    evidence;
  - a validation-only TypeScript 5.9.3 + Microsoft `jsonc-parser` 3.3.1
    differential run, reproducing 514/514 TypeScript and 510/514
    `jsonc-parser` valid-document agreements and 8 diagnosed invalid cases;
  - `causal_intervention.py --full-pipeline`, which repeats A/B/C/D/E through
    the installed Fast Lane `run_pipeline()`, inspects the actual resolved
    graph and complete-repository-context ZIP, and proves that a malformed
    config yields no stock graph warning but exactly one exported
    `tsconfig_parse_failed` warning with the builder-level reference
    integration;
  - `ci_cli_comparison.py` using `python -m unvibecode review`.
- Published differential annotation:
  > `candidate/TypeScript valid agreements=514/514; candidate/jsonc-parser
  > valid agreements=510/514; diagnosed invalid cases=8`
- Published CLI annotation:
  > `status=PASS_KNOWN_BUG_REPRODUCED; strict: cli_exit=1, timed_out=False,
  > files=2, file_edges=1, unresolved=0, file_import=1, symbol_fallback=1,
  > grammar_download_error=False; jsonc: cli_exit=1, timed_out=False, files=2,
  > file_edges=0, unresolved=1, file_import=0, symbol_fallback=1,
  > grammar_download_error=False`
- Artifact `jsonc-verification-logs`:
  - ID `13230967523`
  - 13,639 bytes
  - SHA-256 `1c7026cb8d736da796b936f8c216ad55a39a8a5c7d001858dbbb373ac0928878`

The minimal CLI processes exit 1 after producing the local graph and context
bundle. Those are the artifacts under test; the comparison does not claim that a
later hosted stage completed. Both variants have the same process outcome, so it
cannot explain the strict-vs-JSONC file-edge difference.

The same workflow run also completed six **Platform/Python scope** jobs:
CPython 3.11, 3.12, 3.13, and 3.14 on `ubuntu-latest`, plus CPython 3.12 on
`windows-latest` and `macos-latest`. Each normally installed 0.3.15 and ran
`verify.py --skip-evidence`, which still covers the known-bug reproduction,
exact `--expect-fixed` failure, reference corpus/loader, and both-engine
causal intervention.

The eighth job in the same run, **Patched-install rehearsal — file-level
reference integration**, also succeeded. It recorded the stock state, applied
`solution/apply_reference_patch.py` to the runner's disposable
site-packages, verified that the installed sibling reference module is
byte-identical to `solution/tsconfig_jsonc.py`, ran
`solution/validate_patched_install.py --full-pipeline` with no monkeypatching,
passed `reproduction/verify.py --expect-fixed --skip-evidence`, restored the
stock files, and verified their hashes/reference-module removal.

- Published patched-install annotation:
  > `status=passed; patched resolvers=fast_lane_00a,merged_graph_01; valid
  > JSONC source edges=[['src/feature/comp.ts', 'src/app/util.ts'],
  > ['src/feature/comp.ts', 'src/feature/local.ts']]; malformed graph
  > warning codes=['tsconfig_parse_failed']`
- Artifact `patched-install-rehearsal-evidence`:
  - ID `13230484494`
  - 6,164 bytes
  - SHA-256 `d1073d55b652d8066cbf20d2fc59431517505af8d2f90a11c5ff27260db4b811`

## 2. Lexical under the same ordinary installation

- Workflow: **Lexical clean-environment validation**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41638056381
- Result: **success**
- It fetched lexical at `164af6a4df7114f35724c472152ca74877b6bd04`, ran the
  ordinary CLI as-is and on a copy with only the five comment lines removed,
  then recomputed the strict `paths` oracle and exhaustive selection comparison.
- It then ran the installed Fast Lane pipeline on the **unmodified** lexical
  checkout with only `_load_tsconfig_aliases` patched in memory. The harness
  asserted the original config and `ReactExtension.tsx` hashes were unchanged
  after the run, restored the stock method, found all 4,256 verified
  relationships in the corrected graph, matched the control React Optimal
  selection exactly, asserted the corrected valid-JSONC graph has no tsconfig
  warning, and recomputed corrected-vs-stock selection recoveries.
- It then ran the deterministic answerability audit on the actual as-is,
  control, and corrected repository-context ZIPs: six predeclared
  `ReactExtension.tsx` maintenance tasks require exact fragments in selected
  Optimal chunks from their answering files. The negative control passes in
  all three bundles.
- It finally ran the exhaustive symbol-evidence audit across all 4,256
  verified relationships. Of 10,715 candidate source-specific symbol tasks,
  10,703 were eligible; the workflow asserts 8,163 Optimal and 9,182 Wider
  recovered definition/export instances in both control and corrected
  bundles.
- Published annotation:
  > `as-is edges=1263, control edges=5519, verified lost file
  > relationships=4256, Optimal direct dependencies recovered=2707;
  > in-memory corrected original edges=5519, corrected-vs-stock
  > Optimal/Wider=2707/3345; answer-bearing Optimal tasks
  > as-is/control/corrected=0/6/6 of 6; eligible symbol-definition
  > tasks=10703 (candidate=10715, sources=1239, definition_files=182);
  > Optimal definitions as-is/control/corrected=726/8826/8826, recovered
  > control/corrected=8163/8163; Wider definitions
  > as-is/control/corrected=711/9883/9883, recovered
  > control/corrected=9182/9182`
- Artifact `lexical-clean-environment-evidence`:
  - ID `13232150404`
  - 338,347 bytes
  - SHA-256 `5152cd0ad8a6482f8ee6e59b45a07bb41bb0b6f201740d7233d99890fa068a63`

Therefore the lexical graph and direct downstream-selection result no longer
depends on the sandbox grammar workaround. The corrected run is Fast Lane
graph/context evidence; it is not presented as a shipped fix or as a completed
later hosted-stage result.

## 3. Independent ng-matero under an ordinary installation

- Workflow: **Ng-matero clean-environment validation**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41638056555
- Result: **success**
- It fetched ng-matero at `d351bf5957d8c6dc9eca79d0c9b260c5b8d07822`,
  verified the original root-config SHA-256, ran the ordinary CLI as-is and
  on a copy with only the two leading block comments removed, recomputed the
  strict `paths` oracle, ran TypeScript 5.9.3's compiler API over all gained
  rows, and compared the exported selections. Both runs scan 300 files and
  extract the same 1,192 import records.
- It then ran the installed Fast Lane pipeline on the **unmodified**
  ng-matero checkout with the reference loader/builder-warning integration in
  memory, restored all 111 verified relationships and 241 edges with no
  warning, and recomputed 107 Optimal/Wider recoveries versus stock.
- Its three predeclared `src/app/app.config.ts` final-artifact tasks are
  0/3 as-is and 3/3 in both control and corrected bundles; the source-file
  negative control is 1/1 throughout.
- Published annotation:
  > `as-is edges=130, control edges=241, TypeScript-verified lost
  > relationships=111, Optimal/Wider direct dependencies recovered=107/107;
  > in-memory corrected original edges=241, corrected-vs-stock
  > Optimal/Wider=107/107; answer-bearing Optimal tasks
  > as-is/control/corrected=0/3/3 of 3`
- Artifact `ng-matero-clean-environment-evidence`:
  - ID `13232066872`
  - 16,135 bytes
  - SHA-256 `2a6d88503c5672b628068fc440e2ce412432fdd580dfeea76f6c6df62d973e20`

This removes the earlier local grammar-fallback caveat from the ng-matero
graph/selection/corrected/answerability claims.

## 4. Manual post-fix regression

- Workflow: **Manual post-fix regression — JSONC expected behavior**
- Trigger: `workflow_dispatch` only; it intentionally does not create a PR
  check on the affected release.
- Selected-version command: `python reproduction/repro_unit.py --expect-fixed`
- On UnvibeCode 0.3.15 this raw test fails for the four JSONC fixtures; that
  exact child failure is also visible inside the successful
  `verify-affected-version.log` in run `41638056309`. It should become green
  only after JSONC tsconfig aliases load correctly.

## Retrieval note

GitHub's artifact/log download hosts are not reachable from the restricted
investigation sandbox, so the artifact ZIPs could not be copied into this
repository from that environment. The run links, artifact IDs/digests, step
conclusions, and annotations above were retrieved through the GitHub API. The
workflow logs/artifacts remain the primary CI record; this file is a compact
index, not a reconstructed log.
