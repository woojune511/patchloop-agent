"""Prepare public wheels from literal setup.py metadata without executing project code.

This opt-in operator adapter reuses the existing resolver, installer and descriptor.
It intentionally supports only root runtime requirements, not arbitrary setup programs.
"""
from __future__ import annotations

import argparse
import ast
import re
import tomllib
from pathlib import Path
from unittest.mock import patch

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from patchloop import prepared_probe_dependencies as prepared
from patchloop import probe_dependency_resolution as resolution
from patchloop.errors import ContractError
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes


def metadata(repo: Path, *, groups: list[str], extras: list[str]) -> dict:
    if groups or extras:
        raise ContractError("literal setup adapter supports runtime requirements only")
    pyproject = prepared._read_bytes(repo / "pyproject.toml")
    if "project" in tomllib.loads(pyproject.decode("utf-8")):
        raise ContractError("use ordinary preparation for PEP 621 metadata")
    path = repo / "setup.py"
    if path.is_symlink() or not path.resolve().is_relative_to(repo.resolve()):
        raise ContractError("public setup metadata leaves the prepared source")
    raw = prepared._read_bytes(path)
    tree = ast.parse(raw)
    imported = any(isinstance(n, ast.ImportFrom) and n.module == "setuptools"
                   and any(a.name == "setup" and a.asname is None for a in n.names)
                   for n in tree.body)
    calls = [n.value for n in tree.body if isinstance(n, ast.Expr)
             and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
             and n.value.func.id == "setup"]
    if not imported or len(calls) != 1 or calls[0].args:
        raise ContractError("requires one direct imported setuptools.setup call")
    call = calls[0]
    keywords = {n.arg: n.value for n in call.keywords}
    if None in keywords or len(keywords) != len(call.keywords):
        raise ContractError("setup keyword expansion or duplication is unsupported")

    def literal(key, default=None):
        node = keywords.get(key)
        if node is None:
            return default
        if isinstance(node, ast.Name):
            names = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == node.id]
            assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                           and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                           and n.targets[0].id == node.id and n.lineno < call.lineno]
            if len(names) != 2 or len(assignments) != 1:
                raise ContractError("setup metadata reference is mutated, reused or ambiguous")
            node = assignments[0].value
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError) as exc:
            raise ContractError("setup metadata must be a literal or single literal assignment") \
                from exc

    name = literal("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", name):
        raise ContractError("invalid static setup name")
    python = literal("python_requires", "")
    if not isinstance(python, str) or not SpecifierSet(python).contains("3.12.0"):
        raise ContractError("setup project does not support the probe Python target")
    requirements = literal("install_requires", [])
    if not isinstance(requirements, (list, tuple)) or len(requirements) > 1024:
        raise ContractError("setup runtime requirements must be a bounded literal sequence")
    selected = set()
    for text in requirements:
        if not isinstance(text, str) or any(c in text for c in "\r\n\x00"):
            raise ContractError("setup requirements must be single-line PEP 508 declarations")
        req = Requirement(text)
        if req.url or canonicalize_name(req.name) == canonicalize_name(name):
            raise ContractError("only public index dependencies are supported; no URL/self deps")
        if req.marker and not req.marker.evaluate(resolution.MARKERS):
            continue
        req.marker = None
        selected.add(str(req))
    return {"path": "setup.py", "hash": sha256_bytes(raw), "project_name": name,
            "requires_python": python, "requirements": sorted(selected), "groups": [],
            "extras": [], "adapter": "literal-setup-runtime-v1",
            "pyproject_hash": sha256_bytes(pyproject)}


def workspace_metadata(repo, packages, roots, commit, target):
    public = metadata(repo, groups=[], extras=[])
    name, version = public["project_name"], f"0+patchloop.{commit}"
    if packages != [{"name": name, "source": {"editable": "."}}]:
        raise ContractError("setup workspace identity differs from public resolution")
    record = {"name": name, "version": version,
              "version_basis": "source_snapshot_not_release_version", "project_path": ".",
              "pyproject_hash": public["pyproject_hash"], "setup_hash": public["hash"]}
    directory = target / f"{re.sub(r'[-_.]+', '_', name)}-{version}.dist-info"
    directory.mkdir(exist_ok=False)
    (directory / "METADATA").write_text(
        f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n", encoding="utf-8")
    (directory / "PATCHLOOP-SOURCE.json").write_text(canonical_json(record), encoding="utf-8")
    return [record]


def prepare(*, public, prepared_source: Path, output: Path, source_roots: list[str]):
    with patch.object(resolution, "project_requirements", metadata), \
            patch.object(prepared, "_workspace_metadata", workspace_metadata):
        return prepared.prepare_dependencies(public=public, prepared_source=prepared_source,
            output=output, source_roots=source_roots, resolve=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path)
    parser.add_argument("--prepared-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", action="append", default=[])
    args = parser.parse_args()
    print(prepare(public=load_task_package(args.task).public,
                  prepared_source=args.prepared_source, output=args.output,
                  source_roots=args.source_root))
