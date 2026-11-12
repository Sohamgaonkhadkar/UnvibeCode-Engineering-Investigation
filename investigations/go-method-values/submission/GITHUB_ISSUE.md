# [Bug] Go method values — typed callback references lose method-definition links and focused context

## 1. Problem summary

Three ordinary **0.4.0 client** reviews of the complete pinned public go-redis tree reproduce eight targeted missing method links and four missing implementations in both focused scopes. Receiver-preserving wrappers expose all eight links and all four bodies; no-method callbacks expose none. The client's six Python source files were checked byte-for-byte against the official published wheel.

A Go method value such as `callback := s.Save` does not produce a relationship to `Store.Save` in UnvibeCode 0.3.15 even when `s *Store` is explicitly declared. The corresponding direct call `s.Save()` is resolved. On a real go-redis checkout, this drops callback implementations from per-file focused context.

This is a missing **method reference**, not evidence that merely forming a method value executes the method.

## 2. Test environment

- **Affected product:** official `unvibecode==0.4.0` client, observed hosted code-map output; inspectable `0.3.15` Fast Lane and Normal Lane engines for root cause/correction
- **Local validation:** Python 3.12+/Go (Linux and Windows CI); original investigation on Windows, Python 3.14.5, Go 1.27.3
- **Public repository:** [redis/go-redis](https://github.com/redis/go-redis), pinned at [`5cba5e182946cf18a757718938bc43910e589466`](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466)
- **Version scope:** three full-public-repository 0.4.0 captures on 12 November; 0.3.15 source-level correction and independent MySQL-driver replication. Hosted backend revision is not exposed.
- **Independent repository:** [go-sql-driver/mysql](https://github.com/go-sql-driver/mysql/tree/4cdf75e9037ffccf63a981d10f5c2e669edbfc49), pinned at `4cdf75e9037ffccf63a981d10f5c2e669edbfc49`; both installed 0.3.15 engines and Go compiler oracle.

## 3. Steps to reproduce

Clone the [reproducible investigation](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/fc632c9340057296053f0bdd1ca6b9db4097042b) at the immutable verified commit below. Run these commands in a new working directory:

```sh
git clone https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation.git
cd UnvibeCode-Engineering-Investigation
git checkout fc632c9340057296053f0bdd1ca6b9db4097042b
python -m pip install -r investigations/go-method-values/reproduction/requirements.txt
python investigations/go-method-values/reproduction/verify.py --work ci-logs/minimal --output ci-logs/minimal.json
git clone https://github.com/redis/go-redis.git .local-go-investigation/redis
git -C .local-go-investigation/redis checkout 5cba5e182946cf18a757718938bc43910e589466
python investigations/go-method-values/reproduction/verify.py --repo .local-go-investigation/redis --work ci-logs/redis --output ci-logs/redis.json
```

Prerequisites: Python 3.12+, Git and Go on PATH (CI uses Go 1.27.3). The requirements deliberately pin the inspectable 0.3.15 engine; do not replace it with the hosted-only 0.4.0 client for this source-level experiment.

The script uses installed engine code, compiling Go fixtures, passing/negative controls, a transient correction and restoration. Inspect `ci-logs/redis.json` and the emitted actual context ZIPs. The [Go compiler oracle](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/fc632c9340057296053f0bdd1ca6b9db4097042b/investigations/go-method-values/reproduction/compiler_oracle.go) independently checks method owners and definition locations.

For the current-version public-repository observation, replay the actual downloaded ZIPs offline:

```sh
python investigations/go-method-values/reproduction/check_current_public.py --output ci-logs/current-public.json
```

The [current A/B/C artifacts and replay](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/codex/track1-final-evidence/investigations/go-method-values/evidence/current-public-0.4.0) and [full reproduction/audit](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/codex/track1-final-evidence/investigations/go-method-values/FINAL_EVIDENCE_AUDIT.md) contain separate commands for fresh official-client reviews, public Go tests, independent replication and receiver boundaries. These additions require the evidence branch or its pinned commit, rather than the earlier historical reproduction checkout above.

## 4. Expected behavior

A known receiver's bound method value should preserve a statically justified link to its method definition as a **reference**. Go's [method-value specification](https://go.dev/ref/spec#Method_values) distinguishes formation of a bound method value from calling that value.

## 5. Actual behavior

For `callback := s.Save; callback()`, the stock extractor emits no `Save` usage, and a focused selection can omit `store.go`. Rewriting the local fixture to `callback := func() { s.Save() }` restores the dependency. The reference correction restores the original source's dependency; reverting the correction reproduces the omission. All five fixture states compile and pass.

**Current 0.4.0 public-source comparison:** A is original source; B substitutes eight direct-call wrappers that freeze their pointer receiver at formation; C uses no-op callbacks as a deliberately non-equivalent negative control. The downloaded source differs in exactly eight lines across three files. Target implementations and upload inventories are identical.

| Measure | A: original | B: bound wrapper | C: no-method control |
|---|---:|---:|---:|
| Targeted method relationships | 0 | 8 | 0 |
| Complete target bodies in each of Optimal/Wider | 0/4 | 4/4 | 0/4 |
| All exported relationships | 12,189 | 12,204 | 12,189 |

B adds eight method-call and seven coarse file-import records, with no normalized relationships removed. C's normalized inventory equals A's. All states upload the same 619 paths and omit `go.mod`; the targeted methods are same-package, isolating this matched observation from #662 without repairing module imports.

All three code-understanding lanes completed. Overall status is PARTIAL because business analysis is SKIPPED_LARGE_REPOSITORY. One initial A connection failure produced no artifacts; one later attempt completed. No changed business-risk verdict is claimed.

**Historical reference correction:** Both graph copies on unchanged go-redis yield **23,448 → 23,527 → 23,448** relationships. The 79 additions comprise **13 production method references** (six file pairs) and **66 test references**. No stock relationships are removed.

## 6. Evidence

The [technical investigation](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/cbdc618e320959de138e9bba43920459c3f168e5/investigations/go-method-values/README.md) documents source digests, both engine copies, the reversible experiment, independent type checks, and actual exported ZIP comparisons.

- Go type checker: **13/13** exact production source-position/receiver/definition identities verified in clean Linux CI.
- Seven source-specific production callee identities checked line-by-line in actual Optimal and Wider selections.
- **Five of seven** complete implementations newly recovered in both scopes; the other two remain bounded exceptions.
- Stock ordinary CLI and local-pipeline exports agree: **11,284 chunks, 24,191 exported relationship records, 536 selections**.

Detailed records: [verification JSON](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/fc632c9340057296053f0bdd1ca6b9db4097042b/investigations/go-method-values/evidence/verification.json), [compiler oracle](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/fc632c9340057296053f0bdd1ca6b9db4097042b/investigations/go-method-values/reproduction/compiler_oracle.go), [CI provenance](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/fc632c9340057296053f0bdd1ca6b9db4097042b/investigations/go-method-values/evidence/ci-snapshot.json).

The [current-client replay](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/fc632c9340057296053f0bdd1ca6b9db4097042b/investigations/go-method-values/reproduction/check_current_client.py) checks two captured 0.4.0 ZIPs: original callback 0 method links/no store.go; matched wrapper 1 method link/store.go at Optimal and Wider. Only that expression differs in recovered source text. Code understanding completed; both overall reviews were PARTIAL because business analysis failed.

Offline replay of the preserved current-client results (no service request required):

```sh
python investigations/go-method-values/reproduction/check_current_client.py --output ci-logs/current-client.json
```

Additional verification records on the evidence branch:

- `evidence/current-public-verification.json`: current A/B/C source-line checks, relationship deltas and exact body coverage.
- `evidence/mysql-replication.json` and `mysql-compiler.json`: both engines produce 656 → 658 → 656 relationships; two cross-file methods independently verified by Go; both target bodies absent → complete → absent in each scope.
- `evidence/public-go-tests.json`: the same two mock-backed MultiDB routing/failover tests pass for A and B; C compiles without running tests; four mock-backed MySQL packet tests pass.
- `evidence/boundaries.json`: both engine copies preserve package functions and concrete receiver identity, do not promote function-valued fields, and do not invent a concrete implementation for an interface reference. Runtime tests distinguish formation from execution and check a saved receiver after variable reassignment.

## 7. Impact and scope

Focused context for MultiDB callback initialization can omit `multidbCore.processPipeline`; ring fan-out context can omit `Ring.ForEachShard`. The source is still present in the **complete** repository ZIP; the observed defect is specifically an omission of method implementation evidence from selected focused context.

Four source-backed maintenance questions quantify current focused-context loss:

| Question / required implementation | A → B → C nonblank lines, both scopes |
|---|---|
| FD retry execution bound / `ClusterClient.processPipelineRetries` | 0/72 → 72/72 → 0/72 |
| Concurrent master fan-out and error propagation / `ClusterClient.ForEachMaster` | 0/31 → 31/31 → 0/31 |
| Down-shard filtering / `Ring.ForEachShard` | 0/32 → 32/32 → 0/32 |
| MultiDB retry-setting delegation / `multidbCore.processPipeline` | 0/3 → 3/3 → 0/3 |

The [question-to-source audit](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/codex/track1-final-evidence/investigations/go-method-values/evidence/developer-impact.json) retains implementation excerpts and verifies corresponding historical correction exports. These results establish missing answer-relevant context, not demonstrated incorrect AI answers. Independent MySQL replication adds two real same-mechanism callbacks; it is an installed 0.3.15 result, not a hosted MySQL review.

A budget-only control explains the two remaining bodies: the default MultiDB selections fill 44,997/45,000 and 74,999/75,000 tokens; increasing only each scope’s maximum to 200,000 makes both bodies complete. The primary 5/7 figure keeps original budgets. No hosted business-risk verdict change, arbitrary indirect-call resolution, ecosystem prevalence, or Go runtime bug is claimed.

## 8. Suspected cause / suggested fix

`TreeSitterAstAdapter._collect_go_usages` handles non-call `selector_expression` nodes with `package_selector`. For a known local qualifier, that helper returns without emitting a typed usage, although input parameters correctly populate the receiver environment.

Inspected 0.3.15 source locations (source digests are recorded in the verification JSON):

| Stage | Fast Lane `00a` | Normal graph `01` |
|---|---|---|
| `_collect_go_usages` | line 981 | line 939 |
| `package_selector` | line 1127 | line 1085 |
| Non-call selector branch | line 1292 | line 1250 |
| `_resolve_go_usages` | line 2448 | line 2405 |

A tested reference correction emits `method_reference` for typed local selector values, passes it through `ShipReadyV2DeepGraphBuilder._resolve_go_usages`, and exports `imports_symbol` / `go_method_value` relationships. Unresolved fields remain unpromoted. Both installed methods are restored after each experiment, with source hashes unchanged.

## 9. Duplicate check

A complete historical snapshot of 485 open/closed issues through #596 was reviewed, followed by #597. On **12 November 2026**, the refreshed audit covers **570 open/closed issue records through #682** (567 nonempty bodies, 3 empty), plus nearest-report comments. No matching typed method-value mechanism was identified. The [audit and digests](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/fc632c9340057296053f0bdd1ca6b9db4097042b/investigations/go-method-values/evidence/issue-audit-2026-11-12.json) preserve the search scope.

Closest distinct reports: [#360](https://github.com/FinanceFlash/unvibecode/issues/360) (wrong receiver's target for a resolved call); [#415](https://github.com/FinanceFlash/unvibecode/issues/415) (factory-expression receiver); [#573](https://github.com/FinanceFlash/unvibecode/issues/573) (interface dispatch); [#596](https://github.com/FinanceFlash/unvibecode/issues/596) (named-result binding); [#625](https://github.com/FinanceFlash/unvibecode/issues/625) (unresolved Go diagnostics not exported); [#662](https://github.com/FinanceFlash/unvibecode/issues/662) (0.4.0 uploader omits `go.mod`).

Immediately before publication on 12 November, an all-pages REST refresh reviewed **603 issue records through #715** (600 nonempty bodies, 3 empty). No matching extraction mechanism was identified. [#710](https://github.com/FinanceFlash/unvibecode/issues/710) concerns promoted calls through embedded structs; this reproducer uses a method declared directly on its concrete receiver, with no embedding. [#709](https://github.com/FinanceFlash/unvibecode/issues/709) concerns primary-file context expansion, not the missing typed method reference. The [pre-publication inventory and body digests](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/a257781/investigations/go-method-values/evidence/publication-duplicate-check.json) record the scope of that check.

The earlier JSONC investigation matched [#451](https://github.com/FinanceFlash/unvibecode/issues/451) and is **not** the subject of this report. Duplicate checking is time-bound; the inventory above records the pre-publication check.
