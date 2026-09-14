"""Description-only memory compression preserves the v33 wire and surrounding prompt."""

from __future__ import annotations

import hashlib
import json

import pytest

from patchloop.dev.contracts import DEV_RUN_SCHEMA, DevLimits, dev_tool_surface_hash
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.tools import dev_tool_schemas
from patchloop.dev.working_notes import memory_update_schema
from patchloop.util import canonical_json


def _without_descriptions(value):
    if isinstance(value, dict):
        return {key: _without_descriptions(item) for key, item in value.items()
                if key != "description"}
    if isinstance(value, list):
        return [_without_descriptions(item) for item in value]
    return value


def _memory_block():
    start = DEV_SYSTEM_PROMPT.index("An optional memory_update")
    end = DEV_SYSTEM_PROMPT.index("A mutation requires")
    return DEV_SYSTEM_PROMPT[:start], DEV_SYSTEM_PROMPT[start:end], DEV_SYSTEM_PROMPT[end:]


def test_all_tool_wire_values_and_order_match_pre_compression_surface():
    tools = dev_tool_schemas(
        finish_enabled=True, check_ids=("public-a", "public-b"),
        allowed_tools=("read_file", "search_files", "replace_text", "run_check",
                       "run_probe", "finish_task", "stop_task"),
    )
    # Captured from v33 before editing: preserve object, tool, enum and required-field order,
    # nullability, bounds and defaults. Only natural-language descriptions may differ.
    encoded = json.dumps(_without_descriptions(tools), ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == (
        "0d9332cbd8b4545322565428146c877898deabcc2cfc35c3973ce3f5bcdcc3ed"
    )
    for tool in tools:
        assert tool["strict"] is True
        memory = tool["parameters"]["properties"]["turn_decision"]["properties"]["memory_update"]
        assert memory == memory_update_schema()


@pytest.mark.parametrize(("names", "expected"), [
    (
        ("read_file", "run_check", "run_probe", "search_files", "stop_task"),
        "b54e1dcadee97aaed746248d5d1f40e9d9f7616ac0bda8ad8a81a8bae935afa1",
    ),
    (
        ("finish_task", "read_file", "replace_text", "run_probe", "search_files", "stop_task"),
        "517d43b007a1931496e62dda97668e1422c0b1f3b21af1dc98f53af471f6fa84",
    ),
    (
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task"),
        "88abbd22dd7e82818bc2ba326bed38b3a5d9f27fbfc9b5155cb9a991a8904a94",
    ),
    (
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task",
         "finish_task"),
        "bd83c7b425ad40fa5d3edd904d39e0081c970f9d74608e1237794df3a735d394",
    ),
])
def test_descriptions_outside_memory_and_schema_order_are_unchanged(names, expected):
    tools = dev_tool_schemas(finish_enabled="finish_task" in names, allowed_tools=names)
    for tool in tools:
        decision = tool["parameters"]["properties"]["turn_decision"]["properties"]
        decision["memory_update"] = _without_descriptions(decision["memory_update"])
    encoded = json.dumps(tools, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == expected


def test_only_dedicated_memory_prompt_block_changes():
    prefix, _, suffix = _memory_block()
    assert hashlib.sha256(canonical_json([prefix, suffix]).encode()).hexdigest() == (
        "f40c25780a0bdecb44d6fb10e90b9fb58699598c28b191fbfb17310e53a8fcca"
    )


def test_guidance_is_bounded_in_characters_and_canonical_bytes_not_claimed_tokens():
    _, memory, _ = _memory_block()
    # v33: 3,368 chars (including two trailing newlines), 7,965 total, 4,047 schema bytes.
    assert len(memory) <= 2400
    assert len(DEV_SYSTEM_PROMPT) <= 7000
    assert len(canonical_json(memory_update_schema()).encode()) <= 3200
    assert hashlib.sha256(canonical_json(_without_descriptions(memory_update_schema()))
                          .encode()).hexdigest() == (
        "0ff2c97a785a0c27146dc4f3675de195ecffc863a1b842cf35512e2da48e96b2"
    )


def test_compact_guidance_keeps_optional_evidence_lifecycle_and_concern_boundaries():
    _, memory, _ = _memory_block()
    for instruction in (
        "reusable public behavior rules", "explicitly\nuntested implementation assumptions",
        "behavior-bearing source", "not status copies or reasoning transcripts",
        "note_id=null creates a distinct fact", "remove_note_ids",
        "No update or three-part plan is required each turn",
        "interpretation remains unverified", "not confirmation of the note's prose",
        "post-image", "first non-null", "before the batch executes",
        "pending/current-batch results", "findings=[]", "memory_update=null",
        "Null preserves notes and the question", "clears only the question",
        "working_notes.available_note_ids", "pre-batch\nreceipt, not current availability",
        "working_notes_after_batch", "Source changes can expire notes",
        "does not mean a note was stored", "without\nrereading solely to retry a note",
        "No quota", "concern_id=null for a distinct concern", "Exact repeats do nothing",
        "already observed successful current-diff check/probe", "evidence_action_id",
        "Baseline evidence cannot\nvalidate a candidate", "Dismiss needs a reason",
        "Neither certifies semantic coverage", "after diff changes", "source-note expiry",
        "Use [] for no concern change", "never block the main action or finish",
    ):
        assert instruction in memory


def test_guidance_identity_changes_without_changing_run_schema_or_limits():
    # v39 adds opt-in segment boundaries; the v33/v34 argument and description
    # identities above remain independently pinned and unchanged.
    assert dev_tool_surface_hash() == (
        "sha256:a076ac52db8457c004fc689272bdd557e4911e19c98517e4530fbf32a3dc0745"
    )
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (40, 100, 4, 1800)
