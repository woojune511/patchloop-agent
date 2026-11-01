"""Rejected verification proposals survive recovery without acquiring authority."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_dev_context_v12 import source_gateway as source_gateway

from patchloop.artifacts import ArtifactStore
from patchloop.dev import completion_context, repair_context, runner, segments
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.mutation_proposals import rejected_test_proposal

ORACLE = (
    "def test_public_output(capsys):\n"
    "    run_public_caller(original_input)\n"
    "    assert capsys.readouterr().out.count('observed-message') == 1\n"
)


def edit(path="tests/test_output.py", *, old=None, new=ORACLE):
    return {"path": path, "old_text": old, "new_text": new, "occurrence": 1}


def mutation_events(
    edits=None, *, action="rejected", tool="edit_files", status="failed",
    rolled_back=True, baseline="base", candidate="base",
):
    selected = edits if edits is not None else [edit()]
    args = {"hypothesis": "The public caller emits duplicate messages.",
            "expected_behavior": "The same original caller emits exactly one message."}
    if tool == "edit_files":
        args.update(edits=selected, undo_action_id=None)
    else:
        args.update(selected[0])
    identity = {"action_id": action, "input_hash": f"hash-{action}", "tool": tool}
    return [
        {"event_type": "action_started", "sequence": 1, "payload": {
            **identity, "arguments": args, "baseline_diff_hash": baseline,
        }},
        {"event_type": "action_finished", "sequence": 2, "payload": {
            "action_id": action, "input_hash": identity["input_hash"], "result": {
                **identity, "status": status, "workspace_diff_hash": candidate,
                "error_code": "CONTRACT_ERROR" if status == "failed" else None,
                "message": "Existing shared imports must remain unchanged.",
                "output": {"mutation_failure": {"rolled_back": rolled_back}},
            },
        }},
    ]


def joined(*groups):
    events = copy.deepcopy([event for group in groups for event in group])
    for sequence, event in enumerate(events, 1):
        event["sequence"] = sequence
    return events


def project(events, *, roots=("tests",), current="after-source"):
    return rejected_test_proposal(events, roots=roots, diff_hash=current)


def test_source_only_recovery_preserves_exact_unexecuted_oracle_and_intent():
    rejected = mutation_events([edit("src/logging.py", old="before", new="after"), edit()])
    accepted = mutation_events(
        [edit("src/logging.py", old="before", new="after")], action="source-repair",
        status="succeeded", rolled_back=False, candidate="after-source",
    )
    events = joined(rejected, accepted)
    before = copy.deepcopy(events)
    proposal = project(events)
    assert proposal["action_id"] == "rejected"
    assert proposal["input_hash"] == "hash-rejected"
    assert proposal["baseline_diff_hash"] == "base"
    assert proposal["current_diff_hash"] == "after-source"
    assert proposal["proposal_status"] == "rejected_not_applied"
    assert proposal["interpretation_status"] == "model_authored_unverified"
    assert proposal["error_code"] == "CONTRACT_ERROR"
    assert proposal["error_message"] == "Existing shared imports must remain unchanged."
    assert proposal["expected_behavior"] == rejected[0]["payload"]["arguments"]["expected_behavior"]
    assert proposal["hypothesis"] == rejected[0]["payload"]["arguments"]["hypothesis"]
    assert proposal["edits"] == [{"path": "tests/test_output.py", "old_text": None,
                                  "new_text": ORACLE, "old_text_omitted_chars": 0,
                                  "new_text_omitted_chars": 0}]
    assert proposal["omitted_edit_count"] == 0
    assert "before" not in json.dumps(proposal)
    assert events == before


@pytest.mark.parametrize("tool", ["edit_files", "replace_text"])
def test_each_mutation_tool_retains_the_proposed_test_old_and_new_text(tool):
    proposal = project(mutation_events([edit(old="old assertion\n")], tool=tool))
    assert proposal["edits"][0]["old_text"] == "old assertion\n"
    assert proposal["edits"][0]["new_text"] == ORACLE


@pytest.mark.parametrize("defect", [
    "pending", "succeeded", "not_rolled_back", "missing_failure", "null_failure",
    "wrong_action_id", "wrong_input_hash", "wrong_tool", "finish_without_start",
])
def test_unmatched_or_nonrolledback_results_cannot_create_a_rejected_proposal(defect):
    events = mutation_events()
    result = events[1]["payload"]["result"]
    if defect == "pending":
        events.pop()
    elif defect == "succeeded":
        result["status"] = "succeeded"
    elif defect == "not_rolled_back":
        result["output"]["mutation_failure"]["rolled_back"] = False
    elif defect == "missing_failure":
        result["output"] = {}
    elif defect == "null_failure":
        result["output"]["mutation_failure"] = None
    elif defect == "finish_without_start":
        events.pop(0)
    elif defect == "wrong_tool":
        result["tool"] = "replace_text"
    else:
        result[{"wrong_action_id": "action_id", "wrong_input_hash": "input_hash",
                }[defect]] = "different"
    assert project(events) is None


def test_malformed_edits_cannot_create_or_replace_a_rejected_test_proposal():
    malformed = mutation_events(action="malformed")
    malformed[0]["payload"]["arguments"]["edits"] = 123
    assert project(malformed) is None
    assert project(joined(mutation_events(), malformed))["action_id"] == "rejected"


@pytest.mark.parametrize("hypothesis,expected_behavior", [
    (123, {"outcome": "untrusted shape"}),
    (["untrusted shape"], False),
])
def test_nonstring_intent_is_null_without_losing_valid_proposed_test_text(
    hypothesis, expected_behavior,
):
    events = mutation_events()
    arguments = events[0]["payload"]["arguments"]
    arguments.update(hypothesis=hypothesis, expected_behavior=expected_behavior)
    before = copy.deepcopy(events)
    proposal = project(events)
    assert proposal["hypothesis"] is None
    assert proposal["expected_behavior"] is None
    assert proposal["edits"][0]["new_text"] == ORACLE
    assert proposal["proposal_status"] == "rejected_not_applied"
    assert proposal["interpretation_status"] == "model_authored_unverified"
    assert events == before


@pytest.mark.parametrize("path", [
    "src/test_output.py", "tests_other/test_output.py", "tests.py",
    "tests/../src/test_output.py", "/tests/test_output.py",
])
def test_root_filter_uses_declared_path_boundary_not_test_filename(path):
    assert project(mutation_events([edit(path)])) is None
    assert project(mutation_events(), roots=()) is None


def test_declared_nonstandard_root_and_yaml_are_retained_as_unapplied_text():
    proposal = project(mutation_events([edit("checks/fixtures/case.yml", new="case: input\n")]),
                       roots=("checks",))
    assert proposal["edits"][0]["path"] == "checks/fixtures/case.yml"
    assert proposal["edits"][0]["new_text"] == "case: input\n"
    assert proposal["proposal_status"] == "rejected_not_applied"


def test_newer_qualifying_rejection_replaces_old_but_unrelated_failure_does_not():
    first = mutation_events()
    unrelated = mutation_events([edit("src/other.py")], action="unrelated")
    assert project(joined(first, unrelated))["action_id"] == "rejected"
    latest = mutation_events([edit("tests/test_other.py", new="other oracle")], action="latest")
    assert project(joined(first, latest, unrelated))["action_id"] == "latest"


def test_weaker_accepted_test_or_successful_check_does_not_resolve_rejected_oracle():
    weaker = mutation_events([edit(new="def test_state(): assert state.enabled\n")],
                             action="weaker-test", status="succeeded", rolled_back=False)
    passed = [{"event_type": "action_finished", "payload": {"result": {
        "tool": "run_check", "action_id": "check", "status": "succeeded",
        "output": {"passed": True}, "workspace_diff_hash": "after-source",
    }}}]
    events = joined(mutation_events(), weaker, passed)
    assert project(events)["edits"][0]["new_text"] == ORACLE
    assert project(events)["proposal_status"] == "rejected_not_applied"


def test_excerpts_are_exact_bounded_and_report_omissions_without_changing_events():
    edits = [edit(f"tests/case_{n}.py", old="o" * 5000, new=f"{n}" * 5000)
             for n in range(6)]
    events = mutation_events(edits)
    before = copy.deepcopy(events)
    proposal = project(events)
    assert len(proposal["edits"]) <= 4
    assert proposal["omitted_edit_count"] == len(edits) - len(proposal["edits"])
    assert sum(len(e.get(field) or "") for e in proposal["edits"]
               for field in ("old_text", "new_text")) <= 8000
    for excerpt in proposal["edits"]:
        original = next(e for e in edits if e["path"] == excerpt["path"])
        for field in ("old_text", "new_text"):
            assert original[field].startswith(excerpt[field])
            assert excerpt[f"{field}_omitted_chars"] == len(original[field]) - len(excerpt[field])
    assert proposal["edits"][0]["new_text"] == edits[0]["new_text"]
    assert proposal == project(events)
    assert events == before


def test_context_and_fresh_stage_projections_keep_proposal_without_changing_gate(
    source_gateway, tmp_path,
):
    gateway = source_gateway[0]
    gateway.public_task.constraints.additive_test_roots = ["tests"]
    current = gateway.current_diff_hash
    events = joined(mutation_events(), mutation_events(
        [edit("src.py", old="first", new="changed")], action="accepted-source",
        status="succeeded", rolled_back=False, candidate=current,
    ))
    for event in events:
        gateway.journal.append(event["event_type"], event["payload"])
    gateway.last_failed_mutation = {"action_id": "rejected"}
    gateway._accept_successful_mutation({"changed_files": [], "mutation": {
        "diff_hash": current, "changed_files": ["src.py"],
        "hypothesis": "Source implementation changes.", "expected_behavior": "Caller emits once.",
    }}, refresh_notes=False)
    assert gateway.last_failed_mutation is None
    kwargs = dict(package=SimpleNamespace(public=gateway.public_task), gateway=gateway,
                  journal=gateway.journal, correction=None, latest_tool_results=[],
                  counters=runner._RunCounters(), elapsed_seconds=0, limits=gateway.limits)
    state = json.loads(runner._build_context(**kwargs))
    proposal = state["last_rejected_test_proposal"]
    assert proposal["edits"][0]["new_text"] == ORACLE
    for stage in (lambda value: value, repair_context.project, completion_context.project):
        view = compact_model_state(stage(copy.deepcopy(state)), history=[])
        assert view["last_rejected_test_proposal"] == proposal
        assert view["workflow_gate"] == state["workflow_gate"]
        assert view["available_tool_names"] == state["available_tool_names"]
        assert view["completion_guidance"] == state["completion_guidance"]
    # The old rejected call is deliberately absent from the new native stream.
    # A durable fresh handoff must carry the bounded record as historical data.
    with gateway.journal.execution_lock():
        items = runner._build_segmented_model_input(
            journal=gateway.journal, store=ArtifactStore(tmp_path / "artifacts"),
            context=json.dumps(state), latest_results=[], planning_policy="none",
            force_reason="input_tokens",
        )
    fresh = reconstruct_state(items, context_policy=segments.POLICY)
    assert fresh["last_rejected_test_proposal"] == proposal
    assert fresh["workflow_gate"] == state["workflow_gate"]
    assert fresh["segment_handoff"]["previous_reasoning_available"] is False
    assert not any(item.get("type") == "function_call" for item in items)
    assert state["last_failed_mutation"] is None
