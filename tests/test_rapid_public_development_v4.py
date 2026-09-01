from __future__ import annotations

import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from patchloop.agent.runner import (
    AgentRunner,
    issue_live_execution_authorization,
    issue_row_execution_authorization,
)
from patchloop.errors import ContractError, HarnessAdmissionError
from patchloop.evals import rapid_public_development_v4 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.build_rapid_public_development_v4_candidate(repository=REPOSITORY)


def _persist_plan(candidate: dict[str, Any], runtime: Path) -> None:
    plan = rapid._plan(candidate, approved=True)
    path = (
        runtime
        / "experiments"
        / "plans"
        / f"{candidate['execution_hash'].removeprefix('sha256:')}.json"
    )
    path.parent.mkdir(parents=True)
    path.write_bytes(rapid._plan_bytes(plan))


def test_candidate_uses_compact_runtime_config_task_and_image_bindings(
    candidate: dict[str, Any],
) -> None:
    assert candidate["candidate_revision"] == 6
    assert candidate["official"] is False
    assert candidate["rehearsal_required"] is True
    assert candidate["runtime_build_schema"] == "rapid-runtime-build-v1"
    assert candidate["runtime_build_hash"].startswith("sha256:")
    assert candidate["config_file_sha256"].startswith("sha256:")
    assert candidate["config_semantic_hash"].startswith("sha256:")
    assert "source_files" not in candidate
    assert "validation_files" not in candidate
    assert "runtime_dependencies" not in candidate
    assert all(
        item["package_inventory_hash"].startswith("sha256:")
        for item in candidate["task_bindings"]
    )
    assert all(
        item["evaluator_image_digest"].startswith("sha256:")
        for item in candidate["task_bindings"]
    )
    assert candidate["predecessor_candidate"]["path"].endswith("candidate-v5.json")
    assert candidate["predecessor_terminal"]["path"].endswith(
        "harness-admission-terminal-v3.json"
    )


def test_runner_has_one_registry_dispatch_instead_of_experiment_id_branches() -> None:
    source = inspect.getsource(AgentRunner._live_plan_matches_manifest)
    assert "live_verifier_registry" in source
    assert "rapid-public-dev" not in source
    assert "heldout_ac_live_plan_matches_manifest" not in source
    descriptors = live_verifier_registry().descriptors()
    assert any(item["verifier_id"] == rapid.VERIFIER_ID for item in descriptors)


def test_registry_rejects_known_experiment_with_incompatible_schema_before_run(
    candidate: dict[str, Any],
) -> None:
    plan = rapid._plan(candidate, approved=True)
    body = {
        **{key: value for key, value in plan.items() if key != "content_hash"},
        "schema_version": "experiment-execution-plan-v999",
    }
    tampered = {**body, "content_hash": rapid.sha256_json(body)}
    decision = live_verifier_registry().validate_authorization_plan(tampered)
    assert decision.handled is True
    assert decision.accepted is False

    missing_identity_body = {
        key: value
        for key, value in rapid._plan(candidate, approved=True).items()
        if key not in {"content_hash", "experiment_id"}
    }
    missing_identity = {
        **missing_identity_body,
        "content_hash": rapid.sha256_json(missing_identity_body),
    }
    manifest = rapid.build_rapid_v4_run_manifest(candidate, 1, repository=REPOSITORY)
    row_decision = live_verifier_registry().verify_manifest(
        plan=missing_identity,
        manifest=manifest,
        authorization_plan_path="synthetic",
        authorization_plan_hash="sha256:" + "0" * 64,
        repository=REPOSITORY,
        runner_root=None,
        batch_validation=True,
    )
    assert row_decision.handled is True
    assert row_decision.accepted is False


def test_batch_prevalidates_all_rows_and_row_capability_is_one_use(
    candidate: dict[str, Any],
) -> None:
    prepared = rapid._prepare_batch(
        candidate,
        authority_kind="rehearsal",
        repository=REPOSITORY,
    )
    assert len(prepared.manifests) == 8
    assert prepared.verifier_id == rapid.VERIFIER_ID
    row = issue_row_execution_authorization(
        prepared.authorization,
        prepared.manifests[0],
        active_schedule_order=1,
    )
    boundary = AgentRunner.rehearse_provider_dispatch(prepared.manifests[0], row)
    assert boundary["provider_dispatch_blocked"] is True
    with pytest.raises(HarnessAdmissionError, match="already consumed"):
        AgentRunner.rehearse_provider_dispatch(prepared.manifests[0], row)


def test_manifest_identity_is_deterministic_across_batch_rebuilds(
    candidate: dict[str, Any],
) -> None:
    left = rapid.build_rapid_v4_run_manifest(candidate, 1, repository=REPOSITORY)
    right = rapid.build_rapid_v4_run_manifest(candidate, 1, repository=REPOSITORY)
    assert left.created_at == right.created_at == rapid.MANIFEST_CREATED_AT
    assert left.model_dump(mode="json") == right.model_dump(mode="json")


def test_active_prefix_accepts_real_runtime_official_boolean_after_row_one(
    candidate: dict[str, Any],
) -> None:
    start = rapid._seal_event(rapid._batch_started_event(candidate), None)
    resolved = rapid._rehearsed_resolved_terminal(
        candidate,
        start["content_hash"],
    )
    assert resolved["bundle_official"] is False
    assert resolved["runtime_result_official"] is True
    assert rapid._active_bundle_next_order_from_events(candidate, [start, resolved]) == 2

    terminal_body = {
        key: value
        for key, value in resolved.items()
        if key not in {"content_hash", "previous_event_hash"}
    }
    non_official_runtime = rapid._seal_event(
        {**terminal_body, "runtime_result_official": False},
        start["content_hash"],
    )
    assert (
        rapid._active_bundle_next_order_from_events(
            candidate,
            [start, non_official_runtime],
        )
        == 2
    )

    malformed_runtime = rapid._seal_event(
        {**terminal_body, "runtime_result_official": None},
        start["content_hash"],
    )
    assert (
        rapid._active_bundle_next_order_from_events(
            candidate,
            [start, malformed_runtime],
        )
        is None
    )


def test_live_row_capability_does_not_reconstruct_candidate(
    candidate: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    _persist_plan(candidate, runtime)
    live = issue_live_execution_authorization(candidate["execution_hash"], root=runtime)
    prepared = rapid._prepare_batch(
        candidate,
        authority_kind="live",
        live_authorization=live,
        repository=REPOSITORY,
    )
    row = issue_row_execution_authorization(
        prepared.authorization,
        prepared.manifests[0],
        active_schedule_order=1,
    )
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v4_candidate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("row admission must not reload the candidate")
        ),
    )
    monkeypatch.setattr(rapid.DockerSandbox, "available", staticmethod(lambda: False))
    runner = AgentRunner(tmp_path / "runner")
    with pytest.raises(ContractError, match="digest-pinned Docker evaluator image"):
        runner.start(
            candidate["schedule"][0]["task"],
            model="openai",
            manifest=prepared.manifests[0],
            live_authorization=live,
            row_execution_authorization=row,
        )
    with pytest.raises(HarnessAdmissionError, match="already consumed"):
        runner.start(
            candidate["schedule"][0]["task"],
            model="openai",
            manifest=prepared.manifests[0],
            live_authorization=live,
            row_execution_authorization=row,
        )


def test_rehearsal_reaches_second_dispatch_after_realistic_terminal_without_external_calls(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = TemporaryDirectory(prefix="rapid-v4-rehearse-", dir=REPOSITORY / ".p")
    receipt_path = Path(temporary.name) / "rehearsal.json"
    monkeypatch.setattr(
        rapid,
        "REHEARSAL_PATH",
        receipt_path.relative_to(REPOSITORY),
    )
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v4_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))),
    )
    monkeypatch.setattr(
        rapid.OpenAIResponsesAdapter,
        "execute_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("provider must not be called")
        ),
    )
    receipt = rapid.rehearse_rapid_public_development_v4(repository=REPOSITORY)
    assert receipt["verified_manifest_count"] == 8
    assert (
        receipt["stopped_before"]
        == "second-provider-dispatch-after-resolved-prefix"
    )
    assert receipt["first_provider_boundary"]["provider_dispatch_blocked"] is True
    transition = receipt["inter_row_transition"]
    assert transition["prior_terminal_content_hash"].startswith("sha256:")
    assert {
        key: value
        for key, value in transition.items()
        if key != "prior_terminal_content_hash"
    } == {
        "prior_outcome_kind": "resolved",
        "prior_runtime_result_official": True,
        "prior_bundle_official": False,
        "next_schedule_order": 2,
    }
    assert receipt["second_provider_boundary"]["schedule_order"] == 2
    assert receipt["second_provider_boundary"]["provider_dispatch_blocked"] is True
    assert receipt["provider_calls_made"] == receipt["docker_calls_made"] == 0
    assert receipt["task_calls_made"] == receipt["evaluator_calls_made"] == 0
    assert receipt_path.is_file()
    temporary.cleanup()


def test_live_entry_requires_rehearsal_before_credentials_or_docker(
    candidate: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v4_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: tmp_path / "missing")
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v4_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HarnessAdmissionError("synthetic missing rehearsal")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))),
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(HarnessAdmissionError, match="synthetic missing rehearsal"):
        rapid.run_rapid_public_development_v4(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_contract_terminal_is_counted_outside_agent_failure_rate(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = TemporaryDirectory(prefix="rapid-v4-terminal-", dir=REPOSITORY / ".p")
    bundle = Path(temporary.name) / "run.jsonl"
    prepared = rapid._prepare_batch(
        candidate,
        authority_kind="rehearsal",
        repository=REPOSITORY,
    )
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v4_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: bundle)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v4_rehearsal",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(rapid, "_write_or_validate_plan", lambda *_args: Path("plan"))
    monkeypatch.setattr(
        rapid,
        "issue_live_execution_authorization",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(rapid, "_prepare_batch", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(rapid.DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "image_identity",
        lambda self: self.image.rsplit("@", maxsplit=1)[1],
    )
    monkeypatch.setattr(
        rapid.AgentRunner,
        "start",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HarnessAdmissionError("synthetic row admission rejection")
        ),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    summary = rapid.run_rapid_public_development_v4(
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
        repository=REPOSITORY,
    )
    events = [json.loads(line) for line in bundle.read_text(encoding="utf-8").splitlines()]
    terminal = events[1]
    assert terminal["outcome_kind"] == rapid.HARNESS_ADMISSION_FAILURE
    assert terminal["harness_admission_failure"] is True
    assert terminal["agent_started"] is False
    assert summary["harness_admission_failures"] == 1
    assert summary["agent_rows_started"] == summary["agent_failures"] == 0
    assert summary["agent_failure_rate"] is None
    temporary.cleanup()
