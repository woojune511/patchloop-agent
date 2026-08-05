from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from patchloop.errors import ContractError
from patchloop.evals.qualification import _private_leak_tokens, qualify_run
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts/build_d098_condition_neutral_baseline_seal.py"
REPORT_PATH = ROOT / "reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json"
RUNTIME_ROOT = ROOT / ".patchloop"
EXPERIMENT_ID = "dev-no-memory-condition-neutral-3000k-20260805-r1"
EXECUTION_HASH = "sha256:1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4"
REPORT_FILE_SHA256 = "sha256:ad87fa8c540552da62d964a430c29b032097b5cabbe78f0102c23cf36330b2dc"
REPORT_BODY_SHA256 = "sha256:e35cab52597c3ec6e884f074f9acf346dec65301e22d11edc2de56db7be9eacf"
RUN_IDS = (
    "run_575da4ead3334551",
    "run_74364afdc3d94f9c",
    "run_7ecb4b2489c34982",
    "run_5ffc2e1c58784e17",
    "run_3fe55fd3847d4a4d",
    "run_88f96fae3d2442e6",
    "run_3dc602aab8964d77",
    "run_59aac91defac456b",
    "run_cc179262fa664600",
    "run_ac3ae1a7009a4e8b",
    "run_d5c2e22b485a4578",
    "run_92bf10d2a6b14601",
)
CANDIDATE_RUN_IDS = {
    "run_575da4ead3334551",
    "run_74364afdc3d94f9c",
    "run_5ffc2e1c58784e17",
    "run_88f96fae3d2442e6",
    "run_3dc602aab8964d77",
    "run_59aac91defac456b",
    "run_cc179262fa664600",
    "run_ac3ae1a7009a4e8b",
    "run_d5c2e22b485a4578",
}
TASK_DIRS = tuple(sorted((ROOT / "tasks/dev-train").glob("*")))


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
        pytest.skip("local immutable D-097 runtime evidence is unavailable")


def test_d098_portable_seal_is_content_addressed_and_strict() -> None:
    payload = _load(REPORT_PATH)

    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "report_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == ("condition-neutral-no-memory-baseline-d098-evidence-v1")
    assert payload["semantic_body_hash"] == REPORT_BODY_SHA256
    assert sha256_json(payload["semantic_body"]) == REPORT_BODY_SHA256
    assert payload["report_id"] == f"d098_{REPORT_BODY_SHA256.removeprefix('sha256:')}"

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
        "baseline_admission",
        "campaign_cost",
        "aggregate_usage",
        "aggregate_trace",
        "runs",
        "memory_review_candidates",
        "journal_seal",
        "raw_local_artifacts",
        "portable_contract",
        "evidence_validation",
        "analysis",
        "claims_boundary",
        "next_gate",
    }
    assert body["milestone"] == "D-098"


def test_d098_builder_reproduces_exact_seal_when_raw_evidence_is_present() -> None:
    _skip_without_raw()
    builder = _module(BUILDER_PATH, "d098_builder_reproducible")
    payload = _load(REPORT_PATH)
    state_path = RUNTIME_ROOT / "state.sqlite3"
    before = builder._state_bundle_fingerprint(state_path)

    assert (
        builder.build_seal(
            repo_root=ROOT,
            runtime_root=RUNTIME_ROOT,
            sealed_at=payload["semantic_body"]["sealed_at"],
        )
        == payload
    )
    assert builder._state_bundle_fingerprint(state_path) == before


def test_d098_builder_rejects_noncanonical_seal_time() -> None:
    _skip_without_raw()
    builder = _module(BUILDER_PATH, "d098_builder_sealed_at")

    with pytest.raises(
        builder.D098BuildError,
        match="sealed_at must match the exact D-098 seal time",
    ):
        builder.build_seal(
            repo_root=ROOT,
            runtime_root=RUNTIME_ROOT,
            sealed_at="diff --git a/private b/private",
        )


def test_d098_alternate_state_path_cannot_persist_qualification() -> None:
    _skip_without_raw()

    with pytest.raises(
        ContractError,
        match="alternate qualification state_path requires persist=False",
    ):
        qualify_run(
            RUN_IDS[0],
            task_dir=ROOT / "tasks/dev-train/pyfakefs-makedirs-parent-traversal",
            root=RUNTIME_ROOT,
            state_path=RUNTIME_ROOT / "state.sqlite3",
            persist=True,
        )


def test_d098_builder_rejects_budget_provenance_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _skip_without_raw()
    builder = _module(BUILDER_PATH, "d098_builder_budget_provenance")
    original = builder._load_json

    def tampered_load(content: bytes, *, label: str) -> dict[str, Any]:
        payload = original(content, label=label)
        if label == "run_7ecb4b2489c34982 provenance":
            payload = {**payload, "evaluation_reached": True}
        return payload

    monkeypatch.setattr(builder, "_load_json", tampered_load)
    with pytest.raises(builder.D098BuildError, match="budget provenance artifact drifted"):
        builder.build_seal(
            repo_root=ROOT,
            runtime_root=RUNTIME_ROOT,
        )


@pytest.mark.parametrize(
    ("target_label", "expected_message"),
    (
        (
            "run_7ecb4b2489c34982 manifest",
            "manifest artifact differs from durable state",
        ),
        (
            "run_7ecb4b2489c34982 result",
            "result artifact differs from durable campaign state",
        ),
    ),
)
def test_d098_builder_rejects_budget_manifest_or_result_tamper(
    monkeypatch: pytest.MonkeyPatch,
    target_label: str,
    expected_message: str,
) -> None:
    _skip_without_raw()
    builder = _module(BUILDER_PATH, f"d098_builder_{target_label.rsplit(' ', 1)[-1]}")
    original = builder._load_json

    def tampered_load(content: bytes, *, label: str) -> dict[str, Any]:
        payload = original(content, label=label)
        if label == target_label:
            payload = {**payload, "run_id": "run_mixed_budget_artifact"}
        return payload

    monkeypatch.setattr(builder, "_load_json", tampered_load)
    with pytest.raises(builder.D098BuildError, match=expected_message):
        builder.build_seal(repo_root=ROOT, runtime_root=RUNTIME_ROOT)


def test_d098_tracked_source_bindings_are_exact_without_runtime() -> None:
    source = _body()["source_contract"]
    for key in ("suite", "d096_policy_and_admission", "d097_source_gate"):
        descriptor = source[key]
        content = (ROOT / descriptor["path"]).read_bytes()
        assert len(content) == descriptor["bytes"]
        assert sha256_bytes(content) == descriptor["sha256"]
        if key != "suite":
            payload = json.loads(content)
            assert payload["semantic_body_hash"] == descriptor["semantic_body_hash"]
            assert sha256_json(payload["semantic_body"]) == descriptor["semantic_body_hash"]

    identities = source["schedule_identities"]
    assert identities == {
        "pre_shuffle_admission_schedule_hash": (
            "sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b"
        ),
        "source_expanded_order_hash": (
            "sha256:dff4f38db99bcbc878e917a6c76e10a6c244701d2a8eb5ea4b43daf427a305ba"
        ),
        "runtime_schedule_hash": (
            "sha256:2ecbf257117481bfa31d62454221af243cc541470a91abeefdcae1f0912a552d"
        ),
        "meanings_are_distinct": True,
    }


def test_d098_builder_rejects_mixed_runtime_and_journal_tamper() -> None:
    builder = _module(BUILDER_PATH, "d098_builder_tamper")

    with pytest.raises(
        builder.D098BuildError,
        match="runtime root must be the exact repository runtime",
    ):
        builder.build_seal(repo_root=ROOT, runtime_root=ROOT / "alternate-runtime")

    journal = (RUNTIME_ROOT / "experiments" / "journals" / f"{EXPERIMENT_ID}.jsonl").read_bytes()
    rows = [json.loads(line) for line in journal.decode("utf-8").splitlines()]
    rows[-1]["payload"]["completed_runs"] = 11
    tampered = ("\n".join(canonical_json(row) for row in rows) + "\n").encode()
    with pytest.raises(builder.D098BuildError, match="hash chain drifted"):
        builder._journal_projection(tampered)


def test_d098_measured_baseline_gate_usage_cost_and_trace_are_exact() -> None:
    body = _body()
    experiment = body["experiment"]
    gate = body["original_campaign_result"]["completion_gate"]

    assert experiment["experiment_id"] == EXPERIMENT_ID
    assert experiment["execution_hash"] == EXECUTION_HASH
    assert experiment["expected_runs"] == 12
    assert experiment["completed_runs"] == 12
    assert experiment["conditions"] == ["no_memory"]
    assert experiment["repetitions"] == 2
    assert experiment["approved_maximum_cost_usd"] == 164.0
    assert experiment["campaign_scoped_project_cap_exception_used"] is True
    assert experiment["one_use_execution_hash_consumed"] is True

    assert gate["schema_version"] == "condition-neutral-no-memory-baseline-admission-gate-v2"
    assert gate["passed"] is True
    assert gate["terminal_runs"] == 12
    assert gate["qualified_runs"] == 12
    assert gate["cost_settled_runs"] == 12
    assert gate["official_evaluator_runs"] == 11
    assert gate["budget_terminal_runs"] == 1
    assert gate["budget_terminal_run_ids"] == ["run_7ecb4b2489c34982"]
    assert gate["terminal_branches_mutually_exclusive_and_exhaustive"] is True
    assert gate["comparison_denominator_eligible"] is True
    assert gate["memory_review_eligible"] is True
    assert gate["memory_admission_unlocked"] is False

    assert body["aggregate_usage"] == {
        "input_tokens": 10_492_742,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 881_967,
        "reasoning_output_tokens": 805_212,
        "total_tokens": 11_374_709,
        "model_calls": 613,
        "input_token_count_calls": 614,
        "tool_calls": 964,
        "wall_clock_ms": 7_258_662,
        "model_cost_nanos": 11_838_408_000,
        "model_cost_usd": 11.838408,
    }
    assert body["aggregate_trace"] == {
        "event_count": 4_536,
        "checkpoint_count": 978,
        "worker_claim_count": 12,
        "reclaimed_worker_claim_count": 0,
        "completed_model_responses": 613,
        "input_token_precount_calls": 614,
        "pre_provider_generation_blocks": 1,
        "exact_input_token_matches": 613,
        "exact_total_token_matches": 613,
        "truncation_disabled_responses": 613,
        "store_false_responses": 613,
        "previous_response_dependency_count": 0,
        "submission_accepted_count": 11,
        "run_completed_count": 11,
        "run_failed_count": 1,
        "memory_retrieval_count": 0,
    }
    assert body["campaign_cost"]["actual_usage_derived_standard_list_price_usd"] == (11.838408)
    assert body["campaign_cost"]["full_schedule_reserve_usd"] == 163.35
    assert body["campaign_cost"]["hard_cap_usd"] == 164.0
    assert body["campaign_cost"]["actual_invoice_claimed"] is False


def test_d098_outcomes_and_memory_candidate_boundary_are_exact() -> None:
    body = _body()
    rows = body["runs"]
    candidates = body["memory_review_candidates"]

    assert [row["run_id"] for row in rows] == list(RUN_IDS)
    assert {row["terminal_branch"] for row in rows} == {
        "official_evaluator",
        "canonical_pre_provider_budget",
    }
    assert sum(row["result"]["outcome_kind"] == "resolved" for row in rows) == 2
    assert sum(row["result"]["outcome_kind"] == "task_failure" for row in rows) == 9
    assert sum(row["result"]["outcome_kind"] == "agent_failure" for row in rows) == 1
    assert all(
        row["result"]["verdicts"]["regression_tests"] == "pass"
        and row["result"]["verdicts"]["scope_policy"] == "pass"
        and row["result"]["verdicts"]["safety_policy"] == "pass"
        for row in rows
        if row["terminal_branch"] == "official_evaluator"
    )

    assert candidates["schema_version"] == "memory-review-candidate-set-v1"
    assert candidates["candidate_count"] == 9
    assert {row["run_id"] for row in candidates["candidates"]} == CANDIDATE_RUN_IDS
    assert candidates["excluded_resolved_count"] == 2
    assert candidates["excluded_budget_run_ids"] == ["run_7ecb4b2489c34982"]
    assert candidates["rules_created"] == 0
    assert candidates["review_completed"] is False
    assert candidates["dedup_completed"] is False
    assert candidates["leak_scan_completed"] is False
    assert candidates["memory_admission_unlocked"] is False

    budget_row = next(row for row in rows if row["run_id"] == "run_7ecb4b2489c34982")
    assert budget_row["qualification"]["memory_candidate_eligible"] is False
    assert budget_row["qualification"]["passed_checks"] == 28
    assert budget_row["result"]["terminal_error"] == {
        "type": "ModelGenerationBudgetError",
        "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "reason_code": "exact_request_budget_exceeded",
        "generation_started": False,
    }
    assert budget_row["budget_pressure"]["exact_request"]["deficit_tokens"] == 26_231
    assert all(
        row["qualification"]["passed_checks"] == 29
        for row in rows
        if row["run_id"] != "run_7ecb4b2489c34982"
    )


def test_d098_claims_boundary_opens_review_only() -> None:
    body = _body()
    claims = body["claims_boundary"]
    next_gate = body["next_gate"]

    for key in (
        "live_provider_execution_observed",
        "development_no_memory_baseline_result_established",
        "development_baseline_denominator_complete",
        "comparison_denominator_eligible",
        "memory_review_eligible",
    ):
        assert claims[key] is True
    for key in (
        "memory_admission_unlocked",
        "memory_index_frozen",
        "core_campaign_unlocked",
        "analysis_ready",
        "held_out_or_cross_condition_effect_estimated",
        "automatic_rerun_authorized",
        "hidden_driven_tuning_authorized",
        "per_row_atomic_sqlite_consumption_claimed",
        "duplicate_paid_call_prevention_claimed",
        "live_resume_supported",
        "actual_invoice_or_free_tier_treatment_claimed",
        "original_result_journal_run_or_qualification_modified",
    ):
        assert claims[key] is False
    assert claims["provider_model_calls_observed"] == 613
    assert claims["official_evaluator_runs_observed"] == 11
    assert claims["seal_provider_calls"] == 0
    assert claims["seal_evaluator_calls"] == 0
    assert claims["seal_added_model_cost_usd"] == 0.0
    assert next_gate["decision_required"] == ("public-evidence-memory-review-dedup-and-leak-scan")
    assert next_gate["memory_review_candidate_count"] == 9
    assert next_gate["memory_rule_admission_completed"] is False
    assert next_gate["memory_index_build_authorized"] is False
    assert next_gate["new_live_execution_authorized"] is False


def test_d098_portable_projection_is_leak_safe() -> None:
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    lowered = report_text.lower()
    forbidden_markers = (
        "c:\\users\\",
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

    task_ids = {row["task_id"] for row in _body()["runs"]}
    for task_id in task_ids:
        task_dir = ROOT / "tasks/dev-train" / task_id
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


def test_d098_raw_descriptors_and_final_journal_binding_reconcile_when_present() -> None:
    _skip_without_raw()
    body = _body()
    for descriptor in body["raw_local_artifacts"]:
        content = (ROOT / descriptor["path"]).read_bytes()
        assert len(content) == descriptor["bytes"]
        assert sha256_bytes(content) == descriptor["sha256"]

    journal_path = ROOT / body["journal_seal"]["path"]
    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    previous_hash: str | None = None
    for sequence, event in enumerate(events, start=1):
        assert event["sequence"] == sequence
        assert event["previous_event_hash"] == previous_hash
        event_hash = event["event_hash"]
        assert event_hash == sha256_text(
            canonical_json({key: value for key, value in event.items() if key != "event_hash"})
        )
        previous_hash = event_hash
    assert events[-1]["event_hash"] == body["journal_seal"]["final_event_hash"]
    assert events[-1]["payload"]["result_hash"] == body["journal_seal"]["result_hash"]
