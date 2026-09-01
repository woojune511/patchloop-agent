from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pydantic import ValidationError

from patchloop.agent.finalization_successor_qualification import (
    QUALIFICATION_FILE_BYTES,
    QUALIFICATION_FILE_SHA256,
    QUALIFICATION_PATH,
    FinalizationSuccessorQualification,
    build_finalization_successor_qualification,
    load_finalization_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _rehashed(**changes: object) -> dict:
    body = build_finalization_successor_qualification(REPOSITORY).model_dump(
        mode="python"
    )
    body.update(changes)
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_qualification_binds_consumed_r4_and_all_successor_boundaries() -> None:
    qualification = build_finalization_successor_qualification(REPOSITORY)
    scenarios = {item.scenario_id: item for item in qualification.scenarios}

    assert qualification.source_rows == 6
    assert qualification.source_evaluator_reached == 0
    assert qualification.source_baseline_token_terminals == 3
    assert qualification.source_lean_agent_failures == 3
    assert qualification.predecessor_finalization_max_output_tokens == 5_000
    assert qualification.successor_configured_max_output_tokens == 25_000
    assert scenarios["initial-mutation"].completion_target == "mutation"
    assert scenarios["initial-mutation"].recheck_after_mutation_required is True
    assert scenarios["check-preferred-a"].selected_tool_names == ("run_check",)
    assert scenarios["check-preferred-c"].selected_tool_names == ("run_check",)
    assert scenarios["corrective-mutation"].completion_target == (
        "corrective-mutation"
    )
    assert scenarios["corrective-mutation"].selected_tool_names == ("apply_patch",)
    assert scenarios["diff-review"].selected_tool_names == ("get_diff",)
    assert scenarios["submission"].selected_tool_names == ("finish_task",)
    assert scenarios["split-reduced"].effective_max_output_tokens == 10_000
    assert scenarios["split-reduced"].allowance_decision == "admit_reduced"


def test_qualification_is_condition_neutral_but_makes_no_adequacy_claim() -> None:
    qualification = build_finalization_successor_qualification(REPOSITORY)
    a_check, c_check = qualification.scenarios[1:3]

    assert qualification.condition_neutral_check_projection is True
    assert a_check.completion_target == c_check.completion_target
    assert a_check.selected_tool_names == c_check.selected_tool_names
    assert a_check.effective_max_output_tokens == c_check.effective_max_output_tokens
    assert c_check.normalized_no_memory_request_body_sha256 == a_check.request_body_hash
    assert qualification.reasoning_adequacy_established is False
    assert qualification.completion_improvement_established is False
    assert qualification.quality_improvement_established is False


def test_qualification_has_zero_external_or_activation_authority() -> None:
    qualification = build_finalization_successor_qualification(REPOSITORY)

    assert qualification.runtime_state_files_read == 0
    assert qualification.private_task_files_read == 0
    assert qualification.hidden_files_read == 0
    assert qualification.reference_patches_read == 0
    assert qualification.provider_calls == 0
    assert qualification.runner_calls == 0
    assert qualification.tool_calls == 0
    assert qualification.docker_calls == 0
    assert qualification.evaluator_calls == 0
    assert qualification.added_model_cost_usd == 0
    assert qualification.runtime_activation_authorized is False
    assert qualification.provider_calls_authorized is False
    assert qualification.docker_execution_authorized is False
    assert qualification.paid_execution_authorized is False
    assert qualification.fresh_panel_authorized is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("reasoning_adequacy_established", True),
        ("completion_improvement_established", True),
        ("provider_calls", 1),
        ("runtime_activation_authorized", True),
        ("paid_execution_authorized", True),
    ],
)
def test_qualification_rejects_claim_or_authority_drift(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        FinalizationSuccessorQualification.model_validate(
            _rehashed(**{field: value})
        )


def test_qualification_bytes_are_deterministic_and_consumed_artifact_loads() -> None:
    first = build_finalization_successor_qualification(REPOSITORY)
    second = build_finalization_successor_qualification(REPOSITORY)
    raw = qualification_bytes(first)

    assert first == second
    assert raw == qualification_bytes(second)
    assert raw.endswith(b"\n")
    assert FinalizationSuccessorQualification.model_validate_json(raw) == first

    with TemporaryDirectory(prefix="finalization-current-", dir=REPOSITORY / ".p") as temp:
        current_path = Path(temp) / "qualification.json"
        current_path.write_bytes(raw)
        assert load_finalization_successor_qualification(
            REPOSITORY, current_path.relative_to(REPOSITORY)
        ) == first

    path = REPOSITORY / QUALIFICATION_PATH
    consumed_raw = path.read_bytes()
    assert len(consumed_raw) == QUALIFICATION_FILE_BYTES
    assert "sha256:" + hashlib.sha256(consumed_raw).hexdigest() == (
        QUALIFICATION_FILE_SHA256
    )
    loaded = load_finalization_successor_qualification(REPOSITORY)
    assert qualification_bytes(loaded) == consumed_raw


def test_qualification_source_has_no_runner_provider_or_task_loader_dependency() -> None:
    source = (
        REPOSITORY
        / "patchloop/agent/finalization_successor_qualification.py"
    ).read_text(encoding="utf-8")

    assert "from patchloop.agent.runner" not in source
    assert "from patchloop.task_loader" not in source
    assert "import openai" not in source.lower()
    assert "import subprocess" not in source
    assert "import socket" not in source
