# Benchmark method audit — techniques adopted, findings not copied

This audit was performed after the JSONC defect had already been discovered and verified.
Its purpose was to identify stronger ways to test *this* defect's consequences and to make
the evidence independently reproducible. It does not rank submissions, reuse another
investigation's defect, or treat any benchmark result as evidence for ours.

## Issues and reproduction repositories reviewed

| Benchmark | Methodological feature worth learning from | Adaptation in this investigation | What was deliberately not copied |
|---|---|---|---|
| #395 | Offline replay of prepared artifacts; original/repeat/control/restored toggles; hashes; a concrete application consequence rather than a count alone | Kept the lexical source fixed while toggling only config parseability; preserved graph/bundle hashes and machine-readable deltas; added a concrete `ReactExtension.tsx` context case. The later strengthening makes the toggle explicit as A original, B comments removed, C restored, D in-memory correction, E stock restored | No hosted-model replay is relevant to the local resolver, so none is claimed |
| #426 | Original, each partial correction, combined correction, exact restoration, and negatives recorded against unchanged fingerprints/thresholds | Adapted the sequencing discipline—not the selector finding—to separate comments-only restoration (B) from parser-only restoration (D), require the failure to return at C/E, and keep missing/unconfigured/external specifiers negative in every state | Its Business Risk identifiers, fixture, and result are unrelated and were not reused |
| #409 | Verified installed sources against wheel `RECORD` hashes; replayed saved intermediates; used a narrow enforcement control; reconstructed a customer artifact byte-for-byte | Verified the two engine files against the 0.3.15 wheel record (see `tsconfig-jsonc/ARTIFACT_MANIFEST.md`); used a narrow in-memory parse correction while leaving the rest of resolution unchanged | We did not imply byte reconstruction of hosted output; our claim stops at local graph/context artifacts |
| #388 + `aayush-t-exe/unvibecode-pem-repro` | Semantically matched bug/control fixtures; no-API probe of the actual intermediate request; pinned public-code checks; shipped-vs-proposed implementation compared through the real code path; deterministic evidence separated from variable hosted outcomes | Compared the actual exported `selections.jsonl`/chunks, not only graph-edge counts; used pinned lexical and ng-matero trees; ran the correction through the shipped resolver object | Hosted outcome frequencies are not used because this defect is fully local and deterministic at the tested stages |
| #416 + `Aameen-badrul/Unvibecode-reexport-repro` | The language runtime itself supplies the expected answer; four-file cloneable fixture; deletion control; impact expressed as concrete public API usage | Used TypeScript 5.9.3—both `tsc --showConfig` and the compiler API—as the independent authority for JSONC validity and representative module targets; retained tiny assertion fixtures | No Python-runtime analogy or unrelated symbol-linker finding was imported |
| #378 | Forced the environmental failure rather than hoping it recurs; separated download failure from graph correctness; measured context loss | Added a clean GitHub Actions environment and made `ci_cli_comparison.py` return a distinct exit 2 when extraction is unavailable; grammar failure is never counted as JSONC evidence | The sandbox grammar shim remains explicitly disclosed for local large-repo runs; it is not passed off as a vanilla installation |
| #306 | Joined selected `chunk_id`s to chunk contents; used boundary controls; stated which scope/outcome was *not* established | Compared all common lexical selection rows and scopes; classified direct verified dependencies as recovered, present in both, omitted in both, or present only as-is; retained a chunk-level representative case | We did not infer that every missing edge changes context—the exhaustive join showed hundreds did not |
| `Shashank-VK/unvibecode-stem-fallback-repro` (Cohort 2) | Separate control/bug/monorepo shapes; deterministic reruns; contradiction sought across product outputs; compact captured evidence | Preserved distinct strict/JSONC/no-alias controls; compared resolver state, Stage-1 graph, bundle connections, unresolved records and selections rather than relying on one view | Its false-edge mechanism and examples are unrelated and were not reused |

## Consequences of the audit

The benchmark review changed the investigation in five material ways:

1. **Downstream proof became the primary test.** Edge loss was no longer assumed to mean
   context loss; exported selections were compared exhaustively.
2. **The lexical count was re-derived with TypeScript `paths` semantics.** The earlier
   prefix classifier was treated as a hypothesis, not as an oracle.
3. **Reproduction moved into clean CI.** A normal pinned install now exercises the
   unified `verify.py` entry point, TypeScript fixture acceptance, and minimal CLI path.
   The PR gate proves that the raw post-fix regression fails only for the exact
   documented JSONC symptom; that raw regression remains an explicitly manual post-fix
   workflow rather than a misleading red PR check.
4. **One independent real repository was added.** ng-matero tests whether the mechanism
   generalizes beyond lexical's unusually large exact-mapping table.
5. **Causality is reversible at two levels.** The A/B/C/D/E intervention is
   asserted at resolver level on both shipped engine copies and, in clean CI,
   through actual Fast Lane graph/context artifacts on a minimal repository.
   A separate in-memory-corrected lexical Fast Lane run checks whether the
   diagnostic parser alone recovers the real exported context.

The locked pre-benchmark strategy in `INDEPENDENT_STRATEGY.md` is unchanged.
