"""Mutation feedback references only position-proven, previously delivered source."""

from __future__ import annotations

import copy
import json

import pytest
from native_history_support import input_context, start_turn
from test_dev_completion_v27 import _batch
from test_dev_feedback_integration_v18 import _context, _input, _outputs
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _restart

from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.native_sources import project_mutation_result, reference_native_sources
from patchloop.util import canonical_json, sha256_bytes


def _span(start=1, count=40, *, file_hash="before", path="src.py"):
    return {"path": path, "file_hash": file_hash, "start_line": start,
            "end_line": start + count - 1,
            "content": "\n".join(f"line_{n} = '{'x' * 80}'" for n in range(start, start + count))}


def _native(result):
    return {"type": "function_call_output", "call_id": result["action_id"],
            "output": canonical_json(result)}


def _read_result(span, action_id="read"):
    return {"action_id": action_id, "tool": "read_file", "status": "succeeded",
            "output": {"spans": [span]}}


def _case(*, source=None, anchor=50, old="old", new="new", shift=0):
    source = _span() if source is None else source
    rebound = {**source, "start_line": source["start_line"] + shift,
               "end_line": source["end_line"] + shift, "file_hash": "after",
               "source_diff_hash": "candidate", "origin": "revalidated_after_mutation"}
    result = {"action_id": "edit", "input_hash": "input", "tool": "replace_text",
              "status": "succeeded", "workspace_diff_hash": "candidate", "output": {
                  "worktree_diff_hash": "candidate", "revalidated_spans": [rebound],
                  "alternative_requirement_satisfied": False,
                  "changed_hunk": "EXACT_PUBLIC_CHANGE", "mutation_evidence": {
                      **_span(anchor, 1, file_hash="after"), "content": new,
                      "end_line": anchor + new.count("\n"),
                  },
              }}
    admission = {"tool": "replace_text", "action_id": "edit", "input_hash": "input",
                 "mutation_admitted": True, "mutation_expected_worktree_diff_hash": "candidate",
                 "mutation_preimage_file_hash": "before",
                 "mutation_expected_postimage_file_hash": "after",
                 "mutation_anchor_start_line": anchor,
                 "arguments": {"path": "src.py", "old_text": old, "new_text": new}}
    return result, admission, [_native(_read_result(source))]


def _project(result, admission, history):
    return project_mutation_result(result, admission=admission, history=history)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("old,new,source_start,shift", [
    ("old", "new", 1, 0),       # source before the replacement
    ("old", "new\nextra", 60, 1),
    ("old\n", "", 60, -1),
    ("old\nsecond", "new", 60, -1),
])
def test_exact_position_references_preserve_mutation_feedback(
    newline, old, new, source_start, shift,
):
    source = _span(source_start)
    source["content"] = source["content"].replace("\n", newline)
    result, admission, history = _case(source=source, old=old, new=new, shift=shift)
    before = copy.deepcopy((result, admission, history))
    projected = _project(result, admission, history)
    alias = projected["output"]["revalidated_spans"][0]
    assert "content" not in alias
    assert alias["content_delivery"] == [{
        "action_id": "read", "field": "output.spans[0]", "file_hash": "before",
        "start_line": source_start, "end_line": source_start + 39,
        "target_start_line": source_start + shift,
    }]
    assert alias["file_hash"] == "after"
    assert alias["content_hash"] == sha256_bytes(source["content"].replace("\r\n", "\n").encode())
    assert projected["output"]["mutation_evidence"] == result["output"]["mutation_evidence"]
    assert projected["output"]["changed_hunk"] == "EXACT_PUBLIC_CHANGE"
    assert "alternative_requirement_satisfied" not in projected["output"]
    assert len(canonical_json(projected).encode()) < len(canonical_json(result).encode()) - 2500
    assert (result, admission, history) == before
    state = {"source_spans": result["output"]["revalidated_spans"]}
    referenced = reference_native_sources(state, [*history, _native(projected)])
    assert referenced["source_spans"][0]["content_delivery"][0]["action_id"] == "edit"
    assert "content" not in referenced["source_spans"][0]
    # Prior delivery alone never upgrades the old source hash to the new file identity.
    assert reference_native_sources(state, history) == state


@pytest.mark.parametrize("key,value", [
    ("tool", "read_file"), ("mutation_admitted", False), ("action_id", "other"),
    ("input_hash", "other"), ("mutation_expected_worktree_diff_hash", "other"),
    ("mutation_expected_postimage_file_hash", "other"),
    ("mutation_preimage_file_hash", "other"), ("mutation_anchor_start_line", None),
])
def test_missing_or_mismatched_admission_keeps_whole_body(key, value):
    result, admission, history = _case()
    admission[key] = value
    assert _project(result, admission, history)["output"]["revalidated_spans"] == (
        result["output"]["revalidated_spans"]
    )


@pytest.mark.parametrize("change", ["gap", "conflict", "wrong_position", "wrong_path",
                                        "truncated", "missing", "wrong_action", "failed"])
def test_similar_text_or_incomplete_native_delivery_is_not_rebinding_proof(change):
    result, admission, history = _case()
    prior = json.loads(history[0]["output"])
    span = prior["output"]["spans"][0]
    if change == "gap":
        prior["output"]["spans"] = [_span(1, 20), _span(22, 19)]
    elif change == "conflict":
        conflict = _span()
        conflict["content"] = conflict["content"].replace("line_1", "different_1")
        history.append(_native(_read_result(conflict, "conflicting-read")))
    elif change == "wrong_position":
        span["start_line"] += 1
        span["end_line"] += 1
    elif change == "wrong_path":
        span["path"] = "helper.py"
    elif change == "truncated":
        span["content"] = span["content"].split("\n")[0]
    elif change == "missing":
        prior["output"]["spans"] = []
    elif change == "wrong_action":
        prior["action_id"] = "other"
    elif change == "failed":
        prior["status"] = "failed"
    history[0]["output"] = canonical_json(prior)
    assert _project(result, admission, history)["output"]["revalidated_spans"] == (
        result["output"]["revalidated_spans"]
    )


def test_adjacent_sources_merge_but_fragment_and_byte_limits_keep_inline_fallback():
    result, admission, _ = _case()
    history = [_native(_read_result(_span(1, 20), "a")),
               _native(_read_result(_span(21, 20), "b"))]
    projected = _project(result, admission, history)
    refs = projected["output"]["revalidated_spans"][0]["content_delivery"]
    assert [(ref["action_id"], ref["start_line"], ref["end_line"]) for ref in refs] == [
        ("a", 1, 20), ("b", 21, 40),
    ]
    fragmented = [_native(_read_result(_span(n, 1), f"r{n}")) for n in range(1, 41)]
    assert "content" in _project(result, admission, fragmented)["output"]["revalidated_spans"][0]
    tiny, admission, history = _case(source=_span(1, 1))
    assert "content" in _project(tiny, admission, history)["output"]["revalidated_spans"][0]


def test_deletion_union_keeps_exact_separate_preimage_coordinates():
    result, admission, history = _case(source=_span(1, 80), anchor=40, old="deleted\n", new="")
    target = result["output"]["revalidated_spans"][0]
    lines = target["content"].split("\n")
    target["content"] = "\n".join(lines[:39] + lines[40:])
    target["end_line"] = 79
    projected = _project(result, admission, history)
    refs = projected["output"]["revalidated_spans"][0]["content_delivery"]
    assert [(r["start_line"], r["end_line"], r["target_start_line"]) for r in refs] == [
        (1, 39, 1), (41, 80, 40),
    ]


@pytest.mark.parametrize("change", [None, "body_hash", "source_hash", "range", "target",
                                    "self", "forward"])
def test_alias_chain_is_backward_only_complete_and_hash_verified(change):
    result, admission, history = _case()
    first = _project(result, admission, history)
    alias = first["output"]["revalidated_spans"][0]
    ref = alias["content_delivery"][0]
    if change == "body_hash":
        alias["content_hash"] = "wrong"
    elif change == "source_hash":
        ref["file_hash"] = "wrong"
    elif change == "range":
        ref["end_line"] -= 1
    elif change == "target":
        ref["target_start_line"] += 1
    elif change == "self":
        ref["action_id"] = "edit"
        ref["field"] = "output.revalidated_spans[0]"
        ref["file_hash"] = "after"
    chain = [*history, _native(first)]
    if change == "forward":
        chain.reverse()
    second, admitted, _ = _case()
    second["action_id"] = admitted["action_id"] = "edit-two"
    admitted["mutation_preimage_file_hash"] = "after"
    admitted["mutation_expected_postimage_file_hash"] = "third"
    second["output"]["revalidated_spans"][0]["file_hash"] = "third"
    final = _project(second, admitted, chain)
    span = final["output"]["revalidated_spans"][0]
    if change is not None:
        assert "content" in span
        return
    assert span["content_delivery"][0]["action_id"] == "edit"
    state = {"source_spans": second["output"]["revalidated_spans"]}
    view = reference_native_sources(state, [*chain, _native(final)])
    assert view["source_spans"][0]["content_delivery"][0]["action_id"] == "edit-two"
    assert reference_native_sources(view, [*chain, _native(final)]) == view


def test_rejection_and_canonical_feedback_keep_raw_details_without_legacy_flag():
    result, admission, history = _case()
    admission["private_unused_sentinel"] = "NEVER_PROJECT_THIS"
    projected = _project(result, admission, history)
    assert "NEVER_PROJECT_THIS" not in canonical_json(projected)
    result["status"] = "failed"
    result["output"]["mutation_failure"] = {"class": "scope_violation", "rolled_back": True}
    public = project_mutation_result(result)
    expected = copy.deepcopy(result)
    del expected["output"]["alternative_requirement_satisfied"]
    assert public == expected
    assert result["output"]["alternative_requirement_satisfied"] is False


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_real_mutations_native_history_and_restart_keep_full_gateway_evidence(tmp_path, newline):
    gateway = _gateway(tmp_path, newline=newline)
    read = RequestedTool(
        name="read_file", action_id="observed", arguments={
            "path": "src.py", "start_line": 1, "end_line": 50,
        }, turn_decision=PublicTurnDecision(
            mode="inspect", basis="Observe the public file.",
            evidence_goal="Locate the editable value.",
        ),
    )
    _batch(gateway, read, tmp_path)
    last_input = None
    for index in range(1, 4):
        call = _mutation(f"edit-{index}", f"editable = {index - 1}", f"editable = {index}")
        result = _batch(gateway, call, tmp_path)
        context = _context(gateway, [result])
        canonical_result = json.loads(context)["latest_tool_results"][0]
        assert "alternative_requirement_satisfied" not in canonical_result["output"]
        assert all("content" in span for span in canonical_result["output"]["revalidated_spans"])
        items = _input(gateway, [result], tmp_path, context=context)
        native = _outputs(items)[call.action_id]
        assert "alternative_requirement_satisfied" not in native["output"]
        assert "content_delivery" in native["output"]["revalidated_spans"][0]
        assert native["output"]["mutation_evidence"] == result.output["mutation_evidence"]
        assert result.output["alternative_requirement_satisfied"] is False
        assert all("content" in span for span in result.output["revalidated_spans"])
        assert input_context(items)["mutation_readiness"]["state"] == "ready_to_attempt"
        if last_input is not None:
            assert items[:len(last_input)] == last_input
        last_input = items
        saved = gateway.journal.path.read_bytes(), (gateway.workspace / "src.py").read_bytes()
        gateway = _restart(gateway)
        assert _input(gateway, [result], tmp_path, context=context) == items
        assert gateway.execute(call).replayed
        assert gateway.accepted_mutations == index
        assert gateway.journal.path.read_bytes() == saved[0]
        assert (gateway.workspace / "src.py").read_bytes() == saved[1]


def test_completed_mutation_before_batch_crash_can_replay_then_project_once(tmp_path):
    gateway = _gateway(tmp_path)
    call = RequestedTool(name="read_file", action_id="read", arguments={
        "path": "src.py", "start_line": 1, "end_line": 50,
    }, turn_decision=PublicTurnDecision(
        mode="inspect", basis="Observe the public file.",
        evidence_goal="Locate the editable value.",
    ))
    _batch(gateway, call, tmp_path)
    before = _input(gateway, gateway.journal.latest_tool_batch_results(), tmp_path)
    turn_id = "pending-edit"
    start_turn(gateway.journal, ArtifactStore(tmp_path / "artifacts"), turn_id,
               context=_context(gateway, gateway.journal.latest_tool_batch_results()))
    edit = _mutation("pending")
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [edit.model_dump(mode="json")],
    })
    result = gateway.execute(edit)
    assert result.status == "succeeded"
    restarted = _restart(gateway)
    replay = restarted.execute(edit)
    assert replay.replayed and restarted.accepted_mutations == 1
    restarted.journal.append("tool_batch_finished", {
        "turn_id": turn_id, "action_ids": [edit.action_id],
    })
    items = _input(restarted, [result], tmp_path)
    assert items[:len(before)] == before
    assert list(_outputs(items)) == ["read", "pending"]
    assert "content_delivery" in _outputs(items)["pending"]["output"]["revalidated_spans"][0]
    assert _input(_restart(restarted), [result], tmp_path) == items
