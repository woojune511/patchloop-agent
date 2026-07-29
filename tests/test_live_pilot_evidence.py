from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from patchloop.evals.qualification import (
    _private_leak_tokens,
    calculate_source_evidence_hash,
    load_trace_qualification,
)
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text


def _assert_artifact_identity(artifact: dict[str, object]) -> None:
    source = Path(str(artifact["path"]))
    content = source.read_bytes()
    assert len(content) == artifact["bytes"]
    assert "sha256:" + hashlib.sha256(content).hexdigest() == artifact["sha256"]


def _artifact_for_role(payload: dict[str, object], role: str) -> dict[str, object]:
    artifacts = payload["portable_artifacts"]
    assert isinstance(artifacts, list)
    matches = [artifact for artifact in artifacts if artifact["role"] == role]
    assert len(matches) == 1
    return matches[0]


def test_first_live_pilot_report_keeps_failure_and_counterfactual_separate() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v1"
    assert payload["pilot"]["run_id"] == "run_c6f13dd9a1a1472d"
    assert payload["pilot"]["outcome_kind"] == "agent_failure"
    assert payload["pilot"]["evaluation_status"] == "not_run"
    assert payload["pilot"]["qualification"]["qualified"] is False
    assert payload["pilot"]["forensic_leak_match_counts"]["api_key"] == 0

    counterfactual = payload["format_only_counterfactual"]
    assert counterfactual["official"] is True
    assert counterfactual["scope_compliant_success"] is True
    assert counterfactual["code_edit_changed_from_model_candidate"] is False
    assert counterfactual["count_as_agent_success"] is False
    assert counterfactual["count_as_pilot_repetition"] is False

    claims = payload["claims_boundary"]
    assert claims["paid_provider_path_exercised"] is True
    assert claims["qualified_live_pilot"] is False
    assert claims["live_model_task_success"] is False
    assert claims["development_campaign_unlocked"] is False

    policy = payload["evidence_policy"]
    assert "local-only" in policy["raw_local_artifacts"]
    assert "not bundled" in policy["raw_local_artifacts"]


def test_portable_live_pilot_artifacts_are_hash_bound() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["portable_artifacts"]
    for artifact in payload["portable_artifacts"]:
        _assert_artifact_identity(artifact)


def test_raw_live_pilot_artifacts_match_when_local_evidence_is_available() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local live-pilot evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in payload["raw_local_artifacts"]:
        _assert_artifact_identity(artifact)


def test_second_live_pilot_separates_trace_quality_from_acceptance() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v2"
    assert payload["pilot"]["run_id"] == "run_de8f2a2846044c01"
    assert payload["pilot"]["outcome_kind"] == "agent_failure"
    assert payload["pilot"]["evaluation_status"] == "not_run"
    assert payload["pilot"]["trace_qualification_artifact"]["qualified"] is True
    assert payload["pilot"]["trace_qualification_artifact"]["evaluation_reached"] is False
    assert payload["pilot"]["pilot_acceptance"]["accepted"] is False

    attempts = payload["pilot"]["patch_attempts"]
    assert attempts["model_outputs_with_apply_patch"] == 9
    assert attempts["unique_patch_payloads"] == 7
    assert attempts["failed_apply_patch_calls"] == 8
    assert attempts["declared_old_lines"] == 7
    assert attempts["actual_old_lines"] == 6

    candidate = payload["selected_recount_candidate"]
    assert candidate["strict_git_apply_check_passed"] is False
    assert candidate["recount_git_apply_check_passed"] is True
    assert candidate["official_evaluator_run"] is None
    assert candidate["count_as_agent_success"] is False
    assert candidate["count_as_pilot_repetition"] is False

    claims = payload["claims_boundary"]
    assert claims["trace_qualification_artifact_qualified"] is True
    assert claims["accepted_live_pilot"] is False
    assert claims["live_model_task_success"] is False
    assert claims["development_campaign_unlocked"] is False
    assert payload["spend_to_date"]["cumulative_usd"] == pytest.approx(0.668295625)


def test_second_live_pilot_portable_artifact_is_hash_bound() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["portable_artifacts"]
    for artifact in payload["portable_artifacts"]:
        _assert_artifact_identity(artifact)


def test_second_raw_pilot_artifacts_match_when_local_evidence_is_available() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local second-live-pilot evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)


def test_third_live_pilot_is_trace_qualified_and_accepted() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728-r3.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v2"
    assert payload["pilot"]["run_id"] == "run_3cb86f8d70094a11"
    assert payload["pilot"]["outcome_kind"] == "resolved"
    assert payload["pilot"]["agent_submission_status"] == "completed"
    assert payload["pilot"]["evaluation_status"] == "completed"
    assert payload["pilot"]["scope_compliant_success"] is True
    assert payload["pilot"]["official"] is True
    assert set(payload["pilot"]["verdicts"].values()) == {"pass"}

    qualification = payload["pilot"]["trace_qualification_artifact"]
    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is True
    assert payload["pilot"]["pilot_acceptance"]["accepted"] is True

    mutation = payload["successful_mutation"]
    assert mutation["raw_model_patch_sha256"] != mutation["worktree_diff_sha256"]
    assert mutation["declared_old_lines"] == 7
    assert mutation["actual_old_lines"] == 6
    assert mutation["gateway_result"] == "succeeded"
    assert mutation["patch_applied_exactly_once"] is True
    assert mutation["raw_model_patch_is_final_submitted_diff"] is False

    submitted = payload["submitted_patch"]
    assert submitted["patch_sha256"] == mutation["worktree_diff_sha256"]
    assert submitted["diff_sha256"] == mutation["worktree_diff_sha256"]
    assert submitted["official_evaluator_input"] is True

    claims = payload["claims_boundary"]
    assert claims["accepted_live_pilot"] is True
    assert claims["live_model_task_success"] is True
    assert claims["official_scope_compliant_success"] is True
    assert claims["development_campaign_pilot_gate_passed"] is True
    assert claims["development_campaign_executed"] is False
    assert payload["spend_to_date"]["cumulative_usd"] == pytest.approx(0.828864375)
    correction = payload["historical_correction"]
    assert (
        correction["journal_recorded_result_hash"] != (correction["persisted_result_file_sha256"])
    )
    assert correction["journal_recorded_result_hash"] == (correction["lf_normalized_result_sha256"])
    assert correction["append_only_raw_evidence_preserved"] is True
    assert correction["trace_qualification_affected"] is False
    assert correction["model_or_evaluator_outcome_affected"] is False
    assert '"response_id"' not in path.read_text(encoding="utf-8")


def test_third_live_pilot_portable_artifacts_are_hash_bound() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728-r3.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    candidate = _artifact_for_role(payload, "applied-model-tool-argument")
    submitted = _artifact_for_role(payload, "final-submitted-git-diff")
    _assert_artifact_identity(candidate)
    _assert_artifact_identity(submitted)
    assert candidate["sha256"] == payload["successful_mutation"]["raw_model_patch_sha256"]
    assert submitted["sha256"] == payload["submitted_patch"]["patch_sha256"]


def test_third_portable_patches_match_raw_sources_when_available() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728-r3.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidate = _artifact_for_role(payload, "applied-model-tool-argument")
    submitted = _artifact_for_role(payload, "final-submitted-git-diff")

    raw_artifacts = payload["raw_local_artifacts"]
    model_hash = payload["successful_mutation"]["model_artifact_sha256"]
    model_matches = [artifact for artifact in raw_artifacts if artifact["sha256"] == model_hash]
    submitted_matches = [
        artifact for artifact in raw_artifacts if artifact["path"].endswith("/submitted.patch")
    ]
    assert len(model_matches) == 1
    assert len(submitted_matches) == 1
    model_path = Path(model_matches[0]["path"])
    submitted_path = Path(submitted_matches[0]["path"])
    if not model_path.is_file() or not submitted_path.is_file():
        pytest.skip("raw local third-live-pilot patch evidence is not bundled")

    model_artifact = json.loads(model_path.read_text(encoding="utf-8"))
    apply_calls = [call for call in model_artifact["tool_calls"] if call["name"] == "apply_patch"]
    assert len(apply_calls) == 1
    raw_model_patch = apply_calls[0]["arguments"]["patch"].encode("utf-8")
    assert Path(candidate["path"]).read_bytes() == raw_model_patch
    assert Path(submitted["path"]).read_bytes() == submitted_path.read_bytes()
    assert raw_model_patch != submitted_path.read_bytes()


def test_third_raw_pilot_artifacts_match_when_local_evidence_is_available() -> None:
    path = Path("reports/live-pilot/dev-validation-live-pilot-20260728-r3.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local third-live-pilot evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)


def test_mini_corrective_r2_separates_diagnostic_evidence_from_task_success() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v3"
    assert payload["execution_hash"] == (
        "sha256:fc2649790241f9623ea259a05957a38d1063472a9f17998e9e489b5b3fad21ca"
    )
    assert payload["harness_commit"] == ("ff33d18a520de6fd8949ce9d873e26241b4382ae")

    lineage = payload["retry_lineage"]
    assert lineage["terminal_r1"] == {
        "experiment_id": "dev-validation-gpt54mini-pilot-20260729-r1",
        "run_id": "run_d4fea5e7198b4abc",
        "outcome_kind": "agent_failure",
        "evaluation_status": "not_run",
        "immutable": True,
        "execution_hash": (
            "sha256:86fb73140404ba4326710d3be7088171055f2be03d0d19ffd7bd5d56006349a9"
        ),
        "qualification_hash": (
            "sha256:ef289b20a7e3f953d546fbc7c037a0e4bc49d910dbbceb686800484cd4ab2b64"
        ),
        "source_evidence_hash": (
            "sha256:efdd54f63f201de7a13098eae199a31db975d18a15ab7fb5963889097f63ad65"
        ),
        "qualification_file_sha256": (
            "sha256:82b196df2e0e54dc7708ad6b37201185e9b8bc3c25ce03f2cb7fdd0bc8f72903"
        ),
    }
    assert lineage["corrective_r2"]["run_id"] == "run_4a9737ec91964dca"
    assert lineage["corrective_r2"]["distinct_experiment_and_run"] is True

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 0
    assert campaign["not_started_runs"] == 0
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True
    assert (
        campaign["execution_plan"]["canonical_content_hash"]
        != campaign["execution_plan"]["persisted_file_sha256"]
    )

    pilot = payload["pilot"]
    assert pilot["run_id"] == "run_4a9737ec91964dca"
    assert pilot["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert pilot["outcome_kind"] == "task_failure"
    assert pilot["agent_submission_status"] == "completed"
    assert pilot["evaluation_status"] == "completed"
    assert pilot["scope_compliant_success"] is False
    assert pilot["official"] is True
    assert pilot["event_count"] == 74
    assert pilot["checkpoint_count"] == 14
    assert pilot["patch_applied_events"] == 1
    assert pilot["tool_failures"] == 1
    assert pilot["verdicts"] == {
        "hidden_tests": "fail",
        "regression_tests": "pass",
        "scope_policy": "pass",
        "safety_policy": "pass",
    }

    qualification = pilot["trace_qualification_artifact"]
    assert qualification["schema_version"] == "trace-qualification-v2"
    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is True
    assert qualification["private_match_count"] == 0
    assert qualification["passed_check_count"] == qualification["check_count"] == 22
    assert qualification["memory_candidate_eligible"] is False

    usage = pilot["usage"]
    assert usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"]
    assert usage["total_tokens"] == 66238
    assert usage["total_tokens"] < usage["max_total_tokens"]
    assert usage["reasoning_output_tokens"] <= usage["output_tokens"]
    assert usage["model_cost_usd"] == pytest.approx(0.07796475)
    spend = payload["spend_to_date"]
    assert spend["mini_r1_usd"] + spend["mini_r2_usd"] == pytest.approx(
        spend["mini_lane_cumulative_usd"]
    )
    assert (
        spend["historical_terra_lane_cumulative_usd"] + spend["mini_lane_cumulative_usd"]
    ) == pytest.approx(spend["all_paid_pilot_list_price_total_usd"])
    assert spend["invoice_charge_verified"] is False

    diagnostic = payload["diagnostic_gate"]
    assert diagnostic["telemetry_and_submission_path_exercised"] is True
    assert diagnostic["evaluator_and_receipt_path_exercised"] is True
    assert diagnostic["task_acceptance_passed"] is False
    assert diagnostic["rejected_patch_retry_context_complete"] is False
    assert diagnostic["engineering_followup_required"] is True
    assert diagnostic["ready_for_v2_terra_pilot"] is False

    claims = payload["claims_boundary"]
    assert claims["paid_provider_path_exercised"] is True
    assert claims["prompt_token_integrity_passed"] is True
    assert claims["trace_qualification_artifact_qualified"] is True
    assert claims["evaluation_reached"] is True
    assert claims["v2_submission_lifecycle_passed"] is True
    assert claims["live_model_task_success"] is False
    assert claims["official_scope_compliant_success"] is False
    assert claims["accepted_live_pilot"] is False
    assert claims["mini_r2_substitutes_for_terra_pilot"] is False
    assert claims["development_campaign_unlocked"] is False


def test_mini_corrective_r2_lifecycle_and_context_gap_are_explicit() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    lifecycle = payload["submission_lifecycle"]
    ordered_sequences = [
        lifecycle["patch_applied_sequence"],
        lifecycle["current_diff_visible_check_sequence"],
        lifecycle["post_check_get_diff_sequence"],
        lifecycle["review_phase_sequence"],
        lifecycle["final_model_call_sequence"],
        lifecycle["finish_task_sequence"],
        lifecycle["review_recorded_sequence"],
        lifecycle["submission_attempted_sequence"],
        lifecycle["finish_task_succeeded_sequence"],
        lifecycle["submission_accepted_sequence"],
        lifecycle["done_phase_sequence"],
    ]
    assert ordered_sequences == sorted(ordered_sequences)
    assert lifecycle["same_diff_preserved"] is True
    assert lifecycle["complete_diff_in_final_request"] is True
    assert lifecycle["mutation_after_review"] is False

    mutations = payload["mutations"]
    assert mutations["rejected_attempt"]["official_evaluator_run"] is None
    assert mutations["rejected_attempt"]["counterfactual_success_claimed"] is False
    assert mutations["applied_attempt"]["patch_applied_exactly_once"] is True
    assert (
        mutations["applied_attempt"]["raw_model_patch_sha256"]
        != mutations["applied_attempt"]["worktree_diff_sha256"]
    )

    context = payload["context_rehydration_diagnostic"]
    assert context["provider_state_used"] is False
    assert context["previous_response_id_used"] is False
    assert context["rejected_patch_content_hash_present"] is True
    assert context["rejected_patch_raw_bytes_present"] is False
    assert context["structured_failure_present"] is True
    assert context["provider_truncation_observed"] is False
    assert context["audit_basis"] == "post-run D-037 target audit"
    assert context["qualification_check_active_in_run"] is False
    assert context["followup_required"] is True

    token_integrity = payload["prompt_token_integrity"]
    assert token_integrity["exact_input_count_matches"] == (token_integrity["model_call_count"])
    assert token_integrity["all_responses_completed"] is True
    assert token_integrity["truncation_mode"] == "disabled"
    assert token_integrity["incomplete_response_count"] == 0
    assert token_integrity["prompt_cut_observed"] is False


def test_mini_corrective_r2_portable_artifacts_are_hash_bound() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    applied = _artifact_for_role(payload, "applied-model-tool-argument")
    submitted = _artifact_for_role(payload, "final-submitted-task-failure-diff")
    _assert_artifact_identity(applied)
    _assert_artifact_identity(submitted)
    assert applied["sha256"] == (payload["mutations"]["applied_attempt"]["raw_model_patch_sha256"])
    assert submitted["sha256"] == payload["submitted_patch"]["patch_sha256"]
    assert submitted["sha256"] != applied["sha256"]


def test_mini_corrective_r2_raw_evidence_and_journal_match_when_available() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local mini-r2 evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/dev-validation-gpt54mini-pilot-20260729-r2.jsonl")
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"]).read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for expected_sequence, journal_row in enumerate(journal_rows, start=1):
        recorded_hash = journal_row.pop("event_hash")
        assert journal_row["sequence"] == expected_sequence
        assert journal_row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(journal_row)) == recorded_hash
        previous_hash = recorded_hash
    assert previous_hash == payload["campaign"]["journal"]["last_event_hash"]
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        Path(artifacts[0]["path"]).read_bytes()
    )

    plan_artifact = next(
        artifact for artifact in artifacts if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(Path(plan_artifact["path"]).read_text(encoding="utf-8"))
    assert (
        sha256_text(canonical_json(plan_payload))
        == (payload["campaign"]["execution_plan"]["canonical_content_hash"])
    )

    qualification = load_trace_qualification("run_4a9737ec91964dca")
    assert (
        qualification["qualification_hash"]
        == (payload["pilot"]["trace_qualification_artifact"]["qualification_hash"])
    )
    assert (
        len(qualification["checks"])
        == (payload["pilot"]["trace_qualification_artifact"]["check_count"])
    )
    assert all(check["passed"] for check in qualification["checks"])
    assert (
        calculate_source_evidence_hash("run_4a9737ec91964dca")
        == (payload["pilot"]["trace_qualification_artifact"]["source_evidence_hash"])
    )

    receipt_artifact = next(
        artifact for artifact in artifacts if artifact["path"].endswith("/evaluation-receipt.json")
    )
    receipt = json.loads(Path(receipt_artifact["path"]).read_text(encoding="utf-8"))
    for filename, expected_hash in receipt["file_hashes"].items():
        source = next(
            artifact for artifact in artifacts if artifact["path"].endswith(f"/{filename}")
        )
        assert source["sha256"] == expected_hash
    assert receipt["worktree_diff_hash"] == payload["submitted_patch"]["diff_sha256"]

    applied = _artifact_for_role(payload, "applied-model-tool-argument")
    submitted = _artifact_for_role(payload, "final-submitted-task-failure-diff")
    raw_applied = next(
        artifact for artifact in artifacts if artifact["sha256"] == applied["sha256"]
    )
    raw_submitted = next(
        artifact for artifact in artifacts if artifact["path"].endswith("/submitted.patch")
    )
    assert Path(applied["path"]).read_bytes() == Path(raw_applied["path"]).read_bytes()
    assert Path(submitted["path"]).read_bytes() == Path(raw_submitted["path"]).read_bytes()

    rejected_patch = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"] == payload["mutations"]["rejected_attempt"]["patch_sha256"]
    )
    retry_request = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"]
        == payload["context_rehydration_diagnostic"]["retry_request_artifact_sha256"]
    )
    rejected_text = Path(rejected_patch["path"]).read_text(encoding="utf-8")
    retry_evidence = json.loads(Path(retry_request["path"]).read_text(encoding="utf-8"))
    request_body = retry_evidence["request_body"]
    request_text = "\n".join(item["content"] for item in request_body["input"])
    assert rejected_text not in request_text
    assert payload["mutations"]["rejected_attempt"]["patch_sha256"] in request_text
    assert "CONTRACT_ERROR" in request_text
    assert request_body["store"] is False
    assert "previous_response_id" not in request_body
    assert request_body["truncation"] == "disabled"

    retry_response = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"]
        == "sha256:96057999174eba8a1340089439d4687dc4e5b1a44a43de02e307de549939a5ab"
    )
    response_payload = json.loads(Path(retry_response["path"]).read_text(encoding="utf-8"))
    assert response_payload["requested_input_tokens"] == response_payload["input_tokens"]
    assert response_payload["response_status"] == "completed"
    assert response_payload["response_truncation"] == "disabled"
    assert response_payload["response_incomplete_reason"] is None

    r1_qualification_path = Path(".patchloop/qualifications/run_d4fea5e7198b4abc.json")
    if r1_qualification_path.is_file():
        r1_lineage = payload["retry_lineage"]["terminal_r1"]
        assert (
            sha256_bytes(r1_qualification_path.read_bytes())
            == (r1_lineage["qualification_file_sha256"])
        )
        r1_qualification = load_trace_qualification("run_d4fea5e7198b4abc")
        assert r1_qualification["qualification_hash"] == (r1_lineage["qualification_hash"])
        assert r1_qualification["source_evidence_hash"] == (r1_lineage["source_evidence_hash"])


def test_mini_corrective_r2_checked_evidence_has_no_private_payload() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    forbidden_keys = {
        "check_id",
        "verifier_results",
        "evidence_artifacts",
        "artifact_path",
        "private_spec_hash",
        "hidden_artifacts",
        "request_body",
        "response_id",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {nested for child in value.values() for nested in walk_keys(child)}
        if isinstance(value, list):
            return {nested for child in value for nested in walk_keys(child)}
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))

    checked_text = path.read_text(encoding="utf-8")
    for artifact in payload["portable_artifacts"]:
        checked_text += Path(artifact["path"]).read_text(encoding="utf-8")
    package = load_task_package("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_mini_d037_r3_preserves_terminal_failure_without_claiming_exercise() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r3.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v3"
    assert payload["execution_hash"] == (
        "sha256:c33a50abe48b554c37d95de4833d1d17ede816f4d128b9adc22e88c010e138e6"
    )
    assert payload["harness_commit"] == (
        "11a83c2cdff06978dc961e7b3b3c0caada3b386e"
    )

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 1
    assert campaign["diagnostic_errors"] == 1
    assert campaign["not_started_runs"] == 0
    assert campaign["halt_reason"] == "QualificationFailureHalt"
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    pilot = payload["pilot"]
    assert pilot["run_id"] == "run_e90f7c52aa134182"
    assert pilot["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert pilot["outcome_kind"] == "agent_failure"
    assert pilot["agent_submission_status"] == "failed"
    assert pilot["evaluation_status"] == "not_run"
    assert pilot["official"] is False
    assert pilot["event_count"] == 57
    assert pilot["checkpoint_count"] == 13
    assert pilot["model_calls"] == 8
    assert pilot["tool_calls"] == 12
    assert pilot["patch_prepared_events"] == 0
    assert pilot["patch_applied_events"] == 0
    assert set(pilot["verdicts"].values()) == {"not_run"}

    usage = pilot["usage"]
    assert usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"]
    assert usage["total_tokens"] == 60_930
    assert usage["remaining_total_tokens"] == 29_070
    assert usage["reasoning_output_tokens"] <= usage["output_tokens"]
    assert usage["model_cost_usd"] == pytest.approx(0.06849375)

    activity = payload["trace_activity"]
    assert activity["tool_breakdown"] == {"search_files": 7, "read_file": 5}
    assert activity["mutation_attempts"] == 0
    assert activity["rejected_patch_candidates"] == 0
    assert activity["submitted_patch"] is None
    assert activity["evaluator_runs"] == 0

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["requested_input_tokens"] == (
        telemetry["provider_reported_input_tokens"]
    )
    assert telemetry["exact_input_count_matches"] == telemetry["model_call_count"] == 8
    assert telemetry["completed_response_count"] == 7
    assert telemetry["incomplete_response_count"] == 1
    assert telemetry["truncation_mode"] == "disabled"
    assert telemetry["prompt_cut_observed"] is False

    terminal = payload["terminal_response"]
    assert terminal["model_event_sequence"] == 55
    assert terminal["requested_input_tokens"] == terminal["provider_reported_input_tokens"]
    assert terminal["input_token_count_match"] is True
    assert terminal["output_tokens"] == pilot["max_output_tokens"] == 4096
    assert terminal["reasoning_output_tokens"] == 3989
    assert terminal["response_status"] == "incomplete"
    assert terminal["response_incomplete_reason"] == "max_output_tokens"
    assert terminal["response_truncation"] == "disabled"
    assert terminal["complete_tool_call_present"] is False
    assert terminal["not_total_run_budget_exhaustion"] is True
    assert terminal["not_input_prompt_truncation"] is True

    qualification = payload["trace_qualification_artifact"]
    assert qualification["qualified"] is False
    assert qualification["trace_integrity_passed"] is False
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is False
    assert qualification["passed_check_count"] == 21
    assert qualification["check_count"] == 22
    assert qualification["failed_check_name"] == "prompt_token_integrity"
    assert qualification["failed_event_sequences"] == [55]

    feature = payload["d037_retry_feature"]
    assert feature["conditional_check_passed"] is True
    assert feature["rejected_candidate_count"] == 0
    assert feature["retry_episode_count"] == 0
    assert feature["verified_retry_count"] == 0
    assert feature["failed_source_failure_sequences"] == []
    assert feature["live_retry_exercised"] is False
    assert feature["live_retry_validated"] is False

    diagnostic = payload["diagnostic_gate"]
    assert diagnostic["status"] == "failed"
    assert diagnostic["reason_code"] == "qualification_not_passed"
    assert diagnostic["inconclusive_runs"] == 0
    assert diagnostic["ready_for_v2_terra_pilot"] is False

    spend = payload["spend_to_date"]
    assert (
        spend["mini_r1_usd"] + spend["mini_r2_usd"] + spend["mini_r3_usd"]
    ) == pytest.approx(spend["mini_lane_cumulative_usd"])
    assert (
        spend["historical_terra_lane_cumulative_usd"]
        + spend["mini_lane_cumulative_usd"]
    ) == pytest.approx(spend["all_paid_pilot_list_price_total_usd"])
    assert spend["all_paid_pilot_list_price_total_usd"] == pytest.approx(
        1.052776125
    )
    assert spend["invoice_charge_verified"] is False

    assert payload["portable_artifacts"] == []
    claims = payload["claims_boundary"]
    assert claims["paid_provider_path_exercised"] is True
    assert claims["provider_input_truncation_observed"] is False
    assert claims["terminal_response_completed"] is False
    assert claims["trace_qualification_artifact_qualified"] is False
    assert claims["evaluation_reached"] is False
    assert claims["d037_live_retry_exercised"] is False
    assert claims["d037_live_retry_validated"] is False
    assert claims["accepted_live_pilot"] is False
    assert claims["development_campaign_unlocked"] is False


def test_mini_d037_r3_raw_evidence_matches_when_available() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r3.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local mini-r3 evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/dev-validation-gpt54mini-d037-20260729-r3.jsonl")
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"]).read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for expected_sequence, journal_row in enumerate(journal_rows, start=1):
        recorded_hash = journal_row.pop("event_hash")
        assert journal_row["sequence"] == expected_sequence
        assert journal_row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(journal_row)) == recorded_hash
        previous_hash = recorded_hash
    assert previous_hash == payload["campaign"]["journal"]["final_event_hash"]
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        Path(artifacts[0]["path"]).read_bytes()
    )

    plan_artifact = next(
        artifact for artifact in artifacts if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(Path(plan_artifact["path"]).read_text(encoding="utf-8"))
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )

    qualification = load_trace_qualification("run_e90f7c52aa134182")
    assert qualification["qualification_hash"] == (
        payload["trace_qualification_artifact"]["qualification_hash"]
    )
    assert len(qualification["checks"]) == (
        payload["trace_qualification_artifact"]["check_count"]
    )
    assert sum(check["passed"] for check in qualification["checks"]) == (
        payload["trace_qualification_artifact"]["passed_check_count"]
    )
    assert calculate_source_evidence_hash("run_e90f7c52aa134182") == (
        payload["trace_qualification_artifact"]["source_evidence_hash"]
    )

    terminal_request = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"]
        == "sha256:9486d3b233979e2fe75620381f598cbf85fa58d09a4ad731980d4d4d3b4292ca"
    )
    terminal_response = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"]
        == "sha256:d1cb3c6bc27a11587755eaebd7d479f81cb7978aa407b66c265b6b63e8dbc639"
    )
    request_evidence = json.loads(
        Path(terminal_request["path"]).read_text(encoding="utf-8")
    )
    request_body = request_evidence["request_body"]
    assert request_body["store"] is False
    assert "previous_response_id" not in request_body
    assert request_body["truncation"] == "disabled"
    assert request_body["max_output_tokens"] == 4096

    response_evidence = json.loads(
        Path(terminal_response["path"]).read_text(encoding="utf-8")
    )
    terminal = payload["terminal_response"]
    assert response_evidence["requested_input_tokens"] == (
        terminal["requested_input_tokens"]
    )
    assert response_evidence["input_tokens"] == terminal["provider_reported_input_tokens"]
    assert response_evidence["output_tokens"] == terminal["output_tokens"]
    assert response_evidence["reasoning_output_tokens"] == (
        terminal["reasoning_output_tokens"]
    )
    assert response_evidence["response_status"] == terminal["response_status"]
    assert response_evidence["response_incomplete_reason"] == (
        terminal["response_incomplete_reason"]
    )
    assert response_evidence["tool_calls"] == []


def test_mini_d037_r3_checked_evidence_has_no_private_or_provider_payload() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r3.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["portable_artifacts"] == []
    assert set(payload) == {
        "schema_version",
        "recorded_at",
        "task_id",
        "harness_commit",
        "execution_hash",
        "retry_lineage",
        "campaign",
        "pilot",
        "trace_activity",
        "prompt_token_integrity",
        "terminal_response",
        "trace_qualification_artifact",
        "d037_retry_feature",
        "diagnostic_gate",
        "failure_record",
        "spend_to_date",
        "evidence_policy",
        "portable_artifacts",
        "raw_local_artifacts",
        "claims_boundary",
    }

    forbidden_keys = {
        "api_key",
        "authorization",
        "check_id",
        "verifier_results",
        "evidence_artifacts",
        "artifact_path",
        "headers",
        "input",
        "instructions",
        "output",
        "private_spec_hash",
        "hidden_artifacts",
        "request",
        "request_body",
        "response",
        "response_error",
        "response_id",
        "system_fingerprint",
        "text",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {nested for child in value.values() for nested in walk_keys(child)}
        if isinstance(value, list):
            return {nested for child in value for nested in walk_keys(child)}
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))

    def values_for_key(value: object, key: str) -> list[object]:
        if isinstance(value, dict):
            return [
                *(child for item_key, child in value.items() if item_key == key),
                *(
                    nested
                    for child in value.values()
                    for nested in values_for_key(child, key)
                ),
            ]
        if isinstance(value, list):
            return [
                nested
                for child in value
                for nested in values_for_key(child, key)
            ]
        return []

    assert values_for_key(payload, "tool_calls") == [12]

    checked_text = path.read_text(encoding="utf-8")
    package = load_task_package("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_mini_d037_r4_preserves_budget_failure_without_claiming_retry() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r4.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v4"
    assert payload["execution_hash"] == (
        "sha256:bbb6dbdcab1c7561c868ae4cc40478d6e3401c5900feb59b8ea09ef38d9156a1"
    )
    assert payload["harness_commit"] == (
        "c820a5e6f7b18697fded15bfa8097297253c54b6"
    )

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 1
    assert campaign["diagnostic_errors"] == 1
    assert campaign["not_started_runs"] == 0
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    pilot = payload["pilot"]
    assert pilot["run_id"] == "run_826c1c7fb3d242c2"
    assert pilot["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert pilot["max_output_tokens"] == 25_000
    assert pilot["max_total_tokens"] == 120_000
    assert pilot["outcome_kind"] == "agent_failure"
    assert pilot["agent_submission_status"] == "failed"
    assert pilot["evaluation_status"] == "not_run"
    assert pilot["official"] is False
    assert pilot["event_count"] == 88
    assert pilot["checkpoint_count"] == 17
    assert pilot["model_calls"] == 13
    assert pilot["input_token_count_calls"] == 14
    assert pilot["tool_calls"] == 16
    assert pilot["patch_prepared_events"] == pilot["patch_applied_events"] == 1
    assert pilot["submission_attempted_events"] == 0
    assert set(pilot["verdicts"].values()) == {"not_run"}

    usage = pilot["usage"]
    assert usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"]
    assert usage["total_tokens"] == 91_437
    assert usage["remaining_total_tokens"] == 28_563
    assert usage["reasoning_output_tokens"] <= usage["output_tokens"]
    assert usage["model_cost_usd"] == pytest.approx(0.096159)

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["requested_input_tokens"] == (
        telemetry["provider_reported_input_tokens"]
    )
    assert telemetry["exact_input_count_matches"] == telemetry["model_call_count"] == 13
    assert telemetry["total_token_count_matches"] == 13
    assert telemetry["completed_generation_count"] == 13
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["truncation_mode"] == "disabled"
    assert telemetry["provider_prompt_cut_observed"] is False
    assert telemetry["truncated_tool_result_count"] == 0

    guard = payload["terminal_budget_guard"]
    assert guard["generation_started"] is False
    assert guard["requested_input_tokens"] == 8_583
    assert guard["remaining_tokens"] == 28_563
    assert guard["max_output_tokens"] == 25_000
    assert guard["required_reservation_tokens"] == 33_583
    assert guard["reservation_shortfall_tokens"] == 5_020
    assert guard["retry_context_present"] is False
    assert guard["candidate_content_hash"] is None
    assert guard["per_call_output_ceiling_recurred"] is False

    qualification = payload["trace_qualification_artifact"]
    assert qualification["qualified"] is False
    assert qualification["trace_integrity_passed"] is False
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is False
    assert qualification["passed_check_count"] == 21
    assert qualification["check_count"] == 22
    assert qualification["failed_check_name"] == "prompt_token_integrity"
    assert qualification["failed_event_sequences"] == []
    assert qualification["terminal_generation_block_valid"] is False

    feature = payload["d037_retry_feature"]
    assert feature["conditional_check_passed"] is True
    assert feature["rejected_candidate_count"] == 0
    assert feature["retry_episode_count"] == 0
    assert feature["verified_retry_count"] == 0
    assert feature["failed_source_failure_sequences"] == []
    assert feature["live_retry_exercised"] is False
    assert feature["live_retry_validated"] is False

    diagnostic = payload["diagnostic_gate"]
    assert diagnostic["profile"] == "d037-rejected-patch-retry-v2"
    assert diagnostic["status"] == "failed"
    assert diagnostic["reason_code"] == "qualification_not_passed"
    assert diagnostic["ready_for_v2_terra_pilot"] is False

    spend = payload["spend_to_date"]
    assert (
        spend["mini_r1_usd"]
        + spend["mini_r2_usd"]
        + spend["mini_r3_usd"]
        + spend["mini_r4_usd"]
    ) == pytest.approx(spend["mini_lane_cumulative_usd"])
    assert (
        spend["historical_terra_lane_cumulative_usd"]
        + spend["mini_lane_cumulative_usd"]
    ) == pytest.approx(spend["all_paid_pilot_list_price_total_usd"])
    assert spend["all_paid_pilot_list_price_total_usd"] == pytest.approx(
        1.148935125
    )
    assert spend["invoice_charge_verified"] is False

    claims = payload["claims_boundary"]
    assert claims["paid_provider_path_exercised"] is True
    assert claims["executed_request_token_counts_match"] is True
    assert claims["provider_input_truncation_observed"] is False
    assert claims["incomplete_model_generation_observed"] is False
    assert claims["r3_output_ceiling_confounder_removed"] is True
    assert claims["total_budget_guard_exercised"] is True
    assert claims["trace_qualification_artifact_qualified"] is False
    assert claims["evaluation_reached"] is False
    assert claims["d037_live_retry_exercised"] is False
    assert claims["d037_live_retry_validated"] is False
    assert claims["accepted_live_pilot"] is False
    assert claims["development_campaign_unlocked"] is False


def test_mini_d037_r4_artifacts_are_hash_bound_when_available() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r4.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["portable_artifacts"]) == 1
    portable_candidate = payload["portable_artifacts"][0]
    assert portable_candidate["role"] == "applied-model-candidate"
    _assert_artifact_identity(portable_candidate)

    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local mini-r4 evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    raw_candidate = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"] == portable_candidate["sha256"]
    )
    assert Path(raw_candidate["path"]).read_bytes() == Path(
        portable_candidate["path"]
    ).read_bytes()

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith(
            "/dev-validation-gpt54mini-d037-20260729-r4.jsonl"
        )
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"]).read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for expected_sequence, journal_row in enumerate(journal_rows, start=1):
        recorded_hash = journal_row.pop("event_hash")
        assert journal_row["sequence"] == expected_sequence
        assert journal_row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(journal_row)) == recorded_hash
        previous_hash = recorded_hash
    assert previous_hash == payload["campaign"]["journal"]["final_event_hash"]
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        Path(artifacts[0]["path"]).read_bytes()
    )

    plan_artifact = next(
        artifact for artifact in artifacts if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(Path(plan_artifact["path"]).read_text(encoding="utf-8"))
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )

    qualification = load_trace_qualification("run_826c1c7fb3d242c2")
    assert qualification["qualification_hash"] == (
        payload["trace_qualification_artifact"]["qualification_hash"]
    )
    assert len(qualification["checks"]) == (
        payload["trace_qualification_artifact"]["check_count"]
    )
    assert sum(check["passed"] for check in qualification["checks"]) == (
        payload["trace_qualification_artifact"]["passed_check_count"]
    )
    assert calculate_source_evidence_hash("run_826c1c7fb3d242c2") == (
        payload["trace_qualification_artifact"]["source_evidence_hash"]
    )

    blocked_request = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"]
        == "sha256:ac9def9a14427402c7c0be649f7508af87b54eaa9ed730be982b30fef87a5fe1"
    )
    request_evidence = json.loads(
        Path(blocked_request["path"]).read_text(encoding="utf-8")
    )
    request_body = request_evidence["request_body"]
    assert request_body["store"] is False
    assert "previous_response_id" not in request_body
    assert request_body["truncation"] == "disabled"
    assert request_body["max_output_tokens"] == 25_000


def test_mini_d037_r4_checked_evidence_has_no_private_or_provider_payload() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r4.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {
        "schema_version",
        "recorded_at",
        "task_id",
        "harness_commit",
        "execution_hash",
        "retry_lineage",
        "campaign",
        "pilot",
        "trace_activity",
        "prompt_token_integrity",
        "terminal_budget_guard",
        "trace_qualification_artifact",
        "d037_retry_feature",
        "diagnostic_gate",
        "failure_record",
        "spend_to_date",
        "evidence_policy",
        "portable_artifacts",
        "raw_local_artifacts",
        "claims_boundary",
    }

    forbidden_keys = {
        "api_key",
        "authorization",
        "check_id",
        "verifier_results",
        "evidence_artifacts",
        "artifact_path",
        "headers",
        "input",
        "instructions",
        "output",
        "private_spec_hash",
        "hidden_artifacts",
        "request",
        "request_body",
        "response",
        "response_error",
        "response_id",
        "system_fingerprint",
        "text",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {nested for child in value.values() for nested in walk_keys(child)}
        if isinstance(value, list):
            return {nested for child in value for nested in walk_keys(child)}
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))

    checked_text = path.read_text(encoding="utf-8")
    for artifact in payload["portable_artifacts"]:
        checked_text += Path(artifact["path"]).read_text(encoding="utf-8")
    package = load_task_package("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_mini_d037_r5_preserves_task_success_without_claiming_retry() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r5.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v5"
    assert payload["execution_hash"] == (
        "sha256:97249f05deda8e59118fdac0dd6f62f44c18b086ecb16bface2cc4d0f41a3a12"
    )
    assert payload["harness_commit"] == (
        "a323bfe4bde46cb0e797a2c8eefacad3c2e8d7d1"
    )

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 0
    assert campaign["diagnostic_errors"] == 1
    assert campaign["not_started_runs"] == 0
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    pilot = payload["pilot"]
    assert pilot["run_id"] == "run_0ad8676d42614fbf"
    assert pilot["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert pilot["max_output_tokens"] == 25_000
    assert pilot["max_total_tokens"] == 200_000
    assert pilot["outcome_kind"] == "resolved"
    assert pilot["agent_submission_status"] == "completed"
    assert pilot["evaluation_status"] == "completed"
    assert pilot["scope_compliant_success"] is True
    assert pilot["official"] is True
    assert set(pilot["verdicts"].values()) == {"pass"}
    assert pilot["event_count"] == 131
    assert pilot["checkpoint_count"] == 28
    assert pilot["model_calls"] == pilot["input_token_count_calls"] == 18
    assert pilot["tool_calls"] == 27
    assert pilot["tool_failures"] == 0
    assert pilot["patch_prepared_events"] == pilot["patch_applied_events"] == 1
    assert pilot["submission_attempted_events"] == 1
    assert pilot["submission_rejected_events"] == 0
    assert pilot["submission_accepted_events"] == 1

    usage = pilot["usage"]
    assert usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"]
    assert usage["total_tokens"] == 131_279
    assert usage["remaining_total_tokens"] == 68_721
    assert usage["reasoning_output_tokens"] <= usage["output_tokens"]
    assert usage["model_cost_usd"] == pytest.approx(0.135633)

    activity = payload["trace_activity"]
    assert sum(activity["tool_breakdown"].values()) == pilot["tool_calls"]
    assert activity["rejected_patch_candidates"] == 0
    assert activity["terminal_phase"] == "DONE"
    assert activity["review_recorded"] is True
    assert activity["submission_order_valid"] is True
    assert activity["changed_files"] == ["babel/numbers.py"]
    assert activity["added_lines"] == activity["deleted_lines"] == 1

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["requested_input_tokens"] == (
        telemetry["provider_reported_input_tokens"]
    )
    assert sum(telemetry["requested_input_tokens"]) == usage["input_tokens"]
    assert telemetry["exact_input_count_matches"] == telemetry["model_call_count"] == 18
    assert telemetry["total_token_count_matches"] == 18
    assert telemetry["completed_generation_count"] == 18
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["truncation_mode"] == "disabled"
    assert telemetry["provider_prompt_cut_observed"] is False
    assert telemetry["previous_response_id_used_count"] == 0
    assert telemetry["store_true_count"] == 0
    assert telemetry["truncated_tool_result_count"] == 0
    assert telemetry["maximum_context_policy_omitted_event_count"] == 75

    qualification = payload["trace_qualification_artifact"]
    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is True
    assert qualification["passed_check_count"] == qualification["check_count"] == 23
    assert qualification["failed_check_names"] == []
    assert qualification["failed_event_sequences"] == []

    feature = payload["d037_retry_feature"]
    assert feature["conditional_check_passed"] is True
    assert feature["rejected_candidate_count"] == 0
    assert feature["retry_episode_count"] == 0
    assert feature["verified_retry_count"] == 0
    assert feature["failed_source_failure_sequences"] == []
    assert feature["live_retry_exercised"] is False
    assert feature["live_retry_validated"] is False

    diagnostic = payload["diagnostic_gate"]
    assert diagnostic["profile"] == "d037-rejected-patch-retry-v3"
    assert diagnostic["status"] == "inconclusive"
    assert diagnostic["reason_code"] == "retry_episode_not_observed"
    assert diagnostic["passed_runs"] == 0
    assert diagnostic["inconclusive_runs"] == 1
    assert diagnostic["failed_runs"] == 0
    assert diagnostic["automatic_rerun_allowed"] is False
    assert diagnostic["ready_for_v2_terra_pilot"] is False

    spend = payload["spend_to_date"]
    assert (
        spend["mini_r1_usd"]
        + spend["mini_r2_usd"]
        + spend["mini_r3_usd"]
        + spend["mini_r4_usd"]
        + spend["mini_r5_usd"]
    ) == pytest.approx(spend["mini_lane_cumulative_usd"])
    assert (
        spend["historical_terra_lane_cumulative_usd"]
        + spend["mini_lane_cumulative_usd"]
    ) == pytest.approx(spend["all_paid_pilot_list_price_total_usd"])
    assert spend["all_paid_pilot_list_price_total_usd"] == pytest.approx(
        1.284568125
    )
    assert spend["invoice_charge_verified"] is False

    claims = payload["claims_boundary"]
    assert claims["paid_provider_path_exercised"] is True
    assert claims["executed_request_token_counts_match"] is True
    assert claims["provider_input_truncation_observed"] is False
    assert claims["incomplete_model_generation_observed"] is False
    assert claims["trace_qualification_artifact_qualified"] is True
    assert claims["evaluation_reached"] is True
    assert claims["official_model_candidate_task_success"] is True
    assert claims["d037_live_retry_exercised"] is False
    assert claims["d037_live_retry_validated"] is False
    assert claims["accepted_d037_diagnostic"] is False
    assert claims["development_campaign_unlocked"] is False


def test_mini_d037_r5_artifacts_are_hash_bound_when_available() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r5.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["portable_artifacts"]) == 1
    portable_candidate = payload["portable_artifacts"][0]
    assert portable_candidate["role"] == "submitted-model-candidate"
    _assert_artifact_identity(portable_candidate)

    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local mini-r5 evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    raw_candidate = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"] == portable_candidate["sha256"]
    )
    assert Path(raw_candidate["path"]).read_bytes() == Path(
        portable_candidate["path"]
    ).read_bytes()

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith(
            "/dev-validation-gpt54mini-d037-20260730-r5.jsonl"
        )
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"]).read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for expected_sequence, journal_row in enumerate(journal_rows, start=1):
        recorded_hash = journal_row.pop("event_hash")
        assert journal_row["sequence"] == expected_sequence
        assert journal_row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(journal_row)) == recorded_hash
        previous_hash = recorded_hash
    assert previous_hash == payload["campaign"]["journal"]["final_event_hash"]
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        Path(artifacts[0]["path"]).read_bytes()
    )

    plan_artifact = next(
        artifact for artifact in artifacts if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(Path(plan_artifact["path"]).read_text(encoding="utf-8"))
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )

    qualification = load_trace_qualification("run_0ad8676d42614fbf")
    assert qualification["qualification_hash"] == (
        payload["trace_qualification_artifact"]["qualification_hash"]
    )
    assert len(qualification["checks"]) == (
        payload["trace_qualification_artifact"]["check_count"]
    )
    assert sum(check["passed"] for check in qualification["checks"]) == (
        payload["trace_qualification_artifact"]["passed_check_count"]
    )
    assert calculate_source_evidence_hash("run_0ad8676d42614fbf") == (
        payload["trace_qualification_artifact"]["source_evidence_hash"]
    )

    result_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/run_0ad8676d42614fbf/result.json")
    )
    result_payload = json.loads(Path(result_artifact["path"]).read_text(encoding="utf-8"))
    assert result_payload["official"] is True
    assert result_payload["scope_compliant_success"] is True
    assert result_payload["submitted_patch_artifact_id"] == (
        payload["trace_activity"]["submitted_patch_artifact_id"]
    )


def test_mini_d037_r5_checked_evidence_has_no_private_or_provider_payload() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r5.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {
        "schema_version",
        "recorded_at",
        "task_id",
        "harness_commit",
        "execution_hash",
        "retry_lineage",
        "campaign",
        "pilot",
        "trace_activity",
        "prompt_token_integrity",
        "trace_qualification_artifact",
        "d037_retry_feature",
        "diagnostic_gate",
        "spend_to_date",
        "evidence_policy",
        "portable_artifacts",
        "raw_local_artifacts",
        "claims_boundary",
    }

    forbidden_keys = {
        "api_key",
        "authorization",
        "check_id",
        "verifier_results",
        "evidence_artifacts",
        "artifact_path",
        "headers",
        "input",
        "instructions",
        "output",
        "private_spec_hash",
        "hidden_artifacts",
        "request",
        "request_body",
        "response",
        "response_error",
        "response_id",
        "system_fingerprint",
        "text",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {nested for child in value.values() for nested in walk_keys(child)}
        if isinstance(value, list):
            return {nested for child in value for nested in walk_keys(child)}
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))

    checked_text = path.read_text(encoding="utf-8")
    for artifact in payload["portable_artifacts"]:
        checked_text += Path(artifact["path"]).read_text(encoding="utf-8")
    package = load_task_package("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_mini_d037_r6_preserves_controlled_retry_success_without_model_quality_claim() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r6.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v6"
    assert payload["execution_hash"] == (
        "sha256:d6a756dc69a7cf6e024d541b64a458a940ec41bdfeb3c403a3f01c539660e67b"
    )
    assert payload["harness_commit"] == (
        "1333ab968e2f144b632c0cb5ca341ebd30e0ca4e"
    )

    lineage = payload["retry_lineage"]
    assert lineage["terminal_r5"]["run_id"] == "run_0ad8676d42614fbf"
    assert lineage["terminal_r5"]["diagnostic_status"] == "inconclusive"
    assert lineage["terminal_r5"]["immutable"] is True
    assert lineage["controlled_r6"]["run_id"] == "run_73f5aaf7328a4ea5"
    assert lineage["controlled_r6"]["diagnostic_status"] == "passed"
    assert lineage["controlled_r6"]["distinct_experiment_and_run"] is True
    assert lineage["controlled_r6"]["immutable"] is True

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 0
    assert campaign["diagnostic_errors"] == 0
    assert campaign["not_started_runs"] == 0
    assert campaign["halt_reason"] is None
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    pilot = payload["pilot"]
    assert pilot["run_id"] == "run_73f5aaf7328a4ea5"
    assert pilot["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert pilot["max_output_tokens"] == 25_000
    assert pilot["max_total_tokens"] == 200_000
    assert pilot["fault"] == {
        "type": "controlled-reject-first-prepared-patch",
        "trigger_after": 1,
    }
    assert pilot["outcome_kind"] == "resolved"
    assert pilot["agent_submission_status"] == "completed"
    assert pilot["evaluation_status"] == "completed"
    assert pilot["scope_compliant_success"] is True
    assert pilot["official"] is True
    assert set(pilot["verdicts"].values()) == {"pass"}
    assert pilot["event_count"] == 149
    assert pilot["checkpoint_count"] == 33
    assert pilot["model_calls"] == pilot["input_token_count_calls"] == 19
    assert pilot["tool_calls"] == 32
    assert pilot["tool_failures"] == 1
    assert pilot["patch_prepared_events"] == 2
    assert pilot["patch_applied_events"] == 1
    assert pilot["submission_attempted_events"] == 1
    assert pilot["submission_rejected_events"] == 0
    assert pilot["submission_accepted_events"] == 1

    usage = pilot["usage"]
    assert usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"]
    assert usage["total_tokens"] == 152_062
    assert usage["remaining_total_tokens"] == 47_938
    assert usage["reasoning_output_tokens"] <= usage["output_tokens"]
    assert usage["model_cost_usd"] == pytest.approx(0.1657965)

    activity = payload["trace_activity"]
    assert sum(activity["tool_breakdown"].values()) == pilot["tool_calls"]
    assert activity["mutation_attempts"] == 2
    assert activity["rejected_patch_candidates"] == 1
    assert activity["controlled_rejection_events"] == 1
    assert activity["controlled_rejected_action_patch_applied_events"] == 0
    assert activity["terminal_phase"] == "DONE"
    assert activity["review_recorded"] is True
    assert activity["submission_order_valid"] is True
    assert activity["changed_files"] == ["babel/numbers.py"]
    assert activity["added_lines"] == activity["deleted_lines"] == 1

    controlled = payload["controlled_rejection_evidence"]
    assert controlled["schema_version"] == "controlled-rejection-v1"
    assert controlled["source_call_sequence"] == 86
    assert controlled["source_prepared_sequence"] == 87
    assert controlled["source_failure_sequence"] == 88
    assert controlled["candidate_content_hash"] == (
        "sha256:05eef2c55f098b3fa23d7dfce417e5271fbfe24a5009f3b4b5506c9546cea97b"
    )
    assert (
        controlled["baseline_worktree_diff_hash"]
        == controlled["observed_worktree_diff_hash"]
    )
    assert controlled["worktree_mutated"] is False
    assert controlled["patch_applied_for_rejected_action"] == 0
    assert controlled["next_context_sequence"] == 90
    assert controlled["next_model_sequence"] == 91
    assert controlled["next_request_candidate_body_rehydrated"] is True
    assert controlled["next_request_candidate_hash_rehydrated"] is True
    assert controlled["next_request_structured_reason_rehydrated"] is True
    assert controlled["next_request_truncated"] is False

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["requested_input_tokens"] == (
        telemetry["provider_reported_input_tokens"]
    )
    assert sum(telemetry["requested_input_tokens"]) == usage["input_tokens"]
    assert telemetry["exact_input_count_matches"] == telemetry["model_call_count"] == 19
    assert telemetry["total_token_count_matches"] == 19
    assert telemetry["completed_generation_count"] == 19
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["truncation_mode"] == "disabled"
    assert telemetry["provider_prompt_cut_observed"] is False
    assert telemetry["previous_response_id_used_count"] == 0
    assert telemetry["store_true_count"] == 0
    assert telemetry["truncated_tool_result_count"] == 0
    assert telemetry["maximum_context_policy_omitted_event_count"] == 91
    assert telemetry["maximum_completed_output_tokens"] == 6_124

    qualification = payload["trace_qualification_artifact"]
    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is True
    assert qualification["passed_check_count"] == qualification["check_count"] == 23
    assert qualification["failed_check_names"] == []
    assert qualification["failed_event_sequences"] == []

    feature = payload["d037_retry_feature"]
    assert feature["conditional_check_passed"] is True
    assert feature["rejected_candidate_count"] == 1
    assert feature["retry_episode_count"] == 1
    assert feature["verified_retry_count"] == 1
    assert feature["failed_source_failure_sequences"] == []
    assert feature["controlled_rejection_count"] == 1
    assert feature["verified_controlled_rejection_count"] == 1
    assert feature["failed_controlled_source_failure_sequences"] == []
    assert feature["controlled_patch_applied_sequences"] == []
    assert feature["live_retry_exercised"] is True
    assert feature["live_retry_validated"] is True
    assert "does not show natural model-error recovery" in feature["interpretation"]

    diagnostic = payload["diagnostic_gate"]
    assert diagnostic["profile"] == "d037-rejected-patch-retry-v4"
    assert diagnostic["status"] == "passed"
    assert diagnostic["reason_code"] is None
    assert diagnostic["passed_runs"] == 1
    assert diagnostic["inconclusive_runs"] == 0
    assert diagnostic["failed_runs"] == 0
    assert diagnostic["automatic_rerun_allowed"] is False
    assert diagnostic["ready_for_v2_terra_pilot"] is True

    spend = payload["spend_to_date"]
    assert (
        spend["mini_r1_usd"]
        + spend["mini_r2_usd"]
        + spend["mini_r3_usd"]
        + spend["mini_r4_usd"]
        + spend["mini_r5_usd"]
        + spend["mini_r6_usd"]
    ) == pytest.approx(spend["mini_lane_cumulative_usd"])
    assert (
        spend["historical_terra_lane_cumulative_usd"]
        + spend["mini_lane_cumulative_usd"]
    ) == pytest.approx(spend["all_paid_pilot_list_price_total_usd"])
    assert spend["all_paid_pilot_list_price_total_usd"] == pytest.approx(
        1.450364625
    )
    assert spend["invoice_charge_verified"] is False

    claims = payload["claims_boundary"]
    assert claims["paid_provider_path_exercised"] is True
    assert claims["executed_request_token_counts_match"] is True
    assert claims["trace_qualification_artifact_qualified"] is True
    assert claims["evaluation_reached"] is True
    assert claims["official_model_candidate_task_success"] is True
    assert claims["controlled_d037_retry_exercised"] is True
    assert claims["controlled_d037_retry_validated"] is True
    assert claims["natural_rejection_recovery_validated"] is False
    assert claims["model_quality_improvement_measured"] is False
    assert claims["cross_run_memory_effect_measured"] is False
    assert claims["accepted_d037_diagnostic"] is True
    assert claims["ready_for_v2_terra_pilot"] is True
    assert claims["mini_r6_substitutes_for_terra_pilot"] is False
    assert claims["development_campaign_unlocked"] is False


def test_mini_d037_r6_artifacts_are_hash_bound_when_available() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r6.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["portable_artifacts"]) == 2
    rejected_candidate = _artifact_for_role(
        payload,
        "controlled-rejected-model-candidate",
    )
    submitted_candidate = _artifact_for_role(payload, "submitted-model-candidate")
    _assert_artifact_identity(rejected_candidate)
    _assert_artifact_identity(submitted_candidate)
    assert rejected_candidate["sha256"] != submitted_candidate["sha256"]

    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local mini-r6 evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    for portable in (rejected_candidate, submitted_candidate):
        raw = next(
            artifact
            for artifact in artifacts
            if artifact["sha256"] == portable["sha256"]
        )
        assert Path(raw["path"]).read_bytes() == Path(portable["path"]).read_bytes()

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith(
            "/dev-validation-gpt54mini-d037-20260730-r6.jsonl"
        )
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"]).read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for expected_sequence, journal_row in enumerate(journal_rows, start=1):
        recorded_hash = journal_row.pop("event_hash")
        assert journal_row["sequence"] == expected_sequence
        assert journal_row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(journal_row)) == recorded_hash
        previous_hash = recorded_hash
    assert previous_hash == payload["campaign"]["journal"]["final_event_hash"]
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        Path(artifacts[0]["path"]).read_bytes()
    )

    plan_artifact = next(
        artifact for artifact in artifacts if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(Path(plan_artifact["path"]).read_text(encoding="utf-8"))
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )

    qualification = load_trace_qualification("run_73f5aaf7328a4ea5")
    assert qualification["qualification_hash"] == (
        payload["trace_qualification_artifact"]["qualification_hash"]
    )
    assert len(qualification["checks"]) == (
        payload["trace_qualification_artifact"]["check_count"]
    )
    assert sum(check["passed"] for check in qualification["checks"]) == (
        payload["trace_qualification_artifact"]["passed_check_count"]
    )
    retry = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    controlled = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "controlled_diagnostic_boundary"
    )
    assert retry["passed"] is True
    assert retry["details"]["retry_episode_count"] == 1
    assert retry["details"]["verified_retry_count"] == 1
    assert controlled["passed"] is True
    assert controlled["details"]["controlled_rejection_count"] == 1
    assert controlled["details"]["verified_controlled_rejection_count"] == 1
    assert controlled["details"]["controlled_patch_applied_sequences"] == []
    assert calculate_source_evidence_hash("run_73f5aaf7328a4ea5") == (
        payload["trace_qualification_artifact"]["source_evidence_hash"]
    )

    result_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/run_73f5aaf7328a4ea5/result.json")
    )
    result_payload = json.loads(Path(result_artifact["path"]).read_text(encoding="utf-8"))
    assert result_payload["official"] is True
    assert result_payload["scope_compliant_success"] is True
    assert result_payload["submitted_patch_artifact_id"] == (
        payload["trace_activity"]["submitted_patch_artifact_id"]
    )


def test_mini_d037_r6_checked_evidence_has_no_private_or_provider_payload() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r6.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {
        "schema_version",
        "recorded_at",
        "task_id",
        "harness_commit",
        "execution_hash",
        "retry_lineage",
        "campaign",
        "pilot",
        "trace_activity",
        "controlled_rejection_evidence",
        "prompt_token_integrity",
        "trace_qualification_artifact",
        "d037_retry_feature",
        "diagnostic_gate",
        "spend_to_date",
        "evidence_policy",
        "portable_artifacts",
        "raw_local_artifacts",
        "claims_boundary",
    }

    forbidden_keys = {
        "api_key",
        "authorization",
        "check_id",
        "verifier_results",
        "evidence_artifacts",
        "artifact_path",
        "headers",
        "input",
        "instructions",
        "output",
        "private_spec_hash",
        "hidden_artifacts",
        "request",
        "request_body",
        "response",
        "response_error",
        "response_id",
        "system_fingerprint",
        "text",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {nested for child in value.values() for nested in walk_keys(child)}
        if isinstance(value, list):
            return {nested for child in value for nested in walk_keys(child)}
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    assert payload["evidence_policy"]["raw_local_artifacts"].endswith(
        "not bundled in a clean checkout."
    )

    checked_text = path.read_text(encoding="utf-8")
    for artifact in payload["portable_artifacts"]:
        checked_text += Path(artifact["path"]).read_text(encoding="utf-8")
    package = load_task_package("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_primary_mini_campaign_preserves_source_failure_and_postmortem_separately() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r1.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v7"
    assert payload["execution_hash"] == (
        "sha256:969477ca029570ea61f9fca74fd3aa558f6e16ff9b5be1c7ffa8927ed1139047"
    )
    assert payload["harness_commit"] == (
        "844b1dbe359032c04b29f1e0dd15419486694400"
    )

    campaign = payload["campaign"]
    assert campaign["purpose"] == "development-validation-live-pilot"
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 1
    assert campaign["diagnostic_errors"] == 0
    assert campaign["not_started_runs"] == 0
    assert campaign["halt_reason"] == "QualificationFailureHalt"
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    source = payload["source_pilot"]
    assert source["run_id"] == "run_6993722014bf4e3b"
    assert source["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert source["max_output_tokens"] == 25_000
    assert source["max_total_tokens"] == 200_000
    assert source["max_model_calls"] == 20
    assert source["outcome_kind"] == "agent_failure"
    assert source["agent_submission_status"] == "failed"
    assert source["evaluation_status"] == "not_run"
    assert source["scope_compliant_success"] is False
    assert source["official"] is False
    assert set(source["verdicts"].values()) == {"not_run"}
    assert source["event_count"] == 143
    assert source["checkpoint_count"] == 31
    assert source["model_calls"] == source["input_token_count_calls"] == 20
    assert source["tool_calls"] == 30
    assert source["tool_failures"] == 0
    assert source["patch_prepared_events"] == source["patch_applied_events"] == 1
    assert source["submission_attempted_events"] == 0
    assert source["submission_accepted_events"] == 0
    assert source["terminal_error"] == {
        "type": "ModelGenerationBudgetError",
        "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "reason_code": "model_call_budget_exhausted",
        "generation_started": False,
    }

    usage = source["usage"]
    assert usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"]
    assert usage["total_tokens"] == 143_304
    assert usage["remaining_total_tokens"] == 56_696
    assert usage["reasoning_output_tokens"] <= usage["output_tokens"]
    assert usage["model_cost_usd"] == pytest.approx(0.1526205)

    activity = payload["source_trace_activity"]
    assert sum(activity["tool_breakdown"].values()) == source["tool_calls"]
    assert activity["registered_check_attempts"] == 1
    assert activity["registered_check_passes"] == 1
    assert activity["mutation_attempts"] == 1
    assert activity["submission_attempts"] == 0
    assert activity["finish_task_calls"] == 0
    assert activity["evaluator_runs"] == 0
    assert activity["terminal_phase"] == "REVIEW"
    assert activity["review_recorded"] is False
    assert activity["final_worktree_diff_hash"] == (
        "sha256:9ca2431c14ce0cd5fd49b19710498a7a55a33568c748d3e44fbe794a825e083d"
    )
    assert activity["changed_files"] == ["babel/numbers.py"]
    assert activity["added_lines"] == activity["deleted_lines"] == 1

    blocked = payload["model_generation_block"]
    assert blocked["event_sequence"] == 141
    assert blocked["reason_code"] == "model_call_budget_exhausted"
    assert blocked["generation_started"] is False
    assert blocked["input_token_count_calls"] == 0
    assert blocked["requested_input_tokens"] is None
    assert blocked["remaining_tokens"] is None
    assert blocked["retry_context_present"] is False
    assert blocked["retry_candidate_content_hash"] is None
    assert "not accepted" in blocked["qualification_interpretation"]

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["requested_input_tokens"] == (
        telemetry["provider_reported_input_tokens"]
    )
    assert sum(telemetry["requested_input_tokens"]) == usage["input_tokens"]
    assert telemetry["exact_input_count_matches"] == telemetry["model_call_count"] == 20
    assert telemetry["total_token_count_matches"] == 20
    assert telemetry["completed_generation_count"] == 20
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["truncation_mode"] == "disabled"
    assert telemetry["provider_prompt_cut_observed"] is False
    assert telemetry["previous_response_id_used_count"] == 0
    assert telemetry["store_true_count"] == 0
    assert telemetry["maximum_completed_output_tokens"] == 4_663

    qualification = payload["source_trace_qualification"]
    assert qualification["qualified"] is False
    assert qualification["trace_integrity_passed"] is False
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is False
    assert qualification["passed_check_count"] == 21
    assert qualification["check_count"] == 22
    assert qualification["failed_check_names"] == ["prompt_token_integrity"]
    assert qualification["failed_event_sequences"] == []
    assert qualification["terminal_generation_block_valid"] is False

    postmortem = payload["postmortem_evaluation"]
    assert postmortem["run_id"] == "run_1a742732dae842e3"
    assert postmortem["input_source_run_id"] == source["run_id"]
    assert postmortem["model_calls"] == 0
    assert postmortem["tool_calls"] == 0
    assert postmortem["model_cost_usd"] == 0.0
    assert postmortem["source_patch_identity_matches"] is True
    assert postmortem["normalized_diff_hash"] == (
        activity["final_worktree_diff_hash"]
    )
    assert postmortem["agent_submission_status"] == "completed"
    assert postmortem["evaluation_status"] == "completed"
    assert postmortem["scope_compliant_success"] is True
    assert postmortem["official"] is True
    assert set(postmortem["verdicts"].values()) == {"pass"}
    assert postmortem["proves_patch_evaluator_acceptance"] is True
    assert postmortem["count_as_source_run_success"] is False
    assert postmortem["count_as_campaign_pilot_success"] is False
    assert postmortem["count_as_pilot_repetition"] is False

    spend = payload["spend_to_date"]
    assert (
        spend["historical_mini_diagnostic_lane_cumulative_usd"]
        + spend["mini_campaign_r1_usd"]
    ) == pytest.approx(spend["mini_lane_cumulative_usd"])
    assert (
        spend["historical_terra_lane_cumulative_usd"]
        + spend["mini_lane_cumulative_usd"]
    ) == pytest.approx(spend["all_paid_pilot_list_price_total_usd"])
    assert spend["all_paid_pilot_list_price_total_usd"] == pytest.approx(
        1.602985125
    )
    assert spend["postmortem_evaluation_usd"] == 0.0
    assert spend["invoice_charge_verified"] is False

    claims = payload["claims_boundary"]
    assert claims["paid_provider_path_exercised"] is True
    assert claims["executed_request_token_counts_match"] is True
    assert claims["source_run_terminal_agent_failure"] is True
    assert claims["source_run_trace_qualified"] is False
    assert claims["source_run_evaluation_reached"] is False
    assert claims["source_run_task_success"] is False
    assert claims["source_run_final_patch_present"] is True
    assert claims["source_run_visible_check_passed"] is True
    assert claims["postmortem_used_model_calls"] is False
    assert claims["postmortem_patch_evaluator_acceptance"] is True
    assert claims["postmortem_counts_as_source_run_success"] is False
    assert claims["postmortem_counts_as_pilot_repetition"] is False
    assert claims["accepted_current_live_pilot"] is False
    assert claims["development_campaign_unlocked"] is False


def test_primary_mini_campaign_artifacts_are_hash_bound_when_available() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r1.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["portable_artifacts"]) == 1
    portable = _artifact_for_role(payload, "unsubmitted-final-model-candidate")
    _assert_artifact_identity(portable)

    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local primary mini campaign evidence is not bundled")

    missing = [artifact["path"] for artifact in artifacts if not Path(artifact["path"]).is_file()]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    raw_final_patch = next(
        artifact
        for artifact in artifacts
        if artifact["sha256"] == portable["sha256"]
    )
    assert Path(raw_final_patch["path"]).read_bytes() == Path(
        portable["path"]
    ).read_bytes()

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith(
            "/dev-validation-gpt54mini-campaign-20260730-r1.jsonl"
        )
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"]).read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for expected_sequence, journal_row in enumerate(journal_rows, start=1):
        recorded_hash = journal_row.pop("event_hash")
        assert journal_row["sequence"] == expected_sequence
        assert journal_row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(journal_row)) == recorded_hash
        previous_hash = recorded_hash
    assert previous_hash == payload["campaign"]["journal"]["final_event_hash"]
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        Path(artifacts[0]["path"]).read_bytes()
    )

    plan_artifact = next(
        artifact for artifact in artifacts if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(Path(plan_artifact["path"]).read_text(encoding="utf-8"))
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )

    qualification = load_trace_qualification("run_6993722014bf4e3b")
    assert qualification["qualification_hash"] == (
        payload["source_trace_qualification"]["qualification_hash"]
    )
    assert len(qualification["checks"]) == (
        payload["source_trace_qualification"]["check_count"]
    )
    failed_checks = [
        check["check_id"] for check in qualification["checks"] if not check["passed"]
    ]
    assert failed_checks == ["prompt_token_integrity"]
    prompt_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "prompt_token_integrity"
    )
    assert prompt_check["details"]["failed_event_sequences"] == []
    assert prompt_check["details"]["terminal_generation_block_valid"] is False
    assert calculate_source_evidence_hash("run_6993722014bf4e3b") == (
        payload["source_trace_qualification"]["source_evidence_hash"]
    )

    source_result_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/run_6993722014bf4e3b/result.json")
    )
    source_result = json.loads(
        Path(source_result_artifact["path"]).read_text(encoding="utf-8")
    )
    assert source_result["outcome_kind"] == "agent_failure"
    assert source_result["evaluation_status"] == "not_run"
    assert source_result["submitted_patch_artifact_id"] is None

    postmortem_result_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/run_1a742732dae842e3/result.json")
    )
    postmortem_result = json.loads(
        Path(postmortem_result_artifact["path"]).read_text(encoding="utf-8")
    )
    assert postmortem_result["official"] is True
    assert postmortem_result["scope_compliant_success"] is True
    assert postmortem_result["usage"]["model_calls"] == 0
    assert postmortem_result["usage"]["tool_calls"] == 0

    postmortem_provenance_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/run_1a742732dae842e3/provenance.json")
    )
    postmortem_provenance = json.loads(
        Path(postmortem_provenance_artifact["path"]).read_text(encoding="utf-8")
    )
    assert postmortem_provenance["patch_hash"] == (
        payload["source_trace_activity"]["applied_model_argument_hash"]
    )
    assert postmortem_provenance["diff_hash"] == (
        payload["source_trace_activity"]["final_worktree_diff_hash"]
    )


def test_primary_mini_campaign_evidence_has_no_private_or_provider_payload() -> None:
    path = Path("reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r1.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {
        "schema_version",
        "recorded_at",
        "task_id",
        "harness_commit",
        "execution_hash",
        "campaign",
        "source_pilot",
        "source_trace_activity",
        "model_generation_block",
        "prompt_token_integrity",
        "source_trace_qualification",
        "postmortem_evaluation",
        "spend_to_date",
        "evidence_policy",
        "portable_artifacts",
        "raw_local_artifacts",
        "claims_boundary",
    }

    forbidden_keys = {
        "api_key",
        "authorization",
        "check_id",
        "verifier_results",
        "evidence_artifacts",
        "artifact_path",
        "headers",
        "input",
        "instructions",
        "output",
        "private_spec_hash",
        "hidden_artifacts",
        "request",
        "request_body",
        "response",
        "response_error",
        "response_id",
        "system_fingerprint",
        "text",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {nested for child in value.values() for nested in walk_keys(child)}
        if isinstance(value, list):
            return {nested for child in value for nested in walk_keys(child)}
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    assert payload["evidence_policy"]["raw_local_artifacts"].endswith(
        "not bundled in a clean checkout."
    )
    assert "cannot replace" in payload["evidence_policy"]["postmortem_boundary"]

    checked_text = path.read_text(encoding="utf-8")
    for artifact in payload["portable_artifacts"]:
        checked_text += Path(artifact["path"]).read_text(encoding="utf-8")
    package = load_task_package("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []
