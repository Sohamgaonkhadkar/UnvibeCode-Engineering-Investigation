# Typed Go method values lose callback implementation context

Selected Track 1 candidate, UnvibeCode 0.3.15. No matching mechanism was found in
485 open/closed upstream issue bodies through #596, with nearest Go report
comments checked. No upstream issue or Google Form has been submitted.
New [#597 was also read and excluded](evidence/issue-597-follow-up.json), bringing
the total to 486 distinct issue bodies reviewed. A full REST refresh was rate
limited; the complete snapshot and incremental check are distinguished.

`callback := s.Save; callback()` executes `Store.Save`, but the parser records
no `Save` usage even when `s *Store` is an explicit input parameter. A wrapper
`callback := func() { s.Save() }` restores the relationship and selected source.
Package-function values such as `callback := remote.Save` already work.

The cause is an asymmetric selector visitor. `call_expression` binds a known
receiver to a method; a non-call `selector_expression` goes only through
`package_selector()`, which returns immediately when its qualifier is a known
local variable. The correct type is present but discarded. This is separate
from unknown receiver inference, factory expressions, named results, or ranges.

## Measured results

On unchanged [redis/go-redis at 5cba5e182946cf18a757718938bc43910e589466](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466),
both shipped graph copies produce **23,448 → 23,527 → 23,448** relationships.
The 79 additions comprise **13 production callback references** across six file
pairs and 66 test references. No original relationship is removed. These are
static references, not 79 newly proven invocations or application defects.

Every source-specific production target is audited: all nonblank lines of its
complete definition must match selected source, at both Optimal and Wider.

| Source → method | Stock | Corrected | Restored |
|---|---|---|---|
| `autopipeline_cluster_fd.go` → `ClusterClient.processPipelineRetries` | absent | complete | absent |
| `himport_cluster.go` → `ClusterClient.ForEachMaster` | absent | complete | absent |
| `himport_cluster.go` → `Ring.ForEachShard` | absent | complete | absent |
| `multidb.go` → `multidbCore.processPipeline` | absent | complete | absent |
| `osscluster_router.go` → `ClusterClient.ForEachMaster` | absent | complete | absent |
| `multidb.go` → `multidbCore.process` | incomplete at Optimal; complete at Wider | same | same |
| `multidb.go` → `multidbCore.processTxPipeline` | incomplete | incomplete | incomplete |

Thus **5/7** complete target implementations are restored in each scope; the
remaining two explicitly bound the correction's impact. Scopes share inputs and
are not counted as independent developer tasks. The entire ZIP retains source
throughout. Focused context, rather than whole-archive source availability, fails.

For example, understanding how MultiDB initialization installs pipeline handlers
requires the referenced `processPipeline` body in `multidb_pipeline.go`. Ring
fan-out requires `ForEachShard` in `ring.go`. These files are missing from the
corresponding stock Optimal selections and included after the correction.

## Reproduce

From this evidence repository root, with Python 3.12+ and Go on PATH:

```sh
python -m pip install -r investigations/go-named-results/reproduction/requirements.txt
python investigations/go-method-values/reproduction/verify.py --work ci-logs/method-values-minimal --output ci-logs/method-values-minimal.json
git clone https://github.com/redis/go-redis.git .local-go-investigation/redis
git -C .local-go-investigation/redis checkout 5cba5e182946cf18a757718938bc43910e589466
python investigations/go-method-values/reproduction/verify.py --repo .local-go-investigation/redis --work ci-logs/method-values --output ci-logs/method-values.json
go build -o ci-logs/compiler-oracle investigations/go-named-results/reproduction/compiler_oracle.go
ci-logs/compiler-oracle -repo .local-go-investigation/redis -package . -cases ci-logs/method-values-compiler-cases.json -output ci-logs/compiler-method-values.json
```

Windows executables need `.exe`. Public go-redis requires Go 1.26+; CI pins
1.27.3. Grammar manifest access is required on first parse. A setup failure fails
verification. The compiler oracle uses Go's own type checker and dependency
exports; its legacy `calls_verified` field counts checked selector identities,
not runtime invocations. All **13/13** production identities passed in clean
Linux CI; the existing go-redis root test package compiled without executing
server-dependent tests. The fixture checks passed on both Linux and Windows.

[Verification run](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42372544897)
at `abd5689744593ae315299cdb378c4b567edd88ff` passed both jobs.
[CI provenance and artifact digests](evidence/ci-snapshot.json) identify the exact
15.2 MB Linux artifact containing stock/corrected/restored ZIPs and compiler JSON.
The same commit's unrelated legacy documentation gate required a provenance
follow-up; live PR checks govern the current head.

The ordinary CLI's local-only export also exactly matches the stock pipeline:
11,284 chunks, 24,191 exported relationship records and 536 selections. See
[CLI comparison](evidence/cli-verification.json). Hosted business review was
deliberately skipped for that comparison; it is not a completed hosted review.

## Evidence and correction

[Verifier](reproduction/verify.py), [results](evidence/verification.json), and
[source/cause audit](ROOT_CAUSE.md) explain compiling fixtures, repeated baseline,
wrapper control, correction, restoration, field/package controls, both collectors,
both real graph builders, complete target coverage, and unchanged tracked source.
The shared named-result verifier utilities are reused only for loading, exporting,
hashing and reading chunks; its named-result correction is never applied here.

[Reference correction](solution/method_values.py) resolves typed selector values
through the existing owner-aware method resolver. It emits `imports_symbol` with
`go_method_value`, not a direct `method_call`. Ordinary fields and unresolved
receivers are not promoted. Both in-memory replacements are prepared before
application and restored in `finally`; installed sources are unchanged.

No general indirect-call analysis, method expressions, promoted embedded methods,
or interface dispatch is claimed. The 66 test references are not independently
compiler-audited as production impact. No changed hosted business-risk verdict
or ecosystem prevalence is inferred. CI repeats the evidence on clean runners.

The earlier [named-result investigation](../go-named-results/ELIGIBILITY.md) is
archived because #596 duplicates its cause. [Risk-summary research](../risk-evidence-summary/README.md)
is provisional because of an unresolved earlier-report lead. Neither is bundled
into this submission's defect claim.

The earlier JSONC work also remains excluded by upstream #451.
