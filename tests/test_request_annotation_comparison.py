"""Request-only A/B checks with scripted responses and public fixture tool execution."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dev_probes import FakeProbe
from test_exception_frame_repair import (
    common,
    edit_call,
    no_external,  # noqa: F401 -- import the autouse credential/network/container guard.
    read_call,
    stop_call,
)

from diagnostics import exception_frame_repair as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

# An opaque synthetic packet tests request preservation. Actual file validation is
# independently covered by test_source_ready_packet; these lines are never executed.
PACKET = {"sources": [{"origin": "workspace", "path": "public_source.py",
                       "start_line": 1, "end_line": 148,
                       "content": "\n".join(["public fixture source"] * 148)}],
          "candidate_diff_hash": "seed"}


def _profile():
    return diagnostic.REQUEST_STRUCTURE_PROFILE


def _request(data, arm):
    return diagnostic.request_payload(data, arm, profile=_profile(), source_packet=PACKET)


def _search_call():
    value = read_call("search")
    value.update(name="search_files")
    value["arguments"] = {
        "query": "def parse_rows", "path_glob": "mini_data_utils/*.py",
        "turn_decision": value["arguments"]["turn_decision"],
    }
    return value


def _probe_call():
    return {"name": "run_probe", "action_id": "probe", "arguments": {
        "question": "Does the public behavior hold?", "python_source": "assert True",
        "purpose": {"kind": "helper"}, "replay_action_id": None, "call_path": None,
        "turn_decision": {"mode": "verify", "basis": "Check the public premise.",
                          "evidence_goal": None, "memory_update": None}}}


def _thin(call):
    value = copy.deepcopy(call)
    value["arguments"].pop("turn_decision")
    value["arguments"]["memory_update"] = None
    return value


def _run_arm(gateway_factory, arm, steps, *, policy=None):
    gateway, journal, _ = gateway_factory()
    gateway.agent_policy = policy or diagnostic.arm_policy(_profile(), arm)
    gateway.probe_sandbox = FakeProbe(status="passed")
    gateway.limits.max_accepted_mutations = 1
    gateway.deadline = ExecutionDeadline.from_remaining(60)
    loaded = SimpleNamespace(common=common(gateway.public_task))
    client = ScriptedClient(steps)
    adapter = OpenAIResponsesAdapter(diagnostic.config(), api_key="", client=client)
    ledger = DevCostLedger(_profile().invocation_cap, pricing_for_model(diagnostic.MODEL))
    result = diagnostic.run_model(loaded, arm, gateway, adapter, ledger,
        first_hash=sha256_json(_request(loaded.common, arm)), profile=_profile(),
        source_packet=PACKET)
    return result, client, journal


def _actions(journal):
    return [event["payload"]["result"] for event in journal.events()
            if event["event_type"] == "action_finished"]


def _prepare(smoke_package, tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    calibration = tmp_path / "calibration/calibration.json"
    calibration.parent.mkdir()
    calibration.write_text("{}", encoding="utf-8")
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(canonical_json(PACKET), encoding="utf-8")
    loaded = SimpleNamespace(common=common(smoke_package.public), environment_hash="environment",
        source=SimpleNamespace(root=source, public_path=source / "public.yaml"))
    monkeypatch.setattr(diagnostic, "load_calibration", lambda *_: loaded)
    monkeypatch.setattr(diagnostic, "validate_packet", lambda *_, **__: None)
    prepared = diagnostic.prepare(calibration, "calibration", tmp_path / "plan",
        tmp_path / "result", tmp_path / "unread.env", profile=_profile(),
        source_packet=packet_path, source_packet_hash=sha256_bytes(packet_path.read_bytes()))
    manifest = Path(prepared["manifest"])
    plan, actual = diagnostic.validate(manifest, prepared["manifest_hash"])
    assert actual is loaded
    return prepared, manifest, plan, packet_path


def test_pair_changes_only_annotations_and_retains_identical_full_evidence(smoke_package):
    data = common(smoke_package.public)
    a, b = [_request(data, arm) for arm in ("A", "B")]
    before = copy.deepcopy((a, b))
    assert diagnostic.verify_request_pair(a, b) is None
    assert (a, b) == before
    assert a["input"] == b["input"]
    focus = json.loads(a["input"][1]["content"])
    assert focus["source_packet"] == PACKET
    assert focus["current_failure"]["exception_diagnostics"]["calls"]
    assert len(focus["source_packet"]["sources"][0]["content"].splitlines()) == 148
    assert {k: v for k, v in a.items() if k != "tools"} == {
        k: v for k, v in b.items() if k != "tools"}
    left, right = ({schema["name"]: schema for schema in value["tools"]} for value in (a, b))
    assert left["replace_text"] == right["replace_text"]
    assert left["stop_task"] == right["stop_task"]
    for name in ("read_file", "search_files", "run_probe"):
        lp, rp = left[name]["parameters"], right[name]["parameters"]
        assert "turn_decision" in lp["required"] and "memory_update" not in lp["properties"]
        assert "memory_update" in rp["required"] and "turn_decision" not in rp["properties"]
        assert rp["properties"]["memory_update"]["type"] == ["object", "null"]
        assert rp["properties"]["memory_update"] == lp["properties"]["turn_decision"][
            "properties"]["memory_update"]


def test_pair_rejects_non_annotation_differences(smoke_package):
    a, b = [_request(common(smoke_package.public), arm) for arm in ("A", "B")]
    for field, other in (("max_output_tokens", 25_000), ("model", "other-model"),
                         ("reasoning", {"effort": "high"}), ("parallel_tool_calls", False)):
        with pytest.raises(ContractError):
            diagnostic.verify_request_pair(a, {**b, field: other})
    changed = copy.deepcopy(b)
    changed["input"][0]["content"] += " changed instructions"
    with pytest.raises(ContractError):
        diagnostic.verify_request_pair(a, changed)
    changed = copy.deepcopy(b)
    tool = next(row for row in changed["tools"] if row["name"] == "read_file")
    tool["parameters"]["properties"]["path"]["minLength"] = 2
    with pytest.raises(ContractError):
        diagnostic.verify_request_pair(a, changed)


def test_current_and_thin_requests_execute_equivalent_tools_and_preserve_native_transcript(
        gateway_factory):
    results = {}
    for arm in ("A", "B"):
        calls = [read_call(), _search_call(), _probe_call()]
        steps = [[_thin(call) if arm == "B" else call] for call in calls] + [[edit_call()]]
        actual, client, journal = _run_arm(gateway_factory, arm, steps)
        assert actual["terminal"] == "CANDIDATE_PRODUCED"
        assert (actual["normal_calls"], actual["correction_calls"], actual["tool_actions"],
                actual["new_mutations"], actual["diagnostic_probes"]) == (4, 0, 4, 1, 1)
        actions = _actions(journal)
        assert [row["tool"] for row in actions] == ["read_file", "search_files", "run_probe",
                                                  "replace_text"]
        assert all(row["status"] == "succeeded" and not row["error_code"] for row in actions)
        native = [row for row in client.created[-1]["input"] if row.get("type") == "function_call"]
        assert [row["name"] for row in native] == ["read_file", "search_files", "run_probe"]
        for row in native:
            arguments = json.loads(row["arguments"])
            if arm == "B":
                assert arguments["memory_update"] is None and "turn_decision" not in arguments
            else:
                assert arguments["turn_decision"] and "memory_update" not in arguments
        for counted, sent in zip(client.counted, client.created, strict=True):
            assert {k: sent[k] for k in counted if k != "timeout"} == {
                k: value for k, value in counted.items() if k != "timeout"}
        results[arm] = actual, actions
    assert results["A"][0]["candidate_diff_hash"] == results["B"][0]["candidate_diff_hash"]
    for index in (0, 1):
        assert results["A"][1][index]["output"]["spans"] == results["B"][1][index]["output"][
            "spans"]
    for field in ("status", "stdout", "stderr", "exit_code"):
        assert results["A"][1][2]["output"][field] == results["B"][1][2]["output"][field]


@pytest.mark.parametrize("repeat_invalid", [False, True])
def test_invalid_thin_annotation_is_retained_and_only_one_correction_is_available(
        gateway_factory, repeat_invalid):
    invalid = read_call("invalid-current-annotation")
    next_read = read_call("invalid-again") if repeat_invalid else _thin(read_call("fixed"))
    steps = [[invalid], [next_read],
             [stop_call() if repeat_invalid else edit_call()]]
    actual, client, journal = _run_arm(gateway_factory, "B", steps)
    assert actual["correction_calls"] == 1
    correction = client.created[1]
    assert correction["max_output_tokens"] == 25_000
    preserved = next(row for row in correction["input"] if row.get("type") == "function_call")
    assert json.loads(preserved["arguments"]) == invalid["arguments"]
    assert all(not row["action_id"].startswith("invalid") for row in _actions(journal))
    if repeat_invalid:
        assert actual["terminal"] == "CORRECTION_EXHAUSTED"
        assert len(client.created) == 2 and not _actions(journal)
    else:
        assert actual["terminal"] == "CANDIDATE_PRODUCED"
        assert len(client.created) == 3 and actual["new_mutations"] == 1


def test_gateway_arm_policy_mismatch_stops_before_counting(gateway_factory):
    with pytest.raises(ContractError, match="annotation policy"):
        _run_arm(gateway_factory, "B", [[_thin(read_call())]], policy="current")


def test_gateway_creation_uses_the_selected_arm_policy(gateway_factory, tmp_path, monkeypatch):
    fixture, _, workspace = gateway_factory()
    loaded = SimpleNamespace(public=fixture.public_task, dependencies=None, mutation={},
        old=SimpleNamespace(prepared_source_path=tmp_path / "source",
                            prepared_source_hash="source"),
        source=SimpleNamespace(record=lambda: {}),
        data={"candidate_diff_hash": fixture.current_diff_hash, "current_probe_identity": {}},
        environment=SimpleNamespace(evaluator_image="fixture-image", image_digest="fixture"))
    monkeypatch.setattr(diagnostic, "WorkspaceManager", lambda *_, **__:
                        SimpleNamespace(create=lambda *_, **__: workspace))
    monkeypatch.setattr(diagnostic, "restore_candidate", lambda *args: None)
    monkeypatch.setattr(diagnostic, "DockerProbeSandbox", lambda **_:
                        SimpleNamespace(preflight=lambda **_: {}))
    monkeypatch.setattr(diagnostic, "DockerSandbox", lambda *_:
                        SimpleNamespace(image_identity=lambda **_: "fixture"))
    for arm, policy in (("A", "current"), ("B", "thin")):
        gateway = diagnostic._gateway(loaded, tmp_path / arm, profile=_profile(),
                                      source_packet=PACKET, arm=arm)
        assert gateway.agent_policy == policy
        assert gateway.limits.max_tool_actions == 12 + diagnostic.anchor_reads(PACKET)
    assert all(profile.invocation_cap == Decimal("1.20") for profile in (
        diagnostic.DEFAULT_PROFILE, diagnostic.SOURCE_READY_PROFILE,
        diagnostic.OPPORTUNITY_PROFILE))


def test_pair_manifest_binds_caps_annotations_and_exact_first_requests(
        smoke_package, tmp_path, monkeypatch):
    prepared, manifest, plan, packet_path = _prepare(smoke_package, tmp_path, monkeypatch)
    assert plan["profile"] == "request-annotation-pair-v1" and plan["order"] == ["A", "B"]
    assert (plan["normal_calls"], plan["tool_actions"]) == (8, 12)
    assert plan["row_cap_usd"] == "1.20" and plan["new_cap_usd"] == "2.40"
    assert plan["request_annotation_policies"] == {"A": "current", "B": "thin"}
    assert prepared["credential_reads"] == prepared["provider_calls"] == 0
    for field, value in (("new_cap_usd", "1.20"), ("row_cap_usd", "2.40"),
                         ("request_annotation_policies", {"A": "thin", "B": "thin"})):
        changed = {**plan, field: value}
        manifest.write_text(canonical_json(changed), encoding="utf-8")
        with pytest.raises(ContractError):
            diagnostic.validate(manifest, sha256_bytes(manifest.read_bytes()))
    manifest.write_text(canonical_json(plan), encoding="utf-8")
    first = manifest.parent / "B-first.json"
    frozen = first.read_bytes()
    first.write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="prepared input"):
        diagnostic.validate(manifest, sha256_bytes(manifest.read_bytes()))
    first.write_bytes(frozen)
    packet_path.write_text(canonical_json({**PACKET, "candidate_diff_hash": "changed"}),
                           encoding="utf-8")
    with pytest.raises(ContractError, match="source packet identity"):
        diagnostic.validate(manifest, sha256_bytes(manifest.read_bytes()))


def test_pair_rejects_old_cap_or_wrong_hash_before_external_work(
        smoke_package, tmp_path, monkeypatch):
    prepared, manifest, _, _ = _prepare(smoke_package, tmp_path, monkeypatch)
    monkeypatch.setattr(diagnostic, "_gateway", lambda *_, **__:
                        pytest.fail("wrong approval reached workspace or sandbox setup"))
    with pytest.raises(ContractError, match="cap approval"):
        diagnostic.collect(manifest, prepared["manifest_hash"], Decimal("1.20"))
    with pytest.raises(ContractError, match="manifest hash"):
        diagnostic.collect(manifest, "wrong", Decimal("2.40"))
    assert not (tmp_path / "result").exists()


def test_collection_shares_the_exact_pair_cap_and_passes_each_arm_to_gateway(tmp_path, monkeypatch):
    loaded = SimpleNamespace(source_packet=PACKET, source=SimpleNamespace(
        root=tmp_path / "historical",
        public_path=repository_root() / "tasks/dev-train/current-dev20/13/public.yaml"))
    plan = {"result_root": str(tmp_path / "result"), "calibration": str(tmp_path / "cal/a.json"),
        "calibration_hash": "calibration", "profile": _profile().name,
        "order": ["A", "B"], "credential_file": str(tmp_path / "unread.env"),
        "first_request_hashes": {"A": "a", "B": "b"}, "interpretation": "synthetic"}
    monkeypatch.setattr(diagnostic, "validate", lambda *_: (plan, loaded))
    phases, groups = [], []

    def gateway(_, root, *, profile, source_packet, arm):
        assert profile == _profile() and source_packet == PACKET and root.name == arm
        phases.append((arm, "gateway"))
        return SimpleNamespace(workspace=root, agent_policy=diagnostic.arm_policy(profile, arm))

    monkeypatch.setattr(diagnostic, "_gateway", gateway)
    monkeypatch.setattr(diagnostic, "validate_packet", lambda *_, workspace:
                        phases.append((workspace.name, "validate")))
    monkeypatch.setattr(diagnostic, "observe_sources", lambda gateway, _:
                        phases.append((gateway.workspace.name, "observe")))
    def credential(_):
        arm, previous = phases[-1]
        assert previous == "observe"
        phases.append((arm, "credential_stub"))
        return "synthetic-not-a-key"

    monkeypatch.setattr(diagnostic, "load_exact_openai_api_key", credential)
    monkeypatch.setattr(diagnostic, "OpenAIResponsesAdapter", lambda *_, **__:
                        SimpleNamespace(client=SimpleNamespace(close=lambda: None)))

    def model(_, arm, gateway, adapter, group, *, profile, **kwargs):
        assert gateway.agent_policy == {"A": "current", "B": "thin"}[arm]
        assert group.cap_nanos == 2_400_000_000 and profile.row_cap == Decimal("1.20")
        groups.append(group)
        phases.append((arm, "model"))
        return {"terminal": "AGENT_STOPPED", "stop_remaining": False}

    monkeypatch.setattr(diagnostic, "run_model", model)
    result = diagnostic.collect(tmp_path / "plan/manifest.json", "synthetic-approved",
                                Decimal("2.40"))
    assert groups[0] is groups[1]
    assert phases == [(arm, phase) for arm in ("A", "B")
                      for phase in ("gateway", "validate", "observe", "credential_stub", "model")]
    assert [row["arm"] for row in result["rows"]] == ["A", "B"]
