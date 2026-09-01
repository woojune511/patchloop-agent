from __future__ import annotations

import copy
import json
import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.agent import provider_request_gate as gate
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.provider_schema_adapter import StrictOpenAIResponsesAdapter
from patchloop.agent.provider_schema_admission import validate_provider_tool_schemas
from patchloop.agent.runner import AgentRunner, issue_row_execution_authorization
from patchloop.contracts import EventType
from patchloop.evals import rapid_public_development_v27 as rapid
from patchloop.repository import DiffSummary, WorkspaceManager
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox.runner import DockerImageIdentityProjection, LocalSandbox, SandboxResult
from patchloop.util import sha256_json
from patchloop.verifier import EvaluationEngine
from tests.test_provider_schema_runner import (
    _FakeProvider,
    _manifest,
    _mock_boundaries,
    _provider_adapter,
    _requests,
    _V27Adapter,
)
from tests.test_rapid_public_development_v27 import ROOT, live_batch
from tests.test_workflow_plan_contract_compatibility_runner import _manifest as _v25_manifest
from tests.test_workflow_self_directed_exploration_runner import (
    TASK_PATH,
    _SelfDirectedWorkflowAdapter,
)


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("R24 runner tests require mocked external boundaries")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(DockerSandbox, "available", staticmethod(lambda: False))
    for name in ("image_identity", "image_identity_projection", "run_check", "run_probe"):
        monkeypatch.setattr(DockerSandbox, name, blocked)
    monkeypatch.setattr(EvaluationEngine, "evaluate", blocked)
    monkeypatch.setattr(EvaluationEngine, "evaluate_v2_candidate", blocked)


@pytest.fixture(scope="module")
def candidate():
    return rapid.build_rapid_public_development_v27_candidate(repository=ROOT)


class _SDKStop(BaseException):
    pass


def actual_initial_runner(candidate, tmp_path, monkeypatch, order):
    """Actual R24 manifest/row/start/loop; only workspace and Docker are synthetic."""
    live, prepared = live_batch(candidate, tmp_path)
    manifest = prepared.manifests[order - 1]
    binding = candidate["task_bindings"][0]
    image = binding["evaluator_image"]
    inspected = []

    def inspect(_self):
        inspected.append(image)
        assert len(inspected) == 1
        return DockerImageIdentityProjection(
            requested_repo_digest=image,
            requested_digest=binding["evaluator_image_digest"],
            config_id="sha256:" + "a" * 64,
            repo_digests=(image,),
            matched_repo_digest=image,
        )

    monkeypatch.setattr(DockerSandbox, "image_identity_projection", inspect)
    image_authority = rapid._admit_prepared_image(candidate, prepared, tmp_path)
    for earlier in range(1, order):
        issue_row_execution_authorization(
            prepared.authorization, prepared.manifests[earlier - 1], active_schedule_order=earlier
        )
    row = issue_row_execution_authorization(
        prepared.authorization, manifest, active_schedule_order=order
    )
    runner = AgentRunner(tmp_path / ".patchloop")

    def create(run_id, *_args):
        workspace = runner.root / "workspaces" / run_id / "repo"
        workspace.mkdir(parents=True)
        return workspace

    monkeypatch.setattr(runner.workspaces, "create", create)
    monkeypatch.setattr(runner.workspaces, "validate_managed_workspace", lambda path: path)
    monkeypatch.setattr(runner.workspaces, "validate_pristine", lambda *a: None)
    monkeypatch.setattr(WorkspaceManager, "untracked_files", staticmethod(lambda *_a: []))
    monkeypatch.setattr(
        WorkspaceManager, "diff_summary", staticmethod(lambda *_a: DiffSummary([], 0, 0, ""))
    )
    original_run = subprocess.run

    def public_git_only(command, *args, **kwargs):
        if command == ["git", "rev-parse", "HEAD"]:
            if Path(kwargs["cwd"]).resolve() == ROOT:
                return original_run(command, *args, **kwargs)
            return subprocess.CompletedProcess(
                command, 0, stdout=manifest.base_commit + "\n", stderr=""
            )
        raise AssertionError(f"unexpected subprocess in initial request fixture: {command}")

    monkeypatch.setattr(subprocess, "run", public_git_only)
    return runner, manifest, live, row, image_authority


@pytest.mark.parametrize("order", [1, 2])
@pytest.mark.parametrize("boundary", ["count", "create"])
def test_real_production_initial_request_is_admitted_before_any_sdk(
    candidate, tmp_path, monkeypatch, order, boundary
):
    runner, manifest, live, row, image = actual_initial_runner(
        candidate, tmp_path, monkeypatch, order
    )
    observed = []
    admitted = []
    original_admit = gate.admit_request

    def admit(*args, **kwargs):
        receipt = original_admit(*args, **kwargs)
        admitted.append(receipt["request_hash"])
        observed.append("admitted")
        return receipt

    def count(**request):
        assert observed[-1] == "admitted"
        observed.append("count")
        validate_provider_tool_schemas(request)
        if boundary == "count":
            raise _SDKStop()
        return SimpleNamespace(input_tokens=100)

    def create(**request):
        assert observed[-1] == "admitted"
        assert admitted[-1] == sha256_json(request)
        observed.append("create")
        context = json.loads(request["input"][1]["content"])
        assert context["public_task"]["task_id"] == manifest.task_id
        raise _SDKStop()

    client = SimpleNamespace(
        max_retries=0,
        responses=SimpleNamespace(
            input_tokens=SimpleNamespace(count=count),
            create=create,
        ),
    )
    adapter_type = StrictOpenAIResponsesAdapter if order == 2 else OpenAIResponsesAdapter
    adapter = adapter_type(manifest.model, client=client)
    monkeypatch.setattr(gate, "admit_request", admit)
    monkeypatch.setattr(runner, "_model_adapter", lambda *a, **k: adapter)
    with pytest.raises(_SDKStop):
        runner.start(
            rapid.TASK_PATH,
            model="openai",
            manifest=manifest,
            live_authorization=live,
            row_execution_authorization=row,
            batch_image_authorization=image,
        )
    assert observed[-1] == boundary
    assert not any(
        e.type == EventType.TOOL_CALLED for e in runner.state.list_events(manifest.run_id)
    )
    assert sum(item == "admitted" for item in observed) == sum(
        item in {"count", "create"} for item in observed
    )


@pytest.mark.parametrize("order", [1, 2])
def test_real_initial_schema_drift_blocks_before_count(candidate, tmp_path, monkeypatch, order):
    runner, manifest, live, row, image = actual_initial_runner(
        candidate, tmp_path, monkeypatch, order
    )
    adapter_type = StrictOpenAIResponsesAdapter if order == 2 else OpenAIResponsesAdapter

    class BrokenAdapter(adapter_type):
        def request_payload(self, *args, **kwargs):
            request = copy.deepcopy(super().request_payload(*args, **kwargs))
            request["tools"][0]["parameters"]["required"] = []
            return request

    def unexpected(**kwargs):
        pytest.fail("invalid dynamic schema reached an SDK boundary")

    adapter = BrokenAdapter(
        manifest.model,
        client=SimpleNamespace(
            max_retries=0,
            responses=SimpleNamespace(
                input_tokens=SimpleNamespace(count=unexpected), create=unexpected
            ),
        ),
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *a, **k: adapter)
    result = runner.start(
        rapid.TASK_PATH,
        model="openai",
        manifest=manifest,
        live_authorization=live,
        row_execution_authorization=row,
        batch_image_authorization=image,
    )
    assert result["terminal_error"]["code"] == "PROVIDER_TOOL_SCHEMA_INVALID", result
    assert result["usage"]["model_calls"] == result["usage"]["input_token_count_calls"] == 0


@pytest.mark.parametrize("review", [False, True])
@pytest.mark.parametrize("version", [25, 27])
def test_later_dynamic_requests_in_real_shaped_fake_provider_runner(
    tmp_path, monkeypatch, review, version
):
    """Public smoke scenario, not an AnyIO trajectory or live acceptance result."""
    manifest = (_manifest if version == 27 else _v25_manifest)("run_r24_dynamic_schema_fixture")
    runner = AgentRunner(tmp_path / "d")
    _mock_boundaries(runner, monkeypatch)
    checks = []

    def check(_self, _workspace, registered):
        checks.append(registered.id)
        failed = not review and len(checks) == 1
        return SandboxResult(
            command=registered.command,
            exit_code=1 if failed else 0,
            stdout="synthetic failed behavior" if failed else "synthetic pass",
            stderr="",
            duration_ms=0,
            timed_out=False,
            truncated=False,
            original_output_bytes=24,
        )

    monkeypatch.setattr(LocalSandbox, "run_check", check)

    class DynamicProvider(_FakeProvider):
        def count(self, **request):
            self.count_calls += 1
            gate.validate_request_schemas(request)
            return SimpleNamespace(input_tokens=100)

        def create(self, **request):
            gate.validate_request_schemas(request)
            return super().create(**request)

    client = DynamicProvider()
    client.policy = (_V27Adapter if version == 27 else _SelfDirectedWorkflowAdapter)(
        prefix="dynamic-sdk", fail_first_mutation=not review, review_correction=review
    )
    adapter = _provider_adapter(client)
    if version == 25:
        adapter = OpenAIResponsesAdapter(adapter.config, client=client)
    monkeypatch.setattr(runner, "_model_adapter", lambda *a, **k: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result.get("mock_submission_boundary_reached"), result.get("terminal_error")
    if version == 27:
        requests = _requests(runner, manifest.run_id)
    else:
        from patchloop.agent.lean_runtime import validate_persisted_lean_harness_request

        requests = [
            validate_persisted_lean_harness_request(
                json.loads(Path(event.payload["request_artifact_path"]).read_bytes())
            )
            for event in runner.state.list_events(manifest.run_id)
            if event.type == EventType.MODEL_CALLED
        ]
    names = {
        name for request in requests for name in request.phase_tool_surface.selected_tool_names
    }
    assert {"record_work_plan", "revise_work_plan", "run_check", "get_diff", "finish_task"} <= names
    assert client.count_calls >= client.create_calls > 0
    if version == 27:
        assert all(request.provider_tool_schema_admission for request in requests)
    events = runner.state.list_events(manifest.run_id)
    assert len([e for e in events if e.type == EventType.PLAN_RECORDED]) == 2
    assert len([e for e in events if e.type == EventType.PATCH_APPLIED]) == 2
    assert checks[0] == checks[1]
