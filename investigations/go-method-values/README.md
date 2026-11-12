# Typed Go Method Values — Technical Investigation

**Affected published engine:** UnvibeCode `0.3.15` (both Fast Lane and Normal Lane graph copies)  
**Public source:** [redis/go-redis at `5cba5e182946cf18a757718938bc43910e589466`](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466)  
**Current client check:** 0.4.0 code-map captures on 12 November reproduce the small fixture’s omission; [offline evidence](evidence/latest-client-verification.json). Overall hosted reviews were partial; business outputs are not used.

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

## Current client capture

Two ordinary 0.4.0 client reviews produce completed code-understanding artifacts: the original method value has no Store.Save edge or store.go in either focused scope; a matched one-expression wrapper has one edge and includes store.go. The other three uploaded Go files match. [The offline replay](reproduction/check_current_client.py) verifies the [captured ZIPs](evidence/latest-client-0.4.0) and [results](evidence/latest-client-verification.json).

Both overall reviews are PARTIAL: business analysis stopped at Step 04 with no evidence-valid business path fragments. No complete business review or identical hosted backend source is claimed. This is a fresh small-fixture observation, not a current hosted go-redis recovery count.

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

- Local installed 0.3.15 source, graphs and ZIPs establish the root cause and public-project metrics. Two current 0.4.0 client code-map artifacts independently reproduce the small-fixture symptom; the hosted backend revision is not exposed.
- Method values are **references**, not direct invocations. No general function-pointer dispatch, method-expression support, or interface-dispatch correctness is asserted.
- All claims use pinned commits, measured artifact contents, and explicit denominators; the selected scopes are correlated.
- Experiments preserve the tracked public source and restore the in-memory patched methods in a `finally` block.
- Full 0.4.0 business review did not complete. Separately, [upstream #662](https://github.com/FinanceFlash/unvibecode/issues/662) reports that the new uploader omits `go.mod`; that separate defect must not be confused with the method-value cause.

## Report and originality

The [nine-section issue report](submission/GITHUB_ISSUE.md) provides an immutable reproduction checkout and expected-versus-actual results. The [dated originality review](DUPLICATE_CHECK.md) distinguishes the extraction mechanism from the closest existing reports.
