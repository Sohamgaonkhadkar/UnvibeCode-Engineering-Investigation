# Duplicate audit and competitive research

Snapshot: 7 November 2026. [issue-audit.json](evidence/issue-audit.json) records
the retrieval timestamp, endpoint, body digests, match terms, states, and URLs.
Six paginated REST responses contained 592 issue/PR entries: **482 issues**,
open and closed, through **#593**, with 110 PRs excluded. Every issue title/body
was screened for the mechanism terms. Twenty-five close/important reports were
reviewed more closely; comments were checked for those reports. Only #234 had
comments (seven), which discuss adding Go support and package-versus-file edges.

No title/body matches were found for `named.?result`, `named.?return`,
`result.?parameter`, or `parameter_types`. `_collect_go_usages` matched five
reports; `shadow` matched six. Those matches were examined for their actual
mechanisms. Zero lexical matches alone is not the originality argument.

## Closest mechanisms

All issue numbers below link to `FinanceFlash/unvibecode`. Reported competitor
measurements are summarized from their reports, not independently reproduced
or incorporated into our evidence.

| Issue | Cause / trigger / subsystem | Reported effect and evidence | Why the selected finding differs |
| --- | --- | --- | --- |
| [#446](https://github.com/FinanceFlash/unvibecode/issues/446) | Package-level variable declarations are not added to the Go receiver environment | Explicit/inferred global receiver classified as package selector; adapter-level example | Ours is a function-local result parameter, already typed in the signature. Binding `result` fixes ours and leaves its package-global reproducer unchanged. Global declarations need a separate symbol/binding pass |
| [#454](https://github.com/FinanceFlash/unvibecode/issues/454) | Type-switch case type not propagated to its local variable | Three unresolved calls in pinned escher source; null receiver types | Ours has no switch or branch inference; named result declarations never enter the environment |
| [#415](https://github.com/FinanceFlash/unvibecode/issues/415) | Collector requires identifier operands; direct factory receiver expression unsupported | Factory-result method calls omitted | Our call operand is a plain identifier; adding result bindings leaves the factory-expression reproducer omitted |
| [#542](https://github.com/FinanceFlash/unvibecode/issues/542) | `_go_named_type` does not unwrap collection types | Helper extraction loses collection return metadata; downstream impact claimed | Ours uses an ordinary explicit pointer result, whose type helper already understands. We change no return-type extraction or collection inference |
| [#547](https://github.com/FinanceFlash/unvibecode/issues/547) | Unqualified same-package type/composite-literal usages not collected | Struct/type dependency fixture has no edges | Ours is an executable method call, not a request to add type-reference relationships. The correction adds no composite-literal visitor |
| [#573](https://github.com/FinanceFlash/unvibecode/issues/573) | Resolver intentionally declines interface dispatch without preserving diagnostic | Interface call missing from both outputs in two runs | Our receiver is a known concrete pointer with one method definition; unknown-interface control remains unknown |
| [#360](https://github.com/FinanceFlash/unvibecode/issues/360) | Normal Lane chunk lookup drops already-resolved receiver owner | Reported 28 wrong chunk targets in go-yaml, 16 production; source/order controls and retained input | Ours diverges earlier, before graph resolution, in both collectors. No competing same-name methods in the target file are required. We do not alter chunk lookup |
| [#364](https://github.com/FinanceFlash/unvibecode/issues/364) | Explicit generic call syntax not recognized as a call | Pinned samber/lo export omits a helper; reversible downstream edge control | Ours has no type arguments; the call exists as the wrong usage kind because its binding is missing |
| [#417](https://github.com/FinanceFlash/unvibecode/issues/417) | Dot-imported function searched only in source package | Missing helper implementation | Ours uses named results, not dot imports |
| [#341](https://github.com/FinanceFlash/unvibecode/issues/341) | Mutually exclusive build-constrained definitions indexed together | False ambiguity across platform implementations | Ours has one unambiguous concrete method and no build-constraint dependency |
| [#302](https://github.com/FinanceFlash/unvibecode/issues/302) | Root-only `go.mod`; package edges not visualized | Internal module imports lost or absent from map | Our module root resolves; imported-alias control succeeds throughout |
| [#497](https://github.com/FinanceFlash/unvibecode/issues/497), [#498](https://github.com/FinanceFlash/unvibecode/issues/498) | Go call edges mirrored as `file_import` in export | Duplicate/misclassified records | Our six-call count comes from distinct graph call-site identities; mirror records are not extra impact instances |

The package-global and factory-expression differential checks are committed in
`neighbor_boundaries` within the verification result. They provide concrete
separation from the two closest reports rather than wording-only separation.

## Other important reports reviewed

- [#590](https://github.com/FinanceFlash/unvibecode/issues/590): sink vocabulary
  accepts read-only loops; reported selector qualification/ranking controls are
  stronger evidence than a suspicious regex alone. We do not reuse that mechanism.
- [#451](https://github.com/FinanceFlash/unvibecode/issues/451): same root cause
  as the preserved JSONC investigation. It remains ineligible for a new issue.
- [#452](https://github.com/FinanceFlash/unvibecode/issues/452),
  [#455](https://github.com/FinanceFlash/unvibecode/issues/455),
  [#442](https://github.com/FinanceFlash/unvibecode/issues/442), and
  [#501](https://github.com/FinanceFlash/unvibecode/issues/501): baseUrl,
  inherited configuration, target wildcard substitution, and parent path
  normalization. None concerns the Go binding environment.
- [#591](https://github.com/FinanceFlash/unvibecode/issues/591): report CDN
  resources; unrelated rendering dependency mechanism.
- [#522](https://github.com/FinanceFlash/unvibecode/issues/522) and
  [#386](https://github.com/FinanceFlash/unvibecode/issues/386): relevant to the
  rejected/deferred Python and CSS candidate screens, not the selected report.
- [#325](https://github.com/FinanceFlash/unvibecode/issues/325) and
  [#481](https://github.com/FinanceFlash/unvibecode/issues/481): relationship
  type/documentation boundaries; our expectation is the documented concrete Go
  method-call behavior, not unsupported cross-language call analysis.

The strongest competing investigations (#360, #364, #590) connect a precise
mechanism to actual exported/selected output and use narrow causal controls.
That experimental standard informed our validation approach; their discovery,
code, language, repositories, and measurements are not our submission evidence.

## Assessment and refresh procedure

No same-mechanism report was identified in this snapshot. This is a bounded
search conclusion, not a guarantee against unpublished work or future issues.
The chief ambiguity is how broadly organizers group receiver-environment gaps;
our counterfactual checks show that #446/#415 require different corrections.
The issue draft explicitly names these neighbors rather than concealing them.

Before filing the owner-approved issue, rerun:

```sh
python investigations/go-named-results/reproduction/audit_issues.py --output refreshed-issue-audit.json
```

Read new bodies and relevant comments, compare causes, and stop filing if a
collision appears. Do not silently replace this snapshot or claim later
originality from it. No upstream issue, comment, PR, or form has been submitted.
