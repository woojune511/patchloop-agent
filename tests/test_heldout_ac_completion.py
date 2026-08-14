from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import RunResult, VerdictState
from patchloop.evals import heldout_ac_completion as completion
from patchloop.evals import heldout_ac_persisted_adapter as persisted_adapter
from patchloop.evals.heldout_ac_persisted_adapter import (
    HeldoutACAuthenticatedPersistedEvidence,
    HeldoutACAuthenticatedPersistedRow,
    HeldoutACAuthenticatedQualificationProjection,
    HeldoutACPersistedUsageEvidence,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.util import sha256_json
from tests.test_evaluator_v2_contracts import _v2_chain

ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
EXECUTION_HASH = "sha256:" + "e" * 64
EVALUATOR_SOURCE_HASH = "sha256:" + "a" * 64
SOURCE_QUALIFICATION_HASH = "sha256:" + "b" * 64
RUNTIME_TUPLE_HASH = "sha256:" + "c" * 64
COMPLETION_SOURCE_HASH = "sha256:" + "d" * 64
ANALYSIS_SOURCE_HASH = "sha256:" + "f" * 64


def _sha(label: str) -> str:
    return sha256_json({"test": label})


def _usage(order: int) -> dict[str, Any]:
    input_tokens = 100 + order
    cached_input_tokens = 10
    output_tokens = 10
    cost_nanos = (
        (input_tokens - cached_input_tokens) * 750
        + cached_input_tokens * 75
        + output_tokens * 4_500
    )
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "cache_write_input_tokens": 0,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": 5,
        "model_cost_usd": cost_nanos / 1_000_000_000,
        "model_calls": 2,
        "input_token_count_calls": 2,
        "tool_calls": 3,
        "wall_clock_ms": 4_000,
    }


def _run_result(
    *,
    order: int,
    task_id: str,
    run_id: str,
    success: bool = True,
) -> dict[str, Any]:
    state = VerdictState.PASS if success else VerdictState.FAIL
    payload = deepcopy(_v2_chain(state).result.model_dump(mode="json"))
    payload["run_id"] = run_id
    payload["evaluator_contract"]["task_id"] = task_id
    payload["evaluator_contract"]["evaluator_source_hash"] = EVALUATOR_SOURCE_HASH
    payload["usage"] = _usage(order)
    for verifier in payload["verifier_results"]:
        verifier["run_id"] = run_id
    return RunResult.model_validate(payload).model_dump(mode="json")


def _agent_result(*, order: int, task_id: str, run_id: str) -> dict[str, Any]:
    payload = _run_result(order=order, task_id=task_id, run_id=run_id)
    payload.update(
        {
            "agent_submission_status": "failed",
            "evaluation_status": "not_run",
            "scope_compliant_success": False,
            "verdicts": {
                "hidden_tests": "not_run",
                "regression_tests": "not_run",
                "scope_policy": "not_run",
                "safety_policy": "not_run",
            },
            "submitted_patch_artifact_id": None,
            "submitted_patch_artifact": None,
            "verifier_results": [],
            "outcome_kind": "agent_failure",
            "terminal_error": {"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"},
            "safety_evidence_bundle": None,
            "safety_evidence_bundle_hash": None,
            "safety_evidence": [],
        }
    )
    return RunResult.model_validate(payload).model_dump(mode="json")


def _qualification(
    *,
    suite: Any,
    expected: Any,
    run_id: str,
    schedule_row_id: str,
    outcome_kind: str,
    evaluator_completed: bool,
) -> dict[str, Any]:
    body = {
        "schema_version": "heldout-ac-trace-qualification-contract-fixture-v1",
        "source_schema_version": "heldout-ac-trace-qualification-v1",
        "run_id": run_id,
        "qualified": True,
        "trace_integrity_passed": True,
        "leakage_scan_passed": True,
        "evaluation_reached": evaluator_completed,
        "outcome_kind": outcome_kind,
        "purpose": "core-ac-heldout",
        "experiment_id": suite.suite_id,
        "dataset_role": expected.role,
        "task_id": expected.task_id,
        "suite_hash": suite.content_hash,
        "execution_hash": EXECUTION_HASH,
        "schedule_row_id": schedule_row_id,
        "memory_condition": expected.condition,
        "source_evidence_hash": _sha(f"source-{expected.order}"),
        "qualification_hash": _sha(f"qualification-{expected.order}"),
        "evaluator_version": "v2",
        "evaluator_v2_source_hash": EVALUATOR_SOURCE_HASH,
        "evaluator_v2_source_qualification_hash": SOURCE_QUALIFICATION_HASH,
        "evaluator_v2_receipt_hash": (
            _sha(f"receipt-{expected.order}") if evaluator_completed else None
        ),
        "evaluator_v2_receipt_file_hash": (
            _sha(f"receipt-file-{expected.order}") if evaluator_completed else None
        ),
        "evaluator_v2_runtime_authenticated": evaluator_completed,
        "evaluator_v2_completion_eligible": evaluator_completed,
    }
    return {**body, "content_hash": sha256_json(body)}


def _settlement(
    *,
    order: int,
    result: dict[str, Any],
    qualification: dict[str, Any],
) -> dict[str, Any]:
    usage = {
        key: result["usage"][key]
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "model_calls",
            "input_token_count_calls",
            "tool_calls",
            "wall_clock_ms",
        )
    }
    uncached = usage["input_tokens"] - usage["cached_input_tokens"]
    cost_nanos = (
        uncached * 750
        + usage["cached_input_tokens"] * 75
        + usage["cache_write_input_tokens"] * 750
        + usage["output_tokens"] * 4_500
    )
    body = {
        "schema_version": "heldout-ac-row-settlement-v1",
        "settled": True,
        "usage": usage,
        "token_derived_cost_nanos": cost_nanos,
        "persisted_result_file_hash": _sha(f"result-file-{order}"),
        "persisted_result_semantic_hash": sha256_json(result),
        "qualification_file_hash": _sha(f"qualification-file-{order}"),
        "usage_evidence_hash": _sha(f"usage-{order}"),
        "qualification_projection_hash": qualification["content_hash"],
        "source_evidence_hash": qualification["source_evidence_hash"],
        "evaluator_v2_receipt_file_hash": qualification["evaluator_v2_receipt_file_hash"],
    }
    return {**body, "content_hash": sha256_json(body)}


def _completion_input() -> tuple[Any, dict[str, Any]]:
    suite = load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    rows: list[dict[str, Any]] = []
    for expected in suite.schedule:
        order = expected.order
        run_id = f"run_heldout_{order:02d}"
        schedule_row_id = completion.heldout_ac_schedule_row_id(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            order=order,
        )
        result = _run_result(order=order, task_id=expected.task_id, run_id=run_id)
        qualification = _qualification(
            suite=suite,
            expected=expected,
            run_id=run_id,
            schedule_row_id=schedule_row_id,
            outcome_kind="resolved",
            evaluator_completed=True,
        )
        rows.append(
            {
                "order": order,
                "wave": expected.wave,
                "schedule_row_id": schedule_row_id,
                "task_id": expected.task_id,
                "role": expected.role,
                "condition": expected.condition,
                "repetition": expected.repetition,
                "attempt_status": "terminal",
                "run_id": run_id,
                "retry_performed": False,
                "replacement_performed": False,
                "resume_performed": False,
                "infrastructure_error": None,
                "qualification_error": None,
                "diagnostic_error": None,
                "result": result,
                "terminal_classification": None,
                "qualification": qualification,
                "settlement": _settlement(
                    order=order,
                    result=result,
                    qualification=qualification,
                ),
            }
        )

    runtime_schedule = [
        {
            key: row[key]
            for key in (
                "order",
                "wave",
                "schedule_row_id",
                "task_id",
                "role",
                "condition",
                "repetition",
            )
        }
        for row in rows
    ]
    schedule_hash = sha256_json(runtime_schedule)
    cost_body = {
        "schema_version": "heldout-ac-full-schedule-cost-qualification-v1",
        "passed": True,
        "fully_settled": True,
        "full_schedule_reserved": True,
        "reserved_runs": 48,
        "settled_runs": 48,
        "not_started_runs": 0,
        "unsettled_runs": 0,
        "cost_censoring_events": 0,
        "accrued_cost_nanos": sum(row["settlement"]["token_derived_cost_nanos"] for row in rows),
        "full_schedule_reserve_nanos": 252_000_000_000,
        "hard_cap_nanos": 275_000_000_000,
        "schedule_hash": schedule_hash,
        "campaign_cost_control_hash": completion.heldout_ac_campaign_cost_control_hash(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            schedule_hash=schedule_hash,
        ),
        "live_resume_supported": False,
    }
    body = {
        "schema_version": "heldout-ac-completion-contract-fixture-v1",
        "evidence_status": "offline-untrusted-contract-fixture",
        "persisted_evidence_authenticated": False,
        "source_qualification_present": False,
        "execution_candidate_present": False,
        "paid_approval_present": False,
        "provider_execution_authorized": False,
        "analysis_claim_authorized": False,
        "preregistration_id": completion.PREREGISTRATION_ID,
        "preregistration_content_hash": completion.PREREGISTRATION_CONTENT_HASH,
        "suite_id": suite.suite_id,
        "suite_content_hash": suite.content_hash,
        "execution_candidate_hash": EXECUTION_HASH,
        "execution_hash": EXECUTION_HASH,
        "runtime_tuple_hash": RUNTIME_TUPLE_HASH,
        "evaluator_source_hash": EVALUATOR_SOURCE_HASH,
        "evaluator_source_qualification_hash": SOURCE_QUALIFICATION_HASH,
        "completion_adapter_source_hash": COMPLETION_SOURCE_HASH,
        "analysis_source_hash": ANALYSIS_SOURCE_HASH,
        "rows": rows,
        "campaign_cost_qualification": {
            **cost_body,
            "content_hash": sha256_json(cost_body),
        },
    }
    return suite, {**body, "content_hash": sha256_json(body)}


def _rehash(payload: dict[str, Any]) -> None:
    for row in payload["rows"]:
        terminal = row.get("terminal_classification")
        if isinstance(terminal, dict):
            terminal["content_hash"] = sha256_json(
                {key: value for key, value in terminal.items() if key != "content_hash"}
            )
        qualification = row["qualification"]
        qualification["content_hash"] = sha256_json(
            {key: value for key, value in qualification.items() if key != "content_hash"}
        )
        settlement = row["settlement"]
        settlement["qualification_projection_hash"] = qualification["content_hash"]
        settlement["persisted_result_semantic_hash"] = sha256_json(row["result"])
        settlement["content_hash"] = sha256_json(
            {key: value for key, value in settlement.items() if key != "content_hash"}
        )
    cost = payload["campaign_cost_qualification"]
    cost["content_hash"] = sha256_json(
        {key: value for key, value in cost.items() if key != "content_hash"}
    )
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )


def test_complete_evaluator_matrix_projects_to_unofficial_contract_preview() -> None:
    suite, payload = _completion_input()

    projected = completion.project_heldout_ac_completion_contract_fixture(
        suite=suite, completion=payload
    )
    report = completion.build_heldout_ac_completion_contract_report(projected)
    envelope = completion.preview_heldout_ac_completion_analysis(projected)

    assert projected.evaluator_completed_runs == 48
    assert projected.typed_agent_terminal_runs == 0
    assert projected.task_successes == 48
    assert report.disposition == "offline_complete_matrix_contract_fixture"
    assert report.official is False
    assert report.analysis_ready is False
    assert projected.persisted_evidence_authenticated is False
    assert projected.source_qualification_present is False
    assert projected.execution_candidate_present is False
    assert projected.official is False
    assert projected.analysis_ready is False
    assert envelope.analysis.complete_panel is True
    assert envelope.official is False
    assert envelope.analysis_ready is False
    assert envelope.analysis_claim_authorized is False
    assert envelope.analysis.primary_estimate.model_dump() == {
        "numerator": 0,
        "denominator": 1,
    }
    assert envelope.completion_projection_hash == projected.content_hash
    assert envelope.execution_hash == EXECUTION_HASH
    assert envelope.analysis_source_hash == ANALYSIS_SOURCE_HASH


def test_evaluator_fail_is_an_eligible_zero() -> None:
    suite, payload = _completion_input()
    row = payload["rows"][0]
    row["result"] = _run_result(
        order=1,
        task_id=row["task_id"],
        run_id=row["run_id"],
        success=False,
    )
    row["qualification"]["outcome_kind"] = "task_failure"
    _rehash(payload)

    projected = completion.project_heldout_ac_completion_contract_fixture(
        suite=suite, completion=payload
    )

    assert projected.task_successes == 47
    assert projected.task_failures == 1
    assert projected.outcome_projection.rows[0].outcome.safety_verdict == "FAIL"


def test_typed_pre_evaluator_agent_terminal_is_an_eligible_zero() -> None:
    suite, payload = _completion_input()
    row = payload["rows"][1]
    row["result"] = _agent_result(order=2, task_id=row["task_id"], run_id=row["run_id"])
    terminal_body = {
        "schema_version": "heldout-ac-agent-terminal-classification-v1",
        "terminal_type": "token-budget-exhaustion",
        "terminal_evidence_hash": _sha("terminal-2"),
        "failure_record_id": "fail_heldout_02",
        "failure_record_hash": _sha("failure-2"),
    }
    row["terminal_classification"] = {
        **terminal_body,
        "content_hash": sha256_json(terminal_body),
    }
    row["qualification"].update(
        {
            "evaluation_reached": False,
            "outcome_kind": "agent_failure",
            "evaluator_v2_receipt_hash": None,
            "evaluator_v2_receipt_file_hash": None,
            "evaluator_v2_runtime_authenticated": False,
            "evaluator_v2_completion_eligible": False,
        }
    )
    row["settlement"]["evaluator_v2_receipt_file_hash"] = None
    _rehash(payload)

    projected = completion.project_heldout_ac_completion_contract_fixture(
        suite=suite, completion=payload
    )
    envelope = completion.preview_heldout_ac_completion_analysis(projected)

    assert projected.evaluator_completed_runs == 47
    assert projected.typed_agent_terminal_runs == 1
    assert projected.task_successes == 47
    assert envelope.analysis.eligible_rows == 48


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["rows"].pop(),
        lambda payload: payload["rows"][0].__setitem__("order", True),
        lambda payload: payload["rows"][0].__setitem__("schedule_row_id", _sha("arbitrary")),
        lambda payload: payload["rows"][0].__setitem__("retry_performed", True),
        lambda payload: payload["rows"][0]["qualification"].__setitem__(
            "source_schema_version", "trace-qualification-v2"
        ),
        lambda payload: payload["rows"][0]["qualification"].__setitem__(
            "evaluator_v2_source_hash", _sha("other-source")
        ),
        lambda payload: payload["rows"][0]["qualification"].__setitem__(
            "evaluator_v2_receipt_hash", "x"
        ),
        lambda payload: payload["rows"][0]["settlement"].__setitem__("token_derived_cost_nanos", 0),
        lambda payload: payload["rows"][0]["settlement"]["usage"].__setitem__(
            "cached_input_tokens", 10.0
        ),
        lambda payload: payload["campaign_cost_qualification"].__setitem__(
            "campaign_cost_control_hash", _sha("arbitrary-cost-control")
        ),
        lambda payload: payload["campaign_cost_qualification"].__setitem__("settled_runs", 48.0),
        lambda payload: payload.__setitem__("source_qualification_present", True),
    ],
)
def test_completion_fails_closed_on_contract_drift(mutation) -> None:
    suite, payload = _completion_input()
    mutation(payload)
    _rehash(payload)

    with pytest.raises(completion.HeldoutACCompletionError):
        completion.project_heldout_ac_completion_contract_fixture(suite=suite, completion=payload)


def test_completion_rejects_reduced_run_result_impersonating_v2() -> None:
    suite, payload = _completion_input()
    payload["rows"][0]["result"] = {
        "schema_version": "run-result-v2",
        "run_id": payload["rows"][0]["run_id"],
        "official": False,
    }
    _rehash(payload)

    with pytest.raises(completion.HeldoutACCompletionError, match="run-result-v2"):
        completion.project_heldout_ac_completion_contract_fixture(suite=suite, completion=payload)


def test_analysis_preview_rejects_raw_mapping() -> None:
    suite, payload = _completion_input()
    projected = completion.project_heldout_ac_completion_contract_fixture(
        suite=suite, completion=payload
    )

    with pytest.raises(completion.HeldoutACCompletionError, match="typed contract"):
        completion.preview_heldout_ac_completion_analysis(  # type: ignore[arg-type]
            projected.model_dump(mode="json")
        )


def test_typed_projection_recomputes_counts_from_nested_outcomes() -> None:
    suite, payload = _completion_input()
    projected = completion.project_heldout_ac_completion_contract_fixture(
        suite=suite, completion=payload
    )
    drifted = projected.model_dump(mode="json")
    drifted["task_successes"] = 0
    drifted["task_failures"] = 48
    drifted["content_hash"] = sha256_json(
        {key: value for key, value in drifted.items() if key != "content_hash"}
    )

    with pytest.raises(ValueError, match="nested outcome projection"):
        completion.HeldoutACCompletionProjection.model_validate(drifted)


def _authenticated_persisted_rows():
    suite, payload = _completion_input()
    rows: list[HeldoutACAuthenticatedPersistedEvidence] = []
    prices = {
        "uncached_input": 750,
        "cached_input": 75,
        "cache_write_input": 750,
        "output": 4_500,
    }
    for fixture in payload["rows"]:
        order = fixture["order"]
        result = RunResult.model_validate(fixture["result"])
        qualification_hash = _sha(f"source-qualification-{order}")
        source_evidence_hash = _sha(f"source-evidence-{order}")
        persisted_result_file_hash = _sha(f"result-file-{order}")
        usage = fixture["settlement"]["usage"]
        usage_body = {
            "schema_version": "heldout-ac-durable-usage-evidence-v1",
            "run_id": result.run_id,
            "schedule_row_id": fixture["schedule_row_id"],
            "pricing_binding_hash": _sha("pricing"),
            "price_nanos_per_token": prices,
            "usage": usage,
            "token_derived_cost_nanos": fixture["settlement"]["token_derived_cost_nanos"],
            "qualification_hash": qualification_hash,
            "source_evidence_hash": source_evidence_hash,
            "persisted_result_file_hash": persisted_result_file_hash,
            "evaluator_v2_receipt_file_hash": fixture["qualification"][
                "evaluator_v2_receipt_file_hash"
            ],
        }
        usage_evidence = HeldoutACPersistedUsageEvidence(
            **usage_body,
            content_hash=sha256_json(usage_body),
        )
        qualification_body = {
            "schema_version": "heldout-ac-authenticated-trace-qualification-projection-v2",
            "source_schema_version": "trace-qualification-v2",
            "run_id": result.run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "outcome_kind": result.outcome_kind.value,
            "purpose": "core",
            "experiment_id": suite.suite_id,
            "dataset_role": fixture["role"],
            "task_id": fixture["task_id"],
            "suite_hash": suite.content_hash,
            "execution_hash": EXECUTION_HASH,
            "schedule_row_id": fixture["schedule_row_id"],
            "memory_condition": fixture["condition"],
            "source_evidence_hash": source_evidence_hash,
            "source_qualification_hash": qualification_hash,
            "check_count": 28,
            "checks_hash": _sha(f"checks-{order}"),
            "evaluator_version": "v2",
            "evaluator_v2_source_hash": EVALUATOR_SOURCE_HASH,
            "evaluator_v2_source_qualification_hash": SOURCE_QUALIFICATION_HASH,
            "evaluator_v2_receipt_hash": fixture["qualification"]["evaluator_v2_receipt_hash"],
            "evaluator_v2_receipt_file_hash": fixture["qualification"][
                "evaluator_v2_receipt_file_hash"
            ],
            "evaluator_v2_runtime_authenticated": True,
            "evaluator_v2_completion_eligible": True,
        }
        qualification = HeldoutACAuthenticatedQualificationProjection(
            **qualification_body,
            content_hash=sha256_json(qualification_body),
        )
        row_body = {
            "schema_version": "heldout-ac-authenticated-persisted-row-v1",
            "persisted_evidence_authenticated": True,
            "order": order,
            "wave": fixture["wave"],
            "task_id": fixture["task_id"],
            "role": fixture["role"],
            "condition": fixture["condition"],
            "repetition": fixture["repetition"],
            "run_id": result.run_id,
            "schedule_row_id": fixture["schedule_row_id"],
            "execution_hash": EXECUTION_HASH,
            "task_evaluator_binding_hash": _sha(f"task-binding-{order}"),
            "persisted_result_file_hash": persisted_result_file_hash,
            "persisted_result_semantic_hash": sha256_json(result.model_dump(mode="json")),
            "qualification_file_hash": _sha(f"qualification-file-{order}"),
            "qualification_hash": qualification_hash,
            "source_evidence_hash": source_evidence_hash,
            "usage_evidence_file_hash": _sha(f"usage-file-{order}"),
            "usage_evidence_hash": usage_evidence.content_hash,
            "evaluator_v2_receipt_hash": fixture["qualification"]["evaluator_v2_receipt_hash"],
            "evaluator_v2_receipt_file_hash": fixture["qualification"][
                "evaluator_v2_receipt_file_hash"
            ],
            "result": result.model_dump(mode="json"),
            "usage_evidence": usage_evidence.model_dump(mode="json"),
        }
        row = HeldoutACAuthenticatedPersistedRow(
            **row_body,
            content_hash=sha256_json(row_body),
        )
        evidence_body = {
            "schema_version": "heldout-ac-authenticated-persisted-evidence-v4",
            "persisted_evidence_authenticated": True,
            "official": False,
            "analysis_eligible": False,
            "row": row.model_dump(mode="json"),
            "qualification": qualification.model_dump(mode="json"),
            "terminal_type": None,
            "terminal_event": None,
        }
        rows.append(
            HeldoutACAuthenticatedPersistedEvidence(
                **evidence_body,
                content_hash=sha256_json(evidence_body),
            )
        )
    return suite, rows


def _runtime_authenticated_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, list[HeldoutACAuthenticatedPersistedEvidence]]:
    suite, projected_rows = _authenticated_persisted_rows()
    queued_rows = iter(projected_rows)
    monkeypatch.setattr(
        persisted_adapter,
        "_load_and_project_heldout_ac_persisted_evidence",
        lambda **_kwargs: next(queued_rows),
    )
    authenticated_rows = [
        persisted_adapter.authenticate_heldout_ac_persisted_evidence(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_pricing_binding_hash=_sha("pricing"),
            order=order,
            task_evaluator_binding=object(),  # type: ignore[arg-type]
            run_root=ROOT,
            task_dir=ROOT,
            dataset_manifest_path=ROOT,
            evaluator_authority=object(),  # type: ignore[arg-type]
            usage_evidence_relative_path="unused.json",
        )
        for order in range(1, 49)
    ]
    assert all(type(row) is HeldoutACAuthenticatedPersistedEvidence for row in authenticated_rows)
    return suite, authenticated_rows  # type: ignore[return-value]


def test_directly_constructed_typed_rows_cannot_open_official_analysis() -> None:
    suite, rows = _authenticated_persisted_rows()

    with pytest.raises(completion.HeldoutACCompletionError, match="runtime-issued"):
        completion.project_authenticated_heldout_ac_completion(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_pricing_binding_hash=_sha("pricing"),
            evaluator_source_hash=EVALUATOR_SOURCE_HASH,
            evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
            rows=rows,
        )


def test_authenticated_completion_is_the_only_official_analysis_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite, rows = _runtime_authenticated_rows(monkeypatch)
    projected = completion.project_authenticated_heldout_ac_completion(
        suite=suite,
        execution_hash=EXECUTION_HASH,
        expected_pricing_binding_hash=_sha("pricing"),
        evaluator_source_hash=EVALUATOR_SOURCE_HASH,
        evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
        rows=rows,
    )
    envelope = completion.analyze_authenticated_heldout_ac_completion(projected)

    assert projected.official is True
    assert projected.analysis_ready is True
    assert projected.evaluator_completed_runs == 48
    assert projected.accrued_cost_nanos == sum(
        row.row.usage_evidence.token_derived_cost_nanos for row in rows
    )
    assert projected.full_schedule_reserve_nanos == 252_000_000_000
    assert projected.hard_cap_nanos == 275_000_000_000
    assert envelope.official is True
    assert envelope.analysis.eligible_rows == 48
    assert envelope.suite_content_hash == suite.content_hash
    assert envelope.execution_hash == EXECUTION_HASH
    assert envelope.evaluator_source_hash == EVALUATOR_SOURCE_HASH
    assert envelope.evaluator_source_qualification_hash == SOURCE_QUALIFICATION_HASH
    assert envelope.completion_projection_hash == projected.content_hash

    with pytest.raises(completion.HeldoutACCompletionError, match="typed authenticated"):
        completion.analyze_authenticated_heldout_ac_completion(  # type: ignore[arg-type]
            projected.model_dump(mode="json")
        )
    reconstructed = completion.HeldoutACAuthenticatedCompletionProjection.model_validate(
        projected.model_dump()
    )
    with pytest.raises(completion.HeldoutACCompletionError, match="adapter-issued"):
        completion.analyze_authenticated_heldout_ac_completion(reconstructed)


def test_serialization_revalidation_and_copy_strip_runtime_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite, rows = _runtime_authenticated_rows(monkeypatch)
    reparsed = [
        HeldoutACAuthenticatedPersistedEvidence.model_validate(row.model_dump(mode="json"))
        for row in rows
    ]
    copied = [row.model_copy() for row in rows]

    for unauthoritative in (reparsed, copied):
        with pytest.raises(completion.HeldoutACCompletionError, match="runtime-issued"):
            completion.project_authenticated_heldout_ac_completion(
                suite=suite,
                execution_hash=EXECUTION_HASH,
                expected_pricing_binding_hash=_sha("pricing"),
                evaluator_source_hash=EVALUATOR_SOURCE_HASH,
                evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
                rows=unauthoritative,
            )


def test_persisted_completion_replay_recomputes_without_reissuing_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite, runtime_rows = _runtime_authenticated_rows(monkeypatch)
    projected = completion.project_authenticated_heldout_ac_completion(
        suite=suite,
        execution_hash=EXECUTION_HASH,
        expected_pricing_binding_hash=_sha("pricing"),
        evaluator_source_hash=EVALUATOR_SOURCE_HASH,
        evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
        rows=runtime_rows,
    )
    envelope = completion.analyze_authenticated_heldout_ac_completion(projected)
    persisted_rows = [
        HeldoutACAuthenticatedPersistedEvidence.model_validate(row.model_dump(mode="json"))
        for row in runtime_rows
    ]
    persisted_completion = completion.HeldoutACAuthenticatedCompletionProjection.model_validate(
        projected.model_dump()
    )
    persisted_envelope = completion.HeldoutACOfficialAnalysisEnvelope.model_validate(
        envelope.model_dump()
    )

    assert (
        completion.validate_persisted_heldout_ac_completion_replay(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_pricing_binding_hash=_sha("pricing"),
            evaluator_source_hash=EVALUATOR_SOURCE_HASH,
            evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
            rows=persisted_rows,
            completion=persisted_completion,
            official_envelope=persisted_envelope,
        )
        is None
    )

    drifted_rows = list(persisted_rows)
    drifted_evidence = drifted_rows[0].model_dump(mode="json")
    drifted_row = drifted_evidence["row"]
    drifted_usage = drifted_row["usage_evidence"]
    drifted_usage["price_nanos_per_token"] = {
        "uncached_input": 0,
        "cached_input": 0,
        "cache_write_input": 0,
        "output": 0,
    }
    drifted_usage["token_derived_cost_nanos"] = 0
    drifted_usage["content_hash"] = sha256_json(
        {key: value for key, value in drifted_usage.items() if key != "content_hash"}
    )
    drifted_row["usage_evidence_hash"] = drifted_usage["content_hash"]
    drifted_row["content_hash"] = sha256_json(
        {key: value for key, value in drifted_row.items() if key != "content_hash"}
    )
    drifted_evidence["content_hash"] = sha256_json(
        {key: value for key, value in drifted_evidence.items() if key != "content_hash"}
    )
    drifted_rows[0] = HeldoutACAuthenticatedPersistedEvidence.model_validate(drifted_evidence)
    with pytest.raises(completion.HeldoutACCompletionError, match="usage evidence differs"):
        completion.validate_persisted_heldout_ac_completion_replay(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_pricing_binding_hash=_sha("pricing"),
            evaluator_source_hash=EVALUATOR_SOURCE_HASH,
            evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
            rows=drifted_rows,
            completion=persisted_completion,
            official_envelope=persisted_envelope,
        )
    with pytest.raises(completion.HeldoutACCompletionError, match="adapter-issued"):
        completion.analyze_authenticated_heldout_ac_completion(persisted_completion)

    drifted_body = persisted_envelope.model_dump(mode="json")
    drifted_body["completion_projection_hash"] = _sha("wrong-completion")
    drifted_body["content_hash"] = sha256_json(
        {key: value for key, value in drifted_body.items() if key != "content_hash"}
    )
    drifted_envelope = completion.HeldoutACOfficialAnalysisEnvelope.model_validate(drifted_body)
    with pytest.raises(completion.HeldoutACCompletionError, match="envelope replay differs"):
        completion.validate_persisted_heldout_ac_completion_replay(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_pricing_binding_hash=_sha("pricing"),
            evaluator_source_hash=EVALUATOR_SOURCE_HASH,
            evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
            rows=persisted_rows,
            completion=persisted_completion,
            official_envelope=drifted_envelope,
        )


def test_authenticated_completion_rejects_legacy_or_reduced_row_inputs() -> None:
    suite, rows = _authenticated_persisted_rows()
    raw_rows = [row.model_dump(mode="json") for row in rows]

    with pytest.raises(completion.HeldoutACCompletionError, match="typed persisted-evidence"):
        completion.project_authenticated_heldout_ac_completion(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_pricing_binding_hash=_sha("pricing"),
            evaluator_source_hash=EVALUATOR_SOURCE_HASH,
            evaluator_source_qualification_hash=SOURCE_QUALIFICATION_HASH,
            rows=raw_rows,
        )


def _inconclusive_input() -> tuple[Any, dict[str, Any]]:
    suite = load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    prior: list[dict[str, Any]] = []
    trigger = "qualification-or-completion-contract-mismatch"
    for expected in suite.schedule[:4]:
        prior.append(
            {
                **expected.model_dump(mode="json"),
                "schedule_row_id": completion.heldout_ac_schedule_row_id(
                    suite=suite,
                    execution_hash=EXECUTION_HASH,
                    order=expected.order,
                ),
                "attempt_status": "terminal",
                "run_id": f"run_prior_{expected.order:02d}",
                "cost_settled": True,
                "token_derived_cost_nanos": 100,
                "persisted_result_file_hash": _sha(f"prior-result-{expected.order}"),
                "qualification_file_hash": _sha(f"prior-qualification-{expected.order}"),
                "settlement_evidence_hash": _sha(f"prior-settlement-{expected.order}"),
                "retry_performed": False,
                "replacement_performed": False,
                "resume_performed": False,
            }
        )
    expected = suite.schedule[4]
    confound = {
        **expected.model_dump(mode="json"),
        "schedule_row_id": completion.heldout_ac_schedule_row_id(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            order=expected.order,
        ),
        "attempt_status": "terminal",
        "run_id": "run_confound_05",
        "trigger": trigger,
        "confound_evidence_hash": _sha("confound-5"),
        "cost_settled": False,
        "token_derived_cost_nanos": None,
        "retry_performed": False,
        "replacement_performed": False,
        "resume_performed": False,
    }
    remaining = [
        {
            **expected.model_dump(mode="json"),
            "schedule_row_id": completion.heldout_ac_schedule_row_id(
                suite=suite,
                execution_hash=EXECUTION_HASH,
                order=expected.order,
            ),
            "attempt_status": "not_started",
            "run_id": None,
            "reason": "campaign-halted-after-prespecified-confound",
            "trigger": trigger,
            "retry_performed": False,
            "replacement_performed": False,
            "resume_performed": False,
        }
        for expected in suite.schedule[5:]
    ]
    all_rows = [*prior, confound, *remaining]
    runtime_schedule = [
        {
            key: row[key]
            for key in (
                "order",
                "wave",
                "schedule_row_id",
                "task_id",
                "role",
                "condition",
                "repetition",
            )
        }
        for row in all_rows
    ]
    schedule_hash = sha256_json(runtime_schedule)
    body = {
        "schema_version": "heldout-ac-inconclusive-input-v1",
        "evidence_status": "offline-untrusted-contract-fixture",
        "persisted_evidence_authenticated": False,
        "source_qualification_present": False,
        "execution_candidate_present": False,
        "paid_approval_present": False,
        "provider_execution_authorized": False,
        "preregistration_id": completion.PREREGISTRATION_ID,
        "preregistration_content_hash": completion.PREREGISTRATION_CONTENT_HASH,
        "suite_id": suite.suite_id,
        "suite_content_hash": suite.content_hash,
        "execution_candidate_hash": EXECUTION_HASH,
        "execution_hash": EXECUTION_HASH,
        "runtime_tuple_hash": RUNTIME_TUPLE_HASH,
        "evaluator_source_hash": EVALUATOR_SOURCE_HASH,
        "evaluator_source_qualification_hash": SOURCE_QUALIFICATION_HASH,
        "completion_adapter_source_hash": COMPLETION_SOURCE_HASH,
        "analysis_source_hash": ANALYSIS_SOURCE_HASH,
        "prior_eligible_terminals": prior,
        "first_confounded_row": confound,
        "remaining_not_started_rows": remaining,
        "cost_boundary_phase": "not-applicable",
        "full_schedule_reserved": True,
        "reserved_runs": 48,
        "settled_runs": 4,
        "not_started_runs": 43,
        "unsettled_runs": 1,
        "accrued_cost_nanos": 400,
        "schedule_hash": schedule_hash,
        "campaign_cost_control_hash": completion.heldout_ac_campaign_cost_control_hash(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            schedule_hash=schedule_hash,
        ),
    }
    return suite, {**body, "content_hash": sha256_json(body)}


def test_inconclusive_stop_path_seals_without_primary_analysis() -> None:
    suite, payload = _inconclusive_input()

    report = completion.project_heldout_ac_inconclusive_contract_fixture(suite=suite, value=payload)

    assert report.disposition == "offline_inconclusive_matrix_contract_fixture"
    assert report.official is False
    assert report.analysis_ready is False
    assert report.cost_boundary_phase == "not-applicable"
    assert report.full_schedule_reserved is True
    assert report.reserved_runs == 48
    assert report.first_confound_order == 5
    assert report.primary_outcome_projection is None
    assert report.eligible_terminal_rows == 4
    assert report.not_started_rows == 43
    assert report.unsettled_rows == 1


def test_inconclusive_stop_path_rejects_wrong_not_started_trigger() -> None:
    suite, payload = _inconclusive_input()
    payload["remaining_not_started_rows"][0]["trigger"] = "private-marker-or-leakage-hit"
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )

    with pytest.raises(completion.HeldoutACCompletionError, match="another confound"):
        completion.project_heldout_ac_inconclusive_contract_fixture(suite=suite, value=payload)


def test_pre_reservation_failure_is_representable_without_a_receipt() -> None:
    suite, payload = _inconclusive_input()
    trigger = "full-schedule-reservation-or-hard-cap-boundary-failure"
    first = suite.schedule[0]
    payload["prior_eligible_terminals"] = []
    payload["first_confounded_row"] = {
        **first.model_dump(mode="json"),
        "schedule_row_id": completion.heldout_ac_schedule_row_id(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            order=1,
        ),
        "attempt_status": "not_started",
        "run_id": None,
        "trigger": trigger,
        "confound_evidence_hash": _sha("pre-reservation-boundary"),
        "cost_settled": False,
        "token_derived_cost_nanos": None,
        "retry_performed": False,
        "replacement_performed": False,
        "resume_performed": False,
    }
    payload["remaining_not_started_rows"] = [
        {
            **expected.model_dump(mode="json"),
            "schedule_row_id": completion.heldout_ac_schedule_row_id(
                suite=suite,
                execution_hash=EXECUTION_HASH,
                order=expected.order,
            ),
            "attempt_status": "not_started",
            "run_id": None,
            "reason": "campaign-halted-after-prespecified-confound",
            "trigger": trigger,
            "retry_performed": False,
            "replacement_performed": False,
            "resume_performed": False,
        }
        for expected in suite.schedule[1:]
    ]
    all_rows = [payload["first_confounded_row"], *payload["remaining_not_started_rows"]]
    runtime_schedule = [
        {
            key: row[key]
            for key in (
                "order",
                "wave",
                "schedule_row_id",
                "task_id",
                "role",
                "condition",
                "repetition",
            )
        }
        for row in all_rows
    ]
    payload.update(
        {
            "cost_boundary_phase": "pre-reservation",
            "full_schedule_reserved": False,
            "reserved_runs": 0,
            "settled_runs": 0,
            "not_started_runs": 48,
            "unsettled_runs": 0,
            "accrued_cost_nanos": 0,
            "schedule_hash": sha256_json(runtime_schedule),
            "campaign_cost_control_hash": None,
        }
    )
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )

    report = completion.project_heldout_ac_inconclusive_contract_fixture(suite=suite, value=payload)

    assert report.cost_boundary_phase == "pre-reservation"
    assert report.full_schedule_reserved is False
    assert report.reserved_runs == 0
    assert report.not_started_rows == 48
