# Artifact and version manifest

This manifest identifies the exact software, public source trees, and large
intermediate artifacts used to derive the compact evidence committed in this
repository. Full resolved graphs and context ZIPs are not committed because of
their size; their hashes below identify the local inputs from which the
committed JSON/JSONL summaries were generated. The separate GitHub Actions run
recomputed the same lexical counts under an ordinary installation.

## Software

| Item | Version / identity |
|---|---|
| UnvibeCode | `0.3.15` |
| Local manylinux wheel SHA-256 | `c7f22d70da1566f9f4c93c7587bfbb338722fd6e8d9c119485e0f691d07ba966` |
| Python, local evidence runs | 3.11.2 |
| Python, GitHub Actions | 3.12 (setup-python) |
| TypeScript oracle | 5.9.3 |
| Investigation commit used for the recorded CI runs | `5eca99bf64319afdf4e04983e2b6a06c6f1e9340` |

Both engine files containing `_load_tsconfig_aliases` were checked against the
 hashes in the installed wheel's `RECORD`:

| Installed file | Bytes | SHA-256 (hex) |
|---|---:|---|
| `shipreadyv2/engine_sources/00a_shipreadyv2_fast_lane_v11_api_context_bundle.py` | 330,966 | `bc3f6916ad25cde82e7aa9bd17e0cbbf82d4165155b987c4fefc874b2ca069ca` |
| `shipreadyv2/engine_sources/01_shipreadyv2_merged_graph_pipeline_5chunks.py` | 265,368 | `fb7abfa7c60cf7fe9f3d565c8f8e9140811cfe48f5ec5cf10fd2e1095aebbba1` |

## Public source trees and configs

| Repository | Pinned commit | Config artifact in this repo | SHA-256 |
|---|---|---|---|
| `meta/lexical` | `164af6a4df7114f35724c472152ca74877b6bd04` | `lexical_tsconfig_original.jsonc` | `58840d3690f0a5e6917693cedc6a93cee6af4d06b883a0022abf2689f936059b` |
| lexical control | same tree, five comment lines removed | `lexical_tsconfig_control.json` | `0f7733d055f7866c0985447bce9e739718c515a1379246ac3f210fcef81e61ad` |
| `ng-matero/ng-matero` | `d351bf5957d8c6dc9eca79d0c9b260c5b8d07822` | `ng-matero/tsconfig_as_is.json` | `d911557829a1cb7a18b8f89801b92dcaa4ff7d9a038b844207d372a0158a6a1c` |
| ng-matero control | same tree, two leading comment lines removed | `ng-matero/tsconfig_control.json` | `49b589e011b2b9bfbab73449b670412f060d698ddd8b54ce69cdaa15f4dc39b9` |

## Large local intermediate artifacts

### Lexical

| Artifact | SHA-256 |
|---|---|
| Resolved graph, as-is | `8ee970fe9686e6c7975fee3c5fc72bd8a4d4d087cd08de6f1a92d40ee90c903b` |
| Resolved graph, control | `9e5d2d246ea731b24367bccc7ecd4f40f2b56aaa02ccb36870325517dfe3ebff` |
| Repository-context ZIP, as-is | `0034d20ad51f357d053c0c7df399ffbeda3a94bac11366c72066ca8d8895d0cc` |
| Repository-context ZIP, control | `7846035172d91b82a13d75c96b9c3d86959256635b08bb08512f302115215815` |

### ng-matero

| Artifact | SHA-256 |
|---|---|
| Resolved graph, as-is | `88715a6f7313308d481920257b634eb307cf440880a0feb6b4df230878d0bdee` |
| Resolved graph, control | `b4fdf97748577ab113ed9755eb433737b9b4610f3255faaf671bd42b66e9dda7` |
| Repository-context ZIP, as-is | `0cc4c461260f416775d0858cf247d1f213738f1cbdf1fb277897a9045d6456b3` |
| Repository-context ZIP, control | `f95339abc3faa507981f9d4f57c46bb2cb04f9e0380ffb244e677fcd93a15287` |

## Compact derived evidence committed here

| File | Records / purpose |
|---|---|
| `lost_relationships.jsonl` | 4,256 lexical control-only relationships with source, line, specifier, target, pattern and strategy |
| `direct_selection_omissions.jsonl` | 6,052 lexical scope instances (2,707 Optimal + 3,345 Wider) where a verified direct dependency is absent as-is and restored in control |
| `selection_case_react_extension.json` | Chunk/file-level representative case |
| `alias_oracle_summary.json` / `selection_impact_summary.json` | Aggregate lexical inputs, hashes and classifications |
| `typescript_api_verification.json` | TypeScript-resolver batch cross-check: 4,256/4,256 lexical rows matched |
| `ng-matero/lost_relationships.jsonl` | 111 verified relationships in the independent repository |
| `ng-matero/typescript_api_verification.json` | TypeScript-resolver batch cross-check: 111/111 rows matched |
| `ng-matero/direct_selection_omissions.jsonl` | 214 scope instances (107 Optimal + 107 Wider) |

## GitHub Actions artifacts

See `CI_VERIFICATION.md` for run links and outcomes. Artifact digests:

- `jsonc-verification-logs`: `b4439f89ab4a945797dd44d790c0040c0ea8078f47fa76391c2a5de6444861d6`
- `lexical-clean-environment-evidence`: `ebb397b00484d0f55e050eda104d9a4652cd900a43e52a825a6da8674e661fb2`

## Regeneration outline

From this repository, with `unvibecode==0.3.15` installed normally and a pinned
lexical checkout/control prepared as documented in the README:

```bash
python reproduction/capture_run.py --repository "$LEXICAL" \
  --output-dir "$WORK/capture_lexical"
python reproduction/capture_run.py --repository "$LEXICAL_CONTROL" \
  --output-dir "$WORK/capture_lexical_ctrl"
python reproduction/analyze_alias_oracle.py \
  --graph-as-is "$WORK/capture_lexical/resolved_graph.json" \
  --graph-control "$WORK/capture_lexical_ctrl/resolved_graph.json" \
  --source-root "$LEXICAL" --tsconfig "$LEXICAL/tsconfig.json" \
  --lost-output "$WORK/lost_relationships.jsonl" \
  --summary-output "$WORK/alias_oracle_summary.json"
python reproduction/compare_selections.py \
  --bundle-as-is "$WORK/capture_lexical/repository-context.zip" \
  --bundle-control "$WORK/capture_lexical_ctrl/repository-context.zip" \
  --lost-relationships "$WORK/lost_relationships.jsonl" \
  --summary-output "$WORK/selection_impact_summary.json" \
  --omissions-output "$WORK/direct_selection_omissions.jsonl"
```
