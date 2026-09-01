from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.rapid_public_development_v4 import _runtime_build_binding
from patchloop.util import canonical_json, sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / (
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22-"
    "candidate-v30-prestart-stop-v1.json"
)


def _audit() -> dict:
    value = json.loads(AUDIT.read_bytes())
    body = {key: item for key, item in value.items() if key != "content_hash"}
    assert value["content_hash"] == sha256_json(body)
    assert AUDIT.read_bytes() == (canonical_json(value) + "\n").encode()
    return value


def test_r22_prestart_stop_is_not_a_synthesized_agent_failure() -> None:
    value = _audit()
    observed = value["execution_observation"]
    assert value["status"] == "operator-stopped-before-batch-start"
    assert value["official"] is False
    assert observed["scheduled_rows"] == observed["not_started_rows"] == 6
    for key in (
        "started_rows",
        "settled_rows",
        "run_count",
        "event_count",
        "checkpoint_count",
        "action_result_count",
        "row_start_consumption_count",
        "provider_calls",
        "agent_execution_calls",
        "evaluator_calls",
        "visible_check_calls",
        "added_model_cost_nanos",
    ):
        assert observed[key] == 0
    assert observed["canonical_bundle_exists"] is False
    assert not (ROOT / observed["canonical_bundle_path"]).exists()
    assert value["evidence_boundary"]["canonical_batch_result_synthesized"] is False
    assert value["evidence_boundary"]["agent_performance_measured"] is False


def test_r22_does_not_relabel_unknown_docker_observation_as_zero_calls() -> None:
    value = _audit()
    observed = value["execution_observation"]
    assert value["authorized_scope"]["local_image_identity_checks"] == 1
    assert value["source_observation"]["identity_calls_on_complete_successful_six_row_path"] == 13
    assert observed["observed_image_identity_check_count"] is None
    assert observed["observed_docker_daemon_preflight_count"] is None
    assert observed["docker_call_count_receipt_available"] is False
    assert observed["image_identity_check_count_before_stop_upper_bound"] == 1


def test_r22_prestart_stop_preserves_candidate_runtime_and_approved_plan() -> None:
    value = _audit()
    candidate_raw = (ROOT / value["candidate_path"]).read_bytes()
    assert sha256_bytes(candidate_raw) == value["candidate_file_sha256"]
    candidate = json.loads(candidate_raw)
    assert candidate["execution_hash"] == value["execution_hash"]
    assert candidate["content_hash"] == value["candidate_content_hash"]
    assert candidate["runtime_build_hash"] == value["runtime_build_hash"]
    # R23 is a separately hashed infrastructure successor; the recorded R22
    # runtime identity and approved plan must not be rebound to current source.
    assert _runtime_build_binding(ROOT)[0] != value["runtime_build_hash"]
    invocation = value["invocation"]
    plan_raw = (ROOT / invocation["plan_path"]).read_bytes()
    assert len(plan_raw) == invocation["plan_bytes"]
    assert sha256_bytes(plan_raw) == invocation["plan_file_sha256"]
    assert invocation["count"] == 1
    assert invocation["stopped_by_operator"] is True
    assert value["disposition"]["same_candidate_retry_authorized"] is False
    assert value["disposition"]["runtime_fix_implemented"] is False
    assert value["disposition"]["successor_candidate_created"] is False
