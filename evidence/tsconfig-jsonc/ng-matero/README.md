# Independent second repository — ng-matero

## Why this repository qualifies

- Public and independent of lexical: `ng-matero/ng-matero`
- Pinned commit: `d351bf5957d8c6dc9eca79d0c9b260c5b8d07822`
- Its root `tsconfig.json` begins with two block comments, so it is legal JSONC
  but not strict JSON.
- The same root config declares eight `compilerOptions.paths` patterns:
  `@core`, `@core/*`, `@shared`, `@shared/*`, `@theme`, `@theme/*`, `@env`, and
  `@env/*`.
- The project makes real imports through those aliases, and `tsconfig.app.json`
  extends the root configuration.

The local control is the identical pinned tree with only the two leading
block-comment lines removed. The preserved pair and diff are
`tsconfig_as_is.json`, `tsconfig_control.json`, and `tsconfig_diff.txt`.

## Independent expectation

TypeScript 5.9.3's compiler API parses the commented config without error and
resolves representative imports from `src/app/app.config.ts`:

- `@core` → `src/app/core/index.ts`
- `@env/environment` → `src/environments/environment.ts`
- `@shared` → `src/app/shared/index.ts`
- `@shared/in-mem/in-mem-data.service` → `src/app/shared/in-mem/in-mem-data.service.ts`

Representative output: `typescript_api_case.json`. In addition, the batch
compiler check in `typescript_api_verification.json` resolved all 111 lost
relationship rows to the same targets, with zero mismatches.

## Observed graph effect

Both runs scan the same 300 files and extract the same 1,192 import records.

| Run | Internal file edges | Unresolved/external |
|---|---:|---:|
| Root tsconfig as-is (JSONC comments) | 130 | 1,062 |
| Two comment lines removed | 241 | 951 |

The 111 relationships gained in the control—and no others—were then checked
with the strict TypeScript-`paths` oracle. All 111 point to the file identified
by the configured exact/wildcard mapping (90 exact-pattern and 21 wildcard
records). All 111 are listed in `lost_relationships.jsonl`.

## Observed context-selection effect

The bundles contain 299 common selected files; 147 have at least one altered
scope. Across the 111 distinct verified direct pairs:

- **Optimal:** 107 absent as-is and restored in the control; 4 present in both.
- **Wider:** 107 absent as-is and restored in the control; 4 present in both.
- **Narrow:** direct neighbours are absent in both, as expected at radius 0.

This demonstrates the same parse→alias-table→graph→selection chain in a
different codebase with ordinary directory wildcard aliases rather than
lexical's predominantly exact package mappings.

## Final-artifact answerability

For representative source `src/app/app.config.ts`, three predeclared tasks
require the exact `@core` barrel areas, `@shared` barrel categories, and
environment values in selected Optimal chunks from their answering files.
The ordinary-install result is **0/3 as-is, 3/3 in the control, and 3/3 with
the original config plus the reference loader**; a source-file negative
control passes in all three. Definitions are in
`../../../reproduction/answerability_tasks_ng_matero.json`, with the combined
record in `../ANSWERABILITY_AUDIT.md`.

## Environment note

The originally captured local ng-matero CLI runs used the disclosed grammar
fallback required by the sandbox. That caveat has now been closed for the
reported graph, selection, corrected-output, TypeScript-batch, and
answerability results: the dedicated ordinary-install GitHub Actions
workflow reproduces the same counts without the sandbox fallback. See
`../CI_VERIFICATION.md`.
