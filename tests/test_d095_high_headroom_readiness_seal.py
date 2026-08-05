from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from patchloop.contracts import EventType, Usage
from patchloop.evals.qualification import (
    _private_leak_tokens,
    calculate_source_evidence_hash,
    load_trace_qualification,
    qualify_run,
)
from patchloop.runtime import calculate_model_cost
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts/build_d095_high_headroom_readiness_seal.py"
REPORT_PATH = ROOT / "reports/live-pilot/generic-high-headroom-readiness-v2v5-20260804-r1.json"
RUNTIME_ROOT = ROOT / ".patchloop"
EXPERIMENT_ID = "generic-high-headroom-readiness-v2v5-20260804-r1"
EXECUTION_HASH = "sha256:ae54b9cc14e3bcb80cbead61a003012cec4dbd0e8a205917b3cefdeaf0c11d75"
REPORT_FILE_SHA256 = "sha256:62ef705c992fcdb3e6e6b648e8376c4d5fdbff2534bd5b0a37158b99b4b3f95e"
REPORT_BODY_SHA256 = "sha256:79fe3312222896beec28070b5a77e36ffc7854a00c983a70f90cbe37ac2bb99f"
RUN_IDS = (
    "run_9fd10f7feeee4df5",
    "run_7449597e84b94446",
    "run_9566c0367bd24f52",
)
TASK_DIRS = {
    "anyio-interrupt-runner-cleanup": (ROOT / "tasks/dev-train/anyio-interrupt-runner-cleanup"),
    "pyfakefs-makedirs-parent-traversal": (
        ROOT / "tasks/dev-train/pyfakefs-makedirs-parent-traversal"
    ),
    "hf-hub-xet-endpoint-propagation": (ROOT / "tasks/dev-train/hf-hub-xet-endpoint-propagation"),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _body() -> dict[str, Any]:
    return _load(REPORT_PATH)["semantic_body"]


def _skip_without_raw() -> None:
    path = RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json"
    if not path.is_file():
        pytest.skip("local immutable D-094 runtime evidence is unavailable")


def test_d095_portable_seal_is_content_addressed_and_strict() -> None:
    payload = _load(REPORT_PATH)

    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "report_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == ("generic-high-headroom-readiness-d095-evidence-v1")
    assert payload["semantic_body_hash"] == REPORT_BODY_SHA256
    assert sha256_json(payload["semantic_body"]) == REPORT_BODY_SHA256
    assert payload["report_id"] == f"d095_{REPORT_BODY_SHA256.removeprefix('sha256:')}"

    body = payload["semantic_body"]
    assert set(body) == {
        "milestone",
        "evidence_kind",
        "recorded_at",
        "sealed_at",
        "source_contract",
        "experiment",
        "environment",
        "original_campaign_result",
        "aggregate_usage",
        "aggregate_trace",
        "runs",
        "journal_seal",
        "raw_local_artifacts",
        "portable_contract",
        "evidence_validation",
        "analysis",
        "claims_boundary",
        "next_gate",
    }
    assert body["milestone"] == "D-095"


def test_d095_builder_reproduces_exact_seal_when_raw_evidence_is_present() -> None:
    _skip_without_raw()
    builder = _module(BUILDER_PATH, "d095_builder_reproducible")
    payload = _load(REPORT_PATH)

    assert (
        builder.build_seal(
            repo_root=ROOT,
            runtime_root=RUNTIME_ROOT,
            sealed_at=payload["semantic_body"]["sealed_at"],
        )
        == payload
    )


def test_d095_tracked_source_bindings_are_exact_without_runtime() -> None:
    source = _body()["source_contract"]
    for key in ("suite", "d094_source_gate"):
        descriptor = source[key]
        content = (ROOT / descriptor["path"]).read_bytes()
        assert len(content) == descriptor["bytes"]
        assert sha256_bytes(content) == descriptor["sha256"]

    source_gate = _load(ROOT / source["d094_source_gate"]["path"])
    assert source_gate["semantic_body_hash"] == (
        source["d094_source_gate"]["semantic_body_hash"]
    )
    assert sha256_json(source_gate["semantic_body"]) == source_gate["semantic_body_hash"]
    assert source_gate["gate_id"] == source["d094_source_gate"]["gate_id"]


def test_d095_builder_rejects_a_mixed_runtime_root() -> None:
    builder = _module(BUILDER_PATH, "d095_builder_runtime_root")

    with pytest.raises(
        builder.D095BuildError,
        match="runtime root must be the exact repository runtime",
    ):
        builder.build_seal(
            repo_root=ROOT,
            runtime_root=ROOT / "alternate-runtime",
        )


def test_d095_cached_input_cost_does_not_double_count_tokens() -> None:
    builder = _module(BUILDER_PATH, "d095_builder_cached_cost")

    assert builder._usage_cost(
        {
            "input_tokens": 100,
            "cached_input_tokens": 40,
            "output_tokens": 10,
        }
    ) == Decimal("0.000093")


def test_d095_measured_gate_usage_and_task_outcomes_are_exact() -> None:
    body = _body()
    experiment = body["experiment"]
    original = body["original_campaign_result"]
    gate = original["completion_gate"]

    assert experiment == {
        "experiment_id": EXPERIMENT_ID,
        "purpose": "generic-baseline-readiness",
        "execution_hash": EXECUTION_HASH,
        "suite_hash": ("sha256:06f4be1917494c340db48fc5fb35ffb9ea443c4fa51ae6ee4cce6e3f0834c99a"),
        "schedule_hash": (
            "sha256:e29fd7768666cf9891e40bed872d4739925b0c0ed7ed6187601ee63a9d8349df"
        ),
        "schedule_seed": 20260723,
        "expected_runs": 3,
        "completed_runs": 3,
        "conditions": ["no_memory"],
        "repetitions": 1,
        "approved_maximum_cost_usd": 41.0,
        "one_use_execution_hash_consumed": True,
    }
    assert gate["schema_version"] == "generic-high-headroom-readiness-gate-v1"
    assert gate["gate_id"] == "d094-generic-high-headroom-readiness"
    assert gate["passed"] is True
    for key in (
        "terminal_runs",
        "qualified_runs",
        "evaluator_reached_runs",
        "official_evaluator_runs",
        "accepted_submission_runs",
        "prompt_telemetry_complete_runs",
        "usage_reconciled_runs",
        "persisted_result_verified_runs",
        "qualification_recomputed_runs",
    ):
        assert gate[key] == 3
    assert gate["task_successes"] == 0
    assert gate["task_success_required"] is False
    assert gate["budget_terminal_runs"] == 0
    assert gate["terminal_loop_failure_runs"] == 0
    assert gate["model_or_tool_call_budget_block_runs"] == 0
    assert original["infrastructure_errors"] == 0
    assert original["qualification_errors"] == 0
    assert original["diagnostic_errors"] == 0

    assert body["aggregate_usage"] == {
        "input_tokens": 957_052,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 48_805,
        "reasoning_output_tokens": 43_265,
        "total_tokens": 1_005_857,
        "model_calls": 63,
        "input_token_count_calls": 63,
        "tool_calls": 119,
        "wall_clock_ms": 446_060,
        "model_cost_usd": 0.9374115,
    }
    assert body["aggregate_trace"] == {
        "events": 552,
        "checkpoints": 122,
        "worker_claims": 3,
        "reclaimed_worker_claims": 0,
        "completed_model_responses": 63,
        "exact_input_token_matches": 63,
        "exact_total_token_matches": 63,
        "truncation_disabled_responses": 63,
        "store_false_responses": 63,
        "previous_response_dependency_count": 0,
    }

    assert [run["run_id"] for run in body["runs"]] == list(RUN_IDS)
    assert all(run["result"]["outcome_kind"] == "task_failure" for run in body["runs"])
    assert all(
        run["result"]["verdicts"]
        == {
            "hidden_tests": "fail",
            "regression_tests": "pass",
            "scope_policy": "pass",
            "safety_policy": "pass",
        }
        for run in body["runs"]
    )
    assert all(run["budget_pressure"]["binding_dimension"] == "none" for run in body["runs"])
    assert all(run["qualification"]["passed_checks"] == 28 for run in body["runs"])


def test_d095_claims_boundary_keeps_baseline_memory_and_core_closed() -> None:
    body = _body()
    claims = body["claims_boundary"]
    next_gate = body["next_gate"]

    assert claims["workflow_readiness_gate_passed"] is True
    assert claims["task_successes"] == 0
    assert claims["task_success_is_readiness_requirement"] is False
    assert claims["calibration_only"] is True
    for key in (
        "no_memory_performance_baseline_established",
        "success_rate_estimated",
        "comparison_denominator_eligible",
        "comparison_resource_policy_frozen",
        "memory_review_authorized",
        "memory_admission_unlocked",
        "memory_index_frozen",
        "core_campaign_unlocked",
        "analysis_ready",
        "actual_invoice_or_free_tier_treatment_claimed",
        "hidden_driven_tuning_authorized",
        "automatic_rerun_authorized",
        "original_result_journal_run_or_qualification_modified",
    ):
        assert claims[key] is False
    assert claims["seal_provider_calls"] == 0
    assert claims["seal_evaluator_calls"] == 0
    assert claims["seal_added_model_cost_usd"] == 0.0
    assert next_gate["current_experiment_hard_consumed"] is True
    assert next_gate["current_execution_hash_reusable"] is False
    assert next_gate["new_live_execution_authorized"] is False
    assert next_gate["resource_policy_freeze_completed"] is False
    assert next_gate["no_memory_baseline_admitted"] is False


def test_d095_portable_projection_is_leak_safe() -> None:
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    lowered = report_text.lower()
    forbidden_markers = (
        "diff --git",
        "@@ -",
        "openai_api_key",
        "authorization: bearer",
        '"private_spec_hash"',
        '"verifier_results"',
        '"evidence_artifacts"',
        '"request_body"',
        '"response_body"',
        '"patch_body"',
        '"reference_patch"',
    )
    for marker in forbidden_markers:
        assert marker not in lowered

    for task_dir in TASK_DIRS.values():
        package = load_task_package(task_dir)
        leaked = [
            token
            for token in _private_leak_tokens(package, api_key=None)
            if token.lower() in lowered
        ]
        assert leaked == []

    portable = _body()["portable_contract"]
    assert portable["private_spec_embedded"] is False
    assert portable["hidden_assertion_embedded"] is False
    assert portable["reference_patch_embedded"] is False
    assert portable["submitted_patch_body_embedded"] is False
    assert portable["model_or_tool_body_embedded"] is False
    assert portable["api_key_or_authorization_embedded"] is False


def test_d095_raw_result_journal_qualification_and_trace_reconcile_when_present() -> None:
    _skip_without_raw()
    body = _body()
    raw_descriptor = body["original_campaign_result"]["raw_result"]
    raw_path = ROOT / raw_descriptor["path"]
    raw_bytes = raw_path.read_bytes()
    raw = json.loads(raw_bytes)

    assert len(raw_bytes) == raw_descriptor["bytes"]
    assert sha256_bytes(raw_bytes) == raw_descriptor["sha256"]
    assert raw["execution_hash"] == EXECUTION_HASH
    assert raw["completion_gate"] == body["original_campaign_result"]["completion_gate"]

    artifact_descriptors = body["raw_local_artifacts"]
    for descriptor in artifact_descriptors:
        path = ROOT / descriptor["path"]
        assert path.is_file(), descriptor["role"]
        content = path.read_bytes()
        assert len(content) == descriptor["bytes"]
        assert sha256_bytes(content) == descriptor["sha256"]

    state = StateStore(RUNTIME_ROOT / "state.sqlite3")
    expected_by_run = {run["run_id"]: run for run in body["runs"]}
    for raw_row in raw["runs"]:
        run_id = raw_row["run_id"]
        expected = expected_by_run[run_id]
        task_dir = TASK_DIRS[raw_row["task_id"]]
        persisted = load_trace_qualification(run_id, root=RUNTIME_ROOT)
        recomputed = qualify_run(
            run_id,
            task_dir=task_dir,
            root=RUNTIME_ROOT,
            persist=False,
        )
        assert canonical_json(persisted) == canonical_json(recomputed)
        assert persisted["qualified"] is True
        assert len(persisted["checks"]) == 28
        assert all(check["passed"] for check in persisted["checks"])
        assert persisted["qualification_hash"] == expected["qualification"]["qualification_hash"]
        assert (
            calculate_source_evidence_hash(run_id, root=RUNTIME_ROOT)
            == (expected["qualification"]["source_evidence_hash"])
        )

        events = state.list_events(run_id)
        checkpoints = state.list_checkpoints(run_id)
        claims = state.list_worker_claims(run_id)
        assert len(events) == expected["trace"]["event_count"]
        assert len(checkpoints) == expected["trace"]["checkpoint_count"]
        assert len(claims) == expected["trace"]["worker_claim_count"]
        assert Counter(event.type.value for event in events) == Counter(
            expected["trace"]["event_type_counts"]
        )
        assert events[-1].type == EventType.RUN_COMPLETED

        model_events = [event for event in events if event.type == EventType.MODEL_CALLED]
        usage = Usage.model_validate(raw_row["usage"])
        assert len(model_events) == usage.model_calls
        assert all(
            event.payload["response_status"] == "completed"
            and event.payload["requested_input_tokens"] == event.payload["input_tokens"]
            and event.payload["input_token_count_match"] is True
            and event.payload["total_token_count_match"] is True
            and event.payload["response_truncation"] == "disabled"
            and event.payload["store"] is False
            and event.payload["previous_response_id_used"] is False
            for event in model_events
        )
        assert sum(event.payload["input_tokens"] for event in model_events) == (usage.input_tokens)
        assert sum(event.payload["output_tokens"] for event in model_events) == (
            usage.output_tokens
        )
        manifest = state.get_manifest(run_id)
        assert calculate_model_cost(usage, manifest.model) == pytest.approx(
            usage.model_cost_usd,
            abs=1e-12,
        )

    journal = body["journal_seal"]
    rows = [
        json.loads(line)
        for line in (ROOT / journal["path"]).read_text(encoding="utf-8").splitlines()
        if line
    ]
    previous_hash = None
    for row in rows:
        recorded_hash = row["event_hash"]
        projection = {key: value for key, value in row.items() if key != "event_hash"}
        assert row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(projection)) == recorded_hash
        previous_hash = recorded_hash
    assert previous_hash == journal["final_event_hash"]
    assert rows[-1]["payload"]["result_hash"] == sha256_bytes(raw_bytes)
