# Clean-environment verification — GitHub Actions

The earlier sandbox could not obtain `tree-sitter-language-pack` grammars through
its restricted egress, so local large-repository CLI runs used a disclosed
fallback grammar shim. The runs below close that reproducibility gap in a normal
GitHub-hosted environment. They install only the pinned public package
(`unvibecode==0.3.15`) with Python 3.12 on `ubuntu-latest`; no shim is present.

The latest fully indexed functional verification ran from investigation commit
`5eca99bf64319afdf4e04983e2b6a06c6f1e9340`. Documentation-only commits after
that commit may rerun the same workflows; PR #1's check rollup is the
authoritative status for the current branch head.

## How to read the PR checks

- **Affected-version verification** is green only when the strict control
  resolves, the raw `repro_unit.py --expect-fixed` regression fails only for
  the four exact JSONC fixtures with `aliases={}` and
  `resolution=(None, None)`, the correction proof of concept passes, and the
  committed evidence counts reconcile.
- Therefore, a green PR check means **the 0.3.15 defect was reproduced and
  verified exactly**. It does **not** mean correct JSONC behaviour already
  passes.
- **Manual post-fix regression** keeps the original
  `reproduction/repro_unit.py --expect-fixed` test. It is deliberately manual
  (`workflow_dispatch`) rather than a permanently red PR gate. There is no
  `continue-on-error` masking its result.

## 1. Unified affected-version verification + minimal standard CLI

- Workflow: **PR verification — JSONC defect reproduced exactly (0.3.15)**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41415515251
- Job: **Affected-version verification — exact defect, correction PoC, evidence**
- Result: **success**
- Successful steps include:
  - TypeScript 5.9.3 `tsc --showConfig` on strict, line-comment, block-comment,
    trailing-comma, string-safety, and combined JSONC fixtures;
  - `python reproduction/verify.py`, which runs the known-bug reproducer,
    asserts the exact `--expect-fixed` failure shape, runs the correction PoC,
    and verifies committed lexical/ng-matero evidence;
  - `ci_cli_comparison.py` using `python -m unvibecode review`.
- Published CLI annotation:
  > `status=PASS_KNOWN_BUG_REPRODUCED; strict: cli_exit=1, timed_out=False,
  > files=2, file_edges=1, unresolved=0, file_import=1, symbol_fallback=1,
  > grammar_download_error=False; jsonc: cli_exit=1, timed_out=False, files=2,
  > file_edges=0, unresolved=1, file_import=0, symbol_fallback=1,
  > grammar_download_error=False`
- Artifact `jsonc-verification-logs`:
  - ID `13127406837`
  - 5,993 bytes
  - SHA-256 `b4439f89ab4a945797dd44d790c0040c0ea8078f47fa76391c2a5de6444861d6`

The minimal CLI processes exit 1 after producing the local graph and context
bundle. Those are the artifacts under test; the comparison does not claim that a
later hosted stage completed. Both variants have the same process outcome, so it
cannot explain the strict-vs-JSONC file-edge difference.

## 2. Lexical under the same ordinary installation

- Workflow: **Lexical clean-environment validation**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41415515230
- Result: **success**
- It fetched lexical at `164af6a4df7114f35724c472152ca74877b6bd04`, ran the
  ordinary CLI as-is and on a copy with only the five comment lines removed,
  then recomputed the strict `paths` oracle and exhaustive selection comparison.
- Published annotation:
  > `as-is edges=1263, control edges=5519, verified lost file
  > relationships=4256, Optimal direct dependencies recovered=2707`
- Artifact `lexical-clean-environment-evidence`:
  - ID `13127906021`
  - 116,917 bytes
  - SHA-256 `ebb397b00484d0f55e050eda104d9a4652cd900a43e52a825a6da8674e661fb2`

Therefore the lexical graph and direct downstream-selection result no longer
depends on the sandbox grammar workaround.

## 3. Manual post-fix regression

- Workflow: **Manual post-fix regression — JSONC expected behavior**
- Trigger: `workflow_dispatch` only; it intentionally does not create a PR
  check on the affected release.
- Selected-version command: `python reproduction/repro_unit.py --expect-fixed`
- On UnvibeCode 0.3.15 this raw test fails for the four JSONC fixtures; that
  exact child failure is also visible inside the successful
  `verify-affected-version.log` in run `41415515251`. It should become green
  only after JSONC tsconfig aliases load correctly.

## Retrieval note

GitHub's artifact/log download hosts are not reachable from the restricted
investigation sandbox, so the artifact ZIPs could not be copied into this
repository from that environment. The run links, artifact IDs/digests, step
conclusions, and annotations above were retrieved through the GitHub API. The
workflow logs/artifacts remain the primary CI record; this file is a compact
index, not a reconstructed log.
