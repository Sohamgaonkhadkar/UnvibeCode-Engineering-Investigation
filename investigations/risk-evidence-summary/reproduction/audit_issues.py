"""Screen a preserved full REST issue snapshot; fetch nearest comments only.

Input format: {retrieved_at: UTC timestamp, items: REST issue objects}. Snapshot
must contain all open/closed pages; pull requests are explicitly excluded.
No issue or comment is created. Other participants' code is not republished.
"""
import argparse
import datetime
import hashlib
import json
import re
import urllib.request
from pathlib import Path

TERMS = ['evidence_summary', 'text_for_refs', 'has_source_pattern',
         'EXTERNAL_DEPENDENCY_CALL', 'narrative', 'negation',
         r'summary.{0,40}(source|proof)', r'metadata.{0,40}(source|proof)']
NEAREST = {355, 395, 409, 426, 437, 439, 513, 517, 590}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def matches(text):
    return [term for term in TERMS if re.search(term, text, re.I)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.snapshot.read_text(encoding='utf-8'))
    issues = [x for x in data['items'] if 'pull_request' not in x]
    rows = []
    for issue in issues:
        comments = []
        if issue['number'] in NEAREST and issue['comments']:
            for page in range(1, 30):
                req = urllib.request.Request(issue['comments_url'] + f'?per_page=100&page={page}',
                                             headers={'User-Agent': 'UnvibeCode-quality-investigation'})
                batch = json.load(urllib.request.urlopen(req, timeout=60))
                comments.extend(batch)
                if len(batch) < 100:
                    break
        rows.append({'number': issue['number'], 'title': issue['title'], 'url': issue['html_url'],
                     'state': issue['state'], 'body_sha256': sha(issue.get('body') or ''),
                     'matches': matches(issue['title'] + '\n' + (issue.get('body') or '')),
                     'nearest_report': issue['number'] in NEAREST,
                     'comments': [{'url': c['html_url'], 'body_sha256': sha(c['body']),
                                   'matches': matches(c['body'])} for c in comments]})
    result = {'snapshot_utc': data['retrieved_at'], 'comments_checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'snapshot_sha256': sha(args.snapshot.read_text(encoding='utf-8')),
              'issues': len(issues), 'newest_issue': max(x['number'] for x in issues),
              'terms': TERMS, 'nearest_reports': sorted(NEAREST), 'items': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    items = result.pop('items')
    header = json.dumps(result, indent=2).rstrip()[:-1]
    args.output.write_text(header + ',\n  "items": [\n' + ',\n'.join(
        '    ' + json.dumps(item) for item in items) + '\n  ]\n}\n', encoding='utf-8')
    print(f"Screened {len(issues)} open/closed issue bodies; nearest-report comments checked; newest #{result['newest_issue']}")


if __name__ == '__main__':
    main()
