# Release scope and public-config exposure

Snapshot date: **2026-11-03**

This note answers two bounded questions:

1. Which published UnvibeCode artifacts contain the vulnerable alias loader?
2. Do public root `tsconfig.json` files with declared path aliases actually
   use the JSONC syntax that triggers it?

It does **not** estimate the number of affected UnvibeCode users.

## 1. Published-release scope

Script: [`../../reproduction/version_scope.py`](../../reproduction/version_scope.py)  
Machine-readable result: [`version_scope.json`](version_scope.json)

Command:

```bash
python reproduction/version_scope.py \
  --all-wheels \
  --through 0.3.15 \
  --output evidence/tsconfig-jsonc/version_scope.json
```

Method:

- Read the PyPI JSON metadata for `unvibecode`.
- Download **every published wheel** for releases 0.3.0 through 0.3.15.
- Verify each download against the SHA-256 published by PyPI.
- Inspect both `shipreadyv2/engine_sources` copies in every wheel.
- Fingerprint `_load_tsconfig_aliases` by AST and check for strict
  `json.loads` plus `except Exception: pass`.
- Execute each unique extracted function (not the whole engine) against
  strict-JSON and JSONC configs declaring the same alias.

Result:

| Measure | Count |
|---|---:|
| Releases scanned (0.3.0–0.3.15) | 16 |
| Published wheels scanned | 106 |
| Engine copies scanned | 212 |
| Unique `_load_tsconfig_aliases` AST fingerprints | 1 |
| Releases whose scanned wheels contain the vulnerable behaviour | 16/16 |

The single AST SHA-256 is:

```text
2a4467d270e82bb82b311f8804114736746394be3f0535175d9c3cfe39319495
```

The extracted loader returns `{"@app": "src/app"}` for the strict-JSON
control and `{}` for the semantically identical JSONC config.

### Limits

- This is a PyPI-wheel scope statement, not a statement about source
  branches, sdists as separate artifacts, or non-PyPI builds.
- Behaviour is executed once for the one unique AST rather than 212 times;
  every copy is separately fingerprinted and structurally checked.
- Release 0.3.12 had only one published wheel in the metadata snapshot; the
  release-level conclusion for 0.3.12 is therefore based on that sole wheel.

### Ordinary-install behavioural matrix

The PR workflow separately installs `unvibecode==0.3.15` normally and runs
`reproduction/verify.py --skip-evidence` on:

- CPython 3.11, 3.12, 3.13, and 3.14 on `ubuntu-latest`;
- CPython 3.12 on `windows-latest`; and
- CPython 3.12 on `macos-latest`.

All six jobs reproduce the exact empty-alias symptom, exact post-fix
regression failure shape, reference-loader restoration, and both-engine
reversible sequence. This complements the static all-wheel fingerprint scan;
it is not a claim that every one of the 106 platform wheels was installed
and executed.

## 2. Public root-config exposure sample

Script: [`../../reproduction/ecosystem_exposure.py`](../../reproduction/ecosystem_exposure.py)  
Machine-readable result: [`ecosystem_exposure_sample.json`](ecosystem_exposure_sample.json)

Exact GitHub code-search query:

```text
filename:tsconfig.json extension:json "compilerOptions" "paths"
```

The first three result pages were retrieved. Only results whose path is
exactly `tsconfig.json` (repository root) were retained, deduplicated by
repository/path, and downloaded by the returned Git blob SHA.

A config was **eligible** only if:

- the reference loader could parse it;
- `compilerOptions.paths` was a non-empty object; and
- at least one alias could be extracted.

An eligible config was **affected in the sample** only if:

- strict `json.loads` rejected it; and
- TypeScript 5.9.3 `parseConfigFileTextToJson` reported no error.

For all 184 eligible configs, the `paths` value returned by TypeScript
matched the reference parser's value.

### Results

| Unit of counting | Retrieved | Eligible | TypeScript-verified affected | Path entries in affected configs |
|---|---:|---:|---:|---:|
| Unique repositories/root configs | 210 | 184 | 44 | 211 |
| Unique config contents | 164 | 139 | 35 | 174 |

The conservative headline is the unique-content row: **35 distinct affected
root-config contents containing 174 declared path entries**. Counting unique
repositories instead gives 44 affected repositories. Template/duplicate
configs explain why the two units differ.

Among the 44 affected repository configs, feature counts overlap:

- line comments: 31
- block comments: 20
- trailing commas: 11
- BOM: 0

### Direct installed-loader behaviour on the same sample

Script: [`../../reproduction/ecosystem_loader_behavior.py`](../../reproduction/ecosystem_loader_behavior.py)
Machine-readable result: [`ecosystem_loader_behavior.json`](ecosystem_loader_behavior.json)

To remove strict-JSON rejection as a proxy, every eligible blob was fetched
again by its committed Git blob SHA, checked against its recorded byte count
and SHA-256, and used as the root config for both installed 0.3.15 resolver
copies. Each engine was then repeated with the reference loader in memory and
compared with the aliases produced by applying the shipped mapping rules to
the reference-parsed config.

| Unit | Affected: stock empty both engines | Affected: reference exact both | Unaffected: stock exact both | Unaffected: reference exact both |
|---|---:|---:|---:|---:|
| Repository/root config | **44/44** | **44/44** | **140/140** | **140/140** |
| Unique content | **35/35** | **35/35** | **104/104** | **104/104** |

The 211 declared `paths` entries in affected repository configs collapse to
163 entries under the shipped alias-mapping rules (174→126 after content
deduplication), because exact and wildcard declarations can map to the same
alias prefix. The behavioral audit preserves that distinction.

### What this does and does not prove

It proves that, in an auditable time-bound sample of public root configs,
the triggering syntax co-occurs with real declared aliases. That supports
practical exposure beyond two pinned benchmark repositories.

It does **not** prove that 23.9%, 25.2%, or any other percentage of all
TypeScript projects or UnvibeCode users are affected. GitHub code search is
best-match/index ordered, sees only indexed public code, and the query itself
selects files mentioning `compilerOptions` and `paths`. Accordingly, the
submission reports exact sample counts and never turns the sample share into
an ecosystem prevalence estimate.

Repository names, blob SHAs, content SHA-256 values, classifications, and
feature flags are retained in the JSON. Config bodies are not copied into
this repository.

## Interpretation for the fix

- The vulnerable loader is present across the whole published 0.3.0–0.3.15
  wheel line in the snapshot, so the correction is relevant to the current
  release and to users pinned to earlier 0.3.x wheels.
- The exposure sample contains configs whose aliases are directly emptied by
  both installed stock loaders and exactly recovered by the reference
  solution. It is supporting impact
  evidence; the causal and graph-level proof remains the pinned lexical and
  ng-matero experiments.
