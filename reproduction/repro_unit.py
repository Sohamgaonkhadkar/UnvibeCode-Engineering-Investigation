#!/usr/bin/env python3
"""Unit-level repro (no CLI, no tree-sitter needed): tsconfig alias loading in the
installed UnvibeCode 0.3.15 engine. Run with the wheel importable, e.g.
  PYTHONPATH=<site-packages> python3 repro_unit.py
Pass criterion (expected, per TypeScript's JSONC tsconfig format): BOTH fixtures
load {'@app': 'src/app'} and resolve @app/util -> src/app/util.ts."""
import importlib.util, glob, sys
from pathlib import Path

cands = glob.glob(str(Path(sys.prefix) / "**/shipreadyv2/engine_sources/00a_*.py"), recursive=True) \
     or glob.glob("/tmp/unvibe_pkg/shipreadyv2/engine_sources/00a_*.py")
spec = importlib.util.spec_from_file_location("fastlane", cands[0])
m = importlib.util.module_from_spec(spec); sys.modules["fastlane"] = m; spec.loader.exec_module(m)
print("engine file:", cands[0])

here = Path(__file__).parent
for name in ("minimal_strict", "minimal_jsonc"):
    root = (here / name).resolve()
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.ts"))
    resolver = m.LanguageAwareImportResolver(root, files)
    resolved = resolver._resolve_node_ts("src/feature/comp.ts", "@app/util")
    print(f"{name}: tsconfig_aliases={resolver.tsconfig_aliases}  _resolve_node_ts('@app/util')={resolved}")
