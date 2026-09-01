from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.evals.rapid_public_development_v21_qualification import (
    QUALIFICATION_PATH,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _stored() -> tuple[bytes, dict[str, object]]:
    target = ROOT / QUALIFICATION_PATH
    if not target.exists():
        pytest.skip("candidate-v26 qualification is materialized after offline source gates")
    raw = target.read_bytes()
    return raw, json.loads(raw)


def test_consumed_candidate_v26_qualification_is_canonical_and_zero_call() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    assert len(raw) == 5_621
    assert sha256_bytes(raw) == (
        "sha256:dc2a873b5e3853b87166427f23dba408c2423f43c5aa621be1a3faa7faa605b7"
    )
    assert value["content_hash"] == (
        "sha256:f65de23f9191d0476fa7a1d6cf97734c50d67182d28018e89c2d853652f0986c"
    )
    assert value["status"] == "offline-qualified"
    assert value["candidate_specific_runtime_integrated"] is True
    assert value["candidate_created"] is True
    assert value["rehearsal_created"] is True
    assert value["paid_execution_authorized"] is False
    assert all(
        value["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "task_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
        )
    )


def test_candidate_v26_qualification_binds_terminal_parity_and_recovery() -> None:
    _, value = _stored()

    assert value["driver_qualification"]["successor_policy_version"] == (
        "append-only-row-settlement-driver-v2"
    )
    assert value["registered_admission"]["all_manifest_count"] == 6
    assert value["registered_admission"]["requires_row_capability"] is True
    assert value["result_contract"]["completed_terminal_uses_durable_result"] is True
    assert value["result_contract"]["completed_payload_outcome_kind_required"] is False
    assert value["result_contract"]["candidate_wrapper_has_no_manual_row_loop"] is True
    assert value["recovery_contract"]["consumed_r17_retry_allowed"] is False


def test_stored_candidate_v26_qualification_is_byte_stable() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
