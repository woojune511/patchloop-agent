"""Scripted provider and public fixture only; no Docker, credential or evaluator calls."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import exception_frame_repair as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.contracts import DevToolResult
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("external execution is forbidden")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("patchloop.agent.model.create_openai_client", forbidden)
    monkeypatch.setattr(diagnostic, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(diagnostic.DockerProbeSandbox, "run_probe", forbidden)
    monkeypatch.setattr(diagnostic.DockerSandbox, "run_check", forbidden)


def result(*, matched=True, exception=False):
    calls = []
    for index in (1, 2):
        calls.append({"call_id": f"call-{index}", "inputs": [], "start_cwd": "/scratch",
            "cwd": "/scratch", "arguments": {"argv": [str(index)]},
            "outcome": "returned", "exception": None, "exit_code": None,
            "capture": {"status": "complete", "stdout": "control" if index == 2 else "",
                        "stderr": "", "scope": "python-streams"}})
    if exception:
        calls[0].update(outcome="raised",
                        exception={"type": "FileNotFoundError", "message": "missing"})
    return {"status": "succeeded", "workspace_diff_hash": "seed", "output": {
        "status": "passed", "exit_code": 0, "execution_policy": {"cleanup_status": "confirmed"},
        "reproduction": {"observed_json": "{}",
            "comparison": "matched" if matched else "mismatched",
            "binding": {"program_hash": "program", "case_id": "case",
                        "definition": {"expected_json": "{}"}},
            "call_observation": {"calls": calls, "incomplete": False,
                                 "execution_environment": {"profile_hash": "current"}}},
        "exception_diagnostics": {"calls": [{"call_id": "call-1", "details": {
            "exceptions": [{"frames": [{"function": "trace-only-location"}],
                            "relation": "context", "type": "AttributeError"}]}}]}}}


def common(public):
    return {"public_task": public.model_dump(mode="json"), "candidate_patch": "synthetic seed",
            "candidate_diff_hash": "seed", "original_program": "print('original')",
            "initial_observations": {
                "base": diagnostic._public_result(result(matched=False)),
                "candidate": diagnostic._public_result(result(exception=True))}}


def read_call(action="read"):
    return {"name": "read_file", "action_id": action, "arguments": {
        "path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90,
        "turn_decision": {"mode": "inspect", "basis": "Inspect current code.",
                          "evidence_goal": "Read the edit anchor.", "memory_update": None}}}


def stop_call():
    return {"name": "stop_task", "action_id": "stop", "arguments": {
        "reason_code": "insufficient_public_evidence", "summary": "No justified edit."}}


def edit_call():
    edit = MOCK_MUTATIONS["csv-quoted-newline"]
    return {"name": "replace_text", "action_id": "edit", "arguments": {
        "path": edit.path, "old_text": edit.old_text, "new_text": edit.new_text,
        "occurrence": 1, "hypothesis": edit.hypothesis,
        "expected_behavior": edit.expected_behavior}}


def tool_failure(call, kind):
    if kind == "deadline":
        raise ExecutionDeadlineExceeded("started execution has no completion receipt")
    return DevToolResult(action_id=call.action_id, input_hash="synthetic", tool=call.name,
        status="failed", error_code={"recovery": "RECOVERY_ERROR",
                                     "resume": "RESUME_CONTRACT_MISMATCH"}.get(kind),
        output={"cleanup_failed": kind == "cleanup", "timed_out": kind == "timed_out",
                "execution_policy": {"cleanup_status": "confirmed"}})


def run(gateway_factory, steps, *, failure=None, cap="1.20", execution_failure=None,
        profile=diagnostic.DEFAULT_PROFILE, source_packet=None):
    gateway, journal, _ = gateway_factory()
    gateway.deadline = ExecutionDeadline.from_remaining(60)
    gateway.limits.max_accepted_mutations = 1
    if execution_failure:
        execute = gateway.execute_batch
        gateway.execute_batch = lambda calls: (execute(calls)
            if calls[0].name == "stop_task" else [tool_failure(calls[0], execution_failure)])
    loaded = SimpleNamespace(common=common(gateway.public_task))
    client = ScriptedClient(steps, failure=failure)
    adapter = OpenAIResponsesAdapter(diagnostic.config(), api_key="", client=client)
    first = diagnostic.request_payload(loaded.common, "B", profile=profile,
                                       source_packet=source_packet)
    group = DevCostLedger(Decimal(cap), pricing_for_model(diagnostic.MODEL))
    actual = diagnostic.run_model(loaded, "B", gateway, adapter, group,
                                 first_hash=sha256_json(first), profile=profile,
                                 source_packet=source_packet)
    return actual, client, journal, group


def test_pair_only_changes_initial_frames_and_ignores_unlisted_receipt_fields(smoke_package):
    data = common(smoke_package.public)
    a, b = [diagnostic.request_payload(data, arm) for arm in ("A", "B")]
    diagnostic.verify_pair(a, b)
    assert "trace-only-location" not in json.dumps(a)
    assert "trace-only-location" in json.dumps(b)
    assert "FileNotFoundError" in json.dumps(a)
    assert a["tools"] == b["tools"]
    assert a["max_output_tokens"] == b["max_output_tokens"] == 40000
    assert a["reasoning"] == b["reasoning"] == {"effort": "xhigh"}
    b["max_output_tokens"] = 25000
    with pytest.raises(ContractError, match="beyond"):
        diagnostic.verify_pair(a, b)
    receipt = result()
    receipt["output"]["private_spec"] = "not-model-visible"
    assert "not-model-visible" not in json.dumps(diagnostic._public_result(receipt))


def test_read_then_one_edit_stops_without_consuming_another_response(gateway_factory):
    actual, client, journal, group = run(
        gateway_factory, [[read_call()], [edit_call()], [stop_call()]])
    assert actual["terminal"] == "CANDIDATE_PRODUCED"
    assert actual["new_mutations"] == 1 and actual["normal_calls"] == 2
    assert actual["correction_calls"] == 0 and len(client.created) == 2
    assert actual["new_cost_nanos"] == group.spent_nanos < 600_000_000
    calls = [e for e in journal.events() if e["event_type"] == "action_finished"]
    assert [e["payload"]["result"]["tool"] for e in calls] == ["read_file", "replace_text"]
    for counted, sent in zip(client.counted, client.created, strict=True):
        assert {k: sent[k] for k in counted if k != "timeout"} == {
            k: v for k, v in counted.items() if k != "timeout"}


def test_one_protocol_correction_has_separate_output_ceiling(gateway_factory):
    actual, client, _, _ = run(gateway_factory, [[], [stop_call()]])
    assert actual["terminal"] == "AGENT_STOPPED"
    assert actual["normal_calls"] == actual["correction_calls"] == 1
    assert [r["max_output_tokens"] for r in client.created] == [40000, 25000]


@pytest.mark.parametrize("failure,terminal", [
    ("count", "COUNT_UNCERTAIN"), ("transport", "PROVIDER_UNCERTAIN"),
    ("usage", "BILLING_UNCERTAIN"),
])
def test_uncertainty_stops_before_any_tool(gateway_factory, failure, terminal):
    actual, client, journal, _ = run(gateway_factory, [[read_call()]], failure=failure)
    assert actual["terminal"] == terminal and actual["stop_remaining"]
    assert actual["billing_known"] is False
    assert not any(e["event_type"] == "action_started" for e in journal.events())
    assert len(client.created) <= 1
    if failure == "usage":
        unknown = next(e["payload"] for e in journal.events()
                       if e["event_type"] == "provider_usage_unknown")
        evidence = unknown["usage_evidence"]
        assert (unknown["call_id"], evidence["failure_kind"], evidence["requested_input_tokens"]) \
            == ("call-count-0-0-0", "usage_null", 100)
        assert evidence["fields"]["input_tokens"] == {"state": "unavailable"}
        assert evidence["response_diagnostics"]["body_state"] == "unavailable"


def test_second_invalid_response_ends_correction(gateway_factory):
    actual, client, _, _ = run(gateway_factory, [[], [], [stop_call()]])
    assert actual["terminal"] == "CORRECTION_EXHAUSTED" and len(client.created) == 2


def test_normal_and_cost_limits_stop_before_additional_dispatch(gateway_factory):
    actual, client, _, _ = run(gateway_factory,
                               [[read_call(str(i))] for i in range(5)])
    assert actual["terminal"] == "MODEL_LIMIT" and len(client.created) == 4
    actual, client, _, _ = run(gateway_factory, [[read_call()]], cap="0.001")
    assert actual["terminal"] == "COST_CAP_REACHED" and len(client.created) == 0


def test_source_ready_can_edit_after_four_responses_and_stops_after_one_edit(gateway_factory):
    packet = {"sources": [{"origin": "workspace", "path": "public_source.py"}],
              "candidate_diff_hash": "seed"}
    actual, client, _, _ = run(gateway_factory,
        [[read_call(str(i))] for i in range(4)] + [[edit_call()], [stop_call()]],
        profile=diagnostic.SOURCE_READY_PROFILE, source_packet=packet)
    assert actual["terminal"] == "CANDIDATE_PRODUCED"
    assert actual["normal_calls"] == len(client.created) == 5 and actual["new_mutations"] == 1
    first = client.created[0]
    assert "eight normal" in first["input"][0]["content"]
    focus = json.loads(first["input"][1]["content"])
    assert focus["source_packet"] == packet
    assert focus["current_failure"]["exception_diagnostics"]["calls"]
    initial = json.loads(first["input"][2]["content"])
    assert set(initial["initial_observations"]) == {"base"}
    assert first["max_output_tokens"] == 40000


def test_source_ready_has_eight_response_horizon_and_one_correction(gateway_factory):
    packet = {"sources": []}
    actual, client, _, _ = run(gateway_factory,
        [[read_call(str(i))] for i in range(7)] + [[], [stop_call()]],
        profile=diagnostic.SOURCE_READY_PROFILE, source_packet=packet)
    assert actual["normal_calls"] == 8 and actual["correction_calls"] == 1
    assert actual["terminal"] == "AGENT_STOPPED" and len(client.created) == 9
    assert [r["max_output_tokens"] for r in client.created] == [40000] * 8 + [25000]
    last = json.loads(client.created[-1]["input"][-1]["content"])
    assert last["remaining"]["normal_calls"] == 0


def test_exhausted_tool_allowance_stops_before_count_and_dispatch(gateway_factory):
    steps = [[read_call(f"read-{2 * i}"), read_call(f"read-{2 * i + 1}")]
             for i in range(6)] + [[stop_call()]]
    actual, client, journal, _ = run(gateway_factory, steps,
        profile=diagnostic.SOURCE_READY_PROFILE, source_packet={"sources": []})
    assert actual["terminal"] == "TOOL_LIMIT" and actual["billing_known"]
    assert actual["normal_calls"] == 6 and actual["tool_actions"] == 12
    assert len(client.counted) == len(client.created) == 6
    assert actual["new_mutations"] == 0 and not actual["stop_remaining"]
    assert sum(e["event_type"] == "input_count_started" for e in journal.events()) == 6


def test_last_available_tool_action_can_still_produce_the_candidate(gateway_factory):
    steps = [[read_call(f"read-{2 * i}"), read_call(f"read-{2 * i + 1}")]
             for i in range(5)] + [[read_call("read-10")], [edit_call()], [stop_call()]]
    actual, client, _, _ = run(gateway_factory, steps,
        profile=diagnostic.SOURCE_READY_PROFILE, source_packet={"sources": []})
    assert actual["terminal"] == "CANDIDATE_PRODUCED" and actual["new_mutations"] == 1
    assert actual["tool_actions"] == 12 and actual["normal_calls"] == 7
    assert len(client.counted) == len(client.created) == 7


@pytest.mark.parametrize("kind", ["cleanup", "recovery", "resume", "deadline"])
def test_tool_uncertainty_stops_all_but_retains_known_billing(gateway_factory, kind):
    actual, client, _, _ = run(gateway_factory, [[read_call()], [stop_call()]],
                               execution_failure=kind)
    assert actual["terminal"] == "TASK_FAILED" and actual["stop_remaining"]
    assert actual["billing_known"] is True and len(client.created) == 1


def test_settled_timeout_with_confirmed_cleanup_is_not_uncertain(gateway_factory):
    actual, client, _, _ = run(gateway_factory, [[read_call()], [stop_call()]],
                               execution_failure="timed_out")
    assert actual["terminal"] == "AGENT_STOPPED" and not actual["stop_remaining"]
    assert actual["billing_known"] is True and len(client.created) == 2


def test_boolean_match_does_not_hide_exception_or_changed_control():
    base = result(matched=False)
    assert diagnostic.case_support(base, result())["supported"]
    assert not diagnostic.case_support(base, result(exception=True))["supported"]
    for kind in ("control", "profile", "incomplete", "setup", "program"):
        current = result()
        trace = current["output"]["reproduction"]["call_observation"]
        if kind == "control":
            trace["calls"][1]["capture"]["stdout"] = "changed"
        elif kind == "profile":
            trace["execution_environment"]["profile_hash"] = "other"
        elif kind == "incomplete":
            trace["incomplete"] = True
        elif kind == "program":
            current["output"]["reproduction"]["binding"]["program_hash"] = "changed"
        else:
            current["output"]["setup_checks"] = {"status": "failed"}
        assert not diagnostic.case_support(base, current)["supported"], kind


def test_missing_exact_approval_never_reads_credentials(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="cap approval"):
        diagnostic.collect(manifest, "wrong", Decimal("0.60"))
    with pytest.raises(ContractError, match="manifest hash"):
        diagnostic.collect(manifest, "wrong", Decimal("1.20"))


def test_prepare_freezes_inputs_without_provider_or_target(smoke_package, tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    calibration_dir = tmp_path / "calibration"
    calibration_dir.mkdir()
    calibration = calibration_dir / "calibration.json"
    calibration.write_text("{}", encoding="utf-8")
    loaded = SimpleNamespace(common=common(smoke_package.public), environment_hash="environment",
                             source=SimpleNamespace(root=source,
                                                    public_path=source / "public.yaml"))
    monkeypatch.setattr(diagnostic, "load_calibration", lambda *args: loaded)
    prepared = diagnostic.prepare(calibration, "synthetic", tmp_path / "plan",
                                  tmp_path / "result", tmp_path / "unread.env")
    assert prepared["provider_calls"] == prepared["input_count_calls"] == 0
    assert prepared["credential_reads"] == prepared["target_executions"] == 0
    plan, _ = diagnostic.validate(Path(prepared["manifest"]), prepared["manifest_hash"])
    assert plan["paid_execution_authorized"] is False
    assert plan["row_cap_usd"] == "0.60" and plan["new_cap_usd"] == "1.20"
    assert plan["profile"] == diagnostic.DEFAULT_PROFILE.name
    assert plan["order"] == ["A", "B"] and plan["normal_calls"] == 4


@pytest.mark.parametrize("profile", [diagnostic.SOURCE_READY_PROFILE,
                                   diagnostic.OPPORTUNITY_PROFILE])
def test_source_ready_manifest_binds_scope_and_source_identity(smoke_package, tmp_path,
                                                              monkeypatch, profile):
    source = tmp_path / "source"
    source.mkdir()
    calibration = tmp_path / "calibration/calibration.json"
    calibration.parent.mkdir()
    calibration.write_text("{}", encoding="utf-8")
    packet_path = tmp_path / "packet.json"
    packet = {"sources": [{"origin": "workspace", "path": "public_source.py"}],
              "candidate_diff_hash": "seed"}
    packet_path.write_text(canonical_json(packet), encoding="utf-8")
    loaded = SimpleNamespace(common=common(smoke_package.public), environment_hash="environment",
                             source=SimpleNamespace(root=source,
                                                    public_path=source / "public.yaml"))
    checked = []
    monkeypatch.setattr(diagnostic, "load_calibration", lambda *args: loaded)
    monkeypatch.setattr(diagnostic, "validate_packet",
                        lambda *args, **kw: checked.append((args, kw)))
    prepared = diagnostic.prepare(calibration, "calibration", tmp_path / "plan",
        tmp_path / "result", tmp_path / "unread.env", profile=profile,
        source_packet=packet_path, source_packet_hash=sha256_bytes(packet_path.read_bytes()))
    manifest = Path(prepared["manifest"])
    plan, _ = diagnostic.validate(manifest, prepared["manifest_hash"])
    assert plan["profile"] == profile.name
    assert plan["order"] == ["B"] and plan["normal_calls"] == 8
    assert plan["row_cap_usd"] == plan["new_cap_usd"] == "1.20"
    assert plan["source_packet"] == str(packet_path.resolve()) and len(checked) == 2
    assert plan["host_source_reads"] == diagnostic.anchor_reads(packet)
    assert checked[-1][0] == (loaded, packet, "calibration")
    assert not (manifest.parent / "A-first.json").exists()
    with monkeypatch.context() as changed:
        changed.setattr(diagnostic, "source_helper_hash", lambda: "changed-helper")
        with pytest.raises(ContractError, match="source helper changed"):
            diagnostic.validate(manifest, prepared["manifest_hash"])
    for field, other in (("normal_calls", 4), ("row_cap_usd", "0.60"), ("order", ["A", "B"])):
        changed = {**plan, field: other}
        manifest.write_text(canonical_json(changed), encoding="utf-8")
        with pytest.raises(ContractError, match="scope changed"):
            diagnostic.validate(manifest, sha256_bytes(manifest.read_bytes()))
    manifest.write_text(canonical_json(plan), encoding="utf-8")
    packet_path.write_text(canonical_json({**packet, "candidate_diff_hash": "other"}),
                           encoding="utf-8")
    with pytest.raises(ContractError, match="source packet identity changed"):
        diagnostic.collect(manifest, sha256_bytes(manifest.read_bytes()), Decimal("1.20"))


@pytest.mark.parametrize("failure", ["validate", "observe"])
def test_source_ready_rechecks_workspace_and_anchors_before_credentials(tmp_path, monkeypatch,
                                                                       failure):
    packet, calls = {"sources": [{"origin": "workspace"}]}, []
    loaded = SimpleNamespace(source_packet=packet, source=SimpleNamespace(
        root=tmp_path / "historical",
        public_path=repository_root() / "tasks/dev-train/current-dev20/13/public.yaml"))
    plan = {"result_root": str(tmp_path / "result"), "calibration": str(tmp_path / "cal/a.json"),
            "calibration_hash": "calibration", "profile": diagnostic.SOURCE_READY_PROFILE.name,
            "order": ["B"], "credential_file": str(tmp_path / "unread.env")}
    gateway = SimpleNamespace(workspace=tmp_path / "workspace")
    monkeypatch.setattr(diagnostic, "validate", lambda *_: (plan, loaded))
    monkeypatch.setattr(diagnostic, "_gateway", lambda *_, **__: gateway)

    def validate_packet(actual_loaded, actual_packet, digest, *, workspace):
        assert (actual_loaded, actual_packet, digest, workspace) == (
            loaded, packet, "calibration", gateway.workspace)
        calls.append("validate")
        if failure == "validate":
            raise ContractError("source drift")

    def observe_sources(actual_gateway, actual_packet):
        assert (actual_gateway, actual_packet) == (gateway, packet)
        calls.append("observe")
        raise ContractError("source drift")

    monkeypatch.setattr(diagnostic, "validate_packet", validate_packet)
    monkeypatch.setattr(diagnostic, "observe_sources", observe_sources)
    with pytest.raises(ContractError, match="source drift"):
        diagnostic.collect(tmp_path / "plan/manifest.json", "approved", Decimal("1.20"))
    assert calls == (["validate"] if failure == "validate" else ["validate", "observe"])


def host_fixture(*, fail_at, kind):
    calls = []
    loaded = SimpleNamespace(rows={"base": result(matched=False)},
        data={"original_arguments": {}},
        public=SimpleNamespace(visible_checks=[SimpleNamespace(id=k) for k in ("first", "second")]))

    def execute(call):
        calls.append(call.action_id)
        if call.action_id == fail_at:
            return tool_failure(call, kind)
        packet = result()
        return DevToolResult(**packet, action_id=call.action_id,
                             input_hash="synthetic", tool=call.name)

    gateway = SimpleNamespace(current_diff_hash="seed", execute=execute)
    return loaded, gateway, calls


@pytest.mark.parametrize("fail_at,kind,expected", [
    ("host-original", "cleanup", ["host-original"]),
    ("host-original", "deadline", ["host-original"]),
    ("host-first", "recovery", ["host-original", "host-first"]),
    ("host-first", "resume", ["host-original", "host-first"]),
])
def test_host_checks_stop_sequentially_on_uncertainty(fail_at, kind, expected):
    loaded, gateway, calls = host_fixture(fail_at=fail_at, kind=kind)
    actual = diagnostic.verify_candidate(loaded, gateway)
    assert actual["host_terminal"] == "TASK_FAILED" and actual["stop_remaining"]
    assert calls == expected


def test_host_settled_timeout_can_continue_to_public_regression():
    loaded, gateway, calls = host_fixture(fail_at="host-original", kind="timed_out")
    actual = diagnostic.verify_candidate(loaded, gateway)
    assert actual["host_terminal"] == "CHECKS_COMPLETED" and not actual["stop_remaining"]
    assert actual["case_support"]["supported"] is False
    assert calls == ["host-original", "host-first", "host-second"]


def test_host_uncertainty_prevents_the_second_arm(tmp_path, monkeypatch):
    loaded, host, calls = host_fixture(fail_at="host-original", kind="cleanup")
    loaded.source = SimpleNamespace(root=tmp_path / "historical",
        public_path=repository_root() / "tasks/dev-train/current-dev20/13/public.yaml")
    loaded.source_packet = None
    plan = {"result_root": str(tmp_path / "result"), "calibration": str(tmp_path / "cal/a.json"),
            "profile": diagnostic.DEFAULT_PROFILE.name,
            "order": ["A", "B"], "credential_file": str(tmp_path / "unread.env"),
            "first_request_hashes": {"A": "a", "B": "b"}, "interpretation": "synthetic"}
    manifest = tmp_path / "plan/manifest.json"
    monkeypatch.setattr(diagnostic, "validate", lambda *_: (plan, loaded))
    arms = []

    def gateway(_, root, **_kwargs):
        arms.append(root.name)
        return SimpleNamespace(workspace=tmp_path, sandbox=None, probe_sandbox=None)

    monkeypatch.setattr(diagnostic, "_gateway", gateway)
    monkeypatch.setattr(diagnostic, "load_exact_openai_api_key", lambda *_: "synthetic-not-a-key")
    monkeypatch.setattr(diagnostic, "OpenAIResponsesAdapter", lambda *_args, **_kwargs:
                        SimpleNamespace(client=SimpleNamespace(close=lambda: None)))
    monkeypatch.setattr(diagnostic, "DevToolGateway", lambda **_: host)
    monkeypatch.setattr(diagnostic, "run_model", lambda *_args, **_kwargs:
                        {"terminal": "CANDIDATE_PRODUCED", "stop_remaining": False})
    actual = diagnostic.collect(manifest, "synthetic-approved", Decimal("1.20"))
    assert arms == ["A"] and calls == ["host-original"]
    assert len(actual["rows"]) == 1 and actual["rows"][0]["stop_remaining"]
