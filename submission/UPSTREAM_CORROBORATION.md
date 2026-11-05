# Upstream corroboration draft — DRAFT, NOT FILED

**Status:** prepared 2026-11-05 and deliberately **unfiled**. Do not post this
comment, and do not file `GITHUB_ISSUE.md` as a new issue, without (a) explicit
approval from the repository owner and (b) maintainer/organizer direction that
independent corroborating evidence is wanted on the existing report.

## Why this file exists

The 2026-11-05 duplicate sweep of **434 upstream issues through #532**
([`DUPLICATE_CHECK.md`](../DUPLICATE_CHECK.md)) confirms that upstream
[`FinanceFlash/unvibecode#451`](https://github.com/FinanceFlash/unvibecode/issues/451)
already reports this investigation's locked mechanism: a legal JSONC root
`tsconfig.json` is strict-parsed, the failure is swallowed, and both copies of
`_load_tsconfig_aliases` return an empty alias table with no warning.

Consequences:

1. Filing `GITHUB_ISSUE.md` unchanged would create a **duplicate** issue and
   would misrepresent a mechanism that is already reported.
2. This investigation's evidence predates #451 (personal PR #1 created
   2026-11-01, merged 2026-11-02; PR #2 created 2026-11-02; #451 filed
   2026-11-03), so the work remains **independently derived**. That chronology
   is stated neutrally below and is not a priority claim against another
   contributor.
3. The correct upstream use of this material is therefore **corroboration and
   depth on #451**, not a second report.

Nothing in this file has been posted anywhere. No pull request has ever been
opened against `FinanceFlash/unvibecode`, and none is proposed here.

## Decision required before any upstream action

| Option | What it means | Blocker |
|---|---|---|
| A. Post the comment below on #451 | Attaches independently derived causal, impact, scope, and reference-solution evidence to the existing report | Needs maintainer/organizer direction that corroboration is wanted, plus owner approval |
| B. Organizer-directed supplementary submission | Submits this repository as supplementary evidence through whatever channel the organizer specifies, citing #451 as the upstream report | Needs the organizer to name the channel |
| C. Take no upstream action | Keep the evidence in the personal repository only; the submission cites the repository and the duplicate analysis | None — this is the current state |

Until one of these is chosen, the official submission's "GitHub issue URL"
field has **no honest value that this agent may invent**: #451 is not this
investigation's issue and must never be presented as such, and a duplicate
issue must not be filed to fill the field. The right move is to ask the
organizer which of the following they accept for that field — an existing
upstream issue that the work corroborates (clearly labelled as not filed by the
submitter), the evidence repository/PR link, or a deferral.

## Paste-ready comment text (Option A)

> **Independent corroboration + deeper evidence for this mechanism**
>
> I hit the same defect independently while investigating UnvibeCode 0.3.15 for
> the Cohort 3 Track 1 challenge, and published my evidence before this issue
> was filed (evidence PR #1 opened 2026-11-01, merged 2026-11-02; PR #2 opened
> 2026-11-02). I am not filing a duplicate — this comment is here to add
> corroborating depth in case it helps a maintainer.
>
> Confirmed identically: the supported repository-root `tsconfig.json` is read
> with strict `json.loads` inside a broad `except Exception: pass`, so legal
> JSONC (comments or trailing commas) leaves both engine copies of
> `_load_tsconfig_aliases` returning `{}` with no warning, and non-hardcoded
> aliases silently stop resolving.
>
> Evidence repository (pinned at
> [`db66414`](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/tree/db66414055bd14e5ea2e060e461c7d7ece05098c)):
>
> - **Causality, not correlation.** A reversible A/B/C/D/E intervention on both
>   resolver copies: original JSONC fails; removing only the comments restores
>   resolution; restoring the original fails again; patching only the loader in
>   memory restores it; restoring stock code fails again — with source hashes
>   verified unchanged and negative specifiers never resolving.
> - **Impact on two public repositories under ordinary installs.**
>   `meta/lexical@164af6a`: 4,256 internal file relationships, each
>   independently verified through the TypeScript 5.9.3 API, plus 2,707 direct
>   dependencies missing from as-is Optimal exported selections (3,345 Wider).
>   `ng-matero@d351bf59` replicates the pattern with 111 verified
>   relationships and 107 recovered direct dependencies.
> - **Effect on what a developer actually receives.** A deterministic
>   final-artifact audit of the real exported ZIPs: 0/6 predeclared
>   maintenance questions have all required answer-bearing lines as-is versus
>   6/6 in the comment-stripped control and in the loader-corrected bundle
>   (ng-matero 0/3 → 3/3), with negative controls passing throughout. An
>   exhaustive companion over 10,703 eligible source-specific symbol tasks
>   recovers 8,163 Optimal and 9,182 Wider definition/export instances.
>   Recovered instances concentrate in 101 Lexical target files (top target
>   28.3% of 4,218 distinct source→target pairs), so they are reported as
>   concentrated, not independent.
> - **Scope.** A digest-verified scan found the same vulnerable loader AST in
>   all 212 engine copies across the 106 published 0.3.0–0.3.15 PyPI wheels;
>   ordinary installs reproduce the exact symptom on CPython 3.11–3.14
>   (Ubuntu) and 3.12 (Windows, macOS). A bounded, non-random public-config
>   sample found 35 TypeScript-verified affected unique root-config contents
>   among 139 eligible (exposure evidence, explicitly not prevalence).
> - **A dependency-free reference loader** that agrees with TypeScript on
>   514/514 curated and generated valid documents, has zero critical
>   divergences across 2,277 adversarial cases, preserves comment-like
>   sequences inside string literals and error positions, rejects Python-only
>   constants and lone/elision commas, bounds nesting at 256 levels, and
>   distinguishes a genuinely missing config (silent `{}`) from an existing
>   unreadable/malformed one (exactly one structured `tsconfig_parse_failed`
>   or `tsconfig_read_failed` warning). It was validated in a disposable
>   file-level patched install, then restored to recorded stock hashes.
> - **Maintainer acceptance criteria** for a real fix, including that
>   `python reproduction/verify.py --expect-fixed` passes on both resolver
>   copies — see the repository README §9.2.
>
> Non-claims: no fix is shipped, no upstream pull request is proposed, and
> nothing here depends on hosted model output. Adjacent reports #452
> (`baseUrl`-only resolution), #455 (`extends`/effective config), #442
> (post-load target wildcards), and #501 (unnormalized relative `../`
> candidates) are distinct mechanisms and are deliberately out of scope.

## Filing checklist if Option A is approved

1. Re-run the duplicate sweep immediately before posting; the tracker moves
   daily. If #451 has been closed as fixed, do not post — verify against the
   fixed release instead with `reproduction/verify.py --expect-fixed`.
2. Re-pin every commit-SHA link to a reachable commit. If evidence PR #2 has
   been merged, prefer `main`-branch links so they survive branch deletion.
3. Confirm the comment contains no text, example, measurement, or structure
   copied from #451 or from any other contributor's submission. All numbers
   above come from this repository's own committed evidence.
4. Keep the chronology wording neutral: state dates, do not allege copying or
   claim priority over another contributor.
5. Do not modify the distributed package or open an upstream pull request as
   part of this action.
