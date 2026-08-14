from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals import heldout_ac_budget_amendment as budget
from patchloop.evals.heldout_ac_budget_amendment import (
    AMENDMENT_CONTENT_HASH,
    AMENDMENT_FILE_BYTES,
    AMENDMENT_FILE_SHA256,
    FULL_SCHEDULE_RESERVE_NANOS,
    HARD_CAP_NANOS,
    MAX_CUMULATIVE_INPUT_TOKENS,
    MAX_CUMULATIVE_OUTPUT_TOKENS,
    MAX_TOTAL_TOKENS,
    PER_RUN_RESERVE_NANOS,
    heldout_ac_budget_amendment_binding,
    load_heldout_ac_budget_amendment,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite

ROOT = Path(__file__).resolve().parents[1]


def _copy_closed_inputs(target: Path) -> None:
    paths = [
        budget.AMENDMENT_PATH.as_posix(),
        budget._BASE_SUITE["path"],
        *(item["path"] for item in budget._EVIDENCE_FILES),
    ]
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)


def test_exact_budget_amendment_loads_and_binds() -> None:
    amendment = load_heldout_ac_budget_amendment(repository=ROOT)
    binding = heldout_ac_budget_amendment_binding(repository=ROOT)

    assert amendment.content_hash == AMENDMENT_CONTENT_HASH
    assert binding.file_bytes == AMENDMENT_FILE_BYTES
    assert binding.file_sha256 == AMENDMENT_FILE_SHA256
    assert amendment.runtime_override["max_cumulative_input_tokens"] == 1_000_000
    assert amendment.runtime_override["max_cumulative_output_tokens"] == 100_000
    assert amendment.runtime_override["max_total_tokens"] == 1_100_000
    assert amendment.cost_override["per_run_reserve_usd"] == 1.2
    assert amendment.cost_override["full_schedule_reserve_usd"] == 57.6
    assert amendment.cost_override["hard_cap_usd"] == 60.0


def test_budget_arithmetic_and_development_headroom_are_exact() -> None:
    amendment = load_heldout_ac_budget_amendment(repository=ROOT)
    summary = amendment.development_evidence["summary"]

    assert MAX_TOTAL_TOKENS == (MAX_CUMULATIVE_INPUT_TOKENS + MAX_CUMULATIVE_OUTPUT_TOKENS)
    assert PER_RUN_RESERVE_NANOS == 1_200_000_000
    assert FULL_SCHEDULE_RESERVE_NANOS == PER_RUN_RESERVE_NANOS * 48
    assert HARD_CAP_NANOS == 60_000_000_000
    assert summary["secondary_stress_max_input_tokens"] < MAX_CUMULATIVE_INPUT_TOKENS
    assert summary["secondary_stress_max_output_tokens"] < MAX_CUMULATIVE_OUTPUT_TOKENS
    assert summary["secondary_stress_max_total_tokens"] < MAX_TOTAL_TOKENS
    assert summary["runaway_tail_total_tokens"] > MAX_TOTAL_TOKENS
    assert summary["secondary_stress_max_cost_nanos"] < PER_RUN_RESERVE_NANOS


def test_budget_amendment_reads_only_closed_development_inputs(monkeypatch) -> None:
    observed: set[str] = set()
    original = Path.read_bytes

    def tracked(path: Path) -> bytes:
        resolved = path.resolve()
        if resolved.is_relative_to(ROOT):
            observed.add(resolved.relative_to(ROOT).as_posix())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    load_heldout_ac_budget_amendment(repository=ROOT)

    assert observed == {
        budget.AMENDMENT_PATH.as_posix(),
        budget._BASE_SUITE["path"],
        *(item["path"] for item in budget._EVIDENCE_FILES),
    }
    assert not any(path.startswith("tasks/") for path in observed)
    assert not any("heldout-ac-r11" in path for path in observed)


def test_budget_amendment_preserves_zero_authority() -> None:
    amendment = load_heldout_ac_budget_amendment(repository=ROOT)

    assert amendment.change_control["heldout_outcomes_used_for_threshold_selection"] is False
    assert amendment.change_control["r11_outcomes_used_for_threshold_selection"] is False
    assert amendment.authority == {
        "heldout_task_or_outcome_access_authorized": False,
        "docker_sdk_credential_or_network_observation_authorized": False,
        "provider_evaluator_or_agent_execution_authorized": False,
        "candidate_creation_authorized": False,
        "approval_reservation_or_spend_authorized": False,
        "official_analysis_or_claim_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "added_model_cost_usd": 0.0,
    }


@pytest.mark.parametrize(
    ("actual", "expected"),
    [
        (1, True),
        (1.0, 1),
        ({"value": 1.0}, {"value": 1}),
        ([1, False], [1, 0]),
    ],
)
def test_recursive_scalar_comparison_is_type_exact(actual: object, expected: object) -> None:
    assert budget._exact_typed_equal(actual, expected) is False


def test_duplicate_or_rehashed_amendment_drift_fails_closed(tmp_path: Path) -> None:
    _copy_closed_inputs(tmp_path)
    path = tmp_path / budget.AMENDMENT_PATH
    path.write_text(
        path.read_text(encoding="utf-8") + "status: execution-closed\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError):
        load_heldout_ac_budget_amendment(repository=tmp_path)


def test_bound_development_evidence_drift_fails_closed(tmp_path: Path) -> None:
    _copy_closed_inputs(tmp_path)
    evidence_path = tmp_path / budget._EVIDENCE_FILES[0]["path"]
    evidence_path.write_bytes(evidence_path.read_bytes() + b" ")

    with pytest.raises(ContractError, match="evidence file binding drifted"):
        load_heldout_ac_budget_amendment(repository=tmp_path)


def test_amendment_is_not_a_generic_suite() -> None:
    with pytest.raises(ContractError):
        load_heldout_ac_suite(budget.AMENDMENT_PATH, repository=ROOT)


def test_budget_module_has_no_execution_or_external_import_surface() -> None:
    source = (ROOT / "patchloop/evals/heldout_ac_budget_amendment.py").read_text(encoding="utf-8")
    for forbidden in (
        "import openai",
        "import socket",
        "import subprocess",
        "task_loader",
        "heldout_ac_dispatcher",
        "heldout_ac_preflight",
    ):
        assert forbidden not in source
