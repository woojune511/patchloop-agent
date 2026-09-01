from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v24 as rapid
from patchloop.util import sha256_json
from scripts import run_rapid_public_development_v29 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_candidate() -> dict[str, Any]:
    return rapid.build_rapid_public_development_v24_candidate(repository=REPOSITORY)


def test_candidate_v29_is_exact_three_row_v25_activation_smoke(
    built_candidate: dict[str, Any],
) -> None:
    candidate = built_candidate

    assert candidate["candidate_revision"] == 29
    assert candidate["design_kind"] == "single-arm-mechanical-activation-smoke"
    assert candidate["provider_calls_made"] == 0
    assert candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0
    assert candidate["official"] is False
    assert candidate["variant_contracts"] == rapid.VARIANT_CONTRACTS
    assert candidate["schedule_hash"] == sha256_json(candidate["schedule"])
    assert [row["variant"] for row in candidate["schedule"]] == [
        "lean-harness-v25",
        "lean-harness-v25",
        "lean-harness-v25",
    ]
    treatment = candidate["variant_contracts"]["lean-harness-v25"]
    assert treatment["tool_schema_version"] == "v26"
    assert treatment["context_policy_version"] == "phase-evidence-v35"
    assert treatment["runtime_policy_version"] == "lean-harness-v25"
    assert treatment["request_evidence_schema"] == "lean-harness-request-evidence-v25"
    assert treatment["compatibility_policy_version"] == (
        "trigger-bound-plan-contract-compatibility-v1"
    )
    decision = candidate["selection_evidence"]["activation_decision"]
    assert decision["adopted"] is True
    assert decision["row_count"] == 3
    assert decision["control_rows"] == 0
    assert decision["comparative_effect_claim_allowed"] is False
    assert candidate["selection_evidence"]["consumed_r20"]["retry_allowed"] is False
    assert candidate["cost_control"]["full_schedule_reserve_nanos"] == 3_600_000_000
    assert candidate["cost_control"]["hard_cap_nanos"] == 3_750_000_000


def test_candidate_v29_registered_manifests_match_v25_runtime(
    built_candidate: dict[str, Any],
) -> None:
    prepared = rapid._prepare_batch(
        built_candidate,
        authority_kind="rehearsal",
        repository=REPOSITORY,
    )

    assert prepared.verifier_id == rapid.VERIFIER_ID
    assert len(prepared.manifests) == 3
    assert [
        (manifest.tool_schema_version, manifest.context_policy_version)
        for manifest in prepared.manifests
    ] == [
        ("v26", "phase-evidence-v35"),
        ("v26", "phase-evidence-v35"),
        ("v26", "phase-evidence-v35"),
    ]


def test_two_production_order_rehearsals_are_byte_identical_and_zero_call(
    built_candidate: dict[str, Any],
) -> None:
    first = rapid._build_rehearsal_for(built_candidate, repository=REPOSITORY)
    second = rapid._build_rehearsal_for(built_candidate, repository=REPOSITORY)

    assert rapid.rehearsal_bytes(first) == rapid.rehearsal_bytes(second)
    assert first["verified_manifest_count"] == 3
    assert first["provider_calls_made"] == 0
    assert first["docker_calls_made"] == 0
    assert first["task_calls_made"] == 0
    assert first["evaluator_calls_made"] == 0
    assert first["visible_check_calls_made"] == 0
    assert first["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["inter_row_transition"]["decision"] == "continue"
    assert first["inter_row_transition"]["decision_persisted_before_capability"] is True
    assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_candidate_v29_content_tamper_fails_closed(
    built_candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(built_candidate)
    changed["variant_contracts"]["lean-harness-v25"]["context_policy_version"] = (
        "phase-evidence-v34"
    )
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
        rapid.run_rapid_public_development_v24(
            repository=REPOSITORY,
            approve_live_cost=False,
            approved_execution_hash=None,
        )


def test_rehearsal_cli_does_not_load_env_file(
    built_candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = {"execution_hash": built_candidate["execution_hash"], "no_call": True}
    missing = tmp_path / "missing.env"
    monkeypatch.setattr(
        rapid_script,
        "rehearse_rapid_public_development_v24",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v24",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v29.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
