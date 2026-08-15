from __future__ import annotations

import json
import os
import socket
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop import environment as environment_module
from patchloop import task_loader
from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import heldout_ac_source_qualification as source_q
from patchloop.evals import runner as generic_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_json
from patchloop.verifier import core as verifier_core

ROOT = Path(__file__).resolve().parents[1]


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"source qualification crossed forbidden {label} boundary")

    return fail


@pytest.fixture
def isolated_output(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    relative = source_q.OUTPUT_PATH.parent / f".pytest-heldout-source-{uuid.uuid4().hex}.json"
    output = ROOT / relative
    assert not output.exists()
    monkeypatch.setattr(source_q, "OUTPUT_PATH", relative)

    process_forbidden = _forbidden("process")
    network_forbidden = _forbidden("network")
    provider_forbidden = _forbidden("provider")
    evaluator_forbidden = _forbidden("evaluator")
    docker_forbidden = _forbidden("Docker")
    agent_forbidden = _forbidden("agent")
    task_forbidden = _forbidden("task package")
    retrieval_forbidden = _forbidden("retrieval")

    monkeypatch.setattr(subprocess, "run", process_forbidden)
    monkeypatch.setattr(subprocess, "Popen", process_forbidden)
    monkeypatch.setattr(os, "system", process_forbidden)
    monkeypatch.setattr(socket, "socket", network_forbidden)
    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(task_loader, "load_task_package", task_forbidden)
    monkeypatch.setattr(
        environment_module,
        "exact_openai_api_key_present",
        _forbidden("credential presence"),
    )
    monkeypatch.setattr(
        environment_module,
        "exact_openai_api_key_environment",
        _forbidden("credential environment"),
    )
    monkeypatch.setattr(agent_model, "OpenAI", provider_forbidden)
    monkeypatch.setattr(
        agent_model.OpenAIResponsesAdapter,
        "execute_request",
        provider_forbidden,
    )
    monkeypatch.setattr(agent_model.OpenAIResponsesAdapter, "next_turn", provider_forbidden)
    monkeypatch.setattr(agent_runner.AgentRunner, "start", agent_forbidden)
    monkeypatch.setattr(agent_runner.AgentRunner, "resume", agent_forbidden)
    monkeypatch.setattr(generic_runner, "preflight_suite", evaluator_forbidden)
    monkeypatch.setattr(generic_runner, "evaluate_suite", evaluator_forbidden)
    monkeypatch.setattr(verifier_core.EvaluationEngine, "evaluate", evaluator_forbidden)
    monkeypatch.setattr(
        verifier_core.EvaluationEngine,
        "evaluate_v2_candidate",
        evaluator_forbidden,
    )
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "image_identity", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_check", docker_forbidden)
    monkeypatch.setattr(retrieval, "retrieve_memory", retrieval_forbidden)
    monkeypatch.setattr(retrieval, "_query_embedding", retrieval_forbidden)

    try:
        yield output
    finally:
        if output.exists() or output.is_symlink():
            output.unlink()


def _build(output: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    summary = source_q.run_heldout_ac_source_qualification(repository=ROOT)
    raw = output.read_bytes()
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return summary, payload, raw


def test_identity_is_contract_only_and_does_not_reuse_the_live_runner() -> None:
    assert source_q.SCHEMA_VERSION == "heldout-ac-contract-source-qualification-v10"
    assert source_q.QUALIFICATION_ID == (
        "core-ac-fixed-bundle-heldout-contract-source-qualification-20260815-r10"
    )
    assert source_q.OUTPUT_PATH.as_posix() == (
        "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r10.json"
    )
    assert source_q.STATUS == ("OFFLINE_CONTRACT_SOURCE_QUALIFIED_TASK_EVALUATOR_BINDING_CLOSED")
    assert source_q.SUITE_PATH.as_posix() == ("experiments/heldout-ac-suite-20260814-v1.yaml")
    assert source_q.PLAN_PATH.as_posix() == ("experiments/heldout-ac-suite-20260814-v1.plan.yaml")
    entrypoints = {item.as_posix() for item in source_q.CONTRACT_IMPORT_ENTRYPOINTS}
    assert "patchloop/evals/heldout_ac_suite.py" in entrypoints
    assert "patchloop/evals/heldout_ac_contracts.py" in entrypoints
    assert "patchloop/evals/heldout_ac_persisted_adapter.py" in entrypoints
    assert "patchloop/evals/heldout_ac_budget_amendment.py" in entrypoints
    assert "patchloop/contracts.py" not in entrypoints
    assert "patchloop/evals/runner.py" not in entrypoints


def test_build_validate_and_replay_are_append_only_canonical_and_no_call(
    isolated_output: Path,
) -> None:
    first, payload, raw = _build(isolated_output)
    first_mtime = isolated_output.stat().st_mtime_ns
    validated = source_q.validate_heldout_ac_source_qualification(repository=ROOT)
    replay = source_q.run_heldout_ac_source_qualification(repository=ROOT)

    assert first == validated == replay
    assert isolated_output.read_bytes() == raw
    assert isolated_output.stat().st_mtime_ns == first_mtime
    assert raw == (
        source_q.HeldoutACContractSourceQualification.model_validate_json(raw)
        .model_dump_json(indent=2)
        .encode("utf-8")
        + b"\n"
    )
    assert first == {
        "status": source_q.STATUS,
        "qualification_id": source_q.QUALIFICATION_ID,
        "source_qualification_hash": payload["content_hash"],
        "predecessor_disposition": (
            "invalidated-by-post-seal-candidate-v3-realized-schedule-and-known-history-replay-successor"
        ),
        "predecessor_file_sha256": source_q.R9_PREDECESSOR_FILE_SHA256,
        "contract_import_traversal": "module-scope-imports-v1",
        "contract_source_hash": payload["contract_source_hash"],
        "suite_content_hash": payload["suite_content_hash"],
        "completion_contract_fixture_source_hash": payload[
            "completion_contract_fixture_source_hash"
        ],
        "analysis_source_hash": payload["analysis_source_hash"],
        "persisted_adapter_source_hash": payload["persisted_adapter_source_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "task_package_bindings": 0,
        "evaluator_v2_task_contract_bindings": 0,
        "authoritative_persisted_producer_adapter_bindings": 0,
        "execution_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "agent_runs_made": 0,
        "added_model_cost_usd": 0.0,
    }


def test_artifact_binds_exact_prereg_suite_plan_and_closed_adapters(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)

    assert payload["predecessor"] == {
        "path": source_q.R9_PREDECESSOR_PATH.as_posix(),
        "schema_version": "heldout-ac-contract-source-qualification-v9",
        "qualification_id": (
            "core-ac-fixed-bundle-heldout-contract-source-qualification-20260815-r9"
        ),
        "original_status": source_q.STATUS,
        "disposition": (
            "invalidated-by-post-seal-candidate-v3-realized-schedule-and-known-history-replay-successor"
        ),
        "invalidation_reason": (
            "post-r9-candidate-v3-realized-schedule-and-known-history-replay-fixes"
        ),
        "source_qualification_hash": source_q.R9_PREDECESSOR_CONTENT_HASH,
        "contract_source_hash": source_q.R9_PREDECESSOR_CONTRACT_SOURCE_HASH,
        "file_bytes": source_q.R9_PREDECESSOR_FILE_BYTES,
        "file_sha256": source_q.R9_PREDECESSOR_FILE_SHA256,
        "current_source_replay_valid": False,
        "task_package_bindings": 0,
        "evaluator_v2_task_contract_bindings": 0,
        "authoritative_persisted_producer_adapter_bindings": 0,
        "execution_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "agent_runs_made": 0,
        "added_model_cost_usd": 0.0,
    }
    assert payload["preregistration"] == {
        "path": "experiments/heldout-ac-preregistration-20260814-v1.yaml",
        "file_bytes": 31_338,
        "file_sha256": ("sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f"),
    }
    assert payload["preregistration_content_hash"] == (
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    )
    assert payload["suite"]["path"] == source_q.SUITE_PATH.as_posix()
    assert payload["suite_content_hash"] == (
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    )
    assert payload["plan"]["path"] == source_q.PLAN_PATH.as_posix()
    assert payload["plan_content_hash"] == (
        "sha256:b2058c48de3f2b4d13df872d7fd19a325c3a76ffb5ef24974310409100cb8885"
    )
    assert payload["budget_amendment"]["path"] == (
        "experiments/heldout-ac-budget-amendment-20260815-v1.yaml"
    )
    assert payload["budget_amendment_content_hash"] == (
        "sha256:9df732d5bf8d5c754ea47084e5dbf9c490f78882bcc9fbc6b0c5d2e2b8bf220d"
    )
    assert len(payload["preregistration_section_hashes"]) == 11
    boundary = payload["binding_boundary"]
    assert boundary["qualification_scope"] == ("metadata-suite-completion-analysis-contract-only")
    assert boundary["task_package_binding_status"] == "closed-not-inspected"
    assert boundary["task_package_binding_count"] == 0
    assert boundary["task_private_marker_binding_count"] == 0
    assert boundary["evaluator_v2_task_contract_binding_count"] == 0
    assert boundary["authoritative_persisted_producer_adapter_binding_count"] == 0
    assert boundary["heldout_task_specs_opened"] is False
    assert boundary["heldout_task_outcomes_opened"] is False
    projection = payload["contract_projection"]
    assert projection["completion_fixture_schema"] == ("heldout-ac-completion-contract-fixture-v1")
    assert projection["completion_contract_projection_schema"] == (
        "heldout-ac-completion-contract-projection-v1"
    )
    assert projection["qualification_fixture_schema"] == (
        "heldout-ac-trace-qualification-contract-fixture-v1"
    )
    assert projection["authenticated_completion_projection_schema"] == (
        "heldout-ac-authenticated-completion-v1"
    )
    assert projection["authenticated_persisted_evidence_schema"] == (
        "heldout-ac-authenticated-persisted-evidence-v5"
    )
    assert projection["completion_campaign_authority_schema"] == (
        "heldout-ac-completion-campaign-authority-v1"
    )
    assert projection["completion_campaign_authority_current_candidate_schema"] == (
        "heldout-ac-execution-candidate-v3"
    )
    assert projection["completion_campaign_authority_realized_schedule_hash_required"] is True
    assert projection["authenticated_qualification_projection_schema"] == (
        "heldout-ac-authenticated-trace-qualification-projection-v2"
    )
    assert projection["qualification_source_schema"] == "trace-qualification-v2"
    assert projection["official_analysis_envelope_schema"] == (
        "heldout-ac-official-analysis-envelope-v1"
    )
    assert projection["completion_surface_status"] == "offline-untrusted-contract-fixture"
    assert projection["analysis_surface_status"] == "unofficial-preview-only"
    assert projection["authoritative_persisted_producer_adapter_present"] is True
    assert projection["trace_qualification_v2_persisted_adapter_bound"] is True
    assert projection["candidate_runtime_tuple_authentication_bound"] is True
    assert projection["campaign_cost_control_authentication_bound"] is True
    assert projection["current_persisted_replay_candidate_authority_required"] is True
    assert projection["known_historical_replay_authority_surface"] == "paid-full-closure-only"
    assert projection["runtime_authentication_capability_required"] is True
    assert projection["serialized_persisted_evidence_analysis_eligible"] is False
    assert projection["authenticated_completion_capability_required"] is True
    assert projection["persisted_replay_reissues_runtime_authority"] is False
    assert projection["full_schedule_cost_bound_in_authenticated_completion"] is True
    assert projection["persisted_evidence_authenticated"] is False
    assert projection["official"] is False
    assert projection["official_analysis_ready"] is False
    assert projection["role_strata_count"] == 2
    assert projection["verdict_distribution_count"] == 4
    assert projection["pre_reservation_inconclusive_requires_zero_reserved_runs"] is True
    assert projection["post_reservation_inconclusive_requires_full_48_run_reservation"] is True
    assert projection["budget_amendment_present"] is True
    assert projection["effective_full_schedule_reserve_nanos"] == 57_600_000_000
    assert projection["effective_hard_cap_nanos"] == 60_000_000_000


def test_r9_predecessor_is_read_only_and_exactly_preserved(isolated_output: Path) -> None:
    predecessor = ROOT / source_q.R9_PREDECESSOR_PATH
    before = predecessor.read_bytes()
    before_mtime = predecessor.stat().st_mtime_ns

    _build(isolated_output)

    assert len(before) == source_q.R9_PREDECESSOR_FILE_BYTES
    assert sha256_bytes(before) == source_q.R9_PREDECESSOR_FILE_SHA256
    assert predecessor.read_bytes() == before
    assert predecessor.stat().st_mtime_ns == before_mtime


def test_r5_bytes_remain_preserved_transitively(isolated_output: Path) -> None:
    predecessor = ROOT / (
        "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r5.json"
    )
    before = predecessor.read_bytes()
    before_mtime = predecessor.stat().st_mtime_ns

    _build(isolated_output)

    assert len(before) == 22_753
    assert sha256_bytes(before) == (
        "sha256:6f3130a752f617e57f2f4f4a0e792156983efc81c3a72d56f925ea696125b1c7"
    )
    assert predecessor.read_bytes() == before
    assert predecessor.stat().st_mtime_ns == before_mtime


def test_source_and_validation_closures_are_canonical_and_task_free(
    isolated_output: Path,
) -> None:
    _summary, payload, raw = _build(isolated_output)
    closure = payload["contract_import_closure"]
    source_files = payload["contract_source_files"]
    validation_files = payload["validation_files"]

    assert payload["contract_import_traversal"] == "module-scope-imports-v1"
    assert closure == sorted(set(closure))
    assert set(payload["contract_import_entrypoints"]).issubset(closure)
    assert [item["path"] for item in source_files] == closure
    assert payload["contract_import_closure_hash"] == sha256_json(closure)
    assert payload["contract_source_hash"] == sha256_json(source_files)
    assert [item["path"] for item in validation_files] == sorted(
        item["path"] for item in validation_files
    )
    assert payload["validation_hash"] == sha256_json(validation_files)
    assert "patchloop/evals/heldout_ac_suite.py" in closure
    assert "patchloop/evals/heldout_ac_contracts.py" in closure
    assert "patchloop/evals/heldout_ac_persisted_adapter.py" in closure
    assert "patchloop/evals/heldout_ac_budget_amendment.py" in closure
    assert "patchloop/evals/qualification.py" not in closure
    assert "patchloop/evals/heldout_ac_live_contract.py" not in closure
    assert "patchloop/evals/heldout_ac_execution.py" not in closure
    assert "patchloop/evals/heldout_ac_task_pricing_materialization.py" not in closure
    assert "patchloop/evals/heldout_ac_preflight_source_qualification.py" not in closure
    assert "patchloop/evals/runner.py" not in closure
    validation_paths = {item["path"] for item in validation_files}
    assert {
        "tests/test_heldout_ac_budget_amendment.py",
        "tests/test_heldout_ac_completion.py",
        "tests/test_heldout_ac_persisted_adapter.py",
        "tests/test_heldout_ac_source_qualification.py",
    }.issubset(validation_paths)
    assert all(not path.startswith("tasks/") for path in closure)
    assert all(not item["path"].startswith("tasks/") for item in validation_files)
    assert b'"task_bindings"' not in raw
    assert b'"private_spec_hash"' not in raw


def test_completion_contract_closure_excludes_runtime_activation_modules() -> None:
    from patchloop.evals.heldout_ac_execution_source_qualification import (
        SOURCE_ENTRYPOINTS,
        _paid_path_import_closure,
    )

    contract_closure = {
        item.as_posix()
        for item in source_q._contract_import_closure(ROOT)  # noqa: SLF001
    }
    paid_full_closure = {
        item.as_posix() for item in _paid_path_import_closure(ROOT, entrypoints=SOURCE_ENTRYPOINTS)
    }
    activation_modules = {
        "patchloop/evals/heldout_ac_execution.py",
        "patchloop/evals/heldout_ac_execution_source_qualification.py",
        "patchloop/evals/heldout_ac_task_pricing_materialization.py",
        "patchloop/evals/heldout_ac_binding_source_qualification.py",
        "patchloop/evals/heldout_ac_preflight.py",
        "patchloop/evals/heldout_ac_preflight_source_qualification.py",
        "patchloop/evals/heldout_ac_dispatcher.py",
    }

    assert "patchloop/evals/heldout_ac_completion.py" in contract_closure
    assert "patchloop/evals/heldout_ac_contracts.py" in contract_closure
    assert activation_modules.isdisjoint(contract_closure)
    assert contract_closure != paid_full_closure
    assert "patchloop/evals/heldout_ac_source_qualification.py" in contract_closure
    assert "patchloop/evals/heldout_ac_source_qualification.py" not in paid_full_closure
    assert {
        "patchloop/evals/heldout_ac_execution.py",
        "patchloop/evals/heldout_ac_task_pricing_materialization.py",
        "patchloop/evals/heldout_ac_preflight_source_qualification.py",
    }.issubset(paid_full_closure)


def test_contract_model_rejects_an_explicit_entrypoint_omitted_from_closure(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    omitted = payload["contract_import_entrypoints"][0]
    payload["contract_import_closure"].remove(omitted)
    payload["contract_source_files"] = [
        item for item in payload["contract_source_files"] if item["path"] != omitted
    ]
    payload["contract_import_closure_hash"] = sha256_json(payload["contract_import_closure"])
    payload["contract_source_hash"] = sha256_json(payload["contract_source_files"])
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError, match="omits an explicit entrypoint"):
        source_q.HeldoutACContractSourceQualification.model_validate_json(canonical_json(payload))


def test_runtime_authority_and_observation_counters_are_exactly_closed(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    authority = payload["authority"]

    assert all(value is False for key, value in authority.items() if key.endswith("authorized"))
    assert all(
        type(value) is int and value == 0
        for key, value in authority.items()
        if key.startswith("authorized_") and key.endswith(("_calls", "_runs"))
    )
    assert all(
        type(value) is int and value == 0
        for key, value in authority.items()
        if key.endswith(("_calls_made", "_runs_made"))
    )
    assert type(authority["authorized_cost_usd"]) is float
    assert authority["authorized_cost_usd"] == 0.0
    assert type(authority["added_model_cost_usd"]) is float
    assert authority["added_model_cost_usd"] == 0.0
    assert payload["next_gate"] == source_q.NEXT_GATE


def test_qualification_never_opens_a_task_path(
    isolated_output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[Path] = []
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def tracked_bytes(path: Path) -> bytes:
        observed.append(path.resolve())
        return original_read_bytes(path)

    def tracked_text(path: Path, *args: Any, **kwargs: Any) -> str:
        observed.append(path.resolve())
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", tracked_bytes)
    monkeypatch.setattr(Path, "read_text", tracked_text)
    _build(isolated_output)

    assert observed
    assert all("tasks" not in path.relative_to(ROOT).parts for path in observed)


def test_equal_but_wrong_scalar_type_is_rejected_after_rehash(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    payload["authority"]["authorized_provider_calls"] = False
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        source_q.HeldoutACContractSourceQualification.model_validate_json(canonical_json(payload))


def test_invalid_existing_artifact_is_never_overwritten(isolated_output: Path) -> None:
    _summary, payload, _raw = _build(isolated_output)
    payload["authority"]["provider_execution_authorized"] = True
    tampered = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    isolated_output.write_bytes(tampered)

    with pytest.raises(
        source_q.HeldoutACSourceQualificationError,
        match="artifact is invalid",
    ):
        source_q.run_heldout_ac_source_qualification(repository=ROOT)
    assert isolated_output.read_bytes() == tampered


def test_noncanonical_bytes_fail_closed(isolated_output: Path) -> None:
    _summary, _payload, raw = _build(isolated_output)
    noncanonical = raw + b"\n"
    isolated_output.write_bytes(noncanonical)

    with pytest.raises(
        source_q.HeldoutACSourceQualificationError,
        match="bytes are not canonical",
    ):
        source_q.validate_heldout_ac_source_qualification(repository=ROOT)
    assert isolated_output.read_bytes() == noncanonical


def test_replay_detects_bound_validation_inventory_drift(
    isolated_output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _build(isolated_output)
    monkeypatch.setattr(source_q, "VALIDATION_PATHS", source_q.VALIDATION_PATHS[:-1])

    with pytest.raises(
        source_q.HeldoutACSourceQualificationError,
        match="has drifted",
    ):
        source_q.validate_heldout_ac_source_qualification(repository=ROOT)
