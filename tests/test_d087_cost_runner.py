from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import pytest

from patchloop.evals import runner as eval_runner

SUITE_PATH = Path(
    "experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml"
)


def _admitted_pilot() -> dict:
    return {
        "schema_version": (
            eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_ADMISSION_SCHEMA
        ),
        "run_id": "run_c355405d826641b9",
        "admitted": True,
        "descriptor": {"test_fixture": True},
        "pilot_admission_hash": "sha256:" + ("a" * 64),
        "qualification_hash": "sha256:" + ("b" * 64),
        "source_evidence_hash": "sha256:" + ("c" * 64),
        "reason": None,
    }


def _passing_usage_reconciliation() -> dict:
    return _passing_projection("usage_reconciliation")


def _passing_projection(check_id: str) -> dict:
    return {
        "schema_version": eval_runner.QUALIFICATION_GATE_CHECK_PROJECTION_SCHEMA,
        "check_id": check_id,
        "check_count": 1,
        "passed": True,
    }


def _durable_evidence(
    usage: dict,
    *,
    run_id: str,
    schedule_row_id: str,
) -> dict:
    canonical_usage = dict(usage)
    canonical_usage["model_cost_usd"] = 0
    return eval_runner._d087_usage_evidence(
        eval_runner.Usage.model_validate(canonical_usage),
        run_id=run_id,
        schedule_row_id=schedule_row_id,
        qualification_hash="sha256:" + ("d" * 64),
        source_evidence_hash="sha256:" + ("e" * 64),
        persisted_result_hash="sha256:" + ("f" * 64),
    )


def _ready_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-rendered")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": "a" * 40, "clean": True},
    )
    monkeypatch.setattr("patchloop.runtime.git_commit", lambda: "a" * 40)
    monkeypatch.setattr(
        eval_runner,
        "_docker_image_state",
        lambda images: {
            "available": True,
            "images": [
                {
                    "image": image,
                    "identity": image.rsplit("@", 1)[-1],
                    "ready": True,
                }
                for image in sorted(set(images))
            ],
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_openai_sdk_state",
        lambda: {"installed": True, "version": version("openai")},
    )
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 4, 1, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_condition_neutral_comparison_pilot_admission",
        lambda *_args, **_kwargs: _admitted_pilot(),
    )
    # D-088 hard-consumes the real D-087 identity. These source/runtime tests
    # deliberately exercise the historical contract with an isolated fake
    # provider boundary, so remove only that exact post-run guard here.
    monkeypatch.setattr(
        eval_runner,
        "HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS",
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
        - eval_runner.CONSUMED_CONDITION_NEUTRAL_ACCRUED_CAP_EXPERIMENT_IDS,
    )
    # These tests isolate campaign accounting and use a deliberately minimal
    # synthetic D-085 admission.  The exact execution-plan binding has its own
    # D-087 test module; keep capability issuance focused on the journal here.
    monkeypatch.setattr(
        "patchloop.agent.runner.AgentRunner._live_plan_matches_manifest",
        lambda *_args, **_kwargs: True,
    )


def test_d087_runner_reserves_before_start_and_settles_token_derived_cost(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    unapproved = eval_runner.preflight_suite(SUITE_PATH)
    assert {row["code"] for row in unapproved["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }

    captured = []
    reservation_capabilities = []
    durable_usage_by_run = {}

    class FakeRunner:
        def start(self, _task, *, manifest, **kwargs):
            captured.append(manifest)
            reservation_capabilities.append(
                kwargs.get("campaign_cost_reservation")
            )
            result = {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "official": True,
                "evaluation_status": "completed",
                "scope_compliant_success": False,
                "usage": {
                    # This forged display value must not control D-087 accounting.
                    "model_cost_usd": "forged-display-value",
                    "model_calls": 1,
                    "tool_calls": 1,
                    "input_tokens": 1_000,
                    "cached_input_tokens": 0,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 100,
                    "wall_clock_ms": 1_000,
                },
            }
            durable_usage_by_run[manifest.run_id] = result["usage"]
            return result

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("d" * 64),
            "source_evidence_hash": "sha256:" + ("e" * 64),
            "usage_reconciliation": _passing_usage_reconciliation(),
            "persisted_result": _passing_projection("persisted_result"),
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_load_d087_durable_usage_evidence",
        lambda run_id, row_id, _root: _durable_evidence(
            durable_usage_by_run[run_id],
            run_id=run_id,
            schedule_row_id=row_id,
        ),
    )

    result = eval_runner.evaluate_suite(
        SUITE_PATH,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert len(captured) == 12
    assert all(
        manifest.experiment.campaign_cost_control_hash
        == result["campaign_cost_control"]["content_hash"]
        for manifest in captured
    )
    assert all(capability is not None for capability in reservation_capabilities)
    assert [capability.run_id for capability in reservation_capabilities] == [
        manifest.run_id for manifest in captured
    ]
    assert [
        capability.schedule_row_id
        for capability in reservation_capabilities
    ] == [
        manifest.experiment.schedule_row_id for manifest in captured
    ]
    # (1000 * $0.75/M + 100 * $4.50/M) * 12 = $0.0144.
    assert result["actual_model_cost_usd"] == pytest.approx(0.0144)
    assert result["campaign_cost_qualification"] == {
        "schema_version": "campaign-cost-qualification-v1",
        "passed": True,
        "fully_settled": True,
        "campaign_cost_control_hash": result["campaign_cost_control"][
            "content_hash"
        ],
        "cap_nanos": 25_000_000_000,
        "accrued_cost_nanos": 14_400_000,
        "held_reserve_nanos": 0,
        "maximum_committed_nanos": 7_325_700_000,
        "reserved_runs": 12,
        "settled_runs": 12,
        "reserve_unavailable_events": 0,
        "active_schedule_row_id": None,
        "active_run_id": None,
        "active_usage_reconciliation_passed": None,
        "live_resume_supported": False,
    }
    assert result["not_started_runs"] == 0

    journal = [
        json.loads(line)
        for line in Path(result["campaign_journal"]["path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["event_type"] for row in journal[:5]] == [
        "CampaignStarted",
        "RunCostReserved",
        "RunStarted",
        "RunTerminal",
        "RunCostSettled",
    ]
    assert journal[-1]["event_type"] == "CampaignCompleted"
    terminal = next(row for row in journal if row["event_type"] == "RunTerminal")
    assert terminal["payload"]["usage_evidence"]["content_hash"] == (
        terminal["payload"]["usage_evidence_hash"]
    )
    assert terminal["payload"]["usage_evidence"]["descriptor"][
        "token_derived_cost_nanos"
    ] == 1_200_000


def test_d087_runner_stops_before_the_fourth_full_reserve(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    unapproved = eval_runner.preflight_suite(SUITE_PATH)
    captured = []
    durable_usage_by_run = {}

    class HighCostRunner:
        def start(self, _task, *, manifest, **_kwargs):
            captured.append(manifest.run_id)
            result = {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "official": True,
                "evaluation_status": "completed",
                "scope_compliant_success": False,
                "usage": {
                    "model_cost_usd": 0.0,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "input_tokens": 0,
                    "cached_input_tokens": 0,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 1_600_000,
                    "wall_clock_ms": 1_000,
                },
            }
            durable_usage_by_run[manifest.run_id] = result["usage"]
            return result

    monkeypatch.setattr(eval_runner, "AgentRunner", HighCostRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("d" * 64),
            "source_evidence_hash": "sha256:" + ("e" * 64),
            "usage_reconciliation": _passing_usage_reconciliation(),
            "persisted_result": _passing_projection("persisted_result"),
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_load_d087_durable_usage_evidence",
        lambda run_id, row_id, _root: _durable_evidence(
            durable_usage_by_run[run_id],
            run_id=run_id,
            schedule_row_id=row_id,
        ),
    )

    result = eval_runner.evaluate_suite(
        SUITE_PATH,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert len(captured) == 3
    assert result["actual_model_cost_usd"] == 21.6
    assert result["not_started_runs"] == 9
    assert result["halt_reason"]["type"] == "CostReserveUnavailable"
    assert result["completion_gate"]["passed"] is False
    assert result["completion_gate"]["comparison_denominator_eligible"] is False
    assert result["completion_gate"]["memory_admission_unlocked"] is False
    assert result["campaign_cost_qualification"]["passed"] is True
    assert result["campaign_cost_qualification"]["reserved_runs"] == 3
    assert result["campaign_cost_qualification"][
        "reserve_unavailable_events"
    ] == 1


def test_d087_missing_usage_reconciliation_keeps_reserve_and_halts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    unapproved = eval_runner.preflight_suite(SUITE_PATH)
    captured = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_kwargs):
            captured.append(manifest.run_id)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "official": True,
                "evaluation_status": "completed",
                "scope_compliant_success": False,
                "usage": {
                    "model_cost_usd": 999.0,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "input_tokens": 1_000,
                    "cached_input_tokens": 0,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 100,
                    "wall_clock_ms": 1_000,
                },
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("f" * 64),
        },
    )

    result = eval_runner.evaluate_suite(
        SUITE_PATH,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert len(captured) == 1
    assert result["halt_reason"]["type"] == "InfrastructureFailureHalt"
    assert result["runs"][0]["infrastructure_error"]["type"] == (
        "CostAccountingUnavailable"
    )
    assert result["actual_model_cost_usd"] == 0.0
    assert result["not_started_runs"] == 11
    assert result["campaign_cost_qualification"]["fully_settled"] is False
    assert result["campaign_cost_qualification"]["accrued_cost_nanos"] == 0
    assert result["campaign_cost_qualification"]["held_reserve_nanos"] == (
        7_312_500_000
    )
    assert result["campaign_cost_qualification"]["reserved_runs"] == 1
    assert result["campaign_cost_qualification"]["settled_runs"] == 0
    assert result["campaign_cost_qualification"][
        "active_usage_reconciliation_passed"
    ] is False
