"""Memory compression preserves the wire; action guidance has its own identity."""

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


def _legacy_compression_surface(tools):
    # Setup-helper guidance is tested separately; retired mutation fields are absent.
    # Keep the earlier field/order/description bytes pinned at the memory boundary.
    for tool in tools:
        if tool["name"] == "run_probe":
            description = tool["description"]
            start = description.index("Before exercising behavior, use the available ")
            end = description.index("Compare actual input/output", start)
            tool["description"] = description[:start] + description[end:]
    return tools


def test_all_tool_wire_values_and_order_match_pre_compression_surface():
    tools = dev_tool_schemas(
        finish_enabled=True, check_ids=("public-a", "public-b"),
        allowed_tools=("read_file", "search_files", "replace_text", "run_check",
                       "run_probe", "finish_task", "stop_task"),
    )
    # Preserve object, tool, enum and required-field order, nullability and defaults.
    # Refreshed after annotation retirement and for explicit explanation bounds.
    tools = _legacy_compression_surface(tools)
    encoded = json.dumps(_without_descriptions(tools), ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == (
        "4cde62f052c239f79814b285611e73acf5e37de8d85f606f4e61b3235cfd2c70"
    )
    for tool in tools:
        assert tool["strict"] is True
        memory = tool["parameters"]["properties"]["turn_decision"]["properties"]["memory_update"]
        assert memory == memory_update_schema()


@pytest.mark.parametrize(("names", "expected"), [
    (
        ("read_file", "run_check", "run_probe", "search_files", "stop_task"),
        "3b4a5ff0825dec145cb350ad1edc23e7fed4c20f7177cdbc9312b772a8387703",
    ),
    (
        ("finish_task", "read_file", "replace_text", "run_probe", "search_files", "stop_task"),
        "e5c851f7fb8dfeb585b242a68d9d01ce81618b859a16777e2124f6e4449d39ae",
    ),
    (
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task"),
        "d43eb6f78dcd5388b6ed4bbc0e3122dba599a8c0389d01d3a5299a7ebf6fff5b",
    ),
    (
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task",
         "finish_task"),
        "eb304557fd370a9fcbd8e5b216b60c4dad7985497b907412e4eec63430c58cd0",
    ),
])
def test_descriptions_outside_memory_and_schema_order_are_unchanged(names, expected):
    tools = dev_tool_schemas(finish_enabled="finish_task" in names, allowed_tools=names)
    tools = _legacy_compression_surface(tools)
    for tool in tools:
        decision = tool["parameters"]["properties"]["turn_decision"]["properties"]
        decision["memory_update"] = _without_descriptions(decision["memory_update"])
    encoded = json.dumps(tools, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == expected


def test_surrounding_action_guidance_identity():
    prefix, _, suffix = _memory_block()
    assert hashlib.sha256(canonical_json([prefix, suffix]).encode()).hexdigest() == (
        "c6fc270c54696bfb4ed25d60c5a306b8f8a829487fea2ab11615217efcb9cb97"
    )


def test_guidance_is_bounded_in_characters_and_canonical_bytes_not_claimed_tokens():
    _, memory, _ = _memory_block()
    # v33: 3,368 chars (including two trailing newlines), 7,965 total, 4,047 schema bytes.
    assert len(memory) <= 2400
    # Simplification stays within the original bounded prompt contract.
    assert len(DEV_SYSTEM_PROMPT) <= 8007
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
    # Common action/probe guidance changes the overall surface identity;
    # argument and description identities remain independently pinned above.
    assert dev_tool_surface_hash() == (
        "sha256:25f1db63f18b3f138ee8bdc8686ad320d7c9a3965d4e10acd1055fdd590555b7"
    )
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (40, 100, 4, 1800)
