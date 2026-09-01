from __future__ import annotations

import copy
import json
import socket
from pathlib import Path

import pytest

from patchloop.agent import provider_request_gate as gate
from patchloop.agent.batch_image_authority import rehearse_batch_image_authorization
from patchloop.agent.runner import (
    _consume_row_execution_authorization,
    issue_live_execution_authorization,
    issue_row_execution_authorization,
    row_execution_authorization_receipt,
)
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals import rapid_public_development_v27 as rapid
from patchloop.evals import rapid_v27_package_binding as binding
from patchloop.evals.provider_request_batch_qualification import run_provider_request_batch_mock
from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    from patchloop.sandbox import DockerSandbox
    from patchloop.verifier import EvaluationEngine

    def blocked(*_args, **_kwargs):
        raise AssertionError("R24 tests must not invoke external services")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    for name in ("available", "image_identity", "run_check", "run_probe"):
        monkeypatch.setattr(DockerSandbox, name, blocked)
    monkeypatch.setattr(EvaluationEngine, "evaluate", blocked)
    monkeypatch.setattr(EvaluationEngine, "evaluate_v2_candidate", blocked)


@pytest.fixture(scope="module")
def candidate():
    return rapid.build_rapid_public_development_v27_candidate(repository=ROOT)


def live_batch(candidate, tmp_path):
    rapid._write_or_validate_plan(candidate, tmp_path)
    live = issue_live_execution_authorization(
        candidate["execution_hash"], root=tmp_path / ".patchloop"
    )
    prepared = rapid._prepare_batch(
        candidate, authority_kind="live", live_authorization=live, repository=ROOT
    )
    return live, prepared


def test_candidate_and_all_initial_requests_are_deterministic(candidate, monkeypatch):
    assert rapid.candidate_bytes(candidate) == rapid.candidate_bytes(
        rapid.build_rapid_public_development_v27_candidate(repository=ROOT)
    )
    requests = []
    original = gate.admit_request

    def capture(manifest, authorization, request, adapter, **kwargs):
        requests.append(copy.deepcopy(request))
        return original(manifest, authorization, request, adapter, **kwargs)

    monkeypatch.setattr(gate, "admit_request", capture)
    first = rapid._build_rehearsal_for(candidate, repository=ROOT)
    second = rapid._build_rehearsal_for(candidate, repository=ROOT)
    assert rapid.rehearsal_bytes(first) == rapid.rehearsal_bytes(second)
    assert len(requests) == 12 and requests[:6] == requests[6:]
    assert first["verified_manifest_count"] == 6
    assert first["stopped_before"] == "first-input-token-count-sdk-on-each-of-six-rows"
    assert first["provider_request_contract"] == gate.REQUEST_CONTRACT
    for index, (receipt, request) in enumerate(
        zip(first["all_pre_count_boundaries"], requests[:6], strict=True)
    ):
        manifest = rapid.build_rapid_v27_run_manifest(candidate, index + 1, repository=ROOT)
        assert receipt["request_hash"] == sha256_json(request)
        assert receipt["public_spec_hash"] == manifest.public_spec_hash
        assert receipt["provider_dispatch_blocked"] is True
        assert receipt["provider_acceptance_observed"] is False
        assert receipt["future_execution_request_bytes_observed"] is False
        assert receipt["provider_input_tokens_observed"] is False
        assert receipt["post_count_budget_decisions_exercised"] is False
        context = json.loads(request["input"][1]["content"])
        assert context["public_task"]["issue"]["title"].startswith("Async pytest")
        assert "private_spec" not in context and "reference_patch" not in context
        row = first["all_row_capabilities"][index]
        assert row["consumed"] and row["input_count_rehearsed"]
        assert row["provider_dispatch_rehearsed"] is False
    assert first["provider_calls_made"] == first["docker_calls_made"] == 0


def test_registered_plan_manifest_and_uniform_request_policy(candidate):
    prepared = rapid._prepare_batch(candidate, authority_kind="rehearsal", repository=ROOT)
    assert prepared.verifier_id == rapid.VERIFIER_ID
    assert len(prepared.manifests) == 6
    assert prepared.authorization.provider_request_policy == gate.REQUEST_POLICY
    assert prepared.plan["provider_request_contract"] == gate.REQUEST_CONTRACT
    assert [m.context_policy_version for m in prepared.manifests] == [
        "phase-evidence-v35",
        "phase-evidence-v37",
        "phase-evidence-v37",
        "phase-evidence-v35",
        "phase-evidence-v35",
        "phase-evidence-v37",
    ]
    assert all(rapid._manifest_matches_projection(prepared.plan, m) for m in prepared.manifests)
    bad_plan = copy.deepcopy(prepared.plan)
    bad_plan.pop("provider_request_contract")
    assert not rapid._manifest_matches_projection(bad_plan, prepared.manifests[0])
    assert prepared.plan["promotion_criteria"]["evaluator_reached_rows_min"] == 2
    assert candidate["cost_control"]["full_schedule_reserve_nanos"] == 7_200_000_000
    assert candidate["cost_control"]["hard_cap_nanos"] == 7_500_000_000


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider_request_contract", None),
        ("provider_request_contract", {**gate.REQUEST_CONTRACT, "both_arms": 1}),
        ("variant_contracts", {}),
        ("execution_authorized", True),
    ],
)
def test_rehashed_candidate_cannot_relax_contract(candidate, field, value):
    changed = copy.deepcopy(candidate)
    changed[field] = value
    changed["execution_hash"] = sha256_json(rapid._execution_body(changed))
    changed["content_hash"] = sha256_json({k: v for k, v in changed.items() if k != "content_hash"})
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)


@pytest.mark.parametrize("order", [1, 2])
def test_typed_pre_count_gate_rejects_missing_foreign_and_reused_authority(
    candidate, tmp_path, order
):
    from types import SimpleNamespace

    from patchloop.agent.model import OpenAIResponsesAdapter
    from patchloop.agent.provider_schema_adapter import StrictOpenAIResponsesAdapter
    from patchloop.agent.runner import AgentRunner

    live, prepared = live_batch(candidate, tmp_path)
    manifest = prepared.manifests[order - 1]
    for prior_order in range(1, order):
        issue_row_execution_authorization(
            prepared.authorization,
            prepared.manifests[prior_order - 1],
            active_schedule_order=prior_order,
        )
    row = issue_row_execution_authorization(
        prepared.authorization, manifest, active_schedule_order=order
    )
    adapter_type = StrictOpenAIResponsesAdapter if order == 2 else OpenAIResponsesAdapter
    adapter = adapter_type(manifest.model, client=SimpleNamespace(max_retries=0))
    _, schemas = AgentRunner._runtime_contract(manifest)
    request = {
        "model": manifest.model.model_id,
        "tools": [s for s in schemas if s["name"] == "read_file"],
    }
    assert gate.request_admission_required(manifest, None)
    for invalid in (None, {}, row):
        with pytest.raises(HarnessAdmissionError):
            gate.admit_request(manifest, invalid, request, adapter, stop_before_count=False)
    _consume_row_execution_authorization(
        manifest, row, expected_authority_kind="live", live_authorization=live
    )
    receipt = gate.admit_request(manifest, row, request, adapter, stop_before_count=False)
    assert receipt["request_hash"] == sha256_json(request)
    assert row_execution_authorization_receipt(row)["provider_dispatch_started"] is False
    other = prepared.manifests[order % 6]
    with pytest.raises(HarnessAdmissionError):
        gate.admit_request(other, row, request, adapter, stop_before_count=False)
    with pytest.raises(HarnessAdmissionError):
        _consume_row_execution_authorization(
            manifest, row, expected_authority_kind="live", live_authorization=live
        )
    with pytest.raises(HarnessAdmissionError):
        gate.admit_request(manifest, row, request, adapter, stop_before_count=True)
    malformed = copy.deepcopy(request)
    malformed["tools"][0]["parameters"]["required"] = []
    with pytest.raises(ContractError):
        gate.admit_request(manifest, row, malformed, adapter, stop_before_count=False)
    adapter.client.max_retries = 1
    with pytest.raises(HarnessAdmissionError):
        gate.admit_request(manifest, row, request, adapter, stop_before_count=False)


def test_rehearsal_one_use_does_not_grant_live_authority(candidate):
    import yaml

    from patchloop.contracts import PublicTask

    prepared = rapid._prepare_batch(candidate, authority_kind="rehearsal", repository=ROOT)
    image, _ = rehearse_batch_image_authorization(
        prepared.authorization,
        prepared.manifests,
        image=candidate["task_bindings"][0]["evaluator_image"],
    )
    manifest = prepared.manifests[0]
    row = issue_row_execution_authorization(
        prepared.authorization, manifest, active_schedule_order=1
    )
    public = PublicTask.model_validate(
        yaml.safe_load((ROOT / rapid.TASK_PATH).read_text(encoding="utf-8"))
    )
    gate.rehearse_initial_request(manifest, row, public, repository=ROOT, image_authorization=image)
    with pytest.raises(HarnessAdmissionError):
        gate.rehearse_initial_request(
            manifest, row, public, repository=ROOT, image_authorization=image
        )
    assert not row_execution_authorization_receipt(row)["provider_dispatch_started"]


def test_historical_sources_and_artifacts_recover_without_rebuilding():
    proof = binding.validate_v27_integration_binding(ROOT)
    assert len(proof["reviewed_source_proof"]) == 39
    assert len(proof["immutable_inputs"]) == 9
    assert all(item["reviewed_bytes_recovered"] for item in proof["reviewed_source_proof"])
    assert {
        item["path"] for item in proof["reviewed_source_proof"] if item["marked_integration"]
    } == binding.INTEGRATED_FILES
    assert proof["historical_builders_invoked"] is False
    assert proof["historical_artifacts_modified"] is False


@pytest.mark.parametrize(
    "target", ["patchloop/agent/runner.py", binding.REVIEW_PATH, binding.QUALIFICATION_PATH]
)
def test_predecessor_drift_fails_closed(monkeypatch, target):
    original = binding._raw

    def changed(root, path):
        raw = original(root, path)
        return raw + b"\n# outside integration\n" if path == target else raw

    monkeypatch.setattr(binding, "_raw", changed)
    with pytest.raises(RecoveryError):
        binding.validate_v27_integration_binding(ROOT)


def test_six_real_row_starts_one_mock_inspect_and_six_request_gates(candidate, tmp_path):
    first = run_provider_request_batch_mock(candidate, repository=ROOT, state_root=tmp_path / "a")
    second = run_provider_request_batch_mock(candidate, repository=ROOT, state_root=tmp_path / "b")
    assert first == second
    assert first["mocked_docker_image_inspect_commands"] == 1
    assert (
        first["real_agent_start_count"]
        == first["pre_count_gate_count"]
        == first["provider_gate_count"]
        == 6
    )
    assert first["synthetic_terminal_rows"] == 6
    assert first["actual_docker_calls"] == first["provider_calls"] == first["evaluator_calls"] == 0
    assert first["agent_policies_or_task_behavior_exercised"] is False


def test_execute_requires_fresh_exact_authority_before_rehearsal_or_environment(
    candidate, monkeypatch
):
    monkeypatch.setattr(rapid, "load_rapid_public_development_v27_candidate", lambda *a: candidate)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v27_rehearsal",
        lambda *a, **k: pytest.fail("authority not checked first"),
    )
    with pytest.raises(ContractError, match="exact hash"):
        rapid.run_rapid_public_development_v27(
            repository=ROOT, approve_live_cost=False, approved_execution_hash=None
        )
    with pytest.raises(ContractError, match="exact hash"):
        rapid.run_rapid_public_development_v27(
            repository=ROOT, approve_live_cost=True, approved_execution_hash="sha256:" + "0" * 64
        )


def test_stored_candidate_and_rehearsal_if_frozen():
    if not (ROOT / rapid.CANDIDATE_PATH).exists():
        pytest.skip("candidate intentionally not materialized before source validation")
    candidate = rapid.load_rapid_public_development_v27_candidate(ROOT)
    rehearsal = rapid.load_rapid_public_development_v27_rehearsal(candidate, repository=ROOT)
    assert sha256_bytes((ROOT / rapid.CANDIDATE_PATH).read_bytes()) == sha256_bytes(
        rapid.candidate_bytes(candidate)
    )
    assert rehearsal["provider_calls_made"] == 0


@pytest.mark.parametrize("tool", ["get_diff", "finish_task"])
def test_closed_empty_required_compatibility_preserves_original_wire_bytes(tool):
    request = {
        "tools": [
            {
                "name": tool,
                "type": "function",
                "strict": True,
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        ]
    }
    before = copy.deepcopy(request)
    receipt = gate.validate_request_schemas(request)
    assert request == before
    assert receipt["equivalent_empty_required_paths"] == ["tools[0].parameters"]
    assert receipt["tool_schema_hash"] == sha256_json(request["tools"])
    assert receipt["provider_request_bytes_modified"] is False
    assert receipt["provider_acceptance_observed"] is False


@pytest.mark.parametrize(
    "parameters",
    [
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": False,
        },
        {"type": "object", "properties": {}, "required": None, "additionalProperties": False},
        {"type": "object", "properties": {}, "additionalProperties": True},
        {"type": "object", "properties": {}, "required": ["path"], "additionalProperties": False},
    ],
)
def test_empty_required_compatibility_cannot_repair_nonempty_or_malformed_schema(parameters):
    request = {
        "tools": [
            {"name": "read_file", "type": "function", "strict": True, "parameters": parameters}
        ]
    }
    before = copy.deepcopy(request)
    with pytest.raises(ContractError):
        gate.validate_request_schemas(request)
    assert request == before
