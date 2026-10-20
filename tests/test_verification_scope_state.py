"""Small receipt replays: case evidence is not model discussion or task acceptance."""

import copy

from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.evidence_focus import project_interpretations
from patchloop.dev.reproduction import review


def observation(action="baseline", *, case="case", diff="D1", matched=False, value=1):
    return {"event_type": "action_finished", "payload": {"result": {
        "action_id": action, "tool": "run_probe", "status": "succeeded",
        "workspace_diff_hash": diff, "output": {"source_hash": "program", "reproduction": {
            "binding": {"case_id": case, "root_action_id": "baseline",
                        "definition": {"requirement_quote": "public requirement"}},
            "comparison": "matched" if matched else "mismatched", "reason": None,
            "call_observation": {"incomplete": False, "calls": [{
                "entrypoint": "package.run", "arguments": {"value": value},
                "cwd": "/tmp/case", "sys_path": ["/tmp/case"],
            }]},
        }},
    }}}


def unbound(action="helper", tool="run_probe", *, diff="D1"):
    return {"event_type": "action_finished", "payload": {"result": {
        "action_id": action, "tool": tool, "status": "succeeded", "workspace_diff_hash": diff,
        "output": {"source_hash": "helper-program", "exit_code": 0, "passed": True,
                   "question": "Does the internal helper work?",
                   "stdout": "original failure remains"},
    }}}


def test_zero_exit_unbound_output_and_suite_pass_do_not_create_verified_requirements():
    events = [unbound(), unbound("suite", "run_check")]
    before = copy.deepcopy(events)
    state = review(events, "D1")
    assert state["required"]["status"] == "UNKNOWN"
    assert state["required"]["reason"] == "no_bound_reproduction"
    assert not state["items"] and state["helper_or_unbound_executions"] == 1
    assert [r["scope"] for r in state["other_executions"]] == [
        "helper_or_unbound_diagnostic", "registered_check"]
    assert all(r["requirement_coverage"] == "not_assessed" for r in state["other_executions"])
    assert events == before


def test_same_snapshot_conflict_survives_later_success_and_unrelated_checks():
    events = [observation(), observation("again", matched=True), unbound("suite", "run_check")]
    state = review(events, "D1")
    case = state["items"][0]
    assert case["evidence"]["status"] == "CONFLICT"
    assert case["comparison_status"] == "conflicting_current_observations"
    assert case["evidence"]["evidence_action_ids"] == ["baseline", "again"]
    # A new code snapshot can resolve this experiment; the old failure stays in history.
    repaired = review([*events, observation("repaired", diff="D2", matched=True)], "D2")
    assert repaired["items"][0]["evidence"]["status"] == "SUPPORTED"
    assert repaired["required"]["status"] == "UNKNOWN"
    assert review(events, "D2")["items"][0]["evidence"]["status"] == "UNKNOWN"


def test_changed_observed_setup_cannot_erase_current_counterexample():
    events = [observation(), observation("different-input", matched=True, value=2)]
    case = review(events, "D1")["items"][0]
    assert case["comparison_status"] == "observed_call_or_setup_changed"
    assert case["evidence"]["status"] == "REFUTED"
    assert case["evidence"]["evidence_action_ids"] == ["baseline"]
    later = review([observation(), observation("changed", diff="D2", matched=True, value=2)], "D2")
    assert later["items"][0]["evidence"]["status"] == "UNKNOWN"


def test_model_dismissal_and_plan_changes_do_not_change_required_scope_across_handoff():
    computed = review([observation()], "D1")
    view = {"public_task": {"issue": {"title": "original purpose"}},
            "current_diff": {"patch_hash": "D1"}, "working_plan": {"text": "A different plan"},
            "reproduction_review": computed, "working_notes": {"verification": {
                "unresolved_ids": [], "items": [{
                    "concern_id": "v1", "status": "dismissed", "statement": "Original failure?",
                    "decision": {"outcome": "dismissed", "reason": "Still unresolved."},
                }],
            }}}
    before = copy.deepcopy(computed)
    project_interpretations(view, [])
    notes = view["working_notes"]["verification"]
    assert notes["model_open_concern_ids"] == [] and "unresolved_ids" not in notes
    assert notes["items"][0]["model_position"] == "dismissed_by_model"
    assert notes["items"][0]["behavior_coverage"] == "not_assessed"
    assert "status" not in notes["items"][0]
    wire = assemble_model_input(system_prompt="fixed", state=view, history=[],
                                context_policy="segmented-v1")
    restored = reconstruct_state(wire, context_policy="segmented-v1")
    assert restored["reproduction_review"] == before
    project_interpretations(restored, [])
    assert restored["working_notes"]["verification"] == notes
    assert computed["required"]["status"] == "UNKNOWN"
    assert computed["items"][0]["evidence"]["status"] == "REFUTED"


def test_bounded_view_prioritizes_counterevidence_and_counts_every_case():
    events = [observation(case=f"case-{n}", matched=True) for n in range(4)]
    events += [observation(case="failure"), observation(case="conflict"),
               observation("second", case="conflict", matched=True)]
    state = review(events, "D1")
    assert len(state["items"]) == 3 and state["omitted_count"] == 3
    assert [r["case_id"] for r in state["items"][:2]] == ["conflict", "failure"]
    assert state["case_status_counts"] == {
        "CONFLICT": 1, "REFUTED": 1, "UNKNOWN": 0, "SUPPORTED": 4}
