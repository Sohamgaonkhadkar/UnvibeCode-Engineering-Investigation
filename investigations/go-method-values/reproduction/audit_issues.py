"""Read a full public issues snapshot; audit nearest comments without upstream writes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import urllib.request
from pathlib import Path

TERMS = [r"method.?values?", r"method_reference", r"package_selector",
         r"selector_expression", r"typed.{0,40}callback", r"callback",
         r"ForEachShard", r"processTxPipeline"]
NEAREST = {
    360: "Wrong receiver target for an emitted call; here the known receiver's non-call usage is never emitted.",
    415: "Factory-expression receivers; this reproducer uses an explicitly typed ordinary parameter.",
    573: "Interface dispatch; the fixture receiver is a concrete *Store.",
    596: "Named-result environment binding; the ordinary parameter is already correctly bound here.",
    625: "Exporting unresolved Go diagnostics; this reference is absent before graph resolution, not a stored diagnostic lost during export.",
    662: "Current uploader omits go.mod; the matched hosted controls exercise a same-package Store method and differ only in callback expression.",
    318: "Context-scope selection budgets; relevant to remaining omissions, not the method-reference extraction cause.",
}

def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def matches(text):
    return [term for term in TERMS if re.search(term, text, re.I)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--comments-snapshot", type=Path)
    args = parser.parse_args()
    captured = json.loads(args.comments_snapshot.read_text(encoding="utf-8")) if args.comments_snapshot else None
    data = json.loads(args.snapshot.read_text(encoding="utf-8"))
    issues = [r for r in data["items"] if "pull_request" not in r]
    items = []
    for issue in issues:
        comments = []
        if captured and issue["number"] in NEAREST:
            assert str(issue["number"]) in captured["issues"], "Missing nearest-report comments"
            comments = captured["issues"][str(issue["number"])]
            assert len(comments) == issue["comments"], "Comment snapshot count drift"
        elif issue["number"] in NEAREST and issue["comments"]:
            for page in range(1, 30):
                request = urllib.request.Request(issue["comments_url"]+f"?per_page=100&page={page}",
                    headers={"User-Agent":"UnvibeCode-quality-investigation"})
                batch = json.load(urllib.request.urlopen(request, timeout=60))
                comments.extend(batch)
                if len(batch) < 100:
                    break
        text = issue["title"]+"\n"+(issue.get("body") or "")
        items.append({"number":issue["number"], "url":issue["html_url"], "title":issue["title"],
            "state":issue["state"], "updated_at":issue["updated_at"],
            "body_sha256":sha(issue.get("body") or ""), "body_empty":not bool(issue.get("body")),
            "matched_terms":matches(text), "distinct_cause_review":NEAREST.get(issue["number"]),
            "comments":[{"url":c.get("html_url") or c["url"], "body_sha256":sha(c["body"]), "matched_terms":matches(c["body"])} for c in comments]})
    result = {"full_snapshot_utc":data["retrieved_at"], "comments_checked_utc":datetime.now(timezone.utc).isoformat(),
        "comment_source":captured["source"] if captured else "GitHub REST all comment pages",
        "comment_snapshot_checked_at":captured["checked_at_utc"] if captured else None,
        "snapshot_sha256":sha(args.snapshot.read_text(encoding="utf-8")),
        "issue_records":len(issues), "nonempty_issue_bodies":sum(bool(r.get("body")) for r in issues),
        "empty_issue_bodies":sum(not bool(r.get("body")) for r in issues),
        "pull_requests_excluded":len(data["items"])-len(issues),
        "newest_issue":max(r["number"] for r in issues), "terms":TERMS,
        "nearest_reports":NEAREST, "conclusion":"Search inventory only; human mechanism-level assessment is recorded in DUPLICATE_CHECK.md."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    header=json.dumps(result,indent=2).rstrip()[:-1]
    args.output.write_text(header+',\n  "items": [\n'+',\n'.join('    '+json.dumps(i) for i in items)+'\n  ]\n}\n',encoding="utf-8")
    print(f"Audited {len(issues)} issue records ({result['nonempty_issue_bodies']} nonempty bodies), through #{result['newest_issue']}; nearest comments checked.")

if __name__ == "__main__":
    main()
