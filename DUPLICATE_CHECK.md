# Duplicate check — latest sweep 2026-11-05 against all 434 issues (open + closed, to #532)

## Current result — read this first

The **current** conclusion is the 2026-11-05 sweep of **434 open/closed
issues through #532**, detailed under “Latest re-check” below. It confirms and
supersedes the 2026-11-04 through-#473 result: **#451 remains the only
upstream report of this strict-JSON tsconfig mechanism** — legal
comments/trailing commas make `_load_tsconfig_aliases` return no path
mappings. Filing `submission/GITHUB_ISSUE.md` unchanged as a new upstream
issue would therefore duplicate #451. The 58 issues added since the previous
sweep (#474–#532) contain no second report of this mechanism.

This investigation was already public in the personal evidence repository
before #451 was filed: evidence PR #1 was created on 2026-11-01 and merged on
2026-11-02, and this strengthening PR #2 was created on 2026-11-02. That
chronology supports independent discovery; it does **not** change the tracker
fact that #451 is now the first upstream report of this mechanism. No
competitor finding, example, wording, code, or measurement from #451 has been
reused here.

The adjacent TypeScript-config reports are mechanism-distinct: #452 is
ordinary `baseUrl` resolution without `paths` in a strict-JSON config, and
#455 is failure to follow `extends`/effective config in strict-JSON configs.
#442 remains post-load target-wildcard substitution. New in the 2026-11-05
range, #501 is unnormalized relative `../` candidate paths in
`LanguageAwareImportResolver` and mentions `tsconfig` only to cross-reference
#455; it parses no config and discards no alias table.

The older sections in this file are retained as a chronological audit trail.
Their issue totals and “newest issue” statements were correct when those
searches were run but are **superseded by the current result above** and should
not be quoted as the present tracker state. The mechanism-comparison table
immediately below remains the current nearest-neighbour analysis.

## Historical searches and mechanism comparison
Historical title sweeps for: `tsconfig` (**0 title hits at that stage**; later
body-level API searches return #153/#272/#374), `jsonc` (**0**), `comment`
(0 relevant), `alias` (8, reviewed), `require`/CommonJS, `../`, plus full
re-listing immediately before drafting (no new issues after #417 at that
historical point). Closest issues read in full:

| Issue | What it claims | Why ours is a different underlying cause |
|---|---|---|
| **#374** — `@/` aliases skipped as `hard_path_skipped` although defined in **vite.config.ts** | Linker hard-skips `@/` when the alias lives only in Vite config and the app tsconfig sits in a subdirectory (`frontend/`). | Our alias **is** in the root `tsconfig.json` that the engine already supports; it fails earlier, in `_load_tsconfig_aliases` parsing (strict `json.loads` on JSONC), and is recorded `external_or_unresolved`, not `hard_path_skipped`. Different stage, different function, different trigger, different fix. |
| **#272 / #153** — TypeScript `@/` path aliases skipped | Older behavior for the hardcoded `@/` prefix. | 0.3.15 already resolves `@/` via a hardcoded `src/` branch and custom aliases via tsconfig *when the file is strict JSON* (proven by our strict-JSON control). Our defect disables the custom-alias table itself. |
| **#442** — target wildcards drop core Vue implementations | A loaded mapping such as `@vue/* -> packages/*/src` has its target `*` stripped instead of substituting the captured package name. | Different later mechanism: pattern substitution after config parsing. Our config never loads at all when it contains JSONC comments/trailing commas. Our reference solution deliberately preserves shipped pattern-mapping semantics, so it neither claims nor changes #442's separate defect. |
| **#451** — valid comments discard every configured path mapping | A root JSONC `tsconfig.json` is parsed with strict `json.loads`; the parse error is swallowed and both engines load zero aliases. | **Same mechanism as this investigation.** It is now an upstream duplicate for filing purposes. This repository remains independent corroborating evidence with different pinned repositories, causal controls, scope audits, and a tested reference loader; it should not be filed unchanged as a second report. |
| **#452** — `baseUrl` imports lose local module targets | A strict-JSON root config with `baseUrl` but no `paths` parses, yet ordinary non-relative imports are not resolved relative to `baseUrl`. | Different mechanism. Our trigger is JSONC lexical syntax preventing the whole config/`paths` table from loading. The reference here deliberately retains the shipped alias-mapping/`baseUrl` use inside `paths` and does not claim ordinary `baseUrl`-only resolution. |
| **#455** — aliases inherited through `extends` are never loaded | Strict-JSON configs parse, but the loader does not follow `extends` or discover the effective/non-root config that declares `paths`. | Different mechanism. Our supported root config declares the aliases directly and fails earlier at JSONC parsing. The reference here deliberately does not add `extends`, nested-config discovery, or effective-config merging. |
| **#320** — `_js_import_symbols` collects local aliases from aliased/namespace imports | Symbol-name extraction from import clauses. | Unrelated: our imports extract correctly (they appear in unresolved records); failure is alias-table loading. |
| **#262 / #84** — `../` imports unresolved (`to_posix_rel` never normalizes `..`) | Path normalization in relative resolution. | We reproduced this too (all web/Node resolvers) and deliberately do **not** file it — same cause as #262. Mentioned here to show the check was mechanism-level, not title-level. |
| **#372** — PHP `require/include` never extracted | Missing extractor branch in `_extract_php`. | Different language/stage (extraction vs config parsing). |
| **#378 / #323** — grammar-download / tokenizer failures still ending in “complete”/partial states | Environment failure handling. | Our runs needed a grammar shim in-sandbox (documented in the log); the selected defect is grammar-independent and reproduces at unit level with no parser involved. |

## Final audit re-check — 2026-11-02 (GitHub issue search API, `repo:FinanceFlash/unvibecode is:issue`)

| Search term | Hits | Relevant |
|---|---|---|
| `tsconfig` | 3 | #153, #272, #374 only |
| `jsonc` | **0** | — |
| `trailing comma` | **0** | — |
| `_load_tsconfig_aliases` | **0** | — |
| `path alias` | 22 | above + #320/#305/#297 (unrelated alias senses) |
| `external_or_unresolved` | 8 | #84/#103 (`../` normalization), #134, #284, #308, #386 — none about config parsing |
| `json.loads` | 22 | none about tsconfig loading |
| `comment` | 27 | none about tsconfig comments |

Body-level re-reads this round: **#153** (0.3.3, `fsousac/Dragg`): `@/*` imports recorded `resolution_status: hard_path_skipped`, `detail: alias_prefix_@/` — a Stage-2 *linker* hard-skip of alias-prefixed specifiers. **#272** (0.3.15): same `hard_path_skipped` family (262 records). **#374**: same family, alias defined only in `vite.config.ts`. **#320**: `_js_import_symbols` mis-extracts local binding names — extraction stage. **Our defect differs on every axis**: Stage-1 resolver (`_load_tsconfig_aliases`), trigger = lexical JSONC syntax in a config the engine already supports, observed status `external_or_unresolved` with the alias table empty, fix = tolerant JSONC parsing. No new issues beyond #417 as of this check (322 total). URLs: https://github.com/FinanceFlash/unvibecode/issues/153 · /272 · /320 · /374 (same pattern).

## Strengthening-round re-check — 2026-11-02

The upstream tracker still contains **322 issues, newest #417**. Fresh
GitHub issue-search API results:

| Search term | Hits | Assessment |
|---|---:|---|
| `jsonc` | 0 | No report of the config format itself |
| `trailing comma` | 0 | No report of this trigger |
| `_load_tsconfig_aliases` | 0 | No report names the responsible function |
| `comment tsconfig` | 0 | No report connects comments to tsconfig loading |
| `tsconfig` | 3 | #153, #272, #374 only |
| `compilerOptions.paths` | 3 | #153, #272, #374 only |
| `path aliases` | 15 | The three above; remaining hits use “alias” for symbols/import bindings or unrelated subsystems |

The closest three remain the Stage-2 `hard_path_skipped` family for `@/`.
Our failure occurs before that stage: the root config's whole alias table is
empty because strict JSON parsing fails on legal JSONC. The new clean-CI and
selection experiments use the same mechanism and do not introduce a second
defect.

## Final-QC re-check — 2026-11-02

The tracker has advanced to **325 issues, newest #420**. A fresh
GitHub issue-search API sweep (`repo:FinanceFlash/unvibecode is:issue`,
open + closed) returned:

| Search term | Hits | Assessment |
|---|---:|---|
| `jsonc` | 0 | No report of the config format itself |
| `trailing comma` | 0 | No report of this trigger |
| `_load_tsconfig_aliases` | 0 | No report names the responsible function |
| `comment tsconfig` / `comments tsconfig` | 0 | No report connects comments to tsconfig loading |
| `tsconfig` | 3 | #153, #272, #374 only |
| `compilerOptions.paths` | 3 | #153, #272, #374 only |
| `tsconfig aliases` | 2 | #153, #272 only |
| `json.loads tsconfig` | 2 | #272, #374 only |

The three newest issues are unrelated mechanisms: #418 concerns Python
`from . import <symbol>` resolution, #419 is a responsive-layout report, and
#420 concerns PHP trait/inheritance extraction. The nearest TypeScript
neighbours remain #153/#272/#374 and are distinguished by stage, status, and
remediation above.

## Pre-publication re-check — 2026-11-02

Immediately before submission finalization, the tracker had advanced to **330
issues, newest #426**. The exact-mechanism results were unchanged: `jsonc`,
`trailing comma`, `_load_tsconfig_aliases`, `comment tsconfig`, and `comments
tsconfig` each returned 0; `tsconfig` and `compilerOptions.paths` still returned
only #153/#272/#374. Issues #421–#423, #425, and #426 concern unrelated Flask
linking, CLI interruption, workflow grouping, Python imports, and Business Risk
selection mechanisms (#424 is a pull request).

## Causal-strengthening re-check — 2026-11-02

Before finalizing the reversible-intervention strengthening, the tracker had
advanced to **333 issues, newest #429**. The exact-mechanism results remained
unchanged: `jsonc`, `trailing comma`, `_load_tsconfig_aliases`, `comment
tsconfig`, and `comments tsconfig` each returned 0; `tsconfig` and
`compilerOptions.paths` still returned only #153/#272/#374. Issue #427 concerns
duplicate Pass 1 activation facts, an unrelated hosted-analysis validation
mechanism. Issue #428 concerns an exported local symbol binding
(`Select = SelectPrimitive.Root`) not found while its module and sibling
exports resolve; that is a symbol-export mechanism, not root-tsconfig parsing
or Stage-1 alias-table loading. Issue #429 concerns Python `src/`/`lib/`
layout package re-exports and `module_scope_mismatch`, also unrelated.

## Reference-solution re-check — 2026-11-03

The tracker had advanced to **346 issues, newest #442**. Fresh GitHub
issue-search API results (`repo:FinanceFlash/unvibecode is:issue`, open +
closed) were:

| Search term | Hits | Assessment |
|---|---:|---|
| `jsonc` / `"JSONC"` | 0 | No report of the config format or parse mechanism |
| `"trailing comma"` | 0 | No report of this trigger |
| `_load_tsconfig_aliases` | 1 | #442 only; read in full |
| `tsconfig` | 4 | #153, #272, #374, #442 |
| `"compilerOptions.paths"` | 3 | #153, #272, #374 |
| `comment tsconfig` | 1 | #442 as a broad text match; its mechanism is not comment parsing |
| `alias tsconfig` | 4 | #153, #272, #374, #442 |

Issue #442 is the closest new neighbour because it also involves TypeScript
path mappings. Its stated cause is that `_load_tsconfig_aliases` strips the
wildcard from a target such as `packages/*/src`, after which
`_resolve_node_ts` appends the captured segment at the wrong position. That
is a **post-load pattern-substitution** error. Our trigger and failure state
are earlier and distinguishable: strict `json.loads` rejects a supported
root JSONC config, the broad exception handler leaves the entire alias table
`{}`, and comments-only removal restores it without changing any wildcard
semantics. Fixing #442 would not make a JSONC config load; fixing this issue
would not implement #442's requested wildcard substitution.

## Strengthening re-check — 2026-11-03 through #444 (superseded)

The tracker subsequently advanced to **348 issues, newest #444**. The exact
searches were repeated through the GitHub issue-search API:

| Search term | Hits | Assessment |
|---|---:|---|
| `jsonc` / `"JSONC"` | 0 | No report of the config format or parse mechanism |
| `"trailing comma"` | 0 | No report of this trigger |
| `_load_tsconfig_aliases` | 1 | #442 only |
| `tsconfig` / `alias tsconfig` | 4 | #153, #272, #374, #442 |
| `"compilerOptions.paths"` | 3 | #153, #272, #374 |
| `comment tsconfig` | 1 | #442 broad text match |
| `json.loads tsconfig` | 2 | #272, #374 |

Issue #443 is a results-dashboard/ZIP-label report. Issue #444 was read at
body level: it reports a Python FastAPI `route_handler` kind being overwritten
during entity merging, with contradictory pre-/post-linker records. It does
not involve TypeScript, tsconfig parsing, JSONC, or alias-table loading.

## Re-check — 2026-11-04 through #473 (superseded by the 2026-11-05 sweep)

The tracker subsequently advanced to **377 issues, newest #473**. Fresh
GitHub issue-search API results (`repo:FinanceFlash/unvibecode is:issue`,
open + closed) were:

| Search term | Hits | Assessment |
|---|---:|---|
| `jsonc` / `"JSONC"` | 2 | #451 and #455 |
| `"trailing comma"` | 2 | #451 and #455 |
| `_load_tsconfig_aliases` | 4 | #442, #451, #452, #455 |
| `tsconfig` / `alias tsconfig` | 7 | #153, #272, #374, #442, #451, #452, #455 |
| `"compilerOptions.paths"` | 4 | #153, #272, #374, #455 |
| `comment tsconfig` / `comments tsconfig` | 4 | #442, #451, #452, #455 |
| `json.loads tsconfig` | 4 | #272, #374, #451, #455 |
| `"path aliases"` | 8 | Includes the TypeScript-config neighbours above plus unrelated alias senses |

Issues #451, #452, and #455 were read at body level:

- **#451 is the same mechanism.** It states that both engines call
  `json.loads(safe_read_text(tsconfig))`, swallow the exception, and return an
  empty mapping for a valid commented/trailing-comma root config.
- **#452 is distinct.** Its config is strict JSON and parses; the defect is
  that ordinary imports are not resolved through `baseUrl` when no explicit
  `paths` table exists.
- **#455 is distinct.** Its configs are strict JSON and parse; the defect is
  that inherited/effective `paths` are not loaded because `extends` and
  non-root config discovery are not followed. It mentions #451 only to
  distinguish the parse-failure mechanism.

Issue titles #445–#473 were also scanned. Apart from #451/#452/#455, the new
TypeScript-adjacent titles concern other resolver, graph, workflow, or export
mechanisms; none changes the mechanism classification above.

## Latest re-check — 2026-11-05 through #532

The tracker subsequently advanced to **434 issues (242 open, 192 closed),
newest #532**. Fresh GitHub issue-search API results
(`repo:FinanceFlash/unvibecode is:issue`, open + closed) were:

| Search term | Hits | Assessment |
|---|---:|---|
| `jsonc` | 2 | #451 and #455 — unchanged |
| `"trailing comma"` | 2 | #451 and #455 — unchanged |
| `_load_tsconfig_aliases` | 4 | #442, #451, #452, #455 — unchanged |
| `tsconfig` | 8 | #153, #272, #374, #442, #451, #452, #455, **#501 (new)** |
| `"compilerOptions.paths"` | 4 | #153, #272, #374, #455 — unchanged |
| `comment tsconfig` / `comments tsconfig` | 4 | #442, #451, #452, #455 — unchanged |
| `json.loads tsconfig` | 4 | #272, #374, #451, #455 — unchanged |
| `"path aliases"` | 8 | #153, #272, #320, #378, #452, #453, #455, #457 |

No search term produced a second report of this mechanism. The two hits for
`jsonc` and `"trailing comma"` are still exactly #451 and #455.

All **58 issues added since the previous sweep (#474–#532)** were retrieved
through the REST issues endpoint and scanned at body level for
`jsonc`, `trailing comma`, `json.loads`, `tsconfig`, `compilerOptions`,
`path alias`, `strict json`, and `comments`. Twelve issues matched at least one
term; each match was read in context:

- **#501** is the only new issue whose body mentions `tsconfig`, and only in
  its own duplicate-check section cross-referencing #455's `extends` defect.
  Its mechanism is that unnormalized relative `../` specifiers never produce a
  candidate path in `LanguageAwareImportResolver`. No config is parsed and no
  alias table is discarded, so it is **distinct**.
- **#532** matches `json.loads` only inside its own verification harness,
  which reads a generated `context-store.json`. Its defect is that conditional
  `require`/`import` calls lose alternative module paths during JS/TS import
  extraction — **distinct**.
- **#483, #481, #495, #497, #498, #509, #518, #525** match `json.loads` in
  unrelated mechanisms (path role hints, documentation claims, Python symbol
  resolution, Go call-edge conversion, credential screening, `elif` nesting
  depth, and UTF-8 BOM handling in exported context). None touches tsconfig
  parsing — **distinct**.
- **#480** and **#515** match `comments` in unrelated senses (request
  queueing after a save error, and percent-encoded unreserved characters in an
  HTML asset resolver) — **distinct**.

The other TypeScript-adjacent titles in the new range (#490 `.js`→`.ts`
specifier resolution, #519 skipped `.mts`/`.cts` files, #527 Optimal context
omitting direct imports for a Python file, #531 HTML inline module imports,
#499 Windows separators in cross-reference links) concern extraction, scanner
extension coverage, selection ranking, and link formatting. None reports a
config-parse failure that empties an alias table.

**Conclusion of this sweep: #451 is still the single upstream report of this
mechanism, and the 2026-11-05 range adds no duplicate and no competing claim
of priority.**

## Conclusion
Through #444, no upstream issue reported this JSONC-empty-alias mechanism.
That historical result is no longer the current filing position: **#451
reports the same mechanism upstream**, and the sweeps through #473
(2026-11-04) and #532 (2026-11-05) confirm it is still the only such report.
This investigation's personal evidence repository predates #451, so the work
remains independently derived, but `submission/GITHUB_ISSUE.md` must not be
filed unchanged as a new report. Any upstream use should be a
maintainer/organizer-directed corroborating comment or an explicitly linked
supplementary-evidence submission that cites #451 rather than presenting the
mechanism as unreported; a decision-ready draft of that corroborating comment
is kept unfiled in
[`submission/UPSTREAM_CORROBORATION.md`](submission/UPSTREAM_CORROBORATION.md).
Adjacent #452 (`baseUrl`-only resolution), #455 (`extends`/effective config),
#442 (post-load target wildcards), and #501 (unnormalized relative `../`
candidates) remain distinct defects and are deliberately outside this
investigation's single-mechanism scope.
