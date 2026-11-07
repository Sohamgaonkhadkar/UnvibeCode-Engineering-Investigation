"""Five inexpensive candidate screens; observations are not eligibility claims."""
import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

from verify import load_engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine, path = load_engine("00a_*.py")
    adapter = engine.TreeSitterAstAdapter()
    named = adapter.parse("go", "x.go", Path("x.go"), "package p\nfunc Open() (r *Store) { r.Save(); return }")
    param = adapter.parse("go", "x.go", Path("x.go"), "package p\nfunc Open(r *Store) { r.Save() }")
    assert named['usages'][0]['kind'] == 'selector'
    assert param['usages'][0]['kind'] == 'method_call'
    # New syntax versus the corresponding ordinary try statement.
    classic = engine.PythonSemanticExtractor().extract('try:\n import dependency\nexcept Exception:\n pass\n')
    starred = engine.PythonSemanticExtractor().extract('try:\n import dependency\nexcept* Exception:\n pass\n')
    assert classic['import_uncertainty_by_line'][2] == ['try_import_fallback']
    assert starred['import_uncertainty_by_line'][2] == []
    css = engine.CssAstAdapter()
    flat = css.parse('x.css', Path('x.css'), '.logo { background: url(logo.svg) }')
    nested = css.parse('x.css', Path('x.css'), '@media screen { .logo { background: url(logo.svg) } }')
    assert len(flat['imports']) == 1 and not nested['imports']
    # Source text in an external JS store should round-trip without HTML parsing.
    literal = 'TEXT = "</script> & \\" quoted \\""\n# Unicode: café\n'
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'x.py').write_text(literal, encoding='utf-8')
        graph = engine.ShipReadyV2DeepGraphBuilder(str(root)).build()
        engine.FastLaneContextDownloadBuilder(root, graph).build(root/'store.js')
        raw = (root/'store.js').read_text(encoding='utf-8')
        store = json.loads(raw.removeprefix('window.SHIPREADY_CONTEXT_STORE=').rstrip(';\n'))
        code = next(iter(store['chunks'].values()))['numbered_code']
        assert '</script>' in code and 'café' in code
    # Controlled risk-proof input; no hosted occurrence is assumed.
    selector_path = path.parent / '05_shipreadyv2_critical_business_insight_selector_v4.py'
    spec = importlib.util.spec_from_file_location('screen_selector', selector_path)
    sel = importlib.util.module_from_spec(spec); sys.modules[spec.name] = sel; spec.loader.exec_module(sel)
    header = {'chunk_id':'c', 'file':'x.py', 'start_line':1, 'end_line':2, 'language':'python'}
    source = sel.SourceIndex([{'record_type':'pass1_semantic_request', 'input_payload':
        '<<<CHUNK '+json.dumps(header)+'>>>\n     1 | def value():\n     2 |     return 1\n'}])
    ev = {'evidence_id':'e','validation_status':'VALID','canonical_evidence_level':'E1_DIRECT_CODE',
          'chunk_id':'c','start_line':1,'end_line':2,'evidence_summary':'if input == threshold'}
    facts = sel.PathFacts({}, {'e':ev}, source)
    summary_match = facts.has_source_pattern(['e'], sel.BOUNDARY_PATTERN)[0]
    ev['evidence_summary'] = ''
    source_match = facts.has_source_pattern(['e'], sel.BOUNDARY_PATTERN)[0]
    assert summary_match and not source_match
    rows = [
        {'candidate':'Go named results', 'observation':'selector versus typed method_call', 'decision':'selected after separate real-product validation'},
        {'candidate':'Python except* import uncertainty', 'observation':{'classic':classic['import_uncertainty_by_line'],'starred':starred['import_uncertainty_by_line']}, 'decision':'deferred: metadata-only impact established; adjacent #522 needs further comparison'},
        {'candidate':'CSS nested media assets', 'observation':{'flat_imports':flat['imports'],'nested_imports':nested['imports']}, 'decision':'rejected for submission: asset graph scope already overlaps #386; extraction difference alone insufficient'},
        {'candidate':'Context serialization of HTML-like source', 'observation':'external store round-trips closing-script text and Unicode', 'decision':'hypothesis falsified'},
        {'candidate':'Risk proof summary/source separation', 'observation':{'summary_match':summary_match,'source_match':source_match}, 'decision':'deferred: controlled helper result; no natural candidate or final risk artifact established'},
    ]
    args.output.write_text(json.dumps(rows, indent=2)+'\n',encoding='utf-8')
    print('5 candidate screens completed; one selected; observations written to',args.output)


if __name__ == '__main__':
    main()
