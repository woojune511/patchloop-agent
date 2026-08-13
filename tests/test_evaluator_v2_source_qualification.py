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
import yaml
from pydantic import ValidationError

from patchloop import runtime as runtime_module
from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.contracts import (
    AC_FIXED_BUNDLE_CONTRACT_HARDENED_EXPERIMENT_ID,
    AC_FIXED_BUNDLE_RUNTIME_EVIDENCE_CORRECTED_EXPERIMENT_ID,
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
)
from patchloop.evals import evaluator_v2_source_qualification as source_q
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier import core as verifier_core

REPOSITORY = Path(__file__).resolve().parents[1]


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"source qualification crossed forbidden {label} boundary")

    return fail


@pytest.fixture
def isolated_output(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    relative = source_q.OUTPUT_PATH.parent / f".pytest-evaluator-v2-{uuid.uuid4().hex}.json"
    output = REPOSITORY / relative
    assert not output.exists()
    monkeypatch.setattr(source_q, "OUTPUT_PATH", relative)

    process_forbidden = _forbidden("process")
    network_forbidden = _forbidden("network")
    provider_forbidden = _forbidden("provider")
    evaluator_forbidden = _forbidden("evaluator")
    docker_forbidden = _forbidden("Docker")
    agent_forbidden = _forbidden("agent")
    retrieval_forbidden = _forbidden("retrieval")

    monkeypatch.setattr(subprocess, "run", process_forbidden)
    monkeypatch.setattr(subprocess, "Popen", process_forbidden)
    monkeypatch.setattr(os, "system", process_forbidden)
    monkeypatch.setattr(socket, "socket", network_forbidden)
    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(agent_model, "OpenAI", provider_forbidden)
    monkeypatch.setattr(
        agent_model.OpenAIResponsesAdapter,
        "execute_request",
        provider_forbidden,
    )
    monkeypatch.setattr(
        agent_model.OpenAIResponsesAdapter,
        "next_turn",
        provider_forbidden,
    )
    monkeypatch.setattr(agent_runner.AgentRunner, "start", agent_forbidden)
    monkeypatch.setattr(agent_runner.AgentRunner, "resume", agent_forbidden)
    monkeypatch.setattr(eval_runner, "preflight_suite", evaluator_forbidden)
    monkeypatch.setattr(eval_runner, "evaluate_suite", evaluator_forbidden)
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
    summary = source_q.run_evaluator_v2_ac_source_qualification(repository=REPOSITORY)
    raw = output.read_bytes()
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return summary, payload, raw


def test_r10_source_surfaces_do_not_replace_r9_artifact() -> None:
    r9 = REPOSITORY / (
        "reports/live-pilot/artifacts/"
        "evaluator-v2-ac-successor-offline-source-qualification-r9.json"
    )

    assert source_q.SCHEMA_VERSION == "evaluator-v2-ac-source-qualification-v10"
    assert source_q.QUALIFICATION_ID.endswith("-r10")
    assert source_q.PLAN_PATH.as_posix() == "experiments/ac-structured-pilot-v11.plan.yaml"
    assert source_q.OUTPUT_PATH.name.endswith("qualification-r10.json")
    assert r9.is_file()
    assert len(r9.read_bytes()) == 16_152
    assert sha256_bytes(r9.read_bytes()) == (
        "sha256:6d59aaaeba99743fe760a9a4690d56976698f482172fd21285955437faafeb22"
    )
    assert r9 != REPOSITORY / source_q.OUTPUT_PATH


def test_r8_suite_changes_only_the_contract_hardened_identity() -> None:
    successor = eval_runner.load_suite(source_q.BASE_SUITE_PATH).model_dump(mode="json")
    predecessor = eval_runner.load_suite(source_q.FAST_PREDECESSOR_SUITE_PATH).model_dump(
        mode="json"
    )

    assert successor["experiment_id"] == AC_FIXED_BUNDLE_CONTRACT_HARDENED_EXPERIMENT_ID
    assert predecessor["experiment_id"] == AC_FIXED_BUNDLE_RUNTIME_EVIDENCE_CORRECTED_EXPERIMENT_ID
    for field in ("experiment_id",):
        successor.pop(field)
        predecessor.pop(field)
    assert successor == predecessor


@pytest.mark.parametrize(
    ("field_path", "wrong_value"),
    [
        (("runtime", "max_model_calls"), 180.0),
        (("runtime", "max_model_calls"), "180"),
        (("authority", "provider_or_evaluator_execution_authorized"), 0),
        (("next_gate", "requires_separate_paid_execution_approval"), 1),
    ],
)
def test_plan_rejects_equal_but_wrong_typed_scalars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field_path: tuple[str, str],
    wrong_value: object,
) -> None:
    plan = yaml.safe_load((REPOSITORY / source_q.PLAN_PATH).read_text(encoding="utf-8"))
    plan[field_path[0]][field_path[1]] = wrong_value
    selected = tmp_path / "wrong-typed-plan.yaml"
    selected.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
    relative = selected.relative_to(tmp_path)
    monkeypatch.setattr(source_q, "PLAN_PATH", relative)

    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="successor (runtime tuple|authority|next gate) differs",
    ):
        source_q._load_plan(tmp_path)


def test_plan_loader_rejects_duplicate_mapping_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = (REPOSITORY / source_q.PLAN_PATH).read_text(encoding="utf-8")
    duplicate += "\nstatus: offline-evaluator-v2-source-qualification\n"
    selected = tmp_path / "duplicate-key-plan.yaml"
    selected.write_text(duplicate, encoding="utf-8")
    monkeypatch.setattr(source_q, "PLAN_PATH", selected.relative_to(tmp_path))

    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="successor plan is unreadable",
    ):
        source_q._load_plan(tmp_path)


def test_build_validate_and_replay_are_append_only_and_offline(
    isolated_output: Path,
) -> None:
    first, payload, raw = _build(isolated_output)
    first_mtime = isolated_output.stat().st_mtime_ns
    validated = source_q.validate_evaluator_v2_ac_source_qualification(repository=REPOSITORY)
    replay = source_q.run_evaluator_v2_ac_source_qualification(repository=REPOSITORY)

    assert first == validated == replay
    assert isolated_output.read_bytes() == raw
    assert isolated_output.stat().st_mtime_ns == first_mtime
    assert first == {
        "status": source_q.STATUS,
        "qualification_id": source_q.QUALIFICATION_ID,
        "source_qualification_hash": payload["content_hash"],
        "evaluator_source_hash": payload["evaluator_source_hash"],
        "successor_suite_hash": payload["successor_suite"]["content_hash"],
        "base_suite_hash": payload["base_suite_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "agent_runs_made": 0,
    }
    assert payload["authority"] == {
        **source_q._EXPECTED_AUTHORITY,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "agent_runs_made": 0,
        "retrieval_calls_made": 0,
        "added_model_cost_usd": 0,
    }


def test_successor_suite_is_new_and_preserves_exact_ac_treatment(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    successor = payload["successor_suite"]
    assert successor["suite_id"] == source_q.QUALIFICATION_ID
    assert successor["content_hash"] != payload["base_suite_hash"]
    assert successor["base_suite_hash"] == payload["base_suite_hash"]
    assert successor["evaluator_source_hash"] == payload["evaluator_source_hash"]
    assert [
        (row["order"], row["task_id"], row["condition"], row["repetition"])
        for row in successor["schedule"]
    ] == [
        (1, "moto-query-scanned-count", "no_memory", 1),
        (2, "moto-query-scanned-count", "structured", 1),
        (3, "babel-strict-grouped-decimal-trailing-zeroes", "structured", 1),
        (4, "babel-strict-grouped-decimal-trailing-zeroes", "no_memory", 1),
    ]
    assert successor["runtime_tuple_hash"] == source_q._qualified_runtime_tuple_hash()
    assert successor["treatment_hash"] == sha256_json(source_q._EXPECTED_TREATMENT)
    assert payload["fixed_bundle_sha256"] == source_q.FIXED_BUNDLE_SHA256
    assert payload["base_suite"]["path"] == source_q.BASE_SUITE_PATH.as_posix()
    assert (
        eval_runner.load_suite(source_q.BASE_SUITE_PATH).experiment_id
        == AC_FIXED_BUNDLE_CONTRACT_HARDENED_EXPERIMENT_ID
    )
    assert (
        eval_runner.load_suite(source_q.BASE_SUITE_PATH).pricing_verified_at.isoformat()
        == "2026-08-13T12:05:26+00:00"
    )


def test_legacy_null_pricing_r2_is_not_the_qualified_executable_suite(
    isolated_output: Path,
) -> None:
    _build(isolated_output)
    legacy = eval_runner.load_suite(
        "experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml"
    )

    observed = eval_runner._validated_ac_evaluator_v2_source_qualification(legacy)

    assert observed is not None
    assert observed["base_suite_matches"] is False


def test_source_and_validation_inventories_are_exact_current_bytes(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    for key, expected_paths in (
        ("evaluator_source_files", source_q.SOURCE_PATHS),
        ("validation_files", source_q.VALIDATION_PATHS),
    ):
        bindings = payload[key]
        assert [item["path"] for item in bindings] == [item.as_posix() for item in expected_paths]
        for item in bindings:
            content = (REPOSITORY / item["path"]).read_bytes()
            assert item["file_bytes"] == len(content)
            assert item["file_sha256"] == sha256_bytes(content)


def test_paid_path_import_closure_is_fully_source_bound() -> None:
    closure = source_q._paid_path_import_closure(REPOSITORY)
    source_paths = set(source_q.SOURCE_PATHS)

    assert set(closure).issubset(source_paths)
    assert set(closure) >= {
        Path("patchloop/__init__.py"),
        Path("patchloop/agent/__init__.py"),
        Path("patchloop/agent/model.py"),
        Path("patchloop/dataset.py"),
        Path("patchloop/evals/failures.py"),
        Path("patchloop/sandbox/__init__.py"),
        Path("patchloop/state/__init__.py"),
        Path("patchloop/verifier/__init__.py"),
        Path("patchloop/verifier/policy.py"),
    }


def test_paid_path_import_closure_is_transitive_and_excludes_external_modules(
    tmp_path: Path,
) -> None:
    files = {
        "patchloop/__init__.py": "",
        "patchloop/evals/__init__.py": "",
        "patchloop/evals/runner.py": "import os\nfrom patchloop.agent import runner\n",
        "patchloop/agent/__init__.py": "",
        "patchloop/agent/runner.py": "from patchloop.verifier import policy\n",
        "patchloop/verifier/__init__.py": "",
        "patchloop/verifier/policy.py": "import pydantic\n",
    }
    for relative, content in files.items():
        selected = tmp_path / relative
        selected.parent.mkdir(parents=True, exist_ok=True)
        selected.write_text(content, encoding="utf-8")

    closure = source_q._paid_path_import_closure(tmp_path)

    assert [item.as_posix() for item in closure] == sorted(files)


def test_source_qualification_fails_when_paid_path_import_is_unbound(
    isolated_output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        source_q,
        "SOURCE_PATHS",
        tuple(path for path in source_q.SOURCE_PATHS if path != Path("patchloop/agent/model.py")),
    )

    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="omits paid-path imports: patchloop/agent/model.py",
    ):
        _build(isolated_output)


def test_private_ids_and_reference_hashes_do_not_persist(
    isolated_output: Path,
) -> None:
    _summary, _payload, raw = _build(isolated_output)
    for task_path in source_q.TASK_PATHS:
        package = load_task_package(REPOSITORY / task_path)
        private_markers = source_q.evaluator_v2_task_private_markers(package)
        assert all(marker not in raw for marker in private_markers)


def test_authority_factory_requires_exact_task_and_run_secret_boundary(
    isolated_output: Path,
) -> None:
    summary, _payload, _raw = _build(isolated_output)
    task = REPOSITORY / source_q.TASK_PATHS[0]
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="run-bound secret marker",
    ):
        source_q.load_evaluator_v2_ac_qualification_authority(
            task,
            repository=REPOSITORY,
        )

    secret = b"sk-run-bound-test-marker-not-a-real-key"
    live_shape = source_q.load_evaluator_v2_ac_qualification_authority(
        task,
        runtime_secret_markers=(secret,),
        repository=REPOSITORY,
    )
    assert live_shape.suite_hash == summary["successor_suite_hash"]
    assert live_shape.source_qualification_hash == summary["source_qualification_hash"]
    assert live_shape.runtime_tuple_hash == source_q._qualified_runtime_tuple_hash()
    assert live_shape.runtime.evaluator_source_hash == summary["evaluator_source_hash"]
    assert live_shape.runtime.safety_contract.task_id == "moto-query-scanned-count"
    assert secret in live_shape.runtime.private_markers
    assert secret not in isolated_output.read_bytes()


def test_ac_runner_binds_qualified_v2_manifest(
    isolated_output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _payload, _raw = _build(isolated_output)
    task = REPOSITORY / source_q.TASK_PATHS[0]
    package = load_task_package(task)
    authority = source_q.load_evaluator_v2_ac_qualification_authority(
        task,
        runtime_secret_markers=(b"test-run-marker-not-a-provider-key",),
        repository=REPOSITORY,
    )
    monkeypatch.setattr(runtime_module, "git_commit", lambda: "a" * 40)
    monkeypatch.setattr(runtime_module, "version", lambda _package: "offline-test-sdk")
    context = ExperimentRunContext(
        experiment_id=AC_FIXED_BUNDLE_CONTRACT_HARDENED_EXPERIMENT_ID,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_AC_READINESS,
        suite_hash=summary["successor_suite_hash"],
        execution_hash="sha256:" + "1" * 64,
        campaign_cost_control_hash="sha256:" + "2" * 64,
        dataset_manifest_hash="sha256:" + "3" * 64,
        dataset_role=DatasetRole.DEVELOPMENT_VALIDATION,
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id="sha256:" + "4" * 64,
        repetition=1,
    )
    manifest = runtime_module.build_manifest(
        package,
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        memory_condition=MemoryCondition.NO_MEMORY,
        memory_policy_version="fixed-d110-bundle-v1",
        sandbox_backend="docker",
        budget=Budget(
            max_model_calls=180,
            max_tool_calls=300,
            max_total_tokens=3_350_000,
            wall_clock_timeout_seconds=3_600,
            token_budget_schema_version="cumulative-split-v1",
            max_cumulative_input_tokens=3_000_000,
            max_cumulative_output_tokens=350_000,
        ),
        agent_image_digest=package.environment.image_digest,
        evaluator_image_digest=package.environment.image_digest,
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        experiment_context=context,
    )

    bound = eval_runner._bind_evaluator_v2_manifest(manifest, package, authority)
    qualification = {
        key: summary[key]
        for key in (
            "source_qualification_hash",
            "evaluator_source_hash",
            "successor_suite_hash",
            "base_suite_hash",
        )
    } | {"base_suite_matches": True}

    assert bound.schema_version == "run-manifest-v2"
    assert bound.evaluator_contract is not None
    assert bound.evaluator_contract.evaluator_source_hash == summary["evaluator_source_hash"]
    assert bound.evaluator_contract.contract_hash == authority.runtime.safety_contract.content_hash
    system_prompt, tool_schemas = agent_runner.AgentRunner._runtime_contract(bound)
    runtime_evidence = agent_runner.AgentRunner._generic_baseline_runtime_evidence_document(
        manifest=bound,
        system_prompt=system_prompt,
        tool_schemas=tool_schemas,
    )
    assert runtime_evidence["call_guard_policy"] == (
        eval_runner.AC_FIXED_BUNDLE_SPLIT_CALL_GUARD_POLICY
    )
    assert (
        source_q.validate_evaluator_v2_ac_paid_authority(
            bound,
            authority,
            qualification,
            repository=REPOSITORY,
        )
        == authority
    )

    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="differs from the source artifact",
    ):
        source_q.validate_evaluator_v2_ac_paid_authority(
            bound,
            authority,
            {**qualification, "source_qualification_hash": "sha256:" + "0" * 64},
            repository=REPOSITORY,
        )

    from patchloop.agent.tools import TOOL_SCHEMAS_V2
    from patchloop.verifier.receipt import EvaluatorV2QualificationAuthority
    from patchloop.verifier.runtime_evidence import (
        EvaluatorV2RuntimeAuthority,
        build_evaluator_safety_contract_v2,
    )

    forged_contract = build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=authority.runtime.private_markers,
    )
    forged_authority = EvaluatorV2QualificationAuthority(
        runtime=EvaluatorV2RuntimeAuthority(
            safety_contract=forged_contract,
            evaluator_source_hash=summary["evaluator_source_hash"],
            tool_schemas=tuple(TOOL_SCHEMAS_V2),
            private_markers=authority.runtime.private_markers,
        ),
        suite_hash=summary["successor_suite_hash"],
        source_qualification_hash=summary["source_qualification_hash"],
        runtime_tuple_hash=authority.runtime_tuple_hash,
    )
    forged_bound = eval_runner._bind_evaluator_v2_manifest(
        manifest,
        package,
        forged_authority,
    )
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="differs from the qualified source or task",
    ):
        source_q.validate_evaluator_v2_ac_paid_authority(
            forged_bound,
            forged_authority,
            qualification,
            repository=REPOSITORY,
        )


def test_ac_runner_loads_task_authorities_without_persisting_runtime_marker(
    isolated_output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _payload, _raw = _build(isolated_output)
    runtime_marker = "test-runtime-marker-not-a-provider-key"
    monkeypatch.setenv("OPENAI_API_KEY", runtime_marker)
    suite = eval_runner.load_suite(source_q.BASE_SUITE_PATH)

    authorities = eval_runner._load_ac_evaluator_v2_runtime_authorities(
        suite,
        {
            key: summary[key]
            for key in (
                "source_qualification_hash",
                "evaluator_source_hash",
                "successor_suite_hash",
                "base_suite_hash",
            )
        }
        | {"base_suite_matches": True},
    )

    assert set(authorities) == {
        "moto-query-scanned-count",
        "babel-strict-grouped-decimal-trailing-zeroes",
    }
    assert all(
        runtime_marker.encode("utf-8") in authority.runtime.private_markers
        for authority in authorities.values()
    )
    assert runtime_marker.encode("utf-8") not in isolated_output.read_bytes()


def test_authority_factory_rejects_unqualified_task_and_bad_markers(
    isolated_output: Path,
) -> None:
    _build(isolated_output)
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="outside the qualified successor suite",
    ):
        source_q.load_evaluator_v2_ac_qualification_authority(
            REPOSITORY / "tasks/smoke/csv-quoted-newline",
            runtime_secret_markers=(b"test-secret-marker",),
            repository=REPOSITORY,
        )
    task = REPOSITORY / source_q.TASK_PATHS[0]
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="duplicated",
    ):
        source_q.load_evaluator_v2_ac_qualification_authority(
            task,
            runtime_secret_markers=(b"duplicate-secret", b"duplicate-secret"),
            repository=REPOSITORY,
        )


def test_current_source_drift_fails_closed(
    isolated_output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _build(isolated_output)
    original = source_q._file_binding

    def drifted(root: Path, relative: Path) -> source_q.QualificationFileBinding:
        value = original(root, relative)
        if relative == source_q.SOURCE_PATHS[0]:
            return source_q.QualificationFileBinding(
                path=value.path,
                file_bytes=value.file_bytes,
                file_sha256="sha256:" + "0" * 64,
            )
        return value

    monkeypatch.setattr(source_q, "_file_binding", drifted)
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="has drifted",
    ):
        source_q.validate_evaluator_v2_ac_source_qualification(repository=REPOSITORY)


def test_plan_or_artifact_tamper_fails_closed(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    payload["authority"]["provider_or_evaluator_execution_authorized"] = True
    isolated_output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="artifact is invalid|bytes are not canonical",
    ):
        source_q.validate_evaluator_v2_ac_source_qualification(repository=REPOSITORY)


def test_content_hash_tamper_is_rejected_after_model_copy_roundtrip(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    parsed = source_q.EvaluatorV2ACSourceQualification.model_validate(payload)
    tampered = parsed.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    with pytest.raises(ValidationError):
        source_q.EvaluatorV2ACSourceQualification.model_validate(tampered.model_dump(mode="json"))
