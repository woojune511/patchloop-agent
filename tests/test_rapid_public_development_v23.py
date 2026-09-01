from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v23 as rapid
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v28 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_candidate() -> dict[str, Any]:
    return rapid.build_rapid_public_development_v23_candidate(repository=REPOSITORY)


def test_candidate_v28_binds_exact_v22_v24_panel_and_consumed_r19(
    built_candidate: dict[str, Any],
) -> None:
    candidate = built_candidate
    predecessor_raw = (REPOSITORY / rapid.PREDECESSOR_CANDIDATE_PATH).read_bytes()
    result = rapid._result_identity(REPOSITORY)

    assert candidate["candidate_revision"] == 28
    assert candidate["provider_calls_made"] == 0
    assert candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0
    assert candidate["official"] is False
    assert candidate["variant_contracts"] == rapid.VARIANT_CONTRACTS
    assert candidate["schedule_hash"] == sha256_json(candidate["schedule"])
    assert [row["variant"] for row in candidate["schedule"]] == [
        "lean-harness-v22",
        "lean-harness-v24",
        "lean-harness-v24",
        "lean-harness-v22",
        "lean-harness-v22",
        "lean-harness-v24",
    ]
    treatment = candidate["variant_contracts"]["lean-harness-v24"]
    assert treatment["tool_schema_version"] == "v26"
    assert treatment["context_policy_version"] == "phase-evidence-v34"
    assert treatment["runtime_policy_version"] == "lean-harness-v24"
    assert treatment["self_directed_exploration_policy_version"] == (
        "bounded-self-directed-exploration-v1"
    )
    selection = candidate["selection_evidence"]
    assert selection["changed_experiment_variable"] == (
        "v22-to-v24-self-directed-exploration-plus-bounded-request-context"
    )
    assert selection["single_policy_effect_attribution_allowed"] is False
    assert selection["product_package_comparison_only"] is True
    assert (
        selection["treatment_lean_v24"]["activation_review"]["candidate_preparation_ready"] is True
    )
    assert len(predecessor_raw) == rapid.PREDECESSOR_CANDIDATE_BYTES
    assert sha256_bytes(predecessor_raw) == rapid.PREDECESSOR_CANDIDATE_FILE_SHA256
    assert result["event"] == "batch-completed"
    assert result["terminal_row_count"] == 6
    assert result["not_started_row_count"] == 0


def test_candidate_v28_registered_manifests_match_exact_runtime_rows(
    built_candidate: dict[str, Any],
) -> None:
    prepared = rapid._prepare_batch(
        built_candidate,
        authority_kind="rehearsal",
        repository=REPOSITORY,
    )

    assert prepared.verifier_id == rapid.VERIFIER_ID
    assert len(prepared.manifests) == 6
    assert [
        (manifest.tool_schema_version, manifest.context_policy_version)
        for manifest in prepared.manifests
    ] == [
        ("v25", "phase-evidence-v32"),
        ("v26", "phase-evidence-v34"),
        ("v26", "phase-evidence-v34"),
        ("v25", "phase-evidence-v32"),
        ("v25", "phase-evidence-v32"),
        ("v26", "phase-evidence-v34"),
    ]


def test_two_production_order_rehearsals_are_byte_identical_and_zero_call(
    built_candidate: dict[str, Any],
) -> None:
    first = rapid._build_rehearsal_for(built_candidate, repository=REPOSITORY)
    second = rapid._build_rehearsal_for(built_candidate, repository=REPOSITORY)

    assert rapid.rehearsal_bytes(first) == rapid.rehearsal_bytes(second)
    assert first["verified_manifest_count"] == 6
    assert first["provider_calls_made"] == 0
    assert first["docker_calls_made"] == 0
    assert first["task_calls_made"] == 0
    assert first["evaluator_calls_made"] == 0
    assert first["visible_check_calls_made"] == 0
    assert first["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["inter_row_transition"]["decision"] == "continue"
    assert first["inter_row_transition"]["decision_persisted_before_capability"] is True
    assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_candidate_v28_content_tamper_fails_closed(
    built_candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(built_candidate)
    changed["variant_contracts"]["lean-harness-v24"]["context_policy_version"] = (
        "phase-evidence-v33"
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
        rapid.run_rapid_public_development_v23(
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
        "rehearse_rapid_public_development_v23",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v23",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v28.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
