# [Bug] Go method values — typed callback references lose method-definition links and focused context

## 1. Problem summary

A Go method value such as `callback := s.Save` does not produce a relationship to `Store.Save` in UnvibeCode 0.3.15 even when `s *Store` is explicitly declared. The corresponding direct call `s.Save()` is resolved. On a real go-redis checkout, this drops callback implementations from per-file focused context.

This is a missing **method reference**, not evidence that merely forming a method value executes the method.

## 2. Test environment

- **Affected product:** published `unvibecode==0.3.15`, Fast Lane and Normal Lane graph implementations
- **Local validation:** Python 3.12+/Go (Linux and Windows CI); original investigation on Windows, Python 3.14.5, Go 1.27.3
- **Public repository:** [redis/go-redis](https://github.com/redis/go-redis), pinned at [`5cba5e182946cf18a757718938bc43910e589466`](https://github.com/redis/go-redis/tree/5cba5e182946cf18a757718938bc43910e589466)
- **Engine scope:** 0.3.15 local analysis. The current 0.4.0 hosted engine has not been independently verified for this defect.

## 3. Steps to reproduce

Clone the [reproducible investigation](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/codex/track1-original-investigation) and check out its `codex/track1-original-investigation` branch.

```sh
python -m pip install -r investigations/go-method-values/reproduction/requirements.txt
python investigations/go-method-values/reproduction/verify.py --work ci-logs/minimal --output ci-logs/minimal.json
git clone https://github.com/redis/go-redis.git .local-go-investigation/redis
git -C .local-go-investigation/redis checkout 5cba5e182946cf18a757718938bc43910e589466
python investigations/go-method-values/reproduction/verify.py --repo .local-go-investigation/redis --work ci-logs/redis --output ci-logs/redis.json
```

The script uses installed engine code, compiling Go fixtures, passing/negative controls, a transient correction and restoration. Inspect `ci-logs/redis.json` and the emitted actual context ZIPs. The [Go compiler oracle](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/66f769892aebbf69a2a6f4e417e8c637d4cb4119/investigations/go-method-values/reproduction/compiler_oracle.go) independently checks method owners and definition locations.

## 4. Expected behavior

A known receiver's bound method value should preserve a statically justified link to its method definition as a **reference**. Go's [method-value specification](https://go.dev/ref/spec#Method_values) distinguishes formation of a bound method value from calling that value.

## 5. Actual behavior

For `callback := s.Save; callback()`, the stock extractor emits no `Save` usage, and a focused selection can omit `store.go`. Rewriting the local fixture to `callback := func() { s.Save() }` restores the dependency. The reference correction restores the original source's dependency; reverting the correction reproduces the omission. All five fixture states compile and pass.

Both graph copies on unchanged go-redis yield **23,448 → 23,527 → 23,448** relationships. The 79 additions comprise **13 production method references** (six file pairs) and **66 test references**. No stock relationships are removed.

## 6. Evidence

The [technical investigation](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/66f769892aebbf69a2a6f4e417e8c637d4cb4119/investigations/go-method-values/README.md) documents source digests, both engine copies, the reversible experiment, independent type checks, and actual exported ZIP comparisons.

- Go type checker: **13/13** exact production source-position/receiver/definition identities verified in clean Linux CI.
- Seven source-specific production callee identities checked line-by-line in actual Optimal and Wider selections.
- **Five of seven** complete implementations newly recovered in both scopes; the other two remain bounded exceptions.
- Stock ordinary CLI and local-pipeline exports agree: **11,284 chunks, 24,191 exported relationship records, 536 selections**.

Detailed records: [verification JSON](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/66f769892aebbf69a2a6f4e417e8c637d4cb4119/investigations/go-method-values/evidence/verification.json), [compiler oracle](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/66f769892aebbf69a2a6f4e417e8c637d4cb4119/investigations/go-method-values/reproduction/compiler_oracle.go), [CI provenance](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/66f769892aebbf69a2a6f4e417e8c637d4cb4119/investigations/go-method-values/evidence/ci-snapshot.json).

## 7. Impact and scope

Focused context for MultiDB callback initialization can omit `multidbCore.processPipeline`; ring fan-out context can omit `Ring.ForEachShard`. The source is still present in the **complete** repository ZIP; the observed defect is specifically an omission of method implementation evidence from selected focused context.

No hosted final-report change, arbitrary indirect-call resolution, ecosystem prevalence, or Go runtime bug is claimed.

## 8. Suspected cause / suggested fix

`TreeSitterAstAdapter._collect_go_usages` handles non-call `selector_expression` nodes with `package_selector`. For a known local qualifier, that helper returns without emitting a typed usage, although input parameters correctly populate the receiver environment.

A tested reference correction emits `method_reference` for typed local selector values, passes it through `ShipReadyV2DeepGraphBuilder._resolve_go_usages`, and exports `imports_symbol` / `go_method_value` relationships. Unresolved fields remain unpromoted. Both installed methods are restored after each experiment, with source hashes unchanged.

## 9. Duplicate check

A complete historical snapshot of 485 open/closed issues through #596 was reviewed, followed by #597. On **11 November 2026**, a fresh open-and-closed issue sweep reached **#680** and searched 568 visible issue bodies for method-value, typed-receiver, and callback mechanisms. No issue matching this particular non-call, typed method-value selector failure was found.

Closest distinct reports: [#360](https://github.com/FinanceFlash/unvibecode/issues/360) (wrong receiver's target for a resolved call); [#415](https://github.com/FinanceFlash/unvibecode/issues/415) (factory-expression receiver); [#573](https://github.com/FinanceFlash/unvibecode/issues/573) (interface dispatch); [#596](https://github.com/FinanceFlash/unvibecode/issues/596) (named-result binding); [#625](https://github.com/FinanceFlash/unvibecode/issues/625) (unresolved Go diagnostics not exported); [#662](https://github.com/FinanceFlash/unvibecode/issues/662) (0.4.0 uploader omits `go.mod`).

The earlier JSONC investigation matched [#451](https://github.com/FinanceFlash/unvibecode/issues/451) and is **not** the subject of this report. Duplicate checking is time-bound; repeat it immediately before publication.
