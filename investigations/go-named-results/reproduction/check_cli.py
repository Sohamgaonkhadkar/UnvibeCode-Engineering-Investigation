"""Check an actual CLI bundle against the stock local pipeline output."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from verify import records, selections

p = argparse.ArgumentParser()
p.add_argument('--bundle', type=Path, required=True)
p.add_argument('--pipeline-bundle', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
datasets = []
for path in (a.bundle, a.pipeline_bundle):
    with zipfile.ZipFile(path) as z:
        datasets.append({n: records(z, n) for n in ('chunks.jsonl','connections.jsonl','selections.jsonl')})
assert datasets[0] == datasets[1], 'CLI and stock pipeline payloads differ'
bundle = datasets[0]
assert any(c['file'] == 'leveldb/options.go' for c in bundle['chunks.jsonl'])
for scope in ('1','2'):
    assert not any(c['file'] == 'leveldb/options.go' for c in selections(bundle,'leveldb/session.go',scope))
result = {'status':'passed', 'cli_bundle_sha256':hashlib.sha256(a.bundle.read_bytes()).hexdigest(),
    'record_counts':{n:len(v) for n,v in bundle.items()},
    'cli_equals_stock_pipeline':True, 'options_present_in_complete_zip':True,
    'options_absent_from_session_optimal_and_wider':True,
    'semantic_sha256':hashlib.sha256(json.dumps(bundle,sort_keys=True,ensure_ascii=True).encode()).hexdigest()}
a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
