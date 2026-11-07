# Evidence guide

All current observations are generated from installed UnvibeCode **0.3.15**.
Local platform: Windows 11 build 26300, CPython 3.14.5. Parser dependencies:
tree-sitter 0.26.0, tree-sitter-language-pack 1.25.0. Tokenizer: tiktoken 0.14.0;
PyVis: 0.3.2. Go oracle: 1.27.3, downloaded from go.dev and checked against its
published archive SHA-256 before extraction. No installed engine file was edited.

| Artifact | Meaning |
| --- | --- |
| [verification.json](verification.json) | Both engine hashes; 54 extraction observations; package-global/factory boundary checks; five minimal full-pipeline states; pinned LevelDB stock/corrected/restored graph and selection checks |
| [cli-verification.json](cli-verification.json) | Ordinary CLI ZIP exactly equals stock pipeline chunks, connections and selections; entire ZIP contains `options.go`, but both focused scopes omit it |
| [go-compiler.json](go-compiler.json) | Nine parser fixture forms compile; original and equivalent local-result fixture pass identical runtime tests |
| [candidate-screen.json](candidate-screen.json) | Five preliminary screens and their dispositions |
| [issue-audit.json](issue-audit.json) | All 483 issue metadata/body hashes; mechanism-term matches; 25 nearest/important report checks and comment hashes |
| [ci-verification.json](ci-verification.json) | Immutable evidence commit's 12 successful checks, dedicated Linux/Windows steps, artifact metadata and explicit upload-scope boundary |
| [verification.log](verification.log) | Sanitized successful full-pipeline verifier stdout; paths abbreviated, numbers unchanged |
| [goleveldb-go-tests.log](goleveldb-go-tests.log) | Selected RUN/PASS summary lines from the existing upstream tests on unmodified pinned source; verbose operation traces omitted |

LevelDB: `https://github.com/syndtr/goleveldb`, commit
`126854af5e6d8295ef8e8bee3040dd8380ae72e8`, **95 scanned source files**.
The six regained production calls are four `session` calls in `newSession`
(`session.go:89,93,94,95`) and two `memDB.decref` calls (`db_write.go:78,105`).
They represent **three** distinct source/target file pairs and **two** caller
files. These are not six independent workflows or six distinct target files.

The `setOptions` task requires all five source fragments listed in `verify.py`.
It checks selected target code, not an import name or a relationship count.
The two scopes are correlated views of the same maintenance task, not two
independent answer tasks. No model was asked to answer it.

Full graphs, HTML, external JS stores, and ZIPs are reproducible with `--work`.
They remain outside Git to avoid large redundant artifacts. The ordinary CLI
used `--large-repo-token-limit 1 --no-open-browser` to intentionally obtain only
local outputs. Its PARTIAL status denotes the deliberately skipped business
stage. No hosted business workflow, business risk, or LLM accuracy is asserted.

CI verifies the affected-release symptom and correction, not a shipped product
fix. The dedicated workflow publishes an API-readable notice and uploads full
logs/results for its own head. See the personal PR checks for the live result;
historical JSONC CI is not evidence for this new finding.

The first evidence commit is `1bb14af9985ee373e316b660b98116ab79556a77`;
all 12 checks passed, including the dedicated Go jobs on Ubuntu and Windows.
The Linux job also executed the real-repository and CLI comparisons. Its
Windows CI companion deliberately skips those two steps; both ran locally on
Windows. Follow [PR #3 checks](https://github.com/Sohamgaonkhadkar/UnvibeCode-Engineering-Investigation/pull/3/checks)
for later heads. A follow-up fixes the minimal-ZIP upload glob, with no change
to behavioral assertions.

The preserved legacy verifier was run locally as well. Its initial hash check
detected Git's Windows CRLF checkout conversion in four JSONC/config artifacts.
Restoring their exact committed blob bytes made the complete verifier pass;
their tracked content and evidence hashes were not changed by this PR.
