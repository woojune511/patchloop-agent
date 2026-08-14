from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_completion import (
    heldout_ac_campaign_cost_control_hash,
    heldout_ac_schedule_row_id,
)
from patchloop.evals.heldout_ac_execution import (
    MATERIALIZATION_PATH,
    HeldoutACExecutionCandidate,
    HeldoutACFileBinding,
    HeldoutACSourceQualificationBinding,
    build_heldout_ac_execution_candidate,
    build_heldout_ac_no_call_readiness,
    build_heldout_ac_run_manifest,
    candidate_json,
    encode_heldout_ac_runtime_secret,
    materialize_heldout_ac_runtime_task_authority,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json
from patchloop.verifier.receipt import validate_evaluator_v2_manifest_authority

ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
QUALIFICATION_HASH = "sha256:" + "a" * 64
EVALUATOR_SOURCE_HASH = "sha256:" + "b" * 64


def _source_qualification() -> HeldoutACSourceQualificationBinding:
    return HeldoutACSourceQualificationBinding(
        schema_version="heldout-ac-execution-source-qualification-binding-v1",
        qualification_id="heldout-ac-execution-test-r1",
        qualification_file=HeldoutACFileBinding(
            path="reports/heldout-ac/artifacts/test-source-qualification.json",
            file_bytes=1,
            file_sha256="sha256:" + "c" * 64,
            content_hash=QUALIFICATION_HASH,
        ),
        source_qualification_hash=QUALIFICATION_HASH,
        evaluator_source_hash=EVALUATOR_SOURCE_HASH,
        source_replay_valid=True,
        provider_evaluator_agent_calls_made=0,
    )


def _image_identities() -> list[tuple[str, str]]:
    payload = json.loads((ROOT / MATERIALIZATION_PATH).read_text(encoding="utf-8"))
    return sorted(
        {
            (
                item["task"]["evaluator_image"],
                item["task"]["evaluator_image_digest"],
            )
            for item in payload["task_bindings"]
        }
    )


def _candidate() -> HeldoutACExecutionCandidate:
    readiness = build_heldout_ac_no_call_readiness(
        observed_at=datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
        git_commit="1" * 40,
        git_tree="2" * 40,
        docker_images=_image_identities(),
        openai_sdk_version="9.9.9-test",
        credential_present=True,
        custom_base_url_present=False,
    )
    return build_heldout_ac_execution_candidate(
        readiness=readiness,
        source_qualification=_source_qualification(),
        repository=ROOT,
    )


def test_candidate_binds_exact_48_rows_without_live_authority() -> None:
    suite = load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    candidate = _candidate()

    assert candidate.status == "NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED"
    assert len(candidate.schedule) == 48
    assert candidate.source_qualification.source_qualification_hash == QUALIFICATION_HASH
    assert candidate.full_schedule_reserve_usd == 252.0
    assert candidate.hard_cap_usd == 275.0
    assert candidate.exact_paid_approval_present is False
    assert candidate.provider_execution_authorized is False
    assert candidate.cost_reservation_or_spend_authorized is False
    assert candidate.schedule[0].schedule_row_id == heldout_ac_schedule_row_id(
        suite=suite,
        execution_hash=candidate.execution_hash,
        order=1,
    )
    assert candidate.campaign_cost_control.content_hash == (
        heldout_ac_campaign_cost_control_hash(
            suite=suite,
            execution_hash=candidate.execution_hash,
            schedule_hash=candidate.schedule_hash,
        )
    )


def test_candidate_is_deterministic_and_secret_free() -> None:
    first = _candidate()
    second = _candidate()
    assert first == second
    serialized = candidate_json(first)
    assert "OPENAI_API_KEY" in serialized
    assert "value_observed_or_serialized" in serialized
    assert "test-runtime-secret" not in serialized
    assert first.execution_hash == second.execution_hash


def test_readiness_rejects_missing_credential_or_custom_base_url() -> None:
    common = {
        "observed_at": datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
        "git_commit": "1" * 40,
        "git_tree": "2" * 40,
        "docker_images": _image_identities(),
        "openai_sdk_version": "9.9.9-test",
    }
    with pytest.raises(ContractError, match="credential presence boundary"):
        build_heldout_ac_no_call_readiness(
            **common,
            credential_present=False,
            custom_base_url_present=False,
        )
    with pytest.raises(ContractError, match="credential presence boundary"):
        build_heldout_ac_no_call_readiness(
            **common,
            credential_present=True,
            custom_base_url_present=True,
        )


def test_candidate_rejects_incomplete_docker_image_set() -> None:
    readiness = build_heldout_ac_no_call_readiness(
        observed_at=datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
        git_commit="1" * 40,
        git_tree="2" * 40,
        docker_images=_image_identities()[:-1],
        openai_sdk_version="9.9.9-test",
        credential_present=True,
        custom_base_url_present=False,
    )
    with pytest.raises(ContractError, match="every evaluator image"):
        build_heldout_ac_execution_candidate(
            readiness=readiness,
            source_qualification=_source_qualification(),
            repository=ROOT,
        )


def test_candidate_rejects_rehashed_schedule_scalar_drift() -> None:
    candidate = _candidate()
    raw = candidate.model_dump(mode="json")
    raw["schedule"][0]["order"] = True
    with pytest.raises(ValidationError):
        HeldoutACExecutionCandidate.model_validate(raw)


@pytest.mark.parametrize("value", ["", 1, None, "x" * 16_385])
def test_runtime_secret_encoder_fails_closed(value: object) -> None:
    with pytest.raises(ContractError):
        encode_heldout_ac_runtime_secret(value)  # type: ignore[arg-type]


def test_runtime_secret_expansion_matches_r4_template_and_builds_manifest() -> None:
    candidate = _candidate()
    row = candidate.schedule[0]
    package = load_task_package(ROOT / row.task_path)
    runtime = materialize_heldout_ac_runtime_task_authority(
        candidate=candidate,
        task_id=row.task_id,
        package=package,
        api_key="test-runtime-secret",
        repository=ROOT,
    )
    manifest = build_heldout_ac_run_manifest(
        candidate=candidate,
        row_order=row.order,
        run_id="run_heldout_contract_test_001",
        created_at=datetime(2026, 8, 14, 10, 1, tzinfo=UTC),
        authority=runtime,
    )

    assert runtime.qualification_authority.runtime.private_markers[-1] == b"test-runtime-secret"
    assert runtime.task_binding.evaluator_contract == manifest.evaluator_contract
    assert manifest.experiment is not None
    assert manifest.experiment.execution_hash == candidate.execution_hash
    assert manifest.experiment.schedule_row_id == row.schedule_row_id
    assert manifest.memory.condition.value == row.condition
    assert manifest.budget.max_cumulative_input_tokens == 4_000_000
    assert (
        validate_evaluator_v2_manifest_authority(
            manifest,
            runtime.qualification_authority,
        )
        == runtime.qualification_authority
    )


def test_manifest_builder_rejects_authority_from_another_task() -> None:
    candidate = _candidate()
    first, second = (
        candidate.schedule[0],
        next(row for row in candidate.schedule if row.task_id != candidate.schedule[0].task_id),
    )
    package = load_task_package(ROOT / second.task_path)
    runtime = materialize_heldout_ac_runtime_task_authority(
        candidate=candidate,
        task_id=second.task_id,
        package=package,
        api_key="test-runtime-secret",
        repository=ROOT,
    )
    with pytest.raises(ContractError, match="another row"):
        build_heldout_ac_run_manifest(
            candidate=candidate,
            row_order=first.order,
            run_id="run_heldout_contract_test_002",
            created_at=datetime(2026, 8, 14, 10, 1, tzinfo=UTC),
            authority=runtime,
        )


def test_source_qualification_binding_rejects_content_mismatch() -> None:
    body = _source_qualification().model_dump(mode="json")
    body["qualification_file"]["content_hash"] = "sha256:" + "d" * 64
    with pytest.raises(ValidationError, match="content binding differs"):
        HeldoutACSourceQualificationBinding.model_validate(body)


def test_no_call_readiness_hash_is_type_sensitive() -> None:
    readiness = _candidate().readiness
    body = readiness.model_dump(mode="json")
    body["provider_calls_made"] = False
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        type(readiness).model_validate(body)
