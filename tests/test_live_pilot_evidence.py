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


def test_corrective_primary_r2_is_current_trace_qualified_success() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-campaign-20260730-r2.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v8"
    assert payload["execution_hash"] == (
        "sha256:eb13280308f3f2642504da8493982543bb466d9bafaa5031b727dd4503003411"
    )
    assert payload["harness_commit"] == (
        "624b1d0861f9907af0ca47d8fc25795d4923ca6d"
    )

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 0
    assert campaign["not_started_runs"] == 0
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    pilot = payload["pilot"]
    assert pilot["run_id"] == "run_afd5080a77a34995"
    assert pilot["max_model_calls"] == 21
    assert pilot["outcome_kind"] == "resolved"
    assert pilot["agent_submission_status"] == "completed"
    assert pilot["evaluation_status"] == "completed"
    assert pilot["scope_compliant_success"] is True
    assert pilot["official"] is True
    assert set(pilot["verdicts"].values()) == {"pass"}
    assert pilot["usage"]["total_tokens"] == (
        pilot["usage"]["input_tokens"] + pilot["usage"]["output_tokens"]
    )
    assert pilot["usage"]["model_cost_usd"] == pytest.approx(0.04973175)

    trace = payload["trace_activity"]
    assert sum(trace["tool_breakdown"].values()) == pilot["tool_calls"] == 8
    assert trace["tool_breakdown"]["finish_task"] == 1
    assert trace["raw_model_patch_sha256"] != (
        trace["final_worktree_diff_sha256"]
    )

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["requested_input_tokens"] == (
        telemetry["provider_reported_input_tokens"]
    )
    assert telemetry["exact_input_count_matches"] == (
        telemetry["model_call_count"]
    ) == 7
    assert telemetry["completed_generation_count"] == 7
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["truncation_mode"] == "disabled"
    assert telemetry["provider_prompt_cut_observed"] is False

    qualification = payload["trace_qualification"]
    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is True
    assert qualification["passed_check_count"] == qualification["check_count"] == 23

    claims = payload["claims_boundary"]
    assert claims["accepted_current_live_pilot"] is True
    assert claims["development_campaign_pilot_gate_passed"] is True
    assert claims["rejected_patch_recovery_observed"] is False
    assert claims["cross_run_memory_effect_measured"] is False
    assert payload["spend_to_date"]["all_paid_pilot_list_price_total_usd"] == (
        pytest.approx(1.652716875)
    )


def test_corrective_primary_r2_artifacts_and_journal_are_hash_bound() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-campaign-20260730-r2.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    submitted = _artifact_for_role(payload, "final-submitted-git-diff")
    _assert_artifact_identity(submitted)
    assert submitted["sha256"] == payload["submitted_patch"]["patch_sha256"]

    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local corrective-primary-r2 evidence is not bundled")

    missing = [
        artifact["path"]
        for artifact in artifacts
        if not Path(artifact["path"]).is_file()
    ]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    raw_submitted = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/submitted.patch")
    )
    assert Path(submitted["path"]).read_bytes() == Path(
        raw_submitted["path"]
    ).read_bytes()

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith(
            "/dev-validation-gpt54mini-campaign-20260730-r2.jsonl"
        )
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"])
        .read_text(encoding="utf-8")
        .splitlines()
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
        artifact
        for artifact in artifacts
        if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(
        Path(plan_artifact["path"]).read_text(encoding="utf-8")
    )
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )

    qualification = load_trace_qualification("run_afd5080a77a34995")
    assert qualification["qualification_hash"] == (
        payload["trace_qualification"]["qualification_hash"]
    )
    assert calculate_source_evidence_hash("run_afd5080a77a34995") == (
        payload["trace_qualification"]["source_evidence_hash"]
    )


def test_corrective_primary_r2_evidence_has_no_private_or_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-campaign-20260730-r2.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    checked_text += Path(payload["portable_artifacts"][0]["path"]).read_text(
        encoding="utf-8"
    )
    package = load_task_package(
        "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes"
    )
    private_tokens = _private_leak_tokens(package, api_key=None)
    assert sorted(token for token in private_tokens if token in checked_text) == []


def test_investigation_v4_pilot_passes_only_the_next_preflight_gate() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-investigation-v4-20260730-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "live-pilot-evidence-v9"
    assert payload["execution_hash"] == (
        "sha256:cc2117dc698cdc991ccbcad45bbcfa4302f1ac265bdfdcc0753b60b2fda6eba2"
    )
    assert payload["harness_commit"] == (
        "5045e398646ec73d615785aeb95f02e877c34c90"
    )

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 1
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 0
    assert campaign["diagnostic_errors"] == 0
    assert campaign["not_started_runs"] == 0
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True
    assert campaign["execution_plan"]["invocation_live_cost_approved"] is True
    assert campaign["execution_plan"]["approved_execution_hash_matches"] is True
    assert campaign["execution_plan"]["ready"] is True

    pilot = payload["pilot"]
    assert pilot["run_id"] == "run_d7207fbb06184dd3"
    assert pilot["context_policy_version"] == "phase-evidence-v4"
    assert pilot["memory_condition"] == "no_memory"
    assert pilot["outcome_kind"] == "resolved"
    assert pilot["agent_submission_status"] == "completed"
    assert pilot["evaluation_status"] == "completed"
    assert pilot["scope_compliant_success"] is True
    assert pilot["official"] is True
    assert set(pilot["verdicts"].values()) == {"pass"}
    assert pilot["usage"]["total_tokens"] == (
        pilot["usage"]["input_tokens"] + pilot["usage"]["output_tokens"]
    )
    assert pilot["usage"]["model_cost_usd"] == pytest.approx(0.08807325)

    trace = payload["trace_activity"]
    assert sum(trace["tool_breakdown"].values()) == pilot["tool_calls"] == 10
    assert trace["tool_breakdown"]["apply_patch"] == 2
    assert trace["rejected_mutation_attempts"] == 1
    assert trace["successful_mutation_attempts"] == 1
    assert trace["successful_raw_model_patch_sha256"] != (
        trace["final_worktree_diff_sha256"]
    )

    retry = payload["natural_rejected_patch_retry"]
    assert retry["observed"] is True
    assert retry["controlled_fault"] is False
    assert retry["rejected_candidate_count"] == 1
    assert retry["retry_episode_count"] == 1
    assert retry["verified_retry_count"] == 1
    assert retry["verified_retry_ratio"] == "1/1"
    assert retry["failed_source_failure_sequences"] == []
    assert retry["rejected_action_patch_applied_count"] == 0

    continuity = payload["investigation_continuity"]
    assert continuity["investigation_evidence_check_passed"] is True
    assert continuity["verified_context_count"] == continuity["context_count"] == 10
    assert continuity["failed_context_sequences"] == []
    assert continuity["investigation_lifecycle_check_passed"] is True
    assert continuity["semantic_replay_count"] == 0
    assert continuity["admission_block_count"] == 0
    assert continuity["semantic_replay_branch_observed"] is False
    assert continuity["tail_admission_branch_observed"] is False

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["requested_input_tokens"] == (
        telemetry["provider_reported_input_tokens"]
    )
    assert telemetry["exact_input_count_matches"] == (
        telemetry["model_call_count"]
    ) == 10
    assert telemetry["completed_generation_count"] == 10
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["model_generation_blocked_count"] == 0
    assert telemetry["truncation_mode"] == "disabled"
    assert telemetry["provider_prompt_cut_observed"] is False
    assert telemetry["truncated_tool_result_count"] == 0
    assert telemetry["maximum_context_policy_omitted_event_count"] == 24

    qualification = payload["trace_qualification"]
    assert qualification["schema_version"] == "trace-qualification-v2"
    assert qualification["context_policy_version"] == "phase-evidence-v4"
    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is True
    assert qualification["passed_check_count"] == qualification["check_count"] == 25
    assert qualification["memory_candidate_eligible"] is False

    gate = payload["gate_boundary"]
    assert gate["phase_evidence_v4_pilot_gate_passed"] is True
    assert gate["pilot_run_id_to_bind"] == pilot["run_id"]
    assert gate["next_paid_execution_authorized"] is False
    assert gate["fresh_execution_hash_required"] is True
    assert gate["separate_cost_approval_required"] is True
    assert gate["v4_no_memory_12_run_campaign_executed"] is False
    assert gate["core_campaign_executed"] is False

    claims = payload["claims_boundary"]
    assert claims["accepted_current_v4_live_pilot"] is True
    assert claims["phase_evidence_v4_pilot_gate_passed"] is True
    assert claims["natural_rejected_patch_recovery_observed"] is True
    assert claims["semantic_investigation_replay_observed"] is False
    assert claims["tail_admission_block_observed"] is False
    assert claims["v4_no_memory_12_run_campaign_executed"] is False
    assert claims["cross_run_memory_effect_measured"] is False
    assert claims["core_campaign_executed"] is False
    assert claims["next_paid_campaign_authorized"] is False
    assert payload["spend_to_date"]["all_paid_attempts_list_price_total_usd"] == (
        pytest.approx(3.133982625)
    )


def test_investigation_v4_pilot_artifacts_and_journal_are_hash_bound() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-investigation-v4-20260730-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    submitted = _artifact_for_role(payload, "final-submitted-git-diff")
    _assert_artifact_identity(submitted)
    assert submitted["sha256"] == payload["submitted_patch"]["patch_sha256"]

    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local investigation-v4 evidence is not bundled")

    missing = [
        artifact["path"]
        for artifact in artifacts
        if not Path(artifact["path"]).is_file()
    ]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    raw_submitted = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/submitted.patch")
    )
    assert Path(submitted["path"]).read_bytes() == Path(
        raw_submitted["path"]
    ).read_bytes()

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith(
            "/dev-validation-gpt54mini-investigation-v4-20260730-r1.jsonl"
        )
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"])
        .read_text(encoding="utf-8")
        .splitlines()
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
        artifact
        for artifact in artifacts
        if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(
        Path(plan_artifact["path"]).read_text(encoding="utf-8")
    )
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )
    assert plan_payload["approval"]["invocation_approve_live_cost"] is True
    assert plan_payload["approval"]["matches_execution_hash"] is True
    assert plan_payload["ready"] is True

    qualification = load_trace_qualification("run_d7207fbb06184dd3")
    assert qualification["qualification_hash"] == (
        payload["trace_qualification"]["qualification_hash"]
    )
    assert calculate_source_evidence_hash("run_d7207fbb06184dd3") == (
        payload["trace_qualification"]["source_evidence_hash"]
    )


def test_investigation_v4_evidence_has_no_private_or_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-investigation-v4-20260730-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    assert {
        artifact["role"]
        for artifact in payload["portable_artifacts"]
    } == {"final-submitted-git-diff"}

    checked_text = path.read_text(encoding="utf-8")
    for artifact in payload["portable_artifacts"]:
        checked_text += Path(artifact["path"]).read_text(encoding="utf-8")
    forbidden_payload_markers = {
        '"authorization"',
        '"request_body"',
        '"response_id"',
        "OPENAI_API_KEY",
        "Bearer ",
    }
    assert all(marker not in checked_text for marker in forbidden_payload_markers)

    package = load_task_package(
        "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes"
    )
    private_tokens = _private_leak_tokens(package, api_key=None)
    assert sorted(token for token in private_tokens if token in checked_text) == []


def test_no_memory_campaign_preserves_execution_failure_boundary() -> None:
    path = Path(
        "reports/memory-development/dev-no-memory-20260728.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "memory-development-campaign-evidence-v1"
    )
    assert payload["execution_hash"] == (
        "sha256:48c12899dcb4bacc13b582720df33ff402be38e5b601e130baab397b9dbe7809"
    )
    assert payload["pilot_gate"]["run_id"] == "run_afd5080a77a34995"
    assert payload["pilot_gate"]["qualified"] is True

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 12
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 0
    assert campaign["not_started_runs"] == 0
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    outcome = payload["aggregate_outcome"]
    assert outcome["terminal_attempts"] == 12
    assert outcome["resolved_runs"] == 0
    assert outcome["agent_failure_runs"] == 12
    assert outcome["evaluation_reached_runs"] == 0
    assert outcome["trace_qualified_runs"] == 12
    assert outcome["memory_candidate_eligible_runs"] == 12
    assert outcome["human_reviewed_runs"] == 0
    assert outcome["model_call_budget_exhaustions"] == 6
    assert outcome["tool_call_budget_exhaustions"] == 6
    assert outcome["terminal_phase_reproduce_runs"] == 12

    usage = payload["aggregate_usage"]
    assert usage["input_tokens"] == 1_544_366
    assert usage["output_tokens"] == 52_204
    assert usage["total_tokens"] == (
        usage["input_tokens"] + usage["output_tokens"]
    )
    assert usage["model_calls"] == 231
    assert usage["tool_calls"] == 563
    assert usage["model_cost_usd"] == pytest.approx(1.3931925)

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["exact_input_count_matches"] == (
        telemetry["model_call_count"]
    ) == 231
    assert telemetry["completed_generation_count"] == 231
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["truncation_disabled_count"] == 231
    assert telemetry["provider_prompt_cut_observed"] is False

    runs = payload["runs"]
    assert len(runs) == 12
    assert [run["order"] for run in runs] == list(range(1, 13))
    assert len({run["run_id"] for run in runs}) == 12
    assert len(
        {
            (run["task_id"], run["repetition"])
            for run in runs
        }
    ) == 12
    assert {run["outcome_kind"] for run in runs} == {"agent_failure"}
    assert {run["evaluation_reached"] for run in runs} == {False}
    assert {run["qualified"] for run in runs} == {True}
    assert {run["memory_candidate_eligible"] for run in runs} == {True}
    assert {run["review_status"] for run in runs} == {"unreviewed"}
    assert sum(run["input_tokens"] for run in runs) == usage["input_tokens"]
    assert sum(run["output_tokens"] for run in runs) == usage["output_tokens"]
    assert sum(run["model_calls"] for run in runs) == usage["model_calls"]
    assert sum(run["tool_calls"] for run in runs) == usage["tool_calls"]
    assert sum(run["model_cost_usd"] for run in runs) == pytest.approx(
        usage["model_cost_usd"]
    )

    review = payload["review_admission"]
    assert review["machine_candidate_eligible_runs"] == 12
    assert review["reviewed_runs"] == 0
    assert review["automatically_admitted_to_memory_index"] == 0
    claims = payload["claims_boundary"]
    assert claims["campaign_execution_completed"] is True
    assert claims["task_success_observed"] is False
    assert claims["valid_no_memory_performance_baseline"] is False
    assert claims["cross_run_memory_effect_measured"] is False


def test_no_memory_campaign_raw_evidence_is_hash_bound_when_available() -> None:
    path = Path(
        "reports/memory-development/dev-no-memory-20260728.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local no-memory campaign evidence is not bundled")

    missing = [
        artifact["path"]
        for artifact in artifacts
        if not Path(artifact["path"]).is_file()
    ]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith("/dev-no-memory-20260728.jsonl")
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"])
        .read_text(encoding="utf-8")
        .splitlines()
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
        artifact
        for artifact in artifacts
        if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(
        Path(plan_artifact["path"]).read_text(encoding="utf-8")
    )
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )
    assert plan_payload["pilot_qualification"]["run_id"] == (
        payload["pilot_gate"]["run_id"]
    )
    assert plan_payload["pilot_qualification"]["qualification_hash"] == (
        payload["pilot_gate"]["qualification_hash"]
    )

    qualification_artifacts = {
        Path(artifact["path"]).stem: artifact
        for artifact in artifacts
        if "/qualifications/" in artifact["path"]
    }
    assert len(qualification_artifacts) == 12
    for run in payload["runs"]:
        qualification = json.loads(
            Path(qualification_artifacts[run["run_id"]]["path"]).read_text(
                encoding="utf-8"
            )
        )
        assert qualification["run_id"] == run["run_id"]
        assert qualification["qualification_hash"] == run["qualification_hash"]
        assert qualification["qualified"] is True
        assert qualification["evaluation_reached"] is False
        assert qualification["memory_candidate_eligible"] is True


def test_no_memory_campaign_evidence_has_no_private_or_provider_payload() -> None:
    path = Path(
        "reports/memory-development/dev-no-memory-20260728.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    for task_id in {
        run["task_id"]
        for run in payload["runs"]
    }:
        package = load_task_package(f"tasks/dev-train/{task_id}")
        private_tokens = _private_leak_tokens(package, api_key=None)
        leaked = sorted(
            token for token in private_tokens if token in checked_text
        )
        assert leaked == []


def test_v4_no_memory_campaign_preserves_mixed_failure_boundary() -> None:
    path = Path(
        "reports/memory-development/dev-no-memory-v4-20260730-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "memory-development-campaign-evidence-v2"
    )
    assert payload["execution_hash"] == (
        "sha256:9befd0bf8b2eb7dbc25999786713581b4b6c95f2ad45df56e2f098a9252e5bac"
    )
    assert payload["harness_commit"] == (
        "5045e398646ec73d615785aeb95f02e877c34c90"
    )
    assert payload["pilot_gate"]["run_id"] == "run_d7207fbb06184dd3"
    assert payload["pilot_gate"]["qualified"] is True
    assert payload["harness_execution"] == {
        "strategy": "exact-pilot-commit-detached-worktree-v1",
        "detached_worktree_clean": True,
        "imported_source_from_detached_worktree": True,
        "shared_host_runtime_root": True,
        "append_only_evidence_preserved": True,
        "suite_file_sha256": (
            "sha256:301f4248c764bb556308732eb2274087462915b201d72601035fe5fddded2a83"
        ),
        "template_semantic_difference": "pilot_run_id binding only",
    }

    campaign = payload["campaign"]
    assert campaign["expected_runs"] == campaign["completed_runs"] == 12
    assert campaign["infrastructure_errors"] == 0
    assert campaign["qualification_errors"] == 0
    assert campaign["diagnostic_errors"] == 0
    assert campaign["not_started_runs"] == 0
    assert campaign["halt_reason"] is None
    assert campaign["journal"]["event_count"] == 26
    assert campaign["journal"]["hash_chain_valid"] is True
    assert campaign["journal"]["result_exact_bytes_match"] is True

    outcome = payload["aggregate_outcome"]
    assert outcome["terminal_attempts"] == 12
    assert outcome["resolved_runs"] == 0
    assert outcome["agent_failure_runs"] == 9
    assert outcome["task_failure_runs"] == 3
    assert outcome["evaluation_reached_runs"] == 3
    assert outcome["official_scope_compliant_successes"] == 0
    assert outcome["hidden_failure_runs"] == 3
    assert outcome["evaluated_regression_pass_runs"] == 3
    assert outcome["evaluated_scope_pass_runs"] == 3
    assert outcome["evaluated_safety_pass_runs"] == 3
    assert outcome["trace_qualified_runs"] == 12
    assert outcome["leakage_scan_passed_runs"] == 12
    assert outcome["memory_candidate_eligible_runs"] == 12
    assert outcome["exact_request_budget_exhaustions"] == 9

    usage = payload["aggregate_usage"]
    assert usage["input_tokens"] == 1_753_493
    assert usage["output_tokens"] == 118_321
    assert usage["total_tokens"] == (
        usage["input_tokens"] + usage["output_tokens"]
    )
    assert usage["reasoning_output_tokens"] == 102_617
    assert usage["model_calls"] == 144
    assert usage["input_token_count_calls"] == 153
    assert usage["tool_calls"] == 262
    assert usage["model_cost_usd"] == pytest.approx(1.84756425)

    trace = payload["aggregate_trace_activity"]
    assert sum(trace["tool_breakdown"].values()) == usage["tool_calls"]
    assert trace["event_count"] == 1_215
    assert trace["checkpoint_count"] == 274
    assert trace["patch_prepared_events"] == 6
    assert trace["patch_applied_events"] == 5
    assert trace["submission_accepted_events"] == 3
    assert trace["evaluator_runs"] == 3

    continuity = payload["investigation_continuity"]
    assert continuity["qualified_runs"] == 12
    assert continuity["semantic_replay_events"] == 26
    assert continuity["runs_with_semantic_replay"] == 10
    assert continuity["tail_admission_block_events"] == 0
    assert continuity["tail_exploration_closed_contexts"] == 1
    assert continuity["budget_blocks_before_tail_close"] == 8
    assert continuity["budget_blocks_after_tail_close"] == 1
    assert continuity["rejected_candidate_count"] == 11
    assert continuity["verified_retry_count"] == 11
    assert continuity["failed_retry_source_sequences"] == 0

    telemetry = payload["prompt_token_integrity"]
    assert telemetry["model_call_count"] == 144
    assert telemetry["input_token_count_call_count"] == 153
    assert telemetry["exact_input_count_matches"] == 144
    assert telemetry["total_token_count_matches"] == 144
    assert telemetry["completed_generation_count"] == 144
    assert telemetry["incomplete_generation_count"] == 0
    assert telemetry["model_generation_blocked_count"] == 9
    assert telemetry["truncation_disabled_count"] == 144
    assert telemetry["provider_prompt_cut_observed"] is False
    assert telemetry["previous_response_id_used_count"] == 0
    assert telemetry["store_true_count"] == 0

    runs = payload["runs"]
    assert len(runs) == 12
    assert [run["order"] for run in runs] == list(range(1, 13))
    assert len({run["run_id"] for run in runs}) == 12
    assert len(
        {
            (run["task_id"], run["repetition"])
            for run in runs
        }
    ) == 12
    assert sum(
        run["outcome_kind"] == "agent_failure"
        for run in runs
    ) == 9
    assert sum(
        run["outcome_kind"] == "task_failure"
        for run in runs
    ) == 3
    assert sum(run["evaluation_reached"] for run in runs) == 3
    assert all(run["qualified"] for run in runs)
    assert all(run["memory_candidate_eligible"] for run in runs)
    assert {run["review_status"] for run in runs} == {"unreviewed"}
    assert sum(run["input_tokens"] for run in runs) == usage["input_tokens"]
    assert sum(run["output_tokens"] for run in runs) == usage["output_tokens"]
    assert sum(run["model_calls"] for run in runs) == usage["model_calls"]
    assert sum(run["tool_calls"] for run in runs) == usage["tool_calls"]
    assert sum(run["model_cost_usd"] for run in runs) == pytest.approx(
        usage["model_cost_usd"]
    )

    claims = payload["claims_boundary"]
    assert claims["campaign_execution_completed"] is True
    assert claims["task_success_observed"] is False
    assert claims["valid_no_memory_performance_baseline"] is False
    assert claims["task_failure_candidates_provisionally_admissible"] is True
    assert claims["budget_confounded_runs_admitted"] is False
    assert claims["failure_rules_reviewed"] is False
    assert claims["memory_index_built_from_this_campaign"] is False
    assert claims["cross_run_memory_effect_measured"] is False


def test_v4_no_memory_campaign_artifacts_are_hash_bound_when_available() -> None:
    path = Path(
        "reports/memory-development/dev-no-memory-v4-20260730-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["portable_artifacts"]) == 3
    for artifact in payload["portable_artifacts"]:
        assert artifact["role"] == "submitted-task-failure-diff"
        _assert_artifact_identity(artifact)

    artifacts = payload["raw_local_artifacts"]
    anchor = Path(artifacts[0]["path"])
    if not anchor.is_file():
        pytest.skip("raw local v4 campaign evidence is not bundled")

    missing = [
        artifact["path"]
        for artifact in artifacts
        if not Path(artifact["path"]).is_file()
    ]
    assert not missing
    for artifact in artifacts:
        _assert_artifact_identity(artifact)

    journal_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["path"].endswith(
            "/dev-no-memory-v4-20260730-r1.jsonl"
        )
    )
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    previous_hash = None
    for expected_sequence, journal_row in enumerate(
        journal_rows,
        start=1,
    ):
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
        artifact
        for artifact in artifacts
        if "/experiments/plans/" in artifact["path"]
    )
    plan_payload = json.loads(
        Path(plan_artifact["path"]).read_text(encoding="utf-8")
    )
    assert sha256_text(canonical_json(plan_payload)) == (
        payload["campaign"]["execution_plan"]["canonical_content_hash"]
    )
    assert plan_payload["approval"]["invocation_approve_live_cost"] is True
    assert plan_payload["approval"]["matches_execution_hash"] is True
    assert plan_payload["ready"] is True

    qualification_artifacts = {
        Path(artifact["path"]).stem: artifact
        for artifact in artifacts
        if "/qualifications/" in artifact["path"]
    }
    assert len(qualification_artifacts) == 12
    for run in payload["runs"]:
        qualification = json.loads(
            Path(
                qualification_artifacts[run["run_id"]]["path"]
            ).read_text(encoding="utf-8")
        )
        assert qualification["run_id"] == run["run_id"]
        assert qualification["qualification_hash"] == (
            run["qualification_hash"]
        )
        assert qualification["source_evidence_hash"] == (
            run["source_evidence_hash"]
        )
        assert qualification["qualified"] is True
        assert qualification["evaluation_reached"] == (
            run["evaluation_reached"]
        )
        assert qualification["memory_candidate_eligible"] is True

    for portable in payload["portable_artifacts"]:
        raw = next(
            artifact
            for artifact in artifacts
            if artifact["path"].endswith(
                f"/{portable['run_id']}/submitted.patch"
            )
        )
        assert Path(portable["path"]).read_bytes() == Path(
            raw["path"]
        ).read_bytes()


def test_v4_no_memory_campaign_has_no_private_or_provider_payload() -> None:
    path = Path(
        "reports/memory-development/dev-no-memory-v4-20260730-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    for artifact in payload["portable_artifacts"]:
        checked_text += Path(artifact["path"]).read_text(
            encoding="utf-8"
        )
    assert "OPENAI_API_KEY" not in checked_text
    assert "Bearer " not in checked_text
    for task_id in {
        run["task_id"]
        for run in payload["runs"]
    }:
        package = load_task_package(f"tasks/dev-train/{task_id}")
        private_tokens = _private_leak_tokens(package, api_key=None)
        leaked = sorted(
            token for token in private_tokens if token in checked_text
        )
        assert leaked == []


def test_d055_completion_panel_report_preserves_gate_and_usage_evidence() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-completion-v6-20260731-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "completion-panel-evidence-v1"
    assert payload["harness_commit"] == (
        "59621ecfa8538ecf693d3d5075ae84937b7a777d"
    )
    assert payload["execution_hash"] == (
        "sha256:444cd7f2d00b3925a1227d1e9fc0436c68ba9700005b8416572c5fd654de1f78"
    )
    assert payload["result_hash"] == (
        "sha256:a540ff52f271cd22c58ca561e559d9608ac50b99889a523f8a9a3d80cf8822ba"
    )
    gate = payload["completion_gate"]
    assert gate["passed"] is True
    assert gate["terminal_runs"] == gate["qualified_runs"] == 2
    assert gate["evaluator_reached_runs"] == gate["official_evaluator_runs"] == 2
    assert gate["task_successes"] == 2
    assert gate["infrastructure_errors"] == 0
    assert gate["qualification_errors"] == 0
    assert gate["diagnostic_errors"] == 0
    assert gate["budget_terminal_runs"] == 0
    assert gate["panel_headroom"]["passed"] is True
    assert (
        gate["panel_headroom"]["sufficient_to_freeze_comparison_budget"]
        is False
    )

    runs = payload["runs"]
    assert {run["task_id"] for run in runs} == {
        "babel-strict-grouped-decimal-trailing-zeroes",
        "moto-query-scanned-count",
    }
    assert {run["run_id"] for run in runs} == {
        "run_685c492e34f84fef",
        "run_0814be408332479e",
    }
    assert all(run["outcome_kind"] == "resolved" for run in runs)
    assert all(run["official"] is True for run in runs)
    assert all(run["scope_compliant_success"] is True for run in runs)
    assert all(set(run["verdicts"].values()) == {"pass"} for run in runs)
    assert all(
        run["qualification"]["passed_checks"]
        == run["qualification"]["total_checks"]
        == 25
        for run in runs
    )
    assert all(
        run["qualification"]["memory_candidate_eligible"] is False
        for run in runs
    )
    assert all(
        run["lifecycle"]["patch_prepared"]
        == run["lifecycle"]["patch_applied"]
        == run["lifecycle"]["submission_attempted"]
        == run["lifecycle"]["submission_accepted"]
        == 1
        for run in runs
    )
    assert all(
        run["lifecycle"]["duplicate_mutation_observed"] is False
        for run in runs
    )

    totals = payload["totals"]
    assert totals["input_tokens"] == sum(
        run["usage"]["input_tokens"] for run in runs
    )
    assert totals["output_tokens"] == sum(
        run["usage"]["output_tokens"] for run in runs
    )
    assert totals["reasoning_output_tokens"] == sum(
        run["usage"]["reasoning_output_tokens"] for run in runs
    )
    assert totals["model_calls"] == sum(
        run["usage"]["model_calls"] for run in runs
    )
    assert totals["input_token_count_calls"] == totals["model_calls"] == 19
    assert totals["tool_calls"] == sum(
        run["usage"]["tool_calls"] for run in runs
    )
    assert totals["model_cost_usd"] == pytest.approx(0.15682575)
    assert all(
        run["telemetry"]["input_count_matches"]
        == run["telemetry"]["total_count_matches"]
        == run["telemetry"]["completed_responses"]
        == run["usage"]["model_calls"]
        for run in runs
    )
    assert all(
        run["telemetry"]["incomplete_responses"] == 0
        for run in runs
    )
    assert payload["branch_activity"] == {
        "token_tail_admission_blocks": 0,
        "semantic_replays": 0,
    }
    assert "source_artifacts" not in payload
    assert len(payload["raw_local_artifacts"]) == 5
    assert all(
        artifact["bytes"] > 0
        and artifact["path"].startswith(".patchloop/")
        and artifact["sha256"].startswith("sha256:")
        for artifact in payload["raw_local_artifacts"]
    )
    for artifact in payload["raw_local_artifacts"]:
        if Path(artifact["path"]).exists():
            _assert_artifact_identity(artifact)
    portable_by_role = {
        artifact["role"]: artifact
        for artifact in payload["portable_artifacts"]
    }
    assert set(portable_by_role) == {
        "final-submitted-git-diff-babel",
        "final-submitted-git-diff-moto",
    }
    for artifact in portable_by_role.values():
        _assert_artifact_identity(artifact)
    assert {
        run["submitted_patch_sha256"] for run in runs
    } == {
        artifact["sha256"] for artifact in portable_by_role.values()
    }


def test_d055_completion_panel_report_excludes_private_and_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-validation-gpt54mini-completion-v6-20260731-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8") + "".join(
        Path(artifact["path"]).read_text(encoding="utf-8")
        for artifact in payload["portable_artifacts"]
    )
    assert "OPENAI_API_KEY" not in checked_text
    assert "Bearer " not in checked_text
    for task_id in {
        "babel-strict-grouped-decimal-trailing-zeroes",
        "moto-query-scanned-count",
    }:
        package = load_task_package(f"tasks/dev-validation/{task_id}")
        private_tokens = _private_leak_tokens(package, api_key=None)
        leaked = sorted(
            token for token in private_tokens if token in checked_text
        )
        assert leaked == []


def test_d064_saturation_report_preserves_split_gate_and_usage_evidence() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-saturation-v8-pilot-20260801-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "saturation-pilot-evidence-v1"
    assert payload["harness_commit"] == (
        "c542142c4e4530bd7e9dca28a5efc2cebc11a7f9"
    )
    assert payload["execution_hash"] == (
        "sha256:dcade27f9f89efd6c349db58cbe732c0c81f1bbaf3bbb05e6c14b4ca62f2b85c"
    )
    assert payload["result_hash"] == (
        "sha256:7f9568274488d0b8ddd5b0b7269e6e177df9939260a3872d4006873a951849ac"
    )
    assert payload["journal_final_event_hash"] == (
        "sha256:a9dd243b67fcf92af8ace1f95b188aedc58df6a89e9bf448c1769c010f4aea26"
    )

    gate = payload["completion_gate"]
    assert gate["passed"] is False
    assert gate["terminal_runs"] == gate["qualified_runs"] == 1
    assert gate["evaluator_reached_runs"] == 0
    assert gate["official_evaluator_runs"] == 0
    assert gate["diagnostic_passed_runs"] == 1
    assert gate["budget_terminal_runs"] == 1
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False

    diagnostic = payload["diagnostic"]
    assert diagnostic["status"] == "passed"
    assert diagnostic["saturated_context_sequences"] == [101]
    assert diagnostic["post_saturation_patch_sequences"] == [106]
    assert diagnostic["reset_context_sequences"] == [110]
    assert diagnostic["failed_reset_context_sequences"] == []

    run = payload["run"]
    assert run["run_id"] == "run_45e3edc434d749f7"
    assert run["outcome_kind"] == "agent_failure"
    assert run["official"] is False
    assert run["evaluation_status"] == "not_run"
    assert run["usage"] == {
        "input_tokens": 618370,
        "cached_input_tokens": 50688,
        "output_tokens": 41003,
        "reasoning_output_tokens": 30444,
        "total_tokens": 659373,
        "model_calls": 40,
        "tool_calls": 64,
        "wall_clock_ms": 320219,
        "model_cost_usd": 0.6140766,
    }
    assert run["telemetry"]["completed_responses"] == 40
    assert run["telemetry"]["incomplete_responses"] == 0
    assert run["telemetry"]["input_count_matches"] == 40
    assert run["telemetry"]["total_count_matches"] == 40
    assert run["lifecycle"]["review_task_calls"] == 14
    assert run["lifecycle"]["review_task_rejections"] == 14
    assert run["lifecycle"]["submission_attempted"] == 0
    assert run["terminal_budget"]["binding_dimension"] == "model_calls"
    assert run["terminal_budget"]["headroom"] == {
        "model_calls": 0,
        "tool_calls": 36,
        "total_tokens": 240627,
        "wall_clock_ms": 1479781,
    }
    assert run["qualification"]["qualified"] is True
    assert run["qualification"]["passed_checks"] == 30
    assert run["qualification"]["total_checks"] == 30
    assert run["qualification"]["memory_candidate_eligible"] is False

    assert len(payload["raw_local_artifacts"]) == 4
    for artifact in payload["raw_local_artifacts"]:
        assert artifact["bytes"] > 0
        assert artifact["path"].startswith(".patchloop/")
        assert artifact["sha256"].startswith("sha256:")
        if Path(artifact["path"]).exists():
            _assert_artifact_identity(artifact)


def test_d064_saturation_report_excludes_private_and_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-saturation-v8-pilot-20260801-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in checked_text
    assert "Bearer " not in checked_text
    package = load_task_package(
        "tasks/dev-train/hf-hub-xet-endpoint-propagation"
    )
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_d067_v9_report_preserves_original_gate_and_append_only_correction() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-review-evidence-v9-pilot-20260801-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "review-evidence-v9-pilot-evidence-v1"
    )
    assert payload["source_harness_commit"] == (
        "db144051f7f3d5049498971593df548697789dcf"
    )
    assert payload["correction_harness_commit"] == (
        "24fc92b9bbca5b1b9714a5a1f20d0dfbbc01205a"
    )
    assert payload["execution_hash"] == (
        "sha256:f1b7d78243af8c87e3ec83f9373312f171073e0713a23fbc51c909fac0be6982"
    )

    gate = payload["original_completion_gate"]
    assert gate["passed"] is False
    assert gate["terminal_runs"] == 1
    assert gate["qualified_runs"] == 0
    assert gate["evaluator_reached_runs"] == 1
    assert gate["official_evaluator_runs"] == 1
    assert gate["qualification_errors"] == 1
    assert gate["budget_terminal_runs"] == 0
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False
    assert gate["immutable"] is True
    assert gate["retroactively_recomputed"] is False

    run = payload["run"]
    assert run["run_id"] == "run_4c77b1102e224785"
    assert run["outcome_kind"] == "task_failure"
    assert run["official"] is True
    assert run["scope_compliant_success"] is False
    assert run["verdicts"] == {
        "hidden_tests": "fail",
        "regression_tests": "pass",
        "scope_policy": "pass",
        "safety_policy": "pass",
    }
    assert run["usage"] == {
        "input_tokens": 332204,
        "cached_input_tokens": 26112,
        "output_tokens": 12550,
        "reasoning_output_tokens": 9706,
        "total_tokens": 344754,
        "model_calls": 21,
        "tool_calls": 36,
        "wall_clock_ms": 121894,
        "model_cost_usd": 0.2880024,
    }
    assert run["budget_headroom"]["binding_dimension"] == "none"

    qualification = payload["qualification"]
    original = qualification["original"]
    correction = qualification["append_only_correction"]
    assert qualification["source_evidence_hash"] == (
        "sha256:2096b9a6114dc767aabd5e2d35d89077c91993a8cad6c42eeae99e223539f572"
    )
    assert original["qualification_hash"] == (
        "sha256:8840382b824dc27015e82d2949d39ada06c8169efe0fdcda3b219c3a1dece59e"
    )
    assert original["qualified"] is False
    assert original["passed_checks"] == 32
    assert original["total_checks"] == 33
    assert original["failed_check_ids"] == ["submission_lifecycle"]
    assert original["complete_source_in_context"] is False
    assert correction["correction_id"] == (
        "qcor_51b72504161eddf250e872cc533dbfc5a315c377971e8a6f19a74a380fe3c032"
    )
    assert correction["corrected_qualification_hash"] == (
        "sha256:1bff6db36a32104c2417c6aef65e8dcda50e00e71b451c51d78ae8df75df954c"
    )
    assert correction["correction_hash"] == (
        "sha256:836b013bccbdbcc7d0eecde24248b86eff353d1adef281f07b215c3ded65f0ed"
    )
    assert correction["file_sha256"] == (
        "sha256:2a78f098a0d5ff9782fd5e4385a1b56b2b23623475554f0f2c295cc2b99fba71"
    )
    assert correction["corrected_qualified"] is True
    assert correction["corrected_trace_integrity_passed"] is True
    assert correction["passed_checks"] == correction["total_checks"] == 33
    assert correction["failed_check_ids"] == []
    assert correction["complete_source_in_context"] is True
    assert correction["corrected_outcome_kind"] == "task_failure"
    assert correction["corrected_memory_candidate_eligible"] is False
    assert correction["original_qualification_rewritten"] is False
    assert correction["original_campaign_gate_recomputed"] is False
    assert correction["task_outcome_changed"] is False
    assert correction["scrr_changed"] is False

    assert payload["raw_local_artifacts"] == [
        {
            "role": "experiment-result",
            "path": (
                ".patchloop/experiments/"
                "dev-no-memory-review-evidence-v9-pilot-20260801-r1.json"
            ),
            "bytes": 13935,
            "sha256": (
                "sha256:71bb203ae2ffaf3deeaa9523273410c83bb477a0574b99279242c2e764caf96d"
            ),
        },
        {
            "role": "campaign-journal",
            "path": (
                ".patchloop/experiments/journals/"
                "dev-no-memory-review-evidence-v9-pilot-20260801-r1.jsonl"
            ),
            "bytes": 2753,
            "sha256": (
                "sha256:62e22e068fc08d1de91c8c9d78c9e94b6b2dd75cc1a216b75b5dc7ee916050c0"
            ),
        },
        {
            "role": "execution-plan-file",
            "path": (
                ".patchloop/experiments/plans/"
                "f1b7d78243af8c87e3ec83f9373312f171073e0713a23fbc51c909fac0be6982.json"
            ),
            "bytes": 7857,
            "sha256": (
                "sha256:d7d5497c1d1a464c7962bc89fea73c693e26801db3e25ed24fce2858f4eaa532"
            ),
        },
        {
            "role": "run-result",
            "path": (
                ".patchloop/artifacts/runs/"
                "run_4c77b1102e224785/result.json"
            ),
            "bytes": 4985,
            "sha256": (
                "sha256:e3f4a855ae1d53bcf3381cfe1bc35167503e2774dd80308e929ce2184bcafe8b"
            ),
        },
        {
            "role": "original-trace-qualification",
            "path": (
                ".patchloop/qualifications/"
                "run_4c77b1102e224785.json"
            ),
            "bytes": 16862,
            "sha256": (
                "sha256:1e3558eeee6ab505fe313a3f75ab4ae958e85876010321b74500c8c7a3464d2c"
            ),
        },
        {
            "role": "qualification-correction",
            "path": (
                ".patchloop/qualification-corrections/v1/"
                "run_4c77b1102e224785/"
                "qcor_51b72504161eddf250e872cc533dbfc5a315c377971e8a6f19a74a380fe3c032.json"
            ),
            "bytes": 18832,
            "sha256": (
                "sha256:2a78f098a0d5ff9782fd5e4385a1b56b2b23623475554f0f2c295cc2b99fba71"
            ),
        },
        {
            "role": "submitted-patch",
            "path": (
                ".patchloop/runs/run_4c77b1102e224785/"
                "submitted.patch"
            ),
            "bytes": 2305,
            "sha256": (
                "sha256:e30cb245bb556ce22fcc79bed31dcf97423c622419fb71bf31bf956aa3b29599"
            ),
        },
    ]
    for artifact in payload["raw_local_artifacts"]:
        if Path(artifact["path"]).exists():
            _assert_artifact_identity(artifact)


def test_d067_v9_report_excludes_private_and_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-review-evidence-v9-pilot-20260801-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in checked_text
    assert "Bearer " not in checked_text
    package = load_task_package(
        "tasks/dev-train/hf-hub-xet-endpoint-propagation"
    )
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_d070_v10_report_seals_terminal_failure_and_postmortem() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-coverage-review-v10-pilot-20260802-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "coverage-review-v10-pilot-evidence-v1"
    )
    assert payload["source_harness_commit"] == (
        "52c6f78098bbc147eb4147da8ee9d0e36b10b489"
    )
    assert payload["execution_hash"] == (
        "sha256:cc361c4fa569085b0268a419ec86a7a91ec87719206d604227d2cb45a9c46914"
    )

    gate = payload["original_completion_gate"]
    assert gate["passed"] is False
    assert gate["terminal_runs"] == 1
    assert gate["qualified_runs"] == 0
    assert gate["evaluator_reached_runs"] == 0
    assert gate["official_evaluator_runs"] == 0
    assert gate["qualification_errors"] == 1
    assert gate["budget_terminal_runs"] == 0
    assert gate["coverage_lifecycle_observed_runs"] == 0
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False
    assert gate["immutable"] is True
    assert gate["retroactively_recomputed"] is False

    run = payload["run"]
    assert run["run_id"] == "run_6cc69fc1170c4a44"
    assert run["outcome_kind"] == "agent_failure"
    assert run["agent_submission_status"] == "failed"
    assert run["evaluation_status"] == "not_run"
    assert run["official"] is False
    assert run["scope_compliant_success"] is False
    assert run["terminal_error"]["code"] == "SUBMISSION_PROTOCOL_ERROR"
    assert run["usage"] == {
        "input_tokens": 611450,
        "cached_input_tokens": 58880,
        "output_tokens": 56103,
        "reasoning_output_tokens": 44831,
        "total_tokens": 667553,
        "model_calls": 28,
        "tool_calls": 50,
        "wall_clock_ms": 353004,
        "model_cost_usd": 0.671307,
    }
    assert run["budget_headroom"]["binding_dimension"] == "none"

    review = payload["public_review_postmortem"]
    assert review["accepted_partial_review_sequence"] == 190
    assert review["coverage_target_count"] == 8
    assert review["verified_target_count"] == 7
    assert review["anchor_line_in_run_workspace"] == 1401
    assert review["corrective_read_range"] == {
        "start_line": 1407,
        "end_line": 1478,
    }
    assert review["complete_review_rejection_sequences"] == [220, 225, 230]
    assert review["submitted_unrelated_event_sequence"] == 169
    assert review["authoritative_allowed_event_sequences"] == []
    assert review["rejection_error_details_were_empty"] is True

    qualification = payload["qualification"]
    assert qualification["qualified"] is False
    assert qualification["trace_integrity_passed"] is False
    assert qualification["leakage_scan_passed"] is True
    assert qualification["passed_checks"] == 30
    assert qualification["total_checks"] == 34
    assert qualification["failed_check_ids"] == [
        "coverage_decision_integrity",
        "coverage_submission_lifecycle",
        "coverage_recovery_contract",
        "coverage_terminal_contract",
    ]

    postmortem = payload["no_model_postmortem_evaluation"]
    assert postmortem["run_id"] == "run_c07bb2e439a74380"
    assert postmortem["outcome_kind"] == "task_failure"
    assert postmortem["official"] is True
    assert postmortem["scope_compliant_success"] is False
    assert postmortem["verdicts"] == {
        "hidden_tests": "fail",
        "regression_tests": "pass",
        "scope_policy": "pass",
        "safety_policy": "pass",
    }
    assert postmortem["model_calls"] == 0
    assert postmortem["model_cost_usd"] == 0
    assert postmortem["changes_original_run"] is False

    assert payload["seal_validation"] == {
        "tests_collected": 991,
        "tests_passed": 984,
        "environment_dependent_skipped": 7,
        "ruff_passed": True,
        "git_diff_check_passed": True,
        "provider_calls": 0,
        "added_model_cost_usd": 0.0,
    }

    for artifact in payload["raw_local_artifacts"]:
        if Path(artifact["path"]).exists():
            _assert_artifact_identity(artifact)


def test_d070_v10_report_excludes_private_and_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-coverage-review-v10-pilot-20260802-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in checked_text
    assert "Bearer " not in checked_text
    package = load_task_package(
        "tasks/dev-train/hf-hub-xet-endpoint-propagation"
    )
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_d072_v11_report_seals_qualified_inconclusive_live_result() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "coverage-rejection-v11-pilot-evidence-v1"
    )
    assert payload["source_harness_commit"] == (
        "07f64c20103054d454a13584f2ea581b1363f268"
    )
    assert payload["execution_hash"] == (
        "sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d"
    )
    assert payload["runtime_contract"] == {
        "schema_version": "corrective-runtime-contract-v5",
        "tool_schema_version": "v6",
        "context_policy_version": "phase-evidence-v11",
        "system_prompt_hash": (
            "sha256:4dc0b19db38886bc4c7e274f3ce5a31b135fd10b632a54f4b40d97fa24b0e876"
        ),
        "tool_schema_hash": (
            "sha256:ead74f31a873d2fc2f92e7bdff36af4deb818981e756b94cbe0d75ef27d5b748"
        ),
    }

    gate = payload["original_completion_gate"]
    assert gate["passed"] is True
    assert gate["terminal_runs"] == 1
    assert gate["qualified_runs"] == 1
    assert gate["evaluator_reached_runs"] == 1
    assert gate["official_evaluator_runs"] == 1
    assert gate["infrastructure_errors"] == 0
    assert gate["qualification_errors"] == 0
    assert gate["diagnostic_errors"] == 0
    assert gate["budget_terminal_runs"] == 0
    assert gate["task_successes"] == 0
    assert gate["task_success_required"] is False
    assert gate["coverage_rejection_exercise"] == {
        "status": "inconclusive",
        "passed_runs": 0,
        "inconclusive_runs": 1,
        "failed_runs": 0,
    }
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False
    assert gate["immutable"] is True
    assert gate["retroactively_recomputed"] is False

    run = payload["run"]
    assert run["run_id"] == "run_e2132144a8774b05"
    assert run["outcome_kind"] == "task_failure"
    assert run["agent_submission_status"] == "completed"
    assert run["evaluation_status"] == "completed"
    assert run["official"] is True
    assert run["scope_compliant_success"] is False
    assert run["verdicts"] == {
        "hidden_tests": "fail",
        "regression_tests": "pass",
        "scope_policy": "pass",
        "safety_policy": "pass",
    }
    assert run["usage"] == {
        "input_tokens": 797862,
        "cached_input_tokens": 69120,
        "output_tokens": 64465,
        "reasoning_output_tokens": 42807,
        "total_tokens": 862327,
        "model_calls": 35,
        "tool_calls": 57,
        "wall_clock_ms": 369385,
        "model_cost_usd": 0.841833,
    }
    assert run["budget_headroom"] == {
        "model_calls": 25,
        "tool_calls": 43,
        "total_tokens": 337673,
        "wall_clock_ms": 1430615,
        "binding_dimension": "none",
    }
    assert run["public_submitted_patch"] == {
        "bytes": 4176,
        "sha256": (
            "sha256:d149f69d26f6580d6ca44fd4ff8704b8f760e0a51d2658401fdefbe1992aa31c"
        ),
        "changed_file_count": 3,
        "added_lines": 32,
        "deleted_lines": 5,
    }

    qualification = payload["qualification"]
    assert qualification["qualification_hash"] == (
        "sha256:496d1a835199a96a2237793eb3e2f34143e20e53b4b9e5e57f12040aac04fe72"
    )
    assert qualification["source_evidence_hash"] == (
        "sha256:5914bc5d4a317fb0995f1336551430beb4f9e745321b07c4c5e06f156b501ba8"
    )
    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["evaluation_reached"] is True
    assert qualification["passed_checks"] == qualification["total_checks"] == 36
    assert qualification["failed_check_ids"] == []
    assert qualification["memory_candidate_eligible"] is False

    exercise = payload["coverage_rejection_exercise"]
    assert exercise == {
        "status": "inconclusive",
        "reason": "rejection_not_observed",
        "coverage_citation_rejection_count": 0,
        "verified_coverage_citation_rejection_count": 0,
        "failed_rejection_sequences": [],
        "restart_observed": False,
        "live_recovery_validated": False,
    }
    retry = payload["separate_patch_candidate_retry_context"]
    assert retry["rejected_candidate_count"] == 17
    assert retry["retry_episode_count"] == retry["verified_retry_count"] == 17
    assert retry["failed_source_failure_sequences"] == []
    assert retry["not_coverage_citation_rejections"] is True
    assert payload["saturation_context"] == {
        "check_passed": True,
        "saturated_context_count": 17,
        "post_saturation_patch_count": 1,
        "reset_opportunity_count": 1,
        "reset_context_count": 1,
        "failed_reset_context_sequences": [],
    }

    claims = payload["claims_boundary"]
    assert claims["readiness_gate_passed"] is True
    assert claims["structured_coverage_rejection_observed"] is False
    assert claims["coverage_rejection_recovery_live_validated"] is False
    assert claims["live_hard_restart_validated"] is False
    assert claims["task_success"] is False
    assert claims["scrr"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False

    validation = payload["evidence_validation"]
    assert validation == {
        "raw_artifact_hashes_verified": True,
        "private_leak_scan_passed": True,
        "validation_scope": (
            "D-073 append-only source seal after the single approved "
            "D-072 invocation"
        ),
        "focused_regression": {
            "collected": 375,
            "passed": 374,
            "environment_dependent_skipped": 1,
            "failed": 0,
        },
        "repository_regression": {
            "collected": 1025,
            "passed": 1018,
            "environment_dependent_skipped": 7,
            "failed": 0,
        },
        "static_checks": {
            "ruff": "passed",
            "python_compileall": "passed",
            "git_diff_check": "passed",
        },
        "provider_calls": 0,
        "added_model_cost_usd": 0.0,
    }

    portable_patch = _artifact_for_role(
        payload, "final-submitted-public-source-diff"
    )
    _assert_artifact_identity(portable_patch)
    assert portable_patch["sha256"] == run["public_submitted_patch"]["sha256"]
    raw_submitted = next(
        artifact
        for artifact in payload["raw_local_artifacts"]
        if artifact["role"] == "submitted-patch"
    )
    assert portable_patch["bytes"] == raw_submitted["bytes"]
    assert portable_patch["sha256"] == raw_submitted["sha256"]
    if Path(raw_submitted["path"]).exists():
        assert Path(portable_patch["path"]).read_bytes() == Path(
            raw_submitted["path"]
        ).read_bytes()

    for artifact in payload["raw_local_artifacts"]:
        if Path(artifact["path"]).exists():
            _assert_artifact_identity(artifact)

    if Path(".patchloop/qualifications/run_e2132144a8774b05.json").exists():
        raw_qualification = load_trace_qualification("run_e2132144a8774b05")
        assert raw_qualification["qualification_hash"] == (
            qualification["qualification_hash"]
        )
        saturation_check = next(
            check
            for check in raw_qualification["checks"]
            if check["check_id"] == "saturation_context_contract"
        )
        assert saturation_check["passed"] == (
            payload["saturation_context"]["check_passed"]
        )
        for key in (
            "saturated_context_count",
            "post_saturation_patch_count",
            "reset_opportunity_count",
            "reset_context_count",
            "failed_reset_context_sequences",
        ):
            assert saturation_check["details"][key] == (
                payload["saturation_context"][key]
            )
        assert calculate_source_evidence_hash("run_e2132144a8774b05") == (
            qualification["source_evidence_hash"]
        )


def test_d072_v11_report_excludes_private_and_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    portable_patch = _artifact_for_role(
        payload, "final-submitted-public-source-diff"
    )
    portable_patch_path = Path(portable_patch["path"])
    checked_text = path.read_text(encoding="utf-8")
    checked_text += portable_patch_path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in checked_text
    assert "Bearer " not in checked_text
    package = load_task_package(
        "tasks/dev-train/hf-hub-xet-endpoint-propagation"
    )
    private_tokens = _private_leak_tokens(package, api_key=None)
    leaked = sorted(token for token in private_tokens if token in checked_text)
    assert leaked == []


def test_d075_generic_readiness_report_preserves_gate_and_budget_confound() -> None:
    path = Path(
        "reports/live-pilot/"
        "generic-baseline-readiness-v2v5-20260802-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "generic-baseline-readiness-d075-evidence-v1"
    )
    assert payload["source_harness_commit"] == (
        "2c075abedf58cd8a2ec0d928d8e7ebb0ba9acd1a"
    )
    assert payload["execution_hash"] == (
        "sha256:1709a9e9911f980aafe28cdd9fe9ed486367c134e2dc9e465c88e01f9462bd66"
    )
    assert payload["runtime_contract"] == {
        "schema_version": "generic-baseline-runtime-contract-v1",
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "system_prompt_hash": (
            "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
        ),
        "tool_schema_hash": (
            "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"
        ),
        "transport_max_retries": 0,
        "harness_git_commit": "2c075abedf58cd8a2ec0d928d8e7ebb0ba9acd1a",
    }
    assert payload["model_tuple"] == {
        "provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "provider_sdk_version": "2.47.0",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "max_output_tokens": 25000,
        "memory_condition": "no_memory",
        "repetitions": 1,
        "schedule_seed": 20260723,
    }

    gate = payload["original_completion_gate"]
    assert gate == {
        "schema_version": "generic-baseline-readiness-gate-v1",
        "passed": False,
        "expected_runs": 4,
        "terminal_runs": 4,
        "qualified_runs": 4,
        "evaluator_reached_runs": 2,
        "official_evaluator_runs": 2,
        "infrastructure_errors": 0,
        "qualification_errors": 0,
        "diagnostic_errors": 0,
        "task_identity_passed": True,
        "row_binding_passed": True,
        "run_binding_passed": True,
        "schedule_binding_passed": True,
        "execution_binding_passed": True,
        "budget_terminal_runs": 2,
        "budget_terminal_run_ids": [
            "run_466f7fb5275646e4",
            "run_7e10fe04319c4771",
        ],
        "task_successes": 2,
        "task_success_required": False,
        "comparison_denominator_eligible": False,
        "memory_admission_unlocked": False,
        "immutable": True,
        "retroactively_recomputed": False,
    }
    assert payload["budget"]["actual_campaign_usage"] == {
        "input_tokens": 1580179,
        "cached_input_tokens": 0,
        "output_tokens": 128645,
        "reasoning_output_tokens": 116987,
        "total_tokens": 1708824,
        "model_calls": 95,
        "tool_calls": 142,
        "wall_clock_ms": 915695,
        "model_cost_usd": 1.76403675,
    }
    assert payload["budget"]["terminal_bindings"] == {
        "count": 2,
        "run_ids": ["run_466f7fb5275646e4", "run_7e10fe04319c4771"],
        "dimensions": {
            "run_466f7fb5275646e4": "total_tokens",
            "run_7e10fe04319c4771": "model_calls",
        },
    }

    runs = {run["run_id"]: run for run in payload["runs"]}
    assert set(runs) == {
        "run_466f7fb5275646e4",
        "run_00d5fc0a8d914df4",
        "run_96817acf84c046fc",
        "run_7e10fe04319c4771",
    }
    assert runs["run_00d5fc0a8d914df4"]["scope_compliant_success"] is True
    assert runs["run_96817acf84c046fc"]["scope_compliant_success"] is True
    assert runs["run_466f7fb5275646e4"]["budget_pressure"] == {
        "binding_dimension": "total_tokens",
        "terminal_reason": "exact_request_budget_exceeded",
        "remaining_tokens": 40133,
        "next_exact_input_tokens": 24719,
        "response_allowance_tokens": 25000,
        "exact_request_deficit_tokens": 9586,
        "minimum_total_budget_same_prefix": 859586,
        "maximum_observed_exploration_tail_minimum": 1034573,
    }
    assert runs["run_7e10fe04319c4771"]["budget_pressure"][
        "binding_dimension"
    ] == "model_calls"

    qualifications = {
        item["run_id"]: item for item in payload["qualifications"]
    }
    assert set(qualifications) == set(runs)
    assert all(item["qualified"] for item in qualifications.values())
    assert all(item["trace_integrity_passed"] for item in qualifications.values())
    assert all(item["leakage_scan_passed"] for item in qualifications.values())
    assert all(
        item["passed_checks"] == item["total_checks"]
        for item in qualifications.values()
    )
    assert all(
        item["memory_candidate_eligible"] is False
        for item in qualifications.values()
    )

    claims = payload["claims_boundary"]
    assert claims["readiness_gate_passed"] is False
    assert claims["budget_confound_observed"] is True
    assert claims["no_memory_performance_baseline_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False
    assert payload["next_gate_candidate"] == {
        "change_scope": "budget-only",
        "frozen_model_prompt_tool_retry_evaluator_tuple": True,
        "proposed_per_run_budget": {
            "max_model_calls": 50,
            "max_tool_calls": 100,
            "max_total_tokens": 1_200_000,
            "wall_clock_timeout_seconds": 1_800,
            "max_output_tokens": 25_000,
        },
        "proposed_per_run_cost_reserve_usd": 5.5125,
        "proposed_four_run_reserve_usd": 22.05,
        "requires_new_suite_execution_hash_and_cost_approval": True,
        "authorized_by_this_record": False,
    }
    assert payload["portable_artifacts"] == []


def test_d075_generic_readiness_report_matches_live_raw_artifacts_when_present() -> None:
    path = Path(
        "reports/live-pilot/"
        "generic-baseline-readiness-v2v5-20260802-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]

    assert len(artifacts) == 19
    assert len({artifact["role"] for artifact in artifacts}) == len(artifacts)
    assert len({artifact["path"] for artifact in artifacts}) == len(artifacts)
    assert all(artifact["path"].startswith(".patchloop/") for artifact in artifacts)

    result_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["role"] == "experiment-result"
    )
    if not Path(result_artifact["path"]).exists():
        return

    for artifact in artifacts:
        assert Path(artifact["path"]).exists()
        _assert_artifact_identity(artifact)

    raw_result = json.loads(
        Path(result_artifact["path"]).read_text(encoding="utf-8")
    )
    assert raw_result["execution_hash"] == payload["execution_hash"]
    assert raw_result["suite_hash"] == payload["suite_hash"]
    assert raw_result["schedule_hash"] == payload["schedule_hash"]
    assert raw_result["actual_model_cost_usd"] == pytest.approx(
        payload["budget"]["actual_campaign_usage"]["model_cost_usd"]
    )
    for key, value in raw_result["completion_gate"].items():
        assert payload["original_completion_gate"][key] == value

    evidence_runs = {run["run_id"]: run for run in payload["runs"]}
    for row in raw_result["runs"]:
        run = evidence_runs[row["run_id"]]
        result = row["result"]
        assert run["task_id"] == row["task_id"]
        for key in (
            "outcome_kind",
            "official",
            "evaluation_status",
            "scope_compliant_success",
        ):
            assert run[key] == result[key]
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "model_calls",
            "tool_calls",
            "wall_clock_ms",
            "model_cost_usd",
        ):
            assert run["usage"][key] == result["usage"][key]
        assert run["usage"]["total_tokens"] == (
            result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        )

    evidence_qualifications = {
        item["run_id"]: item for item in payload["qualifications"]
    }
    for run_id, qualification in evidence_qualifications.items():
        raw_qualification = load_trace_qualification(run_id)
        assert raw_qualification["qualification_hash"] == (
            qualification["qualification_hash"]
        )
        assert raw_qualification["source_evidence_hash"] == (
            qualification["source_evidence_hash"]
        )
        assert calculate_source_evidence_hash(run_id) == (
            qualification["source_evidence_hash"]
        )
        assert raw_qualification["qualified"] == qualification["qualified"]
        assert len(raw_qualification["checks"]) == qualification["total_checks"]
        assert sum(check["passed"] for check in raw_qualification["checks"]) == (
            qualification["passed_checks"]
        )


def test_d075_generic_readiness_report_excludes_private_and_provider_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "generic-baseline-readiness-v2v5-20260802-r1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested
                for child in value.values()
                for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested
                for child in value
                for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    for marker in (
        "OPENAI_API_KEY",
        "Bearer ",
        "sk-",
        '"request_body"',
        '"response_id"',
        '"private_spec_hash"',
    ):
        assert marker not in checked_text

    task_paths = (
        "tasks/dev-train/hf-hub-xet-endpoint-propagation",
        "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes",
        "tasks/dev-validation/moto-query-scanned-count",
        "tasks/dev-train/pyfakefs-makedirs-parent-traversal",
    )
    leaked: list[str] = []
    for task_path in task_paths:
        package = load_task_package(task_path)
        private_tokens = _private_leak_tokens(package, api_key=None)
        leaked.extend(token for token in private_tokens if token in checked_text)
    assert sorted(set(leaked)) == []


def test_d077_budget_only_readiness_report_preserves_failed_gate() -> None:
    path = Path(
        "reports/live-pilot/"
        "generic-baseline-readiness-v2v5-20260802-r2.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "generic-baseline-readiness-d077-evidence-v1"
    )
    assert payload["source_harness_commit"] == (
        "4a2596e43398af094f1f17bcb0cb1a7945cb7058"
    )
    assert payload["execution_hash"] == (
        "sha256:de73e622fcaa4cec85191cceb01efdb0d27cc6a5a6b8f05c7cd4844df50763f5"
    )
    assert payload["runtime_contract"] == {
        "schema_version": "generic-baseline-runtime-contract-v1",
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "system_prompt_hash": (
            "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
        ),
        "tool_schema_hash": (
            "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"
        ),
        "transport_max_retries": 0,
        "harness_git_commit": "4a2596e43398af094f1f17bcb0cb1a7945cb7058",
    }
    assert payload["budget"]["actual_campaign_usage"] == {
        "input_tokens": 1_816_830,
        "cached_input_tokens": 0,
        "output_tokens": 181_254,
        "reasoning_output_tokens": 165_716,
        "total_tokens": 1_998_084,
        "model_calls": 125,
        "tool_calls": 219,
        "wall_clock_ms": 1_309_338,
        "model_cost_usd": 2.1782655,
    }

    gate = payload["original_completion_gate"]
    assert gate["passed"] is False
    assert gate["terminal_runs"] == gate["qualified_runs"] == 4
    assert gate["evaluator_reached_runs"] == 3
    assert gate["official_evaluator_runs"] == 3
    assert gate["budget_terminal_runs"] == 1
    assert gate["budget_terminal_run_ids"] == ["run_415695539ad24658"]
    assert gate["task_successes"] == 1
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False
    assert gate["immutable"] is True
    assert gate["retroactively_recomputed"] is False

    runs = {run["run_id"]: run for run in payload["runs"]}
    assert set(runs) == {
        "run_d5155046063644ad",
        "run_48cfb695d0be4c7d",
        "run_4896f998af9644b2",
        "run_415695539ad24658",
    }
    assert runs["run_4896f998af9644b2"]["scope_compliant_success"] is True
    pyfakefs = runs["run_415695539ad24658"]
    assert pyfakefs["evaluation_status"] == "not_run"
    assert pyfakefs["budget_pressure"]["binding_dimension"] == "model_calls"
    assert pyfakefs["budget_pressure"]["binding_reason"] == (
        "model_call_budget_exhausted"
    )
    assert pyfakefs["usage"]["model_calls"] == 50
    assert pyfakefs["usage"]["total_tokens"] == 812_840

    qualifications = {
        item["run_id"]: item for item in payload["qualifications"]
    }
    assert set(qualifications) == set(runs)
    assert [
        qualifications[run_id]["total_checks"]
        for run_id in (
            "run_d5155046063644ad",
            "run_48cfb695d0be4c7d",
            "run_4896f998af9644b2",
            "run_415695539ad24658",
        )
    ] == [27, 27, 27, 26]
    assert all(item["qualified"] for item in qualifications.values())
    assert all(
        item["passed_checks"] == item["total_checks"]
        for item in qualifications.values()
    )
    assert all(
        item["memory_candidate_eligible"] is False
        for item in qualifications.values()
    )

    analysis = payload["analysis"]
    assert analysis["analysis_ready"] is False
    assert analysis["ordinary_metrics_empty"] is True
    assert analysis["diagnostic_scrr"]["estimate"] == 0.25
    claims = payload["claims_boundary"]
    assert claims["readiness_gate_passed"] is False
    assert claims["remaining_binding_dimension"] == "model_calls"
    assert claims["no_memory_performance_baseline_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False
    assert payload["next_gate"] == {
        "automatic_rerun_authorized": False,
        "automatic_budget_increase_authorized": False,
        "prompt_tool_or_context_tuning_authorized": False,
        "baseline_freeze_authorized": False,
        "memory_admission_authorized": False,
        "required_next_action": (
            "review the remaining pyfakefs model-call completion confound "
            "without tuning to hidden outcomes"
        ),
    }
    assert payload["portable_artifacts"] == []


def test_d077_budget_only_readiness_report_matches_raw_artifacts_when_present(
) -> None:
    path = Path(
        "reports/live-pilot/"
        "generic-baseline-readiness-v2v5-20260802-r2.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload["raw_local_artifacts"]

    assert len(artifacts) == 20
    assert len({artifact["role"] for artifact in artifacts}) == len(artifacts)
    assert len({artifact["path"] for artifact in artifacts}) == len(artifacts)
    assert all(artifact["path"].startswith(".patchloop/") for artifact in artifacts)

    result_artifact = next(
        artifact for artifact in artifacts if artifact["role"] == "experiment-result"
    )
    if not Path(result_artifact["path"]).exists():
        return

    for artifact in artifacts:
        assert Path(artifact["path"]).exists()
        _assert_artifact_identity(artifact)

    raw_result = json.loads(
        Path(result_artifact["path"]).read_text(encoding="utf-8")
    )
    assert raw_result["execution_hash"] == payload["execution_hash"]
    assert raw_result["suite_hash"] == payload["suite_hash"]
    assert raw_result["schedule_hash"] == payload["schedule_hash"]
    assert raw_result["actual_model_cost_usd"] == pytest.approx(
        payload["budget"]["actual_campaign_usage"]["model_cost_usd"]
    )
    for key, value in raw_result["completion_gate"].items():
        assert payload["original_completion_gate"][key] == value

    evidence_runs = {run["run_id"]: run for run in payload["runs"]}
    for row in raw_result["runs"]:
        run = evidence_runs[row["run_id"]]
        result = row["result"]
        assert run["task_id"] == row["task_id"]
        for key in (
            "outcome_kind",
            "official",
            "evaluation_status",
            "scope_compliant_success",
        ):
            assert run[key] == result[key]
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "model_calls",
            "tool_calls",
            "wall_clock_ms",
            "model_cost_usd",
        ):
            assert run["usage"][key] == result["usage"][key]
        assert run["usage"]["total_tokens"] == (
            result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        )

    evidence_qualifications = {
        item["run_id"]: item for item in payload["qualifications"]
    }
    for run_id, qualification in evidence_qualifications.items():
        raw_qualification = load_trace_qualification(run_id)
        assert raw_qualification["qualification_hash"] == (
            qualification["qualification_hash"]
        )
        assert raw_qualification["source_evidence_hash"] == (
            qualification["source_evidence_hash"]
        )
        assert calculate_source_evidence_hash(run_id) == (
            qualification["source_evidence_hash"]
        )
        assert raw_qualification["qualified"] == qualification["qualified"]
        assert len(raw_qualification["checks"]) == qualification["total_checks"]
        assert sum(check["passed"] for check in raw_qualification["checks"]) == (
            qualification["passed_checks"]
        )

    report_artifact = next(
        artifact
        for artifact in artifacts
        if artifact["role"] == "post-run-analysis-report"
    )
    report = json.loads(Path(report_artifact["path"]).read_text(encoding="utf-8"))
    assert report["analysis_ready"] is False
    assert report["metrics"] == {}
    assert report["diagnostic_metrics"]["no_memory"]["scrr"]["estimate"] == 0.25


def test_d077_budget_only_readiness_report_excludes_private_payload() -> None:
    path = Path(
        "reports/live-pilot/"
        "generic-baseline-readiness-v2v5-20260802-r2.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
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
            return set(value) | {
                nested for child in value.values() for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested for child in value for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    checked_text = path.read_text(encoding="utf-8")
    for marker in (
        "OPENAI_API_KEY",
        "Bearer ",
        "sk-",
        '"request_body"',
        '"response_id"',
        '"private_spec_hash"',
    ):
        assert marker not in checked_text

    task_paths = (
        "tasks/dev-train/hf-hub-xet-endpoint-propagation",
        "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes",
        "tasks/dev-validation/moto-query-scanned-count",
        "tasks/dev-train/pyfakefs-makedirs-parent-traversal",
    )
    leaked: list[str] = []
    for task_path in task_paths:
        package = load_task_package(task_path)
        private_tokens = _private_leak_tokens(package, api_key=None)
        leaked.extend(token for token in private_tokens if token in checked_text)
    assert sorted(set(leaked)) == []
