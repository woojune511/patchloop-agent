from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals import runner as eval_runner
from patchloop.util import sha256_bytes

ARTIFACT = Path(
    "reports/live-pilot/artifacts/"
    "d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json"
)


def test_d087_source_gate_binds_immutable_predecessors_and_successor() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "condition-neutral-comparison-accrued-spend-cap-source-gate-v1"
    )
    assert payload["gate_id"] == (
        "d087-condition-neutral-comparison-accrued-spend-cap-source-gate"
    )
    for predecessor in payload["predecessors"]:
        assert predecessor["modified"] is False
        assert sha256_bytes(Path(predecessor["path"]).read_bytes()) == predecessor["sha256"]

    source = payload["campaign_source"]
    suite_path = Path(source["suite_path"])
    assert sha256_bytes(suite_path.read_bytes()) == source["suite_sha256"]
    suite = eval_runner.load_suite(suite_path)
    assert suite.experiment_id == source["experiment_id"]
    assert suite.pilot_run_id == source["pilot_run_id"]
    assert source["expected_runs"] == 12
    assert suite.budget.max_total_tokens == 1_600_000


def test_d087_source_gate_keeps_cap_completion_and_authority_separate() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    derivation = payload["cost_cap_derivation"]
    pricing = payload["pricing"]
    policy = payload["campaign_spend_policy"]
    runtime = payload["runtime_binding"]
    authorization = payload["authorization_boundary"]
    claims = payload["claims_boundary"]

    assert derivation["twelve_run_mean_projection_usd"] == 5.38278975
    assert derivation["twelve_run_empirical_envelope_usd"] == 14.36724
    assert derivation["envelope_plus_reserve_usd"] == 21.67974
    assert pricing["campaign_hard_cap_usd"] == 25.0
    assert pricing["twelve_run_worst_rate_upper_bound_usd"] == 87.75
    assert policy["full_schedule_reserved_up_front"] is False
    assert policy["completion_guaranteed"] is False
    assert policy["hard_cap_nano_usd"] == 25_000_000_000
    assert policy["full_next_run_reserve_nano_usd"] == 7_312_500_000
    assert runtime["one_use_paid_boundary_capability"] is True
    assert runtime["atomic_sqlite_reservation_consumption"] is True
    assert runtime["canonical_journal_path_and_runner_root_binding"] is True
    assert runtime["consumed_reservation_set_reconciled_before_next_row"] is True
    assert (
        runtime[
            "marker_deletion_or_journal_reset_rejected_with_preserved_sqlite_anchor"
        ]
        is True
    )
    assert (
        runtime[
            "durable_usage_evidence_binds_qualification_source_and_result_hashes"
        ]
        is True
    )
    assert runtime["prior_settlement_reloaded_and_repriced_before_next_row"] is True
    assert runtime["displayed_model_cost_ignored_for_settlement"] is True
    assert runtime["external_or_request_level_billing_ledger_implemented"] is False
    assert authorization["clean_host_preflight_performed"] is False
    assert authorization["provider_execution_authorized"] is False
    assert authorization["maximum_future_approval_cap_usd"] == 25.0
    assert claims["provider_calls_made"] == 0
    assert claims["added_model_cost_usd"] == 0.0
    assert claims["campaign_executed"] is False
    assert claims["no_memory_baseline_result_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False


def test_d087_source_gate_records_current_offline_verification() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    focused = payload["verification"]["focused"]
    repository = payload["verification"]["repository_wide"]

    assert focused["passed"] == 68
    assert focused["failed"] == 0
    assert "tests/test_d087_source_gate_artifact.py" in focused["command"]
    assert "tests/test_state_store.py" in focused["command"]
    assert repository == {
        "command": "uv run pytest -q",
        "collected": 1472,
        "passed": 1465,
        "skipped": 7,
        "failed": 0,
    }
    assert payload["verification"]["provider_calls"] == 0
    assert payload["verification"]["added_model_cost_usd"] == 0.0
