# Root cause and causal controls

Installed source digests are recorded in `evidence/verification.json`.

| Stage | Fast Lane `00a` | Normal graph `01` |
|---|---|---|
| Usage collector | `_collect_go_usages:981` | `:939` |
| Package-only selector helper | `package_selector:1127` | `:1085` |
| Non-call selector branch | `:1292` | `:1250` |
| Owner-aware Go resolver | `_resolve_go_usages:2448` | `:2405` |
| Method-call-only dispatch | `:2828` | `:2785` |

For a parameter `s *Store`, `parameter_types()` already adds `Store` to the
environment. In a direct `s.Save()` call, the call branch emits a typed
`method_call`. In `callback := s.Save`, the selector branch calls
`package_selector(node, env, "value")`; that helper exits on `qualifier in env`.
No typed usage reaches the resolver. Changing named-result binding cannot fix
this case: it uses an ordinary input parameter with a correctly known type.

The reference correction emits a typed `method_reference` for local selector
values and admits that kind to the existing owner-aware method resolver. Only
successfully resolved method definitions become `imports_symbol` relationships.
Fields without a matching method and unknown/external types stay unpromoted.
It does not treat evaluating a method value as immediately invoking it; Go's
[method-value specification](https://go.dev/ref/spec#Method_values) distinguishes
forming the function value from later calls using its saved receiver.

The minimal fixture executes callbacks and checks memory state. Original,
repeat, wrapper control, corrected, and restored source all compile and pass.
Only the wrapper and corrected states select `store.go` for `source.go`.
The wrapper is equivalent in this fixture because the receiver is never
reassigned; general wrapper equivalence under receiver reassignment is not claimed.
Package function values remain connected. An unrelated type's `Job` method is
not linked to the fixture's function-valued `Store.Job` field.

Both parser copies are exercised separately. The full Fast Lane export runs
on original/control/corrected/restored fixtures, and stock/corrected/restored
public go-redis. The Normal Lane experiment runs its real graph builder and
linker, not a corrected Normal Lane context export or hosted review.

All 13 gained production source positions have expected owner/target identities
saved for an independent `go/types` check. That checker rejects a field (it
requires `*types.Func`) and checks the receiver, target file and defining span.
The complete target audit is exhaustive over seven distinct source-specific
production callee identities; every nonblank source line must match selected
target source. It exposes the two incomplete/control targets as well as the five
restored targets. No source, threshold, token budget, or installed file is edited
in the reference-extraction correction experiments. The separate capacity control
changes only an in-memory scope maximum, as documented in the context audit. Tracked public files are hashed before and after.
