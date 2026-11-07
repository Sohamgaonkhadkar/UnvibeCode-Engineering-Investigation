"""Independent public-source replication, both graph copies, exhaustive target audit.

All six source-specific production callee identities restored by the correction
are audited, including the two already present in stock context as controls.
"""
import argparse
import contextlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from verify import load_engine, corrected, pipeline, key, selections, sha, records

COMMIT = 'ead4e04ba7c6a49654649131e587133b1d9f3eca'
EXPECTED = {
    ('chainable_api.go','gorm.go',126,'AddError','DB'),
    ('chainable_api.go','gorm.go',170,'AddError','DB'),
    ('finisher_api.go','chainable_api.go',97,'Clauses','DB'),
    ('finisher_api.go','chainable_api.go',406,'Model','DB'),
    ('finisher_api.go','gorm.go',70,'AddError','DB'),
    ('finisher_api.go','gorm.go',70,'Session','DB'),
    ('finisher_api.go','gorm.go',72,'AddError','DB'),
    ('finisher_api.go','gorm.go',99,'Set','DB'),
    ('finisher_api.go','gorm.go',117,'Session','DB'),
    ('finisher_api.go','gorm.go',120,'Session','DB'),
    ('finisher_api.go','gorm.go',548,'AddError','DB'),
    ('finisher_api.go','gorm.go',556,'AddError','DB'),
    ('tests/tests_test.go','finisher_api.go',103,'Exec','DB'),
}
QUESTIONS = {
    'AddError':'Does the called error handler translate, accumulate, and propagate errors to the result?',
    'Clauses':'How does Save apply an OnConflict clause versus a statement modifier or ordinary condition?',
    'Model':'How does FirstOrCreate choose the model for its update path?',
    'Set':'Where does Save store the gorm:update_track_time marker?',
    'Session':'How does the called Session method copy or initialize statement context?',
}


def coverage(chunks, target, start, end, source):
    actual = {}
    for chunk in chunks:
        if chunk['file'] != target: continue
        for line in chunk['numbered_code'].splitlines():
            m = re.match(r'^\s*(\d+)\s\|\s?(.*)$', line)
            if m: actual[int(m[1])] = m[2]
    required = {n:source[n-1] for n in range(start,end+1) if source[n-1].strip()}
    return all(actual.get(n) == text for n,text in required.items())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--work',type=Path)
    p.add_argument('--cli-bundle',type=Path)
    args = p.parse_args()
    repo = args.repo.resolve()
    git = lambda *x:subprocess.check_output(['git','-C',str(repo),*x],text=True).strip()
    assert git('rev-parse','HEAD') == COMMIT
    assert not git('status','--porcelain')
    before = {f:sha(repo/f) for f in git('ls-files').splitlines()}
    result = {'repository':'https://github.com/go-gorm/gorm','commit':COMMIT,'engines':[]}
    temp = tempfile.TemporaryDirectory(prefix='uvc-gorm-') if args.work is None else contextlib.nullcontext(str(args.work))
    with temp as directory:
        root = Path(directory); root.mkdir(parents=True,exist_ok=True)
        for pattern in ('00a_*.py','01_*.py'):
            engine,path = load_engine(pattern)
            digest = sha(path)
            graphs=[]; bundles=[]
            for state in ('stock','corrected','restored'):
                out = root/pattern[:3]/state
                with corrected(engine) if state=='corrected' else contextlib.nullcontext():
                    if pattern.startswith('00a'):
                        graph,bundle = pipeline(engine,repo,out)
                        bundles.append(bundle)
                    else:
                        original = engine.ShipReadyV2DeepGraphBuilder(str(repo)).build()
                        linker = engine.LinkerResolutionModule(graph_documents=[original])
                        linker.resolve_to(out/'resolved.json')
                        graph = linker.resolved_document
                graphs.append(graph)
            sets = [{key(e) for e in g['symbol_edges']} for g in graphs]
            assert sets[0] == sets[2]
            assert sets[1]-sets[0] == EXPECTED,sets[1]-sets[0]
            assert not sets[0]-sets[1]
            assert [len(s) for s in sets] == [3948,3961,3948]
            assert sha(path)==digest
            result['engines'].append({'file':path.name,'sha256':digest,'graph_edges':[len(s) for s in sets],
                'gained_calls':len(EXPECTED),'production_calls':12,'test_calls':1,'lost_calls':0})
            if not bundles: continue
            tasks=[]
            identities = sorted({(e[0],e[1],e[3],e[4]) for e in EXPECTED if not e[0].endswith('_test.go')})
            assert len(identities)==6
            for source,target,symbol,owner in identities:
                definitions = [d for d in graphs[1]['global_symbol_index'][symbol]
                    if d['source_file']==target and d.get('owner')==owner]
                assert len(definitions)==1,definitions
                span=definitions[0]['line_range'];start=span['start_line'];end=span['end_line']
                code=(repo/target).read_text(encoding='utf-8').splitlines()
                row={'source':source,'target':target,'symbol':symbol,'owner':owner,'question':QUESTIONS[symbol],
                     'definition_lines':[start,end],'availability':{}}
                expected = [True,True,True] if source=='finisher_api.go' and symbol in {'AddError','Session'} else [False,True,False]
                for scope in ('1','2'):
                    values=[coverage(selections(b,source,scope),target,start,end,code) for b in bundles]
                    assert values==expected,(source,symbol,scope,values)
                    row['availability'][scope]=values
                tasks.append(row)
            result['target_implementation_audit']={'eligible_source_specific_targets':6,'restored_targets':4,
                'already_present_controls':2,'scopes':['Optimal','Wider'],'tasks':tasks,
                'measurement':'all nonblank source lines of each complete callee definition must match selected target code'}
            result['source_files']=len(graphs[0]['nodes'])
            if args.cli_bundle:
                with zipfile.ZipFile(args.cli_bundle) as z:
                    cli={name:records(z,name) for name in ('chunks.jsonl','connections.jsonl','selections.jsonl')}
                assert cli==bundles[0], 'ordinary CLI payload differs'
                result['cli']={'equals_stock_pipeline':True,'record_counts':{n:len(v) for n,v in cli.items()},
                               'bundle_sha256':sha(args.cli_bundle)}
    result['gained_calls']=[{'source':s,'target':t,'line':n,'symbol':sym,'owner':o} for s,t,n,sym,o in sorted(EXPECTED)]
    result['distinct_production_file_pairs']=len({(s,t) for s,t,*_ in EXPECTED if not s.endswith('_test.go')})
    assert before=={f:sha(repo/f) for f in before}
    assert not git('status','--porcelain')
    result['tracked_source_unchanged']=True
    result['source_hashes']={f:before[f] for f in ('gorm.go','chainable_api.go','finisher_api.go','tests/tests_test.go')}
    result['status']='passed'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    cases=[c for c in result['gained_calls'] if not c['source'].endswith('_test.go')]
    args.output.with_name(args.output.stem+'-compiler-cases.json').write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8')
    print('::notice::GORM: both graphs 3948 -> 3961 -> 3948; 12 production calls, 1 test call; 4/6 complete implementation targets restored, 2 controls retained')


if __name__=='__main__':main()
