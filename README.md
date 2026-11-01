# UnvibeCode Engineering Investigation — Cohort 3, Track 1

**Finding:** UnvibeCode 0.3.15 silently ignores `tsconfig.json` when it contains comments or trailing commas (valid JSONC), because `LanguageAwareImportResolver._load_tsconfig_aliases` uses strict `json.loads` inside a bare `except: pass`. All custom path-alias edges vanish from the Connected Code Map/context bundle with no warning. On facebook/lexical @ `164af6a`, five comment lines cost 4,256 of 5,519 internal file edges (~77%).

## Reproduce (fastest first)
1. **Unit level (seconds, no network/grammar):** with the `unvibecode` wheel importable, run `python3 reproduction/repro_unit.py` — `minimal_strict` resolves `@app/util → src/app/util.ts`; `minimal_jsonc` (one comment line differs) yields `tsconfig_aliases={}` and `(None, None)`.
2. **CLI, minimal:** `python -m unvibecode review --repository reproduction/minimal_jsonc` vs `.../minimal_strict`; compare the `STAGE 1 COMPLETE` line in `technical-logs/connected_code_map.log` and `connections.jsonl` in the emitted context ZIP.
3. **CLI, real repo:** clone `facebook/lexical` @ `164af6a4df7114f35724c472152ca74877b6bd04`, run the review as-is (expect `1,263 internal file edges`), then delete only the five `//` lines (9–13) from `tsconfig.json` and re-run (expect `5,519`).

## Layout
- `INDEPENDENT_STRATEGY.md` — strategy locked *before* seeing any external proposal (unchanged).
- `STRATEGY_DECISION.md` — adversarial comparison and final method (invariant/metamorphic testing with independent oracles, minimization, stage tracing).
- `ROOT_CAUSE.md` — mechanism, exact code location, fix direction.
- `DUPLICATE_CHECK.md` — mechanism-level check vs all 322 upstream issues.
- `evidence/EXPERIMENT_LOG.md` — every experiment, including the many negative results and two rejected candidates; `evidence/tsconfig-jsonc/` — lexical Stage-1 comparison + control diff; `evidence/trial-2026-11-01-flask/` — initial genuine trial record.
- `reproduction/` — minimal fixtures, `repro_unit.py`, and the bundle-integrity verifier (`verify_bundle.py`) used for the (negative-result) integrity campaign.
- `submission/GITHUB_ISSUE.md` — official 9-section issue draft (**not yet filed**); `submission/FORM_RESPONSE.md` — Google Form content (issue URL pending filing).

Environment record and sandbox limitations (hosted stages unreachable; grammar shim used and validated against `GO_SUPPORT.md` reference numbers) are documented honestly in `evidence/EXPERIMENT_LOG.md`. Nothing here depends on hosted/LLM output.
