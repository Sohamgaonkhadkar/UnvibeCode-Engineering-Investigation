"""Refresh all open/closed issue bodies and comments on nearest Go reports.

No authentication needed; no writes to upstream. Save compact provenance, not
other participants' reproduction code. Search terms intentionally include
root-cause function names as well as symptom names.
"""
import argparse
import datetime
import hashlib
import json
import re
import urllib.request
from pathlib import Path

API = 'https://api.github.com/repos/FinanceFlash/unvibecode'
TERMS = [r'named.?result', r'named.?return', r'result.?parameter', r'parameter_types',
         r'_collect_go_usages', r'shadow', r'newSession', r'setOptions']
REVIEW = {234,302,325,341,360,364,415,417,446,454,481,497,498,542,547,573,
          451,452,455,442,501,590,591,522,386}


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent':'UnvibeCode-quality-investigation'})
    return json.load(urllib.request.urlopen(request, timeout=60))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    all_rows = []
    issue_pages = 0
    for page in range(1, 30):
        issue_pages += 1
        rows = get(f'{API}/issues?state=all&per_page=100&page={page}')
        all_rows.extend(rows)
        if len(rows) < 100:
            break
    issues = [x for x in all_rows if 'pull_request' not in x]
    summaries = []
    for row in issues:
        text = row['title'] + '\n' + (row.get('body') or '')
        matches = [term for term in TERMS if re.search(term, text, re.I)]
        comments = []
        if row['number'] in REVIEW:
            page = 1
            while True:
                batch = get(row['comments_url']+f'?per_page=100&page={page}') if row['comments'] else []
                comments.extend(batch)
                if len(batch) < 100: break
                page += 1
            print('reviewed', row['number'], 'comments',len(comments),flush=True)
        summaries.append({'number':row['number'], 'url':row['html_url'], 'title':row['title'],
            'state':row['state'], 'updated_at':row['updated_at'], 'body_sha256':digest(row.get('body') or ''),
            'matched_terms':matches, 'close_report_body_reviewed':row['number'] in REVIEW,
            'comments':[{'url':c['html_url'], 'updated_at':c['updated_at'],
                'body_sha256':digest(c.get('body') or ''),
                'matched_terms':[term for term in TERMS if re.search(term,c.get('body') or '',re.I)]} for c in comments]})
    result = {'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'endpoint':API+'/issues?state=all&per_page=100', 'pages':issue_pages,
        'issues':len(issues), 'pull_requests_excluded':len(all_rows)-len(issues),
        'newest_issue':max(x['number'] for x in issues), 'terms':TERMS,
        'close_reports':sorted(REVIEW), 'items':summaries}
    # One issue per line keeps the complete audit compact and reviewable.
    items = result.pop('items')
    header = json.dumps(result, indent=2).rstrip()[:-1]
    payload = header + ',\n  "items": [\n' + ',\n'.join('    '+json.dumps(x) for x in items) + '\n  ]\n}\n'
    args.output.write_text(payload,encoding='utf-8')
    print('audit complete',len(issues),'newest',result['newest_issue'])


if __name__ == '__main__': main()
