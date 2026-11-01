# Standard-installation attempt (no parser-environment modification) — 2026-11-02

**Goal:** reproduce without the sandbox Tree-Sitter grammar workaround.

**What was done:** fresh `python3 -m pip install --target /tmp/std_pkg unvibecode` (0.3.15, vanilla dependencies, no shim on `PYTHONPATH`), Python 3.11.2, Linux x86_64.

**Verified WITHOUT the workaround (complete):**
- `reproduction/repro_unit.py` on the vanilla install: **exit 0, BUG REPRODUCED** — all JSONC fixtures yield `tsconfig_aliases={}` / `(None, None)`; strict-JSON control resolves; negative control behaves correctly. The defect mechanism (config parsing in `_load_tsconfig_aliases`) is pure Python and needs no parser, grammar, or network.

**Not completable in this sandbox (explicitly not claimed as done):**
- CLI end-to-end on the vanilla install: `python -m unvibecode review --repository reproduction/minimal_jsonc` → Stage-1 reports `2 files, 0 internal file edges, 0 unresolved` because TypeScript files are not parsed at all. Root error, reproduced directly:
  `DownloadError: Download error: Failed to fetch manifest from https://github.com/xberg-io/tree-sitter-language-pack/releases/download/v1.22.1/parsers.json: io: unexpected end of file`
  The sandbox egress proxy blocks GitHub release-asset hosts (`release-assets.githubusercontent.com` returns SSL EOF), so `tree-sitter-language-pack` cannot fetch grammars. This is an environment restriction (same failure class as upstream #378), not a product behavior being reported here.

**Workaround used for CLI-scale measurements, and why it cannot create this defect:** grammars were supplied through the engine's own documented fallback (`tree_sitter_languages.get_parser`) backed by official PyPI grammar wheels. It affects only AST production (import/entity extraction). Proof extraction was *not* the variable in the lexical comparison: both runs' extracted import records are identical (9,562 = 9,562) while only alias resolution changes. Shim fidelity was independently validated by reproducing `docs/GO_SUPPORT.md`'s chi reference run exactly (89 / 1,050 / 58).

**Environment-dependent claims:** only the lexical CLI edge counts depend on grammar availability (any correct grammar source — standard download on an unrestricted machine — should reproduce them; bundles were byte-identical across repeated runs). All mechanism claims are verified at unit level on the vanilla install.
