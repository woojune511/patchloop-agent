from __future__ import annotations

import hashlib
import json
from pathlib import Path

INDEX_PATH = Path(
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r6-evidence.json"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_r6_runtime_evidence_index_is_content_addressed_and_bound() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    body = {key: value for key, value in evidence.items() if key != "content_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    assert evidence["content_hash"] == (
        "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )
    assert evidence["execution_source_commit"] == ("7e074b662c5a15914e0f04ea73b8bc3c64269487")
    assert evidence["campaign"]["execution_hash"] == (
        "sha256:c800f36bb133f5e0731e86a2b19870d40b26f54976780a001319c2a7b08e5d61"
    )
    assert evidence["campaign"]["accrued_cost_nanos"] == 169_596_000
    assert evidence["campaign"]["terminal_runs"] == 1
    assert evidence["campaign"]["not_started_runs"] == 3
    assert evidence["external_artifacts"]["journal"]["file_sha256"] == (
        "sha256:c733655c37f424d6c60f95213d013088bfd9b69707dde45e9386fcdf109ce327"
    )
    assert evidence["external_artifacts"]["final_result"]["file_sha256"] == (
        "sha256:2379bcabd2cea89556a8d8b21373202ca3c32a49e8e2f57508feb907367baf7f"
    )

    qualification = evidence["source_qualification"]
    qualification_path = Path(qualification["path"])
    assert qualification_path.stat().st_size == qualification["file_bytes"]
    assert _sha256(qualification_path) == qualification["file_sha256"]
    qualification_record = json.loads(qualification_path.read_text(encoding="utf-8"))
    assert qualification_record["content_hash"] == qualification["qualification_hash"]
    assert (
        qualification_record["successor_suite"]["content_hash"]
        == (qualification["successor_suite_hash"])
    )


def test_r6_index_preserves_runtime_policy_mismatch_and_successful_evaluation() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    failure = evidence["failure_attribution"]
    rows = evidence["rows"]

    assert failure["phase"] == "post-evaluator-trace-qualification"
    assert failure["failed_raw_checks"] == [
        "ac_fixed_runtime_contract",
        "bounded_call_guard_contract",
    ]
    assert failure["observed_call_guard_policy"] == ("model-tool-observability-only-v1")
    assert failure["required_call_guard_policy"] == ("model-tool-bounded-enforcement-v1")
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
    assert sum(row["cost_nanos"] for row in rows) == 169_596_000
    assert all(value is False for value in evidence["claim_authority"].values())
