# Independent replication on GORM

The same named-result binding defect is independently reproduced on unchanged
[go-gorm/gorm](https://github.com/go-gorm/gorm/tree/ead4e04ba7c6a49654649131e587133b1d9f3eca),
commit `ead4e04ba7c6a49654649131e587133b1d9f3eca` (162 scanned source files).
Both actual graph-engine copies give **3,948 → 3,961 → 3,948** call relationships
under stock/corrected/restored execution. The 13 gained calls include **12
production calls and one test-source call**, with no removed relationships.
Production changes collapse to three file pairs and two caller files.

This is a second application/library, not another syntax variant of the fixture.
The restored calls occur in GORM's query-building and persistence APIs, including
`Select`, `Save`, `CreateInBatches`, `FirstOrCreate`, and `Scan`.

## Actual exported implementation impact

We audit **all six distinct source-specific callee identities** reached by those
12 restored production calls. A target passes only when every nonblank line of
its complete original method definition matches selected target code. This
includes the declaration and body, not merely a symbol name or a file label.

| Selected caller file | Required implementation | Stock | Corrected | Restored |
| --- | --- | --- | --- | --- |
| `chainable_api.go` | `DB.AddError` | Absent | Complete | Absent |
| `finisher_api.go` | `DB.Clauses` | Absent | Complete | Absent |
| `finisher_api.go` | `DB.Model` | Absent | Complete | Absent |
| `finisher_api.go` | `DB.Set` | Absent | Complete | Absent |
| `finisher_api.go` | `DB.AddError` | Complete | Complete | Complete |
| `finisher_api.go` | `DB.Session` | Complete | Complete | Complete |

The table holds separately for Optimal and Wider. These are correlated views of
six maintenance questions, not twelve independent tasks. Four complete targets
are restored; two were already available through other links and serve as
controls. The single test-source edge is excluded from this production audit.

Concrete maintenance consequences:

- Invalid `Select` arguments call `AddError`: its body explains error translation,
  accumulation, and propagation into the result object.
- The slice path in `Save` calls `Clauses` and `Set`: their bodies establish how
  `OnConflict` is installed and where `gorm:update_track_time` is stored.
- The existing-row update path of `FirstOrCreate` calls `Model`: its body sets
  the statement model for that update.

These source implementations are available in the complete ZIP throughout.
The failure concerns the focused exports. No LLM answer or changed hosted risk
verdict has been measured.

The ordinary CLI's unmodified `chunks.jsonl`, `connections.jsonl`, and
`selections.jsonl` exactly equal the stock Fast Lane payload. Only the documented
local stage was requested (`--large-repo-token-limit 1 --no-open-browser`). The
Normal Lane replication executes its real graph builder and linker; it does not
claim a Normal Lane hosted review or a corrected Normal Lane context export.

## Reproduction

From the evidence repository root, after installing the pinned requirements:

```sh
git clone https://github.com/go-gorm/gorm.git .local-go-investigation/gorm
git -C .local-go-investigation/gorm checkout ead4e04ba7c6a49654649131e587133b1d9f3eca
python investigations/go-named-results/reproduction/replicate_gorm.py --repo .local-go-investigation/gorm --output gorm-verification.json --work .local-go-investigation/gorm-artifacts
go build -o .local-go-investigation/compiler-oracle investigations/go-named-results/reproduction/compiler_oracle.go
.local-go-investigation/compiler-oracle -repo .local-go-investigation/gorm -package . -cases gorm-verification-compiler-cases.json -output compiler-gorm.json
```

On Windows, give the built executable an `.exe` suffix. The compiler oracle uses
the standard `go/types` checker and compiled dependency exports, independently of
UnvibeCode and the correction. It verifies the exact source call, concrete
receiver, defining file, and definition span for each production relationship.
The generated cases omit the test-only call explicitly.

Local evidence:
[GORM verifier](evidence/gorm-verification.json),
[sanitized log](evidence/gorm-verification.log),
[LevelDB compiler oracle](evidence/compiler-leveldb.json).
The LevelDB oracle verified 6/6 production targets locally. The local GORM
compiler/test attempt was blocked by DNS resolution for `proxy.golang.org`;
no test pass is claimed from that attempt. The dedicated CI workflow additionally
runs the GORM compiler oracle and existing root-package tests in a clean Linux
environment. At commit `e852d05178593f46e9d1bddce54e2e7c799d2e65`,
[run 42369867686](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/actions/runs/42369867686)
passed: the independent compiler verified all 12 GORM production targets, and
the existing GORM root-package tests passed. Both Linux and Windows verification
jobs succeeded. The local DNS limitation above still accurately describes the
local attempt. Upstream #596 now covers the same named-result cause; this
replication is corroborating evidence, not an eligible separate issue.

## Bounded discovery search

Five additional public projects were screened: Gin, go-redis, gorilla/websocket,
bbolt, and GORM, each at the commit recorded in
[expansion-screen.json](evidence/expansion-screen.json). Full usage records were
compared to avoid mistaking same-line repeated symbol names for a change.
GORM was selected for its clear production export consequence. Other changes
were concentrated in test helpers, external types, or same-file methods and
were not promoted into additional impact claims.

No natural wrong-target alias-shadow case was established in this bounded
sample. That behavior remains demonstrated by the compiling fixture. This sample
does not establish ecosystem prevalence, and no new defect is bundled here.
