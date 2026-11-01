"""Diagnostic host work shares the saved invocation's tool and time caps."""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from test_first_reproduction_comparison import source  # noqa: F401

from diagnostics import observation_exposure as diagnostic
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_json


def fork(checkpoint, output, **options):
    saved, _, env_file = checkpoint
    journal = DevJournal(saved.root, saved.run_id)
    cut = next(e for e in reversed(journal.events()) if e["event_type"] == "model_input_prepared")
    return diagnostic._fork(
        saved, cut["sequence"], output, "B", new_cap_usd=Decimal("4"),
        mode="offline-scripted-only", env_file=env_file,
        preserve_parent_configuration=True, **options,
    )


def test_reservation_reduces_only_tools_and_time_and_binds_fork(source, tmp_path):  # noqa: F811
    saved, _, _ = source
    journal = DevJournal(saved.root, saved.run_id)
    before = journal.path.read_bytes(), journal.envelope_path.read_bytes()
    old = journal.load_envelope()
    # The fixture's environment is already bound in its envelope; the resolver
    # normally returns the smoke package without the synthetic image declaration.
    task_dir, package = runner._resolve_task_file(saved.public_path)
    from patchloop.contracts import TaskEnvironment

    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64)})
    with patch.object(runner, "_resolve_task_file", lambda _: (task_dir, package)):
        baseline = fork(source, tmp_path / "baseline")
        reserved = fork(source, tmp_path / "reserved", reserved_tool_actions=1,
                        reserved_wall_seconds=35)
    assert reserved.request.limits == reserved.envelope.limits
    expected = old.limits.model_dump()
    expected.update(max_tool_actions=old.limits.max_tool_actions - 1,
                    wall_time_seconds=old.limits.wall_time_seconds - 35)
    assert reserved.request.limits.model_dump() == expected
    expected_budget = json.loads(json.dumps(baseline.remaining_budget))
    expected_budget["tool_actions"] -= 1
    expected_budget["active_wall_time_seconds"] -= 35
    expected_budget["total_active_wall_time_seconds"] -= 35
    assert reserved.remaining_budget == expected_budget
    assert reserved.request.evaluation_reserve_seconds == old.evaluation_reserve_seconds == 390
    assert reserved.active_elapsed_ms == baseline.active_elapsed_ms
    assert reserved.initial_spent_nanos == baseline.initial_spent_nanos
    assert reserved.ledger.cap_nanos == baseline.ledger.cap_nanos
    assert reserved.ledger.remaining_nanos == baseline.ledger.remaining_nanos == 4 * 10**9
    assert reserved.envelope.model_hash == baseline.envelope.model_hash
    assert reserved.request.max_output_tokens == baseline.request.max_output_tokens == 40000
    assert reserved.request.max_correction_output_tokens == 25000
    for branch in (baseline, reserved):
        marker = json.loads((branch.root / "fork.json").read_bytes())["marker"]
        assert sha256_json(marker) == branch.marker_hash
        if branch is reserved:
            assert marker["diagnostic_resource_reserve"] == {
                "tool_actions": 1, "wall_time_seconds": 35}
        else:
            assert "diagnostic_resource_reserve" not in marker
        assert branch.journal.events()[:branch.inherited_events] == (
            journal.events()[:branch.inherited_events])
    assert before == (journal.path.read_bytes(), journal.envelope_path.read_bytes())
    client = diagnostic.ScriptedClient([[{
        "name": "stop_task", "action_id": "reserved-preview-stop",
        "arguments": {"reason_code": "insufficient_public_evidence",
                      "summary": "Offline reserve delivery check."},
    }]])
    receipt = diagnostic.rehearse(reserved, client)
    assert receipt["result"]["terminal"] == "AGENT_STOPPED"
    assert receipt["synthetic_counts"] == receipt["synthetic_dispatches"] == 1
    assert receipt["provider_calls"] == 0 and receipt["synthetic_probe_calls"] == []
    delivered = json.loads(client.created[0]["input"][-1]["content"])["state"]["remaining_budget"]
    for key in ("model_calls", "tool_actions", "accepted_mutations", "evaluation_reserve_seconds"):
        assert delivered[key] == expected_budget[key]
    assert delivered["active_wall_time_seconds"] <= expected_budget["active_wall_time_seconds"]
    assert (delivered["total_active_wall_time_seconds"]
            <= expected_budget["total_active_wall_time_seconds"])


@pytest.mark.parametrize("options,match", [
    ({"reserved_tool_actions": True}, "nonnegative integers"),
    ({"reserved_wall_seconds": False}, "nonnegative integers"),
    ({"reserved_tool_actions": -1}, "nonnegative integers"),
    ({"reserved_wall_seconds": -1}, "nonnegative integers"),
    ({"reserved_tool_actions": 1.0}, "nonnegative integers"),
    ({"reserved_wall_seconds": "35"}, "nonnegative integers"),
    ({"reserved_tool_actions": 1}, "preserved parent"),
    ({"reserved_wall_seconds": 35}, "preserved parent"),
])
def test_invalid_reserve_rejected_before_source_access(tmp_path, options, match):
    output = tmp_path / "never-created"
    with pytest.raises(ContractError, match=match):
        diagnostic._fork(None, 1, output, "B", new_cap_usd=Decimal("1"),
                         mode="offline-scripted-only", env_file=tmp_path / "absent.env", **options)
    assert not output.exists()


@pytest.mark.parametrize("options", [
    {"reserved_tool_actions": 40}, {"reserved_wall_seconds": 2400},
])
def test_reserve_cannot_take_already_spent_allowance(source, tmp_path, options):  # noqa: F811
    with pytest.raises(ContractError, match="remaining resources"):
        fork(source, tmp_path / "rejected", **options)
