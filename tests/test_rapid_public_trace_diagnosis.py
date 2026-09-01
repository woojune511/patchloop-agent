from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = (
    ROOT
    / "reports"
    / "rapid-development"
    / "rapid-public-dev-hard-panel-20260822-r3-5ae158b3ed65.jsonl"
)
DIAGNOSIS = (
    ROOT
    / "reports"
    / "rapid-development"
    / "artifacts"
    / "rapid-public-dev-hard-panel-20260822-r3-public-trace-diagnosis-v1.json"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_public_trace_diagnosis_binds_consumed_bundle_and_failed_rows() -> None:
    diagnosis = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    bundle_events = [
        json.loads(line) for line in BUNDLE.read_text(encoding="utf-8").splitlines()
    ]
    source = diagnosis["source_bundle"]

    assert diagnosis["schema_version"] == "rapid-public-trace-diagnosis-v1"
    assert diagnosis["official"] is False
    assert source["bytes"] == BUNDLE.stat().st_size == 11_927
    assert source["content_hash"] == _sha256(BUNDLE)
    assert source["terminal_content_hash"] == bundle_events[-1]["content_hash"]
    assert bundle_events[-1]["event"] == "batch-completed"

    failed_bundle_rows = {
        event["run_id"]
        for event in bundle_events
        if event["event"] == "row-terminal"
        and event["outcome_kind"] == "task_failure"
    }
    failed_diagnosis_rows = {row["run_id"] for row in diagnosis["rows"]}
    assert failed_bundle_rows == failed_diagnosis_rows == {
        "run_rapid_v6_5ae158b3ed65_02",
        "run_rapid_v6_5ae158b3ed65_05",
        "run_rapid_v6_5ae158b3ed65_06",
        "run_rapid_v6_5ae158b3ed65_08",
    }


def test_public_trace_diagnosis_preserves_evidence_and_claim_boundaries() -> None:
    diagnosis = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    boundary = diagnosis["evidence_boundary"]

    assert boundary == {
        "docker_calls": 0,
        "evaluator_calls": 0,
        "evaluator_private_artifacts_read": False,
        "hidden_assertions_read": False,
        "inputs_used": [
            "two public task specifications",
            "agent-visible model and tool events",
            "content-addressed submitted diffs",
            "public terminal verdict states",
        ],
        "private_evidence_used": False,
        "provider_calls": 0,
        "reasoning_text_read": False,
        "reference_patches_read": False,
        "settled_cost_usd": "0",
    }
    assert diagnosis["repeated_public_failure_mechanism"]["classification"] == (
        "PUBLIC_BEHAVIOR_CHECK_GAP"
    )
    assert diagnosis["successor_disposition"]["status"] == (
        "proposed_not_implemented_or_executed"
    )
    assert diagnosis["successor_disposition"]["paid_execution_authorized"] is False


def test_public_trace_diagnosis_records_observed_secondary_mechanisms() -> None:
    diagnosis = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    rows = {row["run_id"]: row for row in diagnosis["rows"]}

    assert rows["run_rapid_v6_5ae158b3ed65_06"]["zero_match_searches"] == 17
    assert rows["run_rapid_v6_5ae158b3ed65_06"]["classification"] == (
        "SEARCH_GLOB_BLINDNESS_AND_CAUSAL_BOUNDARY_MISS"
    )
    assert rows["run_rapid_v6_5ae158b3ed65_08"]["failed_tools"] == [
        "apply_patch:CONTRACT_ERROR:raw wrapper marker"
    ]
    secondary = {
        item["classification"]
        for item in diagnosis["non_outcome_separating_observations"]
    }
    assert secondary == {
        "RECOVERED_RAW_DIFF_FAILURE",
        "SINGLE_SEARCH_GLOB_INCIDENT",
    }
