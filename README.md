# UnvibeCode Engineering Investigation — Cohort 3, Track 1

**Finding:** UnvibeCode 0.3.15 silently ignores `tsconfig.json` when it contains comments or trailing commas (valid JSONC), because `LanguageAwareImportResolver._load_tsconfig_aliases` uses strict `json.loads` inside a bare `except: pass`. All custom path-alias edges vanish from the Connected Code Map/context bundle with no warning. On meta/lexical @ `164af6a`, five comment lines suppress 4,256 internal file edges (control total 5,519) — proven at graph-record level to be 100% alias-specifier edges, with identical scanned files and identical extracted imports in both runs.

## Reproduce (fastest first)
1. **Unit level (seconds, no network/grammar):** `python -m pip install --upgrade unvibecode`, then `python reproduction/repro_unit.py` (assertions + exit codes; `--expect-fixed` = post-fix regression mode). Add `python reproduction/correction_poc.py` for the validated fix-direction proof-of-concept.
2. **CLI, minimal:** `python -m unvibecode review --repository reproduction/minimal_jsonc` vs `.../minimal_strict`; compare the `STAGE 1 COMPLETE` line in `technical-logs/connected_code_map.log` and `connections.jsonl` in the emitted context ZIP.
3. **CLI, real repo:** clone `meta/lexical` @ `164af6a4df7114f35724c472152ca74877b6bd04`, run the review as-is (expect `1,263 internal file edges`), then delete only the five `//` lines (9–13) from `tsconfig.json` and re-run (expect `5,519`).

## Layout
- `INDEPENDENT_STRATEGY.md` — strategy locked *before* seeing any external proposal (unchanged).
- `STRATEGY_DECISION.md` — adversarial comparison and final method (invariant/metamorphic testing with independent oracles, minimization, stage tracing).
- `ROOT_CAUSE.md` — mechanism, exact code location, fix direction.
- `DUPLICATE_CHECK.md` — mechanism-level check vs all 322 upstream issues.
- `evidence/EXPERIMENT_LOG.md` — every experiment, including the many negative results and two rejected candidates; `evidence/tsconfig-jsonc/` — lexical Stage-1 comparison, tsconfig original/control pair + diff, graph excerpts + comparison output, standard-install attempt record; `evidence/trial-2026-11-01-flask/` — initial genuine trial record.
- `reproduction/` — minimal fixtures (strict / `//` / `/* */` / trailing-comma / negative-control / string-safety), `repro_unit.py`, `correction_poc.py`, `compare_graphs.py` (graph-level delta attribution), and the bundle-integrity verifier (`verify_bundle.py`) used for the (negative-result) integrity campaign.
- `submission/GITHUB_ISSUE.md` — official 9-section issue draft (**not yet filed**); `submission/FORM_RESPONSE.md` — Google Form content (issue URL pending filing).

Environment record and sandbox limitations (hosted stages unreachable; grammar shim used and validated against `GO_SUPPORT.md` reference numbers) are documented honestly in `evidence/EXPERIMENT_LOG.md`. Nothing here depends on hosted/LLM output.
