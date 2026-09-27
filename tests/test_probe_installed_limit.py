import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_prepared_probe_dependencies import bundle, prepare_fixture  # noqa: F401

from patchloop import prepared_probe_dependencies as prepared
from patchloop.errors import ContractError


def test_inventory_enforces_separate_installed_bound(tmp_path):
    (tmp_path / "data").write_bytes(b"123456789")
    assert prepared._inventory(tmp_path, byte_limit=9)
    with pytest.raises(ContractError, match="byte bound"):
        prepared._inventory(tmp_path, byte_limit=8)
    assert prepared.MAX_BYTES == 256 * 1024 * 1024


@pytest.mark.parametrize("grow", [False, True])
def test_small_file_reads_do_not_reserve_bundle_capacity(tmp_path, monkeypatch, grow):
    path = tmp_path / "data"
    path.write_bytes(b"small")
    original = Path.open
    requested = []

    @contextmanager
    def opened(self, *args, **kwargs):
        with original(self, *args, **kwargs) as stream:
            def read(size):
                requested.append(size)
                data = stream.read(size)
                if grow:
                    with original(path, "ab") as writer:
                        writer.write(b"changed")
                return data
            yield SimpleNamespace(fileno=stream.fileno, read=read)

    monkeypatch.setattr(Path, "open", opened)
    if grow:
        with pytest.raises(ContractError, match="size changed"):
            prepared._inventory(tmp_path, byte_limit=512 * 1024 * 1024)
    else:
        assert prepared._inventory(tmp_path, byte_limit=512 * 1024 * 1024)
    assert requested == [6]


@pytest.mark.parametrize("limit", [255, 1025, 256.0, True])
def test_bad_limit_rejected_before_output(tmp_path, limit):
    output = tmp_path / "absent"
    with pytest.raises(ContractError, match="limit"):
        prepared.prepare_dependencies(public=None, prepared_source=tmp_path / "source",
                                      output=output, resolve=True, installed_limit_mib=limit)
    assert not output.exists()


@pytest.mark.parametrize("limit", [256, 512, 768, 1024])
def test_preparation_publishes_only_nondefault_limit(prepare_fixture, limit):  # noqa: F811
    path = prepared.prepare_dependencies(**prepare_fixture, installed_limit_mib=limit)
    descriptor, identity = prepared.read_descriptor(path)
    assert ("installed_byte_limit" in descriptor) == (limit != 256)
    assert prepared._installed_limit(descriptor) == limit * 1024 * 1024
    dependency = prepared.load_dependencies(path, prepare_fixture["public"], identity)
    dependency.verify()


def test_admitted_limit_enforced_on_copy(bundle, smoke_package, monkeypatch):  # noqa: F811
    descriptor = json.loads(bundle.read_bytes())
    descriptor["installed_byte_limit"] = 512 * 1024 * 1024
    bundle.write_text(json.dumps(descriptor))
    identity = prepared.admit(bundle)
    dependency = prepared.load_dependencies(bundle, smoke_package.public, identity)
    real = prepared._inventory
    observed = []

    def inventory(*args, **kwargs):
        observed.append(kwargs["byte_limit"])
        return real(*args, **kwargs)

    monkeypatch.setattr(prepared, "_inventory", inventory)
    dependency.verify(target=bundle.parent / "copy")
    assert observed == [512 * 1024 * 1024]
    descriptor["installed_byte_limit"] = 768 * 1024 * 1024
    bundle.write_text(json.dumps(descriptor))
    with pytest.raises(ContractError, match="identity changed"):
        dependency.verify()


@pytest.mark.parametrize("value", [True, 1, 2**40, 512 * 1024 * 1024 + 1])
def test_descriptor_limit_cannot_escape_supported_range(bundle, value):  # noqa: F811
    descriptor = json.loads(bundle.read_bytes())
    descriptor["installed_byte_limit"] = value
    bundle.write_text(json.dumps(descriptor))
    assert prepared.admit(bundle) is None


def test_package_snapshot_root_is_not_an_import_search_root(prepare_fixture):  # noqa: F811
    repo = prepare_fixture["output"].parent / "source"
    (repo / "src/__init__.py").write_text("")
    path = prepared.prepare_dependencies(**prepare_fixture)
    descriptor, identity = prepared.read_descriptor(path)
    assert descriptor["source_roots"] == ["src"]
    assert descriptor["import_roots"] == []
    dependency = prepared.load_dependencies(path, prepare_fixture["public"], identity)
    assert dependency.environment["source_roots"] == ["/workspace"]


def test_import_root_cannot_escape_selected_source(bundle):  # noqa: F811
    descriptor = json.loads(bundle.read_bytes())
    descriptor["import_roots"] = ["/private"]
    bundle.write_text(json.dumps(descriptor))
    assert prepared.admit(bundle) is None
