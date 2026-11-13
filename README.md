# UnvibeCode: typed Go callbacks lose implementation context

A reproducible Track 1 engineering investigation, with a reference correction and measured limits.

[![Go evidence](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/workflows/go-method-values.yml/badge.svg?branch=main)](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/workflows/go-method-values.yml)

**[Official issue #716](https://github.com/FinanceFlash/unvibecode/issues/716) · [Results](#measured-results) · [Why two bodies remain missing](#why-two-bodies-remain-missing) · [Reproduce](#reproduce) · [Evidence guide](#evidence-guide)**

> **Finding:** typed Go method values can lose their method-definition links and implementation context. Unmodified **0.4.0 client** runs on pinned go-redis show **eight targeted method links and four complete method bodies missing from original focused context**. Receiver-preserving wrappers expose all eight links and all four bodies; no-method controls expose none. Independent **0.4.0 MySQL-driver reviews also reproduce two missing links and two missing method bodies**, with all three review statuses complete. Source-level controls establish the mechanism and its boundaries.

## The defect

An explicitly typed receiver loses its implementation relationship when its method becomes a callback:

```go
func Run(s *Store) {
    callback := s.Save
    callback()
}
```

In the published 0.3.15 engine, a direct `s.Save()` emits a typed method usage. The non-call selector `s.Save` instead goes through `package_selector()`, which returns for known local variables. The receiver's correct type never reaches owner-aware method resolution.

![Stock extraction drops a known local callback reference; the correction preserves it and resolves its owner.](assets/go-method-values-flow.svg)

**Text alternative:** known receiver → non-call selector → stock package-only helper drops the reference → no method-definition edge. The correction preserves a typed reference and resolves its method owner.

The correction records a reference. Forming a method value does not invoke it; see [Go's method-value semantics](https://go.dev/ref/spec#Method_values).

## What was verified

| Verification layer | Scope and result |
|---|---|
| Root cause and reference correction | Installed UnvibeCode **0.3.15**, both shipped graph implementations |
| Harmless compiling controls | Stock, repeat, wrapper control, corrected, restored; package-value and function-field controls |
| Public-repository replication | Unchanged [redis/go-redis at `5cba5e182946cf18a757718938bc43910e589466`](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466) |
| Independent type check | **13/13** go-redis and **2/2** MySQL production source/receiver/definition identities verified by Go |
| Current-client check | Three **0.4.0** public go-redis captures on 12 November and three public MySQL-driver captures on 13 November (IST); original, bound wrapper and no-method controls |
| Independent repository | Pinned go-sql-driver/mysql: two missing links and two omitted bodies in three completed **0.4.0** reviews, plus the same mechanism in both inspectable **0.3.15** engines |
| Originality refresh | **626 other** open/closed issue records through **#739** before the evidence update (#716 excluded); historical nearest-report comments checked separately |

[PyPI lists 0.4.0 as the latest published release](https://pypi.org/project/unvibecode/) (checked 12 November 2026). The 0.4.0 hosted backend revision is not exposed. Source-level causal inspection and the 13-reference correction experiment belong to 0.3.15. The current-client comparison independently measures the same symptom on the complete pinned public go-redis checkout.

## Measured results

### Graph relationships on the public go-redis commit

Both 0.3.15 graph copies reproduce these results:

| Metric | Stock | Corrected | Restored |
|---|---:|---:|---:|
| Total relationships | 23,448 | **23,527** | 23,448 |
| Production references gained versus stock | 0 | **13** | 0 |
| Test references gained versus stock | 0 | 66 | 0 |
| Stock relationships removed | 0 | **0** | 0 |

**Stock** is the affected release. **Corrected** applies only the transient reference correction. **Restored** removes that correction and intentionally reproduces the original omission. Zeros in the delta rows are measured baselines, not missing results.

The 79 additions are 13 production references across six file pairs and 66 test references. They are not 79 proven runtime calls or application defects.

### Complete method bodies in focused context

A body counts as complete only when every required nonblank source line matches the actual selected code. These five targets have the same result at both Optimal and Wider:

| Caller → required method | Stock | Corrected | Restored |
|---|---:|---:|---:|
| `autopipeline_cluster_fd.go` → `ClusterClient.processPipelineRetries` | 0/72 | **72/72** | 0/72 |
| `himport_cluster.go` → `ClusterClient.ForEachMaster` | 0/31 | **31/31** | 0/31 |
| `himport_cluster.go` → `Ring.ForEachShard` | 0/32 | **32/32** | 0/32 |
| `multidb.go` → `multidbCore.processPipeline` | 0/3 | **3/3** | 0/3 |
| `osscluster_router.go` → `ClusterClient.ForEachMaster` | 0/31 | **31/31** | 0/31 |

Thus **5 of 7** distinct source-specific method definitions are newly recovered in each scope. The scopes share inputs and are not independent tasks. The complete-repository ZIP contains every source file throughout; the measured loss is in the selected focused context.

## Why two bodies remain missing

The [line-coverage and budget audit](investigations/go-method-values/evidence/context-selection-audit.json) makes these limits explicit:

| Target from `multidb.go` | Optimal: stock → corrected → restored | Wider: stock → corrected → restored |
|---|---|---|
| `multidbCore.process` | 0/215 → 0/215 → 0/215 | 215/215 → 215/215 → 215/215 |
| `multidbCore.processTxPipeline` | 0/135 → 0/135 → 0/135 | 0/135 → 0/135 → 0/135 |

The corrected export **does contain the resolved reference edges** for these methods. Its fixed-size selector still excludes their bodies: the saved MultiDB selections estimate **44,997/45,000** tokens at Optimal and **74,999/75,000** at Wider.

A controlled experiment leaves source, corrected graph, chunking and selection ranking unchanged and increases only one scope's maximum to 200,000 tokens. Both bodies then become complete in both scopes. This diagnoses a separate selection-capacity limit. **The main 5/7 result still uses the original budgets.** Raising the diagnostic budget is not presented as a production fix.

The reference correction repairs extraction. The capacity experiment separately measures whether resolved implementations fit into focused context.

## Current 0.4.0: public-repository comparison

The official unmodified client analyzed three disposable copies of the same pinned go-redis tree. **A** is original source. **B** changes eight method-value expressions in three files to direct-call closures that freeze each pointer receiver at formation. **C** replaces those expressions with no-op callbacks: it is a deliberately different negative control, not a behavior-equivalent implementation.

The [offline artifact audit](investigations/go-method-values/evidence/current-public-verification.json) checks every recovered source line, the exact eight edits, identical target implementations, and identical upload paths across all three downloads.

| Measure | A: original | B: bound wrapper | C: no-method control |
|---|---:|---:|---:|
| Selected method relationships | 0 | **8** | 0 |
| Complete target bodies, Optimal and Wider | 0/4 | **4/4** | 0/4 |
| All exported relationships | 12,189 | 12,204 | 12,189 |
| Chunks / file selections | 11,263 / 532 | 11,263 / 532 | 11,263 / 532 |

B adds eight `method_call` records and seven coarse `file_import` records, with no normalized relationships lost. C's normalized relationships equal A's. B is an observational control, not a hosted engine correction; its calls occur inside callbacks, not at callback formation.

All states upload the same 619 paths and omit `go.mod`. The eight target methods are in the same package as their callers, so the matched comparison isolates this symptom from [#662](https://github.com/FinanceFlash/unvibecode/issues/662). It does not repair or measure the missing module dependencies.

Code understanding completed for all three runs. Overall status is **PARTIAL** because business analysis was **SKIPPED_LARGE_REPOSITORY**. One initial A attempt returned a connection error without artifacts; one subsequent attempt completed. No changed business-risk verdict is claimed. [Actual ZIPs and sanitized capture metadata](investigations/go-method-values/evidence/current-public-0.4.0) and [replay script](investigations/go-method-values/reproduction/check_current_public.py) preserve the results. The earlier [minimal 0.4.0 comparison](investigations/go-method-values/evidence/latest-client-verification.json) remains a separate control.

## Measured developer impact

Each row identifies implementation evidence needed to answer a real maintenance question. Fractions count exact matching nonblank method-body lines in both Optimal and Wider.

| Developer question | Required method | A | B | C |
|---|---|---:|---:|---:|
| How many executions can the full-duplex reroute retry bound allow? | `ClusterClient.processPipelineRetries` | 0/72 | **72/72** | 0/72 |
| Does HIMPORT master fan-out run concurrently, wait, and propagate an error? | `ClusterClient.ForEachMaster` | 0/31 | **31/31** | 0/31 |
| Does ring HIMPORT fan-out skip down shards? | `Ring.ForEachShard` | 0/32 | **32/32** | 0/32 |
| Which retry setting does the MultiDB pipeline hook forward? | `multidbCore.processPipeline` | 0/3 | **3/3** | 0/3 |

For the last question, the recovered implementation is:

```go
func (c *multidbCore) processPipeline(ctx context.Context, cmds []Cmder) error {
    return c.processPipelineRetries(ctx, cmds, c.opts.CommandRetries)
}
```

This establishes delegation of `CommandRetries`; it does not by itself establish the entire retry algorithm. [Question-to-source evidence](investigations/go-method-values/evidence/developer-impact.json) also checks the historical stock → corrected → restored exports. **These measurements establish missing answer-relevant source, not incorrect AI answers.** No model-answer accuracy experiment is claimed.

## Independent current-version replication: MySQL driver

The official 0.4.0 client analyzed the complete [go-sql-driver/mysql tree at `4cdf75e9037ffccf63a981d10f5c2e669edbfc49`](https://github.com/go-sql-driver/mysql/tree/4cdf75e9037ffccf63a981d10f5c2e669edbfc49). A is original source. B freezes the receiver and forwards the same byte slice and `(int, error)` result for `mc.readWithTimeout` and `mc.writeWithTimeout`. C substitutes no-op callbacks as a deliberately different negative control.

Only two lines in `packets.go` differ. Target implementations and the 68 uploaded paths are identical across all states; all omit `go.mod`. These are same-package methods. All three hosted reviews report overall **COMPLETE**, FAST_LANE **COMPLETED**, and FULL_ANALYSIS **COMPLETED**. The omission therefore also occurs within completed code/workflow reviews, independently of go-redis's size-related skip. No risk-findings output is listed in these captures; COMPLETE is the service status, not a claim that every report lane produced an output.

| Measure | A: original | B: bound wrapper | C: no-method control |
|---|---:|---:|---:|
| Targeted timeout-method links | 0 | **2** | 0 |
| `mysqlConn.readWithTimeout` body, both scopes | 0/9 | **9/9** | 0/9 |
| `mysqlConn.writeWithTimeout` body, both scopes | 0/9 | **9/9** | 0/9 |
| All exported relationships | 814 | 817 | 814 |
| Chunks / selections | 542 / 60 | 542 / 60 | 542 / 60 |

B adds two method-call records and one coarse file-import record, losing no normalized relationships. C's normalized inventory equals A's. **`connection.go` is present in every audited scope, including those missing both method bodies.** Checking filenames alone would miss the defect.

A developer investigating how packet reads/writes apply configured deadlines needs these implementations: they inspect `ReadTimeout`/`WriteTimeout`, conditionally set the connection deadline, propagate a deadline-setting error, then perform the network operation. The [downloaded ZIPs and statuses](investigations/go-method-values/evidence/current-mysql-0.4.0) and [exact replay results](investigations/go-method-values/evidence/current-mysql-verification.json) establish context availability, not model-answer correctness or a changed business-risk verdict.

Six mock-backed packet tests pass on both A and B, including reads, long-data writes, and error recovery. C compiles only. The existing independent [Go compiler oracle](investigations/go-method-values/evidence/mysql-compiler.json) verifies both original target identities. Historical 0.3.15 correction controls remain **656 → 658 → 656** relationships, with both bodies **0/9 → 9/9 → 0/9** at original budgets in each scope. Their verifier now asserts these exact outcomes rather than merely recording coverage.

## Reproduce

From this checkout, with Python 3.12+, Git and Go on PATH (CI uses Go 1.27.3):

```sh
python -m pip install -r investigations/go-method-values/reproduction/requirements.txt

# Compiling fixture, both parsers, correction and restoration
python investigations/go-method-values/reproduction/verify.py --work ci-logs/minimal --output ci-logs/minimal.json

# Unchanged public source and actual focused exports
git clone https://github.com/redis/go-redis.git .local-go-investigation/redis
git -C .local-go-investigation/redis checkout 5cba5e182946cf18a757718938bc43910e589466
python investigations/go-method-values/reproduction/verify.py --repo .local-go-investigation/redis --work ci-logs/redis --output ci-logs/redis.json

# Independent compiler oracle
go build -o ci-logs/compiler-oracle investigations/go-method-values/reproduction/compiler_oracle.go
ci-logs/compiler-oracle -repo .local-go-investigation/redis -package . -cases ci-logs/redis-compiler-cases.json -output ci-logs/compiler-results.json

# Replay current full-public-repository artifacts; no network or service required
python investigations/go-method-values/reproduction/check_current_public.py --output ci-logs/current-public.json

# Replay the independent completed MySQL reviews
python investigations/go-method-values/reproduction/check_current_public.py --artifacts investigations/go-method-values/evidence/current-mysql-0.4.0 --output ci-logs/current-mysql.json

# Receiver, interface, field and callback-formation boundaries
python investigations/go-method-values/reproduction/check_boundaries.py --work ci-logs/boundaries --output ci-logs/boundaries.json

# Explain line coverage and the separate capacity limit
python investigations/go-method-values/reproduction/explain_context.py --repo .local-go-investigation/redis --artifacts ci-logs/redis/public/00a --verification ci-logs/redis.json --budget-control-work ci-logs/budget-control --output ci-logs/context-audit.json
```

On Windows, give the compiler executable an `.exe` suffix. First-use parser setup needs network access. Setup failures fail verification. Public Redis tests are compiled in CI; server-dependent integration tests are not executed.

The [workflow](.github/workflows/go-method-values.yml) preserves logs, compiler results and actual exported ZIPs. A green affected-version verification means the defect and controls reproduced as expected; it does not mean stock UnvibeCode was fixed.

## Evidence guide

| Evaluation area | Evidence |
|---|---|
| Technical depth and root cause | [Source stages and causal controls](investigations/go-method-values/ROOT_CAUSE.md), [reference correction](investigations/go-method-values/solution/method_values.py) |
| Reproducibility | [Compiling fixtures and public-project verifier](investigations/go-method-values/reproduction/verify.py), [recorded measurements](investigations/go-method-values/evidence/verification.json) |
| Developer impact | [Full technical report](investigations/go-method-values/README.md), [exact focused-context coverage and capacity control](investigations/go-method-values/evidence/context-selection-audit.json) |
| Independent validation | [Go compiler identities](investigations/go-method-values/evidence/verification-compiler-cases.json), [ordinary CLI cross-check](investigations/go-method-values/evidence/cli-verification.json) |
| Current-client behavior | [go-redis A/B/C](investigations/go-method-values/evidence/current-public-verification.json), [MySQL A/B/C](investigations/go-method-values/evidence/current-mysql-verification.json), [offline replay](investigations/go-method-values/reproduction/check_current_public.py) |
| Experiment coverage | [Evidence audit and live-review reproduction](investigations/go-method-values/FINAL_EVIDENCE_AUDIT.md) |
| Originality | [Mechanism-level duplicate review](investigations/go-method-values/DUPLICATE_CHECK.md), [candidate decisions](investigations/go-method-values/CANDIDATES.md) |
| Issue report | [Official issue #716](https://github.com/FinanceFlash/unvibecode/issues/716), [report copy](investigations/go-method-values/submission/GITHUB_ISSUE.md) |
| Current MySQL CI | [Linux and Windows checks for PR #6](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/6/checks) |
| Baseline continuous verification | [Passing Linux and Windows run](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/43265840641) at `edb1aa3a7c744b8c396eea34282aef87dfbdd913`; downloadable logs and generated artifacts |

## Scope and limitations

The proposed correction is a tested reference implementation; it is not a shipped UnvibeCode fix. Reference-correction counts apply to the inspectable 0.3.15 engine. Current wrapper-control counts come from the 0.4.0 downloads, whose hosted backend revision is undisclosed. Go-redis business analysis was skipped for size; all MySQL review lanes completed. No changed business-risk verdict is claimed.

This investigation establishes a static method-reference omission and its focused-context impact. It does not establish general indirect-call resolution, ecosystem prevalence, or a changed business-risk verdict. The two selection scopes share inputs. Originality is assessed against the dated issue inventory, rather than guaranteed against later reports.
