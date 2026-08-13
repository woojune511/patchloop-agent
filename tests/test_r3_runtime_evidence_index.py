from __future__ import annotations

import hashlib
import json
from pathlib import Path

INDEX_PATH = Path(
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260813-r3-evidence.json"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_r3_runtime_evidence_index_is_content_addressed_and_bound() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    body = {key: value for key, value in evidence.items() if key != "content_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    assert (
        evidence["content_hash"]
        == "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )
    assert evidence["execution_source_commit"] == "ff50d0ea8db39496335b896fedc41cae3f89183b"
    expected_campaign = {
        "execution_hash": "sha256:c6506a33a8f55da6f52dffd59e5ad30dc7a945f55b964b484827424762374a2a",
        "state": "SEALED",
        "disposition": "inconclusive",
        "expected_runs": 4,
        "terminal_runs": 2,
        "qualified_runs": 1,
        "receipt_qualified_evaluator_v2_runs": 1,
        "cost_settled_runs": 2,
        "not_started_runs": 2,
        "analysis_ready": False,
        "retry_or_replacement_performed": False,
    }
    assert {key: evidence["campaign"][key] for key in expected_campaign} == expected_campaign
    assert evidence["external_artifacts"]["journal"]["file_sha256"] == (
        "sha256:cff6c0e72dcbc99302ac1f15a8edf5c49b807a368db1f8f0c8014d814eb64f69"
    )
    assert evidence["external_artifacts"]["final_result"]["file_sha256"] == (
        "sha256:d94b0a2956d8664e48fb80415358b6f7020c190abeb9e32e24d5a389cbaedecf"
    )
    assert sum(row.get("cost_nanos", 0) for row in evidence["rows"]) == 3_477_312_750

    qualification = evidence["source_qualification"]
    qualification_path = Path(qualification["path"])
    assert qualification_path.stat().st_size == qualification["file_bytes"]
    assert _sha256(qualification_path) == qualification["file_sha256"]
    qualification_record = json.loads(qualification_path.read_text(encoding="utf-8"))
    assert qualification_record["content_hash"] == qualification["qualification_hash"]
    assert qualification_record["evaluator_source_hash"] == qualification["evaluator_source_hash"]
    assert (
        qualification_record["successor_suite"]["content_hash"]
        == qualification["successor_suite_hash"]
    )


def test_r3_index_preserves_exact_row_and_predecessor_boundaries() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    rows = evidence["rows"]

    assert [(row["task_id"], row["condition"], row["attempt_status"]) for row in rows] == [
        ("moto-query-scanned-count", "no_memory", "terminal"),
        ("moto-query-scanned-count", "structured", "terminal"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "structured", "not_started"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "no_memory", "not_started"),
    ]
    assert rows[0]["evaluator_v2_receipt_hash"] == (
        "sha256:14e16e958e35dfae5077f538f9c9b98bedb9568756f5fe10211dd71b6d0d8418"
    )
    assert rows[1]["evaluation_status"] == "not_run"
    assert rows[1]["observed_terminal_evidence"] == {
        "model_generation_blocked_sequence": 907,
        "reason_code": "exact_request_budget_exceeded",
        "run_failed_sequence": 909,
        "error_type": "ModelGenerationBudgetError",
    }
    assert evidence["predecessor_r2"]["byte_immutability_revalidated_after_r3"] is True
    assert all(value is False for value in evidence["claim_authority"].values())
