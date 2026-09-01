from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v19 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v24 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v19_candidate(REPOSITORY)


def test_candidate_is_exact_consumed_zero_call_anyio_v5_v18_v20(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()

    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 25_333
    assert sha256_bytes(raw) == (
        "sha256:75c030d6350072da15233f1c58138547d74fbed136ea24abd8457d29d3352dd3"
    )
    assert candidate["execution_hash"] == (
        "sha256:df2cc46ce6d313918499a6382ca5b1beface18aa5a7811aaf1deb9132d2ee024"
    )
    assert candidate["content_hash"] == (
        "sha256:e6bccee376fd9cb24435e9c07750b147cd2aaaabfa046bf5543dec31d7f91827"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:37f5948855f1a730121dc87edc88007e3ea9319964ea97573f0e50134841dd5a"
    )
    assert candidate["schedule_hash"] == (
        "sha256:ff75daa01a5aa79799af688a9625d5ec0351944bf732e868df88fe1bda8cfd3c"
    )
    assert candidate["cost_control_hash"] == (
        "sha256:a7bc2f24b7ec0ecb501130ef310f958b790108d5788d51dfad958c2cf4691605"
    )
    assert candidate["execution_hash"] == sha256_json(rapid._execution_body(candidate))
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == 0
    assert candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0
    assert tuple(candidate["variant_contracts"]) == (
        "lean-harness-v18",
        "lean-harness-v20",
    )
    assert (
        candidate["selection_evidence"]["consumed_r15_candidate"]["execution_hash"]
        == rapid.SUPERSEDED_EXECUTION_HASH
    )
    assert (
        candidate["selection_evidence"]["semantic_epoch_parity_activation"]["runtime_build_hash"]
        == candidate["runtime_build_hash"]
    )
    binding = candidate["task_bindings"][0]
    assert binding["task_version"] == 5
    assert binding["visible_check_ids"] == list(rapid.EXPECTED_CHECK_IDS)
    with pytest.raises(ContractError, match="source changes differ"):
        rapid.load_rapid_public_development_v19_candidate(REPOSITORY)


def test_six_manifests_preserve_v18_v20_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    decision = registry.validate_authorization_plan(plan)
    assert decision.accepted is True
    assert decision.verifier_id == rapid.VERIFIER_ID
    assert decision.requires_row_capability is True

    counts = {"lean-harness-v18": 0, "lean-harness-v20": 0}
    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v19_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        counts[row["variant"]] += 1
        expected = (
            ("v22", "phase-evidence-v28")
            if row["variant"] == "lean-harness-v18"
            else ("v24", "phase-evidence-v30")
        )
        assert (manifest.tool_schema_version, manifest.context_policy_version) == expected
        verified = registry.verify_manifest(
            plan=plan,
            manifest=manifest,
            authorization_plan_path="<test-rehearsal>",
            authorization_plan_hash=sha256_bytes(rapid._plan_bytes(plan)),
            repository=REPOSITORY,
            runner_root=None,
            batch_validation=True,
        )
        assert verified.accepted is True
        assert verified.verifier_id == rapid.VERIFIER_ID
    assert counts == {"lean-harness-v18": 3, "lean-harness-v20": 3}


def test_consumed_rehearsal_is_exact_and_stops_before_provider_dispatch(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v19_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_080
    assert sha256_bytes(raw) == (
        "sha256:3abd2b4aa24d4854b4e6132e96ca5b33bd5ca864b289c567f385457f6cd304d5"
    )
    assert stored["content_hash"] == (
        "sha256:81da36d3975a32e02fb7e9ab0a641826c51f7a5da7fc151cc187c86f19ff9ec7"
    )
    assert stored["verified_manifest_count"] == 6
    assert stored["provider_calls_made"] == 0
    assert stored["docker_calls_made"] == 0
    assert stored["task_calls_made"] == 0
    assert stored["evaluator_calls_made"] == 0
    assert stored["added_model_cost_usd"] == 0.0
    assert stored["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert stored["second_provider_boundary"]["provider_dispatch_blocked"] is True
    with pytest.raises(ContractError, match="source changes differ"):
        rapid.build_rapid_public_development_v19_rehearsal(repository=REPOSITORY)


def test_candidate_tamper_and_consumed_live_entry_fail_closed(
    candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(candidate)
    changed["variant_contracts"]["lean-harness-v20"]["tool_schema_version"] = "v23"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    with pytest.raises(
        (ContractError, RecoveryError),
        match="source changes differ|current binding differs|result already exists",
    ):
        rapid.run_rapid_public_development_v19(
            repository=REPOSITORY,
            approve_live_cost=False,
            approved_execution_hash=None,
        )
    with pytest.raises(
        (ContractError, RecoveryError),
        match="source changes differ|current binding differs|result already exists",
    ):
        rapid.run_rapid_public_development_v19(
            repository=REPOSITORY,
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
        )


def test_rehearsal_cli_ignores_env_file(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.env"
    expected = {"execution_hash": candidate["execution_hash"], "no_call": True}
    monkeypatch.setattr(
        rapid_script,
        "rehearse_rapid_public_development_v19",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v19",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v24.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
