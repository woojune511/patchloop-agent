from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v18 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v23 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v18_candidate(REPOSITORY)


def test_candidate_is_exact_consumed_zero_call_anyio_v5_v18_v19(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()

    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 18_887
    assert sha256_bytes(raw) == (
        "sha256:2eeeeeecc9fc1188ab4bc164c3539a3806210b91a8fb62caed351c64b297b9cf"
    )
    assert candidate["execution_hash"] == (
        "sha256:3e5890091927889b27433c6f0fdb65de5ccfb1256d10033fab25a65fbbf30a37"
    )
    assert candidate["content_hash"] == (
        "sha256:33bdb0ed55442c679152868d1f12a04204b95c10c6184716b21d067a27797289"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:aa29a646f00784a139a8d28ffaa418c841e88e5782c0eefbe777c100199773d6"
    )
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == 0
    assert candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0
    assert tuple(candidate["variant_contracts"]) == (
        "lean-harness-v18",
        "lean-harness-v19",
    )
    binding = candidate["task_bindings"][0]
    assert binding["task_version"] == 5
    assert binding["visible_check_ids"] == [
        "public-interrupt-runner-lifecycle",
        "public-ordinary-failure-preservation",
        "upstream-pytest-plugin-regression",
    ]
    assert candidate["execution_hash"] == sha256_json(rapid._execution_body(candidate))
    with pytest.raises(ContractError, match="source changes differ"):
        rapid.load_rapid_public_development_v18_candidate(REPOSITORY)


def test_candidate_binds_public_baseline_and_zero_call_successors(
    candidate: dict[str, Any],
) -> None:
    evidence = candidate["selection_evidence"]

    assert evidence["baseline_role"] == (
        "v18-public-development-workflow-baseline-not-quality-baseline"
    )
    assert evidence["baseline_candidate"]["execution_hash"] == rapid.PREDECESSOR_EXECUTION_HASH
    assert evidence["baseline_result"]["v18_evaluator_reached"] == 2
    assert evidence["baseline_result"]["v18_submissions_completed"] == 2
    assert evidence["baseline_result"]["v18_successes_at_budget"] == 0
    assert evidence["three_check_compatibility"]["content_hash"] == (
        rapid.THREE_CHECK_QUALIFICATION_CONTENT_HASH
    )
    assert evidence["superseded_zero_call_candidate"]["execution_hash"] == (
        rapid.SUPERSEDED_EXECUTION_HASH
    )
    assert evidence["superseded_zero_call_candidate"]["paid_execution_authorized"] is False
    activation = evidence["exploration_gate_activation"]
    assert activation["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v19",
        "tool_schema_version": "v23",
        "context_policy_version": "phase-evidence-v29",
        "request_evidence_schema": "lean-harness-request-evidence-v19",
        "exploration_gate_policy_version": "public-boundary-and-unknown-closure-v1",
        "activation_policy_version": "gateway-owned-public-exploration-closure-v1",
    }
    assert activation["source_preservation"]["lean_v18_behavior_modified"] is False
    assert activation["evidence_boundary"]["provider_calls"] == 0
    assert activation["paid_execution_authorized"] is False


def test_six_manifests_preserve_v18_v19_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    decision = registry.validate_authorization_plan(plan)
    assert decision.accepted is True
    assert decision.verifier_id == rapid.VERIFIER_ID
    assert decision.requires_row_capability is True

    counts = {"lean-harness-v18": 0, "lean-harness-v19": 0}
    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v18_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        counts[row["variant"]] += 1
        expected = (
            ("v22", "phase-evidence-v28")
            if row["variant"] == "lean-harness-v18"
            else ("v23", "phase-evidence-v29")
        )
        assert (manifest.tool_schema_version, manifest.context_policy_version) == expected
        assert manifest.task_version == 5
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
    assert counts == {"lean-harness-v18": 3, "lean-harness-v19": 3}


def test_consumed_rehearsal_is_exact_and_stops_before_provider_dispatch(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v18_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_079
    assert sha256_bytes(raw) == (
        "sha256:4675cfdcd0b6b264749ce61fb97df9ad66eab7492ca3af6fdd79dd6f51067683"
    )
    assert stored["content_hash"] == (
        "sha256:be1f1f360f8d78e4c3e43074793154d1e0ac98ad259df1f980bff5e269bfa5e0"
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
        rapid.build_rapid_public_development_v18_rehearsal(repository=REPOSITORY)


def test_candidate_tamper_and_consumed_live_entry_fail_closed(
    candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(candidate)
    changed["variant_contracts"]["lean-harness-v19"]["tool_schema_version"] = "v22"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    with pytest.raises(ContractError, match="source changes differ"):
        rapid.run_rapid_public_development_v18(
            repository=REPOSITORY,
            approve_live_cost=False,
            approved_execution_hash=None,
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
        "rehearse_rapid_public_development_v18",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v18",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v23.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
