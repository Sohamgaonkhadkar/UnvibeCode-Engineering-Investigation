# Reference solution: JSONC-aware root `tsconfig.json` alias loading

## Status

This directory contains a **tested reference implementation for maintainer
adaptation**. It is not a shipped UnvibeCode fix and this investigation does
not open a pull request to `FinanceFlash/unvibecode`.

- Implementation: [`tsconfig_jsonc.py`](tsconfig_jsonc.py)
- Unit/generated tests: [`test_tsconfig_jsonc.py`](test_tsconfig_jsonc.py)
- Differential validator: [`validate_reference_solution.py`](validate_reference_solution.py)
- Adversarial boundary/mutation probe: [`differential_probe.py`](differential_probe.py)
- Node oracle helper: [`typescript_oracle.mjs`](typescript_oracle.mjs)
- Committed validation results: [`reference_solution_validation.json`](../evidence/tsconfig-jsonc/reference_solution_validation.json) and [`differential_probe.json`](../evidence/tsconfig-jsonc/differential_probe.json)

The existing causal harness patches this exact loader into both installed
0.3.15 engine copies in memory. It does not alter installed package files.

## Contract

`load_tsconfig_aliases_result(workspace_root, read_text, to_posix_rel)` keeps
the supported scope deliberately narrow: the **root** `tsconfig.json`, its
`compilerOptions.baseUrl`, and its `compilerOptions.paths` table.

| Input state | Aliases | Warning |
|---|---:|---|
| No root `tsconfig.json` | `{}` | none |
| Empty or comment-only config | `{}` | none |
| Valid strict JSON or JSONC with aliases | extracted aliases | none |
| Existing config cannot be read (including invalid UTF-8, a non-regular path, or a broken symlink) | `{}` | `tsconfig_read_failed` |
| Existing config has syntax error | `{}` | `tsconfig_parse_failed`, with line/column/offset |
| Parsed config has an invalid alias-table shape | `{}` | `tsconfig_invalid_shape` |

This preserves the product's ability to continue with relative imports while
making degradation visible. The important change is not merely “parse more
syntax”; it is **never equate a malformed existing config with a legitimately
absent alias table**.

## Parser design

The reference is not a regex preprocessor and does not implement a second
JSON grammar:

1. Make one string-aware lexical pass over the original text.
   - A leading BOM becomes one space.
   - `//` and `/* ... */` comments **outside string literals** become spaces.
   - String contents, escapes, LF/CRLF/CR, and offsets are preserved.
   - U+2028/U+2029 outside strings become LF, matching TypeScript's line
     terminators.
2. Make a second string-aware pass that blanks only a comma whose next
   non-whitespace character is `}` or `]` **and** whose previous significant
   character can end a JSON value/member. Doing this after comment blanking
   handles `..., /* comment */}` without rewriting a leading/elision comma
   such as `[,]` or `{,}` into an empty container.
3. Delegate all remaining grammar decisions to Python's strict
   `json.loads`, with two narrow hooks: `parse_constant` rejects Python's
   non-JSON `NaN`/`Infinity` extensions, and `parse_int` prevents CPython's
   integer-digit guard from escaping as an unstructured `ValueError` (an
   integer far beyond the finite JavaScript-number range becomes signed
   infinity, as in JavaScript numeric overflow).
4. Validate the small portion of the parsed shape used for aliases.
5. Apply the shipped alias-prefix mapping unchanged, including
   `replace("/*", "").rstrip("/")`.

Because every replacement is position-preserving, the standard-library
parser's line/column/offset still refer to the user's original file.

Product integration should read this one file with `read_tsconfig_text` (or an
equivalent strict UTF-8 reader), not with the engines' lossy
`safe_read_text(..., errors="ignore")`. The shipped helper is reasonable for
best-effort source scanning, but silently deleting invalid bytes from a
config file would recreate the same “existing input looks absent” failure at
the decoding layer. Strict decoding makes that state a visible
`tsconfig_read_failed` warning instead.

### Explicit grammar boundaries

Accepted beyond strict JSON:

- line and block comments;
- trailing commas in objects/arrays;
- one leading BOM;
- empty/comment-only files as `{}` (verified against TypeScript 5.9.3);
- CR, CRLF, U+2028, and U+2029 line-comment terminators.

Rejected with a diagnostic/warning:

- malformed JSON/JSONC;
- unquoted keys and single-quoted strings;
- leading/elision commas such as `[,]`, `{,}`, and nested variants;
- Python's non-JSON `NaN`, `Infinity`, and `-Infinity` constants;
- other JSON5-only forms;
- falsy non-list `paths` targets (`""`, `None`, `0`, `False`) rather than
  treating them as an empty target list;
- root/options/paths/baseUrl/target values with the wrong shape.

TypeScript's expression-based config parser also accepts JavaScript numeric
spellings such as `.5`, `5.`, `0x10`, `0b101`, `0o17`, and `1_000`; broader
JavaScript string forms such as `\x41` and a backslash line continuation; and
additional Unicode trivia outside strings. Microsoft's `jsonc-parser` (with
its errors inspected) and this reference reject those forms. The reference
follows the JSONC subset rather than silently adopting JSON5 or cloning
TypeScript's full expression grammar; the adversarial differential evidence
records each oracle disagreement instead of hiding it. It does not affect
the reported comment/trailing-comma defect or string-valued `paths`, but it
should not be described as byte-for-byte equivalence to every input
TypeScript's parser accepts.

Nested configs, `extends`, project references, Vite aliases, and full
TypeScript `paths` pattern semantics are separate behaviour and are not
changed here.

## Why this design over the obvious shortcuts?

| Approach | Assessment |
|---|---|
| Regex comment/comma stripping | Rejected: can corrupt URLs, `"@/*"`, `"//cdn..."`, and escaped strings. |
| Python JSON5 | Rejected as the loader grammar: accepts unquoted keys/single quotes and `NaN`/`Infinity` forms that TypeScript diagnoses, and rejects empty/comment-only configs in the tested corpus. |
| Python `json-with-comments` 1.3.0 | Viable dependency candidate only behind a stricter wrapper: in this corpus it failed BOM, U+2028/U+2029, and empty/comment-only valid cases and accepted the leading-comma and Python-constant invalid cases. It also does not provide the position-preserving transform used here. |
| Shell out to TypeScript/Node | Highest parser fidelity, but adds a runtime/process boundary to a Python package for one root-config read. Appropriate only if maintainers want full TypeScript expression-grammar fidelity. |
| Lexical JSONC-to-JSON transform + stdlib parser | Chosen reference: no new dependency, string-safe, auditable, preserves error positions, and limits grammar widening to comments/trailing commas. |

Other ecosystems have hit the same class of failure and fixed it by using a
real JSONC/TypeScript parser and inspecting diagnostics rather than silently
falling back—for example TSDX, Temporal's TypeScript SDK tooling, and AWS CDK.
Those precedents informed the design constraints; no code or issue text was
copied from them.

## Maintainer integration sketch

In each shipped engine copy (or, preferably, in the shared source from which
both are generated):

1. Add the parser/loader module or an equivalent maintained implementation
   behind the same result contract.
2. In `LanguageAwareImportResolver.__init__`, initialise
   `self.tsconfig_warning = None` before loading aliases.
3. Replace the body of `_load_tsconfig_aliases` with the result-returning
   loader, pass the strict `read_tsconfig_text` reader for this config file,
   and store `result.warning.as_dict()` when present.
4. Immediately after each graph builder constructs
   `LanguageAwareImportResolver`, append that warning once to the builder's
   existing `warnings: List[Dict[str, Any]]` so it appears in the graph's
   existing top-level `warnings` field.

Illustrative shape only:

```python
def _load_tsconfig_aliases(self):
    result = load_tsconfig_aliases_result(
        self.workspace_root,
        read_tsconfig_text,
        to_posix_rel,
    )
    self.tsconfig_warning = (
        result.warning.as_dict() if result.warning is not None else None
    )
    return result.aliases
```

```python
resolver = LanguageAwareImportResolver(self.workspace_root, rel_files)
if resolver.tsconfig_warning is not None:
    self.warnings.append(resolver.tsconfig_warning)
```

In UnvibeCode 0.3.15 those builder sites are the Fast Lane and merged-graph
builders that already initialise and export `warnings`; exact current line
numbers are documented in `../ROOT_CAUSE.md`.

### File-level patched-install rehearsal

`apply_reference_patch.py` turns the sketch into a reversible rehearsal for a
**disposable** installed environment. It refuses to run without an explicit
site-packages acknowledgement and a new backup directory; copies this exact
`tsconfig_jsonc.py` beside the installed engine sources; replaces the loader
method in both engine copies; inserts the one-line builder warning append;
records stock/patched SHA-256 values; and can restore the recorded stock
hashes and remove the installed reference module.

`validate_patched_install.py` then loads the patched package normally—with
no monkeypatching—and checks valid JSONC, strict JSON, relative/negative
specifiers, malformed warnings on both resolvers, an invalid-UTF-8 config
producing `tsconfig_read_failed` on both resolvers, and (with
`--full-pipeline`) the actual Fast Lane graph. CI additionally runs
`reproduction/verify.py --expect-fixed --skip-evidence` on that patched
installation before restoring stock. This is stronger integration evidence
than the in-memory harness, but it is still a rehearsal in a disposable
runner, not a shipped fix or an upstream PR.

## Validation performed

- 14 curated valid cases covering strict JSON, comments, trailing commas,
  comment-like strings, escaped backslash/quote boundaries, BOM, CR/CRLF,
  U+2028/U+2029, empty, and comment-only input.
- 500 deterministically generated valid JSONC documents (seed `20261103`)
  whose expected Python values are known before serialization.
- Differential comparison against TypeScript 5.9.3
  `parseConfigFileTextToJson`: 514/514 valid agreements.
- Differential comparison against Microsoft `jsonc-parser` 3.3.1 with
  `allowTrailingComma: true`: 510/514 valid agreements; the four exceptions
  are empty/comment-only and U+2028/U+2029, where the candidate follows
  TypeScript.
- 13 malformed/diagnosed cases rejected by the candidate and diagnosed by
  both Node oracles, including leading object/array commas and all three
  Python `NaN`/`Infinity` constants.
- Adversarial differential probe: 121 hand-enumerated grammar boundaries
  plus 2,156 unique seeded one/two-edit mutations (2,277 cases; 2,271 unique
  texts). All three parsers accept 865 cases with equal values and reject
  1,316. There are **0** candidate-only acceptances, **0** candidate-only
  rejections of cases both oracles accept, and **0** all-accept value
  mismatches. The remaining 96 cases are explicit TypeScript/`jsonc-parser`
  disagreements; four are non-object JSON roots, which the document parser
  returns and the alias-shape layer then rejects with a warning.
- Product integration through both installed engines in
  `../reproduction/causal_intervention.py`: A/C/E fail with the stock loader;
  B and D restore; malformed configs produce `{}` plus exactly one structured
  warning in D.
- Full Fast Lane integration in clean CI: with the builder-level warning
  wiring applied in memory, valid JSONC exports `warnings: []`; the same
  malformed config exports exactly one `tsconfig_parse_failed` warning with
  path/line/column/offset, while the stock pipeline exports no warning.
- File-level patched-install rehearsal in clean CI: both normally loaded
  patched engine copies resolve valid JSONC, report the malformed warning,
  and report `tsconfig_read_failed` for invalid UTF-8; the patched Fast Lane
  graph restores the configured edge, the raw post-fix regression passes, and
  restoration returns both engine files to their recorded stock SHA-256
  values.
- Direct public-config behavior: on all 184 eligible blobs in the bounded
  sample, both stock loaders return `{}` for the 44 affected configs and the
  exact expected aliases for the 140 strict controls; the reference loader is
  exact in both groups on both engines.
- Ordinary-install behaviour matrix in CI: CPython 3.11–3.14 on Ubuntu and
  CPython 3.12 on Windows/macOS all reproduce the stock symptom and pass the
  reference-loader checks.
- Local timing in the current committed validation: lexical root config
  (22,614 UTF-8 bytes), median about 3.66 ms/parse; synthetic 5,000-entry
  config (301,780 bytes), about 55.32 ms/parse. Timing is
  environment-specific; the transform is linear and runs once per resolver
  construction.

Default CI runs the Python corpus through `reproduction/verify.py` and also
installs TypeScript/`jsonc-parser` in a validation-only step to reproduce both
the valid/invalid differential result and the adversarial boundary/mutation
probe. The same comparison can be regenerated locally
with the commands in `validate_reference_solution.py`; neither oracle is a
proposed runtime dependency.

## External design references

- TypeScript discussion that tsconfig files grammatically allow comments and
  trailing commas: https://github.com/microsoft/TypeScript/issues/20384
- Microsoft JSONC parser: https://github.com/microsoft/node-jsonc-parser
- TSDX strict-parse/silent-catch precedent:
  https://github.com/jaredpalmer/tsdx/issues/483 and
  https://github.com/jaredpalmer/tsdx/pull/489
- Temporal TypeScript SDK JSONC replacement:
  https://github.com/temporalio/sdk-typescript/issues/2397 and
  https://github.com/temporalio/sdk-typescript/pull/2398
- AWS CDK JSONC parser/diagnostics change:
  https://github.com/aws/aws-cdk/pull/39276
- Python alternatives evaluated:
  https://pypi.org/project/json-with-comments/ and
  https://pypi.org/project/json5/
- Python `json` documentation for the non-standard default constants and the
  `parse_constant` hook: https://docs.python.org/3/library/json.html
