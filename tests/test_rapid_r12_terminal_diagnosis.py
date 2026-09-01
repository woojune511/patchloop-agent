from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals.rapid_r12_terminal_diagnosis import (
    R12_BUNDLE_PATH,
    build_rapid_r12_terminal_diagnosis,
    diagnosis_bytes,
    prepare_read_only_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT / "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-semantic-progress-ab-20260825-r12-terminal-diagnosis-v1.json"
)


def _snapshot(path: Path) -> Path:
    return prepare_read_only_snapshot(
        repository_root=ROOT,
        source_state_path=ROOT / ".patchloop/state.sqlite3",
        snapshot_path=path,
    )


def _build(snapshot: Path, **kwargs) -> dict:
    return build_rapid_r12_terminal_diagnosis(
        repository_root=ROOT,
        source_state_path=ROOT / ".patchloop/state.sqlite3",
        state_snapshot_path=snapshot,
        **kwargs,
    )


@pytest.fixture(scope="module")
def state_snapshot(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _snapshot(tmp_path_factory.mktemp("r12-terminal-diagnosis") / "state.sqlite3")


def test_r12_terminal_diagnosis_is_deterministic_and_public_only(
    state_snapshot: Path,
) -> None:
    first = _build(state_snapshot)
    second = _build(state_snapshot)

    assert diagnosis_bytes(first) == diagnosis_bytes(second)
    assert first["immutable_batch"] == {
        "rows_started": 6,
        "bundle_agent_failures": 5,
        "evaluator_reached": 1,
        "submissions_completed": 1,
        "successes_at_budget": 0,
        "token_terminals": 0,
        "model_cost_nanos": 2_658_231_750,
    }
    assert first["evidence_boundary"] == {
        "public_bundle_events_read": True,
        "public_tool_metadata_read": True,
        "public_visible_check_artifacts_read": True,
        "durable_structured_plan_text_read_for_marker_projection": True,
        "raw_plan_text_emitted": False,
        "raw_patch_emitted": False,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "llm_response_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "source_state_mutations": 0,
        "local_snapshot_files_created": 1,
        "added_cost_nanos": 0,
    }
    serialized = diagnosis_bytes(first).decode("utf-8")
    assert "I suspect the hook" not in serialized
    assert "diff --git" not in serialized
    assert "reference.patch" not in serialized
    assert "/hidden/" not in serialized and "\\hidden\\" not in serialized


def test_r12_terminal_attribution_separates_mechanical_and_semantic_classes(
    state_snapshot: Path,
) -> None:
    value = _build(state_snapshot)
    rows = {row["order"]: row for row in value["row_attributions"]}

    for order in (1, 4):
        row = rows[order]
        assert row["classification"] == "legacy_reasoning_only_per_turn_truncation"
        assert row["response"] == {
            "status": "incomplete",
            "incomplete_reason": "max_output_tokens",
            "output_tokens": 8_192,
            "reasoning_output_tokens": 8_192,
            "response_text_present": False,
            "response_tool_call_count": 0,
        }
        assert row["cumulative_output_budget_exhausted"] is False
        assert row["recovery_model_call_after_incomplete"] is False
        assert row["terminal_as_pure_agent_failure_supported"] is False

    wrong_check = rows[5]
    assert wrong_check["classification"] == "legacy_unbound_run_check_schema_contract_failure"
    assert wrong_check["request"]["run_check_enum"] is None
    assert wrong_check["dispatchable_run_check_ids"] == []
    assert wrong_check["successor_exact_check_request"]["run_check_enum"] == [
        "public-interrupt-runner-lifecycle"
    ]
    assert wrong_check["requested_check_id_observed"] is False

    submitted = rows[2]
    assert submitted["classification"] == "submitted_visible_checks_passed_task_failure"
    assert [item["passed"] for item in submitted["visible_check_path"]] == [False, True, True]
    assert submitted["get_diff_to_finish_completed"] is True
    assert submitted["exact_task_failure_cause_observed"] is False
    assert submitted["diff"]["raw_patch_emitted"] is False

    admission = rows[6]
    assert admission["classification"] == "duplicate_candidate_path_plan_schema_friction"
    assert admission["reason_codes"] == [["plan_schema_invalid"], ["plan_schema_invalid"]]
    assert admission["offline_successor"]["runtime"] == "lean-harness-v16"
    assert admission["offline_successor"]["live_candidate_created"] is False


def test_r12_semantic_reset_did_not_force_an_alternative_mechanism(
    state_snapshot: Path,
) -> None:
    value = _build(state_snapshot)
    row = value["row_attributions"][2]

    assert row["classification"] == "semantic_reset_without_alternative_causal_mechanism"
    assert row["initial_plus_corrective_mutations"] == "1+3"
    assert row["all_edit_dispatches_accepted"] is True
    assert row["increase_correction_limit_supported"] is False
    assert [item["failure_signature"] for item in row["checks"]] == [
        "AssertionError: PUBLIC_CASE:anyio:test-resumed"
    ] * 4
    assert len({item["worktree_diff_hash"] for item in row["checks"]}) == 4
    assert [item["prior_hypothesis_disposition"] for item in row["plans"]] == [
        None,
        "refined",
        "rejected",
        "rejected",
    ]
    assert [item["semantic_reset_required"] for item in row["plans"]] == [
        False,
        False,
        True,
        True,
    ]
    assert {item["mechanism_family"] for item in row["plans"]} == {
        "runner-lifecycle-before-pytest-reentry"
    }
    assert [item["novel_information_action_count"] for item in row["plans"]] == [
        0,
        3,
        0,
        2,
    ]
    assert row["semantic_equivalence_claimed"] is False
    assert row["rejected_label_forced_alternative_mechanism"] is False
    assert value["selected_failure_class"] == {
        **value["selected_failure_class"],
        "id": "semantic-reset-without-alternative-causal-mechanism",
        "affected_orders": [3],
        "candidate_ready": False,
        "paid_execution_authorized": False,
    }


def test_r12_terminal_diagnosis_fails_closed_on_tampered_bundle(
    tmp_path: Path,
    state_snapshot: Path,
) -> None:
    source = ROOT / R12_BUNDLE_PATH
    tampered = tmp_path / "tampered.jsonl"
    tampered.write_bytes(source.read_bytes() + b"\n")

    with pytest.raises(ContractError, match="bundle file hash differs"):
        _build(state_snapshot, bundle_path=tampered)


def test_r12_snapshot_fails_closed_on_nonzero_wal(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    source.write_bytes(b"source")
    Path(str(source) + "-wal").write_bytes(b"uncheckpointed")

    with pytest.raises(ContractError, match="source trace is not quiescent"):
        prepare_read_only_snapshot(
            repository_root=tmp_path,
            source_state_path=source,
            snapshot_path=tmp_path / "snapshot.sqlite3",
        )


def test_materialized_r12_terminal_diagnosis_matches_builder(state_snapshot: Path) -> None:
    expected = diagnosis_bytes(_build(state_snapshot))
    actual = ARTIFACT.read_bytes()

    assert actual == expected
    document = json.loads(actual)
    assert document["content_hash"] == json.loads(expected)["content_hash"]
    assert "sha256:" + hashlib.sha256(actual).hexdigest() == (
        "sha256:633154b9e505a7bf436caf17502a8364782798bc5cbb557f09f6fc69e3814d45"
    )
