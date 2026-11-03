#!/usr/bin/env python3
"""Apply or restore the reference JSONC patch in an installed package.

This is a **rehearsal tool for a disposable virtual environment**, not an
upstream pull request.  It makes the maintainer-integration claim concrete
at file level:

1. copies ``solution/tsconfig_jsonc.py`` beside the installed engine sources
   as ``_unvibecode_tsconfig_jsonc_reference.py``;
2. replaces ``_load_tsconfig_aliases`` in both shipped engine copies with a
   call to that exact reference loader;
3. appends ``resolver.tsconfig_warning`` to each graph builder's existing
   ``warnings`` list immediately after resolver construction; and
4. writes byte-identical backups plus a hash manifest before changing
   anything, so the stock files can be restored.

Refusing to run without an explicit acknowledgement and backup directory is
deliberate.  Use it only in a throwaway environment, for example::

    python -m venv /tmp/unvibecode-patched
    /tmp/unvibecode-patched/bin/python -m pip install unvibecode==0.3.15
    /tmp/unvibecode-patched/bin/python solution/apply_reference_patch.py \
      --backup-dir /tmp/unvibecode-stock-backup \
      --i-understand-this-modifies-site-packages

Restore with the same interpreter and ``--restore /tmp/unvibecode-stock-backup``.
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

PATCH_MARKER = "UNVIBECODE_JSONC_REFERENCE_PATCH"
REFERENCE_FILENAME = "_unvibecode_tsconfig_jsonc_reference.py"
ENGINE_PATTERNS = ("00a_*.py", "01_*.py")

IMPORT_BLOCK = f'''
# --- BEGIN {PATCH_MARKER} ---
import importlib.util as _uvc_importlib_util
import sys as _uvc_sys

_UVC_TSCONFIG_REFERENCE_NAME = "_unvibecode_tsconfig_jsonc_reference"
if _UVC_TSCONFIG_REFERENCE_NAME in _uvc_sys.modules:
    _UVC_TSCONFIG_JSONC = _uvc_sys.modules[_UVC_TSCONFIG_REFERENCE_NAME]
else:
    _UVC_TSCONFIG_REFERENCE_PATH = Path(__file__).with_name(
        "{REFERENCE_FILENAME}"
    )
    _UVC_TSCONFIG_SPEC = _uvc_importlib_util.spec_from_file_location(
        _UVC_TSCONFIG_REFERENCE_NAME, _UVC_TSCONFIG_REFERENCE_PATH
    )
    if _UVC_TSCONFIG_SPEC is None or _UVC_TSCONFIG_SPEC.loader is None:
        raise ImportError(
            "Cannot load the shared tsconfig JSONC reference module: "
            + str(_UVC_TSCONFIG_REFERENCE_PATH)
        )
    _UVC_TSCONFIG_JSONC = _uvc_importlib_util.module_from_spec(
        _UVC_TSCONFIG_SPEC
    )
    _uvc_sys.modules[_UVC_TSCONFIG_REFERENCE_NAME] = _UVC_TSCONFIG_JSONC
    _UVC_TSCONFIG_SPEC.loader.exec_module(_UVC_TSCONFIG_JSONC)
# --- END {PATCH_MARKER} ---
'''

REPLACEMENT_METHOD = f'''    def _load_tsconfig_aliases(self) -> Dict[str, str]:
        # {PATCH_MARKER}: parse tsconfig as JSONC and preserve degradation.
        result = _UVC_TSCONFIG_JSONC.load_tsconfig_aliases_result(
            self.workspace_root, safe_read_text, to_posix_rel
        )
        self.tsconfig_warning = (
            result.warning.as_dict() if result.warning is not None else None
        )
        return result.aliases
'''

WARNING_LINES = (
    f"        # {PATCH_MARKER}: disclose a degraded tsconfig once.\n"
    "        if getattr(resolver, \"tsconfig_warning\", None) is not None:\n"
    "            self.warnings.append(resolver.tsconfig_warning)\n"
)


class PatchError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def require(condition: bool, message: str, code: int = 1) -> None:
    if not condition:
        raise PatchError(message, code)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def package_engine_root() -> Path:
    spec = importlib.util.find_spec("shipreadyv2")
    require(spec is not None, "shipreadyv2 package is not installed", 2)
    locations = list(spec.submodule_search_locations or [])
    require(bool(locations), "shipreadyv2 package location could not be determined", 2)
    root = Path(locations[0]).resolve() / "engine_sources"
    require(root.is_dir(), f"Installed engine_sources directory not found: {root}", 2)
    return root


def engine_files(engine_root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ENGINE_PATTERNS:
        candidates = sorted(engine_root.glob(pattern))
        require(
            len(candidates) == 1,
            f"Expected exactly one installed engine matching {pattern}, found {len(candidates)}",
            2,
        )
        files.append(candidates[0])
    return files


def find_class(tree: ast.Module, name: str, path: Path) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise PatchError(f"{path.name}: class {name} not found", 2)


def find_method(class_node: ast.ClassDef, name: str, path: Path) -> ast.FunctionDef:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise PatchError(f"{path.name}: method {class_node.name}.{name} not found", 2)


def find_resolver_assignment(class_node: ast.ClassDef, path: Path) -> ast.Assign:
    build = find_method(class_node, "build", path)
    for node in ast.walk(build):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != "resolver":
            continue
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "LanguageAwareImportResolver"
        ):
            return node
    raise PatchError(f"{path.name}: resolver construction in build() not found", 2)


def method_is_stock_vulnerable(method: ast.FunctionDef, source: str) -> bool:
    segment = ast.get_source_segment(source, method) or ""
    has_strict_load = "json.loads(safe_read_text(tsconfig))" in segment
    has_except_pass = False
    for node in ast.walk(method):
        if isinstance(node, ast.ExceptHandler):
            has_except_pass = has_except_pass or (
                len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
            )
    return has_strict_load and has_except_pass


def classify(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    if PATCH_MARKER in source and "_UVC_TSCONFIG_JSONC.load_tsconfig_aliases_result" in source:
        return "patched"
    try:
        tree = ast.parse(source)
        resolver = find_class(tree, "LanguageAwareImportResolver", path)
        method = find_method(resolver, "_load_tsconfig_aliases", path)
    except Exception:
        return "unknown"
    return "stock_vulnerable" if method_is_stock_vulnerable(method, source) else "unknown"


def patched_source(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    require(PATCH_MARKER not in source, f"{path.name} is already patched")
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)

    resolver_class = find_class(tree, "LanguageAwareImportResolver", path)
    method = find_method(resolver_class, "_load_tsconfig_aliases", path)
    require(
        method_is_stock_vulnerable(method, source),
        f"{path.name}: _load_tsconfig_aliases is not the expected stock vulnerable implementation",
        2,
    )
    builder_class = find_class(tree, "ShipReadyV2DeepGraphBuilder", path)
    assignment = find_resolver_assignment(builder_class, path)

    typing_import_end: int | None = None
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            typing_import_end = node.end_lineno
            break
    require(typing_import_end is not None, f"{path.name}: typing import not found", 2)
    require(method.end_lineno is not None, f"{path.name}: method has no end line", 2)
    require(
        assignment.end_lineno is not None,
        f"{path.name}: resolver assignment has no end line",
        2,
    )

    # Apply from bottom to top so original line numbers remain valid.
    insert_at = assignment.end_lineno  # zero-based index of following line
    lines[insert_at:insert_at] = [WARNING_LINES]
    lines[method.lineno - 1 : method.end_lineno] = [REPLACEMENT_METHOD]
    lines[typing_import_end:typing_import_end] = [IMPORT_BLOCK]

    output = "".join(lines)
    try:
        compile(output, str(path), "exec")
    except SyntaxError as exc:
        raise PatchError(f"Patched {path.name} does not compile: {exc}", 2) from exc
    require(classify_text(output) == "patched", f"Patched {path.name} failed classification", 2)
    return output


def classify_text(source: str) -> str:
    if PATCH_MARKER in source and "_UVC_TSCONFIG_JSONC.load_tsconfig_aliases_result" in source:
        return "patched"
    return "unknown"


def write_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.unvibecode-jsonc-tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def apply_patch(backup_dir: Path) -> dict[str, Any]:
    engine_root = package_engine_root()
    files = engine_files(engine_root)
    reference_source = Path(__file__).resolve().with_name("tsconfig_jsonc.py")
    require(reference_source.is_file(), f"Reference module not found: {reference_source}", 2)
    reference_bytes = reference_source.read_bytes()
    reference_dest = engine_root / REFERENCE_FILENAME

    states = {path.name: classify(path) for path in files}
    require(
        all(state == "stock_vulnerable" for state in states.values()),
        f"Refusing to patch unexpected engine states: {states}",
        2,
    )
    if reference_dest.exists():
        require(
            reference_dest.read_bytes() == reference_bytes,
            f"Refusing to overwrite differing reference module: {reference_dest}",
            2,
        )

    # Compute every patched source before writing anything.
    rendered = {path: patched_source(path).encode("utf-8") for path in files}

    backup_dir = backup_dir.resolve()
    if backup_dir.exists():
        require(
            backup_dir.is_dir() and not any(backup_dir.iterdir()),
            f"Backup directory must be new or empty: {backup_dir}",
            2,
        )
    backup_engine_dir = backup_dir / "engine_sources"
    backup_engine_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": "unvibecode-jsonc-reference-patch-backup/v1",
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "engine_root": str(engine_root),
        "reference": {
            "source_name": reference_source.name,
            "installed_name": REFERENCE_FILENAME,
            "sha256": sha256_bytes(reference_bytes),
            "existed_before_patch": reference_dest.exists(),
        },
        "files": {},
    }
    for path in files:
        backup = backup_engine_dir / path.name
        shutil.copy2(path, backup)
        manifest["files"][path.name] = {
            "stock_sha256": sha256_file(path),
            "patched_sha256": sha256_bytes(rendered[path]),
            "backup_relative_path": f"engine_sources/{path.name}",
        }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    write_atomic(reference_dest, reference_bytes)
    for path, data in rendered.items():
        write_atomic(path, data)
        require(classify(path) == "patched", f"Patch verification failed: {path.name}", 2)
    require(
        sha256_file(reference_dest) == manifest["reference"]["sha256"],
        "Installed reference module hash mismatch",
        2,
    )
    return {
        "status": "patched",
        "backup_dir": str(backup_dir),
        "engine_root": str(engine_root),
        "reference_installed": str(reference_dest),
        "files": manifest["files"],
    }


def restore_patch(backup_dir: Path) -> dict[str, Any]:
    backup_dir = backup_dir.resolve()
    manifest_path = backup_dir / "manifest.json"
    require(manifest_path.is_file(), f"Patch backup manifest not found: {manifest_path}", 2)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(
        manifest.get("schema") == "unvibecode-jsonc-reference-patch-backup/v1",
        "Unrecognized patch backup manifest",
        2,
    )
    engine_root = package_engine_root()
    files = engine_files(engine_root)
    for path in files:
        info = manifest.get("files", {}).get(path.name)
        require(bool(info), f"Backup manifest lacks {path.name}", 2)
        require(
            sha256_file(path) == info["patched_sha256"],
            f"Current {path.name} does not match the recorded patched hash; refusing restore",
            2,
        )
        backup = backup_dir / info["backup_relative_path"]
        require(backup.is_file(), f"Backup file missing: {backup}", 2)
        require(
            sha256_file(backup) == info["stock_sha256"],
            f"Backup hash mismatch: {backup}",
            2,
        )

    for path in files:
        info = manifest["files"][path.name]
        write_atomic(path, (backup_dir / info["backup_relative_path"]).read_bytes())
        require(
            sha256_file(path) == info["stock_sha256"],
            f"Restore hash mismatch: {path.name}",
            2,
        )
        require(classify(path) == "stock_vulnerable", f"Restore classification failed: {path.name}", 2)

    reference = manifest.get("reference", {})
    reference_dest = engine_root / REFERENCE_FILENAME
    removed_reference = False
    if not reference.get("existed_before_patch") and reference_dest.is_file():
        require(
            sha256_file(reference_dest) == reference.get("sha256"),
            "Installed reference module changed; refusing to delete it",
            2,
        )
        reference_dest.unlink()
        removed_reference = True
    return {
        "status": "restored",
        "backup_dir": str(backup_dir),
        "engine_root": str(engine_root),
        "removed_reference_module": removed_reference,
        "files": {
            path.name: manifest["files"][path.name]["stock_sha256"] for path in files
        },
    }


def check_patch() -> dict[str, Any]:
    engine_root = package_engine_root()
    files = engine_files(engine_root)
    reference_source = Path(__file__).resolve().with_name("tsconfig_jsonc.py")
    reference_dest = engine_root / REFERENCE_FILENAME
    return {
        "status": "checked",
        "engine_root": str(engine_root),
        "reference_installed": reference_dest.is_file(),
        "reference_matches_solution": (
            reference_dest.is_file()
            and sha256_file(reference_dest) == sha256_file(reference_source)
        ),
        "files": {
            path.name: {"state": classify(path), "sha256": sha256_file(path)}
            for path in files
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report stock/patched state only")
    mode.add_argument("--backup-dir", type=Path, help="apply the patch using this new backup directory")
    mode.add_argument("--restore", type=Path, help="restore stock files from this backup directory")
    parser.add_argument(
        "--i-understand-this-modifies-site-packages",
        action="store_true",
        help="required for --backup-dir and --restore",
    )
    args = parser.parse_args()

    try:
        if args.check:
            result = check_patch()
        else:
            require(
                args.i_understand_this_modifies_site_packages,
                "Refusing to modify site-packages without --i-understand-this-modifies-site-packages",
                2,
            )
            result = (
                apply_patch(args.backup_dir)
                if args.backup_dir is not None
                else restore_patch(args.restore)
            )
    except PatchError as exc:
        print(f"REFERENCE_PATCH_STATUS: failed\nREFERENCE_PATCH_ERROR: {exc}")
        return exc.code
    except Exception as exc:
        print(
            "REFERENCE_PATCH_STATUS: failed\n"
            f"REFERENCE_PATCH_ERROR: {type(exc).__name__}: {exc}"
        )
        return 1

    print(f"REFERENCE_PATCH_STATUS: {result['status']}")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
