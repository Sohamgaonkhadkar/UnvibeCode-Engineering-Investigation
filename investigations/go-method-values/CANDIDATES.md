# Candidate screening

Candidates were screened for duplicate mechanisms, reproducibility and demonstrated developer impact. The selected finding is the typed Go method-value reference omission.

| Candidate | Observation and decision |
|---|---|
| JSONC alias loader | Deeply verified; excluded because #451 reports the same cause. |
| Go named results | Compiler/public-project evidence; excluded after collision with #596. |
| Risk narrative/source proof | Actual selector-file experiments; provisional because #437 refers to earlier summary-text research. |
| Go collection/range receiver binding | Excluded before deeper work: #542 covers the mechanism. |
| JS re-export statements | Excluded: #256 and #494 already report that family of omission. |
| Python except-star import certainty | Parser difference measured; meaningful downstream context impact not established. |
| CSS nested assets | Extraction difference; support and overlap with existing asset reports unresolved. |
| Context serialization | Round-trip control passed; hypothesis falsified. |
| Typed Go method values | Selected: known receiver, compiling controls, both graph implementations, public go-redis exports, independent compiler identities, and a current-client matched observation. |

A bounded screen considered Gin, go-redis, bbolt, GORM and LevelDB. Raw typed selectors include ordinary fields, so their counts are not reported as missing methods. Actual cross-file production references and exported definitions determine the impact claim.

The selected cause is narrower than general callback execution: a static method-definition reference is omitted before owner-aware resolution. The reference correction repairs that loss; the separate selection-capacity experiment explains why graph recovery does not guarantee every method body fits into a bounded export.
