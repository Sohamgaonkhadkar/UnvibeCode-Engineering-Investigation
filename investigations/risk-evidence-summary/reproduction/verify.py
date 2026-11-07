"""Exercise the installed selector's file-based main; no hosted calls.

Normalized nominations are controlled test inputs, NOT captured model output.
The real-repository source is unchanged and verified at a pinned commit.
"""
import argparse
import contextlib
import copy
import hashlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import types

import shipreadyv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'solution'))
from source_patterns import source_only_patterns

ENGINE = Path(shipreadyv2.__file__).parent / 'engine_sources'
NEGATIVE = 'Writes the local database; no requests.get or external API call occurs.'
LOCAL = '''def save(conn, key, value):
    conn.execute("INSERT INTO entries VALUES (?, ?)", (key, value))
    conn.commit()
'''
POSITIVE = '''def save(client, conn, key, value):
    client.post("/events", json={"key": key})
    conn.execute("INSERT INTO entries VALUES (?, ?)", (key, value))
    conn.commit()
'''


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load(prefix):
    path = next(ENGINE.glob(prefix + '*.py'))
    spec = importlib.util.spec_from_file_location('uvc_' + prefix, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, path


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def run(selector, compiler, folder, code, file, start, symbol, summary):
    folder.mkdir(parents=True, exist_ok=True)
    end = start + len(code.splitlines()) - 1
    header = dict(chunk_id='c', file=file, start_line=start, end_line=end,
                  language='go' if file.endswith('.go') else 'python', qualified_name=symbol)
    payload = '<<<CHUNK ' + json.dumps(header) + '>>>\n' + '\n'.join(
        f'{n:6} | {line}' for n, line in enumerate(code.splitlines(), start)) + '\n'
    prepared = dict(record_type='pass1_semantic_request', request_id='r', input_payload=payload)
    # Independently show the compiler's actual citation validator accepts the
    # narrative without establishing the operation described by that narrative.
    raw = dict(chunk_id='c', file_path=file, start_line=start, end_line=end,
               symbol_or_node_id=symbol, evidence_level='E1_DIRECT_CODE', evidence_summary=summary)
    index = types.SimpleNamespace(chunks={'c': dict(file_path=file, start_line=start, end_line=end)})
    evidence = compiler.validate_evidence(raw, index, 'r', 'pack', compiler.AuditLog([]))
    assert evidence['validation_status'] == 'VALID'
    assert evidence['evidence_summary'] == (summary or 'Validated code citation')
    write(folder / 'compiler-validated-evidence.json', evidence)
    # Hold every normalized field (including evidence ID) constant except summary.
    evidence['evidence_id'] = 'e'
    evidence['evidence_summary'] = summary
    path = dict(normalized_path_id='put', component_id='local-store',
                path_summary={'statement': 'Persist a key-value pair'},
                reachability={'canonical_value': 'PUBLIC_LIBRARY_API'},
                canonical_confidence={'score': 90},
                entrypoints=[{'reachability': {'canonical_value': 'PUBLIC_LIBRARY_API'}, 'evidence_refs': ['e']}],
                effects=[{'effect_id': 'write', 'materiality': 3, 'evidence_refs': ['e'],
                          'repo_native_effect': 'persists the key and value in the local database',
                          'effect_classification': {'canonical_value': 'PERSISTENT_DATA_MUTATION',
                                                    'canonicalization_status': 'VERIFIED',
                                                    'canonical_confidence': {'score': 90}}}],
                canonical_activation_signals=[{'signal_id': 'EXTERNAL_DEPENDENCY', 'value': 'TRUE', 'evidence_refs': ['e']}],
                evidence=[evidence])
    normalized = dict(repository={'repository_id': 'local-store', 'repo_name': 'local-store'},
                      scan={'expected_request_ids': ['r']}, paths=[path])
    coverage = dict(repository_id='local-store', scan={'completeness': 'COMPLETE'},
                    repository_wide_conclusions_allowed=True, coverage={'normalized_path_count': 1})
    inputs = {'NORMALIZED_PATHS_JSON': ('normalized_business_paths.json', normalized),
              'BUSINESS_PATH_COVERAGE_JSON': ('business_path_coverage.json', coverage),
              'RESOLVED_GRAPH_JSON': ('shipreadyv2_resolved_graph.json', {'repo_name': 'local-store'})}
    selector.REPORT_FOLDER = folder
    for attr, (name, value) in inputs.items():
        setattr(selector, attr, folder / name)
        write(folder / name, value)
    selector.PASS1_INPUTS_JSONL = folder / 'shipreadyv2_pass1_llm_inputs.jsonl'
    selector.PASS1_INPUTS_JSONL.write_text(json.dumps(prepared) + '\n', encoding='utf-8')
    selector.BUSINESS_PATH_AUDIT_JSONL = folder / 'business_path_compiler_audit.jsonl'
    selector.UNIVERSAL_RULES_YAML = folder / 'absent-optional-rules.yaml'
    outputs = {'ALL_CANDIDATES_JSON': 'all_insight_candidates_v4.json',
               'SELECTED_INSIGHTS_JSON': 'selected_business_insights_v4.json',
               'REJECTED_CANDIDATES_JSON': 'rejected_insight_candidates_v4.json',
               'INVESTIGATION_GAPS_JSON': 'investigation_gap_candidates_v4.json',
               'SELECTION_SUMMARY_JSON': 'insight_selection_summary_v4.json',
               'SELECTOR_AUDIT_JSONL': 'insight_selector_audit_v4.jsonl',
               'SELECTOR_ERRORS_JSONL': 'insight_selector_errors_v4.jsonl'}
    for attr, name in outputs.items():
        setattr(selector, attr, folder / name)
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        selector.main()
    (folder / 'selector.log').write_text(log.getvalue(), encoding='utf-8')
    candidates = json.loads(selector.ALL_CANDIDATES_JSON.read_text())['candidates']
    candidate = next(c for c in candidates if c['family'] == 'EXTERNAL_DEPENDENCY_AND_RECOVERY')
    selected = json.loads(selector.SELECTED_INSIGHTS_JSON.read_text())['selected_insights']
    proof = next(p for p in candidate['proof_obligations'] if p['obligation_id'] == 'EXTERNAL_DEPENDENCY_CALL')
    assert bool(selected) == (candidate['decision'] == 'SELECTED')
    return dict(decision=candidate['decision'], qualification=candidate['qualification_status'],
                score=candidate['score']['total'], selected_count=len(selected), proof=proof,
                reporting_ceiling=candidate['reporting_ceiling']['maximum_allowed_claim'],
                source_sha256=digest(code.encode()), prepared_sha256=digest(selector.PASS1_INPUTS_JSONL.read_bytes()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    selector, source = load('05_')
    compiler, compiler_source = load('04_')
    assert importlib.metadata.version('unvibecode') == '0.3.15'
    commit = subprocess.check_output(['git', '-C', str(args.repo), 'rev-parse', 'HEAD'], text=True).strip()
    assert commit == '126854af5e6d8295ef8e8bee3040dd8380ae72e8'
    assert not subprocess.check_output(['git', '-C', str(args.repo), 'status', '--porcelain'], text=True).strip()
    real_file = args.repo / 'leveldb/db_write.go'
    code = '\n'.join(real_file.read_text().splitlines()[373:376]) + '\n'
    assert code.startswith('func (db *DB) Put(') and 'db.putRec(' in code
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE entries (key TEXT, value TEXT)')
    namespace = {}
    exec(LOCAL, namespace)
    namespace['save'](conn, 'k', 'v')
    assert conn.execute('SELECT * FROM entries').fetchall() == [('k', 'v')]
    conn.close()
    result = {'unvibecode': '0.3.15', 'selector_sha256': digest(source.read_bytes()),
              'compiler_sha256': digest(compiler_source.read_bytes()), 'public_commit': commit,
              'public_file_sha256': digest(real_file.read_bytes()), 'fixture_sqlite_rows': 1,
              'boundary': 'Controlled normalized nominations; actual installed selector main; no hosted model/report run.',
              'cases': {}}
    for label, body, file, start, symbol in [('minimal', LOCAL, 'store.py', 1, 'store.save'),
                                           ('leveldb', code, 'leveldb/db_write.go', 374, 'DB.Put'),
                                           ('positive', POSITIVE, 'store.py', 1, 'store.save')]:
        summaries = [('blank', ''), ('benign', 'Persists a key-value pair locally.'), ('negative', NEGATIVE)]
        rows = {}
        for phase in ['stock', 'corrected', 'restored']:
            intervention = source_only_patterns(selector) if phase == 'corrected' else contextlib.nullcontext()
            with intervention:
                for name, summary in summaries:
                    key = phase + '-' + name
                    row = run(selector, compiler, args.work / label / key, body, file, start, symbol, summary)
                    expected = label == 'positive' or (phase != 'corrected' and name == 'negative')
                    assert row['selected_count'] == int(expected), (label, key, row)
                    assert row['score'] == (17 if expected else 13)
                    assert row['reporting_ceiling'] == ('EVIDENCE_BACKED_RISK' if expected else 'INVESTIGATION_HYPOTHESIS')
                    rows[key] = row
        assert len({r['prepared_sha256'] for r in rows.values()}) == 1
        assert rows['stock-negative'] == rows['restored-negative']
        normalized_inputs = []
        for key in rows:
            value = json.loads((args.work / label / key / 'normalized_business_paths.json').read_text())
            value['paths'][0]['evidence'][0].pop('evidence_summary')
            normalized_inputs.append(value)
        assert all(value == normalized_inputs[0] for value in normalized_inputs)
        result['cases'][label] = rows
    assert digest(source.read_bytes()) == result['selector_sha256']
    assert digest(compiler_source.read_bytes()) == result['compiler_sha256']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, result)
    print('PASS: 27 file-based selector runs; source inputs invariant; negative summary selects only stock/restored; real external-call control retained.')


if __name__ == '__main__':
    main()
