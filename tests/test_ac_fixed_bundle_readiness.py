from __future__ import annotations

import copy
import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from patchloop import runtime as runtime_module
from patchloop.agent.model import SYSTEM_PROMPT_V3
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    DatasetRole,
    EventType,
    ExperimentRunContext,
    MemoryCondition,
    RunEvent,
)
from patchloop.errors import ContractError
from patchloop.evals import budget as budget_module
from patchloop.evals import qualification
from patchloop.evals import runner as eval_runner
from patchloop.memory import fixed_bundle
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text

SUITE_PATH = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r1.yaml")
HISTORICAL_SUITE_PATH = Path("experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml")
HISTORICAL_SUITE_HASH = "sha256:e4e653acf808881cb5ebb2104f9da67b0487ceb0df67a6bcc27160354d93fc67"
SOURCE_COMMIT = "a" * 40
SDK_VERSION = "offline-test-sdk"


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"{label} is forbidden in the offline A/C readiness tests")

    return fail


@pytest.fixture
def ac_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[eval_runner.ExperimentSuite, dict[str, Any]]:
    """Build the source preflight without Docker, SDK, network, or live calls."""

    monkeypatch.setenv("OPENAI_API_KEY", "offline-placeholder-not-used")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 8, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": SOURCE_COMMIT, "clean": True},
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
        lambda: {"installed": True, "version": SDK_VERSION},
    )
    monkeypatch.setattr(
        eval_runner,
        "latest_frozen_index",
        _forbidden("legacy latest_frozen_index"),
    )
    monkeypatch.setattr(runtime_module, "git_commit", lambda: SOURCE_COMMIT)
    monkeypatch.setattr(runtime_module, "version", lambda _package: SDK_VERSION)
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        _forbidden("network connection"),
    )

    class ForbiddenRunner:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("AgentRunner construction is forbidden in source preflight")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)

    suite = eval_runner.load_suite(SUITE_PATH)
    preflight = eval_runner.preflight_suite(SUITE_PATH)
    return suite, preflight


def _manifest_for_row(
    suite: eval_runner.ExperimentSuite,
    preflight: dict[str, Any],
    row_index: int,
):
    schedule_row = preflight["schedule"][row_index]
    task_row = next(row for row in preflight["tasks"] if row["task_id"] == schedule_row["task_id"])
    item = {**task_row, **schedule_row}
    task_path = Path(item["task"])
    package = load_task_package(task_path.parent if task_path.is_file() else task_path)
    evaluator_digest = item["evaluator_image_digest"]
    experiment = ExperimentRunContext(
        experiment_id=suite.experiment_id,
        purpose=suite.purpose,
        suite_hash=preflight["suite_hash"],
        execution_hash=preflight["execution_hash"],
        dataset_manifest_hash=preflight["dataset"]["manifest_hash"],
        dataset_role=DatasetRole(item["dataset_role"]),
        schedule_seed=suite.seed,
        schedule_order=item["order"],
        schedule_row_id=item["schedule_row_id"],
        repetition=item["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id=f"run_ac_readiness_row_{row_index + 1}",
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(item["condition"]),
        memory_policy_version=suite.memory_policy_version or "v1",
        sandbox_backend="docker",
        budget=suite.budget,
        agent_image_digest=evaluator_digest,
        evaluator_image_digest=evaluator_digest,
        input_price_per_million_usd=suite.input_price_per_million_usd,
        cached_input_price_per_million_usd=(suite.cached_input_price_per_million_usd),
        cache_write_input_price_per_million_usd=(suite.cache_write_input_price_per_million_usd),
        output_price_per_million_usd=suite.output_price_per_million_usd,
        reasoning_effort=suite.reasoning_effort,
        reasoning_mode=suite.reasoning_mode,
        service_tier=suite.service_tier,
        transport_max_retries=suite.transport_max_retries,
        max_output_tokens=suite.max_output_tokens,
        experiment_context=experiment,
    )
    return manifest, item


def _request_trace(
    root: Path,
    manifest,
    *,
    context_sequence: int = 1,
) -> list[RunEvent]:
    delivery = fixed_bundle.build_fixed_memory_delivery(condition=manifest.memory.condition)
    rendered_context = json.dumps(
        {
            "task": manifest.task_id,
            "selected_memory": delivery.text or None,
        },
        indent=2,
        ensure_ascii=False,
    )
    request_body = {
        "model": manifest.model.model_id,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT_V3},
            {"role": "user", "content": rendered_context},
        ],
        "tools": TOOL_SCHEMAS_V2,
        "store": False,
        "reasoning": {"effort": manifest.model.reasoning_effort},
        "service_tier": manifest.model.service_tier,
        "max_output_tokens": manifest.model.max_output_tokens,
        "truncation": "disabled",
    }
    request_hash = sha256_text(canonical_json(request_body))
    if manifest.memory.condition == MemoryCondition.STRUCTURED:
        normalized_context = json.dumps(
            {"task": manifest.task_id, "selected_memory": None},
            indent=2,
            ensure_ascii=False,
        )
        normalized_request = copy.deepcopy(request_body)
        normalized_request["input"][1]["content"] = normalized_context
        normalized_hash = sha256_text(canonical_json(normalized_request))
    else:
        normalized_hash = request_hash
    request_evidence = fixed_bundle.FixedMemoryRequestEvidence(
        delivery=delivery.evidence,
        delivery_evidence_sha256=delivery.evidence_sha256,
        request_body_sha256=request_hash,
        normalized_no_memory_request_body_sha256=normalized_hash,
    )
    artifact_payload = {
        "schema_version": "model-request-evidence-v1",
        "provider": manifest.model.provider,
        "endpoint": "/v1/responses",
        "request_body": request_body,
        "request_body_hash": request_hash,
        "context_build": {},
        "fixed_memory_delivery": request_evidence.model_dump(mode="json"),
    }
    fixed_bundle.validate_fixed_memory_request_artifact(artifact_payload)
    artifact = ArtifactStore(root / "artifacts").put_json(artifact_payload)
    context_payload = {
        "context_hash": sha256_text(rendered_context),
        "context_characters": len(rendered_context),
        "context_bytes": len(rendered_context.encode("utf-8")),
        "request_body_hash": request_hash,
        "artifact_id": artifact.artifact_id,
        "artifact_path": artifact.path,
        "artifact_role": "model-request-evidence",
        "provider_state_used": False,
        "memory_delivery_policy_version": fixed_bundle.FIXED_BUNDLE_POLICY_VERSION,
        "memory_delivery_evidence_sha256": delivery.evidence_sha256,
        "memory_delivery_entry_count": delivery.evidence.entry_count,
        "memory_delivery_bundle_sha256": delivery.evidence.bundle_sha256,
        "normalized_no_memory_request_body_sha256": normalized_hash,
    }
    timestamp = datetime(2026, 8, 8, 0, tzinfo=UTC)
    return [
        RunEvent(
            event_id=f"evt_context_{context_sequence}",
            run_id=manifest.run_id,
            sequence=context_sequence,
            type=EventType.CONTEXT_BUILT,
            timestamp=timestamp,
            actor="context-builder",
            payload=context_payload,
        ),
        RunEvent(
            event_id=f"evt_consumer_{context_sequence + 1}",
            run_id=manifest.run_id,
            sequence=context_sequence + 1,
            type=EventType.MODEL_GENERATION_BLOCKED,
            timestamp=timestamp,
            actor="budget-guard",
            payload={
                "request_artifact_id": artifact.artifact_id,
                "request_artifact_path": artifact.path,
                "request_artifact_hash": artifact.content_hash,
                "request_body_hash": request_hash,
                "reason_code": "offline-test-boundary",
            },
        ),
    ]


def test_exact_source_preflight_binds_schedule_bundle_and_cost_but_stays_closed(
    ac_source: tuple[eval_runner.ExperimentSuite, dict[str, Any]],
) -> None:
    suite, preflight = ac_source

    assert eval_runner._is_ac_fixed_bundle_readiness_profile(suite)
    assert [
        (row["order"], row["task_id"], row["condition"], row["repetition"])
        for row in preflight["schedule"]
    ] == [
        (1, "moto-query-scanned-count", "no_memory", 1),
        (2, "moto-query-scanned-count", "structured", 1),
        (3, "babel-strict-grouped-decimal-trailing-zeroes", "structured", 1),
        (4, "babel-strict-grouped-decimal-trailing-zeroes", "no_memory", 1),
    ]
    runtime = preflight["runtime_contract"]
    assert runtime["schema_version"] == eval_runner.AC_FIXED_BUNDLE_RUNTIME_CONTRACT_SCHEMA
    assert runtime["memory_policy_version"] == "fixed-d110-bundle-v1"
    assert runtime["fixed_bundle"]["bundle_sha256"] == fixed_bundle.FIXED_BUNDLE_SHA256
    assert runtime["fixed_bundle"]["d110_index_content_hash"] == (
        fixed_bundle.D110_INDEX_CONTENT_HASH
    )
    assert runtime["full_schedule_cost_policy"] == eval_runner.AC_FIXED_BUNDLE_COST_POLICY
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == 13.6125
    assert preflight["pricing"]["budget_upper_bound_usd"] == 54.45
    assert "campaign_cost_control" not in preflight

    blocker_codes = {blocker["code"] for blocker in preflight["blockers"]}
    assert preflight["ready"] is False
    assert {
        "PRICING_DATE_MISSING",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
        "AC_FULL_SCHEDULE_COST_CONTROL_PENDING",
    } <= blocker_codes
    assert "FROZEN_MEMORY_INDEX_MISSING" not in blocker_codes
    assert "FROZEN_MEMORY_INDEX_INVALID" not in blocker_codes
    assert "GIT_WORKTREE_DIRTY" not in blocker_codes
    assert "DOCKER_UNAVAILABLE" not in blocker_codes
    assert "OPENAI_SDK_MISSING" not in blocker_codes


def test_all_four_manifests_bind_exact_a_c_rows_and_budget_pressure(
    ac_source: tuple[eval_runner.ExperimentSuite, dict[str, Any]],
) -> None:
    suite, preflight = ac_source

    for row_index in range(4):
        manifest, item = _manifest_for_row(suite, preflight, row_index)
        eval_runner._assert_manifest_matches_preflight(
            manifest,
            suite=suite,
            preflight=preflight,
            item=item,
        )
        assert AgentRunner._is_ac_fixed_bundle_readiness_manifest(manifest)
        assert qualification._ac_fixed_bundle_readiness_manifest_matches(manifest)
        expected_index = (
            (None, None)
            if manifest.memory.condition == MemoryCondition.NO_MEMORY
            else (fixed_bundle.D110_INDEX_VERSION, fixed_bundle.D110_INDEX_CONTENT_HASH)
        )
        assert (manifest.memory.index_version, manifest.memory.index_hash) == expected_index

        diagnostic = budget_module.calculate_budget_pressure(manifest, [])
        assert diagnostic["configured_limits"] == {
            "model_calls": None,
            "tool_calls": None,
            "total_tokens": 3_000_000,
            "wall_clock_ms": 3_600_000,
        }
        assert diagnostic["binding_dimension"] == "none"


def test_manifest_and_suite_tamper_fail_closed_and_legacy_hash_is_stable(
    ac_source: tuple[eval_runner.ExperimentSuite, dict[str, Any]],
) -> None:
    suite, preflight = ac_source
    manifest, item = _manifest_for_row(suite, preflight, 0)
    tampered_manifest = manifest.model_copy(
        update={
            "memory": manifest.memory.model_copy(
                update={
                    "index_version": fixed_bundle.D110_INDEX_VERSION,
                    "index_hash": fixed_bundle.D110_INDEX_CONTENT_HASH,
                }
            )
        }
    )
    assert not AgentRunner._is_ac_fixed_bundle_readiness_manifest(tampered_manifest)
    assert not qualification._ac_fixed_bundle_readiness_manifest_matches(tampered_manifest)
    with pytest.raises(ContractError, match="approved execution plan"):
        eval_runner._assert_manifest_matches_preflight(
            tampered_manifest,
            suite=suite,
            preflight=preflight,
            item=item,
        )

    source_payload = yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))
    source_payload["schedule"][2]["condition"] = "no_memory"
    with pytest.raises(ValidationError, match="exact four-row A/C readiness profile"):
        eval_runner.ExperimentSuite.model_validate(source_payload)

    selector_tamper = suite.model_copy(update={"cost_limit_usd": 54.99})
    assert not eval_runner._is_ac_fixed_bundle_readiness_profile(selector_tamper)

    historical = eval_runner.load_suite(HISTORICAL_SUITE_PATH)
    historical_payload = eval_runner._suite_payload(historical)
    assert "schedule" not in historical.model_dump(mode="json")
    assert "memory_policy_version" not in historical.model_dump(mode="json")
    assert "schedule" not in historical_payload
    assert "memory_policy_version" not in historical_payload
    assert eval_runner._suite_hash(historical) == HISTORICAL_SUITE_HASH


@pytest.mark.parametrize(
    ("row_index", "expected_count", "expected_normalized_equal"),
    [(0, 0, True), (1, 3, False)],
)
def test_fixed_delivery_qualifier_replays_a_and_c_happy_paths(
    ac_source: tuple[eval_runner.ExperimentSuite, dict[str, Any]],
    tmp_path: Path,
    row_index: int,
    expected_count: int,
    expected_normalized_equal: bool,
) -> None:
    suite, preflight = ac_source
    manifest, _ = _manifest_for_row(suite, preflight, row_index)
    events = _request_trace(tmp_path, manifest)

    passed, details = qualification._fixed_memory_delivery_evidence(
        root=tmp_path,
        manifest=manifest,
        events=events,
    )

    assert passed is True, details
    assert details["context_request_count"] == 1
    assert details["consumer_count"] == 1
    assert details["replayed_request_count"] == 1
    assert details["entry_counts"] == [expected_count]
    assert details["normalized_request_equalities"] == [expected_normalized_equal]
    assert details["retrieval_event_count"] == 0
    assert details["memory_text_persisted_in_summary"] is False


def test_fixed_delivery_qualifier_rejects_retrieval_and_context_tamper(
    ac_source: tuple[eval_runner.ExperimentSuite, dict[str, Any]],
    tmp_path: Path,
) -> None:
    suite, preflight = ac_source
    manifest, _ = _manifest_for_row(suite, preflight, 1)
    exact_events = _request_trace(tmp_path, manifest)
    timestamp = datetime(2026, 8, 8, 0, tzinfo=UTC)
    retrieval_events = [
        *exact_events,
        RunEvent(
            event_id="evt_forbidden_retrieval",
            run_id=manifest.run_id,
            sequence=3,
            type=EventType.MEMORY_RETRIEVED,
            timestamp=timestamp,
            actor="memory",
            payload={},
        ),
    ]

    passed, details = qualification._fixed_memory_delivery_evidence(
        root=tmp_path,
        manifest=manifest,
        events=retrieval_events,
    )
    assert passed is False
    assert details["retrieval_event_count"] == 1

    context = exact_events[0]
    tampered_payload = dict(context.payload)
    tampered_payload["memory_delivery_entry_count"] = 2
    tampered_events = [
        context.model_copy(update={"payload": tampered_payload}),
        exact_events[1],
    ]
    passed, details = qualification._fixed_memory_delivery_evidence(
        root=tmp_path,
        manifest=manifest,
        events=tampered_events,
    )
    assert passed is False
    assert details["failed_context_sequences"] == [1]
    assert details["replayed_request_count"] == 0


def test_fixed_delivery_qualifier_rejects_ambiguous_consumer_reuse(
    ac_source: tuple[eval_runner.ExperimentSuite, dict[str, Any]],
    tmp_path: Path,
) -> None:
    suite, preflight = ac_source
    manifest, _ = _manifest_for_row(suite, preflight, 1)
    context, consumer = _request_trace(tmp_path, manifest)
    duplicate_context = context.model_copy(update={"event_id": "evt_context_reused", "sequence": 2})
    first_consumer = consumer.model_copy(update={"sequence": 3})
    duplicate_consumer = consumer.model_copy(
        update={"event_id": "evt_consumer_reused", "sequence": 4}
    )

    passed, details = qualification._fixed_memory_delivery_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[context, duplicate_context, first_consumer, duplicate_consumer],
    )

    assert passed is False
    assert details["context_request_count"] == 2
    assert details["consumer_count"] == 2
    assert details["failed_context_sequences"] == [1, 2]
    assert details["matched_consumer_sequences"] == []


def test_terminal_qualifier_routes_ac_checks_and_keeps_legacy_inverse(
    ac_source: tuple[eval_runner.ExperimentSuite, dict[str, Any]],
    tmp_path: Path,
) -> None:
    suite, preflight = ac_source
    manifest, item = _manifest_for_row(suite, preflight, 0)
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    state.append_event(
        manifest.run_id,
        EventType.RUN_STARTED,
        actor="runner",
        payload={},
    )
    state.append_event(
        manifest.run_id,
        EventType.RUN_FAILED,
        actor="runner",
        payload={
            "error_type": "OfflineClosedBoundary",
            "message": "synthetic terminal used only to exercise check routing",
        },
    )
    ac_qualification = qualification.qualify_run(
        manifest.run_id,
        task_dir=Path(item["task"]).parent,
        root=tmp_path,
        persist=False,
    )
    ac_check_ids = {check["check_id"] for check in ac_qualification["checks"]}
    assert {
        "fixed_memory_delivery_integrity",
        "ac_fixed_runtime_contract",
        "disabled_call_guard_contract",
        "pricing_start_freshness",
    } <= ac_check_ids
    assert "no_memory_boundary" not in ac_check_ids
    assert ac_qualification["task_id"] == manifest.task_id
    summary = eval_runner._terminal_qualification_summary(ac_qualification)
    assert summary["task_id"] == manifest.task_id
    assert {
        "fixed_memory_delivery_integrity",
        "ac_fixed_runtime_contract",
        "disabled_call_guard_contract",
        "pricing_start_freshness",
    } <= set(summary["readiness_checks"])

    legacy_root = tmp_path / "legacy"
    task_path = Path(item["task"])
    package = load_task_package(task_path.parent)
    evaluator_digest = package.environment.image_digest
    legacy_manifest = build_manifest(
        package,
        run_id="run_ac_readiness_legacy_inverse",
        provider="openai",
        model_id=suite.model_id,
        sandbox_backend="docker",
        agent_image_digest=evaluator_digest,
        evaluator_image_digest=evaluator_digest,
    )
    legacy_state = StateStore(legacy_root / "state.sqlite3")
    legacy_state.create_run(legacy_manifest)
    legacy_state.append_event(
        legacy_manifest.run_id,
        EventType.RUN_STARTED,
        actor="runner",
        payload={},
    )
    legacy_state.append_event(
        legacy_manifest.run_id,
        EventType.RUN_FAILED,
        actor="runner",
        payload={
            "error_type": "OfflineClosedBoundary",
            "message": "synthetic legacy terminal used only to exercise routing",
        },
    )
    legacy_qualification = qualification.qualify_run(
        legacy_manifest.run_id,
        task_dir=task_path.parent,
        root=legacy_root,
        persist=False,
    )
    legacy_check_ids = {check["check_id"] for check in legacy_qualification["checks"]}
    assert "no_memory_boundary" in legacy_check_ids
    assert {
        "fixed_memory_delivery_integrity",
        "ac_fixed_runtime_contract",
        "disabled_call_guard_contract",
        "pricing_start_freshness",
    }.isdisjoint(legacy_check_ids)
