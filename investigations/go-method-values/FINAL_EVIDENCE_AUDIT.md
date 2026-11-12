# Evidence audit: current product, independent replication and developer impact

## Executive result

The unmodified UnvibeCode **0.4.0 client** reproduces the typed-method-value omission on the complete pinned public go-redis tree. Original source has no links for eight targeted expressions and no complete bodies for their four target methods in either focused scope. Receiver-preserving wrappers expose all eight links and all four bodies. No-method callbacks expose none. The independent MySQL-driver replication establishes the same extraction mechanism in both inspectable 0.3.15 engines.

## Experiments and outcomes

| Experiment | Completion and exact outcome | Evidence |
|---|---|---|
| Original go-redis, first 0.4.0 attempt | Connection error; no returned job ID or artifacts. No completed run claimed for that attempt. | Sanitized attempt record in capture manifest |
| Original go-redis, subsequent attempt (A) | Code understanding completed: 11,263 chunks, 12,189 relationships, 532 selections; 0/8 targeted links, 0/4 target bodies complete in each scope | [A ZIP](evidence/current-public-0.4.0/A.zip) |
| Bound wrapper control (B) | Code understanding completed: 11,263 chunks, 12,204 relationships, 532 selections; 8/8 links, 4/4 bodies complete in each scope | [B ZIP](evidence/current-public-0.4.0/B.zip) |
| No-method negative control (C) | Code understanding completed; normalized relationship inventory equals A; 0/8 targeted links and 0/4 target bodies complete in each scope | [C ZIP](evidence/current-public-0.4.0/C.zip) |
| Public Go behavior checks | A and B each pass the same two mock-backed MultiDB routing/failover tests. C compiles with no tests executed; C deliberately changes behavior. | [Commands/results and excerpts](evidence/public-go-tests.json) |
| Independent full MySQL-driver replication | Both engines: 656 → 658 → 656 relationships, two gained cross-file production references, no original edges removed. Both bodies absent → complete → absent in both scopes. | [Replication](evidence/mysql-replication.json) |
| Independent MySQL type checker | 2/2 exact source positions, owners, target files and definition spans verified | [Compiler results](evidence/mysql-compiler.json) |
| MySQL behavior controls | Four mock-backed packet tests pass without a MySQL server | [Go tests](evidence/public-go-tests.json) |
| Receiver/negative-control regressions | Both engine copies pass local/bound receivers, same-named methods, package functions, function-valued fields, uncertain interfaces, formation/invocation and restoration controls | [Boundary results](evidence/boundaries.json) |
| Developer questions | Four maintenance questions mapped to exact method bodies and original-budget focused exports. Current A/B/C independently confirms the same four coverage outcomes. | [Source-backed questions](evidence/developer-impact.json) |

## Current-version controls and interpretation

The inputs originate from redis/go-redis commit `5cba5e182946cf18a757718938bc43910e589466`. The original checkout remains unchanged. B and C each change exactly eight lines in three disposable files. The replay checks every recovered source line across all three downloads, and rejects unexplained differences. Target method implementations are identical.

B evaluates each pointer receiver at callback formation and returns a closure forwarding the same arguments and return value. This preserves the saved receiver even if the original variable later changes. The formation/invocation regression executes both forms and verifies that formation performs no method call. The public MultiDB tests additionally exercise the changed pipeline callback. These controls do not constitute exhaustive runtime equivalence testing of every fan-out path.

All states upload the same 619 paths. The unmodified client's upload inventory excludes `go.mod` in every state. The selected methods are in their callers' package; the eight method relationships are therefore compared without changing module metadata. This isolates the observation from #662, but does not fix or quantify unrelated module-import loss.

The 15 normalized additions in B consist of eight `method_call` records and seven `file_import` records. No normalized relationships are lost. Comparison preserves source/target files and lines, relationship kind, symbol and confidence; edited-source chunk IDs are not treated as stable identities. C's inventory equals A's.

The hosted backend revision is not exposed. No hosted engine correction is applied or claimed. The established source-level correction remains the inspectable 0.3.15 experiment; B is a source control for the current observable symptom.

All three hosted reviews are **PARTIAL**, with FAST_LANE **COMPLETED** and FULL_ANALYSIS **SKIPPED_LARGE_REPOSITORY**. Business-risk output is not evidence for this finding. No model-answer failure or improved answer accuracy is asserted.

## Reproduce the offline current-version audit

From the repository root, Python 3.12+ is sufficient; no service request is made:

```sh
python investigations/go-method-values/reproduction/check_current_public.py --output ci-logs/current-public.json --focused-output ci-logs/focused-current.zip
```

The three original downloaded ZIPs contain `connections.jsonl`, `chunks.jsonl` and `selections.jsonl`. [Capture metadata](evidence/current-public-0.4.0/manifest.json) records source/client hashes, upload counts and sanitized lane status. [Focused extracts](evidence/current-public-0.4.0/focused-selections.zip) contain the actual selected chunks and scope metadata for `himport_cluster.go` at both Optimal and Wider in every state. These are documented extractions from the downloaded ZIPs, not browser-generated exports.

## Reproduce new hosted A/B/C reviews

These commands upload public source and require the hosted service. They are not part of CI. Keep the historical engine environment separate from the client environment.

1. Clone go-redis and pin it to `5cba5e182946cf18a757718938bc43910e589466`.
2. Prepare disposable copies with a fresh output directory:

```sh
python investigations/go-method-values/reproduction/prepare_current_public.py --repo /path/to/redis --work /path/to/fresh-inputs
```

3. With Go on PATH, compile and check the controls:

```sh
go -C /path/to/fresh-inputs/A test -mod=readonly -count=1 -run '^(TestMultiDBPipelineRoutesToActive|TestMultiDBPipelineFailoverRetry)$' .
go -C /path/to/fresh-inputs/B test -mod=readonly -count=1 -run '^(TestMultiDBPipelineRoutesToActive|TestMultiDBPipelineFailoverRetry)$' .
go -C /path/to/fresh-inputs/C test -mod=readonly -run '^$' .
```

4. In a separate environment containing the official `unvibecode==0.4.0` client, run each input once with a distinct destination:

```sh
python -m unvibecode review --repository /path/to/fresh-inputs/A --output /path/to/results-A --no-open-browser
python -m unvibecode review --repository /path/to/fresh-inputs/B --output /path/to/results-B --no-open-browser
python -m unvibecode review --repository /path/to/fresh-inputs/C --output /path/to/results-C --no-open-browser
```

Use the downloaded repository-context ZIPs for comparison. Backend changes, availability or quota may change later observations. Do not substitute local 0.3.15 pipeline output for a hosted capture.

## Reproduce independent replication and boundaries

Use the pinned historical dependencies in `reproduction/requirements.txt`, with Git and Go on PATH:

```sh
git clone https://github.com/go-sql-driver/mysql.git ci-logs/mysql
git -C ci-logs/mysql checkout 4cdf75e9037ffccf63a981d10f5c2e669edbfc49
python investigations/go-method-values/reproduction/replicate_mysql.py --repo ci-logs/mysql --work ci-logs/mysql-replay --output ci-logs/mysql.json
go build -o ci-logs/compiler-oracle investigations/go-method-values/reproduction/compiler_oracle.go
ci-logs/compiler-oracle -repo ci-logs/mysql -package . -cases ci-logs/mysql-compiler-cases.json -output ci-logs/mysql-compiler.json
go -C ci-logs/mysql test -mod=readonly -count=1 -run '^(TestReadPacketSingleByte|TestReadPacketWrongSequenceID|TestReadPacketSplit|TestWriteExecutePacketValidatesArgsBeforeWriting)$' .
python investigations/go-method-values/reproduction/check_boundaries.py --work ci-logs/boundaries --output ci-logs/boundaries.json
```

On Windows, use an `.exe` suffix for the compiler executable. The [workflow](../../.github/workflows/go-method-values.yml) runs boundary checks and current-artifact replay on Linux and Windows; Linux additionally performs both public-repository experiments, compiler oracles and public Go controls. Hosted reviews are never run in CI.

## CI conclusions and report provenance

[Linux and Windows CI passed](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/43265840641) at `edb1aa3a7c744b8c396eea34282aef87dfbdd913`. [Per-step conclusions](evidence/final-ci.json) record the exact scope: both OS jobs run compiling fixture/boundary checks and both current-client replays; Linux additionally runs go-redis correction exports, the capacity/question audits, 13/13 go-redis and 2/2 MySQL compiler identities, public A/B/C compilation/behavior checks and independent MySQL replication. No live service request runs in CI.

[PR #5](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/5) contains the new artifacts, independent verification scripts, evaluator-facing reports and the expanded nine-section copy of [official issue #716](https://github.com/FinanceFlash/unvibecode/issues/716). The [13 November pre-update duplicate refresh](evidence/issue-update-duplicate-check-2026-11-13.json) records the final originality refresh.
