Title: [Bug] Go callback references — typed method values lose implementation relationships and focused context

## 1. Problem summary

`callback := s.Save; callback()` loses the relationship to `Store.Save` despite
an explicit `s *Store` parameter. Wrapping the same invocation in
`func() { s.Save() }` restores it. Package-function values already work.
Public go-redis consequently exports callback setup without complete referenced
pipeline/fan-out implementations in focused context.

## 2. Test environment

UnvibeCode **0.3.15**, Windows, Python **3.14.5**, Go **1.27.3**.
Both shipped collectors and graph builders are tested. Public source:
[redis/go-redis@5cba5e182946cf18a757718938bc43910e589466](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466).
No upstream source is modified.

## 3. Steps to reproduce

Use the [review evidence repository](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/3),
`investigations/go-method-values/README.md`. Install its pinned dependencies, then:

```sh
python investigations/go-method-values/reproduction/verify.py --work ci-logs/minimal --output ci-logs/minimal.json
```

For public replication, clone the pinned go-redis commit and add
`--repo /path/to/go-redis`. The verifier runs actual installed pipeline functions
and reads the produced ZIPs. Go must be on PATH; grammar setup failures fail.

## 4. Expected behavior

A known receiver's method value should retain its method-definition relationship,
as a symbol reference. Forming a callback is not a direct method invocation;
the [Go specification](https://go.dev/ref/spec#Method_values) distinguishes them.

## 5. Actual behavior

The minimal original and repeat have no `Save` usage or `store.go` focused context.
The equivalent fixture wrapper and reference correction restore both; restoration
reproduces the omission. All five source states compile and pass callback tests.
Package values remain linked; a function-valued field is not linked to another
type's same-named method.

Both real graph copies yield **23,448 → 23,527 → 23,448** relationships, with
zero removed originals. Additions are **13 production references** across six
file pairs and **66 test references**, not 79 proven invocations.

## 6. Evidence

`evidence/verification.json` records both engines, source hashes, compiling
controls, graph identities, and actual exported selections. All seven distinct
source-specific production callee identities are audited against every nonblank
line of their complete definitions at Optimal and Wider.

**Five of seven** complete implementations are absent → complete → absent in
each scope. `process` remains incomplete at Optimal and complete at Wider;
`processTxPipeline` remains incomplete throughout. These bounds are retained.
Independent Go type-checker cases identify the 13 production source positions.

## 7. Impact and scope

MultiDB initialization loses `processPipeline` in `multidb_pipeline.go`; ring
fan-out loses `ForEachShard` in `ring.go`. Developers inspecting focused context
miss the installed callback implementations. Source remains in the complete ZIP.
No changed hosted risk verdict, general indirect-call analysis, or ecosystem
prevalence is claimed. The two scopes are correlated observations.

## 8. Suspected cause / suggested fix

`_collect_go_usages` handles non-call selectors only via `package_selector`,
which exits for known local qualifiers. The receiver's correct type is discarded.
Affected branches: Fast Lane `00a:1292`; Normal graph `01:1250`.

The tested in-memory correction emits typed references, resolves them through
the existing owner-aware resolver, and exports `imports_symbol/go_method_value`.
Unresolved fields stay unpromoted. It restores both original methods afterward.
No installed file is edited.

## 9. Duplicate check

485 open/closed issue bodies through **#596** plus nearest Go comments checked.
No method-value/callback-reference mechanism match found. #360 concerns receiver
selection; #415 factory expressions; #542 collection/range types; #596 named
result bindings. This case has an explicit ordinary parameter and correctly
known type. Earlier JSONC and named-result drafts are excluded as duplicates.
