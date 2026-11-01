# Duplicate check — performed 2026-11-02 against all 322 issues (open + closed, to #417)

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

## Conclusion
No existing issue reports, at any level of wording, that JSONC content in `tsconfig.json` (comments/trailing commas) silently empties the tsconfig alias table. The mechanism, function (`_load_tsconfig_aliases`), trigger bytes, and remediation are all distinct from the neighbors above. This check must be repeated once more immediately before public filing (tracker is moving daily).
