from __future__ import annotations

import copy
import json
import socket
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from patchloop.agent import provider_schema_activation_review as review
from patchloop.agent.provider_count_accounting import project_input_token_count_attempts
from patchloop.agent.provider_schema_admission import (
    ProviderToolSchemaError,
    validate_provider_tool_schemas,
)
from patchloop.agent.runner import (
    _ROW_EXECUTION_AUTHORIZATION_GUARD,
    AgentRunner,
    RowExecutionAuthorization,
    _provider_input_count_boundary,
    _RowExecutionAuthorizationState,
    row_execution_authorization_receipt,
)
from patchloop.contracts import EventType, ModelConfig, RunManifest
from patchloop.errors import ContractError, HarnessAdmissionError
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox.runner import LocalSandbox, SandboxResult
from patchloop.util import sha256_json
from patchloop.verifier import EvaluationEngine
from tests.test_provider_schema_admission import _request
from tests.test_provider_schema_runner import (
    _FakeProvider,
    _manifest,
    _mock_boundaries,
    _provider_adapter,
    _requests,
    _V27Adapter,
)
from tests.test_workflow_self_directed_exploration_runner import TASK_PATH

ROOT = Path(__file__).resolve().parents[1]


def _forbidden(*_args, **_kwargs):
    raise AssertionError("activation review permits no real provider/check/container/evaluator")


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(DockerSandbox, "available", staticmethod(lambda: False))
    for name in ("image_identity", "run_check", "run_probe"):
        monkeypatch.setattr(DockerSandbox, name, _forbidden)
    monkeypatch.setattr(LocalSandbox, "run_check", _forbidden)
    monkeypatch.setattr(EvaluationEngine, "__init__", _forbidden)


@pytest.fixture
def review_no_io(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _forbidden)
    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    monkeypatch.setattr(AgentRunner, "start", _forbidden)
    monkeypatch.setattr(AgentRunner, "resume", _forbidden)


def test_review_is_repeatable_and_does_not_claim_live_readiness(review_no_io):
    first = review.build_activation_review(ROOT)
    raw = review.review_bytes(first)
    assert raw == review.review_bytes(review.build_activation_review(ROOT))
    assert first["decision"] == {
        "adoption_status": "eligible-not-adopted",
        "eligible_for_separate_candidate_integration_decision": True,
        "candidate_design_authorized_by_review": False,
        "live_execution_ready": False,
        "provider_acceptance_observed": False,
    }
    assert all(first["activation_criteria"].values())
    assert first["candidate_created"] is first["rehearsal_created"] is False
    assert first["external_calls"] == 0
    assert first["runtime_source_modified"] is first["paid_execution_authorized"] is False
    assert first["qualification"]["file_sha256"] == review.QUALIFICATION_FILE_HASH
    assert first["qualification"]["content_hash"] == review.QUALIFICATION_CONTENT_HASH
    assert all(
        row["predecessor_bytes_recovered"]
        for row in first["predecessor_preservation"]["source_proof"]
    )
    assert first["official_documentation"][0]["fetched_by_builder"] is False
    assert first["future_comparison_constraints"]["official"] is False
    assert first["next_gate"] == "separate-v27-candidate-integration-adoption-decision"


def test_stored_review_matches_the_current_source_bound_build(review_no_io):
    assert (
        review.review_bytes(review.build_activation_review(ROOT))
        == (ROOT / review.REVIEW_PATH).read_bytes()
    )


def test_review_records_capability_only_rehearsal_as_a_gap(review_no_io):
    value = review.source_observations(ROOT)
    assert value["kind"] == "static-call-site-observation-not-control-flow-proof"
    assert value["legacy_rehearsal"]["checks_row_image_provider_capability"] is True
    assert value["legacy_rehearsal"]["covers_request_construction_and_count_gate"] is False
    assert value["legacy_rehearsal"]["executed_by_review_builder"] is False
    assert value["live_integration"]["all_occurrences_require_mock_provider"] is True
    count = value["gates"]["runner_count"]["ordered_call_sites"]
    assert [row["call"] for row in count] == [
        "adapter.admit_request_v3",
        "_provider_input_count_boundary",
        "counted_request_with_receipts",
    ]
    assert [row["line"] for row in count] == sorted(row["line"] for row in count)


@pytest.mark.parametrize(
    "damage,criterion",
    [
        ("runtime", "exact_qualified_runtime"),
        ("schema", "strict_static_and_projected_plan_schemas"),
        ("read", "ambiguous_reads_rejected"),
        ("count", "count_outcomes_not_conflated"),
        ("retry", "failed_and_uncertain_count_retry_closed"),
        ("gate", "five_source_gate_sequences_reviewed"),
        ("rehearsal", "remaining_rehearsal_gap_explicit"),
        ("live", "live_admission_stays_closed"),
        ("external", "qualification_zero_call_noncreating"),
        ("private", "qualification_zero_call_noncreating"),
    ],
)
def test_review_criteria_reject_missing_or_overstated_evidence(review_no_io, damage, criterion):
    qualification = json.loads((ROOT / review.QUALIFICATION_PATH).read_bytes())
    observations = review.source_observations(ROOT)
    if damage == "runtime":
        qualification["runtime_identity"]["tool_schema_version"] = "v27"
    elif damage == "schema":
        qualification["schema_scenarios"]["static_surface"]["provider_acceptance_observed"] = True
    elif damage == "read":
        qualification["schema_scenarios"]["ambiguous_or_missing_modes_rejected"] = 0
    elif damage == "count":
        qualification["synthetic_count_scenarios"]["failed"]["summary"]["logical_attempts"] = 0
    elif damage == "retry":
        qualification["synthetic_count_scenarios"]["outcome_unknown"]["automatic_retry_blocked"] = (
            False
        )
    elif damage == "gate":
        observations["gates"].pop("runner_count")
    elif damage == "rehearsal":
        observations["legacy_rehearsal"]["covers_request_construction_and_count_gate"] = True
    elif damage == "live":
        observations["live_integration"]["all_occurrences_require_mock_provider"] = False
    elif damage == "external":
        qualification["evidence_boundary"]["provider_calls"] = 1
    else:
        qualification["evidence_boundary"]["private_task_spec_read"] = True
    criteria = review.activation_criteria(qualification, observations)
    assert criteria[criterion] is False
    assert not all(criteria.values())


def test_frozen_qualification_tamper_is_rejected_before_rebuild(
    tmp_path, monkeypatch, review_no_io
):
    path = tmp_path / review.QUALIFICATION_PATH
    path.parent.mkdir()
    path.write_bytes(b"synthetic tampered qualification")
    monkeypatch.setattr(review, "build_qualification", _forbidden)
    with pytest.raises(ContractError, match="frozen V27 qualification bytes differ"):
        review.build_activation_review(tmp_path)


def test_changed_qualified_source_cannot_be_silently_reviewed(monkeypatch, review_no_io):
    value = json.loads((ROOT / review.QUALIFICATION_PATH).read_bytes())
    value["source_files"][0]["file_sha256"] = "sha256:" + "f" * 64
    value["content_hash"] = sha256_json({k: v for k, v in value.items() if k != "content_hash"})
    monkeypatch.setattr(review, "build_qualification", lambda _root: value)
    with pytest.raises(ContractError, match="source binding differs"):
        review.build_activation_review(ROOT)


def test_source_observation_fails_closed_if_gate_call_is_missing(monkeypatch, review_no_io):
    original = review._calls
    monkeypatch.setattr(
        review,
        "_calls",
        lambda node: [r for r in original(node) if r["call"] != "_provider_input_count_boundary"],
    )
    with pytest.raises(ContractError, match="call-site sequence differs: runner_count"):
        review.source_observations(ROOT)


def test_review_artifact_is_append_only_and_hash_bound(tmp_path, monkeypatch, review_no_io):
    body = {"schema_version": "synthetic-review", "external_calls": 0}
    value = {**body, "content_hash": sha256_json(body)}
    monkeypatch.setattr(review, "build_activation_review", lambda _root: value)
    monkeypatch.setattr(review, "REVIEW_PATH", Path("synthetic-review.json"))
    review.materialize_activation_review(tmp_path)
    path = tmp_path / review.REVIEW_PATH
    before = path.read_bytes()
    review.materialize_activation_review(tmp_path)
    assert path.read_bytes() == before
    value["external_calls"] = 1
    with pytest.raises(ContractError, match="content hash differs"):
        review.review_bytes(value)
    value["content_hash"] = sha256_json({k: v for k, v in value.items() if k != "content_hash"})
    with pytest.raises(ContractError, match="never overwrite"):
        review.materialize_activation_review(tmp_path)
    assert path.read_bytes() == before


def test_review_materialization_requires_identical_rebuilds(tmp_path, monkeypatch, review_no_io):
    calls = []

    def changing(_root):
        body = {"schema_version": "synthetic-review", "sequence": len(calls)}
        calls.append(body)
        return {**body, "content_hash": sha256_json(body)}

    monkeypatch.setattr(review, "build_activation_review", changing)
    monkeypatch.setattr(review, "REVIEW_PATH", Path("synthetic-review.json"))
    with pytest.raises(ContractError, match="not byte-identical"):
        review.materialize_activation_review(tmp_path)
    assert not (tmp_path / review.REVIEW_PATH).exists()


def test_mock_v27_tuple_does_not_admit_an_openai_manifest(monkeypatch):
    monkeypatch.setattr("patchloop.runtime.git_commit", lambda: "f" * 40)
    manifest = _manifest("run_v27_review_closed")
    body = manifest.model_dump(mode="json")
    body["model"] = ModelConfig(
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        transport_max_retries=0,
        max_output_tokens=25_000,
    ).model_dump(mode="json")
    with pytest.raises(ValidationError, match="exact public-calibration mock"):
        RunManifest.model_validate(body)


def _synthetic_count_capability():
    """Pure gate fixture, not an admissible RunManifest or an issued live capability.

    No plan, approval, runner, journal or batch issuer is involved. The fixture
    probes exact receipt binding separately from the guarded mock runner tests.
    """
    body = {"run_id": "run_synthetic_gate", "fixture_only": True}
    manifest = SimpleNamespace(
        run_id=body["run_id"],
        experiment=SimpleNamespace(
            execution_hash="sha256:" + "a" * 64,
            schedule_order=1,
            schedule_row_id="synthetic_row",
        ),
        model_dump=lambda **_kwargs: copy.deepcopy(body),
    )
    authorization = RowExecutionAuthorization(
        authority_kind="live",
        execution_hash=manifest.experiment.execution_hash,
        plan_hash="sha256:" + "b" * 64,
        schedule_order=1,
        schedule_row_id="synthetic_row",
        run_id=manifest.run_id,
        manifest_hash=sha256_json(body),
        _state=_RowExecutionAuthorizationState(consumed=True),
        _guard=_ROW_EXECUTION_AUTHORIZATION_GUARD,
    )
    return manifest, authorization


def test_count_gate_does_not_mislabel_generation_as_started():
    manifest, authorization = _synthetic_count_capability()
    before = row_execution_authorization_receipt(authorization)
    _provider_input_count_boundary(manifest, authorization)
    assert row_execution_authorization_receipt(authorization) == before
    assert before["provider_dispatch_started"] is False


@pytest.mark.parametrize(
    "damage",
    ["guard", "rehearsal", "execution", "order", "row", "run", "hash", "unconsumed", "visited"],
)
def test_count_gate_rejects_wrong_or_unadmitted_synthetic_receipt(damage):
    manifest, authorization = _synthetic_count_capability()
    fields = {
        "guard": {"_guard": object()},
        "rehearsal": {"authority_kind": "rehearsal"},
        "execution": {"execution_hash": "sha256:" + "c" * 64},
        "order": {"schedule_order": 2},
        "row": {"schedule_row_id": "different_row"},
        "run": {"run_id": "run_other"},
        "hash": {"manifest_hash": "sha256:" + "d" * 64},
    }
    if damage == "unconsumed":
        authorization._state.consumed = False
    elif damage == "visited":
        authorization._state.provider_dispatch_rehearsed = True
    else:
        authorization = replace(authorization, **fields[damage])
    with pytest.raises(HarnessAdmissionError):
        _provider_input_count_boundary(manifest, authorization)
    assert authorization._state.provider_dispatch_started is False


@pytest.mark.parametrize(
    "entry",
    [
        "count_input_tokens",
        "count_input_tokens_v2",
        "count_input_tokens_v3",
        "execute_request",
        "execute_request_v3",
    ],
)
def test_every_adapter_alias_blocks_invalid_schema_before_fake_sdk(entry):
    client = _FakeProvider()
    adapter = _provider_adapter(client)
    request = adapter.request_payload("synthetic public context", _request()["tools"])
    next(t for t in request["tools"] if t["name"] == "read_file")["parameters"]["required"] = []
    with pytest.raises(ProviderToolSchemaError):
        kwargs = {"requested_input_tokens": 10} if entry.startswith("execute") else {}
        getattr(adapter, entry)(request, **kwargs)
    assert client.count_calls == client.create_calls == 0


@pytest.mark.parametrize("client_retries", [None, False, 1])
def test_adapter_rejects_retry_configuration_before_fake_sdk(client_retries):
    client = _FakeProvider()
    adapter = _provider_adapter(client)
    client.max_retries = client_retries
    request = adapter.request_payload("synthetic public context", _request()["tools"])
    with pytest.raises(HarnessAdmissionError, match="zero SDK retries"):
        adapter.count_input_tokens_v3(request)
    assert client.count_calls == client.create_calls == 0


@pytest.mark.parametrize("review_correction", [False, True])
def test_fake_sdk_runner_preserves_final_schema_across_correction_and_review(
    tmp_path,
    monkeypatch,
    review_correction,
):
    """Public smoke fixture only; no AnyIO run, real visible check or private grading."""

    class AuditedProvider(_FakeProvider):
        def __init__(self):
            super().__init__()
            self.last_count_schema = None
            self.generated_surfaces = []

        def count(self, **kwargs):
            self.last_count_schema = validate_provider_tool_schemas(kwargs)["tool_schema_hash"]
            return super().count(**kwargs)

        def create(self, **kwargs):
            receipt = validate_provider_tool_schemas(kwargs)
            assert receipt["tool_schema_hash"] == self.last_count_schema
            self.generated_surfaces.append(receipt["tool_names"])
            return super().create(**kwargs)

    manifest = _manifest("run_v27_review_dynamics")
    runner = AgentRunner(tmp_path / "g")
    _mock_boundaries(runner, monkeypatch)
    checks = []

    def synthetic_check(_self, _workspace, registered):
        checks.append(registered.id)
        failed = not review_correction and len(checks) == 1
        return SandboxResult(
            command=registered.command,
            exit_code=int(failed),
            stdout="synthetic falsy override mismatch" if failed else "synthetic pass",
            stderr="",
            duration_ms=0,
            timed_out=False,
            truncated=False,
            original_output_bytes=32,
        )

    monkeypatch.setattr(LocalSandbox, "run_check", synthetic_check)
    client = AuditedProvider()
    client.policy = _V27Adapter(
        prefix="review-sdk",
        fail_first_mutation=not review_correction,
        review_correction=review_correction,
    )
    adapter = _provider_adapter(client)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result.get("mock_submission_boundary_reached") is True, result.get("terminal_error")
    assert any("revise_work_plan" in surface for surface in client.generated_surfaces)
    assert all(r.provider_tool_schema_admission for r in _requests(runner, manifest.run_id))
    events = runner.state.list_events(manifest.run_id)
    assert sum(e.type == EventType.PLAN_RECORDED for e in events) == 2
    assert sum(e.type == EventType.PATCH_APPLIED for e in events) == 2
    assert any(e.type == EventType.SUBMISSION_ACCEPTED for e in events)
    summary = project_input_token_count_attempts(manifest.run_id, events)
    usage = runner._usage(manifest.run_id)
    assert summary["logical_attempts"] == summary["completed"] == client.count_calls
    assert summary["failed"] == summary["outcome_unknown"] == 0
    assert usage.input_token_count_calls == client.count_calls
    assert usage.model_calls == client.create_calls
    assert summary["http_request_total"] is None
