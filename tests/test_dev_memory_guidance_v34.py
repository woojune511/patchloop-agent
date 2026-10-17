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
    start = DEV_SYSTEM_PROMPT.index("memory_update retains")
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
    # Refreshed for explicit primary/countercheck roles; other ordered inputs stay pinned.
    tools = _legacy_compression_surface(tools)
    encoded = json.dumps(_without_descriptions(tools), ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == (
        "e02c7ceb93201640950920b260422b0ae35fce974e3728b79e63345fb4bcf0e5"
    )
    for tool in tools:
        assert tool["strict"] is True
        memory = tool["parameters"]["properties"]["turn_decision"]["properties"]["memory_update"]
        assert memory == memory_update_schema()


@pytest.mark.parametrize(("names", "expected"), [
    (
        ("read_file", "run_check", "run_probe", "search_files", "stop_task"),
        "544c19f4d8e63f8a8810efe1dd4cd0adf3dee51cdb0145a4509de554027739c2",
    ),
    (
        ("finish_task", "read_file", "replace_text", "run_probe", "search_files", "stop_task"),
        "b817201c9d1aa8432575b0c1b55015dc01bc08a2b002e3e2cc09ab13bfa229c6",
    ),
    (
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task"),
        "310f8ec3dd129c93fb10c2a0589decf38eb09ce60e395ef906ac814e399e5139",
    ),
    (
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task",
         "finish_task"),
        "6302bc9d248be03d6e1430f0102a0e5c00ecb7883c25d453945f979f21fd3af7",
    ),
])
def test_descriptions_outside_memory_and_schema_order_are_unchanged(names, expected):
    # Finish prose now ties requirements and unfinished verification to evidence; wire stays fixed.
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
        "2d0a9063da8d508a3c1218903cae12e33aa5db97f4d5655ca645fd5d52dc1331"
    )


def test_guidance_is_bounded_in_characters_and_canonical_bytes_not_claimed_tokens():
    _, memory, _ = _memory_block()
    # v33: 3,368 chars (including two trailing newlines), 7,965 total, 4,047 schema bytes.
    assert len(memory) <= 2400
    # Simplification stays within the original bounded prompt contract.
    assert len(DEV_SYSTEM_PROMPT) <= 8007
    # The two-reference question object adds wire structure; final request limits stay fixed.
    assert len(canonical_json(memory_update_schema()).encode()) <= 4000
    assert hashlib.sha256(canonical_json(_without_descriptions(memory_update_schema()))
                          .encode()).hexdigest() == (
        "2b2939d1a9bb49ef05cf62e0274625cda8dfba88ef54e99f850b310945899780"
    )


def test_compact_guidance_keeps_optional_evidence_lifecycle_and_concern_boundaries():
    _, memory, _ = _memory_block()
    for instruction in (
        "model interpretations and untested assumptions",
        "not reasoning\ntranscripts or status copies",
        "behavior-bearing observed source/results",
        "note_id=null creates a distinct interpretation", "remove_note_ids",
        "Updates are optional", "closed_by_model never certify\nbehavior",
        "not confirmation of the note's prose", "Reconsider claims after edits",
        "first non-null", "before the batch executes",
        "pending/current-batch results", "findings=[]", "memory_update=null",
        "Null preserves notes and the question", "clears only the question",
        "working_notes.available_note_ids", "pre-batch\nreceipt, not current availability",
        "working_notes_after_batch", "Source changes can expire notes",
        "does not mean a note was stored", "without\nrereading solely to retry a note",
        "No quota", "concern_id=null for a distinct concern", "Exact repeats do nothing",
        "already observed successful current-diff check/probe", "evidence_action_id",
        "Baseline evidence cannot\nvalidate a candidate", "Dismiss needs a reason",
        "Neither certifies semantic coverage", "after diff changes", "source-note expiry",
        "Use [] for no concern change", "do not mechanically gate actions or finish",
    ):
        assert instruction in memory


def test_guidance_identity_changes_without_changing_run_schema_or_limits():
    # Common action/probe guidance changes the overall surface identity;
    # argument and description identities remain independently pinned above.
    assert dev_tool_surface_hash() == (
        "sha256:eb84e143153fc510c7ec56212f70d9b5d56e3f6042a5f2ecb96f0ff4780577df"
    )
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (40, 100, 4, 1800)
