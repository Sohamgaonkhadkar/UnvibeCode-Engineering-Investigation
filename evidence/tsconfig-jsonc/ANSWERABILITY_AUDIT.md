# Final-artifact answerability audit — lexical Optimal context

## Purpose

The graph and selection counts prove that direct dependencies are restored,
but they do not by themselves show what a developer can learn from the
exported context. This audit therefore asks six concrete maintenance
questions about `ReactExtension.tsx` and checks the **actual exported
repository-context ZIPs** for the exact implementation lines needed to answer
them.

Task definitions: [`../../reproduction/answerability_tasks.json`](../../reproduction/answerability_tasks.json)  
Audit script: [`../../reproduction/answerability_audit.py`](../../reproduction/answerability_audit.py)

## Method

- Repository: `meta/lexical@164af6a4df7114f35724c472152ca74877b6bd04`
- Source selection: `packages/lexical-react/src/ReactExtension.tsx`
- Scope: Optimal (radius 1)
- Bundles compared:
  1. **as-is** — stock UnvibeCode 0.3.15 on lexical's original JSONC config;
  2. **control** — stock package after removing only the five config comments;
  3. **corrected** — original config bytes retained, reference loader patched
     only in memory.
- For each question, the script joins `selections.jsonl` to `chunks.jsonl`,
  selects only chunks whose `file` is the named answering file, strips the
  bundle's line-number prefixes, and requires **every** listed evidence
  fragment to be present.
- Imports and call sites in `ReactExtension.tsx` cannot make a task pass;
  the answering implementation itself must be selected.
- `LexicalErrorBoundary.tsx` is a negative control already present in all
  three bundles.

This measures availability of answer-bearing implementation lines. It does
not invoke an LLM and does not claim that any particular model answer will
be correct.

## Tasks

| Question an engineer/assistant must answer from Optimal context | Answering implementation |
|---|---|
| When `ContentEditable` receives a placeholder, what accessibility prop is required and how is the placeholder rendered? | `LexicalContentEditable.tsx` |
| What are the two elements of `LexicalComposerContextWithEditor`, and how does `getTheme` fall back? | `LexicalComposerContext.ts` |
| What extension name does `ReactProviderExtension` declare, and why is it separate? | `ReactProviderExtension.tsx` |
| What does `invariant` do on a false condition, including `%s` interpolation? | `invariant.ts` |
| Does `defineExtension` transform its extension argument? | `defineExtension.ts` |
| When does `shallowMergeConfig` return the original object versus a new merged object? | `shallowMergeConfig.ts` |
| Negative control: how does `LexicalErrorBoundary` coerce non-`Error` values and what is its default fallback text? | `LexicalErrorBoundary.tsx` |

## Result

Clean GitHub Actions run:
https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/41627056006

| Bundle | Impact tasks answerable | Negative control |
|---|---:|---:|
| as-is | **0/6** | 1/1 |
| comment-stripped control | **6/6** | 1/1 |
| original config + reference loader in memory | **6/6** | 1/1 |

The run annotation reports the same result as:

```text
answer-bearing Optimal tasks as-is/control/corrected=0/6/6 of 6
```

The workflow uploads the complete machine-readable
`answerability_audit.json` in artifact `lexical-clean-environment-evidence`
(ID `13226761265`, SHA-256
`ca2c29e38093c0bc2a75aab780a89f6947703e820ef407c82628b39654bca69e`).

## Interpretation

For these six concrete questions, the as-is Optimal export does not contain
the required implementation lines—not merely fewer graph edges or a smaller
token total. Removing only comments, or keeping the original JSONC bytes and
using the reference loader, restores all six. The unchanged negative control
shows that the audit is not simply scoring the control higher because it
contains more text.

The claim remains bounded to these predeclared tasks and this representative
source. The exhaustive impact claim remains the separately measured 2,707
Optimal and 3,345 Wider direct-dependency recoveries across lexical.
