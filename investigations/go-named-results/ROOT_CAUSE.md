# Root cause: named result bindings are omitted before the Go body walk

The first divergence occurs in `TreeSitterAstAdapter._collect_go_usages.visit`.
Both 0.3.15 engine copies recognize functions, methods, and function literals.
Before visiting their bodies, they copy the enclosing environment and bind the
method receiver and input parameters. They never bind the `result` field.

| Shipped source under `shipreadyv2/engine_sources/` | Collector | Input binding |
| --- | --- | --- |
| `00a_shipreadyv2_fast_lane_v11_api_context_bundle.py` | 981 | 1152–1165; parameters at 1157 |
| `01_shipreadyv2_merged_graph_pipeline_5chunks.py` | 939 | 1110–1123; parameters at 1115 |

Source SHA-256 values are recorded in [verification.json](evidence/verification.json)
and match the engine hashes preserved by the earlier investigation. The upstream
documentation repository does not contain these engine sources; install the
pinned public wheel to inspect the exact locations.

The existing helper `parameter_types` already understands a parameter-list node
containing named results such as `(r *Store)` and `(r, s *Store)`. It excludes `_`
and retains unknown types without guessing. The omitted call is therefore:

```python
local_env.update(parameter_types(child_by_field_name(node, "result")))
```

Insert it immediately after the corresponding `"parameters"` binding in both
copies. [named_results.py](solution/named_results.py) applies precisely this
insertion to a loaded method, rejects an unexpected anchor, and restores the
original method in `finally`. It never writes to the installed package.
This is a diagnostic reference correction for maintainer adaptation.

## Propagation

1. Go declares result `r` as a local variable of known type `*Store`.
2. The collector omits `r` from `local_env`.
3. At `r.Save()`, the identifier receiver is absent from `env`, so the collector
   calls `package_selector` rather than emitting a typed `method_call`.
4. The package resolver interprets `r` as an import qualifier. If no such alias
   exists, no target is produced. If `r` names an imported package elsewhere in
   the file, that package's `Save` function can become the wrong target.
5. That missing/wrong graph relationship propagates into the real chunk
   connections and precomputed focused context selections.

This is not a constructor-return inference problem: the result's type is
declared in the same signature, and the failing call's operand is a plain
identifier. The fixture includes a same-named imported function specifically to
make the incorrect namespace choice observable. Its runtime test establishes
that `Open` mutates `Store.Saved`, while the package control calls `remote.Save`.

The [Go specification](https://go.dev/ref/spec#Declarations_and_scope) places a
function's result variables in the function body scope. The product's
[Go guide at the inspected upstream commit](https://github.com/FinanceFlash/unvibecode/blob/c75b75e26cfd2cca923d2030f3b0a7056eadd89d/docs/GO_SUPPORT.md)
already promises receiver resolution when the type is known and prohibits
guessing a different qualifier owner. Go compilation and runtime controls provide
an independent oracle for these cases.

## Causal evidence

| State | Input / implementation | Target at `Open`'s call | `Store.Save` source selected |
| --- | --- | --- | --- |
| A | Named result, stock | `remote/remote.go` | No |
| B | Unnamed result + local declaration, stock | `store.go` | Yes |
| C | Original named result restored, stock | `remote/remote.go` | No |
| D | Original input, one binding inserted in memory | `store.go` | Yes |
| E | Original method restored | `remote/remote.go` | No |

Both fixture forms compile and pass the same runtime assertions. The
package-qualified call at line 5 always resolves to `remote/remote.go`.
The 54 extraction assertions cover both copies in stock/corrected/restored order:
named functions, named methods, closure capture, grouped results, equivalent
local and parameter controls, inner shadowing, unnamed results, and unknown
interface types. Existing file hashes remain unchanged.

On LevelDB, stock/corrected/restored full Fast Lane runs preserve every tracked
source byte and restore exactly six call-site/target/owner identities. The
set difference contains no lost relationships. It collapses to three file pairs,
so six is not claimed as six independent affected files or workflows.

The `setOptions` maintenance task checks five exact implementation fragments
inside selected `options.go` chunks, not just the presence of the name at its
call site. It measures answer-bearing source availability, not an LLM's answer.

## Boundaries

This correction does not infer package globals, range element types, factory
receiver expressions, embedded/interface implementations, or platform build
constraints. Those remain separate mechanisms, several already reported.
Only 0.3.15 was dynamically tested here. No ecosystem prevalence or hosted
business-risk consequence is inferred from this one public repository.
