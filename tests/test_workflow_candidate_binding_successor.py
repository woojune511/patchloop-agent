from __future__ import annotations

from pathlib import Path

import pytest

from patchloop.agent.workflow_candidate_binding_successor import (
    CANDIDATE_BINDING_POLICY_V16,
    validate_work_plan_v16,
)
from patchloop.agent.workflow_successor_v2 import (
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalogV2,
    SourceEvidenceProjection,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError
from patchloop.util import load_unique_yaml, sha256_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]
TASK = PublicTask.model_validate(
    load_unique_yaml(
        (ROOT / "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml").read_text(
            encoding="utf-8"
        )
    )
)
RUN_ID = "run_r12_shaped_candidate_binding"
DIFF_HASH = sha256_text("")
PATH = "src/anyio/pytest_plugin.py"


def _read(sequence: int, start: int, end: int) -> EligiblePlanEvidence:
    source = SourceEvidenceProjection(
        path=PATH,
        requested_range=(start, end),
        actual_range=(start, end),
        visible_ranges=((start, end),),
        omitted_ranges=(),
        partial_line=False,
        total_lines=1_000,
        file_content_hash="sha256:" + "a" * 64,
    )
    body = {
        "evidence_id": f"pev:{sequence}",
        "kind": "source_read",
        "role": "foundation",
        "run_id": RUN_ID,
        "worktree_diff_hash": DIFF_HASH,
        "canonical_event_sequence": sequence,
        "model_visible_event_sequences": (sequence,),
        "replay_alias_event_sequences": (),
        "artifact_hash": "sha256:" + f"{sequence:064x}",
        "visible_projection_hash": sha256_json(source.model_dump(mode="json")),
        "source": source.model_dump(mode="python"),
        "check": None,
        "diff_review": None,
        "search": None,
    }
    return EligiblePlanEvidence.model_validate(body)


def _catalog() -> EligiblePlanEvidenceCatalogV2:
    items = (_read(12, 120, 180), _read(17, 300, 360))
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "run_id": RUN_ID,
        "task_id": TASK.task_id,
        "task_version": TASK.task_version,
        "public_task_hash": sha256_json(TASK.model_dump(mode="json")),
        "worktree_diff_hash": DIFF_HASH,
        "model_visible_context_hash": "sha256:" + "b" * 64,
        "model_visible_recent_event_sequences": (12, 17),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _arguments(candidate_files: list[dict[str, str]]) -> dict:
    return {
        "observation_status": "static_source",
        "hypothesis": "The public cleanup path needs a bounded source change.",
        "foundation_evidence_ids": ["pev:12", "pev:17"],
        "supporting_evidence_ids": [],
        "candidate_files": candidate_files,
        "intended_change": "Adjust the cited cleanup implementation.",
        "expected_behavior": "The registered public cleanup behavior passes.",
        "unknowns": [],
    }


def _validate(candidate_files: list[dict[str, str]]):
    return validate_work_plan_v16(
        task=TASK,
        catalog=_catalog(),
        arguments=_arguments(candidate_files),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
    )


def test_r12_same_file_different_visible_ranges_are_one_candidate() -> None:
    plan, normalization = _validate(
        [
            {"path": PATH, "read_evidence_id": "pev:17"},
            {"path": PATH, "read_evidence_id": "pev:12"},
        ]
    )

    assert [item.path for item in plan.candidate_files] == [PATH]
    assert plan.candidate_files[0].read_evidence_id == "pev:17"
    assert [item.evidence_id for item in plan.foundation_evidence] == ["pev:12", "pev:17"]
    assert normalization.policy_version == CANDIDATE_BINDING_POLICY_V16
    assert normalization.submitted_binding_count == 2
    assert normalization.canonical_candidate_count == 1
    assert normalization.path_bindings[0].cited_read_evidence_ids == ("pev:12", "pev:17")
    assert normalization.path_bindings[0].collapsed_same_path_bindings is True


def test_candidate_order_and_restart_replay_are_deterministic() -> None:
    first = _validate(
        [
            {"path": PATH, "read_evidence_id": "pev:12"},
            {"path": PATH, "read_evidence_id": "pev:17"},
        ]
    )
    second = _validate(
        [
            {"path": PATH, "read_evidence_id": "pev:17"},
            {"path": PATH, "read_evidence_id": "pev:12"},
        ]
    )

    assert first == second
    assert first[0].content_hash == second[0].content_hash
    assert first[1].content_hash == second[1].content_hash


def test_every_collapsed_binding_must_still_be_current_public_source_evidence() -> None:
    with pytest.raises(ContractError) as exc_info:
        _validate(
            [
                {"path": PATH, "read_evidence_id": "pev:17"},
                {"path": "src/anyio/_core/_eventloop.py", "read_evidence_id": "pev:12"},
            ]
        )

    assert exc_info.value.details["reason_codes"] == ["candidate_read_binding_invalid"]


def test_exact_duplicate_binding_is_collapsed_without_losing_foundation_catalog() -> None:
    plan, normalization = _validate(
        [
            {"path": PATH, "read_evidence_id": "pev:17"},
            {"path": PATH, "read_evidence_id": "pev:17"},
        ]
    )

    assert len(plan.candidate_files) == 1
    assert len(plan.foundation_evidence) == 2
    assert normalization.submitted_binding_count == 2
    assert normalization.path_bindings[0].cited_read_evidence_ids == ("pev:17",)
    assert normalization.path_bindings[0].collapsed_same_path_bindings is True
