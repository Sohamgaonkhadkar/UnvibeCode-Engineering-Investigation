# Root cause — a valid JSONC `tsconfig.json` silently empties the path-alias table

## One-sentence mechanism

`LanguageAwareImportResolver._load_tsconfig_aliases` reads the repository-root
`tsconfig.json` with strict `json.loads` and catches every exception with a bare
`pass`; because TypeScript config files are JSONC, one legal comment or trailing
comma aborts the parse, leaves `tsconfig_aliases = {}`, and makes otherwise
supported path-alias imports unresolvable without any warning.

## Stage-by-stage decomposition

| Stage | Expected behaviour | Observed behaviour | Responsibility |
|---|---|---|---|
| TypeScript config input | Comments and trailing commas are accepted; `compilerOptions.paths` remains available | TypeScript 5.9.3 accepts every fixture and both real configs; compiler API returns their paths targets | External semantic oracle |
| Config read | Root `tsconfig.json` is located and read | File is found; removing only comments changes behaviour, proving the intended file is being read | `_load_tsconfig_aliases` |
| Config parse | JSONC syntax should either be parsed or produce a diagnostic | Strict `json.loads` throws on the first JSONC feature; `except Exception: pass` suppresses it | **Earliest failure** |
| Alias-table construction | Configured mappings populate the resolver | Function returns `{}`; the mapping-transform loop is never reached | Direct consequence of the parse failure |
| Import extraction | Imports and line numbers should be extracted | Lexical extracted the identical 9,562 file/specifier/line records in both runs | Working correctly |
| Node/TS module resolution | Configured aliases should produce candidate files | `_resolve_node_ts` receives no custom alias prefixes, so candidates are empty and imports are `external_or_unresolved` | Propagated failure, not an extractor failure |
| Graph construction | Internal alias imports should become `file_import` relationships | 4,256 verified lexical relationships and 111 ng-matero relationships are absent | Primary product effect |
| Symbol linking/context selection | Connected implementations should be eligible for selections | Some are rescued by fallbacks, but thousands of verified direct dependencies are absent from exported Optimal/Wider selections | Demonstrated downstream effect |

The shipped code is:

`shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py:1913-1931`

```python
try:
    data = json.loads(safe_read_text(tsconfig))   # strict JSON only
    ...
except Exception:
    pass                                            # aliases stay {}
return aliases
```

The same implementation is duplicated at
`01_shipreadyv2_merged_graph_pipeline_5chunks.py:1870-1887`. Both installed
files were verified against the hashes in the 0.3.15 wheel's `RECORD`.

This is not only a latest-release accident. A digest-verified scan of every
PyPI wheel published for 0.3.0–0.3.15 (106 wheels, 212 engine copies) found
exactly one `_load_tsconfig_aliases` AST. Executing that extracted function
returns the expected alias for strict JSON and `{}` for the semantically
identical JSONC control. Ordinary-install CI additionally reproduces the
exact resolver symptom and reference-loader behaviour on CPython 3.11–3.14
(Ubuntu) and CPython 3.12 on Windows/macOS. See
`evidence/tsconfig-jsonc/SCOPE_AND_EXPOSURE.md`.

## Causal controls

- Two-file strict-JSON and JSONC fixtures differ only in config lexical syntax.
  Strict JSON yields `{'@app': 'src/app'}` and `@app/util -> src/app/util.ts`;
  line-comment, block-comment, trailing-comma, and combined JSONC fixtures yield
  `{}` and `(None, None)`.
- A negative-control fixture with no alias declared remains unresolved, while
  its relative import still resolves. The empty table alone is not being treated
  as a bug.
- On lexical, deleting only five comment lines raises Stage-1 internal file
  edges from 1,263 to 5,519. On ng-matero, deleting only two leading block
  comments raises them from 130 to 241.
- Replacing only the parse step in memory—while retaining the shipped resolver
  and its downstream alias use—restores the expected result on every fixture.
- The sequence is explicitly reversible on both engine copies: original JSONC
  fails, comments-only removal restores it, restoring the exact config fails
  again, the in-memory reference loader restores it, and restoring the stock
  method fails again. Source hashes do not change; missing/unconfigured and
  external specifiers remain unresolved throughout.
- In clean CI, that same A–E sequence restores the minimal Fast Lane graph and
  context bundle in B/D. On unmodified lexical, the in-memory loader alone
  restores 5,519 edges and the control's `ReactExtension.tsx` Optimal
  selection exactly.
- The full lexical result was reproduced in a normal GitHub Actions install, so
  it does not depend on this investigation sandbox's temporary grammar shim.

## Strict recount of the lexical delta

The previous graph comparison classified specifiers by the textual prefixes
`lexical`/`@lexical/`. That was not a sufficient oracle: among all 1,543 distinct
extracted lexical specifiers, two (`@lexical/eslint-plugin-internal` and
`lexicalOriginal`) share those prefixes but match no configured `paths` pattern.

`reproduction/analyze_alias_oracle.py` therefore parses lexical's actual config
(220 patterns: 184 exact and 36 wildcard), applies exact-before-wildcard and
longest-wildcard-prefix matching, performs TypeScript-style file probing, and
compares the resulting file with each control-only graph edge.

Result:

- scanned files identical: 2,044 = 2,044;
- extracted import records identical: 9,562 = 9,562;
- control-only file relationships: **4,256**;
- all **4,256** targets match the configured `paths` oracle;
- as-is-only file relationships: **0**;
- the count corresponds to **4,218 distinct source→target file pairs**.

Thus the 4,256 headline survives the stricter recount unchanged. As a further
cross-check, `reproduction/tsc_verify_relationships.mjs` submitted every one of
the 4,218 unique source/specifier pairs to TypeScript 5.9.3's own
`resolveModuleName`; all 4,256 rows again matched the graph target, with zero
mismatches (`typescript_api_verification.json`). Symbol edges are reported
separately because a symbol edge normally targets the defining file, not
necessarily the module-entry file returned by `paths`.

## Downstream effect

Missing file edges were not assumed to imply missing context. Comparing the
actual exported bundles shows 2,707 verified direct dependencies absent from
lexical **Optimal** selections as-is and restored in the control; 3,345 in
**Wider**. At the same time, 434 Optimal pairs are present in both through other
links/fallbacks and 1,062 are absent in both due to selection limits. The
conservative conclusion is therefore not “4,256 missing edges means 4,256 missing
context files,” but that the parse failure demonstrably removes thousands of
direct implementations from customer context selections. A final-artifact
audit adds a concrete task-level check: for six predeclared questions about
`ReactExtension.tsx`, none has all required answer-bearing lines in the as-is
Optimal ZIP, while all six do in both the control and reference-corrected
bundles; a negative control passes throughout. See
`evidence/tsconfig-jsonc/CONTEXT_SELECTION_IMPACT.md` and
`evidence/tsconfig-jsonc/ANSWERABILITY_AUDIT.md`.

## Boundary and non-claims

- Relative imports and the resolver's hardcoded `@/`, `~/`, and `src/` branches
  are unaffected by this loader failure.
- This report is about the supported repository-root `tsconfig.json` loader. It
  does not ask the single fix to add nested-config discovery, `extends` support,
  Vite aliases, or all TypeScript `paths` pattern semantics.
- Separate limitations in how already-loaded alias patterns are transformed or
  probed can still leave some imports unresolved. Those were observed (for
  example in zustand) and are deliberately outside this one-defect claim.
- No claim is made about hosted business-workflow/risk findings. All established
  consequences are in the local graph and exported context bundle.

## Reference-solution status

`solution/tsconfig_jsonc.py` is a dependency-free reference implementation
for maintainer adaptation, not a shipped patch. It performs two
position-preserving, string-aware lexical passes—blank comments outside
strings, then blank only commas immediately before `}`/`]`—and delegates the
remaining grammar to strict `json.loads`. That ordering handles
`..., /* comment */}`, preserves comment-like string contents byte-for-byte,
and preserves useful error line/column/offset values.

The product-style loader distinguishes three states that the current code
conflates:

- missing or empty/comment-only config: `{}`, no warning;
- valid JSONC: extracted aliases, no warning;
- existing unreadable/malformed/invalid-shape config: `{}`, plus one
  structured warning.

For 0.3.15 integration, both graph builders already have a structured
`warnings: List[Dict[str, Any]]` that is exported in the graph:

- Fast Lane (`00a...`): initialise line 2186, construct resolver line 2195,
  export line 2350;
- merged graph (`01...`): initialise line 2143, construct resolver line 2152,
  export line 2307.

The reference loader's `tsconfig_warning.as_dict()` can therefore be appended
once immediately after resolver construction without inventing a new output
channel. The full Fast Lane harness now exercises that builder-level
integration in memory: valid JSONC produces an exported graph with
`warnings: []`, a malformed existing config produces exactly one
`tsconfig_parse_failed` record in the exported graph, and the stock pipeline
produces no warning for the same malformed input. It was validated against
514 curated/generated valid documents with TypeScript 5.9.3 and Microsoft
`jsonc-parser` 3.3.1 as differential oracles; see `solution/README.md`. The
raw post-fix regression
(`repro_unit.py --expect-fixed`) remains the acceptance test for an actual
shipped fix.
