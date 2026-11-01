"""The one-arm continuation must preserve the originally authorized comparison."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from diagnostics import feedback_source_remaining as r
from patchloop.errors import ContractError


def plans():
    old = {key: {"unchanged": key} for key in (
        "scope", "runtime_hash", "credential_file", "bundle_hash",
        "first_request_hashes", "interpretation")}
    old["bindings"] = [{"path": str(Path(r.f.__file__).resolve()), "hash": "before"},
                       {"path": "public-evidence", "hash": "fixed"}]
    new = copy.deepcopy(old)
    new["bindings"][0]["hash"] = "no-diff-postmodel-fix"
    return old, new


def test_only_postmodel_operator_binding_can_change():
    old, new = plans()
    r.assert_same_conditions(old, new)
    new["bindings"][1]["hash"] = "changed"
    with pytest.raises(ContractError, match="extend beyond"):
        r.assert_same_conditions(old, new)


@pytest.mark.parametrize("key", ["scope", "runtime_hash", "credential_file",
                                 "bundle_hash", "first_request_hashes"])
def test_original_conditions_cannot_change(key):
    old, new = plans()
    new[key] = {"changed": key}
    with pytest.raises(ContractError, match="condition changed"):
        r.assert_same_conditions(old, new)


def test_started_r1_cannot_be_repeated(tmp_path, monkeypatch):
    original = tmp_path / "original.json"
    original.write_bytes(b"{}")
    monkeypatch.setattr(r, "ORIGINAL", original)
    monkeypatch.setattr(r, "ORIGINAL_HASH", r.f.sha256_bytes(b"{}"))
    monkeypatch.setattr(r, "PRIOR", tmp_path)
    (tmp_path / "R1").mkdir()
    with pytest.raises(ContractError, match="already started"):
        r.prior_result()


def test_another_output_directory_cannot_reopen_remaining_r1(tmp_path):
    with pytest.raises(ContractError, match="one fixed"):
        r.prepare(tmp_path / "plan", tmp_path / "another-attempt")
