# Track 1 form response — unsubmitted

**Cohort / track:** Cohort 3, Track 1.

**Investigation title:** Typed Go method-value callbacks lose implementation
relationships and focused context.

**Official issue URL:** Not filed. After owner approval, publish the nine-section
draft upstream and use its actual URL here. The personal evidence PR is not an
official challenge issue.

**Evidence PR:** https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/3

**Summary:** UnvibeCode 0.3.15 discards a known local receiver when a method is
used as a callback value. Compiling fixture/control/correction/restoration runs
isolate the selector branch. Both real graph copies on unchanged go-redis restore
13 production references across six file pairs, with no lost original edges.
Actual focused exports restore five of seven complete source-specific method
definitions; two bounded cases are explicitly retained. Reference relationships
are distinguished from direct invocations. Source, budgets, and installed files
remain unchanged. Tests and compiler cases are reproducible in CI.

**What I learned:** A known type can still be lost when an AST visitor routes
two equivalent dependency forms through asymmetric branches. A graph delta alone
does not prove useful context recovery; complete-definition coverage and compiler
identities establish a stronger, bounded result. Rechecking originality invalidated
our earlier named-result draft when another investigator filed #596.

**Improvement suggestion:** Preserve typed method references through extraction
and owner-aware resolution, retaining them as references rather than direct calls.

**Boundaries:** No claim that a hosted final report changed, that every indirect
call is resolved, or that all callback implementations become complete. The 66
additional test references are separated from production impact. Refresh the
duplicate sweep immediately before official publication.

**Submission steps:** Review PR #3 and its CI evidence; approve the issue wording;
publish one official issue; replace the placeholder issue URL; submit the official
form. Neither publication nor form submission is authorized yet. Deadline recorded
from the challenge: 15 November 2026, 23:59 IST. Participant identity/contact fields
must use the owner's actual details, not invented values.
