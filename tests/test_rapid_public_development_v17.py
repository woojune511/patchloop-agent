from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v17 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_workflow_diagnosis import _load_bundle
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v21 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]
DIAGNOSIS_PATH = REPOSITORY / (
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14-workflow-diagnosis-v1.json"
)


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v17_candidate(REPOSITORY)


def test_candidate_is_exact_zero_call_and_binds_v18_qualification(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 33_567
    assert sha256_bytes(raw) == (
        "sha256:9fe924b88abafa30c2dcb3abc6fa51271d6d22521eec16d051d3e9f07b3df877"
    )
    assert candidate["execution_hash"] == (
        "sha256:f077496605d0776d7d2f2e677391cc2ae9135550077486126258429917986c1b"
    )
    assert candidate["content_hash"] == (
        "sha256:cdad1a07ba580f82ed247e78db20411ef98a181a4bf54f5ee6a0db3e8a453725"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:16d3857fdc2cb707b5a041af076731e626e1a0bb432bd71d44cb9ba65ef2ea1c"
    )
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    activation = candidate["selection_evidence"]["causal_plan_projection_activation"]
    assert activation["path"] == (
        "experiments/lean-harness-causal-plan-projection-rapid-activation-"
        "qualification-20260826-v2.json"
    )
    assert activation["content_hash"] == (
        "sha256:b0d10f8e6118db17535ed3919571e83afd937efd676d9ed55a2914a80249d898"
    )
    assert activation["predecessor_qualification"]["content_hash"] == (
        "sha256:359b3bc8b2067bcd9b42f3c8dbbc5d8894d04a0611948c44a1d83d2995979754"
    )
    assert activation["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v18",
        "tool_schema_version": "v22",
        "context_policy_version": "phase-evidence-v28",
        "request_evidence_schema": "lean-harness-request-evidence-v18",
        "activation_policy_version": "gateway-owned-causal-plan-projection-v1",
    }
    assert activation["dynamic_model_surface"]["runtime_surface_activated"] is True
    assert activation["dynamic_model_surface"]["forbidden_server_fields_absent"] is True
    assert activation["cross_reset_evidence_boundary"]["stale_check_observation_only"] is True
    assert activation["paid_execution_authorized"] is False
    assert (
        candidate["selection_evidence"]["source_transition"]["qualified_snapshot_preserved"] is True
    )
    assert candidate["selection_evidence"]["source_transition"]["permitted_changed_paths"] == []
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-causal-activation-ab-20260826-r13-candidate-v20.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-causal-activation-ab-20260826-r13-4799bfa0afab.jsonl"
    )


def test_six_manifests_preserve_v8_v18_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    plan_decision = registry.validate_authorization_plan(plan)
    assert plan_decision.accepted is True
    assert plan_decision.verifier_id == rapid.VERIFIER_ID
    assert plan_decision.requires_row_capability is True

    counts = {"lean-harness-v8": 0, "lean-harness-v18": 0}
    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v17_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        counts[row["variant"]] += 1
        expected = (
            ("v12", "phase-evidence-v18")
            if row["variant"] == "lean-harness-v8"
            else ("v22", "phase-evidence-v28")
        )
        assert (manifest.tool_schema_version, manifest.context_policy_version) == expected
        decision = registry.verify_manifest(
            plan=plan,
            manifest=manifest,
            authorization_plan_path="<test-rehearsal>",
            authorization_plan_hash=sha256_bytes(rapid._plan_bytes(plan)),
            repository=REPOSITORY,
            runner_root=None,
            batch_validation=True,
        )
        assert decision.accepted is True
        assert decision.verifier_id == rapid.VERIFIER_ID
    assert counts == {"lean-harness-v8": 3, "lean-harness-v18": 3}


def test_consumed_rehearsal_is_exact_and_stopped_before_dispatch(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v17_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_087
    assert sha256_bytes(raw) == (
        "sha256:212c5a2890339641ebb47f0851e2cbb3ed4837306249bc0d2854f7f761ea2b58"
    )
    assert stored["content_hash"] == (
        "sha256:504757712c808f3d56e5d96e8087194316c3a2c851ef3bb90ad8b3051516c273"
    )
    assert stored["verified_manifest_count"] == 6
    assert stored["verifier_id"] == "rapid-r14-candidate-v21-plan-v21"
    assert stored["provider_calls_made"] == 0
    assert stored["docker_calls_made"] == 0
    assert stored["task_calls_made"] == 0
    assert stored["evaluator_calls_made"] == 0
    assert stored["added_model_cost_usd"] == 0.0
    assert stored["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert stored["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_consumed_result_and_public_diagnosis_are_exact(
    candidate: dict[str, Any],
) -> None:
    result_path = rapid._result_bundle_path(candidate, REPOSITORY)
    raw = result_path.read_bytes()
    events = _load_bundle(result_path)
    rows = [event for event in events if event["event"] == "row-terminal"]
    summary = events[-1]

    assert len(raw) == 9_583
    assert sha256_bytes(raw) == (
        "sha256:c00864622ac22516404c1bd1bb079e0559b0e0d6dea797b96929eec4449e39a3"
    )
    assert [row["order"] for row in rows] == list(range(1, 7))
    assert len({row["run_id"] for row in rows}) == 6
    assert summary["content_hash"] == (
        "sha256:ea519203604744c134eaa281b913df869a5a7f5d59d808241b511b41670410de"
    )
    assert summary["harness_admission_failures"] == summary["token_terminals"] == 0
    assert summary["evaluator_reached"] == summary["submissions_completed"] == 2
    assert summary["successes_at_budget"] == 0
    assert summary["model_cost_nanos"] == 1_797_960_000

    diagnosis_raw = DIAGNOSIS_PATH.read_bytes()
    diagnosis = json.loads(diagnosis_raw)
    assert len(diagnosis_raw) == 16_969
    assert sha256_bytes(diagnosis_raw) == (
        "sha256:42cedd83a425ef5beca6d0a597d7fcfe7d7243eb2890515ccc5386bca1d5cca5"
    )
    assert diagnosis["content_hash"] == (
        "sha256:fa7497f94aa5854cb28b3ca48ca16d45d2d39db59b0c71da3efa2beec96e3695"
    )
    assert diagnosis["source_bundle"]["file_sha256"] == sha256_bytes(raw)
    assert diagnosis["evidence_boundary"]["state_mutations"] == 0
    assert diagnosis["evidence_boundary"]["added_cost_nanos"] == 0


def test_candidate_tamper_and_consumed_live_entry_fail_closed(
    candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(candidate)
    changed["variant_contracts"]["lean-harness-v18"]["tool_schema_version"] = "v21"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    with pytest.raises(
        (ContractError, RecoveryError),
        match=(
            "result already exists and cannot be retried|current binding differs|"
            "causal-plan Rapid activation change surface differs"
        ),
    ):
        rapid.run_rapid_public_development_v17(
            repository=REPOSITORY,
            approve_live_cost=False,
            approved_execution_hash=None,
        )


def test_candidate_script_rehearsal_ignores_env_file(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.env"
    expected = {"execution_hash": candidate["execution_hash"], "no_call": True}
    monkeypatch.setattr(
        rapid_script,
        "rehearse_rapid_public_development_v17",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v17",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v21.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
