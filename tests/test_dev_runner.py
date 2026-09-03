from __future__ import annotations

import json
import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import patchloop.dev.runner as runner
from patchloop.agent.model import ModelTurn, OpenAIResponsesAdapter
from patchloop.agent.model import RequestedTool as ProviderRequestedTool
from patchloop.contracts import ModelConfig
from patchloop.dev.contracts import (
    DevLimits,
    DevModelTurn,
    DevRunRequest,
    DevToolResult,
    RequestedTool,
)
from patchloop.dev.model import MOCK_MUTATIONS, MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError, ResumeContractMismatch
from patchloop.repository import WorkspaceManager as RealWorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json


def test_latest_tool_result_is_not_evicted_by_working_set(gateway_factory, smoke_package) -> None:
    gateway, journal, _ = gateway_factory()
    for index in range(12):
        gateway.spans[f"span_ffffffffffff{index:04d}"] = {
            "span_id": f"span_ffffffffffff{index:04d}",
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 1,
            "content": f"old-{index}",
            "file_hash": "sha256:" + "0" * 64,
            "last_observed_seq": index + 1,
        }
    latest = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="latest-read",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 13,
            },
        )
    )
    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=smoke_package,
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[latest],
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )
    projected = context["latest_tool_results"][0]["output"]["spans"]
    assert projected[0]["span_id"] == latest.output["spans"][0]["span_id"]
    assert len(context["source_spans"]) == 8


def test_openai_request_requires_a_tool_and_records_only_output_shape() -> None:
    observed: dict[str, dict] = {}

    class FakeInputTokens:
        def count(self, **payload):
            observed["count"] = payload
            return SimpleNamespace(input_tokens=17)

    class FakeResponses:
        input_tokens = FakeInputTokens()

        def create(self, **payload):
            observed["create"] = payload
            return SimpleNamespace(
                id="response-shape-only",
                model="gpt-5.4-mini-2026-03-17",
                status="completed",
                incomplete_details=None,
                output=[
                    SimpleNamespace(type="reasoning", content="private-reasoning-sentinel"),
                    SimpleNamespace(type="message", content="public-message-sentinel"),
                ],
                usage=SimpleNamespace(
                    input_tokens=17,
                    input_tokens_details=SimpleNamespace(cached_tokens=3),
                    output_tokens=5,
                    output_tokens_details=SimpleNamespace(reasoning_tokens=2),
                ),
            )

    fake_client = SimpleNamespace(max_retries=0, responses=FakeResponses())
    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            transport_max_retries=0,
        ),
        api_key="unused-test-key",
        client=fake_client,
    )
    request = adapter.request_payload(
        "{}",
        dev_tool_schemas(finish_enabled=False, check_ids=["public-check"]),
        system_prompt="test prompt",
    )

    assert request["tool_choice"] == "required"
    assert adapter.count_input_tokens_v2(request) == 17
    assert observed["count"]["tool_choice"] == "required"

    turn = adapter.execute_request(request, requested_input_tokens=17)

    assert observed["create"]["tool_choice"] == "required"
    assert turn.error is None
    assert turn.tool_calls == []
    assert turn.output_item_count == 2
    assert turn.non_tool_output_item_count == 2
    assert turn.output_item_types == ("reasoning", "message")
    assert turn.output_shape_hash == sha256_json(
        {"item_count": 2, "item_types": ("reasoning", "message")}
    )
    assert "private-reasoning-sentinel" not in repr(turn)
    assert "public-message-sentinel" not in repr(turn)


def test_failed_mutation_stays_projected_after_read_cards_without_protocol_label(
    gateway_factory,
    smoke_package,
) -> None:
    gateway, journal, _ = gateway_factory()
    source = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="failed-mutation-source",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 20,
            },
        )
    )
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    malformed_patch = mutation.patch.replace(" import csv\n", " import csv_missing\n")
    failed = gateway.execute(
        RequestedTool(
            name="apply_git_diff",
            action_id="failed-mutation",
            arguments={
                "git_diff": malformed_patch,
                "hypothesis": mutation.hypothesis,
                "expected_behavior": mutation.expected_behavior,
                "evidence_span_ids": [source.output["spans"][0]["span_id"]],
                "edit_anchor": {
                    "path": mutation.path,
                    "old_text": mutation.anchor,
                    "occurrence": 1,
                },
                "falsified_prior_hypothesis": None,
                "alternative_mechanism": None,
            },
        )
    )
    _, correction = runner._record_tool_batch(  # noqa: SLF001 - context contract test
        journal=journal,
        gateway=gateway,
        turn_id="failed-mutation-turn",
        results=[failed],
        active_elapsed_ms=1,
    )
    assert correction is None

    reads = gateway.execute_batch(
        [
            RequestedTool(
                name="read_file",
                action_id=f"read-after-failure-{index}",
                arguments={
                    "path": "mini_data_utils/csvlite.py",
                    "start_line": index,
                    "end_line": index + 5,
                },
            )
            for index in range(1, 5)
        ]
    )
    runner._record_tool_batch(  # noqa: SLF001 - displace the bounded attempt cards
        journal=journal,
        gateway=gateway,
        turn_id="read-after-failure-turn",
        results=reads,
        active_elapsed_ms=2,
    )
    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=smoke_package,
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=reads,
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root()
                / "tasks"
                / "smoke"
                / "csv-quoted-newline"
                / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )

    assert context["last_failed_mutation"]["git_diff"] == malformed_patch
    assert "patch failed: mini_data_utils/csvlite.py:1" in context[
        "last_failed_mutation"
    ]["error_message"]
    assert all(
        card["attempt"] not in {"apply_git_diff", "protocol"}
        for card in context["recent_attempt_result_next_question"]
    )


def test_context_projects_every_current_diff_check_and_names_the_remaining_one(
    gateway_factory,
    smoke_package,
) -> None:
    gateway, journal, _ = gateway_factory()
    source = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="four-check-source",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 20,
            },
        )
    )
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    applied = gateway.execute(
        RequestedTool(
            name="apply_git_diff",
            action_id="four-check-mutation",
            arguments={
                "git_diff": mutation.patch,
                "hypothesis": mutation.hypothesis,
                "expected_behavior": mutation.expected_behavior,
                "evidence_span_ids": [source.output["spans"][0]["span_id"]],
                "edit_anchor": {
                    "path": mutation.path,
                    "old_text": mutation.anchor,
                    "occurrence": 1,
                },
                "falsified_prior_hypothesis": None,
                "alternative_mechanism": None,
            },
        )
    )
    assert applied.status == "succeeded"

    original_check = smoke_package.public.visible_checks[0]
    check_ids = ["contract", "basic-regression", "field-regression", "upstream-regression"]
    public = smoke_package.public.model_copy(
        update={
            "visible_checks": [
                original_check.model_copy(update={"id": check_id}) for check_id in check_ids
            ]
        }
    )
    gateway.public_task = public
    diff_hash = gateway.current_diff_hash
    for check_id in check_ids[:3]:
        gateway._remember_check(  # noqa: SLF001 - reconstruct current public evidence
            {
                "check_id": check_id,
                "diff_hash": diff_hash,
                "passed": True,
                "failure_signature": None,
            }
        )
    last_pass = DevToolResult(
        action_id="third-visible-pass",
        input_hash=sha256_json("third-visible-pass"),
        tool="run_check",
        status="succeeded",
        output={
            "check_id": check_ids[2],
            "diff_hash": diff_hash,
            "passed": True,
            "failure_signature": None,
        },
    )

    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=SimpleNamespace(public=public),
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[last_pass],
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root()
                / "tasks"
                / "smoke"
                / "csv-quoted-newline"
                / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )
    card = runner._attempt_card(last_pass, gateway)  # noqa: SLF001

    assert [row["check_id"] for row in context["visible_check_status"]] == check_ids
    assert [row["status"] for row in context["visible_check_status"]] == [
        "PASS",
        "PASS",
        "PASS",
        "NOT_RUN",
    ]
    assert context["remaining_visible_check_ids"] == ["upstream-regression"]
    assert context["workflow_gate"] == "needs_visible_checks"
    assert card["next_question"] == (
        "Run one remaining visible check for the current diff: upstream-regression"
    )
    assert "failure" not in card["next_question"].lower()
    encoded = json.dumps(context)
    assert "hidden-multiline-csv" not in encoded
    assert "reference_patch" not in encoded


def test_mock_end_to_end_isolated_evaluator_and_public_context(tmp_path, monkeypatch) -> None:
    contexts: list[str] = []

    class CapturingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            contexts.append(context)
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", CapturingMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["evaluator"] == {
        "task_acceptance": "PASS",
        "safety_state": "NOT_RUN",
        "failure_class": None,
        "claim_eligible": False,
    }
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["accepted_mutations"] == 1
    assert all("hidden-multiline-csv" not in context for context in contexts)
    assert all("reference_patch" not in context for context in contexts)
    context_keys = {
        "public_task",
        "current_diff",
        "latest_tool_results",
        "source_spans",
        "recent_checks",
        "visible_check_status",
        "remaining_visible_check_ids",
        "last_successful_mutation",
        "last_failed_mutation",
        "recent_attempt_result_next_question",
        "workflow_gate",
        "remaining_budget",
    }
    assert all(set(json.loads(context)) == context_keys for context in contexts)
    projected = [
        json.loads(context)["current_diff"]
        for context in contexts
        if json.loads(context)["current_diff"]["patch"]
    ]
    assert projected
    assert all(item["truncated"] is False for item in projected)

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert all(row["schema_version"] == "dev-run-v1" for row in rows)
    assert all(row["official"] is False for row in rows)
    assert all(row["event_type"] != "state_changed" for row in rows)
    assert [json.loads(context)["workflow_gate"] for context in contexts] == [
        "needs_mutation",
        "needs_mutation",
        "needs_visible_checks",
        "ready_to_submit",
    ]
    assert len([row for row in rows if row["event_type"] == "turn_decision_recorded"]) == 4
    assert len([row for row in rows if row["event_type"] == "tool_batch_finished"]) == 4
    terminal = next(row for row in rows if row["event_type"] == "terminal")
    assert terminal["payload"]["milestones"]["submission"]["patch_hash"].startswith("sha256:")
    turns = [row for row in rows if row["event_type"] == "turn_started"]
    assert len(turns) == 4
    assert all(row["payload"]["context_hash"].startswith("sha256:") for row in turns)
    assert any(
        result["output"].get("spans")
        for context in contexts[1:]
        for result in json.loads(context)["latest_tool_results"]
    )
    evaluator = next(row for row in rows if row["event_type"] == "evaluator_finished")
    assert evaluator["payload"]["agent_context_reinjected"] is False
    event_types = [row["event_type"] for row in rows]
    assert event_types.index("submission_recorded") < event_types.index("manifest_recorded")
    assert event_types.index("manifest_recorded") < event_types.index("evaluator_finished")
    envelope_path = tmp_path / "runs" / f"{run['run_id']}.envelope.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    assert envelope["schema_version"] == "dev-run-envelope-v1"
    manifest = json.loads(
        (tmp_path / "artifacts" / "runs" / run["run_id"] / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["task_content_hash"] == envelope["task_content_hash"]
    assert manifest["runtime_content_hash"] == envelope["runtime_hash"]
    assert manifest["submitted_patch_content_hash"] == run["artifact_hashes"][
        "submitted_patch"
    ]
    assert manifest["visible_check_diff_hash"] == manifest["submitted_patch_content_hash"]
    assert manifest["submitted_changed_files"] == ["mini_data_utils/csvlite.py"]
    workspace_roots = [path for path in (tmp_path / "workspaces").iterdir() if path.is_dir()]
    assert len(workspace_roots) == 2


def test_unexpected_tool_gateway_failure_writes_terminal(tmp_path, monkeypatch) -> None:
    class ExplodingGateway(runner.DevToolGateway):
        def execute_batch(self, calls):
            del calls
            raise RuntimeError("simulated gateway crash")

    monkeypatch.setattr(runner, "DevToolGateway", ExplodingGateway)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "TASK_FAILED"

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    terminal = [row for row in rows if row["event_type"] == "terminal"]
    assert len(terminal) == 1
    assert terminal[0]["payload"]["message"] == "tool gateway failed: RuntimeError"


def test_manifest_submission_and_terminal_provenance_survive_evaluator_error(
    tmp_path,
    monkeypatch,
) -> None:
    observed = {"called": False}

    def fail_after_manifest(
        self,
        task_dir,
        patch_path,
        manifest,
        usage=None,
        submitted_patch_artifact=None,
    ):
        del task_dir, usage
        observed["called"] = True
        manifest_path = self.artifact_store.root / "runs" / manifest.run_id / "manifest.json"
        assert manifest_path.is_file()
        assert submitted_patch_artifact is not None
        assert Path(patch_path).read_bytes() == self.artifact_store.read_bytes(
            submitted_patch_artifact
        )
        raise RuntimeError("simulated evaluator failure")

    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", fail_after_manifest)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert observed["called"] is True
    assert run["terminal"] == "EVALUATOR_ERROR"
    assert run["evaluator"] == {
        "task_acceptance": "ERROR",
        "safety_state": "ERROR",
        "failure_class": "EVALUATOR_INFRA_FAILURE",
        "claim_eligible": False,
    }
    run_artifacts = tmp_path / "artifacts" / "runs" / run["run_id"]
    assert (run_artifacts / "manifest.json").is_file()
    assert (run_artifacts / "terminal-provenance.json").is_file()
    manifest_text = (run_artifacts / "manifest.json").read_text(encoding="utf-8")
    assert "hidden-multiline-csv" not in manifest_text
    assert "reference.patch" not in manifest_text
    assert {"submitted_patch", "manifest", "terminal_provenance"}.issubset(
        run["artifact_hashes"]
    )


def test_invalid_tool_batch_gets_one_correction_then_stops(tmp_path, monkeypatch) -> None:
    class InvalidBatchMock:
        calls = 0

        def __init__(self, task_id) -> None:
            del task_id

        def next_turn(self, context, tools):
            del context, tools
            self.calls += 1
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="read_file",
                        action_id=f"bad-read-{self.calls}",
                        arguments={"path": "mini_data_utils/csvlite.py"},
                    ),
                    RequestedTool(
                        name="run_check",
                        action_id=f"bad-check-{self.calls}",
                        arguments={"check_id": "existing-unit-tests"},
                    ),
                ]
            )

    monkeypatch.setattr(runner, "MockDevAdapter", InvalidBatchMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "PROTOCOL_VIOLATION"
    assert run["call_counts"] == {"model": 2, "input_count": 0, "tool": 0}

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert len([row for row in rows if row["event_type"] == "protocol_correction"]) == 1


def test_protocol_correction_limit_is_consecutive_and_stop_is_structured(
    tmp_path,
    monkeypatch,
) -> None:
    class AlternatingBatchMock:
        def __init__(self, task_id) -> None:
            del task_id
            self.calls = 0

        def next_turn(self, context, tools):
            del context, tools
            self.calls += 1
            if self.calls in {1, 3}:
                return DevModelTurn(
                    tool_calls=[
                        RequestedTool(
                            name="read_file",
                            action_id=f"mixed-read-{self.calls}",
                            arguments={
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 20,
                            },
                        ),
                        RequestedTool(
                            name="run_check",
                            action_id=f"mixed-check-{self.calls}",
                            arguments={"check_id": "existing-unit-tests"},
                        ),
                    ]
                )
            if self.calls == 2:
                return DevModelTurn(
                    tool_calls=[
                        RequestedTool(
                            name="read_file",
                            action_id="valid-read-between-corrections",
                            arguments={
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 20,
                            },
                        )
                    ]
                )
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="stop_task",
                        action_id="structured-stop",
                        arguments={
                            "reason_code": "insufficient_public_evidence",
                            "summary": "No additional public evidence supports a safe edit.",
                            "evidence_span_ids": [],
                        },
                    )
                ]
            )

    monkeypatch.setattr(runner, "MockDevAdapter", AlternatingBatchMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )

    run = runner.run_dev(request)["runs"][0]

    assert run["terminal"] == "AGENT_STOPPED"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 2}
    assert run["accepted_mutations"] == 0
    assert run["agent_stop"] == {
        "reason_code": "insufficient_public_evidence",
        "summary": "No additional public evidence supports a safe edit.",
        "evidence_span_ids": [],
        "diff_hash": sha256_bytes(b""),
    }
    journal = DevJournal(tmp_path, run["run_id"])
    rows = journal.events()
    assert len([row for row in rows if row["event_type"] == "protocol_correction"]) == 2
    assert len([row for row in rows if row["event_type"] == "tool_batch_finished"]) == 2
    assert not any(row["event_type"] == "submission_recorded" for row in rows)
    assert not any(row["event_type"] == "evaluator_finished" for row in rows)


def test_resume_counter_restores_only_corrections_since_last_valid_batch(tmp_path) -> None:
    journal = DevJournal(tmp_path, "run_dev_consecutive01")
    journal.append("protocol_correction", {"turn_id": "turn-invalid-before"})
    journal.append("tool_batch_finished", {"turn_id": "turn-valid"})
    journal.append("protocol_correction", {"turn_id": "turn-invalid-after"})

    counters = runner._restore_counters(journal)  # noqa: SLF001 - resume contract test

    assert counters.protocol_recoveries == 1


def test_live_rejects_non_dev_train_before_credential_or_provider(tmp_path) -> None:
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=not-used\n", encoding="utf-8")
    request = DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-validation"
            / "babel-strict-grouped-decimal-trailing-zeroes-v2"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal("0.01"),
        state_root=tmp_path / "state",
    )
    with pytest.raises(ContractError, match="dev-train"):
        runner.run_dev(request)


def test_live_source_preflight_scopes_cleanliness_to_relevant_tracked_paths(tmp_path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "patchloop@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PatchLoop Test"],
        cwd=repository,
        check=True,
    )
    runtime_file = repository / "patchloop" / "runtime.py"
    runtime_file.parent.mkdir()
    runtime_file.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repository, check=True)

    scratch = repository / "scratch" / "untracked.txt"
    scratch.parent.mkdir()
    scratch.write_text("ignored by the selected pathspec\n", encoding="utf-8")
    runner._require_tracked_clean_paths(repository, ["patchloop/runtime.py"])

    runtime_file.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ContractError, match="match HEAD"):
        runner._require_tracked_clean_paths(repository, ["patchloop/runtime.py"])

    with pytest.raises(ContractError, match="must all be tracked"):
        runner._require_tracked_clean_paths(repository, ["missing.py"])


def test_live_missing_local_image_stops_before_provider(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=test-only-sentinel\n", encoding="utf-8")
    monkeypatch.setattr(runner.DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(runner.DockerSandbox, "image_identity", lambda self: None)
    monkeypatch.setattr(runner, "_live_source_preflight", lambda task_dir, package: None)
    request = DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-train"
            / "anyio-interrupt-runner-cleanup"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal("0.01"),
        state_root=tmp_path / "state",
    )
    result = runner.run_dev(request)
    assert result["runs"][0]["terminal"] == "PREFLIGHT_FAILED"
    assert result["runs"][0]["call_counts"]["model"] == 0


class _SnapshotWorkspaceManager:
    smoke = load_task_package(repository_root() / "tasks" / "smoke" / "csv-quoted-newline")
    diff_summary = staticmethod(RealWorkspaceManager.diff_summary)

    def __init__(self, fixture_root, workspace_root) -> None:
        self.delegate = RealWorkspaceManager(fixture_root, workspace_root)

    def create(self, run_id, repository_url, expected_revision=None):
        del repository_url, expected_revision
        return self.delegate.create(
            run_id,
            self.smoke.public.repository.url,
            self.smoke.public.repository.base_commit,
        )

    def validate_managed_workspace(self, workspace):
        return self.delegate.validate_managed_workspace(workspace)


def _live_request(tmp_path: Path, *, repeat: int = 3, cap: str = "0.01") -> DevRunRequest:
    tmp_path.mkdir(parents=True, exist_ok=True)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=test-only-sentinel\n", encoding="utf-8")
    return DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-train"
            / "anyio-interrupt-runner-cleanup"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal(cap),
        repeat=repeat,
        state_root=tmp_path / "state",
    )


def _patch_live_boundaries(monkeypatch) -> None:
    monkeypatch.setattr(runner, "_live_source_preflight", lambda task_dir, package: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda package: LocalSandbox())
    monkeypatch.setattr(runner, "WorkspaceManager", _SnapshotWorkspaceManager)


class _SimulatedCrash(BaseException):
    pass


def _enveloped_run_id(state_root: Path) -> str:
    envelopes = list((state_root / "runs").glob("run_dev_*.envelope.json"))
    assert len(envelopes) == 1
    return envelopes[0].name.removesuffix(".envelope.json")


def _crash_journal_once(
    monkeypatch,
    *,
    event_type: str,
    when: str,
    predicate=lambda payload: True,
) -> None:
    original = DevJournal.append
    fired = False

    def append(self, current_type, payload=None):
        nonlocal fired
        matches = not fired and current_type == event_type and predicate(payload or {})
        if matches and when == "before":
            fired = True
            raise _SimulatedCrash(current_type)
        result = original(self, current_type, payload)
        if matches and when == "after":
            fired = True
            raise _SimulatedCrash(current_type)
        return result

    monkeypatch.setattr(DevJournal, "append", append)


@pytest.mark.parametrize(
    "crash_case",
    [
        "decision_recorded",
        "mutation_before_result",
        "check_result_recorded",
        "batch_before_finished",
    ],
)
def test_mock_resume_replays_durable_work_without_duplicate_mutation(
    tmp_path,
    monkeypatch,
    crash_case,
) -> None:
    if crash_case == "decision_recorded":
        _crash_journal_once(
            monkeypatch,
            event_type="turn_decision_recorded",
            when="after",
        )
    elif crash_case == "mutation_before_result":
        _crash_journal_once(
            monkeypatch,
            event_type="action_finished",
            when="before",
            predicate=lambda payload: payload.get("result", {}).get("tool")
            == "apply_git_diff",
        )
    elif crash_case == "check_result_recorded":
        _crash_journal_once(
            monkeypatch,
            event_type="action_finished",
            when="after",
            predicate=lambda payload: payload.get("result", {}).get("tool") == "run_check",
        )
    else:
        _crash_journal_once(
            monkeypatch,
            event_type="tool_batch_finished",
            when="before",
            predicate=lambda payload: any(
                action_id.startswith("mock-visible-check-")
                for action_id in payload.get("action_ids", [])
            ),
        )

    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)

    run_id = _enveloped_run_id(tmp_path)
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    run = resumed["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["accepted_mutations"] == 1

    journal = DevJournal(tmp_path, run_id)
    action_results = [
        row["payload"]["result"]
        for row in journal.events()
        if row["event_type"] == "action_finished"
    ]
    mutation_results = [row for row in action_results if row["tool"] == "apply_git_diff"]
    assert len(mutation_results) == 1
    assert len([row for row in journal.events() if row["event_type"] == "run_resumed"]) == 1


def test_resume_contract_and_workspace_mismatch_do_not_change_journal(
    tmp_path,
    monkeypatch,
) -> None:
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(tmp_path)
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()

    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(
            request.model_copy(
                update={"resume_run_id": run_id, "model": "different-mock-model"}
            )
        )
    assert journal.path.read_bytes() == before

    workspace = tmp_path / "workspaces" / run_id / "repo"
    target = workspace / "mini_data_utils" / "csvlite.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# external drift\n", encoding="utf-8")
    with pytest.raises(ResumeContractMismatch, match="workspace diff"):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before


def test_runtime_mismatch_and_pre_envelope_run_fail_before_journal_change(
    tmp_path,
    monkeypatch,
) -> None:
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(tmp_path)
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()
    monkeypatch.setattr(runner, "_runtime_hash", lambda: "sha256:" + "f" * 64)
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before

    old = DevJournal(tmp_path, "run_dev_oldformat0001")
    old.append("run_started", {"runtime": "dev-head"})
    old_before = old.path.read_bytes()
    with pytest.raises(RecoveryError, match="predates resumable envelopes"):
        runner.run_dev(
            request.model_copy(update={"resume_run_id": "run_dev_oldformat0001"})
        )
    assert old.path.read_bytes() == old_before


def test_resume_rejects_raw_task_content_drift_without_journal_change(
    tmp_path,
    monkeypatch,
) -> None:
    task_dir = tmp_path / "copied-task"
    shutil.copytree(
        repository_root() / "tasks" / "smoke" / "csv-quoted-newline",
        task_dir,
    )
    state_root = tmp_path / "state"
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=task_dir / "public.yaml",
        model="mock-dev",
        state_root=state_root,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(state_root)
    journal = DevJournal(state_root, run_id)
    before = journal.path.read_bytes()
    public = task_dir / "public.yaml"
    public.write_text(
        public.read_text(encoding="utf-8") + "\n# raw task drift\n",
        encoding="utf-8",
    )

    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before


def test_terminal_resume_is_read_only_and_does_not_reenter_model(tmp_path, monkeypatch) -> None:
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    first = runner.run_dev(request)
    run_id = first["runs"][0]["run_id"]
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()

    class ForbiddenAdapter:
        def __init__(self, task_id):
            del task_id
            raise AssertionError("terminal resume must not initialize the model")

    monkeypatch.setattr(runner, "MockDevAdapter", ForbiddenAdapter)
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert resumed["runs"][0] == first["runs"][0]
    assert journal.path.read_bytes() == before


def test_provider_response_resume_does_not_repeat_provider_call(tmp_path, monkeypatch) -> None:
    calls = {"execute": 0}

    class OneReadAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config, api_key

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request
            assert timeout_seconds > 0
            calls["execute"] += 1
            return ModelTurn(
                tool_calls=[
                    ProviderRequestedTool(
                        name="read_file",
                        action_id="provider-read-once",
                        arguments={
                            "path": "mini_data_utils/csvlite.py",
                            "start_line": 1,
                            "end_line": 20,
                        },
                    )
                ],
                requested_input_tokens=requested_input_tokens,
                input_tokens=requested_input_tokens,
                output_tokens=1,
                response_id="response-once",
                response_model="mocked-provider",
                response_status="completed",
                output_item_count=2,
                non_tool_output_item_count=1,
                output_item_types=("reasoning", "function_call"),
                output_shape_hash=sha256_json(
                    {
                        "item_count": 2,
                        "item_types": ("reasoning", "function_call"),
                    }
                ),
            )

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", OneReadAdapter)
    _crash_journal_once(
        monkeypatch,
        event_type="provider_call_finished",
        when="after",
    )
    request = _live_request(tmp_path, repeat=1, cap="0.10").model_copy(
        update={"limits": DevLimits(max_model_calls=1)}
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)

    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    run = resumed["runs"][0]
    assert run["terminal"] == "LIMIT_REACHED"
    assert run["call_counts"] == {"model": 1, "input_count": 1, "tool": 1}
    assert run["cost_nanos"] > 0
    assert calls["execute"] == 1
    journal = DevJournal(request.state_root, run_id)
    for event_type in {"provider_call_finished", "turn_decision_recorded"}:
        payload = next(
            row["payload"] for row in journal.events() if row["event_type"] == event_type
        )
        assert payload["output_item_count"] == 2
        assert payload["non_tool_output_item_count"] == 1
        assert payload["output_item_types"] == ["reasoning", "function_call"]
        assert payload["output_shape_hash"].startswith("sha256:")


def test_unfinished_provider_dispatch_becomes_one_unknown_terminal(tmp_path, monkeypatch) -> None:
    calls = {"adapter": 0, "preflight": 0, "execute": 0}

    class NeverExecutedAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config, api_key
            calls["adapter"] += 1

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            calls["execute"] += 1
            raise AssertionError("crash occurs before dispatch")

    def preflight(package):
        del package
        calls["preflight"] += 1
        return LocalSandbox()

    monkeypatch.setattr(runner, "_live_source_preflight", lambda task_dir, package: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", preflight)
    monkeypatch.setattr(runner, "WorkspaceManager", _SnapshotWorkspaceManager)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", NeverExecutedAdapter)
    _crash_journal_once(
        monkeypatch,
        event_type="provider_call_started",
        when="after",
    )
    request = _live_request(tmp_path, repeat=1, cap="0.10").model_copy(
        update={"limits": DevLimits(max_model_calls=1)}
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)

    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert resumed["runs"][0]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert resumed["runs"][0]["call_counts"] == {
        "model": 1,
        "input_count": 1,
        "tool": 0,
    }
    assert calls == {"adapter": 1, "preflight": 1, "execute": 0}
    journal = DevJournal(request.state_root, run_id)
    assert len([row for row in journal.events() if row["event_type"] == "terminal"]) == 1


def test_provider_timeout_stops_remaining_repetitions(tmp_path, monkeypatch) -> None:
    calls = {"create": 0}
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class TimeoutAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config
            assert api_key == "test-only-sentinel"
            assert "OPENAI_API_KEY" not in os.environ

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens
            assert timeout_seconds > 0
            calls["create"] += 1
            raise TimeoutError("ambiguous provider timeout")

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", TimeoutAdapter)
    result = runner.run_dev(_live_request(tmp_path))
    assert result["completed_repetitions"] == 1
    assert result["runs"][0]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert calls["create"] == 1


def test_count_timeout_and_cost_cap_stop_without_generation(tmp_path, monkeypatch) -> None:
    class CountTimeoutAdapter:
        execute_calls = 0

        def __init__(self, config, *, api_key) -> None:
            del config, api_key

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            raise TimeoutError("count timeout")

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            self.execute_calls += 1

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", CountTimeoutAdapter)
    timed_out = runner.run_dev(_live_request(tmp_path / "count"))
    assert timed_out["completed_repetitions"] == 1
    assert timed_out["runs"][0]["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"

    class TooExpensiveAdapter(CountTimeoutAdapter):
        create_calls = 0

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 1_000_000

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            self.create_calls += 1
            raise AssertionError("generation must not be dispatched")

    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", TooExpensiveAdapter)
    capped = runner.run_dev(_live_request(tmp_path / "cap", cap="0.0001"))
    assert capped["runs"][0]["terminal"] == "COST_CAP_REACHED"
