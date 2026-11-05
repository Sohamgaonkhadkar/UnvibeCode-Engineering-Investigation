# Clean-environment verification — GitHub Actions

The earlier sandbox could not obtain `tree-sitter-language-pack` grammars through
its restricted egress, so local large-repository CLI runs used a disclosed
fallback grammar shim. The runs below close that reproducibility gap in a normal
GitHub-hosted environment. The principal jobs install only the pinned public
package (`unvibecode==0.3.15`) with Python 3.12 on `ubuntu-latest`; no shim
is present. A separate matrix repeats the lightweight exact-symptom and
reference-loader verification across CPython/platform combinations.

The latest fully indexed functional verification below ran from investigation
commit `6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb`, which contains the
hardened reference solution (true-trailing-comma tracking, Python-constant
rejection, explicit nesting bound, strict UTF-8 config reading), its unit
tests and 2,277-case adversarial differential probe, graph-warning
integration check, patched-install rehearsal, recovered-edge concentration
audit, lexical and ng-matero final-artifact audits, exhaustive
symbol-evidence audit, and direct public-config loader-behavior evidence.
All 10 PR checks passed at that commit. Follow-up PR #2's check rollup
remains the authoritative status for any later branch head. (The original
investigation was merged through PR #1.)

### Complete indexed run chain — five heads, 10/10 checks each

The detailed artifact IDs and annotations in sections 1–3 below were indexed
from the `6c6c6b2` runs and are unchanged by later commits, which touched
documentation, static-analysis hygiene, the macOS runner label, workflow path
filters, and the documentation-consistency gate only. Every head since then
re-ran the same workflows successfully:

| Investigation commit | Role | Main verification | Lexical | ng-matero | Checks |
|---|---|---|---|---|---|
| `6c6c6b2cd8d046db6e005ea19f5d188ec5e71cfb` | Fully indexed functional snapshot; source of the artifact IDs and digests in sections 1–3 | [`41670913945`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913945) | [`41670913810`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913810) | [`41670913798`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913798) | 10/10 |
| `db66414055bd14e5ea2e060e461c7d7ece05098c` | `macos-15` pin; first head at which the macOS scope job acquired a runner | [`41888843627`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41888843627) | [`41888843612`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41888843612) | [`41888843626`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41888843626) | 10/10 |
| `cb7f142e50d1f2996316ca7c3c8cea4e8c905a35` | Duplicate sweep refreshed through #532; path filters widened so documented claims re-verify | [`42102730901`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42102730901) | [`42102730917`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42102730917) | [`42102731184`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42102731184) | 10/10 |
| `ca4f1b0e342bbbe0bc987775c7f6b6498ad893ec` | Machine-readable provenance records; `check_docs.py` wired into `verify.py` | [`42104144262`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42104144262) | [`42104144266`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42104144266) | [`42104144238`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42104144238) | 10/10 |
| `18295e1c1df280f42bef0c3100e5ba12c694e467` | Documentation gate published as an API-readable annotation | [`42105139576`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42105139576) | [`42105139604`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42105139604) | [`42105139753`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42105139753) | 10/10 |

Every main-verification run completed 8/8 jobs. No step in any
clean-environment job was skipped at any head: the jobs API reports 15 (lexical)
and 16 (ng-matero) step entries, which are the 12 defined workflow steps plus
`Set up job`, the `Post` cleanup steps, and `Complete job`, and every entry is
`completed`/`success`. At `18295e1` the affected-version job reports 19 step
entries and its step 8 is the documentation-consistency gate.

macOS scope-job acquisition at the three heads that recorded it: 605 s queue /
41 s run at `db66414`, 4 s / 110 s at `cb7f142`, and 6 s / 159 s at `18295e1`.

The lexical job re-executed the substantive work rather than short-circuiting:
ordinary install of the pinned package, as-is and comment-stripped control CLI
runs, strict-`paths` oracle and selection recomputation, in-memory-corrected
Fast Lane on the unmodified checkout, the answerability audit, the exhaustive
symbol-definition audit, and the published count assertion.

Self-reference limit, stated plainly: every documentation or evidence commit
re-triggers these workflows, so the newest head's own runs necessarily complete
after the index that would cite them. PR #2's live check rollup is therefore
authoritative for any head newer than those listed here, and
[`../ci_status.json`](../ci_status.json) is the machine-readable record that
[`../../reproduction/check_docs.py`](../../reproduction/check_docs.py) checks
this document against in both directions.

### Documentation-consistency gate

The affected-version job enforces `reproduction/check_docs.py` twice: once
inside `verify.py`'s evidence stage, and once as its own step so that the
outcome is published as an annotation titled **Documentation and claim
consistency**. The annotation is deliberately the observable surface for this
check, because GitHub's log and artifact download hosts are unreachable from
the restricted investigation sandbox (see the retrieval note at the end of this
file) while the check-run annotations API is reachable.

The step is a hard gate: `set -o pipefail` on the checker, then assertions that
the recorded status is `passed`, that `checks_failed` is 0, and that at least 10
checks passed. There is no `continue-on-error`. A stale documented claim — for
example a sweep scope that no longer matches
[`../duplicate_sweep.json`](../duplicate_sweep.json), a cited Actions run that
is not recorded, or a broken permalink — fails the job. Both directions were
exercised locally before the step was added: the step exits 0 and prints its
annotation on the committed tree, and exits 1 with
`FAIL sweep scope #532 is stated in all three sweep documents; README.md does
not mention #532` when that one claim is artificially aged.

The annotation published by the run at `18295e1` (affected-version job
`127517840349`, step 8, conclusion `success`), retrieved verbatim through the
check-run annotations API rather than from a log download, reads:

> `Documentation and claim consistency: status=passed, checks passed=10,
> duplicate sweep=2026-11-05 issues=434 newest=#532 same_mechanism=[451],
> indexed CI snapshots=3`

The same API retrieval path supplies every other annotation quoted in this
file, so the gate's outcome is verifiable from a restricted environment.

### macOS scope-job runner acquisition

The platform matrix's macOS entry was cancelled before executing any step on
three successive heads — with the floating `macos-latest` label (job
`126192817755` in run
[`41715070598`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41715070598)
at `029b9ef`, job `126761623582` in run
[`41883465788`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41883465788)
at `b12105f`) and with an explicit Intel label (job `126771193611` in run
[`41886199794`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41886199794)
at `061c3b7`). Each cancelled job
reported `runner_id: 0` with zero steps, and the check-run annotations API
returns GitHub's own diagnosis verbatim:

> `failure: The job was not acquired by Runner of type hosted even after
> multiple attempts`

> `notice: Due to capacity constraints, jobs targeting macOS arm64 runners may
> experience longer queue times.`

These were therefore hosted-capacity acquisition failures, not defect, test, or
platform-behaviour failures, and no macOS evidence claim ever depended on them.
In each of those three runs the other seven jobs — affected-version
verification, the four Ubuntu scope jobs, the Windows scope job, and the
patched-install rehearsal — all succeeded, so the runs' overall `failure`
conclusion is attributable solely to the unacquired macOS job. An API job rerun
returned `403 Resource not accessible by integration`.
Pinning the job to `macos-15` allowed it to acquire a runner after a
605-second queue (started 18:46:42Z for a run dispatched at 18:36:37Z) and
complete successfully in 41 seconds. The next head, `cb7f142`, acquired the
same pinned label in 4 seconds and passed in 110 seconds, which is consistent
with transient hosted capacity rather than a label-specific fault. Section 1's
platform-scope description below refers to the indexed `6c6c6b2` run, whose
macOS job used the then floating label; the current workflow pins `macos-15`.

## How to read the PR checks

- **Affected-version verification** is green only when the strict control
  resolves, the raw `repro_unit.py --expect-fixed` regression fails only for
  the four exact JSONC fixtures with `aliases={}` and
  `resolution=(None, None)`, the reference-solution corpus, unit tests, and
  loader pass, the TypeScript/`jsonc-parser` differential and adversarial
  boundary/mutation results reproduce, the reversible A/B/C/D/E intervention
  and targeted boundaries pass on both
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
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913945
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
    committed lexical/ng-matero, reference-validation, adversarial-probe,
    recovered-edge-concentration, version-scope, exposure-sample,
    public-config loader-behavior, and answerability-task evidence;
  - `python -m unittest -v solution.test_tsconfig_jsonc` (10 tests), covering
    the parser generated corpus, true/leading trailing commas, constants,
    oversized integers, the explicit nesting bound, invalid shapes, strict
    UTF-8 reading, and non-regular/broken-symlink config states;
  - a validation-only TypeScript 5.9.3 + Microsoft `jsonc-parser` 3.3.1
    differential run, reproducing 514/514 TypeScript and 510/514
    `jsonc-parser` valid-document agreements and 13 diagnosed invalid cases;
  - the adversarial differential probe, reproducing 865 all-accept cases,
    1,316 all-reject cases, and zero critical divergences over 2,277
    enumerated-boundary/seeded-mutation cases;
  - `causal_intervention.py --full-pipeline`, which repeats A/B/C/D/E through
    the installed Fast Lane `run_pipeline()`, inspects the actual resolved
    graph and complete-repository-context ZIP, and proves that a malformed
    config yields no stock graph warning but exactly one exported
    `tsconfig_parse_failed` warning with the builder-level reference
    integration;
  - `ci_cli_comparison.py` using `python -m unvibecode review`.
- Published differential annotation:
  > `candidate/TypeScript valid agreements=514/514; candidate/jsonc-parser
  > valid agreements=510/514; diagnosed invalid cases=13`
- Published adversarial-probe annotation:
  > `cases=2277; all-accept=865; all-reject=1316;
  > candidate-only-accepts=0; candidate-only-rejects=0; all-accept value
  > mismatches=0`
- Published CLI annotation:
  > `status=PASS_KNOWN_BUG_REPRODUCED; strict: cli_exit=1, timed_out=False,
  > files=2, file_edges=1, unresolved=0, file_import=1, symbol_fallback=1,
  > grammar_download_error=False; jsonc: cli_exit=1, timed_out=False, files=2,
  > file_edges=0, unresolved=1, file_import=0, symbol_fallback=1,
  > grammar_download_error=False`
- Artifact `jsonc-verification-logs`:
  - ID `13248261197`
  - 19,150 bytes
  - SHA-256 `2c75f812efcde07d2585e5f2e8f245451eec3a9a2ab8d537dd82b2dab06bda11`

The minimal CLI processes exit 1 after producing the local graph and context
bundle. Those are the artifacts under test; the comparison does not claim that a
later hosted stage completed. Both variants have the same process outcome, so it
cannot explain the strict-vs-JSONC file-edge difference.

The same workflow run also completed six **Platform/Python scope** jobs:
CPython 3.11, 3.12, 3.13, and 3.14 on `ubuntu-latest`, plus CPython 3.12 on
`windows-latest` and `macos-latest`. Each normally installed 0.3.15, ran
`verify.py --skip-evidence` (known-bug reproduction, exact `--expect-fixed`
failure, reference corpus/loader, and both-engine causal intervention), and
ran the 10 reference parser/loader unit tests.

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
  > warning codes=['tsconfig_parse_failed']; invalid-UTF-8 resolver warning
  > codes=['tsconfig_read_failed', 'tsconfig_read_failed']`
- Artifact `patched-install-rehearsal-evidence`:
  - ID `13248391168`
  - 6,242 bytes
  - SHA-256 `d41ee3bce0744883d1d23496a0a944e012bcce1b4f2eeb2b687a43d70a730e9b`

## 2. Lexical under the same ordinary installation

- Workflow: **Lexical clean-environment validation**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913810
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
  - ID `13248786574`
  - 338,338 bytes
  - SHA-256 `6fbe87c263845db928ae2fd133d70dc3df04eb0c2356f452a148911d1816740e`

Therefore the lexical graph and direct downstream-selection result no longer
depends on the sandbox grammar workaround. The corrected run is Fast Lane
graph/context evidence; it is not presented as a shipped fix or as a completed
later hosted-stage result.

## 3. Independent ng-matero under an ordinary installation

- Workflow: **Ng-matero clean-environment validation**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41670913798
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
  - ID `13247723291`
  - 16,128 bytes
  - SHA-256 `db3a9c48a9264ac97f3183d76a438214f7f972f0406b71f459489b111aa93389`

This removes the earlier local grammar-fallback caveat from the ng-matero
graph/selection/corrected/answerability claims.

## 4. Manual post-fix regression

- Workflow: **Manual post-fix regression — JSONC expected behavior**
- Trigger: `workflow_dispatch` only; it intentionally does not create a PR
  check on the affected release.
- Selected-version command: `python reproduction/repro_unit.py --expect-fixed`
- On UnvibeCode 0.3.15 this raw test fails for the four JSONC fixtures; that
  exact child failure is also visible inside the successful
  `verify-affected-version.log` in run `41670913945`. It should become green
  only after JSONC tsconfig aliases load correctly.

## Retrieval note

GitHub's artifact/log download hosts are not reachable from the restricted
investigation sandbox, so the artifact ZIPs could not be copied into this
repository from that environment. The run links, artifact IDs/digests, step
conclusions, and annotations above were retrieved through the GitHub API. The
workflow logs/artifacts remain the primary CI record; this file is a compact
index, not a reconstructed log.
