from __future__ import annotations

import json

import pytest

from patchloop.agent.context import (
    RECENT_EVENT_LIMIT,
    REVIEW_EVIDENCE_SCHEMA,
    REVIEW_EVIDENCE_V2_SCHEMA,
    build_context_with_evidence,
)
from patchloop.agent.review import (
    normalize_public_issue_text,
    public_review_contract_content_hash,
    public_review_coverage_target_id,
    public_review_requirement_id,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Budget,
    Checkpoint,
    EventType,
    Phase,
    PublicReviewContract,
    RegisteredCheck,
    RunEvent,
)
from patchloop.errors import RecoveryError
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json, utc_now


def _task_with_two_checks():
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    return task.model_copy(
        update={
            "visible_checks": [
                *task.visible_checks,
                RegisteredCheck(
                    id="secondary-check",
                    command=["python", "-m", "unittest", "-v"],
                ),
            ]
        }
    )


def _review_contract(task, *, version: int) -> PublicReviewContract:
    excerpt = normalize_public_issue_text(task.issue.description)
    requirement_id = public_review_requirement_id(excerpt)
    requirement: dict[str, object] = {
        "requirement_id": requirement_id,
        "source": "issue.description",
        "source_excerpt": excerpt,
    }
    if version == 2:
        target_specs = [
            {
                "description": "Inspect the primary parser branch.",
                "evidence_kind": "current_diff_inspection",
                "path": "mini_data_utils/csv_tools.py",
                "anchor": "V10_PRIMARY_ANCHOR",
            },
            {
                "description": "Validate both public parser checks.",
                "evidence_kind": "passing_validation",
                "check_ids": ["existing-unit-tests", "secondary-check"],
            },
            {
                "description": "Inspect the secondary parser branch.",
                "evidence_kind": "current_diff_inspection",
                "path": "mini_data_utils/csv_tools.py",
                "anchor": "V10_SECONDARY_ANCHOR",
            },
        ]
        targets = []
        for spec in target_specs:
            target = {
                "coverage_target_id": public_review_coverage_target_id(
                    requirement_id,
                    description=str(spec["description"]),
                    evidence_kind=str(spec["evidence_kind"]),
                    path=spec.get("path"),
                    anchor=spec.get("anchor"),
                    check_ids=spec.get("check_ids"),
                ),
                **spec,
            }
            targets.append(target)
        requirement["coverage_targets"] = targets
    payload = {
        "schema_version": f"public-review-contract-v{version}",
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_spec_hash": sha256_json(task.model_dump(mode="json")),
        "requirements": [requirement],
    }
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def _result_event(
    *,
    sequence: int,
    tool: str,
    artifact,
    diff_hash: str,
    **payload,
) -> RunEvent:
    return RunEvent(
        event_id=f"v10-event-{sequence}",
        run_id="run_v10_review_pin",
        sequence=sequence,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload={
            "tool": tool,
            "status": "succeeded",
            "worktree_diff_hash": diff_hash,
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
            "result_artifact": artifact.model_dump(mode="json"),
            **payload,
        },
    )


def _review_ready_events(task, artifacts: ArtifactStore):
    diff_hash = "sha256:" + ("a" * 64)
    wrong_diff_hash = "sha256:" + ("b" * 64)
    stale_read = artifacts.put_json(
        {
            "path": "mini_data_utils/csv_tools.py",
            "content": "V10_PRIMARY_ANCHOR V10_SECONDARY_ANCHOR stale",
            "worktree_diff_hash": wrong_diff_hash,
        }
    )
    matching_read = artifacts.put_json(
        {
            "path": "mini_data_utils/csv_tools.py",
            "content": (
                "V10_PRIMARY_ANCHOR\n"
                "V10_SECONDARY_ANCHOR\n"
                "v10-unique-selected-read-body"
            ),
            "worktree_diff_hash": diff_hash,
        }
    )
    wrong_path_read = artifacts.put_json(
        {
            "path": "mini_data_utils/other.py",
            "content": "V10_PRIMARY_ANCHOR V10_SECONDARY_ANCHOR wrong path",
            "worktree_diff_hash": diff_hash,
        }
    )
    missing_anchor_read = artifacts.put_json(
        {
            "path": "mini_data_utils/csv_tools.py",
            "content": "latest current-diff read lacks both exact anchors",
            "worktree_diff_hash": diff_hash,
        }
    )
    secondary_check = artifacts.put_json(
        {
            "check_id": "secondary-check",
            "passed": True,
            "timed_out": False,
            "truncated": False,
            "worktree_diff_hash": diff_hash,
        }
    )
    primary_check = artifacts.put_json(
        {
            "check_id": "existing-unit-tests",
            "passed": True,
            "timed_out": False,
            "truncated": False,
            "worktree_diff_hash": diff_hash,
        }
    )
    final_diff = artifacts.put_json(
        {
            "patch": "diff --git a/mini_data_utils/csv_tools.py b/mini_data_utils/csv_tools.py\n",
            "worktree_diff_hash": diff_hash,
        }
    )
    events = [
        RunEvent(
            event_id="v10-mutation",
            run_id="run_v10_review_pin",
            sequence=1,
            type=EventType.PATCH_APPLIED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={"worktree_diff_hash": diff_hash},
        ),
        _result_event(
            sequence=2,
            tool="read_file",
            artifact=stale_read,
            diff_hash=wrong_diff_hash,
        ),
        _result_event(
            sequence=3,
            tool="read_file",
            artifact=matching_read,
            diff_hash=diff_hash,
        ),
        _result_event(
            sequence=4,
            tool="read_file",
            artifact=wrong_path_read,
            diff_hash=diff_hash,
        ),
        _result_event(
            sequence=5,
            tool="read_file",
            artifact=missing_anchor_read,
            diff_hash=diff_hash,
        ),
        _result_event(
            sequence=6,
            tool="run_check",
            artifact=secondary_check,
            diff_hash=diff_hash,
            check_id="secondary-check",
            passed=True,
            timed_out=False,
        ),
        _result_event(
            sequence=7,
            tool="run_check",
            artifact=primary_check,
            diff_hash=diff_hash,
            check_id="existing-unit-tests",
            passed=True,
            timed_out=False,
        ),
        _result_event(
            sequence=8,
            tool="get_diff",
            artifact=final_diff,
            diff_hash=diff_hash,
        ),
    ]
    for sequence in range(9, 9 + RECENT_EVENT_LIMIT + 3):
        events.append(
            RunEvent(
                event_id=f"v10-filler-{sequence}",
                run_id="run_v10_review_pin",
                sequence=sequence,
                type=EventType.PHASE_CHANGED,
                timestamp=utc_now(),
                actor="runner",
                payload={"phase": "REVIEW"},
            )
        )
    checkpoint = Checkpoint(
        checkpoint_id="ckpt_v10_review_pin",
        run_id="run_v10_review_pin",
        through_sequence=events[-1].sequence,
        phase=Phase.REVIEW,
        repository_head="0" * 40,
        worktree_diff_hash=diff_hash,
        created_at=utc_now(),
    )
    return events, checkpoint


def test_v10_pins_ordered_public_coverage_and_current_diff_anchors(
    tmp_path,
) -> None:
    task = _task_with_two_checks()
    artifacts = ArtifactStore(tmp_path / "artifacts")
    contract = _review_contract(task, version=2)
    events, checkpoint = _review_ready_events(task, artifacts)

    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        policy_version="phase-evidence-v10",
        artifact_store=artifacts,
        budget=Budget(),
        max_output_tokens=4096,
        public_review_contract=contract,
    )
    rendered = json.loads(built.rendered)
    review = rendered["review_evidence"]
    target_ids = [
        target.coverage_target_id
        for requirement in contract.requirements
        for target in requirement.coverage_targets
    ]

    assert built.evidence["schema_version"] == "context-build-evidence-v10"
    assert review["schema_version"] == REVIEW_EVIDENCE_V2_SCHEMA
    assert review["pinning_active"] is True
    assert list(review["coverage_target_event_sequences"]) == target_ids
    assert list(review["coverage_target_event_sequences"].values()) == [
        [3],
        [6, 7],
        [3],
    ]
    assert review["passing_check_event_sequences"] == [7, 6]
    assert review["source_get_diff_sequence"] == 8
    assert review["citable_event_sequences"] == [3, 6, 7, 8]
    assert [item["sequence"] for item in review["pinned_results"]] == [
        3,
        6,
        7,
        8,
    ]
    assert built.evidence["review_evidence"][
        "coverage_target_event_sequences"
    ] == review["coverage_target_event_sequences"]
    assert built.evidence["review_evidence"][
        "citable_event_sequences"
    ] == review["citable_event_sequences"]
    assert built.evidence["events"]["included_sequences"] == list(
        range(12, 24)
    )
    assert built.rendered.count("v10-unique-selected-read-body") == 1
    assert rendered["phase_contract"]["schema_version"] == "phase-contract-v4"
    assert rendered["phase_contract"][
        "task_review_coverage_complete"
    ] is None
    assert rendered["phase_contract"][
        "unresolved_coverage_target_ids"
    ] == []


def test_v10_rejects_tampered_selected_inspection_descriptor(tmp_path) -> None:
    task = _task_with_two_checks()
    artifacts = ArtifactStore(tmp_path / "artifacts")
    contract = _review_contract(task, version=2)
    events, checkpoint = _review_ready_events(task, artifacts)
    selected = events[2]
    events[2] = selected.model_copy(
        update={
            "payload": {
                **selected.payload,
                "artifact_id": "art_tampered",
            }
        }
    )

    with pytest.raises(
        RecoveryError,
        match="inspection outcome conflicts with its artifact",
    ):
        build_context_with_evidence(
            task,
            events,
            checkpoint,
            policy_version="phase-evidence-v10",
            artifact_store=artifacts,
            budget=Budget(),
            max_output_tokens=4096,
            public_review_contract=contract,
        )


def test_v10_rejects_current_diff_relabel_of_stale_read_result(tmp_path) -> None:
    task = _task_with_two_checks()
    artifacts = ArtifactStore(tmp_path / "artifacts")
    contract = _review_contract(task, version=2)
    events, checkpoint = _review_ready_events(task, artifacts)
    selected = events[2]
    stale_document = {
        "path": "mini_data_utils/csv_tools.py",
        "content": "V10_PRIMARY_ANCHOR\nV10_SECONDARY_ANCHOR",
        "worktree_diff_hash": "sha256:" + ("b" * 64),
    }
    stale_artifact = artifacts.put_json(stale_document)
    events[2] = selected.model_copy(
        update={
            "payload": {
                **selected.payload,
                # The event claims the current diff while its CAS bytes are stale.
                "artifact_id": stale_artifact.artifact_id,
                "artifact_path": stale_artifact.path,
                "result_artifact": stale_artifact.model_dump(mode="json"),
            }
        }
    )

    with pytest.raises(
        RecoveryError,
        match="current-diff result",
    ):
        build_context_with_evidence(
            task,
            events,
            checkpoint,
            policy_version="phase-evidence-v10",
            artifact_store=artifacts,
            budget=Budget(),
            max_output_tokens=4096,
            public_review_contract=contract,
        )


def test_v10_rejects_failed_check_relabelled_as_passing(tmp_path) -> None:
    task = _task_with_two_checks()
    artifacts = ArtifactStore(tmp_path / "artifacts")
    contract = _review_contract(task, version=2)
    events, checkpoint = _review_ready_events(task, artifacts)
    selected = events[6]
    failed_artifact = artifacts.put_json(
        {
            "check_id": "existing-unit-tests",
            "passed": False,
            "timed_out": False,
            "truncated": False,
            "worktree_diff_hash": checkpoint.worktree_diff_hash,
        }
    )
    events[6] = selected.model_copy(
        update={
            "payload": {
                **selected.payload,
                # Selection metadata is forged; the CAS result still says failed.
                "artifact_id": failed_artifact.artifact_id,
                "artifact_path": failed_artifact.path,
                "result_artifact": failed_artifact.model_dump(mode="json"),
            }
        }
    )

    with pytest.raises(
        RecoveryError,
        match="run_check event conflicts",
    ):
        build_context_with_evidence(
            task,
            events,
            checkpoint,
            policy_version="phase-evidence-v10",
            artifact_store=artifacts,
            budget=Budget(),
            max_output_tokens=4096,
            public_review_contract=contract,
        )


def test_v9_review_rendering_remains_v1_without_coverage_fields(tmp_path) -> None:
    task = _task_with_two_checks()
    artifacts = ArtifactStore(tmp_path / "artifacts")
    contract = _review_contract(task, version=1)
    events, checkpoint = _review_ready_events(task, artifacts)

    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        policy_version="phase-evidence-v9",
        artifact_store=artifacts,
        budget=Budget(),
        max_output_tokens=4096,
        public_review_contract=contract,
    )
    review = json.loads(built.rendered)["review_evidence"]

    assert built.evidence["schema_version"] == "context-build-evidence-v9"
    assert review["schema_version"] == REVIEW_EVIDENCE_SCHEMA
    assert "coverage_target_event_sequences" not in review
    assert review["citable_event_sequences"] == [7, 6, 8]
    assert [item["sequence"] for item in review["pinned_results"]] == [
        7,
        6,
        8,
    ]
