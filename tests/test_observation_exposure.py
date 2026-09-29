"""Synthetic runner diagnostics; no live model or agent-quality evidence."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import observation_exposure as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.contracts import TaskEnvironment
from patchloop.dev import runner
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ActionConflict, ContractError
from patchloop.sandbox import LocalSandbox
from patchloop.util import sha256_bytes


def branch_for(source, tmp_path, arm="A", cap="1"):
    journal = DevJournal(source.root, source.run_id)
    cut = [e for e in journal.events() if e["event_type"] == "model_input_prepared"][-1]
    task_dir, package = runner._resolve_task_file(source.public_path)
    package = package.model_copy(
        update={
            "environment": TaskEnvironment(
                evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64
            )
        }
    )
    with patch.object(runner, "_resolve_task_file", lambda _: (task_dir, package)):
        return diagnostic.fork(
            source, cut["sequence"], tmp_path / arm, arm, synthetic_cap_usd=Decimal(cap)
        )


def test_receipt_scope_requires_bound_fork_and_preserves_ordinary_resume(source, tmp_path):
    branch = branch_for(source, tmp_path)
    ordinary = runner._probe_evidence
    inherited = ordinary(branch.journal, branch.store, source.run_id)
    assert len(inherited) == 1
    with diagnostic.current_probe_receipts(branch):
        assert runner._probe_evidence(branch.journal, branch.store, source.run_id) == []
        branch.marker_hash = "changed"
        with pytest.raises(ContractError, match="lineage boundary changed"):
            runner._probe_evidence(branch.journal, branch.store, source.run_id)
    assert runner._probe_evidence is ordinary
    assert [ref.content_hash for ref in ordinary(branch.journal, branch.store, source.run_id)] == [
        ref.content_hash for ref in inherited
    ]


def test_projection_only_changes_catalogs():
    catalog = {"verification": {"observations": {"items": ["failure"]}, "concerns": []}}
    original = [
        {"role": "developer", "content": json.dumps({"state": {"working_notes": catalog}})},
        {
            "type": "function_call_output",
            "output": json.dumps({"working_notes": catalog, "observations": "raw"}),
        },
        {"encrypted_content": "opaque", "observations": "unrelated"},
    ]
    saved = copy.deepcopy(original)
    projected = diagnostic.project(original, "A")
    state = json.loads(projected[0]["content"])["state"]
    assert "observations" not in state["working_notes"]["verification"]
    assert json.loads(projected[1]["output"])["observations"] == "raw"
    assert projected[2] == original[2]
    assert diagnostic.project(original, "B") == original == saved
    assert diagnostic.project(catalog, "A") == catalog  # unrelated public JSON
    file_text = json.dumps({"working_notes": catalog})
    raw_source = {
        "type": "function_call_output",
        "output": json.dumps(
            {"tool": "read_file", "output": {"path": "example.json", "content": file_text}}
        ),
    }
    assert diagnostic.project(raw_source, "A") == raw_source


@pytest.mark.parametrize("arm", ["A", "B"])
def test_every_turn_after_new_failed_probe(source, tmp_path, arm):
    original = DevJournal(source.root, source.run_id).path.read_bytes()
    branch = branch_for(source, tmp_path, arm)
    client = ScriptedClient(
        [
            [
                call(
                    "run_probe",
                    {"question": "Synthetic failure", "python_source": "print('x')"},
                    "verify",
                )
            ],
            [
                call(
                    "read_file",
                    {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 10},
                    "inspect",
                )
            ],
            *stop_steps(),
        ]
    )
    result = diagnostic.rehearse(branch, client, probe_outcomes={"offline_run_probe": "failed"})
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["synthetic_dispatches"] == result["synthetic_counts"] == 3
    assert result["synthetic_probe_calls"] == ["offline_run_probe"]
    assert result["provider_calls"] == result["billed_cost_nanos"] == 0
    for request in client.created[1:]:
        state = json.loads(request["input"][-1]["content"])["state"]
        verification = state["working_notes"]["verification"]
        if arm == "A":
            assert "observations" not in verification
            assert diagnostic.project(request, "A") == request
        else:
            assert "offline_run_probe" in json.dumps(verification["observations"])
    assert DevJournal(source.root, source.run_id).path.read_bytes() == original
    with pytest.raises(ContractError, match="cannot be retried"):
        diagnostic.rehearse(branch, ScriptedClient(stop_steps()))


@pytest.mark.parametrize(
    "failure,terminal",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("transport", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ],
)
def test_uncertainty_stops(source, tmp_path, failure, terminal):
    branch = branch_for(source, tmp_path)
    result = diagnostic.rehearse(branch, ScriptedClient(stop_steps(), failure=failure))
    assert result["result"]["terminal"] == terminal, result
    assert result["stop_remaining"]
    assert not any(
        e["event_type"] == "action_started"
        for e in branch.journal.events()[branch.inherited_events :]
    )


def test_source_and_cap_are_bound(source, tmp_path):
    with pytest.raises(ContractError, match="source identity"):
        branch_for(replace(source, journal_hash="changed"), tmp_path)
    for cap in ["0", "-1", "NaN", "Infinity"]:
        with pytest.raises(ContractError, match="allowance"):
            branch_for(source, tmp_path, cap=cap)


def test_tiny_cap_stops_before_dispatch(source, tmp_path):
    branch = branch_for(source, tmp_path, cap="0.000000001")
    client = ScriptedClient(stop_steps())
    result = diagnostic.rehearse(branch, client)
    assert not client.created
    assert result["result"]["terminal"] == "COST_CAP_REACHED", result


def test_restarted_gateway_replays_completed_effects(source, tmp_path):
    branch = branch_for(source, tmp_path)
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {
        k: getattr(mutation, k)
        for k in ("path", "old_text", "new_text", "hypothesis", "expected_behavior")
    }
    args.update(occurrence=1, causal_revision=None)
    client = ScriptedClient(
        [
            [call("replace_text", args, "mutate")],
            [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
            [
                call(
                    "run_probe",
                    {"question": "Synthetic only", "python_source": "print('x')"},
                    "verify",
                )
            ],
            *stop_steps(),
        ]
    )
    result = diagnostic.rehearse(branch, client, probe_outcomes={"offline_run_probe": "failed"})
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["result"]["accepted_mutations"] == 1
    # A fresh journal/gateway reload must use durable receipts, with no probe engine.
    journal = DevJournal(branch.root, branch.journal.run_id)
    gateway = DevToolGateway(
        workspace=branch.workspace,
        public_task=branch.package.public,
        sandbox=LocalSandbox(),
        journal=journal,
        limits=branch.request.limits,
    )
    before = journal.path.read_bytes()
    replayed = []
    with journal.execution_lock():
        for event in journal.events()[branch.inherited_events :]:
            p = event["payload"]
            if event["event_type"] != "action_started" or p["tool"] not in {
                "replace_text",
                "run_check",
                "run_probe",
            }:
                continue
            recorded = RequestedTool(
                name=p["tool"],
                action_id=p["action_id"],
                arguments=p["arguments"],
                turn_decision=p["turn_decision"],
            )
            assert gateway.execute(recorded).replayed
            replayed.append(p["tool"])
            with pytest.raises(ActionConflict):
                gateway.execute(recorded.model_copy(update={"arguments": {}}))
    assert replayed == ["replace_text", "run_check", "run_probe"]
    assert journal.path.read_bytes() == before


def test_ordinary_resume_guard_is_not_relaxed(source, tmp_path):
    branch = branch_for(source, tmp_path)
    historical = DevJournal(source.root, source.run_id).load_envelope()
    assert historical.max_cost_nanos != branch.envelope.max_cost_nanos
    assert branch.ledger.remaining_nanos == 10**9
    with pytest.raises(ContractError):
        runner._validate_resume_envelope(historical, branch.envelope)


def test_runtime_change_and_finish_are_rejected(source, tmp_path, monkeypatch):
    branch = branch_for(source, tmp_path)
    with pytest.raises(ContractError, match="does not evaluate"):
        diagnostic.rehearse(branch, ScriptedClient([[call("finish_task", {}, "finish")]]))
    monkeypatch.setattr(diagnostic, "implementation_hash", lambda: "changed")
    with pytest.raises(ContractError, match="implementation changed"):
        diagnostic.rehearse(branch, ScriptedClient(stop_steps()))


@pytest.mark.parametrize("event_type", ["diagnostic_candidate_seeded", "terminal"])
def test_special_prefixes_rejected(source, tmp_path, event_type):
    # Build a separate hash-valid branch; never alter the original fixture journal.
    root = tmp_path / "ineligible"
    journal = DevJournal(root, source.run_id)
    historical = DevJournal(source.root, source.run_id)
    journal.write_envelope(historical.load_envelope())
    journal.append(event_type, {})
    cut = journal.append("model_input_prepared", {})
    altered = replace(
        source,
        root=root,
        journal_hash=sha256_bytes(journal.path.read_bytes()),
        envelope_hash=sha256_bytes(journal.envelope_path.read_bytes()),
    )
    with pytest.raises(ContractError, match="seeded or terminal"):
        diagnostic.fork(
            altered, cut["sequence"], tmp_path / "rejected", "A", synthetic_cap_usd=Decimal("1")
        )
    assert not (tmp_path / "rejected").exists()
