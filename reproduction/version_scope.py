#!/usr/bin/env python3
"""Determine which published UnvibeCode wheels contain the vulnerable loader.

This is an optional evidence-generation script (it needs PyPI network access,
so it is not part of the lightweight ``verify.py`` path).  For every selected
wheel it:

1. verifies the downloaded bytes against the SHA-256 published by PyPI;
2. locates both shipped ``engine_sources`` copies;
3. fingerprints the ``_load_tsconfig_aliases`` AST and checks for strict
   ``json.loads`` plus a broad ``except Exception: pass``; and
4. executes each *unique extracted function* (not the whole engine module)
   against semantically identical strict-JSON and JSONC controls.

Example used for the committed snapshot:

    python reproduction/version_scope.py --all-wheels --through 0.3.15 \
      --output evidence/tsconfig-jsonc/version_scope.json
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import json
import tempfile
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

PYPI_JSON = "https://pypi.org/pypi/unvibecode/json"
STRICT_CONFIG = (
    '{"compilerOptions":{"baseUrl":".",'
    '"paths":{"@app/*":["src/app/*"]}}}'
)
JSONC_CONFIG = """{
  // Same aliases, legal TypeScript JSONC syntax.
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@app/*": ["src/app/*"],
    },
  },
}
"""
EXPECTED_ALIASES = {"@app": "src/app"}


class ScopeError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in version.split("."):
        digits = "".join(character for character in part if character.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "unvibecode-version-scope/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ScopeError(f"Could not fetch PyPI metadata: {exc}", 2) from exc


def fetch_wheel(file_info: dict[str, Any], cache_dir: Path) -> bytes:
    filename = file_info["filename"]
    expected = file_info["digests"]["sha256"]
    cached = cache_dir / filename
    if cached.is_file():
        data = cached.read_bytes()
        if sha256_bytes(data) == expected:
            return data
    request = urllib.request.Request(
        file_info["url"], headers={"User-Agent": "unvibecode-version-scope/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    except Exception as exc:
        raise ScopeError(f"Could not download {filename}: {exc}", 2) from exc
    actual = sha256_bytes(data)
    if actual != expected:
        raise ScopeError(
            f"SHA-256 mismatch for {filename}: PyPI={expected}, downloaded={actual}",
            2,
        )
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    return data


def find_loader(source: str, filename: str) -> ast.FunctionDef:
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_load_tsconfig_aliases":
            return node
    raise ScopeError(f"_load_tsconfig_aliases not found in {filename}")


def function_fingerprint(node: ast.FunctionDef) -> str:
    return sha256_bytes(ast.dump(node, include_attributes=False).encode("utf-8"))


def structural_flags(node: ast.FunctionDef) -> dict[str, bool]:
    strict_json_loads = False
    broad_exception_pass = False
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if (
                child.func.attr == "loads"
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "json"
            ):
                strict_json_loads = True
        if isinstance(child, ast.Try):
            for handler in child.handlers:
                is_exception = isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
                if is_exception and len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                    broad_exception_pass = True
    return {
        "uses_strict_json_loads": strict_json_loads,
        "has_broad_exception_pass": broad_exception_pass,
    }


def safe_read_text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def to_posix_rel(path: str | Path) -> str:
    return Path(path).as_posix()


def behaviour_for_function(node: ast.FunctionDef, source: str) -> dict[str, Any]:
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, Any] = {
        "Dict": Dict,
        "Path": Path,
        "json": json,
        "safe_read_text": safe_read_text,
        "to_posix_rel": to_posix_rel,
    }
    exec(compile(module, "<extracted _load_tsconfig_aliases>", "exec"), namespace)
    loader = namespace["_load_tsconfig_aliases"]

    outcomes: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        config = root / "tsconfig.json"
        fake_self = SimpleNamespace(workspace_root=root)
        for label, text in (("strict_json", STRICT_CONFIG), ("jsonc", JSONC_CONFIG)):
            config.write_text(text, encoding="utf-8")
            try:
                outcomes[label] = {"aliases": loader(fake_self), "error": None}
            except Exception as exc:  # record rather than hide future changes
                outcomes[label] = {
                    "aliases": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
    outcomes["affected"] = (
        outcomes["strict_json"]["aliases"] == EXPECTED_ALIASES
        and outcomes["jsonc"]["aliases"] == {}
    )
    outcomes["function_source_sha256"] = sha256_bytes(
        (ast.get_source_segment(source, node) or "").encode("utf-8")
    )
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through", help="Only scan releases <= this version")
    parser.add_argument("--all-wheels", action="store_true", help="Scan every wheel, not one per release")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "schema": "unvibecode-tsconfig-jsonc-version-scope/v1",
        "status": "running",
        "generated_on": _dt.date.today().isoformat(),
        "source": PYPI_JSON,
        "through_version": args.through,
        "wheel_selection": "all published wheels" if args.all_wheels else "first filename per release",
    }
    code = 0

    try:
        metadata = fetch_json(PYPI_JSON)
        releases = metadata.get("releases", {})
        versions = sorted(releases, key=version_key)
        if args.through:
            maximum = version_key(args.through)
            versions = [version for version in versions if version_key(version) <= maximum]
        if not versions:
            raise ScopeError("No PyPI releases selected", 2)

        cache_dir = args.cache_dir or Path(tempfile.gettempdir()) / "unvibecode-version-scope"
        wheels: list[dict[str, Any]] = []
        behaviours: dict[str, dict[str, Any]] = {}
        version_summaries: dict[str, dict[str, Any]] = {}

        for version in versions:
            files = [
                item
                for item in releases[version]
                if item.get("packagetype") == "bdist_wheel"
            ]
            files.sort(key=lambda item: item["filename"])
            if not args.all_wheels:
                files = files[:1]
            if not files:
                raise ScopeError(f"No wheel found for UnvibeCode {version}", 2)

            version_fingerprints: set[str] = set()
            version_affected = True
            for file_info in files:
                data = fetch_wheel(file_info, cache_dir)
                with zipfile.ZipFile(BytesIO(data)) as archive:
                    engine_names = sorted(
                        name
                        for name in archive.namelist()
                        if "/engine_sources/" in name
                        and ("/00a_" in name or "/01_" in name)
                        and name.endswith(".py")
                    )
                    if len(engine_names) != 2:
                        raise ScopeError(
                            f"Expected two engine copies in {file_info['filename']}, "
                            f"found {engine_names}"
                        )
                    engine_records: list[dict[str, Any]] = []
                    for name in engine_names:
                        source_bytes = archive.read(name)
                        source = source_bytes.decode("utf-8")
                        function = find_loader(source, name)
                        fingerprint = function_fingerprint(function)
                        version_fingerprints.add(fingerprint)
                        if fingerprint not in behaviours:
                            behaviours[fingerprint] = behaviour_for_function(function, source)
                        affected = bool(behaviours[fingerprint]["affected"])
                        version_affected = version_affected and affected
                        engine_records.append(
                            {
                                "path": name,
                                "sha256": sha256_bytes(source_bytes),
                                "loader_ast_sha256": fingerprint,
                                **structural_flags(function),
                                "extracted_loader_affected": affected,
                            }
                        )
                wheels.append(
                    {
                        "version": version,
                        "filename": file_info["filename"],
                        "url": file_info["url"],
                        "size": file_info["size"],
                        "sha256": file_info["digests"]["sha256"],
                        "upload_time_iso_8601": file_info.get("upload_time_iso_8601"),
                        "engine_copies": engine_records,
                    }
                )
            version_summaries[version] = {
                "wheels_scanned": len(files),
                "engine_copies_scanned": len(files) * 2,
                "unique_loader_ast_sha256": sorted(version_fingerprints),
                "affected": version_affected,
            }

        result.update(
            {
                "status": "completed",
                "versions_scanned": versions,
                "version_summaries": version_summaries,
                "wheels": wheels,
                "unique_loader_behaviours": behaviours,
                "summary": {
                    "releases_scanned": len(versions),
                    "wheels_scanned": len(wheels),
                    "engine_copies_scanned": len(wheels) * 2,
                    "unique_loader_ast_fingerprints": len(behaviours),
                    "affected_releases": [
                        version
                        for version, summary in version_summaries.items()
                        if summary["affected"]
                    ],
                    "all_scanned_releases_affected": all(
                        summary["affected"] for summary in version_summaries.values()
                    ),
                },
                "limitations": [
                    "Scope is the wheels published on PyPI at scan time; sdists and non-PyPI builds are not counted as separate artifacts.",
                    "Behaviour is executed once per unique extracted loader AST; byte-identical AST fingerprints are not re-executed for every platform wheel.",
                ],
            }
        )
    except ScopeError as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        code = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        code = 1

    if args.output:
        output = args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"VERSION_SCOPE_STATUS: {result['status']}")
        summary = result.get("summary", {})
        if summary:
            print(
                "VERSION_SCOPE: "
                f"releases={summary['releases_scanned']} "
                f"wheels={summary['wheels_scanned']} "
                f"engine_copies={summary['engine_copies_scanned']} "
                f"unique_loaders={summary['unique_loader_ast_fingerprints']} "
                f"all_affected={summary['all_scanned_releases_affected']}"
            )
        if result.get("error"):
            print(f"VERSION_SCOPE_ERROR: {result['error']}")
        print(f"OUTPUT: {output}")
    else:
        print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
