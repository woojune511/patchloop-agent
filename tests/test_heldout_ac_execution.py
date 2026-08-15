from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.errors import ContractError
from patchloop.evals import heldout_ac_execution as execution
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
    heldout_ac_campaign_identity_hash,
    heldout_ac_candidate_matches_current_execution_inputs,
    heldout_ac_completion_campaign_authority,
    materialize_heldout_ac_runtime_task_authority,
)
from patchloop.evals.heldout_ac_live_contract import (
    heldout_ac_manifest_matches_candidate,
    heldout_ac_runtime_contract,
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


def _rehashed_candidate_payload(
    candidate: HeldoutACExecutionCandidate,
    *,
    updates: dict[str, object],
) -> dict[str, object]:
    provisional = candidate.model_copy(update=updates)
    execution_hash = sha256_json(execution._execution_projection(provisional))
    rebound_schedule = tuple(
        row.model_copy(
            update={
                "schedule_row_id": execution._schedule_row_id(
                    suite_id=candidate.suite_id,
                    suite_content_hash=candidate.suite_content_hash,
                    execution_hash=execution_hash,
                    row=row,
                )
            }
        )
        for row in provisional.schedule
    )
    schedule_hash = sha256_json(execution._runtime_schedule_projection(rebound_schedule))
    cost_body = candidate.campaign_cost_control.model_dump(mode="python", exclude={"content_hash"})
    cost_body.update(
        {
            "execution_hash": execution_hash,
            "schedule_hash": schedule_hash,
        }
    )
    campaign_cost_control = candidate.campaign_cost_control.model_copy(
        update={**cost_body, "content_hash": sha256_json(cost_body)}
    )
    rebuilt = candidate.model_copy(
        update={
            **updates,
            "execution_hash": execution_hash,
            "schedule": rebound_schedule,
            "schedule_hash": schedule_hash,
            "campaign_cost_control": campaign_cost_control,
        }
    )
    return rebuilt.model_dump(mode="python", exclude_none=True)


def _rehashed_candidate_row_payload(
    candidate: HeldoutACExecutionCandidate,
    *,
    field_name: str,
    value: object,
) -> dict[str, object]:
    schedule = list(candidate.schedule)
    schedule[0] = schedule[0].model_copy(update={field_name: value})
    return _rehashed_candidate_payload(
        candidate,
        updates={
            "schedule": tuple(schedule),
            "base_schedule_hash": sha256_json(execution._base_schedule_projection(schedule)),
            "realized_schedule_hash": sha256_json(
                execution._realized_schedule_projection(schedule)
            ),
        },
    )


def _rehashed_candidate_row(
    candidate: HeldoutACExecutionCandidate,
    *,
    field_name: str,
    value: object,
) -> HeldoutACExecutionCandidate:
    return HeldoutACExecutionCandidate.model_validate(
        _rehashed_candidate_row_payload(candidate, field_name=field_name, value=value)
    )


def _rehashed_candidate_runtime_tuple(
    candidate: HeldoutACExecutionCandidate,
) -> HeldoutACExecutionCandidate:
    return HeldoutACExecutionCandidate.model_validate(
        _rehashed_candidate_payload(
            candidate,
            updates={"runtime_tuple_hash": "sha256:" + "8" * 64},
        )
    )


def _legacy_candidate(
    candidate: HeldoutACExecutionCandidate,
    *,
    schema_version: str,
) -> HeldoutACExecutionCandidate:
    if schema_version == "heldout-ac-execution-candidate-v1":
        cost_schema = "heldout-ac-full-schedule-cost-control-v1"
        per_run_reserve_nanos = 5_250_000_000
        full_schedule_reserve_nanos = 252_000_000_000
        hard_cap_nanos = 275_000_000_000
        budget_amendment = None
        materialization = candidate.materialization
        full_schedule_reserve_usd = 252.0
        hard_cap_usd = 275.0
    else:
        cost_schema = "heldout-ac-full-schedule-cost-control-v2"
        per_run_reserve_nanos = 1_200_000_000
        full_schedule_reserve_nanos = 57_600_000_000
        hard_cap_nanos = 60_000_000_000
        budget_amendment = candidate.budget_amendment
        materialization = HeldoutACFileBinding(
            path=execution.LEGACY_MATERIALIZATION_PATH.as_posix(),
            file_bytes=execution.LEGACY_MATERIALIZATION_FILE_BYTES,
            file_sha256=execution.LEGACY_MATERIALIZATION_FILE_SHA256,
            content_hash=execution.LEGACY_MATERIALIZATION_CONTENT_HASH,
        )
        full_schedule_reserve_usd = 57.6
        hard_cap_usd = 60.0
    provisional = candidate.model_copy(
        update={
            "schema_version": schema_version,
            "budget_amendment": budget_amendment,
            "materialization": materialization,
            "realized_schedule_hash": None,
        }
    )
    execution_hash = sha256_json(execution._execution_projection(provisional))
    schedule = tuple(
        row.model_copy(
            update={
                "schedule_row_id": execution._schedule_row_id(
                    suite_id=candidate.suite_id,
                    suite_content_hash=candidate.suite_content_hash,
                    execution_hash=execution_hash,
                    row=row,
                )
            }
        )
        for row in candidate.schedule
    )
    schedule_hash = sha256_json(execution._runtime_schedule_projection(schedule))
    cost_body = {
        "schema_version": cost_schema,
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "execution_hash": execution_hash,
        "schedule_hash": schedule_hash,
        "scheduled_run_count": 48,
        "per_run_reserve_nanos": per_run_reserve_nanos,
        "full_schedule_reserve_nanos": full_schedule_reserve_nanos,
        "hard_cap_nanos": hard_cap_nanos,
        "cost_censoring_allowed": False,
        "live_resume_supported": False,
    }
    rebuilt = candidate.model_copy(
        update={
            "schema_version": schema_version,
            "budget_amendment": budget_amendment,
            "materialization": materialization,
            "realized_schedule_hash": None,
            "execution_hash": execution_hash,
            "schedule": schedule,
            "schedule_hash": schedule_hash,
            "campaign_cost_control": candidate.campaign_cost_control.model_copy(
                update={**cost_body, "content_hash": sha256_json(cost_body)}
            ),
            "full_schedule_reserve_usd": full_schedule_reserve_usd,
            "hard_cap_usd": hard_cap_usd,
        }
    )
    return HeldoutACExecutionCandidate.model_validate(
        rebuilt.model_dump(mode="python", exclude_none=True)
    )


def test_candidate_binds_exact_48_rows_without_live_authority() -> None:
    suite = load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    candidate = _candidate()

    assert candidate.status == "NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED"
    assert len(candidate.schedule) == 48
    assert candidate.source_qualification.source_qualification_hash == QUALIFICATION_HASH
    assert candidate.schema_version == "heldout-ac-execution-candidate-v3"
    assert candidate.realized_schedule_hash == sha256_json(
        execution._realized_schedule_projection(candidate.schedule)
    )
    assert candidate.materialization.path == (
        "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r6.json"
    )
    assert candidate.materialization.file_bytes == 53_250
    assert candidate.materialization.file_sha256 == (
        "sha256:1a3568e372c9b3af1e384addfb3b5d8351138625072b3af95ccc6290bed3d975"
    )
    assert candidate.materialization.content_hash == (
        "sha256:61f65a54891ef60c07c1edbadd67040cdf5d31e21e4c6e1d3ac97d7f94e419fb"
    )
    materialization, _raw = execution._read_materialization(ROOT)
    assert materialization.source_hash == (
        "sha256:7135f82bebfee3b635cd67347fee258be57fa2ef15cce09e3df838897c197131"
    )
    assert candidate.budget_amendment is not None
    assert candidate.full_schedule_reserve_usd == 57.6
    assert candidate.hard_cap_usd == 60.0
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


def test_condition_rehash_changes_approval_identity_and_fails_exact_suite_relation() -> None:
    suite = load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    candidate = _candidate()
    row = candidate.schedule[0]
    package = load_task_package(ROOT / row.task_path)
    authority = materialize_heldout_ac_runtime_task_authority(
        candidate=candidate,
        task_id=row.task_id,
        package=package,
        api_key="test-runtime-secret",
        repository=ROOT,
    )
    approved_manifest = build_heldout_ac_run_manifest(
        candidate=candidate,
        row_order=row.order,
        run_id="run_heldout_schedule_binding_001",
        created_at=datetime(2026, 8, 14, 10, 1, tzinfo=UTC),
        authority=authority,
    )
    changed_condition = "structured" if row.condition == "no_memory" else "no_memory"
    mutated = _rehashed_candidate_row(
        candidate,
        field_name="condition",
        value=changed_condition,
    )

    assert heldout_ac_manifest_matches_candidate(approved_manifest, candidate) is True
    assert heldout_ac_manifest_matches_candidate(approved_manifest, mutated) is False
    assert mutated.realized_schedule_hash != candidate.realized_schedule_hash
    assert mutated.execution_hash != candidate.execution_hash
    assert mutated.schedule[0].schedule_row_id != row.schedule_row_id
    assert mutated.schedule_hash != candidate.schedule_hash
    assert (
        mutated.campaign_cost_control.content_hash != candidate.campaign_cost_control.content_hash
    )
    assert heldout_ac_campaign_identity_hash(mutated) != heldout_ac_campaign_identity_hash(
        candidate
    )
    assert heldout_ac_candidate_matches_current_execution_inputs(mutated, repository=ROOT) is False
    with pytest.raises(ContractError, match="realized schedule differs"):
        materialize_heldout_ac_runtime_task_authority(
            candidate=mutated,
            task_id=row.task_id,
            package=package,
            api_key="test-runtime-secret",
            repository=ROOT,
        )
    with pytest.raises(ContractError, match="schedule differs"):
        heldout_ac_completion_campaign_authority(candidate=mutated, suite=suite)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("task_path", "tasks/tampered-public-path"),
        ("public_spec_hash", "sha256:" + "3" * 64),
        ("private_spec_hash", "sha256:" + "4" * 64),
        ("base_commit", "5" * 40),
        ("evaluator_image", "patchloop/tampered-evaluator:latest"),
        ("evaluator_image_digest", "sha256:" + "6" * 64),
        ("evaluator_contract_template_hash", "sha256:" + "7" * 64),
    ],
)
def test_supplemental_row_rehash_changes_execution_and_paid_identity(
    field_name: str,
    value: object,
) -> None:
    candidate = _candidate()
    mutated = _rehashed_candidate_row(candidate, field_name=field_name, value=value)

    assert mutated.realized_schedule_hash != candidate.realized_schedule_hash
    assert mutated.execution_hash != candidate.execution_hash
    assert mutated.schedule[0].schedule_row_id != candidate.schedule[0].schedule_row_id
    assert mutated.schedule_hash != candidate.schedule_hash
    assert heldout_ac_campaign_identity_hash(mutated) != heldout_ac_campaign_identity_hash(
        candidate
    )
    assert heldout_ac_candidate_matches_current_execution_inputs(mutated, repository=ROOT) is False


def test_runtime_tuple_rehash_changes_execution_but_fails_sealed_input_binding() -> None:
    candidate = _candidate()
    assert heldout_ac_candidate_matches_current_execution_inputs(candidate, repository=ROOT) is True
    mutated = _rehashed_candidate_runtime_tuple(candidate)

    assert mutated.runtime_tuple_hash != candidate.runtime_tuple_hash
    assert mutated.realized_schedule_hash == candidate.realized_schedule_hash
    assert mutated.execution_hash != candidate.execution_hash
    assert mutated.schedule[0].schedule_row_id != candidate.schedule[0].schedule_row_id
    assert mutated.schedule_hash != candidate.schedule_hash
    assert (
        mutated.campaign_cost_control.content_hash != candidate.campaign_cost_control.content_hash
    )
    assert heldout_ac_candidate_matches_current_execution_inputs(mutated, repository=ROOT) is False


def test_task_version_rehash_still_rejects_invalid_supplemental_contract() -> None:
    candidate = _candidate()

    with pytest.raises(ValidationError):
        HeldoutACExecutionCandidate.model_validate(
            _rehashed_candidate_row_payload(candidate, field_name="task_version", value=2)
        )


def test_v3_runtime_contract_and_completion_leaf_bind_realized_schedule() -> None:
    suite = load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    candidate = _candidate()

    runtime_contract = heldout_ac_runtime_contract(candidate)
    completion_authority = heldout_ac_completion_campaign_authority(
        candidate=candidate,
        suite=suite,
    )

    assert runtime_contract["schema_version"] == "heldout-ac-runtime-contract-v2"
    assert runtime_contract["realized_schedule_hash"] == candidate.realized_schedule_hash
    assert completion_authority.candidate_schema_version == "heldout-ac-execution-candidate-v3"
    assert completion_authority.realized_schedule_hash == candidate.realized_schedule_hash
    assert completion_authority.max_cumulative_input_tokens == 1_000_000
    assert completion_authority.max_cumulative_output_tokens == 100_000
    assert completion_authority.max_total_tokens == 1_100_000
    assert completion_authority.full_schedule_reserve_nanos == 57_600_000_000
    assert completion_authority.hard_cap_nanos == 60_000_000_000


@pytest.mark.parametrize(
    "schema_version",
    [
        "heldout-ac-execution-candidate-v1",
        "heldout-ac-execution-candidate-v2",
    ],
)
def test_historical_candidate_hash_and_runtime_contract_remain_parse_compatible(
    schema_version: str,
) -> None:
    legacy = _legacy_candidate(_candidate(), schema_version=schema_version)

    assert legacy.schema_version == schema_version
    assert legacy.realized_schedule_hash is None
    if schema_version == "heldout-ac-execution-candidate-v2":
        assert legacy.materialization.path.endswith("task-pricing-materialization-r5.json")
        assert legacy.materialization.content_hash == execution.LEGACY_MATERIALIZATION_CONTENT_HASH
    assert heldout_ac_runtime_contract(legacy)["schema_version"] == "heldout-ac-runtime-contract-v1"
    assert "realized_schedule_hash" not in heldout_ac_runtime_contract(legacy)


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
    assert manifest.budget.max_cumulative_input_tokens == 1_000_000
    assert manifest.budget.max_cumulative_output_tokens == 100_000
    assert manifest.budget.max_total_tokens == 1_100_000
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
