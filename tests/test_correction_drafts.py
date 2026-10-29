"""Rejected proposals survive correction without becoming executable evidence."""

from __future__ import annotations

import copy
import json

from patchloop.dev import correction_drafts
from patchloop.dev.contracts import RequestedTool
from patchloop.util import canonical_json, sha256_json

DIFF = "sha256:" + "a" * 64


def edit(action_id="edit-1", **changes):
    arguments = {
        "path": "package/source.py", "old_text": "return old\n", "new_text": "return new\n",
        "hypothesis": "Preserve the correct namespace.", "expected_behavior": "Use the caller.",
    }
    arguments.update(changes)
    return RequestedTool(name="replace_text", action_id=action_id, arguments=arguments)


def file_edit(action_id="files-1", *, undo=None, new_text="VALUE = '수정'\n"):
    return RequestedTool(name="edit_files", action_id=action_id, arguments={
        "edits": None if undo else [{"path": "package/helper.py", "old_text": None,
                                     "new_text": new_text, "occurrence": 1}],
        "undo_action_id": undo, "hypothesis": "Keep the related file change recoverable.",
        "expected_behavior": "Preserve unrelated source and original tests.",
    })


def test_create_and_undo_drafts_preserve_exact_shapes_and_withhold_stale_bodies():
    calls = [file_edit(), file_edit("undo-draft", undo="accepted-files")]
    before = [call.model_dump(mode="json") for call in calls]
    packet = correction_drafts.build(calls, turn_id="files-turn", diff_hash=DIFF)
    assert packet["candidate_count"] == 2 and packet["omitted"] == {}
    assert packet["execution_status"] == "not_executed"
    for call, draft in zip(calls, packet["drafts"], strict=True):
        assert draft["tool"] == "edit_files" and draft["arguments"] == call.arguments
        assert draft["arguments_hash"] == sha256_json(call.arguments)
        assert draft["input_hash"] == sha256_json({"tool": call.name, "arguments": call.arguments})
    assert packet["drafts"][0]["arguments"]["undo_action_id"] is None
    assert packet["drafts"][0]["arguments"]["edits"][0]["old_text"] is None
    assert packet["drafts"][1]["arguments"]["edits"] is None
    current = correction_drafts.project(packet, diff_hash=DIFF)
    current["drafts"][0]["arguments"]["edits"][0]["new_text"] = "local"
    assert packet["drafts"][0]["arguments"] == calls[0].arguments
    stale = correction_drafts.project(packet, diff_hash="sha256:" + "b" * 64)
    assert stale["status"] == "stale" and stale["retained_argument_utf8_bytes"] == 0
    assert stale["omitted"] == {"stale_diff": 2}
    assert all("arguments" not in draft and draft["body_status"] == "omitted_stale_diff"
               for draft in stale["drafts"])
    assert [call.model_dump(mode="json") for call in calls] == before


def test_mixed_mutation_drafts_share_the_same_two_draft_limit():
    calls = [edit(), file_edit(), file_edit("undo-draft", undo="accepted-files")]
    packet = correction_drafts.build(calls, turn_id="mixed-turn", diff_hash=DIFF)
    assert packet["candidate_count"] == 3 and len(packet["drafts"]) == 2
    assert [draft["tool"] for draft in packet["drafts"]] == ["replace_text", "edit_files"]
    assert packet["omitted"] == {"count_limit": 1}


def test_file_drafts_obey_whole_body_utf8_and_total_byte_limits():
    large, undo = file_edit(new_text="수" * 11_000), file_edit("undo", undo="accepted-files")
    packet = correction_drafts.build([large, undo], turn_id="large-turn", diff_hash=DIFF)
    assert len(canonical_json(large.arguments).encode("utf-8")) > 32_000
    assert packet["omitted"] == {"argument_byte_limit": 1}
    assert [draft["original_action_id"] for draft in packet["drafts"]] == ["undo"]
    assert packet["drafts"][0]["arguments"] == undo.arguments
    calls = [file_edit(f"files-{index}", new_text="x" * 17_000) for index in range(2)]
    packet = correction_drafts.build(calls, turn_id="total-turn", diff_hash=DIFF)
    assert len(packet["drafts"]) == 1 and packet["omitted"] == {"argument_byte_limit": 1}
    assert packet["retained_argument_utf8_bytes"] <= 32_000
    assert packet["drafts"][0]["arguments"] == calls[0].arguments


def test_two_drafts_keep_exact_arguments_and_gateway_input_identity_without_execution():
    first = edit(repair_prediction={"event": "returned", "expected": {"value": "수정"}})
    second = edit("edit-2", path="tests/test_source.py", occurrence=1, new_text="assert fixed\n")
    calls = [first, second]
    before = [call.model_dump(mode="json") for call in calls]
    packet = correction_drafts.build(calls, turn_id="turn-1", diff_hash=DIFF)
    assert packet["status"] == "retained"
    assert packet["execution_status"] == "not_executed"
    assert packet["interpretation"] == "model_authored_unverified"
    assert packet["origin_turn_id"] == "turn-1" and packet["source_diff_hash"] == DIFF
    assert packet["candidate_count"] == 2 and packet["omitted"] == {}
    for draft, call in zip(packet["drafts"], calls, strict=True):
        assert draft["arguments"] == call.arguments
        assert draft["arguments_hash"] == sha256_json(call.arguments)
        assert draft["input_hash"] == sha256_json({"tool": call.name, "arguments": call.arguments})
        assert draft["original_action_id"] == call.action_id
        assert draft["body_status"] == "retained"
    assert "occurrence" not in packet["drafts"][0]["arguments"]
    assert [call.model_dump(mode="json") for call in calls] == before
    assert "passed" not in packet and "workspace_diff_hash" not in packet


def test_proposed_identity_preserves_explicit_annotation_presence():
    absent = edit()
    explicit = RequestedTool(**{**absent.model_dump(mode="json"), "memory_update": None})
    packets = [correction_drafts.build([call], turn_id="turn-1", diff_hash=DIFF)
               for call in (absent, explicit)]
    assert packets[0]["drafts"][0]["arguments_hash"] == packets[1]["drafts"][0]["arguments_hash"]
    assert packets[0]["drafts"][0]["input_hash"] != packets[1]["drafts"][0]["input_hash"]
    assert packets[1]["drafts"][0]["input_hash"] == sha256_json({
        "tool": explicit.name, "arguments": explicit.arguments, "memory_update": None})


def test_roundtrip_and_projection_are_copies_and_stale_bodies_are_withheld():
    call = edit(repair_prediction={"items": ["unchanged"]})
    packet = correction_drafts.build([call], turn_id="turn-1", diff_hash=DIFF)
    restored = json.loads(json.dumps(packet))
    same = correction_drafts.project(restored, diff_hash=DIFF)
    assert same == packet
    same["drafts"][0]["arguments"]["repair_prediction"]["items"].append("local")
    assert packet["drafts"][0]["arguments"] == call.arguments
    stale = correction_drafts.project(restored, diff_hash="sha256:" + "b" * 64)
    assert stale["status"] == "stale" and stale["retained_argument_utf8_bytes"] == 0
    assert stale["omitted"] == {"stale_diff": 1}
    assert stale["drafts"][0]["arguments_hash"] == packet["drafts"][0]["arguments_hash"]
    assert "arguments" not in stale["drafts"][0]
    assert stale["drafts"][0]["body_status"] == "omitted_stale_diff"
    assert packet["drafts"][0]["arguments"] == call.arguments


def test_oversized_unicode_body_is_omitted_whole_and_does_not_block_small_draft():
    large = edit("too-large", new_text="수" * 11_000)
    small = edit("small")
    packet = correction_drafts.build([large, small], turn_id="turn-1", diff_hash=DIFF)
    assert len(large.arguments["new_text"]) < 20_000
    argument_bytes = len(canonical_json(large.arguments).encode("utf-8"))
    assert argument_bytes > correction_drafts.MAX_ARGUMENT_BYTES
    assert packet["candidate_count"] == 2
    assert packet["omitted"] == {"argument_byte_limit": 1}
    assert [draft["original_action_id"] for draft in packet["drafts"]] == ["small"]
    assert packet["drafts"][0]["arguments"] == small.arguments
    assert packet["retained_argument_utf8_bytes"] <= correction_drafts.MAX_ARGUMENT_BYTES
    alone = correction_drafts.build([large], turn_id="turn-1", diff_hash=DIFF)
    assert alone["status"] == "omitted" and alone["drafts"] == []


def test_total_byte_and_count_limits_do_not_silently_change_replacement_bodies():
    calls = [edit(f"edit-{n}", new_text="x" * 17_000) for n in range(2)]
    packet = correction_drafts.build(calls, turn_id="turn-1", diff_hash=DIFF)
    assert len(packet["drafts"]) == 1 and packet["omitted"] == {"argument_byte_limit": 1}
    assert packet["drafts"][0]["arguments"] == calls[0].arguments
    small = [edit(f"small-{n}").model_dump(mode="json") for n in range(3)]
    before = copy.deepcopy(small)
    packet = correction_drafts.build(small, turn_id="turn-1", diff_hash=DIFF)
    assert len(packet["drafts"]) == correction_drafts.MAX_DRAFTS == 2
    assert packet["omitted"] == {"count_limit": 1} and small == before
    packet["drafts"][0]["arguments"]["new_text"] = "local"
    assert small == before


def test_non_edit_calls_do_not_create_an_edit_draft():
    call = RequestedTool(name="read_file", action_id="read-1", arguments={"path": "source.py"})
    assert correction_drafts.build([call], turn_id="turn-1", diff_hash=DIFF) is None
    assert correction_drafts.project(None, diff_hash=DIFF) is None
