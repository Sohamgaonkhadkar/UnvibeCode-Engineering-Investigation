# Originality check — 12 November 2026

The selected finding concerns a **known concrete receiver's non-call method value** being dropped before graph resolution.

The [complete audit](evidence/issue-audit-2026-11-12.json) covers **570 open/closed issue records through #682**: 567 nonempty bodies and 3 empty bodies. Pull requests are excluded. Each record has a body digest and mechanism-term results. The prior November 7 snapshot and November 11 report remain historical, rather than being relabeled as today's search.

Nearest-report comments were read through the GitHub connector and preserved in [the comment snapshot](evidence/nearest-comments-2026-11-12.json). The public REST comments request hit a rate limit; the auditor therefore accepts that separately captured, count-checked snapshot. No missing comment response is treated as a successful read.

| Report | Why it differs |
|---|---|
| [#360](https://github.com/FinanceFlash/unvibecode/issues/360) | Wrong receiver target after a call is emitted; our non-call reference is never emitted despite a known type. |
| [#415](https://github.com/FinanceFlash/unvibecode/issues/415) | Factory-expression receivers; the minimal case uses an explicitly typed ordinary parameter. |
| [#573](https://github.com/FinanceFlash/unvibecode/issues/573) | Interface dispatch; our receiver is concrete. |
| [#596](https://github.com/FinanceFlash/unvibecode/issues/596) | Missing named-result binding; the ordinary parameter is already bound correctly here. |
| [#625](https://github.com/FinanceFlash/unvibecode/issues/625) | Dropped export of stored unresolved-call diagnostics; our reference disappears earlier during extraction. |
| [#662](https://github.com/FinanceFlash/unvibecode/issues/662) | The current upload omits go.mod. Our matched hosted comparison uses the same uploaded files and a same-package method; only the callback expression differs. |
| [#318](https://github.com/FinanceFlash/unvibecode/issues/318) | Context scope and capacity behavior; relevant to the remaining two selected bodies, not the reference-extraction cause. |

No report of the same typed method-value mechanism was identified in the reviewed records. This is a time-bound search conclusion; repeat the check before official publication.

## Reproduce the audit

Save the all-pages issues-API response as an object containing `retrieved_at` and `items`. Then run:

```sh
python investigations/go-method-values/reproduction/audit_issues.py --snapshot /path/to/upstream-issues.json --comments-snapshot investigations/go-method-values/evidence/nearest-comments-2026-11-12.json --output ci-logs/issue-audit.json
```

A changed comment count fails the supplied-snapshot check. Omit the comments argument to fetch current nearest comments directly. Body matching helps locate reports; the distinction table also compares triggers, source stages and correction mechanisms.

The prior JSONC and named-result findings are excluded because #451 and #596 cover their causes. Their additional evidence does not create a new eligible issue.
