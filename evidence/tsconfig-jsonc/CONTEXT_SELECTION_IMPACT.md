# Downstream context-selection impact — lexical

## Question tested

Do the file relationships lost when lexical's JSONC `tsconfig.json` is discarded
actually change the code a developer/AI receives from the exported Connected Code
context, or do fallback links and the selector's budget/ranking hide the loss?

We compared the emitted `repository-context.zip` bundles from two runs on
`meta/lexical@164af6a4df7114f35724c472152ca74877b6bd04`:

- **as-is:** the repository's real root `tsconfig.json`, including five `//` lines;
- **control:** the identical tree with only those five comment lines removed.

`reproduction/compare_selections.py` compared all 2,044 common `selections.jsonl`
rows. A file was treated as selected only if it appeared in `included_files` or was
the file of a selected chunk after joining `chunk_id` to `chunks.jsonl`.

## Result: the selection impact is real, but not one-for-one

At graph level there are 4,256 lost import relationships, representing **4,218
distinct source→target file pairs**. Their direct-selection states are:

| Scope | Absent as-is, present in control | Present in both | Absent in both | Present only as-is |
|---|---:|---:|---:|---:|
| Narrow (radius 0) | 0 | 0 | 4,218 | 0 |
| Optimal (radius 1) | **2,707** | 434 | 1,062 | 15 |
| Wider (radius 2) | **3,345** | 472 | 398 | 3 |

Interpretation:

- In **Optimal**, 2,707 verified direct dependencies are absent from the as-is
  selection and restored by the control, covering 1,133 source files.
- In **Wider**, 3,345 are restored, covering 1,233 source files.
- Across either non-trivial scope, **3,364 distinct direct pairs / 1,235 source
  files** are affected.
- Fallbacks/other graph paths save some cases: 434 direct pairs are already present
  in both Optimal selections despite the missing Stage-1 file edge.
- Budget/ranking also matters: 1,062 direct pairs are absent from both Optimal
  selections. Those are not attributed to this defect.
- Overall, selections change for **1,494 of 2,044 files** in at least one scope.
  Control selections also displace some chunks under the token budget, especially
  at radius 2; therefore the direct verified-dependency count above—not the raw
  volume of changed chunks—is the conservative impact claim.
- Narrow is radius 0, so non-selected neighbours are expected there and are not
  presented as impact.

Restricting attention to package implementation sources (`packages/*/src`, excluding
tests/examples/playground), 446 distinct package-source→package-source direct pairs
are absent as-is and recovered in at least one of Optimal/Wider.

## Representative developer consequence

Source: `packages/lexical-react/src/ReactExtension.tsx`.

TypeScript 5.9.3's compiler API resolves all six configured alias imports from
that file to the claimed internal files. In the as-is **Optimal** selection, only
four files are included: the source, `LexicalErrorBoundary.tsx`,
`shared/buildEditorComponent.tsx`, and `shared/types.ts` (estimated 7,325 tokens).

The following direct dependencies are absent as-is and present in the control:

- `packages/lexical-react/src/LexicalComposerContext.ts`
- `packages/lexical-react/src/LexicalContentEditable.tsx`
- `packages/lexical-react/src/ReactProviderExtension.tsx`
- `packages/lexical-internal/src/invariant.ts`
- `packages/lexical/src/index.ts`

The control Optimal selection contains 28 files / an estimated 37,769 tokens,
including chunks from each file above and the core implementations of
`defineExtension` and `shallowMergeConfig`.

This is not an abstract graph difference. `ReactExtension.tsx` puts
`<ContentEditable />` into its default config and constructs the
`LexicalComposerContextWithEditor` tuple passed through the React integration.
For a task such as changing the extension's default editable surface, placeholder
behaviour, provider checks, or composer-context/theme handling, the as-is
Optimal export withholds the implementations that define those behaviours.

The important measurement is restoration of these verified relevant
dependencies, not the raw increase from 7,325 to 37,769 estimated tokens;
larger context is not automatically better context. This comparison establishes
what code is present in the exported selections. It does not test or claim a
particular improvement in downstream LLM answer quality.

Machine-readable case record: `selection_case_react_extension.json`.
Compiler-API resolutions: `typescript_api_lexical_case.json`.

A separate final-artifact audit turns that representative case into six
predeclared maintenance questions (placeholder accessibility/rendering,
composer-context tuple/theme fallback, provider-peer identity, `invariant`
failure behaviour, `defineExtension` identity behaviour, and
`shallowMergeConfig` object-identity/copy behaviour). It requires exact
answer-bearing fragments in selected Optimal chunks from the answering files,
so imports in `ReactExtension.tsx` cannot pass the tasks. In clean CI the
result is **0/6 as-is, 6/6 in the comment-stripped control, and 6/6 with the
original config plus the reference loader**; an `LexicalErrorBoundary`
negative control is 1/1 in every bundle. This is an evidence-availability
measurement, not an LLM-output claim. See `ANSWERABILITY_AUDIT.md`.

An exhaustive companion derives 10,703 eligible source-specific
imported-symbol tasks from all 4,256 verified lexical relationships. A task
requires a recognizable declaration/export line in selected chunks from the
symbol's defining file. At Optimal, 726 are available as-is versus 8,826 in
both control and corrected bundles (**8,163 recovered**); at Wider, 711
versus 9,883 (**9,182 recovered**). These are repeated source-specific
instances across 1,239 importing files, not unique symbols or model answers.
See `SYMBOL_EVIDENCE_AUDIT.md`.

A later diagnostic control repeated the lexical Fast Lane run with the
original JSONC config bytes unchanged and only `_load_tsconfig_aliases`
patched in memory. It restored 5,519 file edges and produced exactly the same
`ReactExtension.tsx` Optimal included files/chunk IDs/estimated tokens as the
comment-stripped control; a full corrected-vs-stock bundle comparison again
found 2,707 Optimal and 3,345 Wider direct-dependency recoveries. This is
Fast Lane graph/context evidence, not a claim about later hosted stages. The
workflow record is indexed in `CI_VERIFICATION.md`.

## Independent confirmation on ng-matero

On pinned `ng-matero/ng-matero@d351bf5957d8c6dc9eca79d0c9b260c5b8d07822`,
removing only two leading block-comment lines restores 111 verified direct file
relationships. Of 111 distinct direct pairs, 107 are absent from both Optimal and
Wider as-is selections and restored in the control; the other four are present in
both. See `ng-matero/selection_impact_summary.json`. A dedicated
ordinary-install clean-environment workflow now reproduces those counts and
the corrected result, and its three predeclared `app.config.ts` final-artifact
tasks are **0/3 as-is versus 3/3 in both control and corrected bundles**.

## Provenance

- Lexical graph SHA-256, as-is: `8ee970fe9686e6c7975fee3c5fc72bd8a4d4d087cd08de6f1a92d40ee90c903b`
- Lexical graph SHA-256, control: `9e5d2d246ea731b24367bccc7ecd4f40f2b56aaa02ccb36870325517dfe3ebff`
- Lexical context ZIP SHA-256, as-is: `0034d20ad51f357d053c0c7df399ffbeda3a94bac11366c72066ca8d8895d0cc`
- Lexical context ZIP SHA-256, control: `7846035172d91b82a13d75c96b9c3d86959256635b08bb08512f302115215815`
- Full lost-relationship list: `lost_relationships.jsonl`
- Full direct selection-omission list: `direct_selection_omissions.jsonl`
- Aggregate outputs: `alias_oracle_summary.json`, `selection_impact_summary.json`
- Independent compiler cross-check of all 4,256 rows: `typescript_api_verification.json` (0 mismatches)
