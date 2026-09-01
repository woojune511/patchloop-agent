from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.rapid_public_development_v20_qualification import (
    QUALIFICATION_PATH,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_consumed_candidate_v25_qualification_retains_zero_call_boundary() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
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


def test_consumed_candidate_v25_qualification_binds_driver_and_recovery() -> None:
    value = json.loads((ROOT / QUALIFICATION_PATH).read_bytes())

    assert value["registered_admission"]["all_manifest_count"] == 6
    assert value["registered_admission"]["requires_row_capability"] is True
    assert value["result_contract"]["candidate_wrapper_has_no_manual_row_loop"] is True
    assert value["recovery_contract"]["consumed_r16_retry_allowed"] is False
    assert value["recovery_contract"]["restart_without_ephemeral_receipts_halts"] is True


def test_stored_candidate_v25_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
