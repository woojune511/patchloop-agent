"""Prepare public wheels from literal setup.py metadata without executing project code.

This opt-in operator adapter reuses the existing resolver, installer and descriptor.
It intentionally supports only root runtime requirements, not arbitrary setup programs.
"""
from __future__ import annotations

import argparse
import ast
import configparser
import re
import tomllib
from functools import partial
from pathlib import Path
from unittest.mock import patch

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from patchloop import prepared_probe_dependencies as prepared
from patchloop import probe_dependency_resolution as resolution
from patchloop.errors import ContractError
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, safe_relative_path, sha256_bytes


def metadata(repo: Path, *, groups: list[str], extras: list[str],
             requirements_file: str | None = None,
             supplemental_requirements: list[str] | None = None) -> dict:
    if groups or extras:
        raise ContractError("literal setup adapter supports runtime requirements only")
    project_path = repo / "pyproject.toml"
    pyproject = (prepared._read_bytes(project_path)
                 if project_path.exists() or project_path.is_symlink() else None)
    if pyproject is not None and "project" in tomllib.loads(pyproject.decode("utf-8")):
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
    file_record = None
    if requirements_file is None:
        requirements = literal("install_requires", [])
    else:
        relative = safe_relative_path(requirements_file, field_name="requirements file")
        source = repo / relative
        if source.is_symlink() or not source.resolve().is_relative_to(repo.resolve()):
            raise ContractError("public requirements file leaves the prepared source")
        content = prepared._read_bytes(source)
        requirements = [line.strip() for line in content.decode("utf-8").splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
        file_record = {"path": relative, "hash": sha256_bytes(content)}
    if not isinstance(requirements, (list, tuple)) or len(requirements) > 1024:
        raise ContractError("setup runtime requirements must be a bounded literal sequence")
    selected = set()
    supplemental = supplemental_requirements or []
    if len(supplemental) > 32:
        raise ContractError("supplemental requirements exceed the bound")
    for text in [*requirements, *supplemental]:
        if not isinstance(text, str) or any(c in text for c in "\r\n\x00"):
            raise ContractError("setup requirements must be single-line PEP 508 declarations")
        try:
            req = Requirement(text)
        except InvalidRequirement as exc:
            raise ContractError(
                "requirements must be PEP 508 declarations, not pip options"
            ) from exc
        if req.url or canonicalize_name(req.name) == canonicalize_name(name):
            raise ContractError("only public index dependencies are supported; no URL/self deps")
        if req.marker and not req.marker.evaluate(resolution.MARKERS):
            continue
        req.marker = None
        selected.add(str(req))
    entry_points = literal("entry_points", {})
    if not isinstance(entry_points, dict) or len(entry_points) > 64:
        raise ContractError("setup entry points must be a bounded literal mapping")
    normalized = {}
    for group, entries in entry_points.items():
        if (not isinstance(group, str) or not re.fullmatch(r"[A-Za-z0-9_.]+", group)
                or not isinstance(entries, (list, tuple)) or len(entries) > 128):
            raise ContractError("invalid static setup entry point group")
        values = {}
        for entry in entries:
            if not isinstance(entry, str):
                raise ContractError("setup entry points must be literal strings")
            match = re.fullmatch(
                r"\s*([A-Za-z0-9_.-]+)\s*=\s*"
                r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?::[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)?)\s*",
                entry, flags=re.ASCII,
            )
            if match is None or match[1] in values:
                raise ContractError("invalid or duplicate static setup entry point")
            values[match[1]] = match[2]
        normalized[group] = values
    result = {"path": "setup.py", "hash": sha256_bytes(raw), "project_name": name,
            "requires_python": python, "requirements": sorted(selected), "groups": [],
            "extras": [], "adapter": "literal-setup-runtime-v1",
            "pyproject_hash": sha256_bytes(pyproject) if pyproject is not None else None}
    if normalized:
        result["entry_points"] = normalized
    if supplemental:
        # Operator-selected compatibility inputs, never mislabelled as source declarations.
        result["operator_supplemental_requirements"] = supplemental
    if file_record is not None:
        result.update(adapter="operator-selected-requirements-v1", requirements_file=file_record)
    return result


def workspace_metadata(repo, packages, roots, commit, target, *, requirements_file=None,
                       supplemental_requirements=None, lock_directory="."):
    if lock_directory != ".":
        raise ContractError("setup adapter supports root metadata only")
    public = metadata(repo, groups=[], extras=[], requirements_file=requirements_file,
                      supplemental_requirements=supplemental_requirements)
    name, version = public["project_name"], f"0+patchloop.{commit}"
    if packages != [{"name": name, "source": {"editable": "."}}]:
        raise ContractError("setup workspace identity differs from public resolution")
    record = {"name": name, "version": version,
              "version_basis": "source_snapshot_not_release_version", "project_path": ".",
              "pyproject_hash": public["pyproject_hash"], "setup_hash": public["hash"]}
    if "requirements_file" in public:
        record["requirements_file"] = public["requirements_file"]
    for key in ("entry_points", "operator_supplemental_requirements"):
        if key in public:
            record[key] = public[key]
    directory = target / f"{re.sub(r'[-_.]+', '_', name)}-{version}.dist-info"
    directory.mkdir(exist_ok=False)
    (directory / "METADATA").write_text(
        f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n", encoding="utf-8")
    (directory / "PATCHLOOP-SOURCE.json").write_text(canonical_json(record), encoding="utf-8")
    if public.get("entry_points"):
        config = configparser.ConfigParser(interpolation=None)
        config.optionxform = str
        config.read_dict(public["entry_points"])
        with (directory / "entry_points.txt").open("w", encoding="utf-8") as stream:
            config.write(stream)
    return [record]


def prepare(*, public, prepared_source: Path, output: Path, source_roots: list[str],
            requirements_file: str | None = None,
            supplemental_requirements: list[str] | None = None,
            generated_wheel_receipt: Path | None = None,
            generated_wheel_receipt_hash: str | None = None):
    reader, writer = metadata, workspace_metadata
    if requirements_file is not None or supplemental_requirements:
        options = {"requirements_file": requirements_file,
                   "supplemental_requirements": supplemental_requirements}
        reader = partial(metadata, **options)
        writer = partial(workspace_metadata, **options)
    with patch.object(resolution, "project_requirements", reader), \
            patch.object(prepared, "_workspace_metadata", writer):
        return prepared.prepare_dependencies(public=public, prepared_source=prepared_source,
            output=output, source_roots=source_roots, resolve=True,
            generated_wheel_receipt=generated_wheel_receipt,
            generated_wheel_receipt_hash=generated_wheel_receipt_hash)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path)
    parser.add_argument("--prepared-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", action="append", default=[])
    parser.add_argument("--requirements-file", help="Reviewed repository-relative PEP 508 file")
    parser.add_argument("--supplemental-requirement", action="append", default=[],
                        help="Explicit public-index compatibility requirement, recorded separately")
    parser.add_argument("--generated-wheel-receipt", type=Path)
    parser.add_argument("--generated-wheel-receipt-hash")
    args = parser.parse_args()
    print(prepare(public=load_task_package(args.task).public,
                  prepared_source=args.prepared_source, output=args.output,
                  source_roots=args.source_root, requirements_file=args.requirements_file,
                  supplemental_requirements=args.supplemental_requirement,
                  generated_wheel_receipt=args.generated_wheel_receipt,
                  generated_wheel_receipt_hash=args.generated_wheel_receipt_hash))
