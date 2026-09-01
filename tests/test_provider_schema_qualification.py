from __future__ import annotations

import copy
import json
import socket
import subprocess
from pathlib import Path

import pytest

from patchloop.agent import provider_schema_qualification as qualification
from patchloop.agent.runner import AgentRunner, _provider_input_count_boundary
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.util import sha256_json
from tests.test_provider_schema_runner import _manifest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("offline qualification must not dispatch external work")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(AgentRunner, "start", forbidden)
    monkeypatch.setattr(AgentRunner, "resume", forbidden)


def test_qualification_is_deterministic_and_matches_committed_bytes():
    first = qualification.build_qualification(ROOT)
    second = qualification.build_qualification(ROOT)
    raw = qualification.qualification_bytes(first)
    assert raw == qualification.qualification_bytes(second)
    assert raw == (ROOT / qualification.QUALIFICATION_PATH).read_bytes()
    assert first["status"] == "offline-qualified"
    assert first["candidate_created"] is first["rehearsal_created"] is False
    assert first["external_calls"] == 0
    assert first["provider_acceptance_observed"] is first["paid_execution_authorized"] is False
    boundary = first["evidence_boundary"]
    for key in (
        "provider_calls",
        "docker_calls",
        "evaluator_calls",
        "visible_check_calls",
        "network_calls",
    ):
        assert boundary[key] == 0
    assert boundary["added_cost_usd"] == "0"
    proof = first["predecessor_preservation"]
    assert proof["consumed_candidate_rebuilt"] is proof["historical_artifacts_modified"] is False
    assert sum(row["reverse_delta_used"] for row in proof["source_proof"]) == 5
    assert all(row["predecessor_bytes_recovered"] for row in proof["source_proof"])


def test_count_and_dynamic_schema_scenarios_are_repeatable():
    assert qualification.schema_scenarios() == qualification.schema_scenarios()
    first = qualification.count_scenarios()
    assert first == qualification.count_scenarios()
    assert first["schema_blocked"]["summary"]["logical_attempts"] == 0
    assert first["outcome_unknown"]["summary"]["logical_attempts"] == 1
    assert first["outcome_unknown"]["summary"]["http_request_total"] is None
    assert first["failed"]["automatic_retry_blocked"] is True


@pytest.mark.parametrize("damage", ["source_hash", "replacement", "inventory"])
def test_exact_predecessor_source_proof_rejects_delta_tamper(monkeypatch, damage):
    original = qualification._document

    def document(root, relative, expected_hash=None):
        value = original(root, relative, expected_hash)
        if relative == qualification.DELTA_PATH.as_posix():
            value = copy.deepcopy(value)
            patch = value["source_deltas"][0]
            if damage == "source_hash":
                patch["successor_file_sha256"] = "sha256:" + "f" * 64
            elif damage == "inventory":
                value["source_deltas"].pop()
            else:
                patch["replacements"][0]["predecessor_text"] += "tamper"
            value["content_hash"] = sha256_json(
                {key: item for key, item in value.items() if key != "content_hash"}
            )
        return value

    monkeypatch.setattr(qualification, "_document", document)
    with pytest.raises((ContractError, RecoveryError)):
        qualification.predecessor_source_proof(ROOT)


def test_frozen_artifact_hash_is_checked_before_its_content(tmp_path):
    fixture = tmp_path / "changed.json"
    fixture.write_text('{"content_hash":"untrusted"}', encoding="utf-8")
    with pytest.raises(ContractError, match="frozen provider-schema input changed"):
        qualification._document(tmp_path, fixture.name, "sha256:" + "0" * 64)


def test_materialization_never_overwrites_a_different_artifact(tmp_path, monkeypatch):
    body = {"schema_version": "synthetic-public-only", "external_calls": 0}
    value = {**body, "content_hash": sha256_json(body)}
    monkeypatch.setattr(qualification, "build_qualification", lambda _root: value)
    monkeypatch.setattr(qualification, "QUALIFICATION_PATH", Path("fixture.json"))
    qualification.materialize_qualification(tmp_path)
    path = tmp_path / "fixture.json"
    raw = path.read_bytes()
    qualification.materialize_qualification(tmp_path)
    assert path.read_bytes() == raw
    path.write_bytes(raw + b" ")
    with pytest.raises(ContractError, match="never overwrite"):
        qualification.materialize_qualification(tmp_path)
    assert path.read_bytes() == raw + b" "


@pytest.mark.parametrize("authorization", [None, {}, object()])
def test_offline_mock_manifest_cannot_authorize_live_count(authorization, monkeypatch):
    monkeypatch.setattr("patchloop.runtime.git_commit", lambda: "f" * 40)
    manifest = _manifest("run_v27_no_count_authority")
    with pytest.raises(HarnessAdmissionError, match="lacks a live row capability"):
        _provider_input_count_boundary(manifest, authorization)


def test_qualification_source_inventory_contains_the_actual_adapter_and_runner_tests():
    value = json.loads((ROOT / qualification.QUALIFICATION_PATH).read_bytes())
    assert {row["path"] for row in value["source_files"]} == set(qualification.SOURCE_FILES)
    assert {
        "patchloop/agent/provider_schema_adapter.py",
        "tests/test_provider_schema_runner.py",
        "tests/test_provider_count_accounting.py",
    } <= set(qualification.SOURCE_FILES)
