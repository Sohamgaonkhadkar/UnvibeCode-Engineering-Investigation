# Clean-environment verification — GitHub Actions

The earlier sandbox could not obtain `tree-sitter-language-pack` grammars through
its restricted egress, so local large-repository CLI runs used a disclosed
fallback grammar shim. The runs below close that reproducibility gap in a normal
GitHub-hosted environment. They install only the pinned public package
(`unvibecode==0.3.15`) with Python 3.12 on `ubuntu-latest`; no shim is present.

The latest fully indexed functional verification below ran from investigation
commit `edb2149a8b4801614336ad9b51505731e6e716fc`, which contains the
reference solution and scope evidence. Follow-up PR #2's check rollup remains
the authoritative status for any later branch head. (The original
investigation was merged through PR #1.)

## How to read the PR checks

- **Affected-version verification** is green only when the strict control
  resolves, the raw `repro_unit.py --expect-fixed` regression fails only for
  the four exact JSONC fixtures with `aliases={}` and
  `resolution=(None, None)`, the reference-solution corpus and loader pass,
  the reversible A/B/C/D/E intervention and targeted boundaries pass on both
  resolver copies, and the committed evidence counts reconcile.
- Therefore, a green PR check means **the 0.3.15 defect was reproduced and
  verified exactly**. It does **not** mean correct JSONC behaviour already
  passes.
- **Manual post-fix regression** keeps the original
  `reproduction/repro_unit.py --expect-fixed` test. It is deliberately manual
  (`workflow_dispatch`) rather than a permanently red PR gate. There is no
  `continue-on-error` masking its result.

## 1. Unified affected-version verification + minimal standard CLI

- Workflow: **PR verification — JSONC defect reproduced exactly (0.3.15)**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41618709857
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
    committed lexical/ng-matero, reference-validation, version-scope, and
    exposure-sample evidence;
  - `causal_intervention.py --full-pipeline`, which repeats A/B/C/D/E through
    the installed Fast Lane `run_pipeline()` and inspects the actual resolved
    graph and complete-repository-context ZIP;
  - `ci_cli_comparison.py` using `python -m unvibecode review`.
- Published CLI annotation:
  > `status=PASS_KNOWN_BUG_REPRODUCED; strict: cli_exit=1, timed_out=False,
  > files=2, file_edges=1, unresolved=0, file_import=1, symbol_fallback=1,
  > grammar_download_error=False; jsonc: cli_exit=1, timed_out=False, files=2,
  > file_edges=0, unresolved=1, file_import=0, symbol_fallback=1,
  > grammar_download_error=False`
- Artifact `jsonc-verification-logs`:
  - ID `13222721647`
  - 11,344 bytes
  - SHA-256 `e2647606804b20ac2e55cde8635945e575b9639571ce4a578084e8ebabd00211`

The minimal CLI processes exit 1 after producing the local graph and context
bundle. Those are the artifacts under test; the comparison does not claim that a
later hosted stage completed. Both variants have the same process outcome, so it
cannot explain the strict-vs-JSONC file-edge difference.

## 2. Lexical under the same ordinary installation

- Workflow: **Lexical clean-environment validation**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41618709640
- Result: **success**
- It fetched lexical at `164af6a4df7114f35724c472152ca74877b6bd04`, ran the
  ordinary CLI as-is and on a copy with only the five comment lines removed,
  then recomputed the strict `paths` oracle and exhaustive selection comparison.
- It then ran the installed Fast Lane pipeline on the **unmodified** lexical
  checkout with only `_load_tsconfig_aliases` patched in memory. The harness
  asserted the original config and `ReactExtension.tsx` hashes were unchanged
  after the run, restored the stock method, found all 4,256 verified
  relationships in the corrected graph, matched the control React Optimal
  selection exactly, and recomputed corrected-vs-stock selection recoveries.
- Published annotation:
  > `as-is edges=1263, control edges=5519, verified lost file
  > relationships=4256, Optimal direct dependencies recovered=2707;
  > in-memory corrected original edges=5519, corrected-vs-stock
  > Optimal/Wider=2707/3345`
- Artifact `lexical-clean-environment-evidence`:
  - ID `13222059310`
  - 182,639 bytes
  - SHA-256 `690579897f4e25a1b2e91b1e218f3790b2fc9563d138b08da75f2276cb5d3f7f`

Therefore the lexical graph and direct downstream-selection result no longer
depends on the sandbox grammar workaround. The corrected run is Fast Lane
graph/context evidence; it is not presented as a shipped fix or as a completed
later hosted-stage result.

## 3. Manual post-fix regression

- Workflow: **Manual post-fix regression — JSONC expected behavior**
- Trigger: `workflow_dispatch` only; it intentionally does not create a PR
  check on the affected release.
- Selected-version command: `python reproduction/repro_unit.py --expect-fixed`
- On UnvibeCode 0.3.15 this raw test fails for the four JSONC fixtures; that
  exact child failure is also visible inside the successful
  `verify-affected-version.log` in run `41618709857`. It should become green
  only after JSONC tsconfig aliases load correctly.

## Retrieval note

GitHub's artifact/log download hosts are not reachable from the restricted
investigation sandbox, so the artifact ZIPs could not be copied into this
repository from that environment. The run links, artifact IDs/digests, step
conclusions, and annotations above were retrieved through the GitHub API. The
workflow logs/artifacts remain the primary CI record; this file is a compact
index, not a reconstructed log.
