"""Resolve static public project metadata for the fixed, offline probe environment."""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

from patchloop.artifacts import ArtifactStore
from patchloop.errors import ContractError
from patchloop.generated_probe_wheel import GeneratedWheel
from patchloop.prepared_probe_dependencies import PublicWheel, _read_bytes
from patchloop.prepared_source import PreparedSource
from patchloop.util import canonical_json, sha256_bytes

# Match the existing installer target; never resolve for the Windows host interpreter.
PYTHON = "3.12"
PLATFORM = "x86_64-manylinux_2_28"
MARKERS = {
    "implementation_name": "cpython", "implementation_version": "3.12.0",
    "os_name": "posix", "platform_machine": "x86_64", "platform_release": "",
    "platform_system": "Linux", "platform_version": "",
    "python_full_version": "3.12.0", "platform_python_implementation": "CPython",
    "python_version": PYTHON, "sys_platform": "linux", "extra": "",
}


def _named_table(value: dict) -> dict:
    result = {}
    for name, items in value.items():
        key = canonicalize_name(name, validate=True)
        if key in result or not isinstance(items, list):
            raise ContractError("dependency group/extra names must be unique lists")
        result[key] = items
    return result


def _group(name: str, groups: dict, seen: tuple[str, ...] = ()) -> list[str]:
    name = canonicalize_name(name, validate=True)
    if name in seen or len(seen) >= 32:
        raise ContractError("dependency group includes form a cycle or exceed the depth bound")
    if name not in groups:
        raise ContractError(f"public dependency group is absent: {name}")
    result = []
    for item in groups[name]:
        if isinstance(item, dict) and set(item) == {"include-group"}:
            result.extend(_group(item["include-group"], groups, (*seen, name)))
        elif isinstance(item, str):
            result.append(item)
        else:
            raise ContractError("unsupported public dependency group entry")
        if len(result) > 1024:
            raise ContractError("selected public dependencies exceed the requirement bound")
    return result


def project_requirements(repo: Path, *, groups: list[str], extras: list[str]) -> dict:
    """Read PEP 621/735 data only; never import the project or invoke its build backend."""
    path = repo / "pyproject.toml"
    if not path.resolve().is_relative_to(repo):
        raise ContractError("public project metadata leaves the prepared source")
    raw = _read_bytes(path)
    data = tomllib.loads(raw.decode("utf-8"))
    project = data["project"]
    name = canonicalize_name(project["name"], validate=True)
    dynamic = project.get("dynamic", [])
    if "dependencies" in dynamic or "optional-dependencies" in dynamic:
        raise ContractError("dynamic public dependencies require build hooks and are unsupported")
    requires_python = project.get("requires-python", "")
    if not SpecifierSet(requires_python).contains(MARKERS["python_full_version"]):
        raise ContractError("public project does not support the probe Python target")
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise ContractError("public project dependencies must be a list")
    declarations = [(item, "") for item in dependencies]
    optional = _named_table(project.get("optional-dependencies", {}))
    for extra in extras:
        if extra not in optional:
            raise ContractError(f"public project extra is absent: {extra}")
        declarations.extend((item, extra) for item in optional[extra])
    group_table = _named_table(data.get("dependency-groups", {}))
    for group in groups:
        declarations.extend((item, "") for item in _group(group, group_table))
    if len(declarations) > 1024:
        raise ContractError("selected public dependencies exceed the requirement bound")
    selected = set()
    for text, extra in declarations:
        if not isinstance(text, str) or any(char in text for char in "\r\n\x00"):
            raise ContractError("public dependencies must be single-line PEP 508 requirements")
        requirement = Requirement(text)
        if requirement.url or canonicalize_name(requirement.name) == name:
            raise ContractError(
                "only public index dependencies are supported; no URL/path/self deps",
            )
        if requirement.marker and not requirement.marker.evaluate({**MARKERS, "extra": extra}):
            continue
        requirement.marker = None
        selected.add(str(requirement))
    return {"path": "pyproject.toml", "hash": sha256_bytes(raw), "project_name": project["name"],
            "requires_python": requires_python, "groups": groups, "extras": extras,
            "requirements": sorted(selected)}


def select_wheels(raw: bytes, *, project_name: str,
                  generated: GeneratedWheel | None = None) -> list[PublicWheel | GeneratedWheel]:
    """Choose one compatible wheel per resolved package, without host platform tags."""
    lock = tomllib.loads(raw.decode("utf-8"))
    if lock.get("lock-version") != "1.0" or lock.get("created-by") != "uv":
        raise ContractError("unsupported resolver lock format")
    if not SpecifierSet(lock.get("requires-python", "")).contains(MARKERS["python_full_version"]):
        raise ContractError("resolver lock excludes the probe Python target")
    platforms = [f"manylinux_2_{minor}_x86_64" for minor in range(28, 4, -1)]
    platforms.extend(["manylinux2014_x86_64", "manylinux2010_x86_64", "manylinux1_x86_64",
                      "linux_x86_64"])
    tags = [*cpython_tags((3, 12), abis=["cp312"], platforms=platforms),
            *compatible_tags((3, 12), interpreter="cp312", platforms=platforms)]
    ranks = {tag: index for index, tag in enumerate(tags)}
    selected, names = [], set()
    for package in lock.get("packages", []):
        if package.get("marker") and not Marker(package["marker"]).evaluate(MARKERS):
            continue
        name = canonicalize_name(package["name"], validate=True)
        if name in names or name == canonicalize_name(project_name):
            raise ContractError(
                "resolver lock duplicates a package or includes the workspace project",
            )
        if any(key in package for key in ("vcs", "directory", "archive")):
            raise ContractError("resolver lock must contain public index wheels only")
        names.add(name)
        candidates = []
        for item in package.get("wheels", []):
            if generated is not None and item.get("url") == generated.url:
                wheel = generated
                if item.get("hashes", {}).get("sha256", generated.hash[7:]) != generated.hash[7:]:
                    raise ContractError("resolver changed the generated wheel hash")
            else:
                if item.get("url", "").startswith("file:"):
                    raise ContractError("resolver selected an unreviewed local wheel")
                wheel = PublicWheel(url=item["url"], hash="sha256:" + item["hashes"]["sha256"],
                                    size=item["size"])
            wheel_name, version, _, wheel_tags = parse_wheel_filename(wheel.url.rsplit("/", 1)[-1])
            if wheel_name != name or version != Version(package["version"]):
                raise ContractError("resolver wheel does not match its package name/version")
            matches = [ranks[tag] for tag in wheel_tags if tag in ranks]
            if matches:
                candidates.append((min(matches), wheel.url, wheel))
        if not candidates:
            raise ContractError(f"no compatible public wheel for resolved package: {name}")
        selected.append(min(candidates, key=lambda item: item[:2])[2])
        if len(selected) > 128:
            raise ContractError("resolved public dependencies exceed the wheel bound")
    return selected


def resolve_dependencies(
    *, repo: Path, source: PreparedSource, source_hash: str, output: Path, uv: str,
    groups: list[str], extras: list[str], source_roots: list[str],
    selected_dependencies: list[str] | None = None,
    generated: GeneratedWheel | None = None,
    generated_provenance: dict | None = None,
) -> tuple[dict, list[PublicWheel | GeneratedWheel], list[dict]]:
    from patchloop.sandbox.probes import PROBE_IMAGE

    groups = sorted({canonicalize_name(name, validate=True) for name in groups})
    extras = sorted({canonicalize_name(name, validate=True) for name in extras})
    metadata = project_requirements(repo, groups=groups, extras=extras)
    if selected_dependencies:
        if not (groups or extras):
            raise ContractError("--select-dependency requires a public --group or --extra")
        names = sorted({canonicalize_name(name, validate=True) for name in selected_dependencies})
        requirements = metadata["requirements"]
        declared = {canonicalize_name(Requirement(item).name) for item in requirements}
        if set(names) - declared:
            raise ContractError("selected dependency is absent from target public declarations")
        runtime = project_requirements(repo, groups=[], extras=[])["requirements"]
        metadata["requirements"] = [item for item in requirements if item in runtime
                                    or canonicalize_name(Requirement(item).name) in names]
        metadata["selected_dependencies"] = names
    target = {"python": PYTHON, "platform": "linux/amd64", "image": PROBE_IMAGE,
              "wheel_platform": PLATFORM, "marker_environment": MARKERS}
    provenance = {"schema_version": "resolved-public-probe-wheel-lock-v1",
                  "prepared_source": source.model_dump(mode="json"),
                  "prepared_source_hash": source_hash, "source_metadata": metadata,
                  "source_roots": source_roots, "target": target,
                  "index": "https://pypi.org/simple"}
    if generated_provenance is not None:
        provenance["generated_wheel"] = generated_provenance
    store = ArtifactStore(output)
    store.write_text_immutable(output / "resolution-input.json", canonical_json(provenance))
    requirements = output / "requirements.in"
    store.write_text_immutable(requirements, "\n".join(metadata["requirements"]) + "\n")
    # Public resolution must not consult the operator's saved HTTP credentials.
    credentials = output / "resolver-credentials"
    credentials.mkdir()
    store.write_text_immutable(credentials / "netrc", "")
    lock_path = output / "pylock.toml"
    command = [uv, "pip", "compile", str(requirements), "--format", "pylock.toml",
               "--output-file", str(lock_path), "--python", sys.executable,
               "--python-version", PYTHON, "--python-platform", PLATFORM,
               "--only-binary", ":all:", "--no-config", "--no-cache", "--no-sources",
               "--no-python-downloads", "--default-index", "https://pypi.org/simple",
               "--keyring-provider", "disabled", "--no-header"]
    if generated is not None:
        command.extend(["--find-links", str(output / "generated-wheels")])
    resolver_hash = sha256_bytes(Path(uv).read_bytes())
    result = subprocess.run(command, capture_output=True, check=False, timeout=120, cwd=output,
                            env={**{key: os.environ[key] for key in
                                    ("PATH", "SystemRoot", "TEMP", "TMP") if key in os.environ},
                                 "UV_HTTP_RETRIES": "0", "UV_CREDENTIALS_DIR": str(credentials),
                                 "NETRC": str(credentials / "netrc")})
    receipt = {"argv": command, "exit_code": result.returncode, "resolver_hash": resolver_hash,
               "stdout": result.stdout.decode("utf-8", errors="replace")[-12_000:],
               "stderr": result.stderr.decode("utf-8", errors="replace")[-12_000:]}
    store.write_text_immutable(output / "resolve.json", canonical_json(receipt))
    if result.returncode:
        raise ContractError("public dependency resolution failed; no descriptor published")
    raw_lock = _read_bytes(lock_path)
    wheels = select_wheels(raw_lock, project_name=metadata["project_name"], generated=generated)
    if generated is not None and generated not in wheels:
        raise ContractError("reviewed generated wheel was not selected by public requirements")
    provenance.update({"resolver_hash": resolver_hash, "pylock_hash": sha256_bytes(raw_lock),
                       "resolve_receipt_hash": sha256_bytes((output / "resolve.json").read_bytes()),
                       "wheels": [wheel.model_dump(mode="json") for wheel in wheels]})
    store.write_text_immutable(output / "resolved-wheel-lock.json", canonical_json(provenance))
    packages = [{"name": metadata["project_name"], "source": {"editable": "."}}]
    return provenance, wheels, packages
