from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.context import (
    RECENT_EVENT_LIMIT,
    REVIEW_EVIDENCE_SCHEMA,
    TOOL_RESULT_CHARACTER_LIMIT,
    build_context,
    build_context_with_evidence,
)
from patchloop.agent.review import (
    normalize_public_issue_text,
    public_review_contract_content_hash,
    public_review_requirement_id,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Budget,
    Checkpoint,
    EventType,
    Phase,
    PublicReviewContract,
    RegisteredProbeProfile,
    RunEvent,
)
from patchloop.errors import RecoveryError
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text, utc_now


def _public_review_contract(task) -> PublicReviewContract:
    excerpt = normalize_public_issue_text(task.issue.description)
    payload = {
        "schema_version": "public-review-contract-v1",
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_spec_hash": sha256_text(canonical_json(task.model_dump(mode="json"))),
        "requirements": [
            {
                "requirement_id": public_review_requirement_id(excerpt),
                "source": "issue.description",
                "source_excerpt": excerpt,
            }
        ],
    }
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def _rejected_patch_events(
    *,
    artifact_store: ArtifactStore,
    artifact,
    patch: str,
    action_id: str = "rejected-patch-action",
) -> tuple[list[RunEvent], str, dict[str, str], Artifact]:
    input_hash = sha256_text(canonical_json({"tool": "apply_patch", "input": {"patch": patch}}))
    error_details = {
        "stage": "format",
        "reason": "invalid_envelope",
    }
    error_artifact = artifact_store.put_json(
        {
            "tool": "apply_patch",
            "status": "rejected",
            "error_code": "CONTRACT_ERROR",
            "error_message": "patch must use a raw Git unified diff",
            "error_details": error_details,
        }
    )
    return (
        [
            RunEvent(
                event_id="event-model",
                run_id="run_test",
                sequence=1,
                type=EventType.MODEL_CALLED,
                timestamp=utc_now(),
                actor="model-adapter",
                payload={},
            ),
            RunEvent(
                event_id="event-patch-call",
                run_id="run_test",
                sequence=2,
                type=EventType.TOOL_CALLED,
                timestamp=utc_now(),
                actor="agent",
                correlation_id=action_id,
                payload={
                    "tool": "apply_patch",
                    "input_hash": input_hash,
                    "patch_artifact": artifact.model_dump(mode="json"),
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                },
            ),
            RunEvent(
                event_id="event-patch-failure",
                run_id="run_test",
                sequence=3,
                type=EventType.TOOL_FAILED,
                timestamp=utc_now(),
                actor="tool-gateway",
                correlation_id=action_id,
                payload={
                    "tool": "apply_patch",
                    "status": "rejected",
                    "error_code": "CONTRACT_ERROR",
                    "error_message": "patch must use a raw Git unified diff",
                    "error_details": error_details,
                    "artifact_id": error_artifact.artifact_id,
                    "artifact_path": error_artifact.path,
                    "result_artifact": error_artifact.model_dump(mode="json"),
                },
            ),
        ],
        input_hash,
        error_details,
        error_artifact,
    )


def test_context_rehydrates_recent_public_tool_result(tmp_path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {"path": "module.py", "content": "def broken(): return True"}
    )
    event = RunEvent(
        event_id="event-1",
        run_id="run_test",
        sequence=1,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload={
            "tool": "read_file",
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
        },
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    context, _ = build_context(task, [event], None)
    assert "def broken(): return True" in context
    assert "private.yaml" not in context


def test_context_records_policy_omission_and_tool_result_truncation(tmp_path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {"content": "x" * (TOOL_RESULT_CHARACTER_LIMIT + 1)}
    )
    events = [
        RunEvent(
            event_id=f"event-{sequence}",
            run_id="run_test",
            sequence=sequence,
            type=(
                EventType.TOOL_SUCCEEDED
                if sequence == RECENT_EVENT_LIMIT + 1
                else EventType.PHASE_CHANGED
            ),
            timestamp=utc_now(),
            actor="tool-gateway",
            payload=(
                {
                    "tool": "read_file",
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                }
                if sequence == RECENT_EVENT_LIMIT + 1
                else {"phase": "REPRODUCE"}
            ),
        )
        for sequence in range(1, RECENT_EVENT_LIMIT + 2)
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, events, None)
    original_characters = len(Path(artifact.path).read_text(encoding="utf-8"))

    assert built.evidence["events"]["eligible_count"] == RECENT_EVENT_LIMIT + 1
    assert built.evidence["events"]["included_count"] == RECENT_EVENT_LIMIT
    assert built.evidence["events"]["omitted_count"] == 1
    tool_result = built.evidence["tool_results"][0]
    assert {key: value for key, value in tool_result.items() if key != "included_characters"} == {
        "event_sequence": RECENT_EVENT_LIMIT + 1,
        "original_characters": original_characters,
        "truncated": True,
        "available": True,
        "tool": "read_file",
        "worktree_diff_hash": None,
        "artifact_id": artifact.artifact_id,
    }
    assert tool_result["included_characters"] > len(
        json.dumps({"unavailable": True}, ensure_ascii=False)
    )
    assert '"unavailable": true' not in built.rendered
    assert "field truncated for model context" in built.rendered
    assert built.evidence["rendered_bytes"] == len(built.rendered.encode("utf-8"))


def test_context_evidence_filters_before_selecting_recent_window() -> None:
    events = [
        RunEvent(
            event_id=f"event-{sequence}",
            run_id="run_test",
            sequence=sequence,
            type=(EventType.PHASE_CHANGED if sequence == 1 else EventType.MODEL_CALLED),
            timestamp=utc_now(),
            actor="runner",
            payload={},
        )
        for sequence in range(1, RECENT_EVENT_LIMIT + 2)
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, events, None)

    assert built.evidence["events"]["eligible_count"] == 1
    assert built.evidence["events"]["included_count"] == 1
    assert built.evidence["events"]["omitted_count"] == 0
    assert built.evidence["events"]["included_sequences"] == [1]


def test_legacy_context_policy_preserves_raw_window_and_truncation(tmp_path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {"content": "x" * (TOOL_RESULT_CHARACTER_LIMIT + 1)}
    )
    events = [
        RunEvent(
            event_id=f"event-{sequence}",
            run_id="run_test",
            sequence=sequence,
            type=(EventType.TOOL_SUCCEEDED if sequence == 1 else EventType.MODEL_CALLED),
            timestamp=utc_now(),
            actor="runner",
            payload=(
                {
                    "tool": "read_file",
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                }
                if sequence == 1
                else {}
            ),
        )
        for sequence in range(1, RECENT_EVENT_LIMIT + 2)
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(
        task,
        events,
        None,
        policy_version="v1",
    )

    assert built.evidence["schema_version"] == "context-build-evidence-v1"
    assert built.evidence["events"]["eligible_count"] == 1
    assert built.evidence["events"]["included_count"] == 0
    assert "phase_contract" not in built.rendered


def test_semantic_truncation_remains_bounded_for_large_result_lists(
    tmp_path,
) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {
            "matches": [{"path": f"module_{index}.py", "text": "x" * 200} for index in range(500)],
            "truncated": False,
        }
    )
    event = RunEvent(
        event_id="event-large-list",
        run_id="run_test",
        sequence=1,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload={
            "tool": "search_files",
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
        },
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, [event], None)
    evidence = built.evidence["tool_results"][0]

    assert evidence["truncated"] is True
    assert evidence["available"] is True
    assert evidence["included_characters"] <= TOOL_RESULT_CHARACTER_LIMIT
    assert "top_level_keys" in built.rendered


def test_semantic_truncation_bounds_oversized_object_keys(tmp_path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {f"{'k' * 1_000}-{index}": {"value": "x" * 500} for index in range(50)}
    )
    event = RunEvent(
        event_id="event-large-keys",
        run_id="run_test",
        sequence=1,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload={
            "tool": "search_files",
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
        },
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, [event], None)
    evidence = built.evidence["tool_results"][0]

    assert evidence["truncated"] is True
    assert evidence["included_characters"] <= TOOL_RESULT_CHARACTER_LIMIT
    assert len(built.rendered) < 20_000


def test_next_context_keeps_current_turn_loop_signal_outside_recent_window() -> None:
    events = [
        RunEvent(
            event_id="event-1",
            run_id="run_test",
            sequence=1,
            type=EventType.MODEL_CALLED,
            timestamp=utc_now(),
            actor="model-adapter",
            payload={},
        ),
        RunEvent(
            event_id="event-2",
            run_id="run_test",
            sequence=2,
            type=EventType.LOOP_DETECTED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={
                "tool": "search_files",
                "occurrences": 2,
                "enforcement": "advisory",
            },
        ),
        *[
            RunEvent(
                event_id=f"event-{sequence}",
                run_id="run_test",
                sequence=sequence,
                type=EventType.PHASE_CHANGED,
                timestamp=utc_now(),
                actor="runner",
                payload={"from": "REPRODUCE", "to": "REPRODUCE"},
            )
            for sequence in range(3, RECENT_EVENT_LIMIT + 4)
        ],
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, events, None)
    rendered = json.loads(built.rendered)

    assert 2 not in built.evidence["events"]["included_sequences"]
    assert rendered["execution_signals"]["repeated_calls"] == [
        {
            "sequence": 2,
            "tool": "search_files",
            "occurrences": 2,
            "enforcement": "advisory",
        }
    ]


def test_v3_rehydrates_exact_large_rejected_patch_outside_recent_window(
    tmp_path,
) -> None:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    patch = (
        "diff --git a/module.py b/module.py\n"
        "--- a/module.py\n"
        "+++ b/module.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        f"+{'x' * (TOOL_RESULT_CHARACTER_LIMIT + 1)}\n"
    )
    artifact = artifact_store.put_text(patch, media_type="text/x-diff")
    events, input_hash, error_details, error_artifact = _rejected_patch_events(
        artifact_store=artifact_store,
        artifact=artifact,
        patch=patch,
    )
    events.extend(
        RunEvent(
            event_id=f"event-filler-{sequence}",
            run_id="run_test",
            sequence=sequence,
            type=EventType.PHASE_CHANGED,
            timestamp=utc_now(),
            actor="phase-machine",
            payload={"from": "REPRODUCE", "to": "REPRODUCE"},
        )
        for sequence in range(4, RECENT_EVENT_LIMIT + 6)
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(
        task,
        events,
        None,
        policy_version="phase-evidence-v3",
        artifact_store=artifact_store,
    )
    rendered = json.loads(built.rendered)

    assert len(patch) > TOOL_RESULT_CHARACTER_LIMIT
    assert 2 not in built.evidence["events"]["included_sequences"]
    assert 3 not in built.evidence["events"]["included_sequences"]
    assert rendered["rejected_mutation_retry"] == {
        "schema_version": "rejected-mutation-retry-v1",
        "tool": "apply_patch",
        "action_id": "rejected-patch-action",
        "source_call_sequence": 2,
        "source_failure_sequence": 3,
        "candidate": {
            "patch": patch,
            "content_hash": artifact.content_hash,
            "size_bytes": artifact.size_bytes,
            "input_hash": input_hash,
        },
        "rejection": {
            "status": "rejected",
            "error_code": "CONTRACT_ERROR",
            "error_message": "patch must use a raw Git unified diff",
            "error_details": error_details,
        },
    }
    assert built.evidence["rejected_mutation_retry"] == {
        "included": True,
        "truncated": False,
        "action_id": "rejected-patch-action",
        "source_call_sequence": 2,
        "source_failure_sequence": 3,
        "candidate": {
            "artifact_id": artifact.artifact_id,
            "content_hash": artifact.content_hash,
            "size_bytes": artifact.size_bytes,
            "input_hash": input_hash,
        },
        "rejection": {
            "artifact_id": error_artifact.artifact_id,
            "content_hash": error_artifact.content_hash,
            "size_bytes": error_artifact.size_bytes,
        },
    }
    assert (
        "field truncated for model context"
        not in rendered["rejected_mutation_retry"]["candidate"]["patch"]
    )


def test_v3_rejected_patch_retry_expires_after_next_model_turn(tmp_path) -> None:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    patch = "diff --git a/module.py b/module.py\n"
    artifact = artifact_store.put_text(patch, media_type="text/x-diff")
    events, _, _, _ = _rejected_patch_events(
        artifact_store=artifact_store,
        artifact=artifact,
        patch=patch,
    )
    events.append(
        RunEvent(
            event_id="event-next-model",
            run_id="run_test",
            sequence=4,
            type=EventType.MODEL_CALLED,
            timestamp=utc_now(),
            actor="model-adapter",
            payload={},
        )
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(
        task,
        events,
        None,
        policy_version="phase-evidence-v3",
        artifact_store=artifact_store,
    )
    rendered = json.loads(built.rendered)

    assert rendered.get("rejected_mutation_retry") is None
    assert built.evidence["rejected_mutation_retry"] == {
        "included": False,
        "truncated": False,
    }


def test_v2_context_does_not_rehydrate_rejected_patch_candidate(tmp_path) -> None:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    patch = "diff --git a/module.py b/module.py\n"
    artifact = artifact_store.put_text(patch, media_type="text/x-diff")
    events, _, _, _ = _rejected_patch_events(
        artifact_store=artifact_store,
        artifact=artifact,
        patch=patch,
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(
        task,
        events,
        None,
        policy_version="phase-evidence-v2",
        artifact_store=artifact_store,
    )
    rendered = json.loads(built.rendered)

    assert "rejected_mutation_retry" not in rendered
    assert "rejected_mutation_retry" not in built.evidence
    assert patch not in built.rendered
    assert built.evidence["schema_version"] == "context-build-evidence-v2"


def test_v3_rejected_patch_retry_fails_closed_on_tampered_candidate_cas(
    tmp_path,
) -> None:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    patch = "diff --git a/module.py b/module.py\n"
    artifact = artifact_store.put_text(patch, media_type="text/x-diff")
    events, _, _, _ = _rejected_patch_events(
        artifact_store=artifact_store,
        artifact=artifact,
        patch=patch,
    )
    Path(artifact.path).write_text(
        patch + "tampered",
        encoding="utf-8",
        newline="",
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    with pytest.raises(RecoveryError, match="artifact"):
        build_context_with_evidence(
            task,
            events,
            None,
            policy_version="phase-evidence-v3",
            artifact_store=artifact_store,
        )


def test_v6_context_rehydrates_bounded_probe_ledger(tmp_path) -> None:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    source = "from mini_data_utils.csvlite import parse_rows\nassert parse_rows('a')"
    input_artifact = artifact_store.put_json(
        {
            "tool": "run_probe",
            "input": {
                "probe_id": "python-diagnostic",
                "source": source,
            },
        }
    )
    result_artifact = artifact_store.put_json(
        {
            "schema_version": "ephemeral-python-probe-result-v2",
            "passed": True,
            "worktree_diff_hash": "sha256:probe-diff",
        }
    )
    events = [
        RunEvent(
            event_id="probe-call",
            run_id="run_test",
            sequence=1,
            type=EventType.TOOL_CALLED,
            timestamp=utc_now(),
            actor="agent",
            correlation_id="probe-action",
            payload={
                "tool": "run_probe",
                "input_artifact": input_artifact.model_dump(mode="json"),
                "artifact_id": input_artifact.artifact_id,
                "artifact_path": input_artifact.path,
                "worktree_diff_hash": "sha256:probe-diff",
            },
        ),
        RunEvent(
            event_id="probe-result",
            run_id="run_test",
            sequence=2,
            type=EventType.TOOL_SUCCEEDED,
            timestamp=utc_now(),
            actor="tool-gateway",
            correlation_id="probe-action",
            payload={
                "tool": "run_probe",
                "passed": True,
                "timed_out": False,
                "worktree_diff_hash": "sha256:probe-diff",
                "artifact_id": result_artifact.artifact_id,
                "artifact_path": result_artifact.path,
                "result_artifact": result_artifact.model_dump(
                    mode="json"
                ),
            },
        ),
    ]
    task = load_task_package(
        "tasks/smoke/csv-quoted-newline"
    ).public.model_copy(
        update={
            "schema_version": "task-public-v2",
            "probe_profiles": [
                RegisteredProbeProfile(id="python-diagnostic")
            ],
        }
    )

    built = build_context_with_evidence(
        task,
        events,
        None,
        policy_version="phase-evidence-v6",
        artifact_store=artifact_store,
        budget=Budget(),
        max_output_tokens=4096,
    )
    rendered = json.loads(built.rendered)

    assert built.evidence["schema_version"] == "context-build-evidence-v6"
    assert built.evidence["probe_ledger"]["entry_count"] == 1
    assert rendered["probe_ledger"]["entries"][0]["source"] == source
    assert rendered["probe_ledger"]["entries"][0]["probe_id"] == (
        "python-diagnostic"
    )
    assert rendered["probe_ledger"]["authoritative"] is False
    assert rendered["phase_contract"]["optional_actions"] == ["run_probe"]
    assert rendered["phase_contract"]["required_sequence"][-2:] == [
        "review_task",
        "finish_task",
    ]


def test_v6_context_omits_probe_when_task_has_no_profile(
    tmp_path,
) -> None:
    task = load_task_package(
        "tasks/smoke/csv-quoted-newline"
    ).public

    built = build_context_with_evidence(
        task,
        [],
        None,
        policy_version="phase-evidence-v6",
        artifact_store=ArtifactStore(tmp_path / "artifacts"),
        budget=Budget(),
        max_output_tokens=4096,
    )
    rendered = json.loads(built.rendered)

    assert rendered["phase_contract"]["optional_actions"] == []
    assert "run_probe" not in (
        rendered["phase_contract"]["allowed_next_actions"]
    )
    assert rendered["rules"]["registered_checks_only"] is True
    assert (
        rendered["rules"]["registered_probe_profiles_only"]
        is True
    )


def test_v9_pins_current_diff_review_evidence_outside_recent_window(
    tmp_path,
) -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    artifacts = ArtifactStore(tmp_path / "artifacts")
    diff_hash = "sha256:" + ("9" * 64)
    check_artifact = artifacts.put_json(
        {
            "check_id": task.visible_checks[0].id,
            "passed": True,
            "worktree_diff_hash": diff_hash,
        }
    )
    diff_artifact = artifacts.put_json(
        {
            "patch": "diff --git a/a.py b/a.py\n",
            "patch_hash": diff_hash,
            "worktree_diff_hash": diff_hash,
        }
    )
    rejection_artifact = artifacts.put_json(
        {
            "tool": "review_task",
            "status": "rejected",
            "error_code": "CONTRACT_ERROR",
            "error_message": "stale review citation",
            "error_details": {},
        }
    )
    events = [
        RunEvent(
            event_id="v9-mutation",
            run_id="run_v9_review_pin",
            sequence=1,
            type=EventType.PATCH_APPLIED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={"worktree_diff_hash": diff_hash},
        ),
        RunEvent(
            event_id="v9-check",
            run_id="run_v9_review_pin",
            sequence=2,
            type=EventType.TOOL_SUCCEEDED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={
                "tool": "run_check",
                "check_id": task.visible_checks[0].id,
                "passed": True,
                "worktree_diff_hash": diff_hash,
                "artifact_id": check_artifact.artifact_id,
                "artifact_path": check_artifact.path,
                "result_artifact": check_artifact.model_dump(mode="json"),
            },
        ),
        RunEvent(
            event_id="v9-diff",
            run_id="run_v9_review_pin",
            sequence=3,
            type=EventType.TOOL_SUCCEEDED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={
                "tool": "get_diff",
                "worktree_diff_hash": diff_hash,
                "artifact_id": diff_artifact.artifact_id,
                "artifact_path": diff_artifact.path,
                "result_artifact": diff_artifact.model_dump(mode="json"),
            },
        ),
    ]
    for sequence in range(4, 4 + RECENT_EVENT_LIMIT + 2):
        events.append(
            RunEvent(
                event_id=f"v9-review-failure-{sequence}",
                run_id="run_v9_review_pin",
                sequence=sequence,
                type=EventType.TOOL_FAILED,
                timestamp=utc_now(),
                actor="tool-gateway",
                payload={
                    "tool": "review_task",
                    "status": "rejected",
                    "error_code": "CONTRACT_ERROR",
                    "error_message": "stale review citation",
                    "error_details": {},
                    "artifact_id": rejection_artifact.artifact_id,
                    "artifact_path": rejection_artifact.path,
                },
            )
        )
    checkpoint = Checkpoint(
        checkpoint_id="ckpt_v9_review_pin",
        run_id="run_v9_review_pin",
        through_sequence=events[-1].sequence,
        phase=Phase.REVIEW,
        repository_head="0" * 40,
        worktree_diff_hash=diff_hash,
        created_at=utc_now(),
    )

    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        policy_version="phase-evidence-v9",
        artifact_store=artifacts,
        budget=Budget(),
        max_output_tokens=4096,
        public_review_contract=_public_review_contract(task),
    )
    rendered = json.loads(built.rendered)
    review = rendered["review_evidence"]

    assert built.evidence["schema_version"] == "context-build-evidence-v9"
    assert review["schema_version"] == REVIEW_EVIDENCE_SCHEMA
    assert review["pinning_active"] is True
    assert review["passing_check_event_sequences"] == [2]
    assert review["source_get_diff_sequence"] == 3
    assert review["citable_event_sequences"] == [2, 3]
    assert [item["sequence"] for item in review["pinned_results"]] == [2, 3]
    assert 2 not in built.evidence["events"]["included_sequences"]
    assert 3 not in built.evidence["events"]["included_sequences"]
    assert {2, 3}.issubset(
        {
            item["event_sequence"]
            for item in built.evidence["tool_results"]
        }
    )
    assert rendered["phase_contract"]["allowed_next_actions"] == [
        "review_task",
        "apply_patch",
    ]


def test_v9_review_anchor_body_appears_once_inside_recent_window(
    tmp_path,
) -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    artifacts = ArtifactStore(tmp_path / "artifacts")
    diff_hash = "sha256:" + ("8" * 64)
    check_marker = "v9-unique-current-diff-check-body"
    diff_marker = "v9-unique-current-diff-patch-body"
    check_artifact = artifacts.put_json(
        {
            "tool": "run_check",
            "check_id": task.visible_checks[0].id,
            "passed": True,
            "stdout": check_marker,
        }
    )
    diff_artifact = artifacts.put_json(
        {
            "tool": "get_diff",
            "patch": diff_marker,
            "worktree_diff_hash": diff_hash,
        }
    )
    events = [
        RunEvent(
            event_id="v9-recent-mutation",
            run_id="run_v9_review_recent_dedup",
            sequence=1,
            type=EventType.PATCH_APPLIED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={"worktree_diff_hash": diff_hash},
        ),
        RunEvent(
            event_id="v9-recent-check",
            run_id="run_v9_review_recent_dedup",
            sequence=2,
            type=EventType.TOOL_SUCCEEDED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={
                "tool": "run_check",
                "check_id": task.visible_checks[0].id,
                "passed": True,
                "worktree_diff_hash": diff_hash,
                "artifact_id": check_artifact.artifact_id,
                "artifact_path": check_artifact.path,
                "result_artifact": check_artifact.model_dump(mode="json"),
            },
        ),
        RunEvent(
            event_id="v9-recent-diff",
            run_id="run_v9_review_recent_dedup",
            sequence=3,
            type=EventType.TOOL_SUCCEEDED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={
                "tool": "get_diff",
                "worktree_diff_hash": diff_hash,
                "artifact_id": diff_artifact.artifact_id,
                "artifact_path": diff_artifact.path,
                "result_artifact": diff_artifact.model_dump(mode="json"),
            },
        ),
    ]
    checkpoint = Checkpoint(
        checkpoint_id="ckpt_v9_review_recent_dedup",
        run_id="run_v9_review_recent_dedup",
        through_sequence=3,
        phase=Phase.REVIEW,
        repository_head="0" * 40,
        worktree_diff_hash=diff_hash,
        created_at=utc_now(),
    )

    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        policy_version="phase-evidence-v9",
        artifact_store=artifacts,
        budget=Budget(),
        max_output_tokens=4096,
        public_review_contract=_public_review_contract(task),
    )
    rendered = json.loads(built.rendered)

    assert [
        item["sequence"]
        for item in rendered["review_evidence"]["pinned_results"]
    ] == [2, 3]
    assert [item["sequence"] for item in rendered["recent_events"]] == [1]
    assert built.evidence["events"]["included_sequences"] == [1]
    assert built.rendered.count(check_marker) == 1
    assert built.rendered.count(diff_marker) == 1
