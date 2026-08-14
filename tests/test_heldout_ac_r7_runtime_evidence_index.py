from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "reports/heldout-ac/artifacts/heldout-ac-r7-campaign-inconclusive-r1.json"


def _sha256(raw: bytes) -> str:
    return "sha256:" + sha256(raw).hexdigest()


def test_r7_campaign_evidence_index_is_content_addressed_and_bounded() -> None:
    evidence = json.loads(INDEX_PATH.read_bytes())
    body = {key: value for key, value in evidence.items() if key != "content_hash"}

    assert evidence["content_hash"] == sha256_json(body)
    assert evidence["status"] == ("LIVE_CAMPAIGN_INCONCLUSIVE_QUALIFICATION_BYTES_NONCANONICAL")
    assert evidence["approval"] == {
        "execution_hash": (
            "sha256:2f51935b52cc60a1d01dbd08cfbc811736afd87cc635b08f78bff44c869b2afa"
        ),
        "scheduled_rows": 48,
        "full_schedule_reserve_nanos": 252_000_000_000,
        "hard_cap_nanos": 275_000_000_000,
        "approval_consumed": True,
        "retry_replacement_or_resume_authorized": False,
    }
    assert evidence["campaign_summary"] == {
        "disposition": "inconclusive-matrix",
        "expected_runs": 48,
        "dispatched_runs": 1,
        "terminal_settled_runs": 0,
        "not_started_runs": 47,
        "unsettled_dispatched_runs": 1,
        "settled_model_cost_nanos": 0,
        "cost_accounting_complete": False,
        "analysis_ready": False,
        "official_heldout_analysis": False,
        "memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
    }


def test_r7_index_preserves_observed_row_and_failure_attribution() -> None:
    evidence = json.loads(INDEX_PATH.read_bytes())
    result = evidence["observed_row"]["run_result"]
    usage = evidence["observed_row"]["usage_evidence"]
    qualification = evidence["observed_row"]["trace_qualification"]
    failure = evidence["failure_attribution"]

    assert result["outcome_kind"] == "resolved"
    assert result["raw_official"] is False
    assert {
        result[key] for key in ("hidden_tests", "regression_tests", "scope_policy", "safety_policy")
    } == {"pass"}
    assert qualification["qualified"] is True
    assert qualification["evaluator_v2_completion_eligible"] is True
    assert usage["token_derived_cost_nanos"] == 66_252_750
    assert usage["campaign_settled"] is False
    assert failure["direct_cause"] == (
        "trace-qualification-producer-consumer-canonical-byte-mismatch"
    )
    assert failure["persisted_crlf_count"] == 393
    assert (
        failure["persisted_qualification_bytes"] - failure["lf_canonical_qualification_bytes"]
        == 393
    )
    assert failure["task_or_memory_effect_failure"] is False
    assert all(
        value is False for key, value in evidence["authority"].items() if key.endswith("authorized")
    )


def test_r7_index_revalidates_local_runtime_bytes_when_present() -> None:
    evidence = json.loads(INDEX_PATH.read_bytes())
    bindings = list(evidence["runtime_files"].values())
    bindings.extend(
        evidence["observed_row"][key]
        for key in (
            "run_result",
            "evaluation_receipt",
            "safety_evidence_bundle",
            "trace_qualification",
            "usage_evidence",
        )
    )
    available = [binding for binding in bindings if (ROOT / binding["path"]).is_file()]
    if not available:
        return
    assert len(available) == len(bindings)
    for binding in bindings:
        raw = (ROOT / binding["path"]).read_bytes()
        assert len(raw) == binding["file_bytes"]
        assert _sha256(raw) == binding["file_sha256"]
