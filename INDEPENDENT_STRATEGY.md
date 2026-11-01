# INDEPENDENT STRATEGY — UnvibeCode Engineering Challenge 2026, Cohort 3, Track 1

**Status:** LOCKED independent recommendation. Written **before** viewing any external AI system's proposed approach.
**Date:** 2026-11-02 (IST) · **Investigator:** Soham Gaonkhadkar (lead reliability engineer role, AI-assisted)
**Scope:** Track 1 only — one original, non-duplicate, consequential defect in **UnvibeCode itself**, demonstrated while analyzing a real public repository. Final issue to be filed in `FinanceFlash/unvibecode`. This repository is the evidence workspace.

---

## 1. Understanding of the official challenge

Source of truth: `docs/UnvibeCode_Engineering_Challenge_2026_Cohort_3.md` in `FinanceFlash/unvibecode` (read in full).

- Install `unvibecode` from PyPI, run `python -m unvibecode review --repository "<local path>"` on a **real public repository**, verify claims against actual source — never assume output correctness.
- Find **one** original, non-duplicate, technically meaningful defect; investigate cause/boundaries; gather reproducible evidence; file **one** GitHub issue in the 9-section template; paste issue URL + analyzed-repo URL into the Google Form by **15 Nov 2026, 23:59 IST**. No PR.
- Duplicate rule is by **underlying cause**, not wording. A different example repository does not create originality.
- A missing feature, documented limitation, or speculative risk is **not** a defect. Non-deterministic findings must state frequency/conditions.
- Scoring (100): technical depth/root cause **35** · reproducibility/evidence **30** · real developer impact **20** · originality **10** · clarity **5**.

**Design consequence:** 65% of the score (depth + reproducibility) rewards defects with a *deterministic reproduction and an independently checkable expected result*. Findings that depend on stochastic hosted-LLM prose, or that require a judge to "agree the workflow description feels wrong," are structurally disadvantaged. The strategy below is chosen primarily on that basis.

## 2. Concise technical understanding of UnvibeCode (evidence-based)

Established by reading the official docs **and inspecting the installed PyPI wheel** (`unvibecode 0.3.15`), not from marketing copy.

### 2.1 What the product is
Four outputs per review: (1) Business Workflow Map, (2) Connected Code Map, (3) Business Risk Findings, (4) Complete Repository Context ZIP (`manifest.json`, `chunks.jsonl`, `connections.jsonl`, `selections.jsonl`, `unresolved_relationships.jsonl`). Supported languages: Python, JS/JSX/MJS/CJS, TS/TSX, Rust, PHP, Ruby, HTML/CSS, Go. Full workflow+risk review only at/below ~2M estimated source tokens; above that, only outputs (2) and (4).

### 2.2 Where the code actually lives (critical boundary)
- The **GitHub repository does not contain the engine**. It is docs, examples, workflow packs, skills, and sample reports. Judging "the codebase" from GitHub alone is a category error.
- The **PyPI wheel** installs package `shipreadyv2` (the `unvibecode` package is a 7-line shim). It ships *readable Python engine sources* in `shipreadyv2/engine_sources/` plus `customer_runner.py` (~148 KB), `cli.py`, `redaction.py`, export modules — **and five compiled native modules** (`assets_native`, `partition_native`, `path_merge_native`, `selector_native`, `taxonomy_native`, `.so`). Some partition/merge/selector/taxonomy logic is therefore **not source-inspectable**; claims about those internals must be behavioral, not invented.
- Pipeline (from stage headers + `customer_runner.py` orchestration):
  `00a` Fast Lane: scan → per-language AST (Python `ast`; tree-sitter for JS/TS/Rust/PHP/Ruby/Go) → import/symbol resolution → interactive graph + context bundle. **No LLM.**
  `01` Merged graph pipeline: deep graph, linker resolution, 12K batches → 50–70K semantic packs. **Local.**
  `02` Prepare Pass-1 inputs (token-budgeted, `cl100k_base`). **Local.**
  `03` Pass-1 runner → **hosted LLM** (`https://shipready-api.alphashots.ai/v1`, public-preview token in `cli.py`; no user key).
  `04` Business-path compiler (local, consumes Pass-1 output). `05` Critical-insight selector (**deterministic, explicitly no LLM**). `06` Step-4: one hosted LLM decision + HTML report.
- Credential redaction (`shipreadyv2/redaction.py`: `redact_text` / `redact_artifact` / `redact_payload`) is applied at multiple egress points (verified call sites in `03`, `06`, `secure_transport.create_response`, `completed_context_export`, `workflow_context`).
- Repository size estimate uses `supported_source_bytes / 3.2` (observed verbatim in trial `analysis-status.json`).

### 2.3 What I actually executed (trial record — nothing fabricated)

| Item | Recorded value |
|---|---|
| UnvibeCode | `0.3.15` (PyPI, `pip install --target` into isolated dir) |
| Environment | Python 3.11.2, Linux x86_64 (sandbox), `Linux 6.1.158+` |
| Target repo | `pallets/flask` @ `49943b5a94413a530761350f04e896f76e8d620e` (shallow clone) |
| Command | `python3 -m unvibecode review --repository /tmp/trial/flask` |
| Result | **PARTIAL, exit 1.** Fast Lane COMPLETED (~1.2 s): Connected Code Map + Context ZIP produced. Full analysis FAILED at Step 02. |
| Bundle ground truth | manifest: 102 source files, 482 chunks, 403 connections; `selections.jsonl` 102 rows; `unresolved_relationships.jsonl` 844 rows |
| Failure cause | `02…TokenCounter` → `tiktoken.get_encoding("cl100k_base")` → download from `openaipublic.blob.core.windows.net` blocked in this sandbox (TLS EOF) → `RuntimeError: Exact tokenizer could not be initialized…` |

Two honest conclusions: **(a)** this exact tokenizer failure class is *already reported* (#323, related #66) — it is **not** a candidate finding; **(b)** in *this* sandbox, hosted-dependent stages (03/06, plus 02 without a pre-seeded tiktoken cache) are not executable end-to-end, while the entire deterministic local pipeline (00a/01, exports, redaction functions) **is** executable and inspectable. On a normal developer machine with open egress the hosted stages should run, but any strategy requiring them must budget for LLM non-determinism and hosted credit exhaustion (itself reported: #334/#329/#361).

### 2.4 What the existing issue tracker already covers (duplicate map)

Full sweep on 2026-11-01/02: **321 issues fetched (263 open / 58 closed), numbers to #416**, titles + states reviewed; mechanisms sampled. Crowded classes (representative numbers):

| Class | Saturation | Examples |
|---|---|---|
| Per-language import/symbol graph resolution | **Very high (50+)** | Py re-export/ambiguity #416 #387 #330 #316, wildcard #380 #379, relative #300 #279, src-layout #308; JS/TS alias/query/attributes #374 #384 #383 #320 #324 #232; Rust #393 #391 #390 #371; Go #415 #364 #341 #302; PHP #377 #372 #352; HTML #386 #385 |
| Credential-redaction bypasses | **Very high (~15)** | #396 #388 #375 #368 #365 #353 #345 #344 #327 #326 #315 #406 |
| Hosted workflow/risk correctness & stability | High | #408 unstable workflow sets/IDs, #409 adjudication ceilings, #395, #369, #277, #251, #250 |
| Status/coverage honesty in reports | High | #378 COMPLETE despite 0-symbol files, #294, #253, #50, #328, #290 |
| Scanner/size/token gates | High | #405 pruned dir names, #336, #332 chars/3.2 undercount, #323 tokenizer crash, #225 |
| Chunking/context integrity (specific defects) | Medium | #340 invalid-Python segments, #381 line shift, #397 prelude truncation, #310/#287 line semantics, #367 budget envelope, #318 Wider⊄Optimal |
| CLI/platform crashes | High | Windows cp1252 family (#335 #317 #314 #299…), #407, #373, #350 |
| GitHub-repo content (skills/notebooks/CI) | Medium | #398–#404 — real, but weaker fit for "defect found *using the tool on a real repository*" |

**Implication:** originality will not come from "another import form in language X" or "another secret regex shape" unless the *underlying cause* is demonstrably distinct. White space is more likely in **cross-cutting contracts of the generated artifacts themselves** (invariants spanning chunks/connections/selections/manifest), in **compiler-oracle-verified** graph semantics not yet enumerated, or in **unexamined egress paths** — in that order of expected reproducibility.

---

## 3. Three genuinely different investigation strategies

### Strategy A — Deterministic artifact-integrity auditing via invariant & metamorphic testing *(PREFERRED — see §5)*

1. **Property investigated.** Whether the locally generated context bundle — the artifact developers and downstream LLMs actually consume — satisfies its own structural contracts: (i) *lossless partition* (chunks reconstruct each source file exactly, no silent loss/duplication beyond declared overlap); (ii) *referential integrity* (every `source_chunk`/`target_chunk`/`chunk_ids` reference resolves; no dangling or duplicate IDs); (iii) *manifest truthfulness* (counts/file inventory match bundle contents and the on-disk supported-file inventory); (iv) *determinism* (two runs on identical input produce identical local artifacts modulo timestamps); (v) *coordinate truthfulness* (chunk `line_range` and connection line fields point at the claimed source text).
2. **Why defects are likely.** The bundle is assembled by multiple large, independently evolved stages (00a Fast Lane bundle, 01 graph pipeline, export normalizers, compiled partition/merge natives) with several ID/line-number representations. My Flask trial already shows surface tension worth auditing (not conclusions): size-estimator counts **105** source files vs bundle manifest **102**; a radius-0 selection for a 1,342-token file reports `estimated_tokens: 3842`. Hand-rolled multi-stage serialization is exactly where silent integrity drift accumulates — and silent context corruption misleads every downstream AI-assisted decision.
3. **Why this is not generic bug hunting.** No manual "run it and eyeball the HTML." I write an independent verifier that encodes the contracts as executable invariants, then run it across diverse real repositories + adversarial fixtures (generated edge-case files). Failures are minimized automatically to a smallest violating file set.
4. **Independent oracle.** The source files themselves + `python -m ast` / filesystem inventory + set/hash mathematics. Expected behavior never comes from UnvibeCode's own output.
5. **Falsification.** If all invariants hold across ≥3 diverse real repos and the adversarial fixture suite, the hypothesis "bundle integrity is broken" is *falsified* for those contracts — a legitimate negative result triggering pivot (§5.4). Positive/negative controls: verifier must (a) pass a hand-built known-good bundle, (b) detect deliberately corrupted bundles (mutated IDs, dropped chunk, shifted lines).
6. **Tools/env.** Python 3.11, installed wheel, `jq`/custom verifier scripts, public repo clones. **No hosted API, no LLM, no credits** — fully runnable in this sandbox and on any judge's machine offline (Fast Lane artifacts suffice).
7. **Originality assessment.** Prior issues report *individual* symptoms (#340 invalid segments, #381 line shift for ^L/U+2028, #310/#287 specific line-field semantics, #284 unresolved-record shapes, #337 omitted source). I must (a) treat those exact mechanisms as taken, (b) only file a violation whose mechanism differs (e.g., partition loss, referential breakage, manifest/inventory divergence, non-determinism with a local cause), and (c) cite nearest neighbors in the issue's duplicate-check section with the causal distinction. Risk managed, not eliminated.
8. **Impracticality risks.** Contracts are partly undocumented (e.g., is chunk overlap intended? what does `source_line` promise?) — mitigation: derive promises from `docs/OUTPUTS.md`, bundle README, and code comments; where semantics are genuinely unspecified, test only *self-consistency* invariants no reasonable implementation may violate. Native `.so` stages may block line-level root-causing — mitigation: isolate by stage outputs (Fast Lane store vs final ZIP) to localize without decompilation claims.

**First experiment (A-E1):** Double-run determinism + referential-integrity + manifest-vs-inventory check on the already-produced Flask bundle, plus a fresh second run. Pass/fail is binary and immediate.

### Strategy B — Compiler/runtime-oracle differential testing of the Connected Code graph

1. **Property investigated.** Whether extracted file/symbol edges equal the ground-truth dependency graph as defined by each language's own tooling: Python (`ast` + import system semantics), TypeScript (`tsc` module resolution), Go (`go list`), Rust (`cargo metadata`/module rules), on semantically equivalent multi-file programs and on real repos.
2. **Why defects are likely.** Resolution is reimplemented per language in two parallel engines (00a/01) with name-based fallbacks; the tracker proves this surface is fertile (50+ issues). Fertility is also the problem (see 7).
3. **Difference from generic hunting.** Ground truth is generated by compilers/runtimes, and test programs are *equivalent-by-construction* across languages, so each divergence isolates a resolver rule rather than an anecdote.
4. **Independent oracle.** `go list -json`, `tsc --traceResolution`, Python importlib spec finding, Rust reference module rules — plus execution of the fixture programs.
5. **Falsification.** If edges match oracles across the equivalence corpus (excluding documented heuristic limits), resolver-defect hypothesis fails for those constructs. Controls: fixtures where the correct edge is *absent* (external deps) to catch false-positive edges, not just missing ones.
6. **Tools/env.** Node/tsc, Go, Cargo toolchains (installable here? Go/Rust toolchains are heavy; network limited to GitHub/PyPI/npm in sandbox — Go/Rust oracle setup may be impractical in-sandbox, feasible on a local dev machine).
7. **Originality assessment.** **Highest duplicate risk of the three.** Dozens of resolver mechanisms are taken within the last days alone (#372–#416). Viable only with disciplined pre-checking: enumerate constructs, map each against issue mechanisms, and target only unclaimed semantics (e.g., constructs whose *cause* differs from name-fallback/scoping bugs already filed).
8. **Impracticality risks.** Toolchain provisioning; distinguishing "documented heuristic limitation" (`LIMITATIONS.md`, `GO_SUPPORT.md`) from defect; investigation can fragment into many shallow edge cases — the opposite of the depth criterion.

**First experiment (B-E1):** One 6-file Python package exercising `__init__` re-export, relative submodule import, `TYPE_CHECKING` import, and aliased import; compare edges vs importlib ground truth; discard any divergence whose mechanism matches #416/#300/#150/#311.

### Strategy C — Egress-boundary canary audit (credential redaction completeness)

1. **Property investigated.** Whether *every* path that moves repository content off the machine or into a shareable artifact — Pass-1 request assembly (03), Step-4 request (06), `secure_transport`, completed-context ZIP export, workflow/context downloads, supplemental context, technical logs — applies redaction completely and without corrupting benign code.
2. **Why defects are likely.** Redaction is regex/line-based, invoked from many call sites across two code generations (engine sources + `shipreadyv2/*.py`); new export paths can bypass it. Impact is unambiguous: real secrets sent to a hosted service.
3. **Difference from generic hunting.** A *path × secret-shape matrix* with unique canary tokens per cell; leakage is detected by exact string search, and over-redaction by round-trip diffing of benign code. This tests architecture (coverage of paths), not just one regex.
4. **Independent oracle.** Canary presence/absence. No judgment calls.
5. **Falsification.** If all canaries are redacted on all reachable paths and benign controls survive byte-identical (modulo placeholders), the leakage hypothesis fails for the tested matrix. Controls: known-redacted shapes (e.g., `AKIA…`, PEM blocks) must be caught — proves harness validity.
6. **Tools/env.** Local only: invoke `redact_text`/`redact_artifact` and the export functions directly; capture *pre-upload* request payloads by monkeypatching `create_response`/transport in a test harness. **Never** send canaries to the real hosted service; never use real credentials. (Ethics/compliance: synthetic canaries only; a confirmed *live-service* leak class may belong in private security reporting per repo SECURITY policy — to be weighed before any public issue.)
7. **Originality assessment.** Single-shape regex misses are saturated (~15 issues: #315 #326 #327 #344 #345 #353 #368 #375 #388 #396 #406 #365…). Originality requires a *new path or structural cause* (e.g., an export/log path with no screening at all, or a transformation-order bug where redaction runs before content is added), explicitly differentiated from #365 (ZIP/HTML store) and the shape-miss family.
8. **Impracticality risks.** Duplicate saturation; responsible-disclosure tension (public issue vs private advisory); hosted payload capture requires care to stay offline; a "new regex miss" finding would likely score as duplicate-class despite being real.

**First experiment (C-E1):** Build the egress inventory from call-site grep (done, §2.2), then run 20 known-shape canaries through `redact_artifact` for each artifact filename the tool emits; any path with *zero* screening becomes the lead.

*Considered and not shortlisted:* hosted workflow/risk semantic correctness (non-deterministic oracle, credit/egress dependent — weak on the 30% reproducibility criterion); failure-semantics/status-honesty matrix (valuable, but #378/#294/#253/#407/#323 already claim its center); 2M-token gate accuracy (largely claimed by #332/#336/#225). These remain fallbacks if A–C falsify.

## 4. Comparison against official scoring criteria

Scored as *expected value before execution* (H/M/L), assuming competent execution:

| Criterion (weight) | A: Artifact integrity | B: Compiler-oracle graph | C: Egress canary audit |
|---|---|---|---|
| Technical depth / root cause (35) | **H** — multi-stage contract tracing, stage isolation | H — language-semantics depth, but risks shallow-per-case spread | M–H — deep if architectural; shallow if regex-shape |
| Reproducibility / evidence (30) | **H** — deterministic, offline, binary checks, minimal fixtures | H — deterministic; toolchain setup cost for judges | **H** — canary string match is unambiguous |
| Real developer impact (20) | **H** — corrupted/incomplete context silently misleads AI-assisted changes repo-wide | M–H — wrong edges mislead navigation/context | **H** — secret exfiltration to hosted service |
| Originality (10) | **M–H** — neighbors exist, contract-level white space remains | L–M — most saturated class in tracker | L–M — saturated unless new path/cause |
| Clarity (5) | H — invariant + minimal fixture is easy to state | M — needs language-rule exposition | H — canary in/out is self-evident |
| **Feasibility in available env / by 15 Nov** | **H — proven runnable today** | M — Go/Rust oracles heavy in sandbox | H locally; disclosure judgment needed |

## 5. Independently selected preferred strategy: **A — artifact-integrity auditing**

### 5.1 Why A wins
It maximizes the two heaviest criteria simultaneously: the oracle is mathematics + source text (reproducibility), and any violation forces genuine multi-stage root-cause work across scanner → chunker → linker → exporter (depth). It targets the artifact with the broadest blast radius — the context bundle feeds the Connected Code downloads, workflow context, and users' own LLM sessions — so a silent integrity defect outranks a single missing edge or a single secret shape in developer impact, while sitting in less saturated originality territory than B and C. Crucially, it is the only strategy I have *already proven executable* in the available environment. Strategies B and C remain documented pivots, not decorations.

### 5.2 Target, method, resources
- **Target:** Fast Lane + export path producing `complete_repository_context_for_llm.zip` and the browser context store (`00a`, `repository_context_export.py`, `completed_context_export.py`, `context_readable_export.py`, `workflow_context.py`, natives at stage boundaries).
- **Method:** (1) Extract stated contracts from docs/bundle README/code. (2) Implement `verify_bundle.py` checking invariants (i)–(v) with positive/negative controls. (3) Run on real repos (§5.3) + adversarial fixtures (CRLF/BOM/encoding cookies*, huge single entity, empty files, symlinks*, duplicate basenames, generated code, non-ASCII identifiers — *only where not already claimed: #274/#350 mechanisms excluded*). (4) Minimize first violation to smallest fixture; bisect stage outputs to localize cause; confirm on a second real repo. (5) File one issue with fixture + verifier in this evidence repo.
- **Resources:** Python 3.11 + wheel 0.3.15, git clones, ~hours of compute. No hosted credits. All runs recorded (version, commit, hashes).

### 5.3 Repository selection criteria (real, public)
Diversity over fame: (1) Python `src/`-layout library (Flask — baseline done), (2) mixed Python+JS/TS app repo, (3) repo with very large single files / generated files, (4) monorepo with duplicate basenames. Each pinned by commit SHA. Flask is retained as baseline because judges can reproduce it trivially, not because a Flask-specific symptom would be claimed as original.

### 5.4 Strongest potential evidence & abandonment criteria
- **Strongest evidence:** a ≤5-file fixture + one-command verifier output showing e.g. reconstructable-source loss or a dangling chunk reference, reproduced on a pinned real-repo commit, with stage-isolation pointing at the responsible transformation and a falsifiable fix hypothesis.
- **Abandon A if:** invariants hold on all §5.3 repos + fixture suite; **or** every violation found reduces to a mechanism already filed (#340/#381/#310/#287/#284/#337 family); **or** violations trace only into opaque natives with no behavioral isolation possible. Then pivot to **C** (path-coverage framing) and only then B. Negative results will be recorded in this repo either way — a strategy that cannot fail honestly is not a strategy.
- **Confirmation-bias guards:** verifier written from docs/source *before* inspecting outputs for "interesting" anomalies; controls in §3-A(5); every candidate violation re-checked against raw source by hand; duplicate check performed on *mechanism*, with nearest issues re-read in full before filing.

## 6. Supporting technical evidence & references

- Official challenge, README, `HOW_IT_WORKS.md`, `LIMITATIONS.md`, `OUTPUTS.md`, `DATA_PROCESSING.md` (FinanceFlash/unvibecode, fetched 2026-11-01).
- PyPI wheel `unvibecode-0.3.15`: `SOURCE_MANIFEST.json` (engine baseline 0.2.1 + patch history), `shipreadyv2/cli.py` (hosted base URL, preview token, temp-engine materialization), stage headers `00a`–`06`, `customer_runner.py` structure (lanes, `IGNORED_DIRECTORY_NAMES`, size estimator), `redaction.py` call-site map (this document §2.2).
- Trial artifacts (sandbox `/tmp/trial/run/...20261101_204631/`): `analysis-status.json` (105 files / 188,576 est. tokens / `bytes÷3.2`), bundle manifest (102/482/403), Step-02 tiktoken traceback. Salient excerpts will be copied into `evidence/` with hashes during execution phase; bulk outputs stay out of git.
- Issue sweep: `gh issue list --state all --limit 500` → 321 records to #416 (2026-11-01). Class map in §2.4.

## 7. Known existing issues that could overlap the preferred strategy

Must be re-read in full before filing; any candidate sharing their mechanism is disqualified: **#340** (oversized-entity chunk splits), **#381** (^L/U+2028 line shift), **#397** (prelude truncation), **#310 / #287 / #237** (line-coordinate semantics), **#284** (unresolved record shapes), **#337** (LLM context omits source), **#321** (empty `__init__` markers), **#367 / #223 / #332** (token-budget estimates), **#318** (Wider not superset of Optimal), **#313** (workflow-reference schema mismatch), **#405 / #278 / #148** (scanner inventory), **#357 / #85** (duplicate connection records). For pivots: B ↔ §2.4 row 1 (50+ issues); C ↔ #365 #396 #388 #375 #368 #353 #345 #344 #327 #326 #315 #406 #252.

## 8. First experiments (execution order)

1. **A-E1 Determinism:** second review run on Flask @ pinned SHA; hash-compare bundles (excluding timestamps/paths). Any diff → localize.
2. **A-E2 Referential integrity + manifest truthfulness:** verifier over existing Flask bundle: ID resolution both directions, duplicate IDs, manifest counts vs actual rows, bundle file inventory vs on-disk supported files (explain 105-vs-102).
3. **A-E3 Lossless partition:** per-file reconstruction from `numbered_code` (strip numbering) vs source bytes; report loss/duplication beyond declared overlap; hand-verify first mismatch.
4. **A-E4 Controls:** mutate a copy of the bundle (drop a chunk, rename an ID, shift a line range) — verifier must catch all; hand-built 3-file repo with known graph must pass clean.
5. **A-E5 Adversarial fixtures + second real repo** (mixed-language), only after A-E1…E4 instrumentation is trustworthy.

Each experiment logs: exact command, tool/repo versions, input hashes, raw output — sufficient for a judge to re-run verbatim.

## 9. Uncertainties & feasibility limitations (stated plainly)

- Hosted stages (03/06) and Step 02 were **not** executed end-to-end in this sandbox (egress allowlist blocks `openaipublic.blob.core.windows.net` and the hosted API). Any later claim touching them requires re-execution on an open network with a seeded tiktoken cache and available hosted credits; LLM-stage claims would additionally need multi-run frequency reporting.
- Five engine components are compiled natives; root-cause claims about them will be behavioral/stage-isolated, never fabricated source readings. The GitHub repo's lack of engine source also means "line numbers" in a future issue must reference the *installed wheel* paths+version, which judges can verify via `pip show -f unvibecode`.
- Bundle contracts are only partly documented; where I infer a contract, the issue must label it as inferred-from-code/docs and prefer self-consistency invariants.
- The tracker is moving fast (issues #372–#416 landed within ~2 days). Duplicate checking must be **repeated immediately before filing**, not inherited from this document.
- Trial observations in §2.3/§3 (105-vs-102 files; 3,842-vs-1,342 tokens) are *leads for instrumentation*, explicitly **not** claimed defects; neighbors #405/#367 may already explain them.
- Deadline risk is low for Strategy A (offline, fast runs); the main schedule risk is a late duplicate filing by another participant — mitigated by executing A-E1…E4 immediately after the comparison checkpoint.

---

**Independence declaration:** This strategy was derived solely from the official challenge text, product documentation, the installed 0.3.15 distribution, a genuine trial execution, and the public issue tracker. No external AI system's proposed approach was requested, read, or incorporated. Locked at the comparison checkpoint pending the user's supply of the independent GPT approach; no public issue has been filed and nothing has been submitted.
