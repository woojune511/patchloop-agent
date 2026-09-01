from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v21 as rapid
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v26 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    value = json.loads(raw)
    assert raw == rapid.candidate_bytes(value)
    assert len(raw) == 15_734
    assert sha256_bytes(raw) == (
        "sha256:f5e3d50d4c4368d1a283d7a0b732397c956077d5e4da6f5b421d205745949a8e"
    )
    return value


def test_consumed_candidate_v26_records_the_driver_policy_delta(
    candidate: dict[str, Any],
) -> None:
    predecessor_raw = (REPOSITORY / rapid.PREDECESSOR_CANDIDATE_PATH).read_bytes()
    result = rapid._result_identity(REPOSITORY)

    assert candidate["candidate_revision"] == 26
    assert candidate["content_hash"] == (
        "sha256:073d744112cf39f1046ef0414f0cf2c22b13abc3dfc76bc84eec110d6283da17"
    )
    assert candidate["execution_hash"] == (
        "sha256:afcc526c747fd54dbb3dbfcd6660f6dfbeb393e992a5e4837ba31f8185de95de"
    )
    assert candidate["provider_calls_made"] == 0
    assert candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0
    assert candidate["official"] is False
    assert candidate["variant_contracts"] == rapid.VARIANT_CONTRACTS
    assert candidate["schedule_hash"] == sha256_json(candidate["schedule"])
    assert candidate["driver_contract"]["policy_version"] == (
        "append-only-row-settlement-driver-v2"
    )
    assert candidate["selection_evidence"]["changed_experiment_variable"] == (
        "terminal-state-parity-driver-policy-only"
    )
    assert len(predecessor_raw) == rapid.PREDECESSOR_CANDIDATE_BYTES
    assert sha256_bytes(predecessor_raw) == rapid.PREDECESSOR_CANDIDATE_FILE_SHA256
    assert result["event"] == "batch-halted"
    assert result["reason_codes"] == ["TERMINAL_STATE_NOT_ATOMIC"]
    assert result["terminal_row_count"] == 1
    assert result["not_started_row_count"] == 5


def test_consumed_rehearsal_is_a_byte_audit_and_uses_terminal_parity_v2(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()
    first = json.loads(raw)

    assert raw == rapid.rehearsal_bytes(first)
    assert len(raw) == 5_830
    assert sha256_bytes(raw) == (
        "sha256:78bdf3fa0353e7133d7bce1720730c0f91dc9b991e9fb80c568ba491ebbaa6ce"
    )
    assert first["candidate_content_hash"] == candidate["content_hash"]
    assert first["verified_manifest_count"] == 6
    assert first["driver_binding"]["policy_version"] == ("append-only-row-settlement-driver-v2")
    assert first["provider_calls_made"] == 0
    assert first["docker_calls_made"] == 0
    assert first["task_calls_made"] == 0
    assert first["evaluator_calls_made"] == 0
    assert first["visible_check_calls_made"] == 0
    assert first["first_row_capability"]["provider_dispatch_rehearsed"] is True
    assert first["inter_row_transition"]["decision"] == "continue"
    assert first["inter_row_transition"]["driver_policy_version"] == (
        "append-only-row-settlement-driver-v2"
    )
    assert first["inter_row_transition"]["decision_persisted_before_capability"] is True
    assert first["second_row_capability"]["schedule_order"] == 2
    assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_consumed_candidate_and_rehearsal_bind_terminal_parity_driver_v2(
    candidate: dict[str, Any],
) -> None:
    rehearsal = json.loads((REPOSITORY / rapid.REHEARSAL_PATH).read_bytes())

    assert candidate["driver_contract"]["policy_version"] == (
        "append-only-row-settlement-driver-v2"
    )
    assert rehearsal["driver_binding"] == candidate["driver_contract"]
    assert rehearsal["inter_row_transition"]["driver_policy_version"] == (
        "append-only-row-settlement-driver-v2"
    )


def test_consumed_candidate_content_tamper_fails_closed(candidate: dict[str, Any]) -> None:
    changed = copy.deepcopy(candidate)
    changed["driver_contract"]["policy_version"] = "append-only-row-settlement-driver-v1"
    with pytest.raises(RecoveryError, match="identity differs"):
        rapid.candidate_bytes(changed)


def test_live_entry_requires_exact_approval_before_external_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: pytest.fail("Docker preflight ran before exact approval")),
    )
    with pytest.raises((ContractError, RecoveryError)):
        rapid.run_rapid_public_development_v21(
            repository=REPOSITORY,
            approve_live_cost=False,
            approved_execution_hash=None,
        )


def test_rehearsal_cli_does_not_load_env_file(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = {"execution_hash": candidate["execution_hash"], "no_call": True}
    missing = tmp_path / "missing.env"
    monkeypatch.setattr(
        rapid_script,
        "rehearse_rapid_public_development_v21",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v21",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v26.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
