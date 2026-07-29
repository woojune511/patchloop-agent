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
