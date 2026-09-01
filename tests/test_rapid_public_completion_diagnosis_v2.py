from __future__ import annotations

import hashlib
import json
from pathlib import Path

from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = (
    ROOT
    / "reports"
    / "rapid-development"
    / "rapid-public-dev-anyio-completion-policy-20260823-r8-553f7cfca404.jsonl"
)
DIAGNOSIS = (
    ROOT
    / "reports"
    / "rapid-development"
    / "artifacts"
    / "rapid-public-dev-anyio-completion-policy-20260823-r8-public-trace-diagnosis-v2.json"
)
DIAGNOSIS_SHA256 = (
    "sha256:419b42b8188f0efbaa228f711a1d963e8c945d56936d7a95c519f87b6480dddf"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load() -> dict:
    return json.loads(DIAGNOSIS.read_text(encoding="utf-8"))


def test_r8_public_diagnosis_is_content_addressed_and_binds_consumed_bundle() -> None:
    diagnosis = _load()
    source = diagnosis["source_bundle"]
    bundle_events = [json.loads(line) for line in BUNDLE.read_text(encoding="utf-8").splitlines()]

    assert DIAGNOSIS.stat().st_size == 15_358
    assert _sha256(DIAGNOSIS) == DIAGNOSIS_SHA256
    assert diagnosis["content_hash"] == sha256_json(
        {key: value for key, value in diagnosis.items() if key != "content_hash"}
    )
    assert source == {
        "path": (
            "reports/rapid-development/"
            "rapid-public-dev-anyio-completion-policy-20260823-r8-553f7cfca404.jsonl"
        ),
        "bytes": 9567,
        "file_sha256": _sha256(BUNDLE),
        "execution_hash": (
            "sha256:553f7cfca404df2985fe5a79b267738c4e63afadd2997c9451e1fc35328faa74"
        ),
        "terminal_content_hash": bundle_events[-1]["content_hash"],
    }
    assert bundle_events[-1]["event"] == "batch-completed"


def test_r8_diagnosis_separates_task_budget_and_loop_evidence() -> None:
    diagnosis = _load()
    aggregate = diagnosis["aggregate_tool_path"]
    findings = {item["classification"] for item in diagnosis["findings"]}

    assert diagnosis["observed_batch"] == {
        "attempted_rows": 6,
        "agent_rows_started": 6,
        "harness_admission_failures": 0,
        "agent_failures": 6,
        "evaluator_reached": 0,
        "submissions_completed": 0,
        "successes_at_budget": 0,
        "bundle_token_terminals": 3,
        "provider_incomplete_terminals": 3,
        "model_calls": 277,
        "tool_calls": 444,
        "model_cost_nanos": 5_302_506_000,
    }
    assert diagnosis["budget_counterevidence"]["same_task_baseline_success_rate_across_r7_r8"] == (
        "1/6"
    )
    assert diagnosis["prior_easy_task_counterpoint"]["successes"] == "8/8"
    assert aggregate["baseline"]["visible_check_failures"] == 35
    assert aggregate["lean_v7"] == {
        "search_calls": 25,
        "read_calls": 28,
        "post_first_mutation_search_or_read_calls": 0,
        "raw_patch_calls": 37,
        "structured_edit_calls": 26,
        "patch_applied": 17,
        "executed_edit_failures": 46,
        "raw_invalid_hunk_header_failures": 14,
        "raw_context_mismatch_failures": 18,
        "visible_check_passes": 6,
        "visible_check_failures": 28,
        "simultaneous_check_pairs": 16,
        "targeted_failed_but_upstream_still_ran": 14,
        "diffs_passing_both_visible_checks": 0,
    }
    assert findings == {
        "TASK_DIFFICULTY_IS_REAL_BUT_NOT_IMPOSSIBILITY",
        "TOKEN_CAP_IS_TERMINAL_SURFACE_NOT_PRIMARY_ROOT_CAUSE",
        "V7_BLIND_CORRECTION_LANE",
        "IMPLEMENTATION_FRONTIER_OSCILLATION",
        "EDIT_INTERFACE_AND_CONTEXT_FRICTION_AMPLIFIED_FAILURE",
        "CHECK_SCHEDULING_WASTED_WORK",
        "TERMINAL_ATTRIBUTION_ORDER_BUG",
    }


def test_r8_diagnosis_preserves_claim_and_authority_boundaries() -> None:
    diagnosis = _load()
    boundary = diagnosis["evidence_boundary"]
    successor = diagnosis["implemented_offline_successor"]
    disposition = diagnosis["disposition"]

    assert diagnosis["official"] is False
    assert boundary["hidden_assertions_read"] is False
    assert boundary["private_evaluator_artifacts_read"] is False
    assert boundary["reference_patches_read"] is False
    assert boundary["reasoning_text_read"] is False
    assert boundary["llm_response_text_read"] is False
    assert (boundary["provider_calls"], boundary["docker_calls"], boundary["evaluator_calls"]) == (
        0,
        0,
        0,
    )
    assert diagnosis["request_context_observation"]["offline_latest-only_projection"] == {
        "projected_requests": 112,
        "requests_changed": 63,
        "full_correction_bodies_after_projection": 1,
        "total_context_json_bytes_saved": 356_077,
        "per_changed_request_bytes_saved_range": [1858, 12983],
        "provider_calls": 0,
        "state_mutations": 0,
    }
    assert successor["runtime_wired"] is False
    assert successor["provider_calls_authorized"] is False
    assert successor["paid_execution_authorized"] is False
    assert disposition["r8_consumed"] is True
    assert disposition["r8_retry_authorized"] is False
    assert disposition["quality_improvement_established"] is False
