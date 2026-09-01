from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent.runner import issue_live_execution_authorization
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v20 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v25 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v20_candidate(REPOSITORY)


def test_consumed_candidate_is_an_exact_byte_audit_and_preserves_r16(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    predecessor_raw = (REPOSITORY / rapid.PREDECESSOR_CANDIDATE_PATH).read_bytes()
    result_raw = (REPOSITORY / rapid.PREDECESSOR_RESULT_PATH).read_bytes()

    assert len(raw) == rapid.CONSUMED_CANDIDATE_BYTES
    assert sha256_bytes(raw) == rapid.CONSUMED_CANDIDATE_FILE_SHA256
    assert candidate["content_hash"] == rapid.CONSUMED_CANDIDATE_CONTENT_HASH
    assert candidate["execution_hash"] == rapid.CONSUMED_EXECUTION_HASH
    assert rapid.candidate_bytes(candidate) == raw
    assert candidate["execution_hash"] == sha256_json(rapid._execution_body(candidate))
    assert candidate["provider_calls_made"] == 0
    assert candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0
    assert candidate["official"] is False
    assert candidate["driver_contract"]["policy_version"] == (
        "append-only-row-settlement-driver-v1"
    )
    assert candidate["selection_evidence"]["changed_experiment_variable"] == (
        "append-only-row-settlement-driver-only"
    )
    assert len(predecessor_raw) == rapid.PREDECESSOR_CANDIDATE_BYTES
    assert sha256_bytes(predecessor_raw) == rapid.PREDECESSOR_CANDIDATE_FILE_SHA256
    assert len(result_raw) == rapid.PREDECESSOR_RESULT_BYTES
    assert sha256_bytes(result_raw) == rapid.PREDECESSOR_RESULT_FILE_SHA256


def test_registry_validates_all_six_exact_manifests(candidate: dict[str, Any]) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    decision = registry.validate_authorization_plan(plan)

    assert decision.accepted is True
    assert decision.verifier_id == rapid.VERIFIER_ID
    assert decision.requires_row_capability is True
    observed: list[tuple[str, str]] = []
    for order in range(1, 7):
        manifest = rapid.build_rapid_v20_run_manifest(candidate, order, repository=REPOSITORY)
        observed.append((manifest.tool_schema_version, manifest.context_policy_version))
        verified = registry.verify_manifest(
            plan=plan,
            manifest=manifest,
            authorization_plan_path="<offline-test>",
            authorization_plan_hash=sha256_bytes(rapid._plan_bytes(plan)),
            repository=REPOSITORY,
            runner_root=None,
            batch_validation=True,
        )
        assert verified.accepted is True
        assert verified.verifier_id == rapid.VERIFIER_ID
    assert observed == [
        ("v22", "phase-evidence-v28"),
        ("v24", "phase-evidence-v30"),
        ("v24", "phase-evidence-v30"),
        ("v22", "phase-evidence-v28"),
        ("v22", "phase-evidence-v28"),
        ("v24", "phase-evidence-v30"),
    ]


def test_rehearsal_is_deterministic_and_advances_only_after_decision(
    candidate: dict[str, Any],
) -> None:
    first = rapid._build_rehearsal_for(candidate, repository=REPOSITORY)
    second = rapid._build_rehearsal_for(candidate, repository=REPOSITORY)

    assert rapid.rehearsal_bytes(first) == rapid.rehearsal_bytes(second)
    assert first["verified_manifest_count"] == 6
    assert first["provider_calls_made"] == 0
    assert first["docker_calls_made"] == 0
    assert first["task_calls_made"] == 0
    assert first["evaluator_calls_made"] == 0
    assert first["visible_check_calls_made"] == 0
    assert first["first_row_capability"]["provider_dispatch_rehearsed"] is True
    assert first["inter_row_transition"]["decision"] == "continue"
    assert first["inter_row_transition"]["decision_persisted_before_capability"] is True
    assert first["second_row_capability"]["schedule_order"] == 2
    assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_candidate_runtime_delegates_row_advance_to_append_only_driver(
    candidate: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumed_result = rapid._result_bundle_path(candidate, REPOSITORY)
    consumed_result_raw = consumed_result.read_bytes()
    plan_root = tmp_path / "authority"
    plan_path = (
        plan_root
        / "experiments"
        / "plans"
        / f"{candidate['execution_hash'].removeprefix('sha256:')}.json"
    )
    plan_path.parent.mkdir(parents=True)
    plan_path.write_bytes(rapid._plan_bytes(rapid._plan(candidate, approved=True)))
    live = issue_live_execution_authorization(candidate["execution_hash"], root=plan_root)
    prepared = rapid._prepare_batch(
        candidate,
        authority_kind="live",
        live_authorization=live,
        repository=REPOSITORY,
    )
    observed: dict[str, Any] = {}

    def fake_driver(**kwargs: Any) -> dict[str, Any]:
        observed.update(kwargs)
        return {
            "event": "batch-halted",
            "reason_codes": ["OFFLINE_WIRING_TEST"],
            "official": False,
        }

    monkeypatch.setattr(rapid, "run_append_only_rapid_batch_driver", fake_driver)
    runner = rapid.AgentRunner(tmp_path / "runner")
    terminal = rapid._run_prepared_driver(
        candidate=candidate,
        prepared=prepared,
        live_authorization=live,
        runner=runner,
        repository=REPOSITORY,
    )

    assert terminal["event"] == "batch-halted"
    assert observed["contract"].policy_version == ("append-only-row-settlement-driver-v1")
    assert observed["contract"].execution_hash == candidate["execution_hash"]
    assert len(observed["manifests"]) == 6
    assert tuple(observed["schedule_rows"]) == tuple(candidate["schedule"])
    assert callable(observed["execute_row"])
    assert callable(observed["project_row"])
    assert Path(observed["journal_path"]) == consumed_result
    assert consumed_result.read_bytes() == consumed_result_raw


def test_candidate_and_manifest_tamper_fail_closed(candidate: dict[str, Any]) -> None:
    changed = copy.deepcopy(candidate)
    changed["driver_contract"]["row_advance_owner"] = "manual-loop"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    body = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(body)
    with pytest.raises(RecoveryError, match="identity differs"):
        rapid._validate_candidate(changed)

    manifest = rapid.build_rapid_v20_run_manifest(candidate, 1, repository=REPOSITORY)
    payload = manifest.model_dump(mode="python")
    payload["experiment"]["schedule_order"] = 2
    changed_manifest = type(manifest).model_validate(payload)
    assert (
        rapid.rapid_v20_registered_plan_matches_manifest(
            plan=rapid._plan(candidate, approved=True),
            manifest=changed_manifest,
            repository=REPOSITORY,
        )
        is False
    )


def test_live_entry_requires_exact_approval_before_external_preflight(
    candidate: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    if not (REPOSITORY / rapid.CANDIDATE_PATH).exists():
        pytest.skip("candidate artifact is materialized only after offline source gates")
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: pytest.fail("Docker preflight ran before exact approval")),
    )
    with pytest.raises((ContractError, RecoveryError), match="source binding differs"):
        rapid.run_rapid_public_development_v20(
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
        "rehearse_rapid_public_development_v20",
        lambda **_: expected,
    )
    monkeypatch.setattr(
        rapid_script,
        "run_rapid_public_development_v20",
        lambda **_: pytest.fail("execute callback was dispatched"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_rapid_public_development_v25.py",
            "--mode",
            "rehearse",
            "--env-file",
            str(missing),
        ],
    )

    rapid_script.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
