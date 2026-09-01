from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import DatasetRole, MemoryCondition, RunManifest
from patchloop.errors import ContractError
from patchloop.evals import rapid_public_development_v3 as rapid
from patchloop.util import canonical_json, sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.build_rapid_public_development_v3_candidate(repository=REPOSITORY)


def test_candidate_is_public_development_only_and_external_call_closed(
    candidate: dict[str, Any],
) -> None:
    assert candidate["candidate_revision"] == 3
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0
    assert candidate["approval_required"] is True

    selection = candidate["selection_evidence"]
    assert selection["official"] is False
    assert selection["heldout_outcomes_used"] is False
    assert selection["private_evidence_used"] is False
    assert [(row["task_id"], row["selection_role"]) for row in selection["tasks"]] == [
        ("pdm-ignore-active-venv-resolution", "non-ceiling-anchor"),
        ("anyio-interrupt-runner-cleanup", "completion-stress"),
    ]

    bindings = candidate["task_bindings"]
    assert [item["task_id"] for item in bindings] == [
        "pdm-ignore-active-venv-resolution",
        "anyio-interrupt-runner-cleanup",
    ]
    assert {item["task_version"] for item in bindings} == {1}
    assert all(item["task_package_modified"] is False for item in bindings)
    assert [item["visible_check_ids"] for item in bindings] == [
        ["upstream-project-regression"],
        ["upstream-pytest-plugin-regression"],
    ]


def test_candidate_binds_the_live_boundary_terminal_without_rewriting_it(
    candidate: dict[str, Any],
) -> None:
    predecessor = REPOSITORY / rapid.PREDECESSOR_CANDIDATE_PATH
    terminal = REPOSITORY / rapid.PREDECESSOR_TERMINAL_PATH

    assert candidate["predecessor_candidate"] == {
        "path": rapid.PREDECESSOR_CANDIDATE_PATH.as_posix(),
        "file_bytes": 13_742,
        "file_sha256": (
            "sha256:91f52564d6e7d86b75f62ac0f92528b94b517a41c902267342e9e948b5c16d88"
        ),
    }
    assert candidate["predecessor_terminal"] == {
        "path": rapid.PREDECESSOR_TERMINAL_PATH.as_posix(),
        "file_bytes": 3_733,
        "file_sha256": (
            "sha256:35259a5117f891646855dbd01399f34836d570d2fdaec1fc54dfc43f03facc03"
        ),
    }
    assert sha256_bytes(predecessor.read_bytes()) == candidate["predecessor_candidate"][
        "file_sha256"
    ]
    assert sha256_bytes(terminal.read_bytes()) == candidate["predecessor_terminal"][
        "file_sha256"
    ]


def test_candidate_binds_exact_schedule_runtime_and_cost(
    candidate: dict[str, Any],
) -> None:
    schedule = candidate["schedule"]
    assert len(schedule) == 8
    assert [row["order"] for row in schedule] == list(range(1, 9))
    assert {
        (row["task"], row["variant"], row["repetition"]) for row in schedule
    } == {
        (task, variant, repetition)
        for task in rapid.TASK_PATHS
        for variant in rapid.VARIANTS
        for repetition in (1, 2)
    }
    assert candidate["variant_contracts"]["lean-harness-v2"] == {
        "tool_schema_version": "v8",
        "context_policy_version": "phase-evidence-v13",
        "runtime_policy_version": "lean-harness-v2",
        "completion_policy_version": "completion-driven-current-diff-v1",
        "patch_normalization_policy_version": "safe-raw-diff-normalization-v1",
    }
    assert candidate["cost_control"]["per_run_reserve_nanos"] == 1_200_000_000
    assert candidate["cost_control"]["full_schedule_reserve_nanos"] == 9_600_000_000
    assert candidate["cost_control"]["hard_cap_nanos"] == 10_000_000_000


def test_all_manifests_match_and_pairs_only_change_runtime(
    candidate: dict[str, Any],
) -> None:
    manifests = [
        rapid.build_rapid_v3_run_manifest(candidate, order, repository=REPOSITORY)
        for order in range(1, 9)
    ]
    assert all(rapid._manifest_matches_candidate(candidate, item) for item in manifests)

    for task in rapid.TASK_PATHS:
        for repetition in (1, 2):
            orders = [
                row["order"]
                for row in candidate["schedule"]
                if row["task"] == task and row["repetition"] == repetition
            ]
            left, right = (manifests[order - 1] for order in orders)
            assert left.task_id == right.task_id
            assert left.task_version == right.task_version == 1
            assert left.model == right.model
            assert left.budget == right.budget == rapid.RUNTIME_BUDGET
            assert left.memory.condition == right.memory.condition == MemoryCondition.NO_MEMORY
            assert left.memory.index_hash is None and right.memory.index_hash is None
            assert left.public_spec_hash == right.public_spec_hash
            assert left.private_spec_hash == right.private_spec_hash
            assert left.base_commit == right.base_commit
            assert {
                (left.tool_schema_version, left.context_policy_version),
                (right.tool_schema_version, right.context_policy_version),
            } == {("v2", "phase-evidence-v5"), ("v8", "phase-evidence-v13")}
            assert left.experiment is not None and right.experiment is not None
            assert left.experiment.dataset_role == right.experiment.dataset_role == (
                DatasetRole.MEMORY_DEVELOPMENT
            )
            assert AgentRunner._runtime_contract(left)[0] == AgentRunner._runtime_contract(right)[0]


def test_manifest_matcher_rejects_schedule_drift(candidate: dict[str, Any]) -> None:
    manifest = rapid.build_rapid_v3_run_manifest(candidate, 2, repository=REPOSITORY)
    payload = manifest.model_dump(mode="python")
    payload["experiment"]["schedule_row_id"] = candidate["schedule"][0][
        "schedule_row_id"
    ]
    tampered = RunManifest.model_validate(payload)

    assert not rapid._manifest_matches_candidate(candidate, tampered)


def test_common_capability_gate_accepts_only_the_exact_rapid_v3_plan_kind(
    candidate: dict[str, Any],
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    plan = rapid._plan(candidate, approved=True)
    path = (
        runtime
        / "experiments"
        / "plans"
        / f"{candidate['execution_hash'].removeprefix('sha256:')}.json"
    )
    path.parent.mkdir(parents=True)
    path.write_text(canonical_json(plan) + "\n", encoding="utf-8")

    authorization = issue_live_execution_authorization(
        candidate["execution_hash"],
        root=runtime,
    )
    assert authorization.execution_hash == candidate["execution_hash"]
    assert authorization.plan_path == str(path)

    tampered = {**plan, "plan_kind": "unregistered-plan-kind"}
    path.write_text(canonical_json(tampered) + "\n", encoding="utf-8")
    with pytest.raises(ContractError, match="does not authorize"):
        issue_live_execution_authorization(candidate["execution_hash"], root=runtime)


def test_capability_gate_precedes_credentials_and_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v3_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        rapid,
        "_write_or_validate_plan",
        lambda *_args, **_kwargs: REPOSITORY / ".patchloop" / "synthetic-plan.json",
    )
    monkeypatch.setattr(
        rapid,
        "issue_live_execution_authorization",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ContractError("synthetic capability rejection")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called")),
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ContractError, match="synthetic capability rejection"):
        rapid.run_rapid_public_development_v3(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_paid_matcher_requires_the_exact_active_next_row_prefix(
    candidate: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "active.jsonl"
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: bundle)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v3_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    first = rapid.build_rapid_v3_run_manifest(candidate, 1, repository=REPOSITORY)
    second = rapid.build_rapid_v3_run_manifest(candidate, 2, repository=REPOSITORY)
    plan = rapid._plan(candidate, approved=True)

    assert not rapid.rapid_v3_live_plan_matches_manifest(
        plan=plan,
        manifest=first,
        repository=REPOSITORY,
    )
    rapid._append_bundle_event(bundle, rapid._batch_started_event(candidate), create=True)
    assert rapid.rapid_v3_live_plan_matches_manifest(
        plan=plan,
        manifest=first,
        repository=REPOSITORY,
    )
    assert not rapid.rapid_v3_live_plan_matches_manifest(
        plan=plan,
        manifest=second,
        repository=REPOSITORY,
    )

    runtime = tmp_path / "runtime"
    plan_path = (
        runtime
        / "experiments"
        / "plans"
        / f"{candidate['execution_hash'].removeprefix('sha256:')}.json"
    )
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(canonical_json(plan) + "\n", encoding="utf-8")
    authorization = issue_live_execution_authorization(
        candidate["execution_hash"],
        root=runtime,
    )
    AgentRunner._require_live_authorization(first, authorization)

    rapid._append_bundle_event(
        bundle,
        {
            "schema_version": rapid.RESULT_SCHEMA,
            "event": "row-terminal",
            **candidate["schedule"][0],
            "run_id": f"run_rapid_v3_{candidate['execution_hash'][7:19]}_01",
            "bundle_official": False,
            "runtime_result_official": False,
            "outcome_kind": "task_failure",
        },
    )
    assert not rapid.rapid_v3_live_plan_matches_manifest(
        plan=plan,
        manifest=first,
        repository=REPOSITORY,
    )
    assert rapid.rapid_v3_live_plan_matches_manifest(
        plan=plan,
        manifest=second,
        repository=REPOSITORY,
    )

    tampered_plan = json.loads(json.dumps(plan))
    tampered_plan["schedule"][1]["context_policy_version"] = "phase-evidence-v12"
    assert not rapid.rapid_v3_live_plan_matches_manifest(
        plan=tampered_plan,
        manifest=second,
        repository=REPOSITORY,
    )

    rapid._append_bundle_event(
        bundle,
        {
            "schema_version": rapid.RESULT_SCHEMA,
            "event": "batch-completed",
            "official": False,
        },
    )
    assert not rapid.rapid_v3_live_plan_matches_manifest(
        plan=plan,
        manifest=second,
        repository=REPOSITORY,
    )


def test_live_entry_creates_an_authorizing_prefix_before_the_first_row(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = TemporaryDirectory(prefix="rapid-v3-entry-", dir=REPOSITORY / ".p")
    bundle = Path(temporary.name) / "run.jsonl"
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: bundle)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v3_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        rapid,
        "_write_or_validate_plan",
        lambda *_args: Path(temporary.name) / "plan",
    )
    monkeypatch.setattr(
        rapid,
        "issue_live_execution_authorization",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(rapid, "_persisted_result", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(rapid.DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "image_identity",
        lambda self: self.image.rsplit("@", maxsplit=1)[1],
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")

    def fail_after_match(
        _runner: AgentRunner,
        _task: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        manifest = kwargs["manifest"]
        assert rapid.rapid_v3_live_plan_matches_manifest(
            plan=rapid._plan(candidate, approved=True),
            manifest=manifest,
            repository=REPOSITORY,
        )
        raise ContractError("synthetic terminal after paid-boundary match")

    monkeypatch.setattr(rapid.AgentRunner, "start", fail_after_match)
    summary = rapid.run_rapid_public_development_v3(
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
        repository=REPOSITORY,
    )

    assert summary["started_rows"] == 1
    assert summary["model_calls"] == summary["tool_calls"] == 0
    events = [json.loads(line) for line in bundle.read_text(encoding="utf-8").splitlines()]
    assert events[1]["error_message"] == "synthetic terminal after paid-boundary match"
    assert [event["event"] for event in events] == [
        "batch-started",
        "row-terminal",
        *("row-not-started" for _ in range(7)),
        "batch-completed",
    ]
    temporary.cleanup()


def test_live_entry_fails_before_credentials_or_docker_without_exact_approval(
    candidate: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v3_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: tmp_path / "missing")
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called")),
    )
    with pytest.raises(ContractError, match="exact hash and cost-cap approval"):
        rapid.run_rapid_public_development_v3(
            approve_live_cost=False,
            approved_execution_hash=None,
            repository=REPOSITORY,
        )


def test_consumed_result_stops_before_credentials_or_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = (
        REPOSITORY
        / "reports"
        / "rapid-development"
        / "rapid-public-dev-lean-harness-20260821-r2-f066bd044465.jsonl"
    )
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v3_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: existing)
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called")),
    )
    with pytest.raises(ContractError, match="execution is consumed"):
        rapid.run_rapid_public_development_v3(
            approve_live_cost=True,
            approved_execution_hash="sha256:" + "0" * 64,
            repository=REPOSITORY,
        )
