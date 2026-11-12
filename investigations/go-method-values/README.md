# Typed Go Method Values — Technical Investigation

**Affected published engine:** UnvibeCode `0.3.15` (both Fast Lane and Normal Lane graph copies)  
**Public source:** [redis/go-redis at `5cba5e182946cf18a757718938bc43910e589466`](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466)  
**Current client check:** three 0.4.0 code-map captures on the complete pinned go-redis tree reproduce eight missing method links and four missing implementations; [offline evidence](evidence/current-public-verification.json). Code understanding completed; business analysis was skipped for repository size.

**Main claim:** A known local receiver used as a Go method value is omitted before owner-aware resolution, sometimes excluding the implementation from focused code context.

## Failure and cause

```go
func Run(s *Store) {
    cb := s.Save
    cb()
}
```

Go permits a method value with its receiver bound at expression evaluation. In the published analyzer, a direct `s.Save()` call emits a typed method usage, whereas the non-call selector `s.Save` is routed through `package_selector`. That helper returns for known local qualifiers, dropping the typed reference despite the receiver type already being available.

The proposed narrow correction emits `method_reference` during non-call selector extraction, resolves it with the existing owner-aware method resolver, and exports a symbol-reference relationship (`imports_symbol` / `go_method_value`). It **does not** relabel method-value formation as an invocation.

See [the source-level analysis](ROOT_CAUSE.md) and [the Go specification](https://go.dev/ref/spec#Method_values).

## Experimental design

The verifier executes the installed engine code (not a reimplementation) in the following states:

| State | Input/engine condition | Expected relationship |
|---|---|---|
| Stock | `callback := s.Save` | Missing |
| Repeat | Same source and engine | Missing |
| Wrapper control | `callback := func() { s.Save() }` | Direct method call present |
| Corrected | Original source + transient correction | Typed method reference present |
| Restored | Original source + unmodified engine restored | Missing |

It also checks package function values, same-named methods on unrelated types, and ordinary function-valued fields. Five Go source variants compile and pass tests. Both shipped collectors/builders are exercised; the real Fast Lane writes and reads its exported ZIP.

## Measured public-project outcome

The pinned go-redis source remains unchanged.

| Measure | Stock | Corrected | Restored |
|---|---:|---:|---:|
| Total graph relationships per shipped copy | 23,448 | 23,527 | 23,448 |
| Production references gained versus stock | 0 | 13 | 0 |
| Test references gained versus stock | 0 | 66 | 0 |
| Existing relationships removed | 0 | 0 | 0 |

The 13 production selector positions are checked against Go's actual resolved method identities (receiver, target source file, method span). A clean Linux CI run verified **13/13**. The 66 test references are not independently claimed as real-world production impact.

### Complete-definition impact in focused context

The selected output is checked line-by-line against all nonblank lines of each target method, for seven distinct production caller→callee pairs.

| Caller → required method | Stock | Corrected | Restored |
|---|---:|---:|---:|
| `autopipeline_cluster_fd.go` → `ClusterClient.processPipelineRetries` | 0/72 | **72/72** | 0/72 |
| `himport_cluster.go` → `ClusterClient.ForEachMaster` | 0/31 | **31/31** | 0/31 |
| `himport_cluster.go` → `Ring.ForEachShard` | 0/32 | **32/32** | 0/32 |
| `multidb.go` → `multidbCore.processPipeline` | 0/3 | **3/3** | 0/3 |
| `osscluster_router.go` → `ClusterClient.ForEachMaster` | 0/31 | **31/31** | 0/31 |

Each fraction counts matching required nonblank method-body lines. These five rows hold at both Optimal and Wider. For `multidb.go` → `multidbCore.process`, all three states have 0/215 at Optimal and 215/215 at Wider. For `multidb.go` → `multidbCore.processTxPipeline`, all three have 0/135 at both scopes.

Thus **5/7** full source definitions become newly available in both audited selection scopes. The two exceptions are documented; the complete repository ZIP still contains the original code.

## Selection-capacity limits

The exact line audit finds 0/215 matching nonblank lines for `process` at Optimal and 215/215 at Wider in all three states. `processTxPipeline` has 0/135 in both scopes throughout. The corrected ZIP contains their resolved reference edges, but selection estimates are already 44,997/45,000 and 74,999/75,000 tokens.

A separate diagnostic changes only a scope’s maximum to 200,000 tokens. Both bodies then become complete. Source, corrected graph, chunking and ranking remain unchanged. This isolates a capacity limit; the main **5/7** recovery result still uses original budgets. See [the exact audit](evidence/context-selection-audit.json) and [reproducer](reproduction/explain_context.py).

## Current client: full public-repository A/B/C

The unmodified 0.4.0 client analyzed original go-redis (A), eight receiver-preserving wrapper substitutions (B), and eight no-method callbacks (C). Every recovered source line is checked; only eight lines in three files differ, target implementations remain identical, and upload paths are identical. All states omit `go.mod`; the targeted methods are same-package relationships.

| Measure | A | B | C |
|---|---:|---:|---:|
| Targeted method links | 0 | 8 | 0 |
| Complete target implementations in each scope | 0/4 | 4/4 | 0/4 |
| Exported relationship records | 12,189 | 12,204 | 12,189 |

The gains are eight method-call records and seven coarse imports, with no normalized relationships removed. C matches A's normalized graph. B captures the pointer receiver before returning a forwarding closure, preserving bound receiver semantics. C is a deliberately different no-op control; it is not a proposed workaround or equivalent behavior.

Code understanding is COMPLETED; business analysis is SKIPPED_LARGE_REPOSITORY and overall status PARTIAL. One initial A connection failure yielded no artifacts; a subsequent attempt completed. Hosted backend revision is not exposed. [Captured ZIPs](evidence/current-public-0.4.0), [offline replay](reproduction/check_current_public.py) and [experiment audit](FINAL_EVIDENCE_AUDIT.md) preserve the current-version result.

## Source-backed developer questions

| Question | Implementation needed | Exact nonblank lines: A → B → C, both scopes |
|---|---|---|
| What execution bound does FD reroute apply? | `ClusterClient.processPipelineRetries` | 0/72 → 72/72 → 0/72 |
| Is master fan-out concurrent and error-propagating? | `ClusterClient.ForEachMaster` | 0/31 → 31/31 → 0/31 |
| Are down ring shards skipped? | `Ring.ForEachShard` | 0/32 → 32/32 → 0/32 |
| Which retry setting does the MultiDB pipeline hook forward? | `multidbCore.processPipeline` | 0/3 → 3/3 → 0/3 |

The [question audit](evidence/developer-impact.json) includes implementation excerpts, source anchors and exact coverage in the original-budget historical correction exports. Current A/B/C measurements independently confirm these same four bodies. This tests context availability, not model answer correctness.

## Independent MySQL-driver replication

The complete [go-sql-driver/mysql checkout](https://github.com/go-sql-driver/mysql/tree/4cdf75e9037ffccf63a981d10f5c2e669edbfc49) contains two cross-file typed method values in `packets.go`: `mc.readWithTimeout` and `mc.writeWithTimeout`. Both definitions are in `connection.go`. The same extraction-stage mechanism is reproduced by both installed 0.3.15 engines.

Relationships are **656 → 658 → 656**, with zero original relationships lost. Both bodies are absent → complete → absent in both scopes. [Go's type checker](evidence/mysql-compiler.json) confirms both method identities; four mock-backed packet tests pass. [The replay script](reproduction/replicate_mysql.py) measures the entire pinned repository. No current hosted MySQL run is claimed.

## Regression boundaries

[Additional compiler/runtime-backed controls](reproduction/check_boundaries.py) test explicitly typed and inferred local receivers, same-named methods on different concrete types, package function values, ordinary function-valued fields, interface uncertainty, and callback formation versus invocation. Both engine copies preserve stock → corrected → restored causality. Fields are not promoted to methods, and interface references do not invent concrete implementations. [Results](evidence/boundaries.json) and [public-project tests](evidence/public-go-tests.json) retain the observations.

## Reproduction

From the repository root:

```bash
python -m pip install -r investigations/go-method-values/reproduction/requirements.txt

python investigations/go-method-values/reproduction/verify.py \
  --work ci-logs/minimal --output ci-logs/minimal.json

git clone https://github.com/redis/go-redis.git .local-go-investigation/redis
git -C .local-go-investigation/redis checkout 5cba5e182946cf18a757718938bc43910e589466

python investigations/go-method-values/reproduction/verify.py \
  --repo .local-go-investigation/redis \
  --work ci-logs/redis --output ci-logs/redis.json

go build -o ci-logs/compiler-oracle investigations/go-method-values/reproduction/compiler_oracle.go
ci-logs/compiler-oracle -repo .local-go-investigation/redis -package . \
  -cases ci-logs/redis-compiler-cases.json -output ci-logs/compiler-results.json
```

Requires Python 3.12+, a compatible Go toolchain (CI: Go 1.27.3), and first-use grammar downloads. `go test -c` in CI compiles the public test package; it does **not** execute Redis-dependent integration tests.

## Provenance and artifacts

- [Machine-readable verified results](evidence/verification.json)
- [Compiler test identities](evidence/verification-compiler-cases.json)
- [Ordinary local CLI stock-bundle equality](evidence/cli-verification.json): 11,284 chunks, 24,191 exported relationship records, 536 selections
- [CI artifact digests and historical test run](evidence/ci-snapshot.json)
- [Conservative transient reference correction](solution/method_values.py)
- [Maintainer-ready issue report](submission/GITHUB_ISSUE.md)
- [Current CI workflow](../../.github/workflows/go-method-values.yml)

## Validated boundaries

- Local installed 0.3.15 source, graphs and ZIPs establish the root cause and public-project metrics. Three current 0.4.0 client code-map artifacts independently reproduce the full-public-repository symptom; the hosted backend revision is not exposed.
- Method values are **references**, not direct invocations. No general function-pointer dispatch, method-expression support, or interface-dispatch correctness is asserted.
- All claims use pinned commits, measured artifact contents, and explicit denominators; the selected scopes are correlated.
- Experiments preserve the tracked public source and restore the in-memory patched methods in a `finally` block.
- Full 0.4.0 business review was skipped for go-redis size. Separately, [upstream #662](https://github.com/FinanceFlash/unvibecode/issues/662) reports that the new uploader omits `go.mod`; that separate defect must not be confused with the method-value cause.

## Report and originality

The [official Track 1 issue #716](https://github.com/FinanceFlash/unvibecode/issues/716) and its [local report copy](submission/GITHUB_ISSUE.md) provide an immutable reproduction checkout and expected-versus-actual results. The [dated originality review](DUPLICATE_CHECK.md) distinguishes the extraction mechanism from the closest existing reports.
