"""A frozen first decision, synthetic encrypted state and no real provider or tools."""
from __future__ import annotations

import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from test_decision_sampler import FakeClient, ProcessKilled, artifact_json, events

from diagnostics import decision_sampler as shared
from diagnostics import declaration_checkpoint as checkpoint
from diagnostics import declaration_sampler as sampler
from patchloop.contracts import TaskEnvironment
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.prepared_source import prepare_source
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, directory_hash, sha256_bytes, sha256_json

FIELD = '''buffer_mode: str = "ordinary"
"""Formatting options.

Ordinary callers may use the same format.
Representation does not declare a capability.
DECLARATION_END
"""
'''


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp("declaration")
    fixtures = root / "fixtures"
    snapshot = fixtures / "mini-data-utils"
    shutil.copytree(repository_root() / "fixtures/repositories/mini-data-utils", snapshot)
    target = snapshot / "mini_data_utils/csvlite.py"
    target.write_bytes(FIELD.encode() + b"\n" + target.read_bytes())
    task = root / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = yaml.safe_load((task / "public.yaml").read_text(encoding="utf-8"))
    public["split"] = "dev-train"
    public["repository"]["base_commit"] = directory_hash(snapshot)
    (task / "public.yaml").write_text(yaml.safe_dump(public), encoding="utf-8")
    manifest = prepare_source(repository_url=public["repository"]["url"],
                              base_commit=public["repository"]["base_commit"],
                              output=root / "prepared-source", fixture_root=fixtures)

    def response(value):
        n = len(client.created)
        value.model = "gpt-5.4-2026-03-05"
        call = value.output[1]
        if n == 1:
            call.name = "search_files"
            arguments = {"query": "buffer_mode", "path_glob": "**/*.py", "turn_decision": {
                "mode": "inspect", "basis": "Inspect public settings.",
                "evidence_goal": "Understand the declaration.", "memory_update": None,
                "plan_update": "Inspect, repair and check.",
            }}
        else:
            call.name = "stop_task"
            arguments = {"reason_code": "insufficient_public_evidence", "summary": "Fixture end.",
                         "turn_decision": {"mode": "stop", "basis": "End saved fixture.",
                                           "memory_update": None, "plan_update": None}}
        call.arguments = canonical_json(arguments)

    client = FakeClient(count_value=100, edit_response=response)
    request = DevRunRequest(
        provider="openai", model="gpt-5.4-2026-03-05", reasoning_effort="xhigh",
        context_policy="segmented-v1", planning_policy="brief-v1", repair_recheck=True,
        repeat=1, max_cost_usd=Decimal("1.20"), env_file=root / "absent.env",
        task=task / "public.yaml", prepared_source=manifest, state_root=root / "state",
    )
    task_dir, package = runner._resolve_task_file(request.task)
    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64,
    )})
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
        patch.setattr(runner, "_live_task_is_admitted", lambda *a, **k: None)
        patch.setattr(runner, "_live_source_preflight", lambda *a, **k: None)
        patch.setattr(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox())
        patch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
        patch.setattr(runner, "_resolve_task_file", lambda _: (task_dir, package))
        patch.setattr(runner, "OpenAIResponsesAdapter",
                      lambda config, **_: client.factory(config))
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert len(client.created) == 2
    journal = DevJournal(request.state_root, result["run_id"])
    source = checkpoint.Source(
        request.state_root, result["run_id"], sha256_bytes(journal.path.read_bytes()),
        sha256_bytes(journal.envelope_path.read_bytes()), request.task,
        sha256_bytes(request.task.read_bytes()),
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
        packet = sampler.prepare(source, root / "design", cap=Decimal("2.40"))
        plan = sampler.load_plan(root / "design/packet.json", packet["packet_hash"])
    return SimpleNamespace(root=root, source=source, plan=plan, packet=packet,
                           original_request=client.created[1], manifest=manifest)


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("real credential/provider or project execution reached")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)


def approval(prepared, root):
    plan = prepared.plan
    return shared.Approval(
        plan.packet_hash, sampler.sampler_hash(), root, repository_root() / ".env",
        Decimal(plan.packet["proposed_total_cap_usd"]), sha256_json(plan.packet["pricing"]),
        datetime.now(UTC).date().isoformat(),
    )


def client_for_model(**kwargs):
    def response(value):
        value.model = "gpt-5.4-2026-03-05"
        call = value.output[1]
        args = json.loads(call.arguments)
        args["turn_decision"]["plan_update"] = None
        call.arguments = canonical_json(args)
    return FakeClient(edit_response=response, **kwargs)


def test_exact_original_and_only_derived_search_state(prepared):
    plan = prepared.plan
    a, b = [json.loads(plan.cells[n].request_json) for n in (0, 1)]
    original = {k: v for k, v in prepared.original_request.items() if k != "timeout"}
    assert a == original
    assert "DECLARATION_END" not in json.dumps(a)
    assert "DECLARATION_END" in json.dumps(b)
    assert {k: v for k, v in a.items() if k != "input"} == {
        k: v for k, v in b.items() if k != "input"}
    sa, sb = [reconstruct_state(r["input"], context_policy=segments.POLICY) for r in (a, b)]
    for key in ("working_plan", "working_notes", "remaining_budget", "public_task", "current_diff",
                "visible_check_status", "action_horizon", "completion_guidance", "segment_handoff"):
        assert sa[key] == sb[key]
    for kind in ("reasoning", "function_call"):
        assert [i for i in a["input"] if i.get("type") == kind] == [
            i for i in b["input"] if i.get("type") == kind]
    assert [i for i in a["input"] if i.get("type") == "reasoning"]
    assert sa["working_plan"]["plan"]["text"] == "Inspect, repair and check."
    receipt = artifact_json(plan.packet["rebuild_receipt"])
    assert receipt["original_request_exact"] and receipt["first_plan_unchanged"]
    assert set(receipt["changed_context_fields"]) <= checkpoint.DERIVED_CONTEXT
    assert not any("private" in Path(p).name for p in receipt["inherited_artifacts"])


def test_four_independent_responses_reuse_cost_collector_without_tools(
    prepared, tmp_path, monkeypatch,
):
    from patchloop.dev.tools import DevToolGateway

    monkeypatch.setattr(DevToolGateway, "execute",
                        lambda *_: pytest.fail("sampled action executed"))
    grant = approval(prepared, tmp_path / "result")
    client = client_for_model()
    result = sampler.collect(prepared.plan, grant, adapter_factory=client.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED", result
    assert result["sample_count"] == result["provider_calls"] == result["input_count_calls"] == 4
    assert result["tool_executions"] == 0 and result["task_acceptance"] == "NOT_RUN"
    assert result["completed_comparison_blocks"] == 2
    assert shared.inspect_result(grant.result_root) == result
    assert client.created[0]["input"] == client.created[3]["input"]
    assert client.created[1]["input"] == client.created[2]["input"]
    recorded = events(grant)
    assert [(e["payload"]["arm"], e["payload"]["sample_number"]) for e in recorded
            if e["event_type"] == "provider_call_started"] == list(sampler.SCHEDULE)
    assert "PLAINTEXT_REASONING_SENTINEL" not in json.dumps(recorded)


@pytest.mark.parametrize("kind,expected", [
    ("count", "COUNT_TIMEOUT_OR_UNKNOWN"), ("provider", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
])
def test_uncertainty_stops_without_retry(prepared, tmp_path, kind, expected):
    client = client_for_model(count_error=kind == "count", create_error=kind == "provider")
    if kind == "billing":
        client.edit_response = lambda r: setattr(r.usage, "input_tokens", 101)
    result = sampler.collect(prepared.plan, approval(prepared, tmp_path / "result"),
                             adapter_factory=client.factory)
    assert result["terminal"] == expected
    assert len(client.counted) == 1 and len(client.created) <= 1


def test_interrupted_dispatch_inspects_without_resume(prepared, tmp_path):
    grant, client = approval(prepared, tmp_path / "result"), client_for_model()

    def kill(stage):
        if stage == "provider_returned":
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(prepared.plan, grant, adapter_factory=client.factory, hook=kill)
    assert shared.inspect_result(grant.result_root)["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    with pytest.raises(ContractError, match="exists"):
        sampler.collect(prepared.plan, grant, adapter_factory=client.factory)
    assert len(client.created) == 1


@pytest.mark.parametrize("field", ["packet_hash", "sampler_hash", "pricing_hash", "max_cost_usd",
                                   "credential_file"])
def test_wrong_grant_fails_before_count(prepared, tmp_path, field):
    grant = approval(prepared, tmp_path / "result")
    value = (Decimal("1.20") if field == "max_cost_usd" else tmp_path / "different.env"
             if field == "credential_file" else "sha256:" + "0" * 64)
    with pytest.raises(ContractError):
        sampler.collect(prepared.plan, replace(grant, **{field: value}),
                        adapter_factory=lambda _: pytest.fail("adapter initialized"))
    assert not grant.result_root.exists()


def test_changed_request_artifact_fails_before_count(prepared, tmp_path):
    ref = prepared.plan.packet["request_artifacts"]["B"]
    path = Path(ref["path"])
    original = path.read_bytes()
    try:
        path.write_bytes(original + b" ")
        with pytest.raises(RecoveryError):
            sampler.collect(prepared.plan, approval(prepared, tmp_path / "result"),
                            adapter_factory=lambda _: pytest.fail("adapter initialized"))
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize("damage", [
    "public", "continuation", "missing_continuation", "source", "checkpoint_hash",
])
def test_corrupt_or_missing_source_rejected_before_dispatch(prepared, tmp_path, damage):
    source = prepared.source
    loaded = checkpoint.load(source)
    if damage == "checkpoint_hash":
        with pytest.raises(ContractError):
            checkpoint.load(replace(source, journal_hash="sha256:" + "0" * 64))
        return
    if damage == "public":
        path = source.public_path
    elif damage == "source":
        path = prepared.manifest.parent / "workspaces/source/repo/mini_data_utils/csvlite.py"
    else:
        ref = next(e["payload"]["continuation_ref"] for e in loaded.prefix
                   if e["event_type"] == "turn_decision_recorded")
        path = Path(ref["artifact"]["path"])
    original = path.read_bytes()
    try:
        if damage == "missing_continuation":
            path.unlink()
        else:
            path.write_bytes(b"corrupted")
        with pytest.raises((ContractError, RecoveryError)):
            sampler.collect(prepared.plan, approval(prepared, tmp_path / "result"),
                            adapter_factory=lambda _: pytest.fail("adapter initialized"))
    finally:
        path.write_bytes(original)


def test_existing_preparation_and_protected_result_roots_rejected(prepared):
    with pytest.raises(ContractError, match="fresh"):
        sampler.prepare(prepared.source, prepared.plan.packet_path.parent, cap=Decimal("2.40"))
    grant = approval(prepared, prepared.manifest.parent / "result")
    with pytest.raises(ContractError, match="protected"):
        sampler.collect(prepared.plan, grant, adapter_factory=lambda _: pytest.fail("adapter"))
    assert not grant.result_root.exists()


def test_unrelated_budget_drift_prevents_packet_publication(prepared, tmp_path, monkeypatch):
    original = runner._build_context

    def drift(**kwargs):
        state = json.loads(original(**kwargs))
        state["remaining_budget"]["model_calls"] += 1
        return canonical_json(state)

    monkeypatch.setattr(runner, "_build_context", drift)
    with pytest.raises(ContractError, match="baseline canonical state"):
        sampler.prepare(prepared.source, tmp_path / "failed", cap=Decimal("2.40"))
    assert not (tmp_path / "failed/packet.json").exists()


def test_interrupted_expansion_is_not_a_collectible_packet(prepared, tmp_path, monkeypatch):
    def interrupted(*_):
        raise ProcessKilled()

    monkeypatch.setattr(checkpoint.expansion, "expand_search_result", interrupted)
    with pytest.raises(ProcessKilled):
        sampler.prepare(prepared.source, tmp_path / "failed", cap=Decimal("2.40"))
    assert not (tmp_path / "failed/packet.json").exists()
    assert sha256_bytes((prepared.source.root / "runs" /
                         f"{prepared.source.run_id}.jsonl").read_bytes()) == (
        prepared.source.journal_hash)
