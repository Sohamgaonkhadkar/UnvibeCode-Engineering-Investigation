# Clean-environment verification — GitHub Actions

The earlier sandbox could not obtain `tree-sitter-language-pack` grammars through
its restricted egress, so local large-repository CLI runs used a disclosed
fallback grammar shim. The runs below close that reproducibility gap in a normal
GitHub-hosted environment. They install only the pinned public package
(`unvibecode==0.3.15`) with Python 3.12 on `ubuntu-latest`; no shim is present.

All three workflows ran from investigation commit
`d1338184f60e7282383fbf83be75afd1001badf9`.

## 1. Known-bug reproduction + correction + minimal standard CLI

- Workflow: **JSONC defect reproduction (UnvibeCode 0.3.15)**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41360396080
- Result: **success**
- Successful steps include:
  - TypeScript 5.9.3 `tsc --showConfig` on strict, line-comment, block-comment,
    trailing-comma, string-safety, and combined JSONC fixtures;
  - `repro_unit.py` in known-bug mode;
  - `correction_poc.py`;
  - `ci_cli_comparison.py` using `python -m unvibecode review`.
- Published annotation:
  > `status=PASS_KNOWN_BUG_REPRODUCED; strict: cli_exit=1, timed_out=False,
  > files=2, file_edges=1, unresolved=0, file_import=1, symbol_fallback=1,
  > grammar_download_error=False; jsonc: cli_exit=1, timed_out=False, files=2,
  > file_edges=0, unresolved=1, file_import=0, symbol_fallback=1,
  > grammar_download_error=False`
- Artifact `jsonc-verification-logs`:
  - ID `13105615011`
  - 5,787 bytes
  - SHA-256 `595a9661ba3f2ae826ac9c09d036b5172d4ff75d26541377e30bc131a7cb050c`

The minimal CLI processes exit 1 after producing the local graph and context
bundle. Those are the artifacts under test; the comparison does not claim that a
later hosted stage completed. Both variants have the same process outcome, so it
cannot explain the strict-vs-JSONC file-edge difference.

## 2. Lexical under the same ordinary installation

- Workflow: **Lexical clean-environment validation**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41360396130
- Result: **success**
- It fetched lexical at `164af6a4df7114f35724c472152ca74877b6bd04`, ran the
  ordinary CLI as-is and on a copy with only the five comment lines removed,
  then recomputed the strict `paths` oracle and exhausted selection comparison.
- Published annotation:
  > `as-is edges=1263, control edges=5519, verified lost file
  > relationships=4256, Optimal direct dependencies recovered=2707`
- Artifact `lexical-clean-environment-evidence`:
  - ID `13105505434`
  - 116,915 bytes
  - SHA-256 `156080638d43b863356aaeb933baba9efacdd2d7603ec83914b33e317e356cb1`

Therefore the lexical graph and direct downstream-selection result no longer
depends on the sandbox grammar workaround.

## 3. Expected-behavior regression — intentionally red

- Workflow: **JSONC expected behavior regression (red on 0.3.15)**
- Run: https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41360396004
- Result: **failure**, at `repro_unit.py --expect-fixed`, as expected on the
  unpatched release.
- This workflow does **not** use `continue-on-error`: it should become green only
  after JSONC tsconfig aliases load correctly. The green workflow above is a
  successful demonstration that the known defect reproduces; it is not a claim
  that expected behaviour passes.

## Retrieval note

GitHub's artifact/log download hosts are not reachable from the restricted
investigation sandbox, so the artifact ZIPs could not be copied into this
repository from that environment. The run links, artifact IDs/digests, step
conclusions, and annotations above were retrieved through the GitHub API. The
workflow logs/artifacts remain the primary CI record; this file is a compact
index, not a reconstructed log.
