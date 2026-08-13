from __future__ import annotations

import copy
import shutil
import socket
import subprocess
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import pytest
import yaml

from patchloop import runtime as runtime_module
from patchloop.agent import model as model_module
from patchloop.agent.model import SYSTEM_PROMPT_V3
from patchloop.agent.runner import (
    AgentRunner,
    _load_live_execution_plan,
    issue_live_execution_authorization,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    FaultSpec,
    MemoryCondition,
    MemoryConfig,
    ModelConfig,
    RunManifest,
    Usage,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals import evaluator_v2_source_qualification as source_q
from patchloop.evals import qualification
from patchloop.evals import runner as eval_runner
from patchloop.evals.evaluator_v2_source_qualification import (
    validate_evaluator_v2_ac_paid_authority,
)
from patchloop.runtime import build_manifest
from patchloop.sandbox import DockerSandbox
from patchloop.state import StateStore
from patchloop.task_loader import load_public_task, load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

R8_SUITE = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml")
OFFLINE_SOURCE_COMMIT = "b" * 40
OFFLINE_SECRET = "offline-r8-contract-chain-never-sent"
R8_MOTO_TASK = Path("tasks/dev-validation/moto-query-scanned-count")


def _machine_scalar_paths(value: Any, path: tuple[str | int, ...] = ()):
    if type(value) in {bool, int, float} or type(value) in {datetime, date, time}:
        yield path
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _machine_scalar_paths(item, (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _machine_scalar_paths(item, (*path, index))


def _replace_machine_scalar(value: Any) -> str | int:
    if type(value) is bool:
        return str(value).lower()
    if type(value) is int:
        return str(value)
    if type(value) is float:
        return int(value) if value.is_integer() else str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    raise AssertionError(f"unsupported machine scalar: {value!r}")


def _mutate_path(payload: Any, path: tuple[str | int, ...]) -> None:
    selected = payload
    for part in path[:-1]:
        selected = selected[part]
    selected[path[-1]] = _replace_machine_scalar(selected[path[-1]])


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"{label} is forbidden in the API-free R8 contract-chain test")

    return fail


@pytest.fixture
def r8_approved_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, eval_runner.ExperimentSuite, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Replay the sealed pre-execution R8 chain with external access impossible."""

    run_root = tmp_path / "runtime"
    monkeypatch.setenv("OPENAI_API_KEY", OFFLINE_SECRET)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 13, 12, 5, 27, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: run_root)
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": OFFLINE_SOURCE_COMMIT, "clean": True},
    )
    monkeypatch.setattr(
        eval_runner,
        "_docker_image_state",
        lambda images: {
            "available": True,
            "images": [
                {
                    "image": image,
                    "identity": image.rsplit("@", 1)[-1],
                    "ready": True,
                }
                for image in sorted(set(images))
            ],
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_openai_sdk_state",
        lambda: {"installed": True, "version": "offline-contract-chain-sdk"},
    )
    monkeypatch.setattr(runtime_module, "git_commit", lambda: OFFLINE_SOURCE_COMMIT)
    monkeypatch.setattr(
        runtime_module,
        "version",
        lambda _package: "offline-contract-chain-sdk",
    )

    # These guards sit below the offline projections above. Any accidental
    # provider, network, Docker CLI, agent construction, or child process use
    # therefore fails before it can leave the test process.
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network connection"))
    monkeypatch.setattr(subprocess, "run", _forbidden("subprocess.run"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("subprocess.Popen"))
    monkeypatch.setattr(model_module, "OpenAI", _forbidden("OpenAI client"))
    monkeypatch.setattr(model_module.httpx, "Client", _forbidden("HTTP client"))
    monkeypatch.setattr(AgentRunner, "__init__", _forbidden("AgentRunner construction"))
    monkeypatch.setattr(DockerSandbox, "__init__", _forbidden("DockerSandbox construction"))

    suite = eval_runner.load_suite(R8_SUITE)
    qualification_raw = (source_q._repo_root(None) / source_q.OUTPUT_PATH).read_bytes()
    qualification_payload = source_q.EvaluatorV2ACSourceQualification.model_validate_json(
        qualification_raw
    )
    assert qualification_raw == source_q._canonical_bytes(qualification_payload)
    qualification_summary = source_q._summary(qualification_payload, qualification_raw)
    monkeypatch.setattr(
        source_q,
        "_load_validated",
        lambda _root: (qualification_payload, qualification_raw),
    )
    monkeypatch.setattr(
        eval_runner,
        "HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS",
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS - {suite.experiment_id},
    )
    monkeypatch.setattr(
        eval_runner,
        "_validated_ac_evaluator_v2_source_qualification",
        lambda selected: {
            "source_qualification_hash": qualification_summary["source_qualification_hash"],
            "evaluator_source_hash": qualification_summary["evaluator_source_hash"],
            "successor_suite_hash": qualification_summary["successor_suite_hash"],
            "base_suite_hash": qualification_summary["base_suite_hash"],
            "base_suite_matches": (
                eval_runner._suite_hash(selected) == qualification_summary["base_suite_hash"]
            ),
        },
    )
    candidate = eval_runner.preflight_suite(R8_SUITE)
    assert (
        candidate["evaluator_v2_qualification"]["source_qualification_hash"]
        == (qualification_summary["source_qualification_hash"])
    )
    assert candidate["suite_hash"] == qualification_summary["successor_suite_hash"]
    assert {blocker["code"] for blocker in candidate["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }

    approved = eval_runner.preflight_suite(
        R8_SUITE,
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
    )
    assert approved["ready"] is True
    assert approved["blockers"] == []
    assert approved["approval"] == {
        "invocation_approve_live_cost": True,
        "invocation_approved_execution_hash": candidate["execution_hash"],
        "matches_execution_hash": True,
        "suite_live_cost_approved_deprecated": False,
        "suite_approved_execution_hash_deprecated": None,
    }

    plan_binding = eval_runner._persist_preflight_plan(approved)
    authorization = issue_live_execution_authorization(
        approved["execution_hash"],
        root=run_root,
    )
    plan = _load_live_execution_plan(authorization)
    assert plan["schema_version"] == "experiment-execution-plan-v1"
    assert plan_binding["artifact_hash"] == sha256_text(canonical_json(plan))
    assert authorization.plan_hash == sha256_bytes(Path(plan_binding["path"]).read_bytes())
    assert OFFLINE_SECRET not in canonical_json(plan)

    authorities = eval_runner._load_ac_evaluator_v2_runtime_authorities(
        suite,
        approved["evaluator_v2_qualification"],
    )
    assert set(authorities) == {row["task_id"] for row in approved["tasks"]}
    return run_root, suite, approved, plan, authorities


def _bound_manifest(
    suite: eval_runner.ExperimentSuite,
    approved: dict[str, Any],
    authorities: dict[str, Any],
    *,
    row_index: int,
):
    schedule_row = approved["schedule"][row_index]
    task_row = next(row for row in approved["tasks"] if row["task_id"] == schedule_row["task_id"])
    item = {**task_row, **schedule_row}
    task_path = Path(item["task"])
    package = load_task_package(task_path.parent if task_path.is_file() else task_path)
    experiment = ExperimentRunContext(
        experiment_id=suite.experiment_id,
        purpose=suite.purpose,
        suite_hash=approved["suite_hash"],
        execution_hash=approved["execution_hash"],
        campaign_cost_control_hash=approved["campaign_cost_control"]["content_hash"],
        dataset_manifest_hash=approved["dataset"]["manifest_hash"],
        dataset_role=DatasetRole(item["dataset_role"]),
        schedule_seed=suite.seed,
        schedule_order=item["order"],
        schedule_row_id=item["schedule_row_id"],
        repetition=item["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id=f"run_r8_offline_contract_chain_{row_index + 1}",
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(item["condition"]),
        memory_policy_version=suite.memory_policy_version or "v1",
        sandbox_backend="docker",
        budget=suite.budget,
        agent_image_digest=item["evaluator_image_digest"],
        evaluator_image_digest=item["evaluator_image_digest"],
        input_price_per_million_usd=suite.input_price_per_million_usd,
        cached_input_price_per_million_usd=suite.cached_input_price_per_million_usd,
        cache_write_input_price_per_million_usd=(suite.cache_write_input_price_per_million_usd),
        output_price_per_million_usd=suite.output_price_per_million_usd,
        reasoning_effort=suite.reasoning_effort,
        reasoning_mode=suite.reasoning_mode,
        service_tier=suite.service_tier,
        transport_max_retries=suite.transport_max_retries,
        max_output_tokens=suite.max_output_tokens,
        fault=eval_runner._diagnostic_fault(suite),
        experiment_context=experiment,
    )
    authority = authorities[package.public.task_id]
    manifest = eval_runner._bind_evaluator_v2_manifest(manifest, package, authority)
    validate_evaluator_v2_ac_paid_authority(
        manifest,
        authority,
        approved["evaluator_v2_qualification"],
    )
    eval_runner._assert_manifest_matches_preflight(
        manifest,
        suite=suite,
        preflight=approved,
        item=item,
    )
    return manifest, package, item


def _write_offline_runtime_trace(
    run_root: Path,
    manifest: Any,
    *,
    call_guard_policy: str | None = None,
) -> dict[str, Any]:
    runtime_document = AgentRunner._generic_baseline_runtime_evidence_document(
        manifest=manifest,
        system_prompt=SYSTEM_PROMPT_V3,
        tool_schemas=TOOL_SCHEMAS_V2,
    )
    assert runtime_document is not None
    if call_guard_policy is not None:
        runtime_document["call_guard_policy"] = call_guard_policy

    artifact = ArtifactStore(run_root / "artifacts").put_json(runtime_document)
    state = StateStore(run_root / "state.sqlite3")
    state.create_run(manifest)
    state.append_event(
        manifest.run_id,
        EventType.RUN_STARTED,
        actor="runner",
        payload={
            "task_id": manifest.task_id,
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
            "artifact_role": "runtime-contract",
            "runtime_contract_artifact": artifact.model_dump(mode="json"),
        },
    )
    state.append_event(
        manifest.run_id,
        EventType.CONTEXT_BUILT,
        actor="context-builder",
        payload={"investigation_tail_block_reasons": []},
    )
    state.append_event(
        manifest.run_id,
        EventType.RUN_FAILED,
        actor="runner",
        payload={
            "error_type": "OfflineContractChainTerminal",
            "message": "synthetic local terminal; no provider request was made",
        },
    )
    return runtime_document


def _checks(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {check["check_id"]: check for check in payload["checks"]}


@pytest.mark.parametrize(
    ("field_path", "quoted_value"),
    [
        (("repetitions",), "1"),
        (("schedule", 0, "order"), "1"),
        (("max_output_tokens",), "25000"),
        (("budget", "max_model_calls"), "180"),
        (("campaign_cost_policy", "scheduled_run_count"), "4"),
        (("campaign_cost_policy", "cost_censoring_allowed"), "false"),
        (("live_cost_approved",), "false"),
        (("estimated_cost_usd",), "15.3"),
        (("seed",), "20260723"),
        (("cost_limit_usd",), 18),
        (("campaign_cost_policy", "hard_cap_usd"), 18),
        (("pricing_verified_at",), "2026-08-13T12:05:26Z"),
    ],
)
def test_r8_raw_suite_rejects_quoted_machine_scalars(
    tmp_path: Path,
    field_path: tuple[str | int, ...],
    quoted_value: str,
) -> None:
    payload = yaml.safe_load(R8_SUITE.read_text(encoding="utf-8"))
    selected: Any = payload
    for part in field_path[:-1]:
        selected = selected[part]
    selected[field_path[-1]] = quoted_value
    path = tmp_path / "r8-quoted-scalar.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ContractError, match="experiment contract validation failed"):
        eval_runner.load_suite(path)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"approve_live_cost": 1},
        {"credential_present": 1},
        {"credential_present": "true"},
    ],
)
def test_preflight_rejects_non_boolean_control_inputs(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ContractError, match="must be a boolean"):
        eval_runner.preflight_suite(R8_SUITE, **kwargs)


@pytest.mark.parametrize("value", [False, 0.0, "0"])
def test_usage_counters_reject_non_integer_json_scalars(value: object) -> None:
    with pytest.raises(ValueError, match="usage counters must be JSON integers"):
        Usage(input_tokens=value)


def test_manifest_nested_machine_contracts_reject_coercive_scalars() -> None:
    hashes = {
        "suite_hash": "sha256:" + "1" * 64,
        "execution_hash": "sha256:" + "2" * 64,
        "schedule_row_id": "sha256:" + "3" * 64,
    }
    with pytest.raises(ValueError, match="schedule fields must be JSON integers"):
        ExperimentRunContext(
            experiment_id="offline-type-check",
            purpose=ExperimentPurpose.OFFLINE_SMOKE,
            schedule_seed="20260723",
            schedule_order=1,
            repetition=1,
            **hashes,
        )
    with pytest.raises(ValueError, match="fault trigger_after must be a JSON integer"):
        FaultSpec(trigger_after=True)
    with pytest.raises(ValueError, match="memory max_context_tokens must be a JSON integer"):
        MemoryConfig(max_context_tokens=2_000.0)
    with pytest.raises(ValueError, match="prices must be JSON numbers with decimals"):
        ModelConfig(
            provider="openai",
            model_id="offline-model",
            input_price_per_million_usd=1,
        )
    with pytest.raises(ValueError, match="manifest task_version must be a JSON integer"):
        RunManifest(
            run_id="run_offline_type_check",
            task_id="offline-type-check",
            task_version=True,
            base_commit="offline",
            public_spec_hash="sha256:" + "4" * 64,
            model=ModelConfig(provider="mock", model_id="offline-model"),
            created_at=datetime(2026, 8, 14, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="created_at must be an RFC3339 string or datetime"):
        RunManifest(
            run_id="run_offline_timestamp_check",
            task_id="offline-type-check",
            task_version=1,
            base_commit="offline",
            public_spec_hash="sha256:" + "4" * 64,
            model=ModelConfig(provider="mock", model_id="offline-model"),
            created_at=1_786_646_400,
        )


def test_suite_loader_rejects_duplicate_mapping_keys(tmp_path: Path) -> None:
    duplicate = R8_SUITE.read_text(encoding="utf-8") + "\ncost_limit_usd: 18.0\n"
    selected = tmp_path / "duplicate-key-suite.yaml"
    selected.write_text(duplicate, encoding="utf-8")

    with pytest.raises(ContractError, match="duplicate key 'cost_limit_usd'"):
        eval_runner.load_suite(selected)


def test_r8_suite_rejects_every_normalizable_machine_scalar_type(tmp_path: Path) -> None:
    original = yaml.safe_load(R8_SUITE.read_text(encoding="utf-8"))
    paths = list(_machine_scalar_paths(original))
    assert paths
    selected = tmp_path / "r8-machine-scalar-type.yaml"

    for path in paths:
        payload = copy.deepcopy(original)
        _mutate_path(payload, path)
        selected.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        with pytest.raises(ContractError, match="experiment contract validation failed"):
            eval_runner.load_suite(selected)


def test_task_loader_rejects_every_normalizable_machine_scalar_type(tmp_path: Path) -> None:
    copied_task = tmp_path / "moto-query-scanned-count"
    shutil.copytree(R8_MOTO_TASK, copied_task)

    for filename in ("public.yaml", "private.yaml"):
        target = copied_task / filename
        original_text = target.read_text(encoding="utf-8")
        original = yaml.safe_load(original_text)
        paths = list(_machine_scalar_paths(original))
        assert paths
        for path in paths:
            payload = copy.deepcopy(original)
            _mutate_path(payload, path)
            target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            with pytest.raises(ContractError, match="scalar type mismatch"):
                load_task_package(copied_task)
        target.write_text(original_text, encoding="utf-8")


def test_task_loader_rejects_duplicate_mapping_keys(tmp_path: Path) -> None:
    selected = tmp_path / "public.yaml"
    selected.write_text(
        R8_MOTO_TASK.joinpath("public.yaml").read_text(encoding="utf-8") + "\ntask_version: 1\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="duplicate key 'task_version'"):
        load_public_task(selected)


def test_task_loader_rejects_binary_text_scalar(tmp_path: Path) -> None:
    payload = yaml.safe_load(R8_MOTO_TASK.joinpath("public.yaml").read_text(encoding="utf-8"))
    payload["task_id"] = b"moto-query-scanned-count"
    selected = tmp_path / "public.yaml"
    selected.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ContractError, match="expected str, got bytes"):
        load_public_task(selected)


def test_all_checked_in_task_packages_keep_exact_scalar_contracts() -> None:
    package_roots = {path.parent for path in Path("tasks").rglob("public.yaml")} | {
        path.parent for path in Path("fixtures/task-packages").rglob("public.yaml")
    }
    assert len(package_roots) == 26
    for package_root in sorted(package_roots):
        load_task_package(package_root)


def test_dataset_loader_rejects_every_normalizable_machine_scalar_type(
    tmp_path: Path,
) -> None:
    manifest_path = Path("data/dataset-manifest.yaml")
    original = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    paths = list(_machine_scalar_paths(original))
    assert paths
    selected = tmp_path / "dataset-manifest.yaml"

    for path in paths:
        payload = copy.deepcopy(original)
        _mutate_path(payload, path)
        selected.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        with pytest.raises(ContractError):
            load_dataset_manifest(selected)


def test_dataset_loader_rejects_duplicate_mapping_keys(tmp_path: Path) -> None:
    manifest_path = Path("data/dataset-manifest.yaml")
    selected = tmp_path / "dataset-manifest.yaml"
    selected.write_text(
        manifest_path.read_text(encoding="utf-8") + "\ncalibration_target: 5\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="duplicate key 'calibration_target'"):
        load_dataset_manifest(selected)


def test_dataset_loader_rejects_binary_enum_scalar(tmp_path: Path) -> None:
    manifest_path = Path("data/dataset-manifest.yaml")
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["tasks"][0]["role"] = b"calibration"
    selected = tmp_path / "dataset-manifest.yaml"
    selected.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ContractError, match="expected str, got bytes"):
        load_dataset_manifest(selected)


def test_r8_r10_producer_consumer_chain_accepts_all_four_rows_without_api(
    r8_approved_chain: tuple[
        Path,
        eval_runner.ExperimentSuite,
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    run_root, suite, approved, plan, authorities = r8_approved_chain

    for row_index in range(4):
        manifest, package, _item = _bound_manifest(
            suite,
            approved,
            authorities,
            row_index=row_index,
        )
        assert qualification._execution_plan_matches(plan=plan, manifest=manifest)

        runtime_document = _write_offline_runtime_trace(run_root, manifest)
        assert runtime_document["budget"] == approved["runtime_contract"]["budget"]
        assert (
            runtime_document["call_guard_policy"]
            == (approved["runtime_contract"]["call_guard_policy"])
        )
        assert runtime_document["memory_condition"] == manifest.memory.condition.value
        assert OFFLINE_SECRET not in canonical_json(runtime_document)

        payload = qualification.qualify_run(
            manifest.run_id,
            task_dir=package.root,
            root=run_root,
            persist=False,
        )
        checks = _checks(payload)
        assert checks["approved_execution_plan"]["passed"] is True
        assert checks["ac_fixed_runtime_contract"]["passed"] is True
        assert checks["bounded_call_guard_contract"]["passed"] is True
        assert checks["bounded_call_guard_contract"]["details"] == {
            "policy_version": eval_runner.AC_FIXED_BUNDLE_SPLIT_CALL_GUARD_POLICY,
            "model_call_limit": 180,
            "tool_call_limit": 300,
            "forbidden_generation_block_sequences": [],
            "forbidden_tail_block_sequences": [],
            "runtime_contract_valid": True,
            "context_tail_failure_sequences": [],
            "admission_tail_failure_sequences": [],
        }


def test_r8_qualifier_rejects_the_r6_legacy_call_guard_serialization(
    r8_approved_chain: tuple[
        Path,
        eval_runner.ExperimentSuite,
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    run_root, suite, approved, plan, authorities = r8_approved_chain
    manifest, package, _item = _bound_manifest(
        suite,
        approved,
        authorities,
        row_index=0,
    )
    assert qualification._execution_plan_matches(plan=plan, manifest=manifest)
    _write_offline_runtime_trace(
        run_root,
        manifest,
        call_guard_policy="model-tool-observability-only-v1",
    )

    payload = qualification.qualify_run(
        manifest.run_id,
        task_dir=package.root,
        root=run_root,
        persist=False,
    )
    checks = _checks(payload)
    assert checks["approved_execution_plan"]["passed"] is True
    assert checks["ac_fixed_runtime_contract"]["passed"] is False
    assert checks["bounded_call_guard_contract"]["passed"] is False
    assert checks["bounded_call_guard_contract"]["details"]["runtime_contract_valid"] is False
