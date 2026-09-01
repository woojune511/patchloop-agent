from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.budget_adequacy import (
    BudgetAdequacyReport,
    r8_public_budget_adequacy_contract,
)
from patchloop.agent.budget_adequacy_qualification import (
    BOUNDARY_SCENARIOS,
    QUALIFICATION_PATH,
    SOURCE_PATHS,
    VALIDATION_PATHS,
    BudgetAdequacyPublicQualification,
    build_budget_adequacy_public_qualification,
    load_budget_adequacy_public_qualification,
    qualification_bytes,
)
from patchloop.errors import RecoveryError
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _rehashed_qualification(**changes) -> dict:
    body = build_budget_adequacy_public_qualification(REPOSITORY).model_dump(mode="python")
    body.update(changes)
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_public_qualification_binds_r8_and_all_measurement_boundaries() -> None:
    qualification = build_budget_adequacy_public_qualification(REPOSITORY)

    assert qualification.status == "PUBLIC_NO_CALL_BUDGET_ADEQUACY_QUALIFIED_RUNTIME_CLOSED"
    assert qualification.contract_hash == qualification.contract.content_hash
    assert qualification.reference_report.budget_adequacy_gate_passed is True
    assert qualification.reference_report.overall_summary.successes == 4
    assert qualification.reference_report.overall_summary.evaluator_reached_rows == 4
    assert qualification.reference_report.overall_summary.any_token_terminal_rows == 0
    assert qualification.reference_report.overall_summary.patch_attempts == 6
    assert qualification.reference_report.overall_summary.patch_rejections == 1
    assert qualification.reference_report.overall_summary.no_new_evidence_turns == 3
    assert qualification.reference_report.realized_schedule_hash == (
        qualification.contract.public_realized_schedule_hash
    )
    assert qualification.reference_report.settled_model_cost_nanos == 366_421_500
    assert qualification.reference_report.dollar_cap_boundary_reached is False
    assert tuple(item.scenario for item in qualification.boundary_observations) == (
        BOUNDARY_SCENARIOS
    )
    assert tuple(
        item.report.budget_adequacy_gate_passed for item in qualification.boundary_observations
    ) == (False, False, False, True)
    assert (
        tuple(
            item.report.fixed_budget_primary_status for item in qualification.boundary_observations
        )
        == ("estimable-complete-matrix",) * 4
    )
    zero_success = qualification.boundary_observations[-1].report.condition_summaries[1]
    assert zero_success.cost_per_success_nanos.status == "undefined-zero-denominator"
    assert zero_success.cost_per_success_nanos.value is None


def test_qualification_reads_only_bound_artifacts_and_inventory_files(monkeypatch) -> None:
    original = Path.read_bytes
    reads: list[Path] = []

    def tracked(path: Path) -> bytes:
        resolved = path.resolve()
        reads.append(resolved)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)

    qualification = build_budget_adequacy_public_qualification(REPOSITORY)

    expected = {
        (REPOSITORY / relative).resolve()
        for relative in (
            qualification.contract.r8_development_evidence.path,
            qualification.contract.finalization_reserve.path,
            qualification.contract.saturation_thresholds.path,
            qualification.contract.admission_recovery_shadow.path,
            *SOURCE_PATHS,
            *VALIDATION_PATHS,
        )
    }
    assert set(reads) == expected
    assert all("tasks" not in path.parts for path in reads)
    assert all(".patchloop" not in path.parts for path in reads)
    assert all("r16" not in path.name.lower() for path in reads)


def test_qualification_has_zero_runtime_or_claim_authority() -> None:
    qualification = build_budget_adequacy_public_qualification(REPOSITORY)

    assert qualification.threshold_selection_uses_r16 is False
    assert qualification.r16_artifact_files_read == 0
    assert qualification.trace_snapshot_files_read == 0
    assert qualification.runtime_state_files_read == 0
    assert qualification.public_task_files_read == 0
    assert qualification.private_task_files_read == 0
    assert qualification.hidden_files_read == 0
    assert qualification.reference_patches_read == 0
    assert qualification.provider_transport_calls == 0
    assert qualification.provider_generation_calls == 0
    assert qualification.runner_calls == 0
    assert qualification.tool_execution_calls == 0
    assert qualification.docker_calls == 0
    assert qualification.evaluator_calls == 0
    assert qualification.added_model_cost_usd == 0
    assert qualification.provider_calls_authorized is False
    assert qualification.runner_activation_authorized is False
    assert qualification.tool_policy_activation_authorized is False
    assert qualification.request_integration_authorized is False
    assert qualification.state_mutation_authorized is False
    assert qualification.fresh_panel_authorized is False
    assert qualification.paid_execution_authorized is False


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("threshold_selection_uses_r16", True, "literal_error"),
        ("r16_artifact_files_read", 1, "literal_error"),
        ("provider_generation_calls", 1, "literal_error"),
        ("runner_activation_authorized", True, "literal_error"),
        ("fresh_panel_authorized", True, "literal_error"),
    ],
)
def test_qualification_rejects_authority_or_heldout_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        BudgetAdequacyPublicQualification.model_validate(_rehashed_qualification(**{field: value}))


def test_qualification_rejects_rehashed_contract_drift() -> None:
    qualification = build_budget_adequacy_public_qualification(REPOSITORY)
    contract = qualification.contract.model_dump(mode="python")
    contract["population_terminal_rate_bound_established"] = True
    contract["content_hash"] = sha256_json(
        {key: value for key, value in contract.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        BudgetAdequacyPublicQualification.model_validate(
            _rehashed_qualification(contract=contract, contract_hash=contract["content_hash"])
        )


def test_qualification_rejects_rehashed_reference_interpretation() -> None:
    qualification = build_budget_adequacy_public_qualification(REPOSITORY)
    report = qualification.reference_report.model_dump(mode="python")
    report["budget_adequacy_gate_passed"] = False
    report["administrative_truncation_status"] = "exceeds-zero-terminal-criterion"
    report["higher_budget_capability_status"] = "inconclusive-administrative-truncation"
    report["content_hash"] = sha256_json(
        {key: value for key, value in report.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError, match="gate differs"):
        BudgetAdequacyPublicQualification.model_validate(
            _rehashed_qualification(
                reference_report=report,
                reference_report_hash=report["content_hash"],
            )
        )


def test_qualification_revalidates_copied_nested_report() -> None:
    qualification = build_budget_adequacy_public_qualification(REPOSITORY)
    copied = qualification.reference_report.model_copy(
        update={"budget_adequacy_gate_passed": False}
    )
    body = qualification.model_copy(update={"reference_report": copied}).model_dump(mode="python")
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError, match="gate differs"):
        BudgetAdequacyPublicQualification.model_validate(body)


def test_qualification_rejects_predecessor_byte_drift(monkeypatch) -> None:
    relative = r8_public_budget_adequacy_contract().r8_development_evidence.path
    target = (REPOSITORY / relative).resolve()
    original = Path.read_bytes

    def drift(path: Path) -> bytes:
        raw = original(path)
        return raw + b" " if path.resolve() == target else raw

    monkeypatch.setattr(Path, "read_bytes", drift)

    with pytest.raises(RecoveryError, match="predecessor differs"):
        build_budget_adequacy_public_qualification(REPOSITORY)


def test_qualification_bytes_are_deterministic_and_round_trip() -> None:
    first = build_budget_adequacy_public_qualification(REPOSITORY)
    second = build_budget_adequacy_public_qualification(REPOSITORY)
    raw = qualification_bytes(first)

    assert first == second
    assert raw == qualification_bytes(second)
    assert raw.endswith(b"\n")
    assert BudgetAdequacyPublicQualification.model_validate_json(raw) == first


def test_loader_rejects_duplicate_json_keys(monkeypatch) -> None:
    raw = qualification_bytes(build_budget_adequacy_public_qualification(REPOSITORY))
    duplicate = raw.replace(
        b'{\n  "schema_version":',
        b'{\n  "schema_version": "duplicate",\n  "schema_version":',
        1,
    )
    original = Path.read_bytes

    def fake(path: Path) -> bytes:
        if path.name == "duplicate-budget-adequacy.json":
            return duplicate
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", fake)

    with pytest.raises(RecoveryError, match="invalid JSON"):
        load_budget_adequacy_public_qualification(
            REPOSITORY,
            "experiments/duplicate-budget-adequacy.json",
        )


def test_checked_in_artifact_loads_exactly_after_materialization() -> None:
    path = REPOSITORY / QUALIFICATION_PATH
    if not path.exists():
        pytest.skip("canonical budget-adequacy qualification is not materialized yet")

    loaded = load_budget_adequacy_public_qualification(REPOSITORY)

    assert path.read_bytes() == qualification_bytes(loaded)
    assert loaded == build_budget_adequacy_public_qualification(REPOSITORY)


def test_qualification_models_forbid_extra_fields_and_raw_type_drift() -> None:
    body = _rehashed_qualification(unregistered=True)
    with pytest.raises(ValidationError):
        BudgetAdequacyPublicQualification.model_validate(body)

    report = build_budget_adequacy_public_qualification(REPOSITORY).reference_report
    raw = report.model_dump(mode="python")
    raw["expected_rows"] = 4.0
    raw["content_hash"] = sha256_json(
        {key: value for key, value in raw.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        BudgetAdequacyReport.model_validate(raw)


def test_source_has_no_runner_provider_or_task_loader_dependency() -> None:
    source = (REPOSITORY / "patchloop/agent/budget_adequacy_qualification.py").read_text(
        encoding="utf-8"
    )

    assert "patchloop.agent.runner" not in source
    assert "patchloop.task_loader" not in source
    assert "openai" not in source.lower()
    assert "subprocess" not in source
    assert "socket" not in source
