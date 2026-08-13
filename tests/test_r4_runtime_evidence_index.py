from __future__ import annotations

import hashlib
import json
from pathlib import Path

INDEX_PATH = Path(
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r4-evidence.json"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_r4_runtime_evidence_index_is_content_addressed_and_bound() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    body = {key: value for key, value in evidence.items() if key != "content_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    assert evidence["content_hash"] == (
        "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )
    assert evidence["execution_source_commit"] == (
        "33f789edc539f4e117693b422ceb2bc3d2a30474"
    )
    assert evidence["campaign"] == {
        "execution_hash": "sha256:be4ea2e4e17a1354895c9122cd33180837cf29aa3922df4caeaafb46a08d7124",
        "schedule_hash": "sha256:c232f6ddd649d0c6a743ff877e61e4089ce075918a45ea45e3d866565a4b0e1a",
        "cost_control_hash": (
            "sha256:8a784b6458d28d10fda97d75f55311269acce3093b6a0acd508b1ac8d57a1a88"
        ),
        "full_schedule_reserve_nanos": 15_300_000_000,
        "hard_cap_nanos": 18_000_000_000,
        "accrued_cost_nanos": 0,
        "state": "SEALED",
        "disposition": "inconclusive",
        "expected_runs": 4,
        "terminal_runs": 1,
        "qualified_runs": 0,
        "receipt_qualified_evaluator_v2_runs": 0,
        "cost_settled_runs": 0,
        "not_started_runs": 3,
        "infrastructure_errors": 1,
        "analysis_ready": False,
        "retry_or_replacement_performed": False,
    }
    assert evidence["external_artifacts"]["journal"]["file_sha256"] == (
        "sha256:69b680946e70fc2c0643de796726c95b5a447320e565b5d6cccabfb51688779e"
    )
    assert evidence["external_artifacts"]["final_result"]["file_sha256"] == (
        "sha256:e33232fe2441324e310cf1db444f9c311c336d65f8138026bd1b45c3c9aec092"
    )

    qualification = evidence["source_qualification"]
    qualification_path = Path(qualification["path"])
    assert qualification_path.stat().st_size == qualification["file_bytes"]
    assert _sha256(qualification_path) == qualification["file_sha256"]
    qualification_record = json.loads(qualification_path.read_text(encoding="utf-8"))
    assert qualification_record["content_hash"] == qualification["qualification_hash"]
    assert qualification_record["evaluator_source_hash"] == (
        qualification["evaluator_source_hash"]
    )
    assert qualification_record["successor_suite"]["content_hash"] == (
        qualification["successor_suite_hash"]
    )


def test_r4_index_preserves_provider_before_dispatch_failure_boundary() -> None:
    evidence = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    failure = evidence["failure_attribution"]
    rows = evidence["rows"]

    assert failure == {
        "phase": "provider-before-dispatch",
        "row": 1,
        "run_id": "run_0e8ff15172bd45a7",
        "task_id": "moto-query-scanned-count",
        "condition": "no_memory",
        "error_type": "ContractError",
        "error_message": (
            "live model execution requires an approved experiment execution capability"
        ),
        "direct_cause": (
            "paid execution-plan revalidation compared the split-budget runtime contract "
            "to the legacy aggregate-only budget"
        ),
        "provider_dispatch_reached": False,
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "model_cost_nanos": 0,
        "automatic_retry_or_resume_allowed": False,
    }
    assert [(row["task_id"], row["condition"], row["attempt_status"]) for row in rows] == [
        ("moto-query-scanned-count", "no_memory", "terminal"),
        ("moto-query-scanned-count", "structured", "not_started"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "structured", "not_started"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "no_memory", "not_started"),
    ]
    assert sum(row["cost_nanos"] for row in rows) == 0
    assert all(value is False for value in evidence["claim_authority"].values())
