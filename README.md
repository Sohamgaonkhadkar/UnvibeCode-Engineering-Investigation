# UnvibeCode Engineering Investigation — Cohort 3, Track 1

## Finding

UnvibeCode **0.3.15** silently discards TypeScript path aliases when the
repository-root `tsconfig.json` contains a comment or trailing comma. Those are
valid JSONC features, but `LanguageAwareImportResolver._load_tsconfig_aliases`
uses strict `json.loads` inside a bare `except: pass`; the parse failure leaves
an empty alias table and emits no warning.

The effect is now established beyond graph counts:

- On `meta/lexical@164af6a`, removing only five `//` lines raises internal file
  edges from **1,263 to 5,519**. A strict TypeScript-`paths` recount verifies
  all **4,256** gained relationships.
- In the actual exported context bundles, **2,707** verified direct
  dependencies are missing from as-is **Optimal** selections and restored in
  the control; **3,345** in **Wider**.
- The same controlled transformation on independent
  `ng-matero/ng-matero@d351bf59` restores **111** verified relationships and
  107 direct context dependencies.
- A normal pinned install in GitHub Actions reproduces the minimal fixture,
  correction proof of concept, full lexical counts, and selection impact.
- A separate expected-behaviour workflow is intentionally red on 0.3.15; it is
  the post-fix regression test, not a passing check disguised by test inversion.

## Reproduce

Install the tested release and run the assertion-based unit reproducer:

```bash
python -m pip install unvibecode==0.3.15
python reproduction/repro_unit.py
# Post-fix regression form (expected to FAIL on 0.3.15):
python reproduction/repro_unit.py --expect-fixed
# Correction feasibility proof of concept:
python reproduction/correction_poc.py
```

For an ordinary-install minimal CLI comparison:

```bash
python reproduction/ci_cli_comparison.py --output-root /tmp/jsonc-cli
```

To regenerate the lexical graph and downstream context analysis, use
`reproduction/capture_run.py`, `reproduction/analyze_alias_oracle.py`, and
`reproduction/compare_selections.py`; the exact command outline and hashes are
in `evidence/tsconfig-jsonc/ARTIFACT_MANIFEST.md`.

Clean-environment runs and workflow links are indexed in
`evidence/tsconfig-jsonc/CI_VERIFICATION.md`.

## Key documents

- `ROOT_CAUSE.md` — stage-by-stage mechanism, strict recount, boundaries.
- `DUPLICATE_CHECK.md` — mechanism-level comparison with upstream issues.
- `evidence/tsconfig-jsonc/CONTEXT_SELECTION_IMPACT.md` — exhaustive downstream
  impact and the representative `ReactExtension.tsx` case.
- `evidence/tsconfig-jsonc/ng-matero/README.md` — independent repository result.
- `evidence/BENCHMARK_METHOD_AUDIT.md` — benchmark methods adopted after the
  defect had been found; no competitor findings are reused.
- `evidence/EXPERIMENT_LOG.md` — all positive, negative, rejected, and audit
  results.
- `INDEPENDENT_STRATEGY.md` — original strategy, preserved unchanged.
- `submission/GITHUB_ISSUE.md` — official nine-section issue draft; **not yet
  filed**. `submission/FORM_RESPONSE.md` still awaits the real issue URL.

## Evidence and scripts

`reproduction/` contains the minimal strict/JSONC fixtures, resolver and CLI
reproducers, string-aware correction PoC, TypeScript paths oracle, graph
capture, bundle selection comparison, representative-case extractor, and
TypeScript compiler-API representative resolver and batch verifier.

`evidence/tsconfig-jsonc/` contains compact machine-readable results: the
4,256-row lost-relationship list, direct selection-omission list, aggregate
summaries with input hashes, TypeScript API resolutions, configs/diffs, CI
index, artifact manifest, and the independent ng-matero evidence.

Local large-repository runs in the restricted investigation sandbox used a
disclosed grammar shim because release-asset downloads are blocked there. That
workaround is documented for provenance, but the lexical conclusion has since
been independently reproduced in GitHub Actions under a standard installation.
No claim depends on hosted or LLM output.
