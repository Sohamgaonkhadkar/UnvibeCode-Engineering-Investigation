"""Compile parser controls with Go, and run equivalent named/local runtime tests."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from verify import CASES, HERE

p = argparse.ArgumentParser()
p.add_argument('--go', default='go')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
rows = []
def run(root, label):
    r = subprocess.run([a.go,'test','-v','./...'],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    assert r.returncode == 0, r.stdout
    rows.append({'case':label,'exit':r.returncode,'output':r.stdout})
with tempfile.TemporaryDirectory(prefix='uvc-go-compiler-') as directory:
    root = Path(directory)
    for label,(body,_,_) in CASES.items():
        target = root/label; target.mkdir()
        (target/'go.mod').write_text('module example.test/control\n\ngo 1.20\n')
        (target/'source.go').write_text('package fixture\ntype Store struct{}\ntype Other struct{}\nfunc (*Store) Save() {}\nfunc (*Other) Save() {}\n'+body+'\n')
        run(target,label)
    for label in ('named_runtime','local_runtime'):
        target = root/label
        shutil.copytree(HERE/'fixtures/named',target)
        if label == 'local_runtime':
            path=target/'source.go'
            text=path.read_text().replace('func Open() (r *Store) {','func Open() *Store {\n\tvar r *Store').replace('\treturn\n','\treturn r\n')
            path.write_text(text)
        run(target,label)
version = subprocess.check_output([a.go,'version'],text=True).strip()
a.output.write_text(json.dumps({'go':version,'status':'passed','cases':rows},indent=2)+'\n',encoding='utf-8')
print('Go compiler: 9 syntax controls compiled; named and local runtime tests passed')
