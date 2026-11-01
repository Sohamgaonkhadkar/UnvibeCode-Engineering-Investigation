#!/usr/bin/env python3
"""Independent integrity verifier for UnvibeCode's Complete Repository Context bundle.

Checks (oracle = bundle's own stated contracts + the source files, never another model):
  V1 manifest counts vs actual JSONL row counts / distinct files
  V2 referential integrity: connection & selection chunk IDs resolve; duplicate chunk IDs
  V3 chunk fidelity: numbered_code line numbers vs line_range; chunk text vs actual source lines
  V4 per-file line coverage: gaps (source lines in no chunk), overlaps, conflicting copies
  V5 selection sanity: estimated_tokens vs maximum_tokens; scope chunk-ID monotonicity (measured)
Usage: verify_bundle.py <extracted_bundle_dir> <source_repo_dir>
Exit 0 = all hard checks pass; 1 = violations found. Soft measurements are reported, not failed.
"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

BUNDLE, REPO = Path(sys.argv[1]), Path(sys.argv[2])
load = lambda n: [json.loads(l) for l in (BUNDLE / n).read_text(encoding="utf-8").splitlines() if l.strip()]
manifest = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
chunks, conns, sels = load("chunks.jsonl"), load("connections.jsonl"), load("selections.jsonl")
fails, notes = [], []
def fail(check, msg): fails.append(f"[{check}] {msg}")

# ---- V1 manifest truthfulness
if manifest.get("atomic_code_sections") != len(chunks):
    fail("V1", f"manifest atomic_code_sections={manifest.get('atomic_code_sections')} != chunks rows={len(chunks)}")
if manifest.get("verified_cross_file_connections") != len(conns):
    fail("V1", f"manifest verified_cross_file_connections={manifest.get('verified_cross_file_connections')} != connections rows={len(conns)}")
chunk_files = {c["file"] for c in chunks}
if manifest.get("source_files") != len(chunk_files):
    fail("V1", f"manifest source_files={manifest.get('source_files')} != distinct chunk files={len(chunk_files)}")
sel_files = {s["file"] for s in sels}
if sel_files != chunk_files:
    fail("V1", f"selections files != chunk files (only-in-selections={sorted(sel_files-chunk_files)[:5]}, only-in-chunks={sorted(chunk_files-sel_files)[:5]})")
if manifest.get("skipped_files"):
    notes.append(f"manifest skipped_files={manifest['skipped_files']}")

# ---- V2 referential integrity
ids = [c["chunk_id"] for c in chunks]
dup = [i for i, n in Counter(ids).items() if n > 1]
if dup: fail("V2", f"duplicate chunk_id values: {dup[:5]}")
idset = set(ids)
dangling = 0
for c in conns:
    for k in ("source_chunk", "target_chunk"):
        if c.get(k) not in idset: dangling += 1
if dangling: fail("V2", f"{dangling} connection endpoints reference nonexistent chunk IDs")
bad_sel = sum(1 for s in sels for sc in s["scopes"].values() for i in sc["chunk_ids"] if i not in idset)
if bad_sel: fail("V2", f"{bad_sel} selection chunk_ids reference nonexistent chunks")
by_id = {c["chunk_id"]: c for c in chunks}
for c in conns:  # endpoint file fields must agree with the referenced chunk's file
    for ck, fk in (("source_chunk", "source_file"), ("target_chunk", "target_file")):
        ch = by_id.get(c.get(ck))
        if ch and ch["file"] != c.get(fk):
            fail("V2", f"connection {fk}={c.get(fk)} but chunk {c.get(ck)} is in {ch['file']}"); break

# ---- V3 chunk fidelity vs source + V4 coverage
NUM = re.compile(r"^\s*(\d+)\s\|\s?(.*)$")
src_cache = {}
def srclines(rel):
    if rel not in src_cache:
        p = REPO / rel
        src_cache[rel] = p.read_text(encoding="utf-8", errors="surrogateescape").splitlines() if p.is_file() else None
    return src_cache[rel]
coverage = defaultdict(dict)  # file -> line_no -> text (from chunks)
conflicts = 0
for c in chunks:
    rel, lr = c["file"], c["line_range"]
    lines, nums = [], []
    for raw in c["numbered_code"].splitlines():
        m = NUM.match(raw)
        if not m: fail("V3", f"{c['chunk_id']} ({rel}): unnumbered line {raw[:60]!r}"); continue
        nums.append(int(m.group(1))); lines.append(m.group(2))
    if not nums: fail("V3", f"{c['chunk_id']} ({rel}): empty numbered_code"); continue
    if (nums[0], nums[-1]) != (lr["start_line"], lr["end_line"]):
        fail("V3", f"{rel} {c['chunk_id']}: numbered {nums[0]}-{nums[-1]} != line_range {lr['start_line']}-{lr['end_line']}")
    if nums != list(range(nums[0], nums[-1] + 1)):
        fail("V3", f"{rel} {c['chunk_id']}: line numbers not contiguous")
    src = srclines(rel)
    if src is None: fail("V3", f"chunk file missing on disk: {rel}"); continue
    for n, text in zip(nums, lines):
        if n < 1 or n > len(src):
            fail("V3", f"{rel}:{n} beyond EOF ({len(src)} lines) in {c['chunk_id']}"); continue
        if src[n - 1] != text:
            fail("V3", f"{rel}:{n} chunk text != source | chunk={text[:70]!r} src={src[n-1][:70]!r}")
        prev = coverage[rel].get(n)
        if prev is not None and prev != text: conflicts += 1
        coverage[rel][n] = text
if conflicts: fail("V4", f"{conflicts} source lines appear with conflicting text in different chunks")
gap_summary, overlap_files = {}, 0
for rel in sorted(chunk_files):
    src = srclines(rel) or []
    covered = coverage[rel]
    gaps = [n for n in range(1, len(src) + 1) if n not in covered]
    # collapse gaps to ranges; separate blank-only gaps from code gaps
    code_gaps = [n for n in gaps if src[n-1].strip()]
    if code_gaps: gap_summary[rel] = code_gaps
    per_chunk_counts = Counter()
    for c in chunks:
        if c["file"] == rel:
            for n in range(c["line_range"]["start_line"], c["line_range"]["end_line"] + 1): per_chunk_counts[n] += 1
    if any(v > 1 for v in per_chunk_counts.values()): overlap_files += 1
if gap_summary:
    tot = sum(len(v) for v in gap_summary.values())
    fail("V4", f"{tot} non-blank source lines in {len(gap_summary)} files appear in NO chunk; e.g. " +
         "; ".join(f"{f}:{v[:6]}" for f, v in list(gap_summary.items())[:4]))
notes.append(f"files with overlapping chunk ranges (measured, may be by design): {overlap_files}/{len(chunk_files)}")

# ---- V5 selections (measurements; budget breach is a hard fail per docs' stated budgets)
over = [(s["file"], k, sc["estimated_tokens"], sc["maximum_tokens"]) for s in sels for k, sc in s["scopes"].items()
        if sc["estimated_tokens"] > sc["maximum_tokens"]]
if over: fail("V5", f"{len(over)} selections exceed their own maximum_tokens; e.g. {over[:3]}")
nonmono = 0
for s in sels:
    scopes = [s["scopes"][k] for k in sorted(s["scopes"], key=lambda x: int(x))]
    for a, b in zip(scopes, scopes[1:]):
        if not set(a["chunk_ids"]) <= set(b["chunk_ids"]): nonmono += 1
notes.append(f"non-monotonic scope inclusions (measured; cf. upstream #318): {nonmono}")

print(f"bundle={BUNDLE} repo={REPO}")
print(f"chunks={len(chunks)} connections={len(conns)} selections={len(sels)} files={len(chunk_files)}")
for n in notes: print("NOTE:", n)
# de-duplicate repeated V3 text mismatches for readability, keep counts
seen, shown = Counter(), []
for f in fails:
    key = f.split(":", 1)[0]
    seen[key] += 1
    if seen[key] <= 12: shown.append(f)
for f in shown: print("FAIL:", f)
hidden = len(fails) - len(shown)
if hidden: print(f"... plus {hidden} more failures (grouped above)")
print("RESULT:", "PASS" if not fails else f"FAIL ({len(fails)} violations)")
sys.exit(0 if not fails else 1)
