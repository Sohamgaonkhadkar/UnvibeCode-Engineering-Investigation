"""Typed Go callback references: actual installed parsers, graphs and ZIPs."""
import argparse
import contextlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
from helpers import load_engine, pipeline, key, selections, sha, coverage
sys.path.insert(0, str(ROOT / 'solution'))
from method_values import corrected

SHA = '5cba5e182946cf18a757718938bc43910e589466'
PRODUCTION = {
    ('autopipeline_cluster_fd.go','osscluster.go',119,'processPipelineRetries','ClusterClient'),
    *{('himport_cluster.go','osscluster.go',n,'ForEachMaster','ClusterClient') for n in (135,151,167)},
    *{('himport_cluster.go','ring.go',n,'ForEachShard','Ring') for n in (182,196,210)},
    ('multidb.go','multidb_core.go',750,'process','multidbCore'),
    ('multidb.go','multidb_pipeline.go',751,'processPipeline','multidbCore'),
    ('multidb.go','multidb_pipeline.go',752,'processTxPipeline','multidbCore'),
    *{('osscluster_router.go','osscluster.go',n,'ForEachMaster','ClusterClient') for n in (178,181,184)},
}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def extraction(engine):
    cases = {
        'parameter_value': 'func Run(s *Store) { callback := s.Save; callback() }',
        'local_value': 'func Run() { s := &Store{}; callback := s.Save; callback() }',
        'callback_argument': 'func Run(s *Store) { register(s.Save) }',
        'direct_control': 'func Run(s *Store) { s.Save() }',
        'package_control': 'func Run() { callback := remote.Save; callback() }',
    }
    rows = []
    for phase in ('stock', 'corrected', 'restored'):
        with corrected(engine) if phase == 'corrected' else contextlib.nullcontext():
            for name, code in cases.items():
                data = engine.TreeSitterAstAdapter().parse('go', 'source.go', Path('source.go'), 'package p\n' + code)
                assert not data['parse_errors']
                found = [u for u in data['usages'] if u.get('symbol') == 'Save']
                if name == 'package_control':
                    assert len(found) == 1 and found[0]['kind'] == 'selector'
                elif name == 'direct_control':
                    assert len(found) == 1 and found[0]['kind'] == 'method_call'
                elif phase == 'corrected':
                    assert len(found) == 1 and found[0]['kind'] == 'method_reference'
                    assert found[0]['receiver_type']['name'] == 'Store'
                else:
                    assert not found
                rows.append({'phase': phase, 'case': name, 'Save_usages': found})
    return rows


def minimal(engine, work):
    fixture = work / 'fixture'
    shutil.copytree(HERE / 'fixtures', fixture, dirs_exist_ok=True)
    source = fixture / 'source.go'
    original = source.read_text()
    rows = []
    for phase in ('stock', 'repeat', 'source-control', 'corrected', 'restored'):
        source.write_text(original.replace('callback := s.Save', 'callback := func() { s.Save() }')
                          if phase == 'source-control' else original, encoding='utf-8')
        runtime = subprocess.run(['go','test','-mod=readonly','-count=1','-v','./...'], cwd=fixture,
                                 text=True, capture_output=True)
        (work / (phase + '-go-test.log')).write_text(runtime.stdout + runtime.stderr, encoding='utf-8')
        assert runtime.returncode == 0, runtime.stdout + runtime.stderr
        with corrected(engine) if phase == 'corrected' else contextlib.nullcontext():
            graph, bundle = pipeline(engine, fixture, work / phase)
        edges = [e for e in graph['symbol_edges'] if e['source'] == 'source.go' and e.get('symbol') == 'Save' and e.get('owner') == 'Store']
        expected = phase in {'source-control', 'corrected'}
        assert len(edges) == int(expected), edges
        files = sorted({c['file'] for c in selections(bundle, 'source.go')})
        assert ('store.go' in files) == expected, files
        assert any(e['source'] == 'source.go' and e['target'] == 'remote/remote.go' and e.get('symbol') == 'Save' for e in graph['symbol_edges'])
        assert not any(e['source'] == 'source.go' and e.get('symbol') == 'Job' for e in graph['symbol_edges'])
        if phase == 'corrected':
            assert edges[0]['type'] == 'imports_symbol' and edges[0]['import_style'] == 'go_method_value'
        rows.append({'phase': phase, 'runtime': 'passed', 'method_relationships': edges, 'selected_files': files,
                     'package_value_preserved': True, 'unrelated_field_method_not_linked': True})
    source.write_text(original, encoding='utf-8')
    assert rows[0]['selected_files'] == rows[1]['selected_files'] == rows[-1]['selected_files']
    return rows


def public(args):
    repo = args.repo.resolve()
    git = lambda *x: subprocess.check_output(['git','-C',str(repo),*x], text=True).strip()
    assert git('rev-parse','HEAD') == SHA and not git('status','--porcelain')
    before = {f: sha(repo / f) for f in git('ls-files').splitlines()}
    result = {'repository': 'https://github.com/redis/go-redis', 'commit': SHA, 'engines': []}
    for pattern in ('00a_*.py','01_*.py'):
        engine, path = load_engine(pattern)
        digest = sha(path)
        graphs, bundles = [], []
        for phase in ('stock','corrected','restored'):
            out = args.work / 'public' / pattern[:3] / phase
            with corrected(engine) if phase == 'corrected' else contextlib.nullcontext():
                if pattern.startswith('00a'):
                    graph, bundle = pipeline(engine, repo, out)
                    bundles.append(bundle)
                else:
                    original = engine.ShipReadyV2DeepGraphBuilder(str(repo)).build()
                    linker = engine.LinkerResolutionModule(graph_documents=[original])
                    linker.resolve_to(out / 'resolved.json')
                    graph = linker.resolved_document
            graphs.append(graph)
        sets = [{key(e) for e in g['symbol_edges']} for g in graphs]
        gained = sets[1] - sets[0]
        prod = {e for e in gained if not e[0].endswith('_test.go')}
        assert prod == PRODUCTION, prod
        assert len(gained) == 79 and len(gained-prod) == 66
        assert sets[0] == sets[2] and not sets[0] - sets[1]
        assert [len(s) for s in sets] == [23448,23527,23448]
        assert sha(path) == digest
        result['engines'].append({'file': path.name, 'sha256': digest, 'relationships': [len(s) for s in sets],
                                  'production_references_restored': 13, 'test_references_restored': 66, 'lost': 0})
        if not bundles:
            continue
        targets = []
        for source,target,symbol,owner in sorted({(s,t,sym,o) for s,t,n,sym,o in PRODUCTION}):
            definitions = [d for d in graphs[1]['global_symbol_index'][symbol] if d['source_file'] == target and d.get('owner') == owner]
            assert len(definitions) == 1
            span = definitions[0]['line_range']
            start,end = span['start_line'],span['end_line']
            lines = (repo / target).read_text(encoding='utf-8').splitlines()
            availability = {scope: [coverage(selections(b,source,scope),target,start,end,lines) for b in bundles] for scope in ('1','2')}
            expected = {'1': [False,True,False], '2': [False,True,False]}
            if symbol == 'process':
                expected = {'1': [False,False,False], '2': [True,True,True]}
            if symbol == 'processTxPipeline':
                expected = {'1': [False,False,False], '2': [False,False,False]}
            assert availability == expected, (source,symbol,availability)
            targets.append(dict(source=source,target=target,symbol=symbol,owner=owner,definition_lines=[start,end],availability=availability))
        result['complete_target_audit'] = targets
        result['source_files'] = len(graphs[0]['nodes'])
    assert before == {f: sha(repo/f) for f in before} and not git('status','--porcelain')
    result['tracked_source_unchanged'] = True
    result['source_hashes'] = {f: before[f] for f in sorted({e[0] for e in PRODUCTION}|{e[1] for e in PRODUCTION})}
    result['production_references'] = [dict(zip(('source','target','line','symbol','owner'),e)) for e in sorted(PRODUCTION)]
    save(args.output.with_name(args.output.stem + '-compiler-cases.json'), result['production_references'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.work = args.work.resolve()
    args.work.mkdir(parents=True, exist_ok=True)
    result = {'product': 'unvibecode==0.3.15', 'engines': []}
    for pattern in ('00a_*.py','01_*.py'):
        engine,path = load_engine(pattern)
        digest = sha(path)
        result['engines'].append({'file': path.name, 'sha256': digest, 'extraction': extraction(engine)})
        if pattern.startswith('00a'):
            result['minimal'] = minimal(engine, args.work / 'minimal')
        assert sha(path) == digest
    if args.repo:
        result['public'] = public(args)
    result['status'] = 'passed'
    save(args.output, result)
    print('PASS: both parser copies, five compiling fixture states, typed method references and field/package controls' + ('; both public graphs and complete target audit' if args.repo else ''))


if __name__ == '__main__':
    main()
