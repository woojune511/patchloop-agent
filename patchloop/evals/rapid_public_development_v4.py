"""Contract-rehearsed candidate-v6 successor for the Rapid V3 hard panel.

V4 keeps the exact public PDM/AnyIO comparison and cost ceiling.  It replaces
per-row candidate reconstruction with one compact runtime build binding, one
batch admission, and typed one-use row capabilities.  A durable no-call
rehearsal receipt is required before the paid entry point can open.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.runner import (
    AgentRunner,
    BatchExecutionAuthorization,
    LiveExecutionAuthorization,
    issue_batch_execution_authorization,
    issue_live_execution_authorization,
    issue_row_execution_authorization,
)
from patchloop.contracts import (
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
    RunOutcomeKind,
    Usage,
)
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_public_development import (
    FULL_SCHEDULE_RESERVE_NANOS,
    HARD_CAP_NANOS,
    MODEL_ID,
    RUNTIME_BUDGET,
    _append_bundle_event,
    _persisted_result,
    _row_projection,
    _runtime_dependencies,
    _source_snapshot,
    _within,
)
from patchloop.evals.rapid_public_development_v2 import _write_once
from patchloop.evals.rapid_public_development_v3 import (
    CONFIG_PATH,
    EXPERIMENT_ID,
    SCHEDULE_SEED,
    SELECTION_EVIDENCE,
    VARIANT_CONTRACTS,
    RapidPublicDevelopmentV3Config,
    _binding,
    _read_config,
    _schedule_projection,
    _task_bindings,
)
from patchloop.memory.fixed_bundle import FIXED_BUNDLE_POLICY_VERSION
from patchloop.runtime import build_manifest
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

CANDIDATE_SCHEMA = "rapid-public-development-candidate-v6"
CANDIDATE_REVISION = 6
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-candidate-v6.json"
)
PREDECESSOR_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-candidate-v5.json"
)
PREDECESSOR_TERMINAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-harness-admission-terminal-v3.json"
)
REHEARSAL_SCHEMA = "rapid-public-development-rehearsal-v3"
REHEARSAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-candidate-v6-rehearsal-v3.json"
)
RESULT_SCHEMA = "rapid-public-development-bundle-event-v6"
PLAN_SCHEMA = "experiment-execution-plan-v6"
PLAN_KIND = "rapid-public-development-batch-v1"
RUNTIME_BUILD_SCHEMA = "rapid-runtime-build-v1"
VERIFIER_ID = "rapid-r3-candidate-v6-plan-v6"
HARNESS_ADMISSION_FAILURE = "harness_admission_failure"
MANIFEST_CREATED_AT = datetime(2026, 8, 22, tzinfo=UTC)

_REHEARSAL_STAGE_SEQUENCE = (
    "candidate-current-binding",
    "registered-plan-schema",
    "all-row-manifests",
    "batch-capability",
    "batch-start-prefix",
    "first-row-capability",
    "first-provider-dispatch-boundary",
    "realistic-resolved-row-terminal",
    "second-row-prefix",
    "second-row-capability",
    "second-provider-dispatch-boundary",
)


@dataclass(frozen=True)
class PreparedRapidV4Batch:
    plan: dict[str, Any]
    plan_hash: str
    manifests: tuple[RunManifest, ...]
    authorization: BatchExecutionAuthorization
    verifier_id: str


def _runtime_build_binding(root: Path) -> tuple[str, dict[str, str]]:
    """Collapse source and dependency inventory into one runtime/build hash."""

    source = _source_snapshot(root)
    dependencies = _runtime_dependencies(root)
    descriptor = {
        "schema_version": RUNTIME_BUILD_SCHEMA,
        "source_scope": source["scope"],
        "source_file_count": source["file_count"],
        "source_snapshot_hash": source["content_hash"],
        "uv_lock_sha256": dependencies["uv_lock_sha256"],
        "openai_sdk_version": dependencies["openai_sdk_version"],
    }
    return sha256_json(descriptor), dependencies


def _candidate_body(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    config, raw, selected = _read_config(repository=root)
    bindings = _task_bindings(config, root)
    schedule = _schedule_projection(config, bindings)
    runtime_build_hash, dependencies = _runtime_build_binding(root)
    cost_control = {
        **config.cost_policy.model_dump(mode="json"),
        "scheduled_run_count": len(schedule),
        "cost_censoring_allowed": False,
        "official": False,
    }
    model_contract = {
        "provider": "openai",
        "model_id": MODEL_ID,
        "provider_sdk_version": dependencies["openai_sdk_version"],
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "temperature": 0.0,
        "max_output_tokens": 25_000,
    }
    return {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_revision": CANDIDATE_REVISION,
        "experiment_id": EXPERIMENT_ID,
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "config_path": selected.relative_to(root).as_posix(),
        "config_file_sha256": sha256_bytes(raw),
        "config_semantic_hash": sha256_json(config.model_dump(mode="json")),
        "selection_evidence": SELECTION_EVIDENCE,
        "selection_evidence_hash": sha256_json(SELECTION_EVIDENCE),
        "runtime_build_schema": RUNTIME_BUILD_SCHEMA,
        "runtime_build_hash": runtime_build_hash,
        "model_contract": model_contract,
        "predecessor_candidate": _binding(
            root,
            PREDECESSOR_CANDIDATE_PATH,
        ).model_dump(mode="json"),
        "predecessor_terminal": _binding(
            root,
            PREDECESSOR_TERMINAL_PATH,
        ).model_dump(mode="json"),
        "variant_contracts": VARIANT_CONTRACTS,
        "task_bindings": [item.model_dump(mode="json") for item in bindings],
        "schedule": list(schedule),
        "schedule_hash": sha256_json(list(schedule)),
        "cost_control": cost_control,
        "cost_control_hash": sha256_json(cost_control),
    }


def _execution_body(candidate: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "candidate_revision",
        "experiment_id",
        "purpose",
        "official",
        "config_path",
        "config_file_sha256",
        "config_semantic_hash",
        "selection_evidence",
        "selection_evidence_hash",
        "runtime_build_schema",
        "runtime_build_hash",
        "model_contract",
        "predecessor_candidate",
        "predecessor_terminal",
        "variant_contracts",
        "task_bindings",
        "schedule",
        "schedule_hash",
        "cost_control",
        "cost_control_hash",
    )
    try:
        return {key: candidate[key] for key in keys}
    except KeyError as exc:
        raise RecoveryError("Rapid candidate-v6 execution body is incomplete") from exc


def build_rapid_public_development_v4_candidate(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build the compact no-call candidate under explicit external-call guards."""

    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    original_available = DockerSandbox.available
    original_next_turn = OpenAIResponsesAdapter.next_turn
    original_execute_request = OpenAIResponsesAdapter.execute_request
    original_start = AgentRunner.start
    original_create_connection = socket.create_connection
    original_socket_connect = socket.socket.connect
    original_popen = subprocess.Popen

    def blocked_external(*_args: Any, **_kwargs: Any) -> Any:
        raise RecoveryError("Rapid candidate-v6 generation attempted an external call")

    DockerSandbox.available = staticmethod(blocked_external)
    OpenAIResponsesAdapter.next_turn = blocked_external
    OpenAIResponsesAdapter.execute_request = blocked_external
    AgentRunner.start = blocked_external
    socket.create_connection = blocked_external
    socket.socket.connect = blocked_external
    subprocess.Popen = blocked_external
    try:
        body = _candidate_body(root)
    finally:
        DockerSandbox.available = staticmethod(original_available)
        OpenAIResponsesAdapter.next_turn = original_next_turn
        OpenAIResponsesAdapter.execute_request = original_execute_request
        AgentRunner.start = original_start
        socket.create_connection = original_create_connection
        socket.socket.connect = original_socket_connect
        subprocess.Popen = original_popen
    execution_hash = sha256_json(body)
    candidate = {
        **body,
        "execution_hash": execution_hash,
        "source_qualified": True,
        "execution_authorized": False,
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "approval_required": True,
        "rehearsal_required": True,
    }
    return {**candidate, "content_hash": sha256_json(candidate)}


def _validate_candidate(candidate: dict[str, Any]) -> None:
    content_body = {key: value for key, value in candidate.items() if key != "content_hash"}
    if (
        type(candidate) is not dict
        or candidate.get("schema_version") != CANDIDATE_SCHEMA
        or candidate.get("candidate_revision") != CANDIDATE_REVISION
        or candidate.get("experiment_id") != EXPERIMENT_ID
        or candidate.get("official") is not False
        or candidate.get("runtime_build_schema") != RUNTIME_BUILD_SCHEMA
        or candidate.get("source_qualified") is not True
        or candidate.get("execution_authorized") is not False
        or candidate.get("provider_calls_made") != 0
        or candidate.get("docker_calls_made") != 0
        or candidate.get("added_model_cost_usd") != 0.0
        or candidate.get("approval_required") is not True
        or candidate.get("rehearsal_required") is not True
        or candidate.get("execution_hash") != sha256_json(_execution_body(candidate))
        or candidate.get("content_hash") != sha256_json(content_body)
    ):
        raise RecoveryError("Rapid candidate-v6 identity differs")


def candidate_bytes(candidate: dict[str, Any]) -> bytes:
    _validate_candidate(candidate)
    return (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def materialize_rapid_public_development_v4_candidate(
    repository: str | Path = ".",
    output_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    output = ensure_within(root, Path(output_path).as_posix())
    if output.exists():
        return load_rapid_public_development_v4_candidate(root, output_path)
    candidate = build_rapid_public_development_v4_candidate(repository=root)
    _prepare_batch(candidate, authority_kind="rehearsal")
    _write_once(output, candidate_bytes(candidate))
    return load_rapid_public_development_v4_candidate(root, output_path)


def load_rapid_public_development_v4_candidate(
    repository: str | Path = ".",
    candidate_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    selected = ensure_within(root, Path(candidate_path).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError("Rapid candidate-v6 is unavailable")
    try:
        candidate = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("Rapid candidate-v6 is invalid") from exc
    if type(candidate) is not dict or candidate_bytes(candidate) != selected.read_bytes():
        raise RecoveryError("Rapid candidate-v6 bytes differ")
    current = build_rapid_public_development_v4_candidate(repository=root)
    if candidate != current:
        raise RecoveryError("Rapid candidate-v6 current binding differs")
    return candidate


def _plan(candidate: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    _validate_candidate(candidate)
    body = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "experiment_id": EXPERIMENT_ID,
        "candidate_revision": CANDIDATE_REVISION,
        "candidate_content_hash": candidate["content_hash"],
        "ready": approved,
        "blockers": [] if approved else ["EXACT_APPROVAL_REQUIRED"],
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "suite_hash": candidate["config_semantic_hash"],
        "config_file_sha256": candidate["config_file_sha256"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "selection_evidence_hash": candidate["selection_evidence_hash"],
        "model_contract": candidate["model_contract"],
        "variant_contracts": candidate["variant_contracts"],
        "task_bindings": candidate["task_bindings"],
        "schedule": candidate["schedule"],
        "schedule_hash": candidate["schedule_hash"],
        "campaign_cost_control": {
            "content_hash": candidate["cost_control_hash"],
            "descriptor": candidate["cost_control"],
        },
        "approval": {
            "invocation_approve_live_cost": approved,
            "invocation_approved_execution_hash": (
                candidate["execution_hash"] if approved else None
            ),
            "matches_execution_hash": approved,
        },
    }
    return {**body, "content_hash": sha256_json(body)}


def _plan_bytes(plan: dict[str, Any]) -> bytes:
    return (canonical_json(plan) + "\n").encode("utf-8")


def _build_manifest_unchecked(
    candidate: dict[str, Any],
    order: int,
    *,
    repository: str | Path,
) -> RunManifest:
    root = Path(repository).resolve()
    row = next(item for item in candidate["schedule"] if item["order"] == order)
    binding = next(
        item for item in candidate["task_bindings"] if item["task_id"] == row["task_id"]
    )
    package = load_task_package(_within(root, row["task"]).parent)
    experiment = ExperimentRunContext(
        experiment_id=EXPERIMENT_ID,
        purpose=ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT,
        suite_hash=candidate["config_semantic_hash"],
        execution_hash=candidate["execution_hash"],
        campaign_cost_control_hash=candidate["cost_control_hash"],
        dataset_manifest_hash=None,
        dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
        schedule_seed=SCHEDULE_SEED,
        schedule_order=order,
        schedule_row_id=row["schedule_row_id"],
        repetition=row["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id=f"run_rapid_v6_{candidate['execution_hash'][7:19]}_{order:02d}",
        provider="openai",
        model_id=MODEL_ID,
        memory_condition=MemoryCondition.NO_MEMORY,
        memory_policy_version=FIXED_BUNDLE_POLICY_VERSION,
        sandbox_backend="docker",
        budget=RUNTIME_BUDGET,
        agent_image_digest=binding["evaluator_image_digest"],
        evaluator_image_digest=binding["evaluator_image_digest"],
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        cache_write_input_price_per_million_usd=0.75,
        output_price_per_million_usd=4.5,
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        experiment_context=experiment,
    )
    payload = manifest.model_dump(mode="python")
    payload["model"]["temperature"] = 0.0
    payload["tool_schema_version"] = row["tool_schema_version"]
    payload["context_policy_version"] = row["context_policy_version"]
    payload["created_at"] = MANIFEST_CREATED_AT
    return RunManifest.model_validate(payload)


def build_rapid_v4_run_manifest(
    candidate: dict[str, Any],
    order: int,
    *,
    repository: str | Path = ".",
) -> RunManifest:
    _validate_candidate(candidate)
    return _build_manifest_unchecked(candidate, order, repository=repository)


def _manifest_matches_projection(
    projection: dict[str, Any],
    manifest: RunManifest,
) -> bool:
    try:
        experiment = manifest.experiment
        assert experiment is not None
        row = next(
            item
            for item in projection["schedule"]
            if item["schedule_row_id"] == experiment.schedule_row_id
        )
        binding = next(
            item
            for item in projection["task_bindings"]
            if item["task_id"] == manifest.task_id
        )
        model = projection["model_contract"]
        cost_control = projection["campaign_cost_control"]
        cost_hash = (
            cost_control["content_hash"]
            if isinstance(cost_control, dict)
            else projection["cost_control_hash"]
        )
        return bool(
            experiment.purpose == ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT
            and experiment.experiment_id == EXPERIMENT_ID
            and experiment.suite_hash == projection["suite_hash"]
            and experiment.execution_hash == projection["execution_hash"]
            and experiment.campaign_cost_control_hash == cost_hash
            and experiment.dataset_role == DatasetRole.MEMORY_DEVELOPMENT
            and experiment.schedule_seed == SCHEDULE_SEED
            and experiment.schedule_order == row["order"]
            and experiment.repetition == row["repetition"]
            and manifest.task_id == row["task_id"] == binding["task_id"]
            and manifest.task_version == row["task_version"] == binding["task_version"] == 1
            and manifest.tool_schema_version == row["tool_schema_version"]
            and manifest.context_policy_version == row["context_policy_version"]
            and manifest.memory.condition == MemoryCondition.NO_MEMORY
            and manifest.memory.index_version is None
            and manifest.memory.index_hash is None
            and manifest.budget == RUNTIME_BUDGET
            and manifest.model.provider == model["provider"]
            and manifest.model.model_id == model["model_id"]
            and manifest.model.provider_sdk_version == model["provider_sdk_version"]
            and manifest.model.reasoning_effort == model["reasoning_effort"]
            and manifest.model.reasoning_mode == model["reasoning_mode"]
            and manifest.model.service_tier == model["service_tier"]
            and manifest.model.transport_max_retries == model["transport_max_retries"]
            and manifest.model.temperature == model["temperature"]
            and manifest.model.max_output_tokens == model["max_output_tokens"]
            and manifest.sandbox_backend == "docker"
            and manifest.evaluator_image_digest == binding["evaluator_image_digest"]
            and manifest.agent_image_digest == binding["evaluator_image_digest"]
            and manifest.public_spec_hash == binding["public_spec_hash"]
            and manifest.private_spec_hash == binding["private_spec_hash"]
            and manifest.base_commit == binding["base_commit"]
        )
    except (AssertionError, KeyError, StopIteration, TypeError, ValueError):
        return False


def _candidate_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite_hash": candidate["config_semantic_hash"],
        "execution_hash": candidate["execution_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "model_contract": candidate["model_contract"],
        "task_bindings": candidate["task_bindings"],
        "schedule": candidate["schedule"],
        "campaign_cost_control": {"content_hash": candidate["cost_control_hash"]},
    }


def _manifest_matches_candidate(candidate: dict[str, Any], manifest: RunManifest) -> bool:
    return _manifest_matches_projection(_candidate_projection(candidate), manifest)


def rapid_v4_registered_plan_matches_manifest(
    *,
    plan: dict[str, Any],
    manifest: RunManifest,
    repository: str | Path = ".",
) -> bool:
    """Pure row match used by the registry during one batch admission."""

    del repository
    return _manifest_matches_projection(plan, manifest)


def _prepare_batch(
    candidate: dict[str, Any],
    *,
    authority_kind: Literal["live", "rehearsal"],
    live_authorization: LiveExecutionAuthorization | None = None,
    repository: str | Path = ".",
) -> PreparedRapidV4Batch:
    """Validate candidate, plan and every manifest exactly once for the batch."""

    _validate_candidate(candidate)
    root = Path(repository).resolve()
    plan = _plan(candidate, approved=True)
    plan_hash = sha256_bytes(_plan_bytes(plan))
    registry = live_verifier_registry()
    plan_decision = registry.validate_authorization_plan(plan)
    if not (
        plan_decision.handled
        and plan_decision.accepted
        and plan_decision.verifier_id == VERIFIER_ID
        and plan_decision.requires_row_capability
    ):
        raise HarnessAdmissionError(
            "Rapid candidate-v6 plan schema is not registered exactly"
        )
    manifests = tuple(
        _build_manifest_unchecked(candidate, order, repository=root) for order in range(1, 9)
    )
    for manifest in manifests:
        decision = registry.verify_manifest(
            plan=plan,
            manifest=manifest,
            authorization_plan_path=(
                live_authorization.plan_path if live_authorization is not None else "<rehearsal>"
            ),
            authorization_plan_hash=plan_hash,
            repository=root,
            runner_root=None,
            batch_validation=True,
        )
        if not decision.accepted or decision.verifier_id != VERIFIER_ID:
            raise HarnessAdmissionError(
                "Rapid candidate-v6 manifest is incompatible with its verifier"
            )
    batch_authorization = issue_batch_execution_authorization(
        authority_kind=authority_kind,
        execution_hash=candidate["execution_hash"],
        plan_hash=plan_hash,
        runtime_build_hash=candidate["runtime_build_hash"],
        schedule_hash=candidate["schedule_hash"],
        cost_control_hash=candidate["cost_control_hash"],
        manifests=manifests,
        live_authorization=live_authorization,
    )
    return PreparedRapidV4Batch(
        plan=plan,
        plan_hash=plan_hash,
        manifests=manifests,
        authorization=batch_authorization,
        verifier_id=VERIFIER_ID,
    )


def _result_bundle_path(candidate: dict[str, Any], root: Path) -> Path:
    return (
        root
        / "reports"
        / "rapid-development"
        / f"{EXPERIMENT_ID}-{candidate['execution_hash'][7:19]}.jsonl"
    )


def _batch_started_event(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA,
        "event": "batch-started",
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "candidate_content_hash": candidate["content_hash"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "schedule_hash": candidate["schedule_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "verifier_registry_hash": live_verifier_registry().content_hash,
        "full_schedule_reserve_nanos": FULL_SCHEDULE_RESERVE_NANOS,
        "hard_cap_nanos": HARD_CAP_NANOS,
    }


def _seal_event(event: dict[str, Any], previous: str | None) -> dict[str, Any]:
    body = {**event, "previous_event_hash": previous}
    return {**body, "content_hash": sha256_json(body)}


def _rehearsed_resolved_terminal(
    candidate: dict[str, Any],
    previous: str,
) -> dict[str, Any]:
    """Project the normal row shape needed to exercise the inter-row gate."""

    schedule_row = candidate["schedule"][0]
    return _seal_event(
        {
            "schema_version": RESULT_SCHEMA,
            "event": "row-terminal",
            **schedule_row,
            "run_id": (
                f"run_rapid_v6_{candidate['execution_hash'][7:19]}_01"
            ),
            "agent_started": True,
            "harness_admission_failure": False,
            "evaluator_reached": True,
            "token_terminal": False,
            "submission_completed": True,
            "success_at_budget": True,
            "outcome_kind": RunOutcomeKind.RESOLVED.value,
            "usage": Usage().model_dump(mode="json"),
            "model_cost_nanos": 0,
            "runtime_result_official": True,
            "bundle_official": False,
            "error_type": None,
            "error_code": None,
            "error_message": None,
        },
        previous,
    )


def _active_bundle_next_order_from_events(
    candidate: dict[str, Any],
    events: list[dict[str, Any]],
) -> int | None:
    if not events:
        return None
    previous: str | None = None
    for event in events:
        if type(event) is not dict or type(event.get("content_hash")) is not str:
            return None
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if body.get("previous_event_hash") != previous or event["content_hash"] != sha256_json(
            body
        ):
            return None
        previous = event["content_hash"]
    expected_start = {**_batch_started_event(candidate), "previous_event_hash": None}
    first_body = {key: value for key, value in events[0].items() if key != "content_hash"}
    if first_body != expected_start or len(events) > len(candidate["schedule"]):
        return None
    for index, event in enumerate(events[1:]):
        schedule_row = candidate["schedule"][index]
        expected_run_id = (
            f"run_rapid_v6_{candidate['execution_hash'][7:19]}_{schedule_row['order']:02d}"
        )
        if (
            event.get("schema_version") != RESULT_SCHEMA
            or event.get("event") != "row-terminal"
            or event.get("bundle_official") is not False
            or type(event.get("runtime_result_official")) is not bool
            or event.get("run_id") != expected_run_id
            or event.get("harness_admission_failure") is not False
            or event.get("outcome_kind")
            not in {
                RunOutcomeKind.RESOLVED.value,
                RunOutcomeKind.TASK_FAILURE.value,
                RunOutcomeKind.AGENT_FAILURE.value,
            }
            or any(event.get(key) != value for key, value in schedule_row.items())
        ):
            return None
    return len(events)


def _active_bundle_next_order(candidate: dict[str, Any], root: Path) -> int | None:
    path = _result_bundle_path(candidate, root)
    if path.is_symlink() or not path.is_file():
        return None
    try:
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, TypeError, ValueError):
        return None
    return _active_bundle_next_order_from_events(candidate, events)


def _write_or_validate_plan(candidate: dict[str, Any], root: Path) -> Path:
    plan = _plan(candidate, approved=True)
    raw = _plan_bytes(plan)
    path = (
        root
        / ".patchloop"
        / "experiments"
        / "plans"
        / f"{candidate['execution_hash'].removeprefix('sha256:')}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ContractError(
                "Rapid candidate-v6 approved plan path contains different bytes"
            ) from None
    return path


def _rehearsal_body(
    candidate: dict[str, Any],
    prepared: PreparedRapidV4Batch,
    first_boundary: dict[str, Any],
    transition: dict[str, Any],
    second_boundary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REHEARSAL_SCHEMA,
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "candidate_content_hash": candidate["content_hash"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "config_file_sha256": candidate["config_file_sha256"],
        "schedule_hash": candidate["schedule_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "plan_hash": prepared.plan_hash,
        "plan_schema": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "verifier_id": prepared.verifier_id,
        "verifier_registry_hash": live_verifier_registry().content_hash,
        "verified_manifest_count": len(prepared.manifests),
        "stage_sequence": list(_REHEARSAL_STAGE_SEQUENCE),
        "first_provider_boundary": first_boundary,
        "inter_row_transition": transition,
        "second_provider_boundary": second_boundary,
        "stopped_before": "second-provider-dispatch-after-resolved-prefix",
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "task_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "harness_admission_failures": 0,
    }


def rehearsal_bytes(receipt: dict[str, Any]) -> bytes:
    body = {key: value for key, value in receipt.items() if key != "content_hash"}
    if receipt.get("content_hash") != sha256_json(body):
        raise RecoveryError("Rapid candidate-v6 rehearsal content hash differs")
    return (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def rehearse_rapid_public_development_v4(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Walk the production admission sequence and stop at provider dispatch."""

    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    candidate = load_rapid_public_development_v4_candidate(root)
    prepared = _prepare_batch(candidate, authority_kind="rehearsal", repository=root)
    start = _seal_event(_batch_started_event(candidate), None)
    next_order = _active_bundle_next_order_from_events(candidate, [start])
    if next_order != 1:
        raise HarnessAdmissionError(
            "Rapid candidate-v6 rehearsal batch prefix is incompatible"
        )
    first = prepared.manifests[0]
    row_authorization = issue_row_execution_authorization(
        prepared.authorization,
        first,
        active_schedule_order=next_order,
    )
    first_boundary = AgentRunner.rehearse_provider_dispatch(first, row_authorization)
    first_terminal = _rehearsed_resolved_terminal(candidate, start["content_hash"])
    second_order = _active_bundle_next_order_from_events(
        candidate,
        [start, first_terminal],
    )
    if second_order != 2:
        raise HarnessAdmissionError(
            "Rapid candidate-v6 rehearsal inter-row prefix is incompatible"
        )
    second = prepared.manifests[1]
    second_authorization = issue_row_execution_authorization(
        prepared.authorization,
        second,
        active_schedule_order=second_order,
    )
    second_boundary = AgentRunner.rehearse_provider_dispatch(
        second,
        second_authorization,
    )
    transition = {
        "prior_terminal_content_hash": first_terminal["content_hash"],
        "prior_outcome_kind": first_terminal["outcome_kind"],
        "prior_runtime_result_official": first_terminal["runtime_result_official"],
        "prior_bundle_official": first_terminal["bundle_official"],
        "next_schedule_order": second_order,
    }
    body = _rehearsal_body(
        candidate,
        prepared,
        first_boundary,
        transition,
        second_boundary,
    )
    receipt = {**body, "content_hash": sha256_json(body)}
    output = ensure_within(root, REHEARSAL_PATH.as_posix())
    if output.exists():
        existing = load_rapid_public_development_v4_rehearsal(candidate, repository=root)
        if existing != receipt:
            raise RecoveryError(
                "Rapid candidate-v6 rehearsal receipt differs from current contracts"
            )
        return existing
    _write_once(output, rehearsal_bytes(receipt))
    return load_rapid_public_development_v4_rehearsal(candidate, repository=root)


def load_rapid_public_development_v4_rehearsal(
    candidate: dict[str, Any],
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    path = ensure_within(root, REHEARSAL_PATH.as_posix())
    if path.is_symlink() or not path.is_file():
        raise HarnessAdmissionError(
            "Rapid candidate-v6 requires its exact no-call rehearsal receipt"
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessAdmissionError("Rapid candidate-v6 rehearsal receipt is invalid") from exc
    if type(receipt) is not dict:
        raise HarnessAdmissionError(
            "Rapid candidate-v6 rehearsal receipt must be an object"
        )
    plan = _plan(candidate, approved=True)
    first_boundary = receipt.get("first_provider_boundary")
    transition = receipt.get("inter_row_transition")
    second_boundary = receipt.get("second_provider_boundary")
    start = _seal_event(_batch_started_event(candidate), None)
    first_terminal = _rehearsed_resolved_terminal(candidate, start["content_hash"])
    expected_transition = {
        "prior_terminal_content_hash": first_terminal["content_hash"],
        "prior_outcome_kind": RunOutcomeKind.RESOLVED.value,
        "prior_runtime_result_official": True,
        "prior_bundle_official": False,
        "next_schedule_order": 2,
    }
    expected = {
        "schema_version": REHEARSAL_SCHEMA,
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "candidate_content_hash": candidate["content_hash"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "config_file_sha256": candidate["config_file_sha256"],
        "schedule_hash": candidate["schedule_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "plan_hash": sha256_bytes(_plan_bytes(plan)),
        "plan_schema": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "verifier_id": VERIFIER_ID,
        "verifier_registry_hash": live_verifier_registry().content_hash,
        "verified_manifest_count": 8,
        "stage_sequence": list(_REHEARSAL_STAGE_SEQUENCE),
        "stopped_before": "second-provider-dispatch-after-resolved-prefix",
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "task_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "harness_admission_failures": 0,
    }
    body = {key: value for key, value in receipt.items() if key != "content_hash"}
    valid_first_boundary = bool(
        isinstance(first_boundary, dict)
        and first_boundary.get("stage") == "provider-dispatch-boundary"
        and first_boundary.get("provider_dispatch_blocked") is True
        and first_boundary.get("execution_hash") == candidate["execution_hash"]
        and first_boundary.get("schedule_order") == 1
        and first_boundary.get("schedule_row_id")
        == candidate["schedule"][0]["schedule_row_id"]
        and first_boundary.get("run_id")
        == f"run_rapid_v6_{candidate['execution_hash'][7:19]}_01"
    )
    valid_second_boundary = bool(
        isinstance(second_boundary, dict)
        and second_boundary.get("stage") == "provider-dispatch-boundary"
        and second_boundary.get("provider_dispatch_blocked") is True
        and second_boundary.get("execution_hash") == candidate["execution_hash"]
        and second_boundary.get("schedule_order") == 2
        and second_boundary.get("schedule_row_id")
        == candidate["schedule"][1]["schedule_row_id"]
        and second_boundary.get("run_id")
        == f"run_rapid_v6_{candidate['execution_hash'][7:19]}_02"
    )
    comparable = {
        key: value
        for key, value in body.items()
        if key
        not in {
            "first_provider_boundary",
            "inter_row_transition",
            "second_provider_boundary",
        }
    }
    if (
        not valid_first_boundary
        or transition != expected_transition
        or not valid_second_boundary
        or comparable != expected
        or receipt.get("content_hash") != sha256_json(body)
        or rehearsal_bytes(receipt) != path.read_bytes()
    ):
        raise HarnessAdmissionError(
            "Rapid candidate-v6 rehearsal receipt does not bind current contracts"
        )
    return receipt


def _row_started(runner: AgentRunner, run_id: str) -> bool:
    try:
        return any(
            event.type == EventType.RUN_STARTED for event in runner.state.list_events(run_id)
        )
    except Exception:
        return False


def _rapid_v4_row_projection(
    *,
    schedule_row: dict[str, Any],
    manifest: RunManifest,
    result: dict[str, Any] | None,
    runner: AgentRunner,
    error: Exception | None,
) -> dict[str, Any]:
    agent_started = _row_started(runner, manifest.run_id) or result is not None
    admission_failure = bool(
        error is not None and isinstance(error, ContractError) and not agent_started
    )
    if admission_failure:
        message = " ".join(str(error).split())
        return {
            **schedule_row,
            "run_id": manifest.run_id,
            "agent_started": False,
            "harness_admission_failure": True,
            "evaluator_reached": False,
            "token_terminal": False,
            "submission_completed": False,
            "success_at_budget": False,
            "outcome_kind": HARNESS_ADMISSION_FAILURE,
            "usage": Usage().model_dump(mode="json"),
            "model_cost_nanos": 0,
            "runtime_result_official": None,
            "bundle_official": False,
            "error_type": type(error).__name__,
            "error_code": getattr(error, "code", "CONTRACT_ERROR"),
            "error_message": message if 0 < len(message) <= 500 else None,
        }
    projected = _row_projection(
        schedule_row=schedule_row,
        result=result,
        runner=runner,
        error=error,
    )
    return {
        **projected,
        "run_id": manifest.run_id,
        "agent_started": agent_started,
        "harness_admission_failure": False,
        "error_code": getattr(error, "code", None) if error is not None else None,
    }


def run_rapid_public_development_v4(
    config_path: str | Path = CONFIG_PATH,
    *,
    approve_live_cost: bool,
    approved_execution_hash: str | None,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Run the rehearsed hard panel only after exact hash-and-cap approval."""

    root = Path(repository).resolve()
    _read_config(config_path, root)
    candidate = load_rapid_public_development_v4_candidate(root)
    bundle_path = _result_bundle_path(candidate, root)
    if bundle_path.exists() or bundle_path.is_symlink():
        raise ContractError("Rapid candidate-v6 execution is consumed and cannot be retried")
    if not approve_live_cost or approved_execution_hash != candidate["execution_hash"]:
        raise ContractError(
            "Rapid candidate-v6 live execution requires its exact hash and cost-cap approval"
        )
    load_rapid_public_development_v4_rehearsal(candidate, repository=root)

    _write_or_validate_plan(candidate, root)
    live_authorization = issue_live_execution_authorization(
        candidate["execution_hash"],
        root=root / ".patchloop",
    )
    prepared = _prepare_batch(
        candidate,
        authority_kind="live",
        live_authorization=live_authorization,
        repository=root,
    )
    if not os.environ.get("OPENAI_API_KEY"):
        raise ContractError("Rapid candidate-v6 live execution requires OPENAI_API_KEY")
    if not DockerSandbox.available():
        raise ContractError(
            "Rapid candidate-v6 live execution requires the local Docker daemon"
        )
    for binding in candidate["task_bindings"]:
        if (
            DockerSandbox(binding["evaluator_image"]).image_identity()
            != binding["evaluator_image_digest"]
        ):
            raise ContractError(
                "Rapid candidate-v6 evaluator image is unavailable: "
                f"{binding['task_id']}"
            )
    _append_bundle_event(bundle_path, _batch_started_event(candidate), create=True)

    runner = AgentRunner(root / ".patchloop")
    rows: list[dict[str, Any]] = []
    accrued_nanos = 0
    halted_reason: str | None = None
    for schedule_row, manifest in zip(
        candidate["schedule"], prepared.manifests, strict=True
    ):
        if halted_reason is not None:
            _append_bundle_event(
                bundle_path,
                {
                    "schema_version": RESULT_SCHEMA,
                    "event": "row-not-started",
                    "official": False,
                    **schedule_row,
                    "reason": halted_reason,
                },
            )
            continue
        result: dict[str, Any] | None = None
        error: Exception | None = None
        try:
            active_order = _active_bundle_next_order(candidate, root)
            if active_order is None:
                raise HarnessAdmissionError(
                    "Rapid candidate-v6 active bundle prefix is invalid"
                )
            if active_order != schedule_row["order"]:
                raise HarnessAdmissionError(
                    "Rapid candidate-v6 active bundle row order differs"
                )
            row_authorization = issue_row_execution_authorization(
                prepared.authorization,
                manifest,
                active_schedule_order=active_order,
            )
            result = runner.start(
                schedule_row["task"],
                model="openai",
                memory_condition=MemoryCondition.NO_MEMORY,
                manifest=manifest,
                live_authorization=live_authorization,
                row_execution_authorization=row_authorization,
            )
        except Exception as exc:  # terminal projection preserves the exact failure
            error = exc
            result = _persisted_result(runner, manifest.run_id)
        projected = _rapid_v4_row_projection(
            schedule_row=schedule_row,
            manifest=manifest,
            result=result,
            runner=runner,
            error=error,
        )
        accrued_nanos += projected["model_cost_nanos"]
        if accrued_nanos > HARD_CAP_NANOS:
            raise ContractError(
                "Rapid candidate-v6 observed cost exceeds the approved hard cap"
            )
        _append_bundle_event(
            bundle_path,
            {"schema_version": RESULT_SCHEMA, "event": "row-terminal", **projected},
        )
        rows.append(projected)
        if projected["harness_admission_failure"]:
            halted_reason = "prior-harness-admission-failure"
        elif projected["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value:
            halted_reason = "prior-infrastructure-terminal"

    agent_rows_started = sum(bool(row["agent_started"]) for row in rows)
    agent_failures = sum(
        row["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value for row in rows
    )
    harness_failures = sum(bool(row["harness_admission_failure"]) for row in rows)
    summary = {
        "schema_version": RESULT_SCHEMA,
        "event": "batch-completed",
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "attempted_rows": len(rows),
        "started_rows": agent_rows_started,
        "agent_rows_started": agent_rows_started,
        "harness_admission_failures": harness_failures,
        "agent_failures": agent_failures,
        "agent_failure_rate": (
            agent_failures / agent_rows_started if agent_rows_started else None
        ),
        "evaluator_reached": sum(row["evaluator_reached"] for row in rows),
        "token_terminals": sum(row["token_terminal"] for row in rows),
        "submissions_completed": sum(row["submission_completed"] for row in rows),
        "successes_at_budget": sum(row["success_at_budget"] for row in rows),
        "model_calls": sum(row["usage"]["model_calls"] for row in rows),
        "tool_calls": sum(row["usage"]["tool_calls"] for row in rows),
        "model_cost_nanos": accrued_nanos,
        "result_bundle": bundle_path.relative_to(root).as_posix(),
        "external_claim_authorized": False,
        "confirmatory_promotion_automatic": False,
    }
    return _append_bundle_event(bundle_path, summary)


__all__ = [
    "CANDIDATE_PATH",
    "CONFIG_PATH",
    "EXPERIMENT_ID",
    "HARNESS_ADMISSION_FAILURE",
    "REHEARSAL_PATH",
    "RapidPublicDevelopmentV3Config",
    "build_rapid_public_development_v4_candidate",
    "build_rapid_v4_run_manifest",
    "load_rapid_public_development_v4_candidate",
    "load_rapid_public_development_v4_rehearsal",
    "materialize_rapid_public_development_v4_candidate",
    "rapid_v4_registered_plan_matches_manifest",
    "rehearse_rapid_public_development_v4",
    "run_rapid_public_development_v4",
]
