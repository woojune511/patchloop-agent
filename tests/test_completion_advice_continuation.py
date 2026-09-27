"""Exercise repeated delivery through real loop bookkeeping with a finite SDK."""
import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_deferred_scope_cue import correct_source as correct_source  # noqa: F401
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_continuation as continuation
from diagnostics import completion_advice_continuation as advice
from diagnostics import post_edit_budget_checkpoint as checkpoint
from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.segmented_input_audit import verify_turn
from patchloop.contracts import Artifact
from patchloop.util import canonical_json


@pytest.mark.parametrize("scenario", ["ready", "count", "segment", "edit"])
def test_continuous_advice_removal(correct_source, tmp_path, scenario):
    packet = checkpoint.prepare(correct_source, tmp_path / "packet", Decimal("3"))
    branch = continuation.restore(Path(packet["packet"]), packet["packet_hash"],
                                  tmp_path / "fork", "A")
    steps = [
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        [call("read_file", {"path": "mini_data_utils/csvlite.py", "start_line": 1,
                            "end_line": 90}, "inspect")]]
    if scenario == "edit":
        steps.append([call("replace_text", {
            "path": "mini_data_utils/csvlite.py",
            "old_text": "Parse CSV text into rows while preserving quoted values.",
            "new_text": "Parse CSV text into rows while preserving quoted fields.",
            "occurrence": 1, "causal_revision": None,
            "hypothesis": "Clarify the docstring without changing parsing.",
            "expected_behavior": "Parsing still preserves quoted fields."}, "mutate")])
        steps[-1][0]["action_id"] = "offline_second_mutation"
    client = continuation.ScriptedClient(
        [*steps, *stop_steps()], failure="count" if scenario == "count" else None)
    if scenario == "segment":
        original_count = client.responses.input_tokens.count

        def count(**request):
            client.input_tokens = 60_001 if len(client.counted) == 2 else 100
            return original_count(**request)

        client.responses.input_tokens.count = count
    result = advice.rehearse(branch, client)
    assert result["first_state_restored"]
    assert result["result"]["terminal"] == (
        "COUNT_TIMEOUT_OR_UNKNOWN" if scenario == "count" else "AGENT_STOPPED")
    events = branch.journal.events()
    reader = ForkStore(branch.root, events)
    markers = [e for e in events if e["event_type"] == "diagnostic_advice_removed"]
    assert len(markers) == {"count": 1, "ready": 3, "segment": 4, "edit": 4}[scenario]
    assert len(client.created) == {"count": 0, "ready": 3, "segment": 3, "edit": 4}[scenario]
    for marker, counted in zip(markers, client.counted, strict=True):
        p = marker["payload"]
        baseline = json.loads(reader.read_bytes(Artifact.model_validate(p["baseline_request"])))
        normalized = copy.deepcopy(counted)
        normalized.pop("timeout", None)
        view = json.loads(normalized["input"][-1]["content"])
        assert view["state"]["completion_guidance"]["next_action"] is None
        view["state"]["completion_guidance"] = json.loads(
            baseline["input"][-1]["content"])["state"]["completion_guidance"]
        normalized["input"][-1]["content"] = canonical_json(view)
        assert normalized == {k: baseline[k] for k in normalized}
        count = next(e for e in events if e["event_type"] == "input_count_started"
                     and e["payload"]["turn_id"] == p["boundary_id"])
        assert marker["sequence"] < count["sequence"]
    if scenario == "edit":
        state = json.loads(client.created[-1]["input"][-1]["content"])["state"]
        assert state["completion_guidance"]["stage"] == "needs_visible_checks"
        assert not state["completion_guidance"]["submission_ready"]
    if scenario == "segment":
        assert any(e["event_type"] == "context_segment_started"
                   and "input_tokens" in canonical_json(e["payload"])
                   for e in events[branch.inherited_events:])
    for request, turn in zip(client.created, [e for e in events
            if e["sequence"] > branch.inherited_events and e["event_type"] == "turn_started"],
            strict=True):
        assert verify_turn(turn, events, reader, actual_input=request["input"])["verified"]
