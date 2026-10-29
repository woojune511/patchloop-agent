"""Synthetic runner diagnostics; no live model or agent-quality evidence."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_first_reproduction_comparison import (
    argument_branch,
    execute,
    scripted_original,
)
from test_first_reproduction_comparison import source as original_source  # noqa: F401
from test_mutation_advice_checkpoint import source as source  # noqa: F401
from test_original_argument_correction import GOOD

from diagnostics import observation_exposure as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.contracts import Artifact, TaskEnvironment
from patchloop.dev import runner
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ActionConflict, ContractError
from patchloop.sandbox import LocalSandbox
from patchloop.util import sha256_bytes, sha256_json


def branch_for(source, tmp_path, arm="A", cap="1", *, preserve_parent_configuration=False):
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
            source, cut["sequence"], tmp_path / arm, arm, synthetic_cap_usd=Decimal(cap),
            preserve_parent_configuration=preserve_parent_configuration,
        )


@pytest.mark.parametrize("parent_policy", ["public-checks-v1", "reproduction-gated-v1"])
@pytest.mark.parametrize("preserve_parent_configuration", [True, False])
def test_fork_preserves_parent_verification_policy_only_when_requested(
    source, tmp_path, monkeypatch, parent_policy, preserve_parent_configuration,
):
    parent = diagnostic.read_checkpoint_envelope(source).model_copy(
        update={"verification_policy": parent_policy},
    )
    monkeypatch.setattr(diagnostic, "read_checkpoint_envelope", lambda _: parent)
    branch = branch_for(
        source, tmp_path, preserve_parent_configuration=preserve_parent_configuration,
    )
    expected = parent_policy if preserve_parent_configuration else "reproduction-gated-v1"
    assert branch.request.verification_policy == expected
    assert branch.envelope.verification_policy == expected
    assert branch.journal.load_envelope().verification_policy == expected


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
        # Repair context carries the same advisory verification catalog here.
        verification = state["repair_intent"]["verification"]
        if arm == "A":
            assert "observations" not in verification
            assert diagnostic.project(request, "A") == request
        else:
            observations = verification["observations"]["items"]
            failed = next(row for row in observations if row["action_id"] == "offline_run_probe")
            assert failed["execution"]["status"] == "failed"
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


@pytest.fixture(scope="module")
def settled_source(original_source, tmp_path_factory):  # noqa: F811
    """A real local probe result in a fork with references to an older source root."""
    root = tmp_path_factory.mktemp("settled-original")
    task_dir, package = runner._resolve_task_file(original_source[0].public_path)
    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64,
    )})
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(runner, "_resolve_task_file", lambda _: (task_dir, package))
        branch, plan, backend = argument_branch(original_source, root, patcher)
        receipt = execute(branch, plan, root, ScriptedClient([
            [scripted_original("first-original", GOOD)],
        ]))
    assert receipt["result"]["terminal"] == "FIRST_PROBE_SETTLED" and backend.calls == 1
    cut = [e for e in branch.journal.events() if e["event_type"] == "tool_batch_finished"][-1]
    saved = replace(
        branch.source, root=branch.root,
        journal_hash=sha256_bytes(branch.journal.path.read_bytes()),
        envelope_hash=sha256_bytes(branch.journal.envelope_path.read_bytes()),
    )
    return saved, cut, task_dir, package


def settled_fork(saved, cut, output, task_dir, package):
    with patch.object(runner, "_resolve_task_file", lambda _: (task_dir, package)):
        return diagnostic.fork(
            saved, cut["sequence"], output, "B", synthetic_cap_usd=Decimal("1"),
            preserve_parent_configuration=True, after_tool_batch=True,
        )


def test_after_tool_batch_preserves_evidence_budget_and_nested_artifacts(settled_source, tmp_path):
    saved, cut, task_dir, package = settled_source
    historical = DevJournal(saved.root, saved.run_id)
    before = {p: p.read_bytes() for p in (
        historical.path, historical.envelope_path, saved.root / "fork.json",
    )}
    branch = settled_fork(saved, cut, tmp_path / "continued", task_dir, package)
    prefix = [e for e in historical.events() if e["sequence"] <= cut["sequence"]]
    assert branch.journal.events()[:branch.inherited_events] == prefix
    assert prefix[-1] == cut and branch.active_elapsed_ms == cut["payload"]["active_elapsed_ms"]
    counters = runner._restore_counters(branch.journal)
    assert branch.remaining_budget["model_calls"] == branch.envelope.limits.max_model_calls - 3
    assert branch.remaining_budget["tool_actions"] == branch.envelope.limits.max_tool_actions - 7
    assert (counters.model_calls, counters.tool_actions) == (3, 7)
    assert branch.initial_spent_nanos == sum(
        row["cost_nanos"] for row in historical.provider_usage())
    assert branch.ledger.remaining_nanos == 10**9
    assert branch.original_obligation["stage"] == "acquired"
    assert len(branch.original_obligation["baseline_failure_case_ids"]) == 1
    latest = branch.latest_results[0]
    assert latest.action_id == "first-original"
    assert latest.output["reproduction"]["declared_failure_comparison"] == "matched"
    references = list(diagnostic._artifacts(prefix))
    assert any(not str(ref.path).startswith(str(saved.root)) for ref in references)
    with diagnostic.inherited_reads(branch):
        for ref in references:
            data = branch.store.read_bytes(ref)
            assert sha256_bytes(data) == ref.content_hash
            copied = branch.references[sha256_json(ref.model_dump(mode="json"))][1]
            assert branch.store.read_bytes(Artifact.model_validate(copied)) == data
    assert all(path.read_bytes() == data for path, data in before.items())
    with pytest.raises(ContractError, match="fresh output"):
        settled_fork(saved, cut, branch.root, task_dir, package)


@pytest.mark.parametrize("uncertainty", ["dispatch", "cleanup"])
def test_after_tool_batch_rejects_uncertainty_before_creating_output(
    settled_source, tmp_path, uncertainty,
):
    saved, cut, task_dir, package = settled_source
    parent = DevJournal(saved.root, saved.run_id)
    root = tmp_path / "uncertain"
    journal = DevJournal(root, saved.run_id)
    journal.write_envelope(parent.load_envelope())
    prefix = [e for e in parent.events() if e["sequence"] < cut["sequence"]]
    for event in prefix:
        payload = copy.deepcopy(event["payload"])
        if uncertainty == "cleanup" and event["event_type"] == "action_finished":
            payload["result"]["output"]["cleanup_failed"] = True
        journal.append(event["event_type"], payload)
    if uncertainty == "dispatch":
        journal.append("provider_call_started", {"call_id": "unsettled"})
    altered_cut = journal.append("tool_batch_finished", cut["payload"])
    altered = replace(saved, root=root, journal_hash=sha256_bytes(journal.path.read_bytes()),
                      envelope_hash=sha256_bytes(journal.envelope_path.read_bytes()))
    with pytest.raises(ContractError, match="uncertain|result identity"):
        settled_fork(altered, altered_cut, tmp_path / "rejected", task_dir, package)
    assert not (tmp_path / "rejected").exists()
