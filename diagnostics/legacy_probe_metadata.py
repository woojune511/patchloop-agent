"""Read public static setup metadata without importing a repository or running builds."""

from __future__ import annotations

import ast
import configparser
import re
import tomllib
from functools import partial
from unittest.mock import patch

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from patchloop import prepared_probe_dependencies as prepared
from patchloop import probe_dependency_resolution as resolution
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


def _setup(repo):
    raw = prepared._read_bytes(repo / "setup.py")
    tree = ast.parse(raw)
    assignments = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                assignments.setdefault(target.id, []).append(node.value)

    def value(node, seen=()):
        if isinstance(node, ast.Name):
            choices = assignments.get(node.id, [])
            if len(choices) != 1 or node.id in seen:
                raise ContractError("ambiguous/nonliteral public setup metadata")
            return value(choices[0], (*seen, node.id))
        if isinstance(node, ast.Dict):
            return {
                value(k, seen): value(v, seen)
                for k, v in zip(node.keys, node.values, strict=True)
            }
        if isinstance(node, (ast.List, ast.Tuple)):
            return [value(n, seen) for n in node.elts]
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "dict"
        ):
            # Resolve only the selected keys later; setup dicts contain executable
            # version/description values that are never needed or evaluated here.
            return {k.arg: k.value for k in node.keywords}
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError) as exc:
            raise ContractError("public setup field is not static") from exc

    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "setup"
    ]
    if len(calls) != 1 or calls[0].args:
        raise ContractError("one public setup call required")
    fields = {n.arg: n.value for n in calls[0].keywords if n.arg is not None}
    for keyword in calls[0].keywords:
        if keyword.arg is None:
            expanded = value(keyword.value)
            if not isinstance(expanded, dict) or set(fields) & set(expanded):
                raise ContractError("ambiguous setup keyword expansion")
            fields.update(expanded)

    def selected(key, default):
        node = fields.get(key, default)
        return value(node) if isinstance(node, ast.AST) else node

    return {
        "path": "setup.py",
        "hash": sha256_bytes(raw),
        "project_name": selected("name", None),
        "requires_python": selected("python_requires", ""),
        "requirements": selected("install_requires", []),
        "entry_points": selected("entry_points", {}),
    }


def metadata(repo, *, groups, extras, supplements=(), python="3.12"):
    if groups or extras:
        raise ContractError("this adapter resolves public runtime requirements only")
    pyproject = repo / "pyproject.toml"
    if pyproject.exists() and "project" in tomllib.loads(prepared._read_bytes(pyproject).decode()):
        result = _PEP_METADATA(repo, groups=[], extras=[])
    elif (repo / "setup.cfg").exists():
        raw = prepared._read_bytes(repo / "setup.cfg")
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(raw.decode())
        if not config.has_option("metadata", "name"):
            result = _setup(repo)
        else:

            def lines(section, key):
                return [
                    s.strip()
                    for s in config.get(section, key, fallback="").splitlines()
                    if s.strip() and not s.strip().startswith("#")
                ]

            result = {
                "path": "setup.cfg",
                "hash": sha256_bytes(raw),
                "project_name": config.get("metadata", "name"),
                "requires_python": config.get("options", "python_requires", fallback=""),
                "requirements": lines("options", "install_requires"),
                "entry_points": {
                    k: lines("options.entry_points", k)
                    for k in config.options("options.entry_points")
                }
                if config.has_section("options.entry_points")
                else {},
            }
    else:
        result = _setup(repo)
    name = result["project_name"]
    if result["requires_python"] and python not in SpecifierSet(result["requires_python"]):
        raise ContractError("public Python requirement excludes the probe interpreter")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise ContractError("public project name must be literal")
    requirements = []
    for item in [*result["requirements"], *supplements]:
        req = Requirement(item)
        if req.url or canonicalize_name(req.name) == canonicalize_name(name):
            raise ContractError("only public index third-party dependencies supported")
        if req.marker and not req.marker.evaluate(resolution.target_markers(python)):
            continue
        req.marker = None
        requirements.append(str(req))
    result.update(
        requirements=sorted(set(requirements)),
        groups=[],
        extras=[],
        adapter="static-public-metadata-v1",
        operator_supplemental_requirements=list(supplements),
    )
    return result


_PEP_METADATA = resolution.project_requirements


def read_metadata(repo, *, groups, extras, supplements=(), python="3.12"):
    # Keep the original reader explicit; replacing its module binding must not recurse.
    path = repo / "pyproject.toml"
    if path.exists() and "project" in tomllib.loads(prepared._read_bytes(path).decode()):
        base = _PEP_METADATA(repo, groups=groups, extras=extras, python=python)
        for text in supplements:
            req = Requirement(text)
            if req.url:
                raise ContractError("only public index supplements supported")
        return {
            **base,
            "requirements": sorted(set([*base["requirements"], *supplements])),
            "operator_supplemental_requirements": list(supplements),
        }
    return metadata(repo, groups=groups, extras=extras, supplements=supplements, python=python)


def prepare(public, prepared_source, output, roots, supplements=(), installed_limit_mib=256,
            runtime_profile="python312-v1", caller_requirements=None):
    from patchloop.probe_runtime import runtime

    reader = partial(read_metadata, supplements=supplements, python=runtime(runtime_profile)[0])

    def writer(repo, packages, roots, commit, target, *, lock_directory="."):
        if lock_directory != ".":
            raise ContractError("root metadata required")
        info = reader(repo, groups=[], extras=[])
        name, version = info["project_name"], f"0+patchloop.{commit}"
        if packages != [{"name": canonicalize_name(name), "source": {"editable": "."}}]:
            raise ContractError("workspace metadata identity mismatch")
        folder = target / f"{re.sub(r'[-_.]+', '_', name)}-{version}.dist-info"
        folder.mkdir()
        record = {
            "name": name,
            "version": version,
            "version_basis": "source_snapshot_not_release_version",
            "project_path": ".",
            "public_metadata": info,
            "metadata_path": info["path"],
            "metadata_hash": info["hash"],
            "pyproject_hash": sha256_bytes((repo / "pyproject.toml").read_bytes())
            if (repo / "pyproject.toml").exists() else None,
        }
        (folder / "METADATA").write_text(
            f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n", encoding="utf-8"
        )
        (folder / "PATCHLOOP-SOURCE.json").write_text(canonical_json(record), encoding="utf-8")
        points = info.get("entry_points") or {}
        if points:
            cfg = configparser.ConfigParser(interpolation=None)
            cfg.optionxform = str
            for group, entries in points.items():
                cfg[group] = {}
                for entry in entries:
                    key, separator, value = entry.partition("=")
                    if not separator or not re.fullmatch(r"[\w.:]+", value.strip()):
                        raise ContractError("unsupported static plugin entry point")
                    cfg[group][key.strip()] = value.strip()
            with (folder / "entry_points.txt").open("w", encoding="utf-8") as stream:
                cfg.write(stream)
        return [record]

    with (
        patch.object(resolution, "project_requirements", reader),
        patch.object(prepared, "_workspace_metadata", writer),
    ):
        return prepared.prepare_dependencies(
            public=public,
            prepared_source=prepared_source,
            output=output,
            source_roots=roots,
            resolve=True,
            installed_limit_mib=installed_limit_mib,
            runtime_profile=runtime_profile,
            caller_requirements=caller_requirements,
        )
