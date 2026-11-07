# Go named results disappear from the receiver environment

Intended new Cohort 3 Track 1 investigation. The earlier JSONC work remains at
the repository root and is corroborating research because upstream #451 reports
that mechanism. This investigation changes no upstream files and files no issue.

UnvibeCode 0.3.15 classifies `r.Save()` as a package selector when `r` is declared
in a Go function's named result list. Its type is explicit, but the collector
binds only receivers and input parameters before visiting the function body.
An unimported `r` silently loses the call; an imported alias `r` can instead
produce a high-confidence link to an unrelated package function.

The minimal compiling example calls `Store.Save`, while the stock graph and
exported connection identify `remote.Save`. Replacing the named result with an
equivalent local declaration restores the right edge. Adding **one environment
binding** restores it with the original source unchanged. Restoration reproduces
the wrong result. The package-qualified control remains correct throughout.

On unchanged [syndtr/goleveldb at `126854af5e6d8295ef8e8bee3040dd8380ae72e8`](https://github.com/syndtr/goleveldb/tree/126854af5e6d8295ef8e8bee3040dd8380ae72e8),
the same correction restores six production method calls across three distinct
source/target file pairs, with zero removed edges: **1,858 → 1,864 → 1,858**.
For `leveldb/session.go`, both Optimal and Wider exports omit all of
`leveldb/options.go` as-is. The correction includes the actual `setOptions`
implementation, including comparer/filter adaptation and cached option setup.
The implementation exists in the complete ZIP throughout; the demonstrated
loss concerns focused selections, not loss of the whole source archive.

The ordinary CLI's stock bundle was checked too: all 1,141 chunks, 2,035
exported relationship records, and 95 selections exactly equal the local
pipeline's payloads. Relationship records are not counted as distinct calls.

## Reproduce

From the investigation repository root, using Python 3.12 or newer:

```sh
python -m venv .venv
# Activate .venv using your platform's usual command.
python -m pip install -r investigations/go-named-results/reproduction/requirements.txt
python investigations/go-named-results/reproduction/verify.py --output minimal-result.json
git clone https://github.com/syndtr/goleveldb.git .local-go-investigation/goleveldb
git -C .local-go-investigation/goleveldb checkout 126854af5e6d8295ef8e8bee3040dd8380ae72e8
python investigations/go-named-results/reproduction/verify.py --real-repo .local-go-investigation/goleveldb --output full-result.json
python investigations/go-named-results/reproduction/compile_controls.py --output compiler-result.json
```

`compile_controls.py` also requires Go on PATH. The parser package downloads its
grammar on first use. A grammar/setup failure makes verification fail; empty
extraction is never treated as a successful reproduction. Add `--work <directory>`
to retain full generated graph/HTML/ZIP artifacts; otherwise they are temporary.

To inspect the normal CLI's **local** artifacts without hosted business review:

```sh
python -m unvibecode review --repository .local-go-investigation/goleveldb --large-repo-token-limit 1 --no-open-browser
```

The hidden size threshold deliberately skips hosted analysis and reports PARTIAL.
That status is expected for this command and is not the reported defect. See the
[CLI checker](reproduction/check_cli.py) for payload comparison. No hosted risk
verdict, model answer, or full business-review completion is claimed.

## Evidence and review

- [Root cause and correction](ROOT_CAUSE.md)
- [Five-candidate decision record](CANDIDATES.md)
- [Fresh duplicate audit and competition comparison](DUPLICATE_CHECK.md)
- [Machine-readable behavioral verification](evidence/verification.json)
- [Normal CLI comparison](evidence/cli-verification.json)
- [Evidence guide and limitations](evidence/README.md)
- [Reference correction](solution/named_results.py), applied only in memory
- [Nine-section issue draft](submission/GITHUB_ISSUE.md)
- [Google Form response draft and owner fields](submission/FORM_RESPONSE.md)

Green reproduction checks mean the pinned stock defect was observed and the
reference correction passed controls. They do not mean UnvibeCode ships a fix.
[Personal review PR #3](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/3)
must remain unmerged for owner review. Its initial evidence commit passed all
12 checks; [CI provenance](evidence/ci-verification.json) distinguishes that
snapshot from later live checks. The official
issue and Google Form remain unsubmitted.
