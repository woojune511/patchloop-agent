from __future__ import annotations

import copy
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import EventType
from patchloop.evals import budget as budget_module
from patchloop.evals import runner as eval_runner
from patchloop.evals.qualification import (
    _private_leak_tokens,
    calculate_source_evidence_hash,
    load_trace_qualification,
    qualify_run,
)
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / "reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json"
)
CORRECTION_PATH = (
    ROOT
    / "reports/live-pilot/artifacts/"
    "d086-condition-neutral-comparison-pilot-budget-pressure-correction.json"
)
RUNTIME_ROOT = ROOT / ".patchloop"
EXPERIMENT_ID = "dev-validation-condition-neutral-v2v5-pilot-20260803-r1"
RUN_ID = "run_c355405d826641b9"
EXECUTION_HASH = (
    "sha256:7163f6c44aa5b7790d35546be37781248d6575eac60986b2610f2e21c35348a0"
)
TASK_DIR = ROOT / "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes"
REPORT_FILE_SHA256 = (
    "sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464"
)
CORRECTION_FILE_SHA256 = (
    "sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_path(relative: str) -> Path:
    return ROOT / relative


def _skip_without_raw() -> None:
    if not (RUNTIME_ROOT / "state.sqlite3").is_file():
        pytest.skip("local immutable D-085 runtime evidence is unavailable")


def _assert_portable_contract(
    report: dict[str, Any], correction: dict[str, Any]
) -> None:
    assert report["schema_version"] == (
        "condition-neutral-comparison-pilot-d086-evidence-v1"
    )
    report_hash = sha256_text(canonical_json(report["semantic_body"]))
    assert report["semantic_body_hash"] == report_hash
    assert report["report_id"] == f"d086_{report_hash.removeprefix('sha256:')}"

    assert correction["schema_version"] == (
        "condition-neutral-comparison-pilot-budget-pressure-correction-v1"
    )
    correction_hash = sha256_text(canonical_json(correction["semantic_body"]))
    assert correction["semantic_body_hash"] == correction_hash
    assert correction["correction_id"] == (
        f"bpcor_{correction_hash.removeprefix('sha256:')}"
    )

    body = report["semantic_body"]
    claims = body["claims_boundary"]
    assert claims["workflow_readiness_gate_passed"] is True
    assert claims["single_task_resolved"] is True
    assert claims["calibration_only"] is True
    assert claims["no_memory_performance_baseline_established"] is False
    assert claims["success_rate_estimated"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["memory_index_frozen"] is False
    assert claims["core_campaign_unlocked"] is False
    assert claims["analysis_ready"] is False
    assert claims["actual_invoice_or_free_tier_treatment_claimed"] is False
    assert claims["automatic_rerun_authorized"] is False

    next_gate = body["next_gate"]
    assert next_gate["decision_required"] == (
        "separate-12-run-no-memory-cost-cap-decision"
    )
    assert next_gate["current_12_run_cap_usd"] == 20
    assert next_gate["candidate_12_run_cap_usd"] == 88
    assert next_gate["candidate_cap_is_approved"] is False
    assert next_gate["new_campaign_source_commit_required"] is True
    assert next_gate["fresh_no_call_preflight_required"] is True
    assert next_gate["new_execution_hash_required"] is True
    assert next_gate["separate_user_cost_approval_required"] is True
    assert next_gate["automatic_campaign_execution_authorized"] is False

    correction_body = correction["semantic_body"]
    assert correction_body["source_harness_git_commit"] == (
        "629b9fdd9f69d1522cf565a06ae9679abe3f60a7"
    )
    assert correction_body["correction_harness_git_commit"] == (
        "e186f910f3c9eed81c8ec67b4bfc82bffa9bb785"
    )
    assert correction_body["original_observation"] == {
        "schema_version": "budget-pressure-error-v1",
        "run_id": RUN_ID,
        "error": (
            "disabled model/tool call limits require the exact workflow "
            "completion probe, D-081 generic readiness, or frozen "
            "condition-neutral comparison observability contract"
        ),
    }
    corrected = correction_body["corrected_budget_pressure"]
    assert corrected["schema_version"] == "budget-pressure-v1"
    assert corrected["binding_dimension"] == "none"
    assert corrected["binding_reason"] is None
    assert corrected["headroom"]["total_tokens"] == 1_526_799
    assert corrected["headroom"]["wall_clock_ms"] == 1_749_231
    assert correction_body["correction_boundary"][
        "original_readiness_gate_replaced"
    ] is False
    assert correction_body["correction_boundary"][
        "original_readiness_gate_passed"
    ] is True
    assert correction_body["correction_boundary"]["new_provider_call_made"] is False


def test_d086_portable_report_and_correction_internal_hashes() -> None:
    report = _load(REPORT_PATH)
    correction = _load(CORRECTION_PATH)

    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
    assert sha256_bytes(CORRECTION_PATH.read_bytes()) == CORRECTION_FILE_SHA256
    _assert_portable_contract(report, correction)

    body = report["semantic_body"]
    correction_ref = body["budget_pressure_correction"]
    assert correction_ref["artifact_sha256"] == sha256_bytes(
        CORRECTION_PATH.read_bytes()
    )
    assert correction_ref["artifact_bytes"] == CORRECTION_PATH.stat().st_size
    assert correction_ref["correction_id"] == correction["correction_id"]
    assert correction_ref["semantic_body_hash"] == correction["semantic_body_hash"]
    assert body["portable_contract"][
        "self_contained_without_local_runtime_artifacts"
    ] is True


def test_d086_portable_contract_survives_absent_local_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report = copy.deepcopy(_load(REPORT_PATH))
    correction = copy.deepcopy(_load(CORRECTION_PATH))

    monkeypatch.chdir(tmp_path)
    assert not Path(".patchloop").exists()
    _assert_portable_contract(report, correction)


def test_d086_portable_payload_is_leak_safe() -> None:
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    correction_text = CORRECTION_PATH.read_text(encoding="utf-8")
    checked = f"{report_text}\n{correction_text}".lower()
    package = load_task_package(TASK_DIR)

    for token in _private_leak_tokens(package, api_key=None):
        assert token.lower() not in checked
    assert "diff --git" not in checked
    assert "@@ -" not in checked
    assert "openai_api_key" not in checked
    assert "authorization:" not in checked
    assert package.private.reference_patch.sha256 not in checked

    portable = _load(REPORT_PATH)["semantic_body"]["portable_contract"]
    assert portable["private_spec_embedded"] is False
    assert portable["hidden_assertion_embedded"] is False
    assert portable["reference_patch_embedded"] is False
    assert portable["submitted_patch_body_embedded"] is False
    assert portable["api_key_or_authorization_embedded"] is False


def test_d086_raw_files_reconcile_when_present() -> None:
    _skip_without_raw()
    report = _load(REPORT_PATH)["semantic_body"]

    for artifact in report["raw_local_artifacts"]:
        path = _raw_path(artifact["path"])
        assert path.is_file(), artifact["role"]
        assert path.stat().st_size == artifact["bytes"]
        assert sha256_bytes(path.read_bytes()) == artifact["sha256"]

    raw = _load(
        RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json"
    )
    row = raw["runs"][0]
    run_result = _load(
        RUNTIME_ROOT / "artifacts" / "runs" / RUN_ID / "result.json"
    )
    run_manifest = _load(
        RUNTIME_ROOT / "artifacts" / "runs" / RUN_ID / "manifest.json"
    )
    plan = _load(
        RUNTIME_ROOT
        / "experiments"
        / "plans"
        / f"{EXECUTION_HASH.removeprefix('sha256:')}.json"
    )

    assert raw["experiment_id"] == report["experiment"]["experiment_id"]
    assert raw["execution_hash"] == report["experiment"]["execution_hash"]
    assert raw["suite_hash"] == report["experiment"]["suite_hash"]
    assert raw["schedule_hash"] == report["experiment"]["schedule_hash"]
    assert raw["completion_gate"] == report["original_campaign_result"][
        "completion_gate"
    ]
    assert canonical_json(row["result"]) == canonical_json(run_result)
    assert row["run_id"] == RUN_ID
    assert row["schedule_row_id"] == report["experiment"]["schedule_row_id"]
    assert row["usage"] == run_result["usage"]
    assert run_result["verdicts"] == report["run_result"]["verdicts"]
    assert run_result["official"] is True
    assert run_result["scope_compliant_success"] is True

    assert run_manifest["harness_git_commit"] == report["experiment"][
        "source_harness_git_commit"
    ]
    assert run_manifest["experiment"]["execution_hash"] == EXECUTION_HASH
    assert run_manifest["experiment"]["schedule_row_id"] == report["experiment"][
        "schedule_row_id"
    ]
    assert run_manifest["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 1_600_000,
        "wall_clock_timeout_seconds": 1_800,
    }

    suite = eval_runner.ExperimentSuite.model_validate(plan["suite"])
    assert eval_runner._suite_hash(suite) == plan["suite_hash"]
    schedule_row = dict(plan["schedule"][0])
    recorded_row_id = schedule_row.pop("schedule_row_id")
    assert recorded_row_id == sha256_text(
        canonical_json(
            {
                "experiment_id": plan["experiment_id"],
                "purpose": plan["purpose"],
                **schedule_row,
            }
        )
    )
    assert sha256_text(canonical_json(plan["schedule"])) == plan["schedule_hash"]
    assert (
        eval_runner._execution_hash(
            suite,
            dataset=plan["dataset"],
            task_rows=plan["tasks"],
            schedule_hash=plan["schedule_hash"],
            git_state=plan["environment"]["git"],
            docker_state=plan["environment"]["docker"],
            openai_sdk=plan["environment"]["openai_sdk"],
            pilot_qualification=plan["pilot_qualification"],
            runtime_contract=plan["runtime_contract"],
        )
        == EXECUTION_HASH
    )

    receipt = _load(
        RUNTIME_ROOT
        / "artifacts"
        / "runs"
        / RUN_ID
        / "evaluation-receipt.json"
    )
    for filename, expected_hash in receipt["file_hashes"].items():
        path = RUNTIME_ROOT / "artifacts" / "runs" / RUN_ID / filename
        assert sha256_bytes(path.read_bytes()) == expected_hash
    patch_path = RUNTIME_ROOT / "runs" / RUN_ID / "submitted.patch"
    assert sha256_bytes(patch_path.read_bytes()) == receipt["worktree_diff_hash"]
    assert patch_path.read_text(encoding="utf-8") not in REPORT_PATH.read_text(
        encoding="utf-8"
    )


def test_d086_journal_chain_and_result_hash_reconcile_when_present() -> None:
    _skip_without_raw()
    seal = _load(REPORT_PATH)["semantic_body"]["journal_seal"]
    journal_path = _raw_path(seal["path"])
    rows = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
    ]

    previous_hash = None
    for expected_sequence, source in enumerate(rows, start=1):
        row = dict(source)
        recorded_hash = row.pop("event_hash")
        assert row["sequence"] == expected_sequence
        assert row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(row)) == recorded_hash
        previous_hash = recorded_hash

    assert sha256_bytes(journal_path.read_bytes()) == seal["file_sha256"]
    assert len(rows) == seal["final_sequence"]
    assert rows[-1]["event_type"] == seal["final_event_type"]
    assert previous_hash == seal["final_event_hash"]
    assert rows[-1]["previous_event_hash"] == seal["previous_event_hash"]
    assert rows[-1]["payload"]["result_hash"] == seal["result_hash"]
    result_path = RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json"
    assert sha256_bytes(result_path.read_bytes()) == seal["result_hash"]


def test_d086_qualification_recomputes_exactly_from_durable_state() -> None:
    _skip_without_raw()
    body = _load(REPORT_PATH)["semantic_body"]
    expected = body["qualification"]
    persisted = load_trace_qualification(RUN_ID, root=RUNTIME_ROOT)
    recomputed = qualify_run(
        RUN_ID,
        task_dir=TASK_DIR,
        root=RUNTIME_ROOT,
        persist=False,
    )

    assert canonical_json(recomputed) == canonical_json(persisted)
    assert persisted["qualified"] is True
    assert persisted["trace_integrity_passed"] is True
    assert persisted["leakage_scan_passed"] is True
    assert persisted["evaluation_reached"] is True
    assert persisted["qualification_hash"] == expected["qualification_hash"]
    assert persisted["source_evidence_hash"] == expected["source_evidence_hash"]
    assert calculate_source_evidence_hash(
        RUN_ID, root=RUNTIME_ROOT, require_valid_plan=False
    ) == expected["source_evidence_hash"]
    assert len(persisted["checks"]) == expected["total_checks"] == 28
    assert sum(check["passed"] for check in persisted["checks"]) == 28
    assert not [check for check in persisted["checks"] if not check["passed"]]

    checks = {check["check_id"]: check for check in persisted["checks"]}
    for check_id in expected["required_checks"]:
        assert checks[check_id]["passed"] is True
    call_guard = [
        check
        for check in persisted["checks"]
        if check["check_id"] == "disabled_call_guard_contract"
    ]
    assert len(call_guard) == 1
    assert call_guard[0]["passed"] is True


def test_d086_trace_telemetry_and_artifact_cas_reconcile_when_present() -> None:
    _skip_without_raw()
    body = _load(REPORT_PATH)["semantic_body"]
    expected = body["trace_evidence"]
    state = StateStore(RUNTIME_ROOT / "state.sqlite3")
    events = state.list_events(RUN_ID)
    checkpoints = state.list_checkpoints(RUN_ID)
    claims = state.list_worker_claims(RUN_ID)

    assert len(events) == expected["event_count"] == 57
    assert [event.sequence for event in events] == list(range(1, 58))
    assert len(checkpoints) == expected["checkpoint_count"] == 10
    assert len(claims) == expected["worker_claim_count"] == 1
    assert sum(claim["reclaimed"] for claim in claims) == 0
    assert Counter(event.type.value for event in events) == Counter(
        expected["event_type_counts"]
    )

    terminal = events[-1]
    assert terminal.type == EventType.RUN_COMPLETED
    assert terminal.sequence == body["run_result"]["terminal_event"]["sequence"]
    assert sha256_text(canonical_json(terminal.model_dump(mode="json"))) == body[
        "run_result"
    ]["terminal_event"]["canonical_event_hash"]

    model_events = [event for event in events if event.type == EventType.MODEL_CALLED]
    assert len(model_events) == 8
    assert all(event.payload["response_status"] == "completed" for event in model_events)
    assert all(
        event.payload["requested_input_tokens"] == event.payload["input_tokens"]
        for event in model_events
    )
    assert all(
        event.payload["response_truncation"] == "disabled"
        for event in model_events
    )
    assert all(event.payload["store"] is False for event in model_events)
    assert all(
        event.payload["previous_response_id_used"] is False
        for event in model_events
    )
    assert sum(event.payload["input_tokens"] for event in model_events) == 69_701
    assert sum(event.payload["output_tokens"] for event in model_events) == 3_500
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 9
    assert not [event for event in events if event.type == EventType.TOOL_FAILED]
    assert not [
        event for event in events if event.type == EventType.MODEL_GENERATION_BLOCKED
    ]
    assert not [
        event for event in events if event.type == EventType.TOOL_ADMISSION_BLOCKED
    ]

    documents: list[Any] = [event.model_dump(mode="json") for event in events]
    documents.extend(
        [
            _load(RUNTIME_ROOT / "artifacts" / "runs" / RUN_ID / "result.json"),
            _load(RUNTIME_ROOT / "artifacts" / "runs" / RUN_ID / "provenance.json"),
        ]
    )
    descriptors: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if (
                isinstance(value.get("path"), str)
                and isinstance(value.get("content_hash"), str)
                and isinstance(value.get("size_bytes"), int)
            ):
                descriptors.append(value)
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    for document in documents:
        collect(document)
    unique = {
        (item["path"], item["content_hash"], item["size_bytes"])
        for item in descriptors
    }
    assert len(unique) == expected["artifact_integrity"][
        "unique_artifact_descriptor_count"
    ] == 18
    for raw_path, content_hash, size_bytes in unique:
        path = Path(raw_path)
        assert path.is_file()
        assert path.stat().st_size == size_bytes
        assert sha256_bytes(path.read_bytes()) == content_hash


def test_d086_budget_pressure_correction_is_read_only_and_reconciled() -> None:
    _skip_without_raw()
    correction = _load(CORRECTION_PATH)["semantic_body"]
    raw_result_path = RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json"
    journal_path = RUNTIME_ROOT / "experiments" / "journals" / f"{EXPERIMENT_ID}.jsonl"
    before = {
        "result": sha256_bytes(raw_result_path.read_bytes()),
        "journal": sha256_bytes(journal_path.read_bytes()),
    }
    raw = _load(raw_result_path)
    raw_row = raw["runs"][0]
    assert raw_row["budget_pressure"] == correction["original_observation"]

    state = StateStore(RUNTIME_ROOT / "state.sqlite3")
    manifest = state.get_manifest(RUN_ID)
    events = state.list_events(RUN_ID)
    with sqlite3.connect(RUNTIME_ROOT / "state.sqlite3") as connection:
        stored_result = json.loads(
            connection.execute(
                "SELECT result_json FROM runs WHERE run_id = ?", (RUN_ID,)
            ).fetchone()[0]
        )
    usage = stored_result["usage"]
    observed_total = usage["input_tokens"] + usage["output_tokens"]
    corrected = correction["corrected_budget_pressure"]
    assert corrected["observed_usage"]["total_tokens"] == observed_total == 73_201
    assert corrected["headroom"]["total_tokens"] == (
        manifest.budget.max_total_tokens - observed_total
    )
    assert corrected["headroom"]["wall_clock_ms"] == (
        manifest.budget.wall_clock_timeout_seconds * 1000 - usage["wall_clock_ms"]
    )
    assert corrected["blocked_tool_count"] == sum(
        event.type == EventType.TOOL_ADMISSION_BLOCKED for event in events
    ) == 0
    assert corrected["binding_dimension"] == "none"
    assert corrected["binding_reason"] is None

    cumulative = 0
    observed_prefix_minimum = 0
    for event in events:
        if event.type != EventType.MODEL_CALLED:
            continue
        requested = event.payload["requested_input_tokens"]
        observed_prefix_minimum = max(
            observed_prefix_minimum,
            cumulative + requested + manifest.model.max_output_tokens,
        )
        cumulative += event.payload["input_tokens"] + event.payload["output_tokens"]
    assert corrected["exact_request"][
        "observed_prefix_minimum_total_budget"
    ] == observed_prefix_minimum == 98_077

    production_diagnostic = budget_module.calculate_budget_pressure(
        manifest, events, stored_result
    )
    assert production_diagnostic == corrected

    after = {
        "result": sha256_bytes(raw_result_path.read_bytes()),
        "journal": sha256_bytes(journal_path.read_bytes()),
    }
    assert after == before
    assert raw["completion_gate"]["passed"] is True
    assert correction["correction_boundary"]["original_readiness_gate_replaced"] is False
