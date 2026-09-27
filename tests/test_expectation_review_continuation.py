"""Matched later-checkpoint restoration with synthetic probe evidence."""
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_deferred_scope_cue import correct_source as correct_source  # noqa: F401
from test_dev_probes import FakeProbe
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_continuation as c
from diagnostics import completion_advice_continuation as advice
from diagnostics import expectation_review_checkpoint as review
from diagnostics import expectation_review_continuation as continuation
from diagnostics import post_edit_budget_checkpoint as budget
from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.declaration_checkpoint import Source
from diagnostics.segmented_input_audit import verify_turn
from patchloop.util import sha256_bytes


@pytest.fixture(scope="module")
def packet(correct_source, tmp_path_factory):
    root = tmp_path_factory.mktemp("review-source")
    prep = budget.prepare(correct_source, root / "budget", Decimal("3"))
    branch = c.restore(Path(prep["packet"]), prep["packet_hash"], root / "source", "A")
    probe = call("run_probe", {"question": "Synthetic observation", "python_source": "print(1)"},
                 "verify")
    probe["action_id"] = "offline_review_source_probe"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(c.UnexecutedProbe, "run_probe", lambda self, *a, **kw:
                   FakeProbe(status="passed").run_probe(*a, **kw))
        result = advice.rehearse(branch, c.ScriptedClient([[probe], *stop_steps()]))
    assert result["result"]["terminal"] == "AGENT_STOPPED"
    events = branch.journal.events()
    turn = [e for e in events if e["event_type"] == "turn_started"
            and e["sequence"] > branch.inherited_events][-1]
    source = Source(branch.root, branch.journal.run_id,
        sha256_bytes(branch.journal.path.read_bytes()),
        sha256_bytes(branch.journal.envelope_path.read_bytes()),
        correct_source.public_path, correct_source.public_hash)
    return review.prepare(source, turn["payload"]["turn_id"], root / "packet")


@pytest.mark.parametrize("arm,failure", [("A", None), ("B", None), ("B", "count"),
                                       ("B", "segment")])
def test_later_boundary(packet, tmp_path, arm, failure):
    branch = c.restore(Path(packet["packet"]), packet["packet_hash"], tmp_path / arm, arm)
    client = c.ScriptedClient([[call("read_file", {"path": "mini_data_utils/csvlite.py",
        "start_line": 1, "end_line": 90}, "inspect")], *stop_steps()],
        failure="count" if failure == "count" else None)
    if failure == "segment":
        original_count = client.responses.input_tokens.count

        def count(**request):
            client.input_tokens = 60_001 if not client.counted else 100
            return original_count(**request)

        client.responses.input_tokens.count = count
    result = continuation.rehearse(branch, client)
    assert result["first_state_restored"]
    assert result["result"]["terminal"] == (
        "COUNT_TIMEOUT_OR_UNKNOWN" if failure == "count" else
        "LIMIT_REACHED" if failure == "segment" else "AGENT_STOPPED")
    assert len(client.created) == (0 if failure else 2)
    first = client.counted[0]
    assert (review.FIELD in json.loads(first["input"][-1]["content"])["state"]) == (arm == "B")
    if not failure:
        assert {k: v for k, v in client.created[0].items() if k != "timeout"} == branch.selected
        state = json.loads(client.created[1]["input"][-1]["content"])["state"]
        assert review.FIELD not in state
        assert state["completion_guidance"]["next_action"] is None
    events = branch.journal.events()
    turns = [e for e in events if e["event_type"] == "turn_started"
             and e["sequence"] > branch.inherited_events]
    for turn, request in zip(turns, client.created, strict=True):
        assert verify_turn(turn, events, ForkStore(branch.root, events),
                           actual_input=request["input"])["verified"]
    assert not any(e["event_type"] == "action_started" and e["payload"]["tool"] == "run_probe"
                   for e in events[branch.inherited_events:])
