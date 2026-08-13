from __future__ import annotations

import hashlib
import json
from pathlib import Path

INDEX_PATH = Path(
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r5-evidence.json"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_r5_runtime_evidence_index_is_content_addressed_and_bound() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    body = {key: value for key, value in evidence.items() if key != "content_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    assert evidence["content_hash"] == (
        "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )
    assert evidence["execution_source_commit"] == (
        "6f0f94ef8b6d88c179053b12c3047b3bb91101f7"
    )
    assert evidence["campaign"]["execution_hash"] == (
        "sha256:b8d156c6deeb3749b7a42f327fcfc7f5467a498b1ec0afaae4b19797b62a1627"
    )
    assert evidence["campaign"]["accrued_cost_nanos"] == 193_034_250
    assert evidence["campaign"]["terminal_runs"] == 1
    assert evidence["campaign"]["not_started_runs"] == 3
    assert evidence["external_artifacts"]["journal"]["file_sha256"] == (
        "sha256:4ea90b6390112667e0bed77ceb7a85f14c6df946e0691847fb3567e6d3ab9c7d"
    )
    assert evidence["external_artifacts"]["final_result"]["file_sha256"] == (
        "sha256:1edd9e788fa3fdbde521f9abeef4996f667638cc85650604b7efbb7420926f9f"
    )

    qualification = evidence["source_qualification"]
    qualification_path = Path(qualification["path"])
    assert qualification_path.stat().st_size == qualification["file_bytes"]
    assert _sha256(qualification_path) == qualification["file_sha256"]
    qualification_record = json.loads(qualification_path.read_text(encoding="utf-8"))
    assert qualification_record["content_hash"] == qualification["qualification_hash"]
    assert qualification_record["successor_suite"]["content_hash"] == (
        qualification["successor_suite_hash"]
    )


def test_r5_index_preserves_successful_evaluation_and_qualification_failure() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    failure = evidence["failure_attribution"]
    rows = evidence["rows"]

    assert failure["phase"] == "post-evaluator-trace-qualification"
    assert failure["failed_raw_checks"] == [
        "disabled_call_guard_contract",
        "frozen_model_contract",
    ]
    assert failure["forbidden_generation_block_sequences"] == []
    assert failure["forbidden_tail_block_sequences"] == []
    assert failure["evaluator_reached"] is True
    assert failure["task_resolved"] is True
    assert [(row["task_id"], row["condition"], row["attempt_status"]) for row in rows] == [
        ("moto-query-scanned-count", "no_memory", "terminal"),
        ("moto-query-scanned-count", "structured", "not_started"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "structured", "not_started"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "no_memory", "not_started"),
    ]
    assert rows[0]["verdicts"] == {
        "hidden_tests": "pass",
        "regression_tests": "pass",
        "scope_policy": "pass",
        "safety_policy": "pass",
    }
    assert rows[0]["trace_qualified"] is False
    assert sum(row["cost_nanos"] for row in rows) == 193_034_250
    assert all(value is False for value in evidence["claim_authority"].values())
