from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_continuation as continuation
from diagnostics import mutation_advice_checkpoint as checkpoint
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ActionConflict, ContractError
from patchloop.sandbox import LocalSandbox
from patchloop.util import sha256_json


@pytest.fixture(scope="module")
def packet(source, tmp_path_factory):
    root = tmp_path_factory.mktemp("continuation-packet")
    return checkpoint.prepare(source, root / "packet")


def call(name, arguments, mode):
    return {
        "name": name,
        "action_id": "offline_" + name,
        "arguments": {
            **arguments,
            "turn_decision": {
                "mode": mode,
                "basis": "Synthetic local rehearsal.",
                "evidence_goal": None,
                "memory_update": None,
                "plan_update": None,
            },
        },
    }


def stop_steps():
    return [
        [
            call(
                "stop_task",
                {
                    "reason_code": "insufficient_public_evidence",
                    "summary": "Offline restoration checked.",
                },
                "stop",
            )
        ]
    ]


def branch_for(packet, tmp_path, arm):
    return continuation.restore(Path(packet["packet"]), packet["packet_hash"], tmp_path / arm, arm)


@pytest.mark.parametrize("arm", ["A", "B"])
def test_edit_check_submit_through_restored_gateway(packet, tmp_path, arm):
    branch = branch_for(packet, tmp_path, arm)
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {
        k: getattr(mutation, k)
        for k in ("path", "old_text", "new_text", "hypothesis", "expected_behavior")
    }
    args.update(occurrence=1, causal_revision=None)
    steps = [
        [call("replace_text", args, "mutate")],
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        [call("finish_task", {}, "finish")],
    ]
    client = continuation.ScriptedClient(steps)
    result = continuation.rehearse(branch, client)
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["first_state_restored"] and result["simulated_calls"] == 3
    assert result["agent_efficacy"] == result["docker_safety"] == "NOT_RUN"
    actual = {k: v for k, v in client.created[0].items() if k != "timeout"}
    assert actual == branch.selected
    assert sha256_json(actual) == packet["pair"][arm + "_request_hash"]
    assert result["new_billed_cost_nanos"] == 0 and result["simulated_counts"] == 3
    assert result["simulated_new_cost_nanos"] > 0
    assert not any(
        e["event_type"] == "action_started" and e["payload"]["tool"] == "run_probe"
        for e in branch.journal.events()[branch.inherited_events :]
    )
    with pytest.raises(ContractError, match="cannot be retried"):
        continuation.rehearse(branch, continuation.ScriptedClient(stop_steps()))
    after = json.loads(client.created[1]["input"][-1]["content"])["state"]
    assert after["completion_guidance"]["next_action"] is not None
    # Restart the actual gateway: completed mutation/check results must replay
    # without another edit or check, and conflicting reuse must still fail.
    gateway = DevToolGateway(
        workspace=branch.root / "workspaces" / branch.journal.run_id / "repo",
        public_task=branch.package.public,
        sandbox=LocalSandbox(),
        journal=branch.journal,
        limits=branch.request.limits,
    )
    before = branch.journal.path.read_bytes()
    with branch.journal.execution_lock():
        for event in branch.journal.events()[branch.inherited_events :]:
            p = event["payload"]
            if event["event_type"] != "action_started" or p["tool"] not in {
                "replace_text",
                "run_check",
            }:
                continue
            recorded = RequestedTool(
                name=p["tool"],
                action_id=p["action_id"],
                arguments=p["arguments"],
                turn_decision=p["turn_decision"],
            )
            assert gateway.execute(recorded).replayed
            changed = recorded.model_copy(update={"arguments": {}})
            with pytest.raises(ActionConflict):
                gateway.execute(changed)
    assert branch.journal.path.read_bytes() == before


@pytest.mark.parametrize(
    "failure, terminal",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("transport", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ],
)
def test_uncertainty_stops_without_tool_execution(packet, tmp_path, failure, terminal):
    branch = branch_for(packet, tmp_path, "A")
    client = continuation.ScriptedClient(stop_steps(), failure=failure)
    result = continuation.rehearse(branch, client)
    assert result["result"]["terminal"] == terminal, result
    assert result["stop_remaining"]
    assert result["simulated_billing_known"] == (failure == "count")
    assert result["simulated_new_cost_nanos"] == (0 if failure == "count" else None)
    new_events = branch.journal.events()[branch.inherited_events :]
    assert not any(e["event_type"] == "action_started" for e in new_events)


def test_failed_visible_check_cannot_become_acceptance(packet, tmp_path):
    branch = branch_for(packet, tmp_path, "A")
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {
        k: getattr(mutation, k)
        for k in ("path", "old_text", "new_text", "hypothesis", "expected_behavior")
    }
    args.update(new_text="def parse_rows(text):\n    return []", occurrence=1, causal_revision=None)
    steps = [
        [call("replace_text", args, "mutate")],
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        *stop_steps(),
    ]
    result = continuation.rehearse(branch, continuation.ScriptedClient(steps))
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["result"]["evaluator"] is None
    assert result["result"]["accepted_mutations"] == 1
    assert not any(e["event_type"] == "submission_recorded" for e in branch.journal.events())
    checks = [
        e["payload"]["result"]
        for e in branch.journal.events()
        if e["event_type"] == "action_finished" and e["payload"]["result"]["tool"] == "run_check"
    ]
    assert checks and checks[-1]["output"]["passed"] is False
