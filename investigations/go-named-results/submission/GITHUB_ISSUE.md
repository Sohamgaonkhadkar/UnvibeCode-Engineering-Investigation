Title: [Bug] Go receiver collector — named result variables become package qualifiers, losing or misrouting method calls

## 1. Problem summary

UnvibeCode 0.3.15 does not add Go named result parameters to its receiver
environment. A call such as `r.Save()` inside `func Open() (r *Store)` is treated
as a package selector despite the explicit local type. It disappears when no
package alias `r` exists; if an imported package uses that alias, the graph can
link to its unrelated `Save` function instead.

On unchanged public LevelDB source this removes six production calls. The
focused context for `leveldb/session.go` omits the `setOptions` implementation
that initializes session options, comparer/filter wrappers, and cached settings.

## 2. Test environment

- UnvibeCode: **0.3.15**, current PyPI release checked 7 November 2026.
- Local OS / Python: Windows 11 build 26300 / CPython 3.14.5.
- tree-sitter 0.26.0; tree-sitter-language-pack 1.25.0; tiktoken 0.14.0; PyVis 0.3.2.
- Compiler/runtime oracle: Go 1.27.3.
- Public repository: [syndtr/goleveldb](https://github.com/syndtr/goleveldb/tree/126854af5e6d8295ef8e8bee3040dd8380ae72e8),
  commit `126854af5e6d8295ef8e8bee3040dd8380ae72e8`; 95 source files scanned.
- Evidence repository: [UnvibeCode-Engineering-Investigation, new investigation](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/codex/track1-original-investigation/investigations/go-named-results).
  Use the immutable evidence commit linked by its review PR when reproducing.

## 3. Steps to reproduce

Clone the evidence repository, check out the evidence commit, activate a Python
virtual environment, then run from that checkout:

```sh
python -m pip install -r investigations/go-named-results/reproduction/requirements.txt
python investigations/go-named-results/reproduction/verify.py --output minimal-result.json
git clone https://github.com/syndtr/goleveldb.git .local-go-investigation/goleveldb
git -C .local-go-investigation/goleveldb checkout 126854af5e6d8295ef8e8bee3040dd8380ae72e8
python investigations/go-named-results/reproduction/verify.py --real-repo .local-go-investigation/goleveldb --output full-result.json --work .local-go-investigation/artifacts
python investigations/go-named-results/reproduction/compile_controls.py --output compiler-result.json
```

Go on PATH is required only for the last command. Grammar downloads need network
access on first use. The verifier calls the installed engines' own collector and
full Fast Lane pipeline; it does not reimplement the resolver.

The minimal fixture includes:

```go
import r "example.test/namedresult/remote"
func Imported() string { return r.Save() }
func Open() (r *Store) {
    r = &Store{}
    r.Save()
    return
}
```

`Store.Save` sets `Saved = true`; `remote.Save` returns a string. The committed
runtime test verifies that `Open().Saved` is true and the separate imported call
returns `"remote"`.

For normal CLI output, run:

```sh
python -m unvibecode review --repository .local-go-investigation/goleveldb --large-repo-token-limit 1 --no-open-browser
```

The hidden threshold deliberately skips hosted business analysis. Its PARTIAL
status is expected here. Open Connected Code, select `leveldb/session.go`, and
inspect Optimal/Wider context; or join the ZIP's `selections.jsonl` chunk IDs to
`chunks.jsonl`. Compare with the retained corrected bundle under `--work`.

## 4. Expected behavior

A named result is a local variable whose scope includes the function body,
under the [Go specification](https://go.dev/ref/spec#Declarations_and_scope).
`r.Save()` should resolve to the unique `Store.Save`, just as it does when the
same variable is declared locally or supplied as an input parameter. An imported
alias shadowed by this local binding must not determine the call target.

The [documented Go contract](https://github.com/FinanceFlash/unvibecode/blob/c75b75e26cfd2cca923d2030f3b0a7056eadd89d/docs/GO_SUPPORT.md)
already supports method calls on known concrete receiver types.

## 5. Actual behavior

| Minimal state | Graph target for `Open`'s `r.Save()` | `Store` implementation in Optimal |
| --- | --- | --- |
| A: named result, stock | `remote/remote.go` — wrong | Absent |
| B: equivalent local variable, stock | `store.go` | Present |
| C: original input restored | `remote/remote.go` — wrong | Absent |
| D: original input, result binding corrected in memory | `store.go` | Present |
| E: stock collector restored | `remote/remote.go` — wrong | Absent |

The actual exported connections follow the same targets. The separate
package-qualified `Imported` control stays correct in every state.

On unchanged LevelDB, distinct graph call-site identities are
**1,858 stock → 1,864 corrected → 1,858 restored**, with zero removed edges.
Four restored calls are `session.go:89,93,94,95` (`setOptions`, `refLoop`,
`setVersion`, `log`); two are `db_write.go:78,105` (`memDB.decref`).

## 6. Evidence

- [Behavioral verification and engine hashes](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/codex/track1-original-investigation/investigations/go-named-results/evidence/verification.json)
- [CLI versus pipeline payload comparison](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/codex/track1-original-investigation/investigations/go-named-results/evidence/cli-verification.json)
- [Compiler/runtime controls](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/codex/track1-original-investigation/investigations/go-named-results/evidence/go-compiler.json)
- [Root-cause detail and reversible reference correction](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/codex/track1-original-investigation/investigations/go-named-results/ROOT_CAUSE.md)

The normal CLI bundle exactly matches the stock local pipeline's 1,141 chunk
records, 2,035 connection records, and 95 selections. Those 2,035 exported
records include mirrored relationships and are not presented as distinct calls.

Real source: [newSession](https://github.com/syndtr/goleveldb/blob/126854af5e6d8295ef8e8bee3040dd8380ae72e8/leveldb/session.go#L71-L97)
declares `(s *session, err error)` and calls `s.setOptions(o)` at line 89.
The target [options.go:25](https://github.com/syndtr/goleveldb/blob/126854af5e6d8295ef8e8bee3040dd8380ae72e8/leveldb/options.go#L25-L44)
contains the missing implementation. All tracked public source bytes remain
unchanged across the three runs.

## 7. Impact and scope

The fixture shows a wrong implementation relationship, not just an unresolved
diagnostic. The real repository shows omitted answer-bearing implementation in
both focused export scopes: all five checked `setOptions` source fragments are
absent as-is and present after the correction. The full ZIP contains that source
throughout. Two scopes of one maintenance task are not two independent tasks.

Six restored call-site records collapse to three source/target file pairs and
two caller files. This is measured on one pinned public repository; no ecosystem
prevalence is claimed. The parser failure is reproduced on both shipped engine
copies. Full export/CLI evidence here uses Fast Lane. No hosted workflow,
business-risk verdict, or LLM answer accuracy is claimed.

## 8. Suspected cause / suggested fix

Confirmed earliest cause: `TreeSitterAstAdapter._collect_go_usages.visit` binds
method receivers and `parameters` but omits `result` before visiting the body.

- `shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py`:
  collector at 981; environment initialization at 1152–1165; input binding 1157.
- `shipreadyv2/engine_sources/01_shipreadyv2_merged_graph_pipeline_5chunks.py`:
  collector at 939; corresponding input binding 1115.

Immediately after the input binding, reuse the existing helper:

```python
local_env.update(parameter_types(child_by_field_name(node, "result")))
```

The in-memory reference passes 54 extraction checks across stock/corrected/
restored states on both engines. Controls cover grouped results, named methods,
closures, ordinary locals/parameters, inner shadowing, and unknown interfaces.
Original method objects and installed-file hashes are restored. This is
supporting reference code, not a shipped upstream fix.

## 9. Duplicate check

On 7 November 2026, screened titles/bodies of **482 open/closed issues through
#593**, excluding PRs, plus comments on 25 close/important reports. No report of
missing **named result parameter bindings** was identified.

- [#446](https://github.com/FinanceFlash/unvibecode/issues/446): package globals;
  our correction leaves that reproducer classified as a selector.
- [#454](https://github.com/FinanceFlash/unvibecode/issues/454): type-switch
  narrowing; no switch is needed here.
- [#415](https://github.com/FinanceFlash/unvibecode/issues/415): direct factory
  receiver expression; our operand is an identifier and its reproducer stays omitted.
- [#542](https://github.com/FinanceFlash/unvibecode/issues/542): collection
  return-type extraction; ours is an explicit ordinary pointer result.
- [#360](https://github.com/FinanceFlash/unvibecode/issues/360): Normal Lane
  discards an already-resolved receiver during chunk lookup; ours diverges before
  graph resolution in both collectors.
- [#547](https://github.com/FinanceFlash/unvibecode/issues/547): same-package
  type/composite-literal references; ours is an actual method call.
- [#573](https://github.com/FinanceFlash/unvibecode/issues/573): interface-dispatch
  diagnostics; ours is a statically known concrete receiver.

[Full comparison and audit provenance](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/blob/codex/track1-original-investigation/investigations/go-named-results/DUPLICATE_CHECK.md).
Originality is bounded by that snapshot and must be refreshed immediately before filing.
