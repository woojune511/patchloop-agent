"""Production-shaped, zero-external-call row-start qualification for R24.

Workspace creation and the model/evaluation loop are substituted. The real
candidate/manifest/capability, image-admission, AgentRunner.start and six-row
settlement paths are exercised; the substitute explicitly invokes the real
provider-capability gate and then creates a synthetic terminal. No request
generation, agent/task performance or live Docker behavior is measured.
"""

from __future__ import annotations

import json
import socket
import subprocess
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from patchloop.agent import runner as runner_module
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.provider_request_gate import admit_request
from patchloop.agent.provider_schema_adapter import StrictOpenAIResponsesAdapter
from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import EventType, RunOutcomeKind, RunResult, RunStatus, Usage, Verdicts
from patchloop.errors import ContractError
from patchloop.evals import rapid_public_development_v27 as rapid
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox import runner as sandbox_module
from patchloop.state import StateStore
from patchloop.verifier import EvaluationEngine


def run_provider_request_batch_mock(
    candidate: dict[str, Any],
    *,
    repository: Path,
    state_root: Path,
) -> dict[str, Any]:
    """Use an isolated local state root; caller must never use production state."""
    root = repository.resolve()
    state_root = state_root.resolve()
    if state_root == root or state_root == root / ".patchloop" or state_root.exists():
        raise ContractError("image qualification requires a new isolated mock state root")
    counts = {
        "inspect_adapter": 0,
        "real_agent_start_completed": 0,
        "provider_gate": 0,
        "pre_count_gate": 0,
    }
    run_ids = []
    original_popen = subprocess.Popen
    original_connect = StateStore._connect
    mock_connections = []

    def connect_owned(store: StateStore) -> Any:
        if not store.path.resolve().is_relative_to(state_root):
            raise AssertionError("qualification attempted non-isolated state access")
        connection = original_connect(store)
        mock_connections.append(connection)
        return connection

    def close_owned_connections() -> None:
        # sqlite3's transaction context manager does not close the connection.
        # Close only this mock's handles; production StateStore is unchanged.
        for connection in reversed(mock_connections):
            connection.close()

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("batch image qualification crossed an external boundary")

    def local_git_only(args: Any, *rest: Any, **kwargs: Any) -> Any:
        if (
            args == ["git", "rev-parse", "HEAD"]
            and kwargs.get("cwd") == root
            and not kwargs.get("shell", False)
        ):
            return original_popen(args, *rest, **kwargs)
        return blocked(args, *rest, **kwargs)

    def inspect_command(command: list[str], **kwargs: Any) -> tuple[Any, ...]:
        counts["inspect_adapter"] += 1
        if counts["inspect_adapter"] != 1:
            raise AssertionError("batch performs more than one inspect")
        image = candidate["task_bindings"][0]["evaluator_image"]
        if command != [
            "mock-docker",
            "image",
            "inspect",
            image,
            "--format",
            sandbox_module._DOCKER_IMAGE_INSPECT_FORMAT,
        ] or kwargs != {
            "input_bytes": b"",
            "timeout_seconds": 10,
            "output_limit_bytes": sandbox_module._DOCKER_IMAGE_INSPECT_OUTPUT_LIMIT_BYTES,
        }:
            raise AssertionError("inspection command differs from the single approved query")
        output = json.dumps({"Id": "sha256:" + "a" * 64, "RepoDigests": [image]}).encode()
        return 0, False, output, b"", len(output)

    with ExitStack() as stack:
        stack.callback(close_owned_connections)
        stack.enter_context(patch.object(StateStore, "_connect", connect_owned))
        for target, name in (
            (DockerSandbox, "available"),
            (DockerSandbox, "image_identity"),
            (DockerSandbox, "probe_image_identity"),
            (DockerSandbox, "run_check"),
            (OpenAIResponsesAdapter, "next_turn"),
            (OpenAIResponsesAdapter, "execute_request"),
            (EvaluationEngine, "evaluate"),
            (EvaluationEngine, "evaluate_v2_candidate"),
            (socket, "create_connection"),
            (socket.socket, "connect"),
        ):
            stack.enter_context(patch.object(target, name, blocked))
        stack.enter_context(patch.object(subprocess, "Popen", local_git_only))
        original_which = sandbox_module.shutil.which
        stack.enter_context(
            patch.object(
                sandbox_module.shutil,
                "which",
                lambda command: "mock-docker" if command == "docker" else original_which(command),
            )
        )
        stack.enter_context(
            patch.object(sandbox_module, "_run_with_bounded_pipes", inspect_command)
        )
        rapid._write_or_validate_plan(candidate, state_root)
        live = issue_live_execution_authorization(
            candidate["execution_hash"], root=state_root / ".patchloop"
        )
        prepared = rapid._prepare_batch(
            candidate, authority_kind="live", live_authorization=live, repository=root
        )
        image_authorization = rapid._admit_prepared_image(candidate, prepared, state_root)
        runner = AgentRunner(state_root / ".patchloop")

        def create(run_id: str, *_args: Any) -> Path:
            path = runner.root / "workspaces" / run_id / "repo"
            path.mkdir(parents=True, exist_ok=False)
            return path

        def synthetic_terminal(
            package: Any, workspace: Path, manifest: Any, model: str, **kwargs: Any
        ) -> dict[str, Any]:
            del package, workspace
            if model != "openai":
                raise AssertionError("mock row did not take the real live admission path")
            counts["real_agent_start_completed"] += 1
            run_ids.append(manifest.run_id)
            # Synthetic static first-turn surface; actual public-task assembly is
            # exercised separately by the initial no-call rehearsal.
            adapter_type = (
                StrictOpenAIResponsesAdapter
                if manifest.context_policy_version == "phase-evidence-v37"
                else OpenAIResponsesAdapter
            )
            adapter = adapter_type(manifest.model, client=SimpleNamespace(max_retries=0))
            _, schemas = AgentRunner._runtime_contract(manifest)
            request = {
                "model": manifest.model.model_id,
                "tools": [
                    schema for schema in schemas if schema["name"] in {"search_files", "read_file"}
                ],
            }
            admit_request(
                manifest,
                kwargs["row_execution_authorization"],
                request,
                adapter,
                stop_before_count=False,
            )
            counts["pre_count_gate"] += 1
            runner_module._provider_dispatch_boundary(
                manifest, kwargs["row_execution_authorization"], stop_before_dispatch=False
            )
            counts["provider_gate"] += 1
            result = RunResult(
                run_id=manifest.run_id,
                agent_submission_status="completed",
                evaluation_status="completed",
                scope_compliant_success=True,
                official=False,
                verdicts=Verdicts(),
                usage=Usage(),
                outcome_kind=RunOutcomeKind.RESOLVED,
            )
            runner.state.set_run_status(manifest.run_id, RunStatus.RUNNING)
            runner.state.finalize_run(
                manifest.run_id,
                status=RunStatus.COMPLETED,
                result=result,
                event_type=EventType.RUN_COMPLETED,
                actor="runner",
                payload={
                    "scope_compliant_success": True,
                    "official": False,
                    "duration_ms": 0,
                    "failure_classification_error": None,
                },
            )
            return result.model_dump(mode="json")

        stack.enter_context(patch.object(runner.workspaces, "create", create))
        stack.enter_context(
            patch.object(runner.workspaces, "validate_managed_workspace", lambda p: p)
        )
        stack.enter_context(patch.object(runner.workspaces, "validate_pristine", lambda *a: None))
        stack.enter_context(
            patch.object(runner, "_prepare_public_review_base_provenance", lambda **k: None)
        )
        stack.enter_context(patch.object(runner, "_execute", synthetic_terminal))
        rapid._run_prepared_driver(
            candidate=candidate,
            prepared=prepared,
            live_authorization=live,
            image_authorization=image_authorization,
            runner=runner,
            repository=state_root,
        )
        events = [
            json.loads(line)
            for line in rapid._result_bundle_path(candidate, state_root).read_bytes().splitlines()
        ]
        end = events[-1]
        if not (
            counts
            == {
                "inspect_adapter": 1,
                "real_agent_start_completed": 6,
                "provider_gate": 6,
                "pre_count_gate": 6,
            }
            and end["event"] == "batch-completed"
            and end["terminal_row_count"] == 6
            and end["not_started_row_count"] == 0
            and end["accrued_cost_nanos"] == 0
            and len(set(run_ids)) == 6
        ):
            raise ContractError("batch image production-shaped mock did not complete all six rows")
    return {
        "schema_version": "provider-request-batch-start-mock-v1",
        "fixture_kind": "synthetic-isolated-row-terminals-no-agent-performance-measurement",
        "inspect_adapter_calls": counts["inspect_adapter"],
        "mocked_docker_image_inspect_commands": counts["inspect_adapter"],
        "actual_docker_calls": 0,
        "daemon_version_calls": 0,
        "per_row_image_inspect_calls": 0,
        "real_agent_start_count": counts["real_agent_start_completed"],
        "provider_gate_count": counts["provider_gate"],
        "pre_count_gate_count": counts["pre_count_gate"],
        "request_kind": "synthetic-static-first-turn-schema-model-only",
        "provider_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "network_calls": 0,
        "added_cost_nanos": 0,
        "synthetic_terminal_rows": 6,
        "distinct_run_ids": 6,
        "agent_policies_or_task_behavior_exercised": False,
        "isolated_mock_sqlite_connections_closed": True,
    }
