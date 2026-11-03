# Exhaustive symbol-definition evidence audit — lexical exported bundles

## Purpose

The six-question answerability audit is representative and intentionally
concrete. This companion scales the final-artifact question across every
verified lost lexical relationship: when a source file imports a symbol
through a configured alias, does its exported Optimal/Wider selection contain
a recognizable declaration/export line from the file that defines that
symbol?

Script: [`../../reproduction/symbol_evidence_audit.py`](../../reproduction/symbol_evidence_audit.py)

## Method

1. Start with the 4,256 independently TypeScript-verified lost relationship
   rows.
2. For each source/specifier/line, read the comment-stripped control graph's
   per-import `symbol_resolutions` to identify imported symbols and their
   defining files. This produced **10,715 candidate source-specific symbol
   tasks**.
3. Search the full control bundle for a recognizable declaration/export
   pattern for each symbol in its defining file. **10,703 tasks** are
   eligible; the other 12 are excluded rather than counted as failures.
4. For the as-is, comment-stripped-control, and in-memory-corrected bundles,
   join each importing source's Optimal/Wider `selections.jsonl` entry to
   `chunks.jsonl`, restrict the text to chunks from the defining file, and
   require the same declaration/export pattern to be present.

The eligible tasks cover **1,239 importing source files** and **182 defining
files**. Counts below are *source-specific imported-symbol instances*, not
unique symbols and not LLM answers. Repeated imports of the same symbol by
different source files are separate context-availability observations.

The control graph supplies the symbol-to-defining-file mapping; the
underlying module relationships themselves are the independently
TypeScript-verified rows. The audit therefore measures exported
definition/export evidence, complementing—not replacing—the six
implementation-line maintenance tasks in `ANSWERABILITY_AUDIT.md`.

## Clean-CI result

Run:
https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41639781771

| Scope | As-is definitions available | Control | Corrected | Recovered vs as-is (control/corrected) |
|---|---:|---:|---:|---:|
| Optimal (radius 1) | 726 / 10,703 | 8,826 | 8,826 | **8,163 / 8,163** |
| Wider (radius 2) | 711 / 10,703 | 9,883 | 9,883 | **9,182 / 9,182** |

At Optimal, the state breakdown is 663 available in both, 8,163 recovered,
63 available only as-is, and 1,814 available in neither. At Wider, it is
701 in both, 9,182 recovered, 10 only as-is, and 810 in neither. In
particular, the audit does **not** claim that every direct dependency or
symbol becomes available after correction; unrelated selection limits remain.

The complete `symbol_evidence_audit.json` and per-task
`symbol_evidence_details.jsonl` are in artifact
`lexical-clean-environment-evidence` (ID `13231264139`, SHA-256
`0ebce5ec4a3e369358ec144d8668e221f2ce23c82e8bf0474cf9e10d791c7765`).
The workflow now asserts these exact counts rather than only requiring a
positive recovery.
