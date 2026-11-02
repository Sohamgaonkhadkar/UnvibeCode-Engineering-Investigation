# Duplicate check — latest strengthening sweep 2026-11-02 against all 332 issues (open + closed, to #428)

## Searches run
Title sweeps for: `tsconfig` (**0 hits**), `jsonc` (**0**), `comment` (0 relevant), `alias` (8, reviewed), `require`/CommonJS, `../`, plus full re-listing immediately before drafting (no new issues after #417). Closest issues read in full:

| Issue | What it claims | Why ours is a different underlying cause |
|---|---|---|
| **#374** — `@/` aliases skipped as `hard_path_skipped` although defined in **vite.config.ts** | Linker hard-skips `@/` when the alias lives only in Vite config and the app tsconfig sits in a subdirectory (`frontend/`). | Our alias **is** in the root `tsconfig.json` that the engine already supports; it fails earlier, in `_load_tsconfig_aliases` parsing (strict `json.loads` on JSONC), and is recorded `external_or_unresolved`, not `hard_path_skipped`. Different stage, different function, different trigger, different fix. |
| **#272 / #153** — TypeScript `@/` path aliases skipped | Older behavior for the hardcoded `@/` prefix. | 0.3.15 already resolves `@/` via a hardcoded `src/` branch and custom aliases via tsconfig *when the file is strict JSON* (proven by our strict-JSON control). Our defect disables the custom-alias table itself. |
| **#320** — `_js_import_symbols` collects local aliases from aliased/namespace imports | Symbol-name extraction from import clauses. | Unrelated: our imports extract correctly (they appear in unresolved records); failure is alias-table loading. |
| **#262 / #84** — `../` imports unresolved (`to_posix_rel` never normalizes `..`) | Path normalization in relative resolution. | We reproduced this too (all web/Node resolvers) and deliberately do **not** file it — same cause as #262. Mentioned here to show the check was mechanism-level, not title-level. |
| **#372** — PHP `require/include` never extracted | Missing extractor branch in `_extract_php`. | Different language/stage (extraction vs config parsing). |
| **#378 / #323** — grammar-download / tokenizer failures still ending in “complete”/partial states | Environment failure handling. | Our runs needed a grammar shim in-sandbox (documented in the log); the filed defect is grammar-independent and reproduces at unit level with no parser involved. |

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
advanced to **332 issues, newest #428**. The exact-mechanism results remained
unchanged: `jsonc`, `trailing comma`, `_load_tsconfig_aliases`, `comment
tsconfig`, and `comments tsconfig` each returned 0; `tsconfig` and
`compilerOptions.paths` still returned only #153/#272/#374. Issue #427 concerns
duplicate Pass 1 activation facts, an unrelated hosted-analysis validation
mechanism. Issue #428 concerns an exported local symbol binding
(`Select = SelectPrimitive.Root`) not found while its module and sibling
exports resolve; that is a symbol-export mechanism, not root-tsconfig parsing
or Stage-1 alias-table loading.

## Conclusion
No existing issue reports, at any level of wording, that JSONC content in `tsconfig.json` (comments/trailing commas) silently empties the tsconfig alias table. The mechanism, function (`_load_tsconfig_aliases`), trigger bytes, and remediation are all distinct from the neighbors above. This check must be repeated once more immediately before public filing (tracker is moving daily).
