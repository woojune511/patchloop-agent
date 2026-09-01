from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v16 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v20 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v16_candidate(REPOSITORY)


def test_candidate_is_exact_zero_call_and_binds_v17_qualification(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 33_862
    assert sha256_bytes(raw) == (
        "sha256:9d4f10276923b8ec19f5566438196c280efa10ae96047d40eaa82f4ef1001eee"
    )
    assert candidate["execution_hash"] == (
        "sha256:4799bfa0afaba2aeff57ae33d06eb676b4272251847c087515b4a3280fc936b3"
    )
    assert candidate["content_hash"] == (
        "sha256:28e36bdafeaba1e2c901598195611054f64201de20228c7a0a0600b684fe1c0d"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:87576db9ca01d9f1b3fc82d6453585d99116bc7d3fc9359d01ce662d905bcf80"
    )
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    activation = selection["causal_activation"]
    assert activation["predecessor_qualification"] == {
        "path": (
            "experiments/lean-harness-causal-alternative-activation-public-"
            "qualification-20260826-v1.json"
        ),
        "bytes": 5_235,
        "file_sha256": ("sha256:72576cdcf05a9337bcee415d3200bfe76f04fd8b13b3231b02140fb6b2cd448e"),
        "content_hash": ("sha256:45f469b256c50b7259b7c1df6a59e3b4fe8f598f67733ef93a96733b72191f85"),
    }
    assert activation["runtime_identity"] == {
        "activation_policy_version": "gateway-owned-causal-baseline-reset-v1",
        "context_policy_version": "phase-evidence-v27",
        "request_evidence_schema": "lean-harness-request-evidence-v17",
        "runtime_policy_version": "lean-harness-v17",
        "tool_schema_version": "v21",
    }
    assert activation["generic_plan_surface"]["exception_specific_key_present"] is False
    assert activation["generic_plan_surface"]["task_specific_field_names"] == []
    assert activation["restore_trigger"]["failure_events_deleted"] is False
    assert activation["source_transition"]["observed_changed_paths"] == [
        "patchloop/contracts.py",
        "tests/test_workflow_causal_alternative_activation_qualification.py",
    ]
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-causal-activation-ab-20260826-r13-candidate-v19.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-semantic-progress-ab-20260825-r12-4d4fbf5839ed.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_six_manifests_preserve_v8_v17_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    plan_decision = registry.validate_authorization_plan(plan)
    assert plan_decision.accepted is True
    assert plan_decision.verifier_id == rapid.VERIFIER_ID
    assert plan_decision.requires_row_capability is True

    counts = {"lean-harness-v8": 0, "lean-harness-v17": 0}
    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v16_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        counts[row["variant"]] += 1
        expected = (
            ("v12", "phase-evidence-v18")
            if row["variant"] == "lean-harness-v8"
            else ("v21", "phase-evidence-v27")
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
    assert counts == {"lean-harness-v8": 3, "lean-harness-v17": 3}


def test_consumed_rehearsal_is_exact_and_stopped_before_dispatch(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v16_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_082
    assert sha256_bytes(raw) == (
        "sha256:08693a6a3e7e2f72e9eb09e55e819dffd70541202d8db77f346d3b115f87382b"
    )
    assert stored["content_hash"] == (
        "sha256:cca31b6c9838bc952a098dc3c244130cad3f629bf0f76c77dc253057bf731061"
    )
    assert stored["verified_manifest_count"] == 6
    assert stored["verifier_id"] == "rapid-r13-candidate-v20-plan-v20"
    assert stored["provider_calls_made"] == 0
    assert stored["docker_calls_made"] == 0
    assert stored["task_calls_made"] == 0
    assert stored["evaluator_calls_made"] == 0
    assert stored["added_model_cost_usd"] == 0.0
    assert stored["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert stored["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_candidate_tamper_and_unapproved_live_entry_fail_closed(
    candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(candidate)
    changed["variant_contracts"]["lean-harness-v17"]["tool_schema_version"] = "v20"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    with pytest.raises(
        (ContractError, RecoveryError),
        match=(
            "result already exists and cannot be retried|current binding differs|"
            "causal Rapid activation change surface differs"
        ),
    ):
        rapid.run_rapid_public_development_v16(
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
        "rehearse_rapid_public_development_v16",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v16",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v20.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
