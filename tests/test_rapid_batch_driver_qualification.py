from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals.rapid_batch_driver_qualification import (
    QUALIFICATION_PATH,
    load_rapid_batch_driver_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _consumed_qualification() -> dict[str, object]:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    return json.loads(raw)


def test_consumed_driver_qualification_retains_zero_call_boundary() -> None:
    first = _consumed_qualification()

    assert qualification_bytes(first) == (ROOT / QUALIFICATION_PATH).read_bytes()
    assert first["status"] == "offline-qualified"
    assert first["typed_capability_gateway_integrated"] is True
    assert first["append_only_rapid_driver_integrated"] is True
    assert first["candidate_specific_runtime_integrated"] is False
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
        )
    )


def test_consumed_driver_qualification_covers_the_required_fault_and_order_gate() -> None:
    value = _consumed_qualification()
    faults = value["fault_matrix"]

    assert set(faults) == {
        "eligible_returned_row",
        "escaped_exception",
        "artifact_fault",
        "accounting_fault",
        "active_worker_lock",
        "restart_without_ephemeral_receipts",
        "duplicate_grant",
        "rehashed_semantic_tamper",
    }
    assert faults["eligible_returned_row"]["decision"] == "continue"
    assert all(
        faults[name]["decision"] == "halt"
        for name in (
            "escaped_exception",
            "artifact_fault",
            "accounting_fault",
            "active_worker_lock",
            "restart_without_ephemeral_receipts",
        )
    )
    assert value["schedule_advance_contract"] == {
        "ordinary_terminal_requires_typed_continue": True,
        "infrastructure_terminal_requires_gateway_continue": True,
        "decision_persisted_before_capability": True,
        "capability_persisted_before_next_row_start": True,
        "halt_or_incomplete_journal_starts_no_later_row": True,
    }


def test_consumed_driver_qualification_is_source_superseded() -> None:
    value = _consumed_qualification()

    assert value["consumed_r16_modified"] is False
    assert value["consumed_r16_retry_allowed"] is False
    with pytest.raises(ContractError, match="source binding differs"):
        load_rapid_batch_driver_qualification(ROOT)


def test_stored_driver_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
