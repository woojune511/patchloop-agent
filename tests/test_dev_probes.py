from __future__ import annotations

import json

import pytest
from test_dev_tools import mutation_call, read_calls

import patchloop.dev.runner as runner
from patchloop.dev.contracts import (
    DevLimits,
    DevModelTurn,
    DevRunRequest,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import ActionConflict, ContractError, ResumeContractMismatch
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import (
    PROBE_IMAGE_DIGEST,
    probe_execution_policy,
    probe_profile_hash,
)
from patchloop.util import sha256_bytes, sha256_json


class FakeProbe:
    def __init__(self, *, status="failed", effect=None):
        self.calls = 0
        self.status = status
        self.effect = effect

    def preflight(self, **kwargs):
        return {"image_digest": PROBE_IMAGE_DIGEST, "profile_hash": probe_profile_hash()}

    def run_probe(self, workspace, question, python_source, *, deadline, execution_identity):
        self.calls += 1
        assert execution_identity["run_id"].startswith("run_dev_")
        if self.effect:
            self.effect(workspace)
        policy = probe_execution_policy(
            effective_timeout_seconds=30.0, row_deadline_limited=False,
            cleanup_status="confirmed",
        )
        return {
            "status": self.status, "source_hash": sha256_bytes(python_source.encode()),
            "snapshot_hash": sha256_json({"public_snapshot": "test-only"}),
            "image_digest": PROBE_IMAGE_DIGEST, "profile_hash": probe_profile_hash(),
            "exit_code": 0 if self.status == "passed" else 1,
            "stdout": "PUBLIC_PROBE_OUTPUT", "stderr": "", "timed_out": False,
            "cleanup_failed": False, "deadline_exhausted": False,
            "execution_policy": policy, "execution_policy_hash": sha256_json(policy),
        }


def probe_call(action_id="probe-1"):
    return RequestedTool(
        name="run_probe", action_id=action_id,
        arguments={"question": "Does this public behavior hold?", "python_source": "assert False"},
        turn_decision=PublicTurnDecision(mode="verify", basis="Test a public hypothesis."),
    )


def context(gateway, package, latest=()):
    return json.loads(runner._build_context(
        package=package, gateway=gateway, journal=gateway.journal, correction=None,
        latest_tool_results=list(latest), counters=runner._RunCounters(),
        elapsed_seconds=0, limits=DevLimits(),
    ))


def test_probe_schema_is_opt_in_single_action_and_correction_matches(gateway_factory):
    assert "run_probe" not in {item["name"] for item in dev_tool_schemas(finish_enabled=True)}
    schemas = dev_tool_schemas(finish_enabled=False, allowed_tools=frozenset({"run_probe"}))
    assert [item["name"] for item in schemas] == ["run_probe"]
    properties = schemas[0]["parameters"]["properties"]
    assert properties["python_source"]["maxLength"] == 8000
    assert properties["turn_decision"]["properties"]["evidence_goal"]["type"] == "null"
    validate_tool_batch([probe_call()], max_parallel_reads=4)
    with pytest.raises(ContractError):
        validate_tool_batch([probe_call(), read_calls()[0]], max_parallel_reads=4)
    gateway, _, _ = gateway_factory()
    for enabled in (False, True):
        gateway.probe_sandbox = FakeProbe() if enabled else None
        policy = runner._tool_policy(gateway, runner._RunCounters(), DevLimits())
        correction = runner._protocol_correction(
            turn_id="turn-1", code="test", issue="Choose one available action.",
            gateway=gateway, policy=policy,
        )
        assert ("run_probe" in correction["message"]) is enabled


@pytest.mark.parametrize("resource", ["model_calls", "tool_actions"])
def test_probe_cannot_spend_protected_or_required_read_allowance(gateway_factory, resource):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe()
    limits = DevLimits()
    protected = runner._tool_policy(
        gateway, runner._RunCounters(), limits,
    ).completion_budget_calls
    cap = limits.max_model_calls if resource == "model_calls" else limits.max_tool_actions
    for remaining, expected in ((protected + 1, True), (protected, False), (1, False)):
        counters = runner._RunCounters(**{resource: cap - remaining})
        policy = runner._tool_policy(gateway, counters, limits)
        assert ("run_probe" in policy.allowed_tools) is expected


def test_probe_is_diagnostic_replayed_and_historical_after_edit(gateway_factory, smoke_package):
    gateway, journal, workspace = gateway_factory()
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    baseline = gateway.current_diff_hash
    result = gateway.execute(probe_call())
    assert result.status == "succeeded"
    assert result.output["question"] == probe_call().arguments["question"]
    assert result.output["diff_hash"] == baseline
    assert gateway.checks_by_diff == {}
    assert gateway.has_current_mutation_evidence() is False
    assert gateway.execute(probe_call()).replayed is True
    assert backend.calls == 1
    restored = DevToolGateway(
        workspace=workspace, public_task=smoke_package.public, sandbox=gateway.sandbox,
        probe_sandbox=backend, journal=journal, limits=DevLimits(),
    )
    assert restored.execute(probe_call()).replayed is True
    assert backend.calls == 1
    changed = probe_call().model_copy(
        update={"arguments": {"question": "changed", "python_source": "0"}},
    )
    with pytest.raises(ActionConflict):
        restored.execute(changed)
    latest = context(gateway, smoke_package, [result])
    assert latest["recent_probes"][0]["delivery"] == "latest_tool_result"
    assert "stdout" not in latest["recent_probes"][0]
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    projected = context(gateway, smoke_package)
    assert projected["recent_probes"][0]["historical"] is True
    assert projected["recent_probes"][0]["diagnostic_only"] is True
    assert projected["recent_probes"][0]["stdout"] == "PUBLIC_PROBE_OUTPUT"
    assert projected["remaining_visible_check_ids"]


def test_probe_drift_preserves_execution_receipt(gateway_factory):
    gateway, _, _ = gateway_factory()
    baseline = gateway.current_diff_hash

    def drift(workspace):
        source = workspace / "mini_data_utils/csvlite.py"
        source.write_bytes(source.read_bytes() + b"\n# concurrent drift\n")

    gateway.probe_sandbox = FakeProbe(effect=drift)
    result = gateway.execute(probe_call())
    assert result.error_code == "RECOVERY_ERROR"
    assert result.workspace_diff_hash == baseline
    assert result.output["diff_hash"] == baseline
    assert result.output["observed_diff_hash"] == gateway.current_diff_hash != baseline
    assert result.output["execution_policy_hash"] == sha256_json(result.output["execution_policy"])
    assert runner._batch_execution_abort([result])[0].value == "TASK_FAILED"


class Crash(BaseException):
    pass


@pytest.mark.parametrize("crash_event", ["turn_decision_recorded", "tool_batch_finished"])
def test_probe_resume_and_manifest_keep_diagnostic_execution_once(
    tmp_path, monkeypatch, crash_event,
):
    backend = FakeProbe()
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)

    class ProbeThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            if not json.loads(context).get("recent_probes"):
                assert "run_probe" in {item["name"] for item in tools}
                return DevModelTurn(tool_calls=[probe_call()])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", ProbeThenMock)
    original_append = DevJournal.append
    crashed = False

    def append(self, event_type, payload):
        nonlocal crashed
        result = original_append(self, event_type, payload)
        if event_type == crash_event and not crashed:
            crashed = True
            raise Crash()
        return result

    request = DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml", state_root=tmp_path,
    )
    monkeypatch.setattr(DevJournal, "append", append)
    with pytest.raises(Crash):
        runner.run_dev(request)
    envelope_path = next((tmp_path / "runs").glob("*.envelope.json"))
    run_id = envelope_path.name.removesuffix(".envelope.json")
    mismatch = request.model_copy(update={"resume_run_id": run_id, "enable_probes": False})
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(mismatch)
    resumed_request = request.model_copy(update={"resume_run_id": run_id})
    result = runner.run_dev(resumed_request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["accepted_mutations"] == 1
    assert backend.calls == 1
    assert result["call_counts"]["model"] == 5
    assert result["call_counts"]["tool"] == 6
    manifest = json.loads((tmp_path / "artifacts/runs" / run_id / "manifest.json").read_text())
    assert manifest["probe_execution_count"] == len(manifest["probe_evidence"]) == 1
    receipt_hash = manifest["probe_evidence"][0]["content_hash"]
    assert result["artifact_hashes"]["probe_receipt_1"] == receipt_hash
    assert runner.run_dev(resumed_request)["runs"][0] == result
    assert backend.calls == 1


@pytest.mark.parametrize("fault", ["missing_image", "identity_drift"])
def test_probe_preflight_fails_before_model_turn(tmp_path, monkeypatch, fault):
    class MissingImage(FakeProbe):
        def preflight(self, **kwargs):
            if fault == "identity_drift":
                return {"image_digest": PROBE_IMAGE_DIGEST, "profile_hash": sha256_json("changed")}
            raise ContractError("pinned probe image is not local")

    monkeypatch.setattr(runner, "DockerProbeSandbox", MissingImage)
    monkeypatch.setattr(runner, "MockDevAdapter", lambda *_: pytest.fail("model was created"))
    result = runner.run_dev(DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml", state_root=tmp_path,
    ))["runs"][0]
    assert result["terminal"] == "PREFLIGHT_FAILED"
    assert result["call_counts"] == {"model": 0, "input_count": 0, "tool": 0}


def test_probe_cleanup_failure_keeps_receipt_without_further_execution(tmp_path, monkeypatch):
    class CleanupFailed(FakeProbe):
        def run_probe(self, *args, **kwargs):
            result = super().run_probe(*args, **kwargs)
            return {**result, "status": "cleanup_failed", "cleanup_failed": True}

    backend = CleanupFailed()
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)

    class OneProbe(MockDevAdapter):
        def next_turn(self, context, tools):
            assert backend.calls == 0, "model continued after cleanup uncertainty"
            return DevModelTurn(tool_calls=[probe_call()])

    monkeypatch.setattr(runner, "MockDevAdapter", OneProbe)
    result = runner.run_dev(DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml", state_root=tmp_path,
    ))["runs"][0]
    assert result["terminal"] == "TASK_FAILED"
    assert result["call_counts"] == {"model": 1, "input_count": 0, "tool": 1}
    assert result["evaluator"] is None
    assert "probe_receipt_1" in result["artifact_hashes"]
    assert backend.calls == 1
