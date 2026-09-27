import io
import json
import zipfile

import pytest

from patchloop.errors import ContractError
from patchloop.generated_probe_wheel import stage_receipt
from patchloop.prepared_probe_dependencies import prepare_dependencies
from patchloop.probe_dependency_resolution import select_wheels
from patchloop.sandbox.probes import PROBE_IMAGE
from patchloop.util import sha256_bytes


@pytest.fixture
def receipt(tmp_path):
    def file(name, data, url=None):
        (tmp_path / name).write_bytes(data)
        return {"path": name, "hash": sha256_bytes(data), "size": len(data),
                **({"url": url} if url else {})}

    source = file("source.tar.gz", b"public source",
                  "https://files.pythonhosted.org/packages/aa/demo-1.0.tar.gz")
    metadata = {"info": {"name": "demo", "version": "1.0"}, "urls": [{
        "packagetype": "sdist", "url": source["url"], "size": source["size"],
        "digests": {"sha256": source["hash"][7:]},
    }]}
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("demo-1.0.dist-info/METADATA",
                         "Name: demo\nVersion: 1.0\nRequires-Dist: numpy\n")
    value = {
        "schema_version": "public-built-probe-wheel-v1", "source": source,
        "source_metadata": file("metadata.json", json.dumps(metadata).encode()),
        "build_tools": [file("tool.whl", b"tool",
                              "https://files.pythonhosted.org/packages/aa/tool.whl")],
        "script": file("build.py", b"reviewed build"),
        "result": file("result.json", b'{"exit_code":0}'),
        "image": PROBE_IMAGE, "network": "none", "exit_code": 0,
        "wheel": file("demo-1.0-py3-none-any.whl", data.getvalue()),
    }
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(value))
    return path, value


def test_stage_verified_wheel_and_reject_unreviewed_resolver_file(receipt, tmp_path):
    path, _ = receipt
    wheel, record = stage_receipt(path, sha256_bytes(path.read_bytes()), tmp_path / "out")
    assert record["evidence"] and wheel.receipt_hash == record["receipt_hash"]
    raw = ('lock-version="1.0"\ncreated-by="uv"\nrequires-python=">=3.12"\n'
           '[[packages]]\nname="demo"\nversion="1.0"\n[[packages.wheels]]\n'
           f'url="{wheel.url}"\nhashes={{}}\n').encode()
    assert select_wheels(raw, project_name="project", generated=wheel) == [wheel]
    with pytest.raises(ContractError, match="unreviewed local"):
        select_wheels(raw, project_name="project")


@pytest.mark.parametrize("field", ["source", "source_metadata", "script", "result", "wheel"])
def test_changed_build_evidence_is_rejected(receipt, tmp_path, field):
    path, value = receipt
    (tmp_path / value[field]["path"]).write_bytes(b"changed")
    with pytest.raises(ContractError, match="hash/size|size bound"):
        stage_receipt(path, sha256_bytes(path.read_bytes()), tmp_path / "out")


def test_changed_reviewed_receipt_is_rejected(receipt, tmp_path):
    path, _ = receipt
    digest = sha256_bytes(path.read_bytes())
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ContractError, match="reviewed hash"):
        stage_receipt(path, digest, tmp_path / "out")


@pytest.mark.parametrize("change", ["escape", "image", "source_url", "failed_build"])
def test_receipt_cannot_expand_admission(receipt, tmp_path, change):
    path, value = receipt
    if change == "escape":
        value["source"]["path"] = "../source.tar.gz"
    elif change == "image":
        value["image"] = "unreviewed:latest"
    elif change == "source_url":
        value["source"]["url"] = "https://example.com/source.tar.gz"
    else:
        raw = b'{"exit_code":1}'
        (tmp_path / "result.json").write_bytes(raw)
        value["result"].update(hash=sha256_bytes(raw), size=len(raw))
    path.write_text(json.dumps(value))
    with pytest.raises((ContractError, ValueError)):
        stage_receipt(path, sha256_bytes(path.read_bytes()), tmp_path / "out")


@pytest.mark.parametrize("options", [
    {"generated_wheel_receipt_hash": "sha256:" + "a" * 64},
    {"generated_wheel_receipt": "receipt.json"},
    {"generated_wheel_receipt": "receipt.json",
     "generated_wheel_receipt_hash": "sha256:" + "a" * 64},
])
def test_generated_options_fail_before_output_creation(tmp_path, options):
    target = tmp_path / "not-created"
    with pytest.raises(ContractError, match="generated wheel"):
        prepare_dependencies(public=None, prepared_source=tmp_path / "source",
                             output=target, **options)
    assert not target.exists()


def test_generated_metadata_cannot_request_url_dependencies(receipt, tmp_path):
    path, value = receipt
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("demo-1.0.dist-info/METADATA", "Name: demo\nVersion: 1.0\n"
                         "Requires-Dist: injected @ https://example.com/injected.whl\n")
    raw = data.getvalue()
    (tmp_path / value["wheel"]["path"]).write_bytes(raw)
    value["wheel"].update(hash=sha256_bytes(raw), size=len(raw))
    path.write_text(json.dumps(value))
    with pytest.raises(ContractError, match="URL dependencies"):
        stage_receipt(path, sha256_bytes(path.read_bytes()), tmp_path / "out")
