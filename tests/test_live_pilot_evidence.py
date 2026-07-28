from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


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
    assert correction["journal_recorded_result_hash"] != (
        correction["persisted_result_file_sha256"]
    )
    assert correction["journal_recorded_result_hash"] == (
        correction["lf_normalized_result_sha256"]
    )
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
        artifact
        for artifact in raw_artifacts
        if artifact["path"].endswith("/submitted.patch")
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
