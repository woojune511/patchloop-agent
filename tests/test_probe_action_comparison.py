"""The pair preserves context; all counts, responses and probes here are synthetic."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_dev_probes import FakeProbe
from test_observation_comparison import install_sdk, resolver
from test_observation_comparison import source as source  # noqa: F401

from diagnostics import probe_action_comparison as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.declaration_checkpoint import Source
from patchloop.dev import runner
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(scope="module")
def prepared(source, tmp_path_factory):
    root = tmp_path_factory.mktemp("action-pair")
    events = DevJournal(source.root, source.run_id).events()
    cut = [e for e in events if e["event_type"] == "model_input_prepared"][-1]["sequence"]
    target = next(e["payload"]["action_id"] for e in events
                  if e["event_type"] == "action_started" and e["payload"]["tool"] == "run_probe")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(diagnostic.live, "clean_implementation", lambda: None)
        patch.setattr(runner, "_require_tracked_clean_paths", lambda *a: None)
        patch.setattr(diagnostic, "environment", lambda *a: {"status": "READY"})
        patch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
        return diagnostic.prepare(source, cut, target, source.root.parent / "absent.env",
                                  root / "result", Decimal("1.20"), root / "plan")


@pytest.fixture
def manifest(prepared, tmp_path, monkeypatch):
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    plan["result_root"] = str(tmp_path / "result")
    path = tmp_path / "plan" / "manifest.json"
    path.parent.mkdir()
    path.write_text(canonical_json(plan), encoding="utf-8")
    monkeypatch.setattr(diagnostic.live, "clean_implementation", lambda: None)
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *a: None)
    monkeypatch.setattr(diagnostic, "environment", lambda *a: {"status": "READY"})
    monkeypatch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
    monkeypatch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
    return path


def test_control_changes_only_replay_schema_and_rejects_unoffered_mode():
    schemas = dev_tool_schemas(finish_enabled=True, allowed_tools={"run_probe", "read_file"})
    projected = diagnostic.project_tools(schemas, "A")
    assert projected[0] == schemas[0]
    a = next(t for t in projected if t["name"] == "run_probe")
    b = next(t for t in schemas if t["name"] == "run_probe")
    assert "replay_action_id" not in canonical_json(a)
    assert "replay_action_id" in b["parameters"]["required"]
    assert diagnostic.project_tools(schemas, "B") == schemas
    with diagnostic.surface("A"), pytest.raises(ContractError, match="not offered"):
        DevToolGateway.execute(None, RequestedTool(
            name="run_probe", action_id="attempt", arguments={"replay_action_id": "old"}))


def test_preparation_has_identical_public_context_and_preserves_parent(prepared, source):
    assert prepared["provider_calls"] == prepared["cost_nanos"] == 0
    assert prepared["pair_diff"] == "run_probe schema only"
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    assert plan["new_cap_nanos"] == 2_400_000_000
    assert plan["model"] == DevJournal(source.root, source.run_id).load_envelope().model
    assert not Path(plan["result_root"]).exists()
    assert plan["audit"]["target_id_visible"]
    journal = DevJournal(source.root, source.run_id)
    assert sha256_bytes(journal.path.read_bytes()) == source.journal_hash


@pytest.mark.parametrize("failure", [None, "count", "transport", "usage"])
def test_collector_checks_first_input_and_stops_group_on_uncertainty(
    manifest, source, monkeypatch, failure,
):
    plan = json.loads(manifest.read_bytes())
    first = ScriptedClient(stop_steps(), failure=failure)
    target = plan["target_action_id"]
    replay = call("run_probe", {"question": None, "python_source": None,
                                "replay_action_id": target}, "verify")
    second = ScriptedClient([[replay], *stop_steps()])
    install_sdk(monkeypatch, source, [first, second])
    probe = FakeProbe(status="passed")
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda **_: probe)
    result = diagnostic.collect(manifest, sha256_bytes(manifest.read_bytes()), Decimal("2.40"))
    if failure is None:
        assert result["stop_reason"] is None, result
        assert all(r["result"]["terminal"] == "AGENT_STOPPED" for r in result["rows"])
        assert probe.calls == 1
        branch = DevJournal(Path(plan["result_root"]) / "B", source.run_id)
        assert any(e["event_type"] == "action_finished"
                   and e["payload"]["result"].get("output", {}).get("replayed_from", {})
                   .get("action_id") == target for e in branch.events())
    else:
        assert result["stop_reason"]
        assert result["rows"][1]["status"] == "NOT_RUN"
        assert not second.created and probe.calls == 0
    assert (result["new_cost_nanos"] is not None) == result["billing_known"]


def test_nested_fork_can_be_audited_without_replaying_history(prepared, source):
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    root = Path(prepared["manifest"]).parent / "B"
    journal = DevJournal(root, source.run_id)
    nested = Source(root, source.run_id, sha256_bytes(journal.path.read_bytes()),
                    sha256_bytes(journal.envelope_path.read_bytes()),
                    source.public_path, source.public_hash)
    cut = [e for e in journal.events() if e["event_type"] == "model_input_prepared"][-1]["sequence"]
    audited = diagnostic.audit(nested, cut, plan["target_action_id"])
    assert audited["target"] == plan["audit"]["target"]
    assert audited["candidate_diff_hash"] == plan["audit"]["candidate_diff_hash"]


def test_collector_reaches_isolated_fixture_evaluation(manifest, source, monkeypatch):
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {key: getattr(mutation, key) for key in
            ("path", "old_text", "new_text", "hypothesis", "expected_behavior")}
    args.update(occurrence=1, causal_revision=None)
    repair = [[call("replace_text", args, "mutate")],
              [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
              [call("finish_task", {}, "finish")]]
    install_sdk(monkeypatch, source, [ScriptedClient(repair), ScriptedClient(stop_steps())])
    result = diagnostic.collect(manifest, sha256_bytes(manifest.read_bytes()), Decimal("2.40"))
    assert result["rows"][0]["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["rows"][0]["result"]["evaluator"]["safety_state"] == "NOT_RUN"
    assert result["rows"][1]["result"]["terminal"] == "AGENT_STOPPED"
    assert result["billing_known"] and not result["fresh_solve"]


@pytest.mark.parametrize("changed", ["hash", "cap", "request"])
def test_wrong_approval_or_prepared_request_never_dispatches(
    manifest, source, monkeypatch, changed,
):
    client = ScriptedClient(stop_steps())
    install_sdk(monkeypatch, source, [client])
    plan = json.loads(manifest.read_bytes())
    if changed == "request":
        plan["first_request_hashes"]["A"] = "sha256:" + "0" * 64
        manifest.write_text(canonical_json(plan), encoding="utf-8")
    if changed in {"hash", "cap"}:
        with pytest.raises(ContractError):
            diagnostic.collect(manifest, "bad" if changed == "hash" else
                               sha256_bytes(manifest.read_bytes()),
                               Decimal("1") if changed == "cap" else Decimal("2.40"))
    else:
        result = diagnostic.collect(manifest, sha256_bytes(manifest.read_bytes()), Decimal("2.40"))
        assert result["rows"][1]["status"] == "NOT_RUN"
    assert not client.created
