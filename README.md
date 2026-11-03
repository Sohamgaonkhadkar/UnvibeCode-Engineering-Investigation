# UnvibeCode Engineering Investigation — Cohort 3, Track 1

## Finding

UnvibeCode **0.3.15** silently discards TypeScript path aliases when the
repository-root `tsconfig.json` contains a comment or trailing comma. Those are
valid JSONC features, but `LanguageAwareImportResolver._load_tsconfig_aliases`
uses strict `json.loads` inside a swallowing `except Exception: pass`; the parse failure leaves
an empty alias table and emits no warning.

The effect is now established beyond graph counts:

- On `meta/lexical@164af6a`, removing only five `//` lines raises internal file
  edges from **1,263 to 5,519**. A strict TypeScript-`paths` recount verifies
  all **4,256** gained relationships.
- In the actual exported context bundles, **2,707** verified direct
  dependencies are missing from as-is **Optimal** selections and restored in
  the control; **3,345** in **Wider**.
- A deterministic final-artifact audit of the exported lexical Optimal ZIPs
  finds **0/6** predeclared answer-bearing maintenance tasks supported as-is,
  versus **6/6** in both the control and reference-loader corrected bundles;
  its negative control passes in all three.
- An exhaustive companion derives 10,703 eligible source-specific
  imported-symbol tasks from all 4,256 verified lexical relationships. In
  Optimal selections, a recognizable definition/export line is available for
  726 as-is versus 8,826 in both control and corrected bundles—**8,163
  recovered instances** (9,182 at Wider).
- The same controlled transformation on independent
  `ng-matero/ng-matero@d351bf59` restores **111** verified relationships and
  107 direct context dependencies. Its final-artifact audit is likewise
  **0/3 as-is versus 3/3 control/corrected**, now reproduced under an
  ordinary install in a dedicated clean-environment workflow.
- A reversible A/B/C/D/E intervention passes on both shipped resolver copies:
  original JSONC fails, removing only comments restores it, restoring the
  config fails again, an in-memory reference loader restores it, and removing
  that in-memory patch fails again—all with source hashes unchanged.
- In clean GitHub Actions, the same sequence restores the minimal Fast Lane
  graph/context output, and patching only the loader in memory on unmodified
  lexical restores 5,519 edges and the exact control `ReactExtension.tsx`
  Optimal selection.
- A tested reference solution parses the JSONC subset, preserves strings and
  error positions, and returns a structured warning instead of silently
  treating a malformed existing config as an absent alias table. It agrees
  with TypeScript 5.9.3 on 514 curated/generated valid documents.
- In full Fast Lane pipeline checks, the builder-level reference integration
  leaves a valid JSONC graph warning-free but exports exactly one structured
  `tsconfig_parse_failed` warning for a malformed existing config, while the
  stock pipeline exports none.
- A separate disposable-runner rehearsal applies those exact changes at file
  level to both installed engine copies, validates both patched resolvers and
  the full Fast Lane graph with **no monkeypatching**, passes the raw post-fix
  regression, and then restores the stock file hashes.
- A digest-verified scan of all 106 PyPI wheels for 0.3.0–0.3.15 found the
  same vulnerable loader AST in all 212 engine copies; ordinary installs also
  reproduce the exact symptom across CPython 3.11–3.14 on Ubuntu and Python
  3.12 on Windows/macOS in CI.
- A bounded, explicitly non-random GitHub code-search sample found 35 unique
  affected root-config contents (174 declared path entries) among 139
  eligible unique contents; this is exposure evidence, not a prevalence
  estimate. Executing both installed loaders on every eligible sampled blob
  confirms the behavior directly: all 44 repository-level affected configs
  return `{}` stock and the exact expected table with the reference loader,
  while all 140 strict-JSON controls are exact under both.
- Normal pinned installs in GitHub Actions reproduce the minimal fixture,
  reference loader, patched-install rehearsal, full lexical counts, the
  independent ng-matero counts, and both selection/answerability impacts.
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
the exact four empty-alias JSONC cases, runs the reference-solution corpus and
integration check, runs the reversible causal intervention and targeted
boundary checks on both resolver copies, and checks the committed
lexical/ng-matero, reference-solution, version-scope, and exposure-sample
evidence counts.
The original scripts remain directly runnable:

```bash
python reproduction/repro_unit.py
python reproduction/repro_unit.py --expect-fixed  # post-fix regression; fails on 0.3.15
python reproduction/correction_poc.py
python solution/validate_reference_solution.py
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
- `solution/README.md` — reference parser/loader design, alternatives,
  maintainer integration points, and differential validation.
- `evidence/tsconfig-jsonc/SCOPE_AND_EXPOSURE.md` — all-wheel release scope
  and the bounded public-config exposure sample.
- `DUPLICATE_CHECK.md` — mechanism-level comparison with upstream issues.
- `evidence/tsconfig-jsonc/CONTEXT_SELECTION_IMPACT.md` — exhaustive downstream
  impact and the representative `ReactExtension.tsx` case.
- `evidence/tsconfig-jsonc/ANSWERABILITY_AUDIT.md` — six lexical and three
  ng-matero concrete questions whose answer-bearing lines are checked in the
  actual exported Optimal ZIPs.
- `evidence/tsconfig-jsonc/SYMBOL_EVIDENCE_AUDIT.md` — exhaustive
  definition/export-line availability for 10,703 eligible lexical
  imported-symbol instances.
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
reproducers, reference-loader integration check, reversible causal
intervention, targeted boundary checks, TypeScript paths oracle, graph
capture, bundle selection comparison, representative-case extractor,
final-artifact answerability and symbol-evidence audits, TypeScript
compiler-API verifiers, generic corrected-Fast-Lane validation, and optional
PyPI/GitHub scope and public-config loader-behavior samplers.

`solution/` contains the dependency-free reference parser/loader, its unit
and generated tests, the TypeScript/`jsonc-parser` differential validator,
and a reversible file-level patcher/validator for disposable installed
environments. It is a maintainer-adaptable reference implementation and
rehearsal, not a shipped patch.

`evidence/tsconfig-jsonc/` contains compact machine-readable results: the
4,256-row lost-relationship list, direct selection-omission list, causal
intervention record, reference-solution validation, all-wheel version scope,
public-config exposure sample and direct installed-loader behavior audit,
aggregate summaries with input hashes,
TypeScript API resolutions, configs/diffs, CI index, artifact manifest, and
the independent ng-matero evidence.

Local large-repository runs in the restricted investigation sandbox used a
disclosed grammar shim because release-asset downloads are blocked there. That
workaround is documented for provenance, but both the lexical and ng-matero
conclusions have since been independently reproduced in GitHub Actions under
standard installations.
No claim depends on hosted or LLM output.
