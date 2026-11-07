# Candidate screening and scope decision

> Historical decision. Upstream #596 now covers the selected Go cause; see
> [ELIGIBILITY.md](ELIGIBILITY.md). The risk-summary candidate has since reached
> full selector-file experiments, but an earlier-report lead prevents an
> originality claim; see [provisional research](../risk-evidence-summary/README.md).

Five plausible directions were screened using the installed product. Commands:

```sh
python investigations/go-named-results/reproduction/screen_candidates.py --output candidate-screen.json
```

Recorded output: [candidate-screen.json](evidence/candidate-screen.json).
These screens precede the selected candidate's deeper verification; helper-level
observations are deliberately not presented as complete product defects.

| Candidate / subsystem | Controlled observation | Decision |
| --- | --- | --- |
| Go result-variable receiver binding / graph parsing | `(r *Store)` produces package `selector`; input parameter `r *Store` produces typed `method_call` | Selected after full export and public-source validation |
| Python `except*` / uncertainty metadata | Ordinary `try` marks an enclosed import `try_import_fallback`; equivalent `TryStar` wrapper leaves the reason list empty | Deferred: no measured developer-facing export impact; compare adjacent #522 before any further claim |
| CSS nested media assets / source extraction | Top-level `url(logo.svg)` extracted; same declaration under `@media` omitted | Rejected for this submission: asset graph scope overlaps #386; parsing difference alone does not establish a new meaningful supported relationship |
| HTML-like source / context serialization | Closing-script text and Unicode survive external JS-store serialization and JSON parsing | Hypothesis falsified; the store is external JS, not an inline HTML script body |
| Risk-proof summary/source separation / deterministic qualification | A boundary regex can match the evidence summary when cited source alone does not match | Deferred: controlled helper input only; natural nomination and final finding not established. No claim of a shipped false finding |

The selected hypothesis arose from inspecting the collector's environment setup,
not from a competitor's reproducer. An initial minimal run without grammar
network access returned `tree_sitter_missing` in all three controls; this was an
environment failure, not evidence. Rerunning the actual installed parser with
grammar access produced the typed-versus-selector divergence. A first diagnostic
patch had an indentation error before application; it was corrected, and all
reported results come from the subsequent successful verifier.

The preliminary real-repository search checked go-sql-driver/mysql signatures,
but no qualifying public impact was established there. LevelDB was selected
because its `newSession` named result invokes methods in other files and the
exported selections expose a concrete loss.

## Decision matrix against the official criteria

Judgments are qualitative; the table does not invent predicted judge scores.

| Candidate | Root-cause confidence (35) | Reproducibility (30) | Developer impact (20) | Originality (10) | Overall |
| --- | --- | --- | --- | --- | --- |
| Go named results | Exact omitted binding; reversible intervention | Both engines, compiling controls, real ZIP, ordinary CLI | Wrong implementation in fixture; missing initializer implementation on LevelDB | No mechanism match in current audit; adjacent Go reports differentiated | Strongest verified candidate |
| Python `TryStar` | Missing visitor specialization observed | Small deterministic input | Only metadata measured | Not established; adjacent issue remains | Insufficient impact |
| CSS nested media | At-rule content not traversed | Small deterministic input | Asset support boundary uncertain | Adjacent asset omission report | Reject |
| Context serialization | Expected behavior holds | Deterministic round-trip | No failure | Not applicable | Reject |
| Risk summary/source | Helper combines text sources | Deterministic helper input | No natural final finding | Not fully audited | Defer |

Scope locked to **one mechanism: missing named-result bindings in the Go usage
environment**. Missing links and alias-shadow false links are two consequences
of that same omission, resolved by the same one-line change per engine.
