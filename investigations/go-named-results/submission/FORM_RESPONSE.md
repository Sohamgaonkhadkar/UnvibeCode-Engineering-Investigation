# Google Form draft — unsubmitted

> **ARCHIVED — DO NOT SUBMIT.** Upstream #596 covers this cause.
> See ../ELIGIBILITY.md. Earlier originality checks are historical snapshots.

Official form checked 7 November 2026:
[Challenge entry](https://docs.google.com/forms/d/1an-hce3EQ8bUVArnZJnD1VwxQIxgmNzLKYQ8h814CVE/viewform).
Deadline: **15 November 2026, 11:59 PM IST**.

This is a preparation document, not an upstream issue or a submitted form.
Owner must review the issue, refresh the duplicate audit, file the approved
issue, then replace the issue-URL placeholder below. No competitor issue or
personal PR can stand in for that URL.

| Current form field | Draft / owner action |
| --- | --- |
| 1. Name or team name (required) | Soham Gaonkhadkar — owner to confirm |
| 2. Email (required) | OWNER TO ENTER |
| 3. Brief feedback, under 200 words (required) | Draft below; the form requests personal feedback, so owner should review and rewrite in their own voice |
| 4. GitHub issue link (Track 1) | **PENDING — official issue not filed** |
| 5. Track 2 proposal | Leave blank; this work targets Track 1 |
| 6. Creative bonus (optional) | Leave blank |
| 7. Originality / no private data confirmation (required) | Owner to confirm after reviewing evidence and refreshing duplicates |
| 8. GitHub profile (optional) | https://github.com/Sohamgaonkhadkar |
| 9. College name and year (required) | OWNER TO ENTER |
| 10. College referral or NA | OWNER TO ENTER |

Suggested brief feedback for owner editing:

> The local Connected Code and repository ZIP make relationships inspectable and
> reproducible. I found a concrete gap in Go receiver resolution: named result
> variables are treated as package qualifiers. On pinned LevelDB source this
> removes six method calls and omits session option initialization from focused
> context. A minimal compiling fixture also shows a wrong link when the result
> shadows an import alias. The evidence includes passing controls, reversible
> experiments, real exported artifacts, and a one-line reference correction per
> engine. Unknown or missing relationships should be visible so sparse context
> does not appear complete.

Supporting submission notes (the current form does not have separate fields for
all of these; retain them in the linked issue):

- Repository analyzed: `https://github.com/syndtr/goleveldb`.
- Exact commit: `126854af5e6d8295ef8e8bee3040dd8380ae72e8`.
- Defect: Go named result parameters are omitted from the collector's local
  receiver environment, producing missing or incorrectly routed method links.
- Root cause: `_collect_go_usages.visit` binds `receiver` and `parameters` but
  omits `result` in both shipped engines.
- Evidence: 54 extraction checks on both copies; five full fixture pipeline
  states; runtime/compiler controls; stock/corrected/restored LevelDB graph
  1,858/1,864/1,858 with no lost edges; real CLI payload equality.
- Developer impact: actual `setOptions` implementation absent from Optimal and
  Wider session context as-is and present after the reference correction.
- Verification and draft: [investigation README](../README.md),
  [issue draft](GITHUB_ISSUE.md), [duplicate audit](../DUPLICATE_CHECK.md).

Submission order: approve personal PR → refresh duplicates → approve and file
the official issue → paste its real URL → complete owner-only form fields →
owner approval before submitting the form. Merging the personal PR is an owner
decision; an upstream challenge PR must not be opened.
