# Provisional research: narrative text qualifies source proofs

**Do not submit as original yet.** Upstream [#437](https://github.com/FinanceFlash/unvibecode/issues/437)
distinguishes its own cause from an earlier report 34 about summary text. Its
linked 41–43 public evidence archive confirms that reference and includes a
source-only intervention in the scope checker, but not report 34's full draft.
No exact standalone issue-body match was found among 485 open/closed issues
through #596. That absence does not resolve this earlier public reference.

This candidate was independently screened before reading that reference. The
verified results remain useful research; eligibility is provisional. No issue
or form has been filed. Ordinary parsing candidates are being investigated.

## Verified result

UnvibeCode 0.3.15 `PathFacts.has_source_pattern()` searches `text_for_refs()`,
which joins model-written `evidence_summary` with cited source. The compiler's
citation validator preserves the summary: `VALID` validates an interval, not
the narrative's truth. Narrative text can therefore satisfy an operation proof.

The actual installed selector `main()` reads input files, builds proofs, scores,
deduplicates, invokes compiled selection, and writes its selected/gap JSON.
No scores or decisions are supplied by the test.

| Case | Stock | Source-only correction | Restored |
|---|---|---|---|
| SQLite write; blank/benign summary | Gap, 13 | Gap, 13 | Gap, 13 |
| Same source; summary denies `requests.get` | Selected, 17 | Gap, 13 | Selected, 17 |
| Unchanged LevelDB `DB.Put`; same negative summary | Selected, 17 | Gap, 13 | Selected, 17 |
| Source with `client.post(...)`; each summary | Selected, 17 | Selected, 17 | Selected, 17 |

The external-dependency proof becomes passed/`OBSERVED`, and the reporting
ceiling rises from `INVESTIGATION_HYPOTHESIS` to `EVIDENCE_BACKED_RISK`.
The latter is not `CONFIRMED_FLAW`. All 27 runs passed their expected outcomes.
Within each source case, prepared input bytes remain identical; normalized
objects differ only in `evidence_summary`. Installed source hashes are unchanged.
The SQLite fixture executes a real in-memory insert and verifies its row.
The `client.post` source is a lexical positive control, without network activity.

## Reproduce

```sh
python -m pip install -r investigations/risk-evidence-summary/reproduction/requirements.txt
git clone https://github.com/syndtr/goleveldb.git .local-go-investigation/goleveldb
git -C .local-go-investigation/goleveldb checkout 126854af5e6d8295ef8e8bee3040dd8380ae72e8
python investigations/risk-evidence-summary/reproduction/verify.py --repo .local-go-investigation/goleveldb --work ci-logs/risk --output ci-logs/risk-verification.json
```

[Verification](evidence/verification.json) records hashes and outcomes.
[Reference correction](solution/source_patterns.py) changes source-pattern
matching in memory and restores it in `finally`. Narrative remains available
for display. This does not solve comments/string literals matching within source.

Normalized nominations are controlled fixtures, not captured model replies.
The real compiler citation validator is exercised separately; no complete compiler
replay from a semantic reply or hosted final false finding is claimed. The public
LevelDB source is unchanged at the pinned commit, `leveldb/db_write.go:374–376`.
The verifier rejects a dirty/differently pinned checkout. No ecosystem frequency,
displaced genuine finding, or ranking position follows from these experiments.

The full issue-body audit and nearest-report comment checks are preserved in
[issue-audit.json](evidence/issue-audit.json). The report-34 lead remains unresolved.
