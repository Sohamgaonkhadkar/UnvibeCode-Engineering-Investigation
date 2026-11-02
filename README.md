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
- A reversible A/B/C/D/E intervention passes on both shipped resolver copies:
  original JSONC fails, removing only comments restores it, restoring the
  config fails again, an in-memory tolerant loader restores it, and removing
  that diagnostic patch fails again—all with source hashes unchanged.
- In clean GitHub Actions, the same sequence restores the minimal Fast Lane
  graph/context output, and patching only the loader in memory on unmodified
  lexical restores 5,519 edges and the exact control `ReactExtension.tsx`
  Optimal selection.
- A normal pinned install in GitHub Actions reproduces the minimal fixture,
  correction proof of concept, full lexical counts, and selection impact.
- The PR check is green only when the affected release fails the post-fix
  regression for the exact documented symptom. That means **successful defect
  verification**, not successful expected behaviour. The raw regression is an
  explicitly manual post-fix workflow.

## Reproduce

Install the tested release and run the single verification entry point:

```bash
python -m pip install unvibecode==0.3.15
python reproduction/verify.py
```

`verify.py` checks the Python/package environment, runs the strict control and
all JSONC variants, asserts that `repro_unit.py --expect-fixed` fails only for
the exact four empty-alias JSONC cases, runs the correction proof of concept,
runs the reversible causal intervention and targeted boundary checks on both
resolver copies, and checks the committed lexical/ng-matero evidence counts.
The original scripts remain directly runnable:

```bash
python reproduction/repro_unit.py
python reproduction/repro_unit.py --expect-fixed  # post-fix regression; fails on 0.3.15
python reproduction/correction_poc.py
python reproduction/causal_intervention.py --output causal-intervention.json
# In an environment with working tree-sitter extraction, also inspect the
# actual Fast Lane graph/context ZIP for every A/B/C/D/E state:
python reproduction/causal_intervention.py --full-pipeline --output causal-intervention-full.json
```

For an ordinary-install minimal CLI comparison:

```bash
python reproduction/ci_cli_comparison.py --output-root ./cli-comparison-output
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
reproducers, string-aware correction PoC, reversible causal intervention,
targeted boundary checks, TypeScript paths oracle, graph capture, bundle
selection comparison, representative-case extractor, and TypeScript
compiler-API representative resolver and batch verifier.

`evidence/tsconfig-jsonc/` contains compact machine-readable results: the
4,256-row lost-relationship list, direct selection-omission list, causal
intervention record, aggregate summaries with input hashes, TypeScript API
resolutions, configs/diffs, CI index, artifact manifest, and the independent
ng-matero evidence.

Local large-repository runs in the restricted investigation sandbox used a
disclosed grammar shim because release-asset downloads are blocked there. That
workaround is documented for provenance, but the lexical conclusion has since
been independently reproduced in GitHub Actions under a standard installation.
No claim depends on hosted or LLM output.
