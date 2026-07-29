from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.contracts import DatasetRole, ExperimentPurpose
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals import qualification as trace_qualification
from patchloop.evals import runner as eval_runner
from patchloop.evals.runner import ExperimentSuite
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text


def _core_suite_payload(dataset_manifest_hash: str) -> dict:
    return {
        "schema_version": "experiment-v1",
        "experiment_id": "core-role-test",
        "core": True,
        "tasks": [f"task-{index}" for index in range(12)],
        "conditions": [
            "no_memory",
            "raw_trace",
            "structured",
            "selective_structured",
        ],
        "repetitions": 2,
        "model": "mock",
        "embedding_revision": "test-revision",
        "dataset_manifest_hash": dataset_manifest_hash,
    }


def _ready_live_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-rendered")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": "a" * 40, "clean": True},
    )
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
        lambda: {"installed": True, "version": "2.47.0"},
    )
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 7, 29, 2, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")


def _retry_qualification(
    *,
    retry_episode_count: int,
    verified_retry_count: int,
    failed_source_failure_sequences: list[int],
    check_count: int = 1,
    check_passed: bool = True,
) -> dict:
    return {
        "run_id": "run_diagnostic",
        "qualified": True,
        "trace_integrity_passed": True,
        "evaluation_reached": True,
        "qualification_hash": "sha256:" + ("d" * 64),
        "trace_features": {
            "rejected_patch_retry_context": {
                "check_count": check_count,
                "check_passed": check_passed,
                "rejected_candidate_count": retry_episode_count,
                "retry_episode_count": retry_episode_count,
                "verified_retry_count": verified_retry_count,
                "failed_source_failure_sequences": (
                    failed_source_failure_sequences
                ),
            }
        },
    }


def test_expected_runtime_contract_hash_uses_phase_evidence_v3() -> None:
    encoded = json.dumps(
        {
            "system_prompt": eval_runner.SYSTEM_PROMPT_V2,
            "tools": eval_runner.TOOL_SCHEMAS_V2,
            "tool_schema_version": "v2",
            "context_policy_version": "phase-evidence-v3",
        },
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")

    assert eval_runner._expected_runtime_contract_hash() == sha256_bytes(encoded)


def test_live_campaign_approval_is_an_invocation_preflight_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite = eval_runner.load_suite("experiments/dev-validation-pilot.template.yaml")
    assert suite.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT

    unapproved = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    blocker_codes = {row["code"] for row in unapproved["blockers"]}
    assert blocker_codes == {"LIVE_COST_NOT_APPROVED", "APPROVAL_HASH_MISMATCH"}
    assert "test-secret-never-rendered" not in json.dumps(unapproved)

    approved = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml",
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )
    assert approved["ready"] is True
    assert approved["execution_hash"] == unapproved["execution_hash"]


def test_gpt54mini_pilot_has_exact_model_budget_and_pricing_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-validation-gpt54mini-pilot-r2.yaml"

    unapproved = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in unapproved["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert unapproved["purpose"] == (
        "development-validation-model-candidate-pilot"
    )
    assert unapproved["suite"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert unapproved["suite"]["budget"]["max_total_tokens"] == 90_000
    assert unapproved["suite"]["max_output_tokens"] == 4096
    assert unapproved["pricing"]["input_price_per_million_usd"] == 0.75
    assert unapproved["pricing"]["cached_input_price_per_million_usd"] == 0.075
    assert unapproved["pricing"]["cache_write_input_price_per_million_usd"] is None
    assert unapproved["pricing"]["output_price_per_million_usd"] == 4.5
    assert unapproved["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        (90_000 + 4096) * 4.5 / 1_000_000
    )

    approved = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )
    assert approved["ready"] is True


def test_d037_r3_pilot_binds_exact_diagnostic_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    r1 = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-pilot.yaml"
    )
    r2 = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-pilot-r2.yaml"
    )
    suite_path = "experiments/dev-validation-gpt54mini-d037-r3.yaml"
    r3 = eval_runner.load_suite(suite_path)

    assert r1.diagnostic is None
    assert r2.diagnostic is None
    assert r3.diagnostic is not None
    assert r3.diagnostic.profile == "d037-rejected-patch-retry-v1"
    assert r3.diagnostic.required_trace_features == [
        "rejected_patch_retry_context"
    ]
    historical_payload = r2.model_dump(mode="json")
    historical_payload.pop("diagnostic")
    assert eval_runner._suite_hash(r2) == sha256_text(
        canonical_json(historical_payload)
    )
    r2_yaml = yaml.safe_load(
        Path(
            "experiments/dev-validation-gpt54mini-pilot-r2.yaml"
        ).read_text(encoding="utf-8")
    )
    r3_yaml = yaml.safe_load(
        Path(suite_path).read_text(encoding="utf-8")
    )
    r3_yaml.pop("diagnostic")
    r3_yaml["experiment_id"] = r2_yaml["experiment_id"]
    assert r3_yaml == r2_yaml

    preflight = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in preflight["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["suite"]["diagnostic"] == {
        "schema_version": "experiment-diagnostic-v1",
        "profile": "d037-rejected-patch-retry-v1",
        "required_trace_features": [
            "rejected_patch_retry_context"
        ],
    }


def test_d037_r4_binds_corrective_output_allowance_and_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-validation-gpt54mini-d037-r4.yaml"

    suite = eval_runner.load_suite(suite_path)

    assert suite.diagnostic is not None
    assert suite.diagnostic.profile == "d037-rejected-patch-retry-v2"
    assert suite.max_output_tokens == 25_000
    assert suite.budget.max_total_tokens == 120_000
    assert suite.estimated_cost_usd == pytest.approx(0.66)

    preflight = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in preflight["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["suite"]["diagnostic"]["profile"] == (
        "d037-rejected-patch-retry-v2"
    )
    assert preflight["suite"]["max_output_tokens"] == 25_000
    assert preflight["suite"]["budget"]["max_total_tokens"] == 120_000
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        (120_000 + 25_000) * 4.5 / 1_000_000
    )
    assert preflight["pricing"]["budget_upper_bound_usd"] == pytest.approx(
        0.6525
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_output_tokens", 4096),
        ("budget", {"max_total_tokens": 90_000}),
        (
            "diagnostic",
            {
                "schema_version": "experiment-diagnostic-v1",
                "profile": "d037-rejected-patch-retry-v1",
                "required_trace_features": [
                    "rejected_patch_retry_context"
                ],
            },
        ),
    ],
)
def test_d037_r4_rejects_partial_corrective_contract(
    field: str,
    value: object,
) -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r4.yaml").read_text(
            encoding="utf-8"
        )
    )
    if field == "budget":
        payload["budget"].update(value)
    else:
        payload[field] = value

    with pytest.raises(ValidationError):
        ExperimentSuite.model_validate(payload)


def test_d037_diagnostic_is_rejected_outside_model_candidate_pilot() -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["purpose"] = "development-validation-live-pilot"

    with pytest.raises(
        ValidationError,
        match="diagnostic profiles are allowed only",
    ):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize(
    "required_features",
    [
        [
            "rejected_patch_retry_context",
            "rejected_patch_retry_context",
        ],
        ["unknown_feature"],
    ],
)
def test_d037_diagnostic_rejects_invalid_feature_contract(
    required_features: list[str],
) -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["diagnostic"]["required_trace_features"] = required_features

    with pytest.raises(ValidationError):
        ExperimentSuite.model_validate(payload)


def test_d037_diagnostic_removal_invalidates_approved_execution_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["experiment_id"] = "d037-hash-binding"
    suite_path = tmp_path / "d037-hash-binding.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    diagnostic_preflight = eval_runner.preflight_suite(suite_path)
    payload.pop("diagnostic")
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    modified_preflight = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=diagnostic_preflight["execution_hash"],
    )

    assert (
        modified_preflight["execution_hash"]
        != diagnostic_preflight["execution_hash"]
    )
    assert "APPROVAL_HASH_MISMATCH" in {
        row["code"] for row in modified_preflight["blockers"]
    }

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail(
                "changed diagnostic contract must stop before runner creation"
            )

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="approved execution hash"):
        eval_runner.evaluate_suite(
            suite_path,
            approve_live_cost=True,
            approved_execution_hash=diagnostic_preflight[
                "execution_hash"
            ],
        )
    assert not (
        tmp_path
        / "runtime"
        / "experiments"
        / "journals"
        / "d037-hash-binding.jsonl"
    ).exists()


@pytest.mark.parametrize(
    ("qualification", "expected_status", "expected_reason"),
    [
        (
            _retry_qualification(
                retry_episode_count=1,
                verified_retry_count=1,
                failed_source_failure_sequences=[],
            ),
            "passed",
            None,
        ),
        (
            _retry_qualification(
                retry_episode_count=0,
                verified_retry_count=0,
                failed_source_failure_sequences=[],
            ),
            "inconclusive",
            "retry_episode_not_observed",
        ),
        (
            _retry_qualification(
                retry_episode_count=2,
                verified_retry_count=1,
                failed_source_failure_sequences=[42],
            ),
            "failed",
            "retry_episode_not_fully_verified",
        ),
        (
            {
                **_retry_qualification(
                    retry_episode_count=1,
                    verified_retry_count=1,
                    failed_source_failure_sequences=[],
                ),
                "evaluation_reached": False,
            },
            "failed",
            "evaluation_not_reached",
        ),
    ],
)
def test_d037_diagnostic_truth_table(
    qualification: dict,
    expected_status: str,
    expected_reason: str | None,
) -> None:
    suite = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-d037-r3.yaml"
    )

    diagnostic = eval_runner._diagnostic_result(suite, qualification)

    assert diagnostic is not None
    assert diagnostic["status"] == expected_status
    assert diagnostic["reason_code"] == expected_reason


def test_d037_diagnostic_rejects_missing_or_duplicate_qualification_check() -> None:
    suite = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-d037-r3.yaml"
    )

    missing = _retry_qualification(
        retry_episode_count=1,
        verified_retry_count=1,
        failed_source_failure_sequences=[],
        check_count=0,
    )
    duplicate = _retry_qualification(
        retry_episode_count=1,
        verified_retry_count=1,
        failed_source_failure_sequences=[],
        check_count=2,
    )
    unqualified = _retry_qualification(
        retry_episode_count=1,
        verified_retry_count=1,
        failed_source_failure_sequences=[],
    )
    unqualified["qualified"] = False

    assert eval_runner._diagnostic_result(
        suite,
        missing,
    )["reason_code"] == "qualification_check_cardinality"
    assert eval_runner._diagnostic_result(
        suite,
        duplicate,
    )["reason_code"] == "qualification_check_cardinality"
    assert eval_runner._diagnostic_result(
        suite,
        unqualified,
    )["reason_code"] == "qualification_not_passed"


def test_d037_qualification_summary_does_not_copy_malformed_bodies(
    monkeypatch,
) -> None:
    secret_body = "PRIVATE_PATCH_OR_ERROR_BODY"
    monkeypatch.setattr(
        trace_qualification,
        "qualify_run",
        lambda *_args, **_kwargs: {
            "qualified": True,
            "checks": [
                {
                    "check_id": "rejected_patch_retry_context",
                    "passed": secret_body,
                    "details": {
                        "rejected_candidate_count": secret_body,
                        "retry_episode_count": secret_body,
                        "verified_retry_count": secret_body,
                        "failed_source_failure_sequences": [
                            secret_body
                        ],
                    },
                }
            ],
        },
    )

    summary = eval_runner._qualify_terminal_run(
        "run_sanitized",
        "tasks/dev-validation/"
        "babel-strict-grouped-decimal-trailing-zeroes/public.yaml",
    )
    feature = summary["trace_features"][
        "rejected_patch_retry_context"
    ]

    assert feature["check_count"] == 1
    assert feature["check_passed"] is None
    assert feature["rejected_candidate_count"] is None
    assert feature["retry_episode_count"] is None
    assert feature["verified_retry_count"] is None
    assert feature["failed_source_failure_sequences"] is None
    assert secret_body not in json.dumps(summary)


def test_gpt54mini_corrective_retry_preserves_terminal_r1_contract() -> None:
    terminal = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot.yaml").read_text(
            encoding="utf-8"
        )
    )
    retry = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot-r2.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert terminal["experiment_id"] == (
        "dev-validation-gpt54mini-pilot-20260729-r1"
    )
    assert retry["experiment_id"] == (
        "dev-validation-gpt54mini-pilot-20260729-r2"
    )
    assert retry["live_cost_approved"] is False
    assert retry["approved_execution_hash"] is None
    ignored = {"experiment_id", "pricing_verified_at"}
    assert {
        key: value for key, value in terminal.items() if key not in ignored
    } == {
        key: value for key, value in retry.items() if key not in ignored
    }


def test_gpt54mini_pilot_rejects_non_frozen_token_budget() -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot-r2.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["budget"]["max_total_tokens"] = 80_000

    with pytest.raises(ValidationError, match="max_total_tokens=90000"):
        ExperimentSuite.model_validate(payload)


def test_gpt54mini_pilot_preflight_rejects_wrong_price(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot-r2.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["experiment_id"] = "gpt54mini-wrong-price"
    payload["input_price_per_million_usd"] = 2.5
    suite_path = tmp_path / "gpt54mini-wrong-price.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    preflight = eval_runner.preflight_suite(suite_path)

    assert "PRICING_RATE_MISMATCH" in {
        row["code"] for row in preflight["blockers"]
    }


def test_v2_development_campaign_has_exact_twelve_run_matrix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite("experiments/dev-no-memory.template.yaml")

    assert preflight["purpose"] == "memory-development-no-memory"
    assert preflight["expected_runs"] == 12
    assert len({row["schedule_row_id"] for row in preflight["schedule"]}) == 12
    assert {row["dataset_role"] for row in preflight["tasks"]} == {
        "memory-development"
    }
    assert {row["condition"] for row in preflight["schedule"]} == {"no_memory"}
    assert {row["repetition"] for row in preflight["schedule"]} == {1, 2}
    assert {
        row["code"] for row in preflight["blockers"]
    } == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
        "QUALIFIED_PILOT_REQUIRED",
    }


def test_development_campaign_rejects_stale_pilot_source_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-no-memory.template.yaml").read_text(encoding="utf-8")
    )
    suite_payload["experiment_id"] = "dev-stale-pilot-source"
    suite_payload["pilot_run_id"] = "run_qualified_pilot"
    suite_path = tmp_path / "dev-stale-pilot-source.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    stored_source_hash = "sha256:" + ("a" * 64)
    monkeypatch.setattr(
        trace_qualification,
        "load_trace_qualification",
        lambda *_args, **_kwargs: {
            "run_id": "run_qualified_pilot",
            "purpose": "development-validation-live-pilot",
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("c" * 64),
            "source_evidence_hash": stored_source_hash,
            "outcome_kind": "resolved",
        },
    )
    monkeypatch.setattr(
        trace_qualification,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: "sha256:" + ("b" * 64),
    )

    preflight = eval_runner.preflight_suite(suite_path)

    assert "QUALIFIED_PILOT_REQUIRED" in {
        row["code"] for row in preflight["blockers"]
    }
    assert preflight["pilot_qualification"]["qualified"] is False
    assert preflight["pilot_qualification"]["reason"] == (
        "pilot source evidence hash mismatch"
    )


def test_model_candidate_pilot_cannot_unlock_terra_development_campaign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-no-memory.template.yaml").read_text(encoding="utf-8")
    )
    suite_payload["experiment_id"] = "dev-reject-model-candidate-pilot"
    suite_payload["pilot_run_id"] = "run_model_candidate_pilot"
    suite_path = tmp_path / "dev-reject-model-candidate-pilot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    source_hash = "sha256:" + ("a" * 64)
    monkeypatch.setattr(
        trace_qualification,
        "load_trace_qualification",
        lambda *_args, **_kwargs: {
            "run_id": "run_model_candidate_pilot",
            "purpose": "development-validation-model-candidate-pilot",
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("c" * 64),
            "source_evidence_hash": source_hash,
            "outcome_kind": "resolved",
        },
    )
    monkeypatch.setattr(
        trace_qualification,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: source_hash,
    )

    preflight = eval_runner.preflight_suite(suite_path)

    assert preflight["pilot_qualification"]["qualified"] is False
    assert "QUALIFIED_PILOT_REQUIRED" in {
        row["code"] for row in preflight["blockers"]
    }


def test_legacy_runtime_pilot_cannot_unlock_v2_development_campaign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-no-memory.template.yaml").read_text(
            encoding="utf-8"
        )
    )
    suite_payload["experiment_id"] = "dev-reject-v1-runtime-pilot"
    suite_payload["pilot_run_id"] = "run_v1_runtime_pilot"
    suite_path = tmp_path / "dev-reject-v1-runtime-pilot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    source_hash = "sha256:" + ("a" * 64)
    monkeypatch.setattr(
        trace_qualification,
        "load_trace_qualification",
        lambda *_args, **_kwargs: {
            "schema_version": "trace-qualification-v1",
            "run_id": "run_v1_runtime_pilot",
            "purpose": "development-validation-live-pilot",
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("c" * 64),
            "source_evidence_hash": source_hash,
            "outcome_kind": "resolved",
            "model_provider": "openai",
            "memory_condition": "no_memory",
            "fault_type": "none",
        },
    )
    monkeypatch.setattr(
        trace_qualification,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: source_hash,
    )

    preflight = eval_runner.preflight_suite(suite_path)

    pilot = preflight["pilot_qualification"]
    assert pilot["qualified"] is False
    assert "schema_version" in pilot["contract_mismatches"]
    assert "tool_schema_version" in pilot["contract_mismatches"]
    assert "runtime_contract_content_hash" in pilot["contract_mismatches"]
    assert "QUALIFIED_PILOT_REQUIRED" in {
        row["code"] for row in preflight["blockers"]
    }


def test_v2_development_campaign_rejects_an_incomplete_task_set() -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-no-memory.template.yaml").read_text(encoding="utf-8")
    )
    payload["tasks"] = payload["tasks"][:-1]

    with pytest.raises(ValidationError, match="six frozen development tasks"):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize("mutation", ["path", "private", "environment"])
def test_live_preflight_binds_canonical_private_evaluator_package(
    tmp_path: Path,
    monkeypatch,
    mutation: str,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    original_loader = eval_runner.load_task_package
    package = original_loader(Path(eval_runner.PILOT_TASK).parent)
    if mutation == "path":
        forged = package.model_copy(update={"root": str(tmp_path / "forged-task")})
    elif mutation == "private":
        forged = package.model_copy(
            update={"private_spec_hash": "sha256:" + ("f" * 64)}
        )
    else:
        forged = package.model_copy(update={"environment": None})
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _path: forged)

    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )

    blockers = {row["code"] for row in preflight["blockers"]}
    assert "TASK_NOT_ELIGIBLE" in blockers
    assert preflight["tasks"] == []


def test_blocked_preflight_happens_before_agent_construction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("AgentRunner must not be constructed before live approval")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="explicit --approve-live-cost"):
        eval_runner.evaluate_suite("experiments/dev-validation-pilot.template.yaml")


def test_approved_pilot_persists_plan_manifest_and_qualification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    byte_writes: dict[Path, bytes] = {}
    original_write_bytes = Path.write_bytes

    def record_write_bytes(path: Path, content: bytes) -> int:
        byte_writes[path] = content
        return original_write_bytes(path, content)

    monkeypatch.setattr(Path, "write_bytes", record_write_bytes)
    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    captured = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            captured.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "usage": {
                    "model_cost_usd": 0.5,
                    "model_calls": 2,
                    "tool_calls": 1,
                    "input_tokens": 100,
                    "output_tokens": 20,
                },
            }

    qualification_hash = "sha256:" + ("e" * 64)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": qualification_hash,
        },
    )

    result = eval_runner.evaluate_suite(
        "experiments/dev-validation-pilot.template.yaml",
        approve_live_cost=True,
        approved_execution_hash=preflight["execution_hash"],
    )

    assert len(captured) == 1
    assert captured[0].experiment.purpose == (
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
    )
    assert captured[0].experiment.execution_hash == result["execution_hash"]
    assert result["runs"][0]["qualification"]["qualification_hash"] == qualification_hash
    plan_path = Path(result["execution_plan"]["path"])
    assert plan_path.is_file()
    assert json.loads(plan_path.read_text(encoding="utf-8"))["schema_version"] == (
        "experiment-execution-plan-v1"
    )
    journal_rows = [
        json.loads(line)
        for line in Path(result["campaign_journal"]["path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == [
        "CampaignStarted",
        "RunStarted",
        "RunTerminal",
        "CampaignCompleted",
    ]
    assert journal_rows[1]["payload"]["run_id"] == result["runs"][0]["run_id"]
    temporary_result_path = Path(result["path"]).with_suffix(".json.tmp")
    assert byte_writes[temporary_result_path] == Path(result["path"]).read_bytes()
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        byte_writes[temporary_result_path]
    )
    previous_hash = None
    for sequence, row in enumerate(journal_rows, start=1):
        recorded_hash = row.pop("event_hash")
        assert row["sequence"] == sequence
        assert row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(row)) == recorded_hash
        previous_hash = recorded_hash
    retry = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    assert {
        "EXPERIMENT_RESULT_EXISTS",
        "EXPERIMENT_JOURNAL_EXISTS",
    }.issubset({row["code"] for row in retry["blockers"]})


def test_d037_pilot_keeps_inconclusive_exercise_separate_from_qualification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["experiment_id"] = "d037-inconclusive-integration"
    suite_path = tmp_path / "d037-inconclusive-integration.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    preflight = eval_runner.preflight_suite(suite_path)

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "usage": {
                    "model_cost_usd": 0.0,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "input_tokens": 10,
                    "output_tokens": 5,
                },
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            **_retry_qualification(
                retry_episode_count=0,
                verified_retry_count=0,
                failed_source_failure_sequences=[],
            ),
            "run_id": run_id,
        },
    )

    result = eval_runner.evaluate_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=preflight["execution_hash"],
    )
    run = result["runs"][0]

    assert run["qualification"]["qualified"] is True
    assert run["qualification_error"] is None
    assert run["diagnostic"]["status"] == "inconclusive"
    assert run["diagnostic_error"]["type"] == "TraceExerciseInconclusive"
    assert result["qualification_errors"] == 0
    assert result["diagnostic_errors"] == 1
    assert result["diagnostic_gate"] == {
        "profile": "d037-rejected-patch-retry-v1",
        "required_trace_features": [
            "rejected_patch_retry_context"
        ],
        "passed": False,
        "passed_runs": 0,
        "inconclusive_runs": 1,
        "failed_runs": 0,
    }


def test_paid_execution_uses_the_suite_snapshot_approved_by_preflight(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-validation-pilot.template.yaml").read_text(
            encoding="utf-8"
        )
    )
    suite_payload["experiment_id"] = "pilot-suite-snapshot"
    suite_path = tmp_path / "pilot-suite-snapshot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    approved = eval_runner.preflight_suite(suite_path)
    original_preflight = eval_runner.preflight_suite

    def preflight_then_replace_suite(*args, **kwargs):
        preflight = original_preflight(*args, **kwargs)
        replaced = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
        replaced["experiment_id"] = "pilot-suite-snapshot-replaced"
        suite_path.write_text(
            yaml.safe_dump(replaced, sort_keys=False),
            encoding="utf-8",
        )
        return preflight

    captured = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_kwargs):
            captured.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "usage": {"model_cost_usd": 0.0},
            }

    monkeypatch.setattr(eval_runner, "preflight_suite", preflight_then_replace_suite)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("e" * 64),
        },
    )

    result = eval_runner.evaluate_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=approved["execution_hash"],
    )

    assert result["experiment_id"] == "pilot-suite-snapshot"
    assert len(captured) == 1
    assert captured[0].experiment.experiment_id == "pilot-suite-snapshot"
    assert captured[0].model.model_id == "gpt-5.6-terra"


def test_paid_execution_rejects_task_package_replacement_before_run_start(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-validation-pilot.template.yaml").read_text(
            encoding="utf-8"
        )
    )
    suite_payload["experiment_id"] = "pilot-task-snapshot"
    suite_path = tmp_path / "pilot-task-snapshot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    approved = eval_runner.preflight_suite(suite_path)
    original_loader = eval_runner.load_task_package
    replace_task = False

    def mark_post_preflight(_preflight):
        nonlocal replace_task
        replace_task = True

    def load_replaced_task(path):
        package = original_loader(path)
        if not replace_task:
            return package
        return package.model_copy(
            update={"private_spec_hash": "sha256:" + ("f" * 64)}
        )

    class FakeRunner:
        def start(self, *_args, **_kwargs):
            pytest.fail("replaced task package must not reach the model runner")

    monkeypatch.setattr(
        eval_runner,
        "_assert_live_environment_unchanged",
        mark_post_preflight,
    )
    monkeypatch.setattr(eval_runner, "load_task_package", load_replaced_task)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)

    with pytest.raises(ContractError, match="task package changed"):
        eval_runner.evaluate_suite(
            suite_path,
            approve_live_cost=True,
            approved_execution_hash=approved["execution_hash"],
        )

    journal_path = Path(approved["journal_path"])
    journal_rows = [
        json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == ["CampaignStarted"]


def test_hard_crash_journal_blocks_duplicate_paid_schedule(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )

    class CrashingRunner:
        def start(self, *_args, **_kwargs):
            raise SystemExit("synthetic hard crash after durable row start")

    monkeypatch.setattr(eval_runner, "AgentRunner", CrashingRunner)
    with pytest.raises(SystemExit, match="synthetic hard crash"):
        eval_runner.evaluate_suite(
            "experiments/dev-validation-pilot.template.yaml",
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )

    retry = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    assert "EXPERIMENT_JOURNAL_EXISTS" in {
        row["code"] for row in retry["blockers"]
    }
    journal_rows = [
        json.loads(line)
        for line in Path(retry["journal_path"]).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == [
        "CampaignStarted",
        "RunStarted",
    ]


def test_atomic_journal_claim_blocks_a_racing_paid_invocation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    journal_path = Path(preflight["journal_path"])

    def claim_journal_after_preflight(_preflight):
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        journal_path.write_text("claimed-by-racing-invocation\n", encoding="utf-8")

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("a losing journal claimant must not construct AgentRunner")

    monkeypatch.setattr(
        eval_runner,
        "_assert_live_environment_unchanged",
        claim_journal_after_preflight,
    )
    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    monkeypatch.setattr(
        eval_runner,
        "issue_live_execution_authorization",
        lambda *_args, **_kwargs: pytest.fail(
            "a losing journal claimant must not receive live authorization"
        ),
    )

    with pytest.raises(ContractError, match="duplicate schedule ownership"):
        eval_runner.evaluate_suite(
            "experiments/dev-validation-pilot.template.yaml",
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )

    assert journal_path.read_text(encoding="utf-8") == (
        "claimed-by-racing-invocation\n"
    )


def test_environment_drift_after_preflight_stops_before_agent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    commits = iter(["a" * 40, "a" * 40, "b" * 40])
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": next(commits), "clean": True},
    )
    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("environment drift must stop before AgentRunner construction")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="changed after the approved preflight"):
        eval_runner.evaluate_suite(
            "experiments/dev-validation-pilot.template.yaml",
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )


@pytest.mark.parametrize("model", ["openai", "gpt-5.6-terra", "unknown-provider"])
def test_direct_openai_run_is_blocked_before_adapter_construction(
    monkeypatch,
    model: str,
) -> None:
    def forbidden_run(*_, **__):
        pytest.fail("direct live run must not reach run_from_cli")

    monkeypatch.setattr("patchloop.agent.runner.run_from_cli", forbidden_run)
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--task",
            "tasks/smoke/csv-quoted-newline/public.yaml",
            "--model",
            model,
        ],
    )

    assert result.exit_code == 1
    assert "direct live runs are disabled" in result.stdout


def test_core_campaign_requires_exact_design() -> None:
    with pytest.raises(ValidationError, match="12 unique"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=["task"],
            conditions=["no_memory"],
            model="mock",
        )


def test_core_campaign_requires_dataset_manifest_hash() -> None:
    with pytest.raises(ValidationError, match="dataset manifest hash"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=[f"task-{index}" for index in range(12)],
            conditions=[
                "no_memory",
                "raw_trace",
                "structured",
                "selective_structured",
            ],
            repetitions=2,
            model="mock",
            embedding_revision="test-revision",
        )


def test_offline_smoke_remains_a_calibration_suite() -> None:
    suite = eval_runner.load_suite("experiments/smoke.yaml")
    assert suite.core is False
    assert suite.purpose == ExperimentPurpose.OFFLINE_SMOKE
    assert suite.dataset_manifest_hash is None


def test_core_campaign_rejects_calibration_registry_role(tmp_path, monkeypatch) -> None:
    package = load_task_package("tasks/dev-train/duration-minute-boundary")
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(dataset[1]), sort_keys=False),
        encoding="utf-8",
    )
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _: package)

    with pytest.raises(ContractError, match="dataset role calibration is not eligible"):
        eval_runner.evaluate_suite(suite_path)
    assert preflight_calls == 1


def test_core_campaign_rejects_dataset_manifest_hash_drift(tmp_path, monkeypatch) -> None:
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("f" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_runner, "require_frozen_dataset", lambda: dataset)

    with pytest.raises(ContractError, match="does not match"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_runs_complete_frozen_dataset_preflight_first(
    tmp_path: Path,
    monkeypatch,
) -> None:
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("a" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def reject_incomplete_dataset():
        raise ContractError("core experiment requires a complete frozen dataset")

    def fail_if_task_loading_starts(_):
        pytest.fail("task loading must not start before the frozen-dataset preflight")

    monkeypatch.setattr(
        eval_runner,
        "require_frozen_dataset",
        reject_incomplete_dataset,
    )
    monkeypatch.setattr(eval_runner, "load_task_package", fail_if_task_loading_starts)

    with pytest.raises(ContractError, match="complete frozen dataset"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_schedule_remains_96_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_hash = "sha256:" + ("a" * 64)
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(manifest_hash), sort_keys=False),
        encoding="utf-8",
    )
    dataset = SimpleNamespace(dataset_id="core-role-test")
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset, manifest_hash, tmp_path / "dataset.yaml"

    def fake_load_task_package(path):
        index = int(Path(path).name.removeprefix("task-"))
        split = "same-repo-heldout" if index < 6 else "cross-repo-heldout"
        public = SimpleNamespace(
            task_id=f"task-{index}",
            task_version=1,
            split=split,
            repository=SimpleNamespace(base_commit=f"{index:040x}"),
        )
        image_digest = "sha256:" + f"{index + 200:064x}"
        return SimpleNamespace(
            public=public,
            root=str((eval_runner.repository_root() / f"task-{index}").resolve()),
            public_spec_hash="sha256:" + f"{index:064x}",
            private_spec_hash="sha256:" + f"{index + 100:064x}",
            environment=SimpleNamespace(
                evaluator_image=f"example.invalid/task-{index}@{image_digest}",
                image_digest=image_digest,
            ),
        )

    def fake_require_dataset_role(*, task_id, **_):
        index = int(task_id.removeprefix("task-"))
        role = (
            DatasetRole.CORE_SAME_REPO
            if index < 6
            else DatasetRole.CORE_CROSS_REPO
        )
        return SimpleNamespace(
            role=role,
            path=f"task-{index}",
            private_spec_hash="sha256:" + f"{index + 100:064x}",
        )

    index_path = tmp_path / "memory-index.json"
    index_path.write_text(
        json.dumps(
            {
                "entries": [{"memory_id": "mem_test"}],
                "embedding": {
                    "implementation": "sentence-transformers",
                    "revision": "test-revision",
                },
                "dataset_manifest_hash": manifest_hash,
            }
        ),
        encoding="utf-8",
    )

    starts: list[tuple[str, object]] = []

    class FakeRunner:
        def start(self, task, *, memory_condition, **_):
            starts.append((task, memory_condition))
            return {"usage": {"model_cost_usd": 0.0}}

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", fake_load_task_package)
    monkeypatch.setattr(eval_runner, "require_dataset_role", fake_require_dataset_role)
    monkeypatch.setattr(eval_runner, "latest_frozen_index", lambda: index_path)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda *_: pytest.fail("core runs must not use the development qualifier"),
    )

    result = eval_runner.evaluate_suite(suite_path)

    assert preflight_calls == 1
    assert result["expected_runs"] == 96
    assert result["completed_runs"] == 96
    assert result["infrastructure_errors"] == 0
    assert len(result["runs"]) == 96
    assert len(starts) == 96
    assert result["qualification_errors"] == 0
    assert Path(result["execution_plan"]["path"]).is_file()
    assert {row["task_id"] for row in result["runs"]} == {
        f"task-{index}" for index in range(12)
    }
    assert {
        row["condition"] for row in result["runs"]
    } == {
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    }
    assert {row["repetition"] for row in result["runs"]} == {1, 2}


def test_core_campaign_rejects_memory_index_from_another_dataset() -> None:
    suite = ExperimentSuite.model_validate(_core_suite_payload("sha256:" + ("a" * 64)))
    index_payload = {
        "entries": [{"memory_id": "mem_test"}],
        "embedding": {
            "implementation": "sentence-transformers",
            "revision": "test-revision",
        },
        "dataset_manifest_hash": "sha256:" + ("b" * 64),
    }

    with pytest.raises(ContractError, match="memory index dataset manifest hash"):
        eval_runner._validate_memory_index(index_payload, suite)


def test_infrastructure_outcome_halts_and_preserves_not_started_ledger(
    tmp_path: Path,
    monkeypatch,
) -> None:
    suite_path = tmp_path / "offline-two-task.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "experiment-v2",
                "experiment_id": "offline-infrastructure-halt",
                "purpose": "offline-smoke",
                "tasks": [
                    "tasks/smoke/csv-quoted-newline/public.yaml",
                    "tasks/smoke/config-falsy-override/public.yaml",
                ],
                "conditions": ["no_memory"],
                "repetitions": 1,
                "model": "mock",
                "model_id": "mock-v1",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    captured_manifests = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            captured_manifests.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "infrastructure_error",
                "terminal_error": {
                    "type": "ProviderUnavailable",
                    "message": "synthetic provider failure",
                },
                "usage": {
                    "model_cost_usd": 0.125,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "input_tokens": 50,
                    "output_tokens": 0,
                },
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda *_: pytest.fail("offline smoke must not use the development qualifier"),
    )

    result = eval_runner.evaluate_suite(suite_path)

    assert len(captured_manifests) == 1
    assert captured_manifests[0].experiment is not None
    assert captured_manifests[0].experiment.execution_hash == result["execution_hash"]
    assert result["actual_model_cost_usd"] == 0.125
    assert result["infrastructure_errors"] == 1
    assert result["not_started_runs"] == 1
    assert len(result["runs"]) == 2
    assert result["runs"][0]["run_id"] == captured_manifests[0].run_id
    assert result["runs"][0]["usage"]["model_calls"] == 1
    assert result["runs"][1]["attempt_status"] == "not_started"
    assert result["runs"][1]["run_id"] is None
    assert result["runs"][1]["not_started_reason"]["type"] == "InfrastructureFailureHalt"
