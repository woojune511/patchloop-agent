"""Registered dependency reads stay within pinned public Python source."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.dev.dependency_sources import MAX_SOURCE_BYTES, DependencySources
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import PreparedDependencies, read_descriptor
from patchloop.probe_runtime import runtime
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture
def source_bundle(tmp_path):
    contents = {
        "caller/__init__.py": b"raise RuntimeError('source must never be imported')\n",
        "caller/lint/expand.py": b"def expand(items):\n    return list(items)\n",
        "caller/config.txt": b"non-source\n",
        "unregistered/secret.py": b"SECRET = 1\n",
    }
    directory = tmp_path / "site-packages"
    for relative, content in contents.items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    python, image = runtime("python312-v1")
    files = {relative: sha256_bytes(content) for relative, content in contents.items()}
    descriptor = {
        "schema_version": "prepared-probe-dependencies-v1",
        "repository_url": "https://example.invalid/project.git", "base_commit": "a" * 40,
        "python": python, "image": image, "platform": "linux/amd64", "source_roots": [],
        "files": files, "content_hash": sha256_json(files),
        "wheel_lock": {"operator_caller_requirements": ["caller==1.2"],
                       "source_metadata": {"project_name": "project"}},
    }
    path = tmp_path / "prepared-probe-dependencies.json"
    path.write_text(json.dumps(descriptor), encoding="utf-8")
    dependencies = PreparedDependencies(
        path, read_descriptor(path)[1], descriptor["repository_url"], descriptor["base_commit"],
        callers=("caller==1.2",),
    )
    return dependencies, contents


def test_registered_candidates_and_read_have_pinned_provenance(source_bundle):
    dependencies, contents = source_bundle
    sources = DependencySources(dependencies, {"caller": "caller"})
    assert sources.paths("dependency:caller", "caller/**") == [
        "caller/__init__.py", "caller/lint/expand.py",
    ]
    assert sources.paths("dependency:caller", "caller/*.py") == ["caller/__init__.py"]
    assert sources.paths("dependency:caller", "pylint/**") == []
    text, provenance = sources.read("dependency:caller", "caller/lint/expand.py")
    assert text == contents["caller/lint/expand.py"].decode()
    assert provenance == {
        **sources.catalog()[0], "path": "caller/lint/expand.py", "origin": "prepared_dependency",
        "file_hash": sha256_bytes(contents["caller/lint/expand.py"]),
    }
    assert sources.catalog()[0] == {
        "scope": "dependency:caller", "package": "caller", "version": "1.2", "root": "caller",
        "manifest_hash": dependencies.identity.manifest_hash,
        "content_hash": dependencies.identity.content_hash,
    }
    assert sources.identity.startswith("sha256:")
    sources.catalog()[0]["root"] = "changed"
    assert sources.catalog()[0]["root"] == "caller"
    assert "never be imported" in sources.read("dependency:caller", "caller/__init__.py")[0]


@pytest.mark.parametrize("path", [
    "../caller/__init__.py", "/caller/__init__.py", "C:/caller/__init__.py",
    "caller/__init__.py:stream", "caller/../../outside.py", "caller/\x00.py",
    "caller/config.txt", "unregistered/secret.py", "caller/unindexed.py",
])
def test_unregistered_and_unsafe_paths_are_rejected(source_bundle, path):
    dependencies, _ = source_bundle
    sources = DependencySources(dependencies, {"caller": "caller"})
    with pytest.raises(ContractError):
        sources.read("dependency:caller", path)


def test_unregistered_scopes_roots_and_search_traversal_are_rejected(source_bundle):
    dependencies, _ = source_bundle
    sources = DependencySources(dependencies, {"caller": "caller"})
    for operation in (lambda: sources.paths("dependency:unregistered"),
                      lambda: sources.read("dependency:unregistered", "unregistered/secret.py"),
                      lambda: sources.paths("dependency:caller", "../**")):
        with pytest.raises(ContractError):
            operation()
    for roots in ({"unregistered": "unregistered"}, {"caller": "../caller"},
                  {"caller": "."}, {"caller": "caller/*"}, {"caller": "absent"}):
        with pytest.raises(ContractError):
            DependencySources(dependencies, roots)


def test_registry_binds_descriptor_caller_and_source_identities(source_bundle):
    dependencies, _ = source_bundle
    for changed in (replace(dependencies, callers=()),
                    replace(dependencies, base_commit="b" * 40)):
        with pytest.raises(ContractError, match="identity changed"):
            DependencySources(changed, {"caller": "caller"})
    dependencies.path.write_text(dependencies.path.read_text() + " ", encoding="utf-8")
    with pytest.raises(ContractError, match="identity changed"):
        DependencySources(dependencies, {"caller": "caller"})


def test_reads_verify_file_hash_lazily_and_do_not_expose_unindexed_files(source_bundle):
    dependencies, _ = source_bundle
    sources = DependencySources(dependencies, {"caller": "caller"})
    directory = dependencies.path.parent / "site-packages/caller"
    (directory / "unindexed.py").write_text("new source", encoding="utf-8")
    (directory / "lint/expand.py").write_text("changed source", encoding="utf-8")
    assert "caller/unindexed.py" not in sources.paths("dependency:caller")
    assert sources.read("dependency:caller", "caller/__init__.py")
    with pytest.raises(ContractError, match="hash changed"):
        sources.read("dependency:caller", "caller/lint/expand.py")


def test_reads_enforce_source_size_limit(source_bundle):
    dependencies, _ = source_bundle
    sources = DependencySources(dependencies, {"caller": "caller"})
    path = dependencies.path.parent / "site-packages/caller/__init__.py"
    path.write_bytes(b"x" * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(ContractError, match="larger than 2 MB"):
        sources.read("dependency:caller", "caller/__init__.py")


@pytest.mark.parametrize("linked_part", ["file", "ancestor", "root"])
def test_reads_reject_symlinked_file_ancestor_or_root(source_bundle, linked_part):
    dependencies, _ = source_bundle
    sources = DependencySources(dependencies, {"caller": "caller"})
    root = dependencies.path.parent / "site-packages"
    original = {"file": root / "caller/lint/expand.py",
                "ancestor": root / "caller/lint", "root": root}[linked_part]
    target = original.with_name(original.name + "-real")
    original.rename(target)
    try:
        original.symlink_to(target, target_is_directory=linked_part != "file")
    except OSError as exc:
        target.rename(original)
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(ContractError, match="symlinks and reparse"):
        sources.read("dependency:caller", "caller/lint/expand.py")


@pytest.mark.parametrize("relative", ["caller/lint/expand.py", "caller/lint", "."])
def test_reads_reject_windows_reparse_metadata_without_link_privilege(
    source_bundle, monkeypatch, relative,
):
    dependencies, _ = source_bundle
    sources = DependencySources(dependencies, {"caller": "caller"})
    marked = dependencies.path.parent / "site-packages" / relative
    original_lstat = Path.lstat

    def lstat(path, *args, **kwargs):
        result = original_lstat(path, *args, **kwargs)
        if path == marked:
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
        return result

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ContractError, match="symlinks and reparse"):
        sources.read("dependency:caller", "caller/lint/expand.py")
