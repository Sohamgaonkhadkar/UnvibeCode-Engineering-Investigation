# Typed Go Method Values — Technical Investigation

**Affected published engine:** UnvibeCode `0.3.15` (both Fast Lane and Normal Lane graph copies)  
**Public source:** [redis/go-redis at `5cba5e182946cf18a757718938bc43910e589466`](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466)  
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
| Additional production references | — | 13 | — |
| Additional test references | — | 66 | — |
| Existing relationships removed | — | 0 | — |

The 13 production selector positions are checked against Go's actual resolved method identities (receiver, target source file, method span). A clean Linux CI run verified **13/13**. The 66 test references are not independently claimed as real-world production impact.

### Complete-definition impact in focused context

The selected output is checked line-by-line against all nonblank lines of each target method, for seven distinct production caller→callee pairs.

| Method | Stock | Corrected | Restored |
|---|---|---|---|
| `ClusterClient.processPipelineRetries` from `autopipeline_cluster_fd.go` | Absent | Complete | Absent |
| `ClusterClient.ForEachMaster` from `himport_cluster.go` | Absent | Complete | Absent |
| `Ring.ForEachShard` from `himport_cluster.go` | Absent | Complete | Absent |
| `multidbCore.processPipeline` from `multidb.go` | Absent | Complete | Absent |
| `ClusterClient.ForEachMaster` from `osscluster_router.go` | Absent | Complete | Absent |
| `multidbCore.process` from `multidb.go` | Incomplete at Optimal; complete at Wider | Unchanged | Unchanged |
| `multidbCore.processTxPipeline` from `multidb.go` | Incomplete | Incomplete | Incomplete |

Thus **5/7** full source definitions become newly available in both audited selection scopes. The two exceptions are documented; the complete repository ZIP still contains the original code.

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

- The local installed 0.3.15 graph, selectors and ZIP were tested; **hosted UnvibeCode 0.4.0 behavior was not**.
- Method values are **references**, not direct invocations. No general function-pointer dispatch, method-expression support, or interface-dispatch correctness is asserted.
- All claims use pinned commits, measured artifact contents, and explicit denominators; the selected scopes are correlated.
- Experiments preserve the tracked public source and restore the in-memory patched methods in a `finally` block.
- A full 0.4.0 hosted review needs separate validation. In particular, [upstream #662](https://github.com/FinanceFlash/unvibecode/issues/662) reports that the new uploader omits `go.mod`; that separate defect must not be confused with the method-value cause.
