from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from patchloop.contracts import EventType
from patchloop.errors import ContractError
from patchloop.evals.rapid_workflow_diagnosis import (
    _load_bundle,
    build_rapid_workflow_diagnosis,
    diagnosis_bytes,
)
from patchloop.trace_view import ReadOnlyTraceStore
from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".patchloop" / "state.sqlite3"
TASK = ROOT / "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml"
R8 = (
    ROOT / "reports/rapid-development/"
    "rapid-public-dev-anyio-completion-policy-20260823-r8-553f7cfca404.jsonl"
)
R9 = (
    ROOT / "reports/rapid-development/"
    "rapid-public-dev-anyio-ordered-correction-20260824-r9-db9e887fea43.jsonl"
)
R10 = (
    ROOT / "reports/rapid-development/"
    "rapid-public-dev-anyio-workflow-ab-20260824-r10-cbe3f560b03b.jsonl"
)
TASK_V5 = ROOT / "fixtures/task-packages/anyio-interrupt-runner-cleanup-v5/public.yaml"
R19 = (
    ROOT / "reports/rapid-development/"
    "rapid-public-dev-anyio-v5-plan-feedback-ab-20260828-r19-ed5c319756ed.jsonl"
)
R19_DIAGNOSIS = (
    ROOT / "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-plan-feedback-ab-20260828-r19-workflow-diagnosis-v1.json"
)


def _build(bundle: Path) -> dict:
    return build_rapid_workflow_diagnosis(
        bundle_path=bundle,
        state_path=STATE,
        public_task_path=TASK,
        repository_root=ROOT,
    )


def _build_r19() -> dict:
    return build_rapid_workflow_diagnosis(
        bundle_path=R19,
        state_path=STATE,
        public_task_path=TASK_V5,
        repository_root=ROOT,
    )


def _rewrite_chain(path: Path, events: list[dict]) -> None:
    previous: str | None = None
    output: list[str] = []
    for event in events:
        body = {key: value for key, value in event.items() if key != "content_hash"}
        body["previous_event_hash"] = previous
        content_hash = sha256_json(body)
        output.append(json.dumps({**body, "content_hash": content_hash}, sort_keys=True))
        previous = content_hash
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def test_bundle_rejects_non_object_events_fail_closed(tmp_path: Path) -> None:
    bundle = tmp_path / "invalid.jsonl"
    bundle.write_text('"batch-started"\n{}\n{}\n', encoding="utf-8")

    with pytest.raises(ContractError, match="event must be an object"):
        _load_bundle(bundle)


def test_diagnosis_is_byte_deterministic_and_public_only() -> None:
    first = _build(R9)
    second = _build(R9)
    assert diagnosis_bytes(first) == diagnosis_bytes(second)
    assert first["evidence_boundary"] == {
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "llm_response_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "state_mutations": 0,
        "added_cost_nanos": 0,
    }


def test_r8_regression_reproduces_edit_and_check_scheduling_failures() -> None:
    value = _build(R8)
    lean = next(item for item in value["variants"] if item["variant"] == "lean-harness-v7")
    assert lean["edit_rejections"] == 46
    assert lean["edit_attempts"] == 63
    assert lean["edit_acceptance_rate"] == "17/63"
    assert lean["upstream_before_target_pass"] == 14


def test_r9_totals_match_bundle_and_separate_harness_contract_failure() -> None:
    value = _build(R9)
    assert value["observed_batch"] == {
        "attempted_rows": 6,
        "agent_rows_started": 6,
        "harness_admission_failures": 0,
        "agent_failures": 6,
        "evaluator_reached": 0,
        "submissions_completed": 0,
        "successes_at_budget": 0,
        "token_terminals": 3,
        "model_calls": 171,
        "tool_calls": 274,
        "model_cost_nanos": 2_882_583_750,
    }
    lean = next(item for item in value["variants"] if item["variant"] == "lean-harness-v8")
    assert lean["terminal_attribution"] == {"harness_runtime_contract_failure": 3}
    assert lean["model_calls"] == 3
    assert lean["tool_calls"] == 0
    assert all(
        row["terminal_attribution"]["model_error_code"] == "input_token_count_mismatch"
        for row in value["rows"]
        if row["variant"] == "lean-harness-v8"
    )


def test_r10_preserves_failed_v10_plan_gate_without_promotion() -> None:
    first = _build(R10)
    second = _build(R10)
    assert diagnosis_bytes(first) == diagnosis_bytes(second)
    assert first["content_hash"] == (
        "sha256:42b6b45d8fda3e36c53a2267e324f188a72134a0e869702d1ff81f672af082c6"
    )
    assert first["observed_batch"] == {
        "attempted_rows": 6,
        "agent_rows_started": 6,
        "harness_admission_failures": 0,
        "agent_failures": 5,
        "evaluator_reached": 1,
        "submissions_completed": 1,
        "successes_at_budget": 1,
        "token_terminals": 0,
        "model_calls": 365,
        "tool_calls": 362,
        "model_cost_nanos": 4_508_519_250,
    }

    variants = {row["variant"]: row for row in first["variants"]}
    assert variants["lean-harness-v8"] == {
        "variant": "lean-harness-v8",
        "rows": 3,
        "evaluator_reached": 1,
        "submissions_completed": 1,
        "successes_at_budget": 1,
        "model_calls": 93,
        "tool_calls": 91,
        "model_cost_nanos": 1_332_644_250,
        "edit_attempts": 15,
        "edit_rejections": 6,
        "edit_acceptance_rate": "9/15",
        "upstream_before_target_pass": 0,
        "terminal_attribution": {"agent_execution_terminal": 2, "completed": 1},
    }
    assert variants["lean-harness-v10"] == {
        "variant": "lean-harness-v10",
        "rows": 3,
        "evaluator_reached": 0,
        "submissions_completed": 0,
        "successes_at_budget": 0,
        "model_calls": 272,
        "tool_calls": 271,
        "model_cost_nanos": 3_175_875_000,
        "edit_attempts": 0,
        "edit_rejections": 0,
        "edit_acceptance_rate": "0/0",
        "upstream_before_target_pass": 0,
        "terminal_attribution": {"agent_execution_terminal": 3},
    }

    store = ReadOnlyTraceStore(STATE)
    v10_rows = [row for row in first["rows"] if row["variant"] == "lean-harness-v10"]
    rejected_plan_counts: list[int] = []
    for row in v10_rows:
        events = store.list_events(row["run_id"])
        assert not any(event.type == EventType.PLAN_RECORDED for event in events)
        assert row["first_mutation_evidence"]["event_sequence"] is None
        assert row["terminal_attribution"]["message"] == (
            "Lean split budget blocks the exact request"
        )
        rejected = [
            event
            for event in events
            if event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") == "record_work_plan"
        ]
        assert all(
            event.payload.get("error_message")
            == "record_work_plan cites stale or non-public evidence"
            for event in rejected
        )
        rejected_plan_counts.append(len(rejected))
    assert rejected_plan_counts == [88, 67, 86]


def test_r19_driver_v2_projection_is_deterministic_and_separates_infrastructure() -> None:
    first = _build_r19()
    second = _build_r19()
    raw = diagnosis_bytes(first)
    assert raw == diagnosis_bytes(second)
    assert raw == R19_DIAGNOSIS.read_bytes()
    assert len(raw) == 23_559
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == (
        "sha256:eae5b243ec92a520b2649db493cd7c3dd30222fb38b0dd825777ba193eded764"
    )
    assert first["content_hash"] == (
        "sha256:402943ef2e6bada597b7f2bf5779cc60960a49b6c6cfa653480cec4b87033696"
    )
    assert first["observed_batch"] == {
        "attempted_rows": 6,
        "agent_rows_started": 6,
        "harness_admission_failures": 0,
        "agent_failures": 4,
        "evaluator_reached": 1,
        "submissions_completed": 1,
        "successes_at_budget": 0,
        "token_terminals": 0,
        "model_calls": 143,
        "tool_calls": 131,
        "model_cost_nanos": 3_068_239_500,
    }
    assert first["evidence_boundary"] == {
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "llm_response_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "state_mutations": 0,
        "added_cost_nanos": 0,
    }

    rows = {row["order"]: row for row in first["rows"]}
    assert rows[2]["visible_checks"]["passes"] == 3
    assert rows[2]["review_submission"]["completed_get_diff_to_finish"] is True
    assert rows[5]["outcome_kind"] == "infrastructure_error"
    assert rows[5]["terminal_attribution"] == {
        "classification": "infrastructure_error",
        "event_sequence": 168,
        "event_type": "RunFailed",
        "error_code": "RECOVERY_ERROR",
        "model_error_code": None,
        "message": "semantic progress request state differs",
    }
    assert [rows[index]["terminal_attribution"]["error_code"] for index in (3, 6)] == [
        "SEMANTIC_NO_PROGRESS_EVIDENCE_EXHAUSTED",
        "SEMANTIC_NO_PROGRESS_EVIDENCE_EXHAUSTED",
    ]


@pytest.mark.parametrize("failure", ["projection_hash", "order_binding"])
def test_r19_driver_v2_projection_fails_closed(
    tmp_path: Path,
    failure: str,
) -> None:
    events = [json.loads(line) for line in R19.read_text(encoding="utf-8").splitlines()]
    row = next(event for event in events if event.get("event") == "row-terminal")
    if failure == "projection_hash":
        row["projected_row"]["usage"]["model_calls"] += 1
    else:
        row["projected_row"]["order"] = 2
        row["projected_row_hash"] = sha256_json(row["projected_row"])
    selected = tmp_path / f"{failure}.jsonl"
    _rewrite_chain(selected, events)

    with pytest.raises(ContractError, match="driver row projection"):
        _load_bundle(selected)
