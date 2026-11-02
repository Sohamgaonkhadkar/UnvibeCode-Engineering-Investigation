# STRATEGY DECISION — Phase 2 adversarial comparison

**Date:** 2026-11-02 (IST). `INDEPENDENT_STRATEGY.md` is retained unchanged; this document records the post-comparison decision only.

## 1. The two strategies, faithfully summarized

**Mine (locked pre-comparison).** Preferred: *Strategy A — deterministic artifact-integrity auditing* of the Complete Repository Context bundle (lossless chunk partition, referential integrity, manifest truthfulness, determinism, coordinate truthfulness), oracle = source files + `ast` + set math, fully offline. Alternatives documented: B compiler-oracle graph differential testing; C egress/redaction canary audit. Selection driven by scoring weights (depth 35 + reproducibility 30), proven sandbox executability (genuine Flask trial), and a 321-issue duplicate map.

**GPT's.** *Contract-based differential and metamorphic investigation*: test correctness contracts between pipeline stages via (A) metamorphic relations (semantics-preserving/-changing/negative-control transformations), (B) independent ground-truth oracles, (C) cross-stage consistency, (D) counterexample minimization, (E) implementation tracing to earliest corrupted stage. Deliberately target-agnostic: a methodology in search of the most valuable contract, with explicit warnings that output difference ≠ defect and that invariants must be contract-justified.

## 2. Adversarial critique — GPT's proposal

**Strengths.** Metamorphic relations + negative controls are exactly the right antidote to confirmation bias, and my Strategy A underuses semantics-preserving transformations (I test one input deeply; GPT tests *relations between inputs*, which can expose defects invisible in any single run — e.g., order-dependence, rename sensitivity). Minimization (D) and earliest-stage localization (E) materially strengthen root-cause scoring. Its repeated contract-justification warnings are technically correct and would have prevented several weak issues already in the tracker.

**Weaknesses.**
1. **It is a method, not a target.** It never commits to *which* contract, language, or stage — so it cannot be scored for originality or feasibility as written. Executed naively it drifts toward the graph-resolution surface, which my sweep shows is the most duplicate-saturated class (50+ issues; still growing — #417 landed during this comparison).
2. **Metamorphic oracles for static analysis are easy to overstate.** Rename/move/reorder transformations *legitimately* change chunk IDs, line numbers, token packing, tie-breaking, and heuristic fallbacks; defining the equivalence relation tightly enough to survive a skeptical maintainer is the entire difficulty, and GPT's text acknowledges but does not solve it.
3. **Cost.** Building semantics-preserving transformers + equivalence normalizers for multiple constructs is the most expensive option under a 15 Nov deadline, with real risk of producing elegant machinery and no defect.
4. It is silent on this environment's hard constraint (hosted stages/tokenizer unreachable in-sandbox) and on the compiled-native visibility limits — both discovered only by executing the real distribution.

## 3. Adversarial critique — my own strategy

1. **Contract risk (GPT's strongest implicit hit).** Several of my invariants (lossless partition, strict referential closure) are only *partly* documented. If chunking is intentionally selective, "missing lines" is a design choice, not a defect. Mitigation already planned — self-consistency invariants + doc-derived promises — but the risk is real and could falsify A quickly. That is acceptable *only* because falsification is cheap (hours, not days).
2. **Neighbor density.** #340/#381/#397/#310/#287/#284/#337/#318/#367 claim individual integrity symptoms. A generic "bundle is inconsistent" finding would be a duplicate bundle, not a finding. I must isolate *one mechanism* outside that set or abandon.
3. **Single-input blindness.** Pure invariant checking on static outputs cannot detect defects that are internally consistent but semantically wrong (e.g., consistently wrong resolution). GPT's differential technique covers this; mine alone does not.
4. Native `.so` stages may cap root-cause depth at stage-boundary localization.

## 4. Overlap with existing issues (refreshed sweep: 322 issues, to #417)

| Direction | Saturation verdict |
|---|---|
| Graph/import resolution (GPT's likely drift; my B) | Saturated; #417 (Go dot-import) filed *today*. Execute only with pre-mapped unclaimed constructs. |
| Redaction shapes (my C) | Saturated by shape; viable only via unscreened *path*. |
| Bundle integrity symptoms (my A) | Individual symptoms claimed (list in `INDEPENDENT_STRATEGY.md` §7); **contract-level invariants** (partition losslessness, ID referential closure, manifest-vs-inventory, local determinism) not yet claimed as mechanisms. |
| Metamorphic/differential *relations* (GPT A) | No existing issue is framed as a transformation-relation violation — methodological white space, but the *underlying cause* found could still duplicate an existing one; cause-level check remains mandatory. |

## 5. Decision: **C — justified hybrid, with ONE primary direction**

**Primary direction (unchanged): the deterministic local artifact pipeline — bundle/graph outputs of stages 00a/01 + exporters.** This is the only surface simultaneously (i) executable end-to-end in the available environment, (ii) deterministic (immune to LLM nondeterminism — GPT critique #3 does not apply), (iii) source-inspectable in the shipped wheel, and (iv) not yet saturated at the contract level.

**Adopted from GPT (each adoption is load-bearing, not decorative):**
- *Metamorphic controls (GPT-A/B/C)* layered onto invariant testing: semantics-preserving transformations (consistent rename; append unrelated file; reorder independent declarations) must preserve the tested invariant/relationship after stated normalization; semantics-changing single-edit controls must move exactly the expected records; negative controls must move nothing. This converts "I found an inconsistency" into "*this input condition causes* the inconsistency" — the causal evidence pattern GPT §7 describes.
- *Minimization (GPT-D)*: delta-reduce any real-repo violation to the smallest fixture preserving it.
- *Earliest-stage tracing (GPT-E)*: compare Fast Lane store → graph JSON → bundle ZIP to find where the property is first lost; no invented internals for natives/hosted steps.
- *Oracle discipline (GPT-B)*: expected results from source text, `ast`, importlib — never from another LLM.

**Rejected:** GPT as a standalone target-agnostic program (unbounded cost, drift to saturated surface); my Strategies B/C as primaries (saturation/disclosure reasons unchanged — they remain pivots).

Why this is technically stronger than either alone: my strategy supplies the *target, oracle, and feasibility proof*; GPT supplies *causal experimental design* my original lacked. Neither alone maximizes depth×reproducibility×originality; the hybrid's first experiments are cheap and falsifiable within hours.

## 6. First experiments (expected results stated BEFORE running)

| # | Experiment | Expected if implementation is correct | Falsifies |
|---|---|---|---|
| E1 | Verifier on existing Flask bundle: manifest counts, ID referential closure, chunk `line_range`↔`numbered_code` agreement, chunk text vs source lines, per-file line coverage (gaps/overlaps/conflicts) | All counts match; zero dangling IDs; chunk text equals source at claimed lines; every source line covered ≥1× with no conflicting copies | "Bundle is self-consistent & faithful" |
| E2 | Controls: (a) hand-built 3-file known-good repo → tool → verifier must pass relevant checks; (b) mutated bundle (drop chunk, rename ID, shift line) → verifier must flag each | Verifier passes (a), flags all (b) | "Verifier itself is trustworthy" |
| E3 | Determinism: two fresh runs, Flask @ `49943b5…`, compare bundle member bytes | Identical modulo archive timestamps | "Local pipeline is deterministic" |
| E4 | Metamorphic: consistent module rename in fixture copy; append-unrelated-file control; single-import-edit control | Named relationship preserved under rename after normalization; unrelated file changes no existing records except additions; single edit changes only records for that import | "Outputs depend only on relevant semantics" |
| E5 | Second real repo (mixed-language) + adversarial fixtures (CRLF, BOM, empty file, duplicate basenames, oversized entity*) | Invariants hold as in E1 | Generality of any E1 finding (*oversized-entity chunking mechanism #340 excluded from claims) |

## 7. Abandonment / pivot criteria (binding)

- If E1–E5 show no violation outside already-filed mechanisms → **abandon A**; pivot to Strategy C path-coverage (local export/log paths), then B with pre-mapped constructs. Record negative results in `evidence/`.
- If a violation's cause matches an existing issue's mechanism (full-text re-read, not title) → discard candidate, keep hunting within budget; never repackage.
- If root cause is unreachable (native-only, no behavioral isolation) and impact cannot be measured → downgrade candidate; prefer a shallower but provable defect over an impressive unprovable one.
- Time box: candidate must be verified + minimized well before 15 Nov; submission drafts are prepared but **not published without user approval** (Part VI boundary).

## 8. Environment record (Phase 1, actuals)

OS/arch: Linux 6.1.158+ x86_64 (sandbox) · Python 3.11.2 · `unvibecode 0.3.15` (PyPI wheel; deps incl. tree-sitter 0.26.0, tree-sitter-language-pack 1.22.1, tiktoken 0.14.0, openai 2.54.0) · Target: `https://github.com/pallets/flask` @ `49943b5a94413a530761350f04e896f76e8d620e` · Command: `python3 -m unvibecode review --repository <path>` · Stage status in trial: Fast Lane COMPLETED; full analysis FAILED @ Step 02 (tiktoken BPE download blocked by sandbox egress — already upstream as #323; hosted stages therefore **out of scope** for claims until re-executed on an open network).
