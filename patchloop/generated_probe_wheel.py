"""Admission of an explicitly reviewed, offline-built public pure-Python wheel.

Receipts are operator provenance, not cryptographic proof of build isolation.
No build hooks or package imports execute during admission.
"""

from __future__ import annotations

import io
import json
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name, parse_wheel_filename
from pydantic import Field

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import StrictModel
from patchloop.errors import ContractError
from patchloop.util import safe_relative_path, sha256_bytes


class BuildFile(StrictModel):
    path: str
    hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size: int = Field(gt=0, le=256 * 1024 * 1024)


class PublicBuildFile(BuildFile):
    url: str


class BuildReceipt(StrictModel):
    schema_version: Literal["public-built-probe-wheel-v1"]
    source: PublicBuildFile
    source_metadata: BuildFile
    build_tools: list[PublicBuildFile] = Field(min_length=1, max_length=16)
    script: BuildFile
    result: BuildFile
    image: str
    network: Literal["none"]
    exit_code: Literal[0]
    wheel: BuildFile


class GeneratedWheel(StrictModel):
    url: str
    hash: str
    size: int
    receipt_hash: str


def stage_receipt(path: Path, expected_hash: str, output: Path) -> tuple[GeneratedWheel, dict]:
    from patchloop.prepared_probe_dependencies import PublicWheel, _read_bytes
    from patchloop.sandbox.probes import PROBE_IMAGE

    raw = _read_bytes(path)
    if sha256_bytes(raw) != expected_hash:
        raise ContractError("generated wheel receipt differs from its reviewed hash")
    receipt = BuildReceipt.model_validate_json(raw)
    if receipt.image != PROBE_IMAGE:
        raise ContractError("generated wheel requires the reviewed clean Python image")
    store = ArtifactStore(output)
    evidence = {}

    def read(item: BuildFile) -> bytes:
        relative = safe_relative_path(item.path, field_name="build evidence path")
        target = path.parent / relative
        if not target.resolve().is_relative_to(path.parent.resolve()):
            raise ContractError("build evidence escapes receipt directory")
        for part in (target, *target.parents):
            if part == path.parent:
                break
            if part.is_symlink() or getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
                raise ContractError("build evidence must not use links")
        data = _read_bytes(target, item.size)
        if len(data) != item.size or sha256_bytes(data) != item.hash:
            raise ContractError("generated wheel build evidence hash/size mismatch")
        evidence[item.path] = store.put_bytes(data).model_dump(mode="json")
        return data

    source_url = urlsplit(receipt.source.url)
    if (source_url.scheme != "https" or source_url.netloc != "files.pythonhosted.org"
            or not source_url.path.startswith("/packages/") or source_url.query
            or source_url.fragment or "%" in source_url.path
            or not source_url.path.endswith(".tar.gz")):
        raise ContractError("generated wheel source must be a public PyPI sdist")
    read(receipt.source)
    metadata = json.loads(read(receipt.source_metadata))
    if not any(item.get("packagetype") == "sdist" and item.get("url") == receipt.source.url
               and item.get("size") == receipt.source.size
               and "sha256:" + item.get("digests", {}).get("sha256", "") == receipt.source.hash
               for item in metadata.get("urls", [])):
        raise ContractError("source is not bound by the saved public release metadata")
    for tool in receipt.build_tools:
        PublicWheel(url=tool.url, hash=tool.hash, size=tool.size)
        read(tool)
    read(receipt.script)
    if json.loads(read(receipt.result)).get("exit_code") != 0:
        raise ContractError("generated wheel build did not complete successfully")
    wheel_bytes = read(receipt.wheel)
    filename = Path(receipt.wheel.path).name
    name, version, _, tags = parse_wheel_filename(filename)
    if {str(tag) for tag in tags} != {"py3-none-any"}:
        raise ContractError("generated wheel admission currently supports pure Python only")
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
        names = archive.namelist()
        selected = [n for n in names if n.endswith(".dist-info/METADATA")]
        if len(selected) != 1 or archive.getinfo(selected[0]).file_size > 4_000_000:
            raise ContractError("generated wheel metadata is missing or ambiguous")
        info = BytesParser().parsebytes(archive.read(selected[0]))
    if (canonicalize_name(info["Name"]) != name or info["Version"] != str(version)
            or canonicalize_name(metadata["info"]["name"]) != name
            or metadata["info"]["version"] != str(version)):
        raise ContractError("generated wheel identity differs from its public source")
    if not SpecifierSet(info.get("Requires-Python", "")).contains("3.12.0"):
        raise ContractError("generated wheel excludes the probe Python target")
    if any(Requirement(value).url for value in info.get_all("Requires-Dist", [])):
        raise ContractError("generated wheel URL dependencies are unsupported")
    target = output / "generated-wheels" / filename
    store.write_bytes_atomic(target, wheel_bytes)
    return GeneratedWheel(url=target.as_uri(), hash=receipt.wheel.hash,
                          size=receipt.wheel.size, receipt_hash=expected_hash), {
        "receipt_hash": expected_hash, "receipt": receipt.model_dump(mode="json"),
        "evidence": evidence,
    }
