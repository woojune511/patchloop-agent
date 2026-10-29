"""Pin memory and unaffected wire values alongside the explicit small-core contract."""

from __future__ import annotations

import hashlib
import json

import pytest
from repair_mechanism_expectations import FROZEN_ARM

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
    end = DEV_SYSTEM_PROMPT.index(
        "A mutation sends only" if FROZEN_ARM is None else "A mutation requires")
    return DEV_SYSTEM_PROMPT[:start], DEV_SYSTEM_PROMPT[start:end], DEV_SYSTEM_PROMPT[end:]


def _assert_small_core(tool):
    fields = {
        "replace_text": ["path", "old_text", "new_text", "occurrence", "hypothesis",
                         "expected_behavior"],
        "stop_task": ["reason_code", "summary"],
    }
    if FROZEN_ARM is not None or tool["name"] not in fields:
        return False
    parameters = tool["parameters"]
    assert list(parameters["properties"]) == fields[tool["name"]]
    assert parameters["required"] == fields[tool["name"]]
    assert parameters["additionalProperties"] is False
    return True


def _legacy_compression_surface(tools):
    # Setup-helper guidance is tested separately; retired mutation fields are absent.
    # Normalize only that guidance block. Frozen arms retain their original delimiter;
    # current caller/API descriptions and every ordered wire value remain pinned below.
    for tool in tools:
        if tool["name"] == "run_probe":
            description = tool["description"]
            start = description.index(
                "Helper mode automatically supplies only check_setup" if FROZEN_ARM is None
                else "Before exercising behavior, use the available ")
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
    # Fresh edit/stop inputs omit annotations; all other wire values remain pinned.
    tools = _legacy_compression_surface(tools)
    encoded = json.dumps(_without_descriptions(tools), ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == (
        "09e5eabd0e782b15f86cdc2aec844df14617a2f1588d2cd6c95d998004b83eb9"
        if FROZEN_ARM is None else
        "e02c7ceb93201640950920b260422b0ae35fce974e3728b79e63345fb4bcf0e5"
    )
    for tool in tools:
        assert tool["strict"] is True
        if _assert_small_core(tool):
            continue
        memory = tool["parameters"]["properties"]["turn_decision"]["properties"]["memory_update"]
        assert memory == memory_update_schema()


@pytest.mark.parametrize(("names", "expected"), [
    pytest.param(
        ("read_file", "run_check", "run_probe", "search_files", "stop_task"),
        "fc047c2ebd151936e94ebfa2aaa1c8548acf32260a2ad2a033b93149f2db7e7c"
        if FROZEN_ARM is None else
        "544c19f4d8e63f8a8810efe1dd4cd0adf3dee51cdb0145a4509de554027739c2",
        id="names0-99567faf1ea920a9157e5ea6618c5d43e7d56e441820be941403a025d9b2abe9"
        if FROZEN_ARM is None else None,
    ),
    pytest.param(
        ("finish_task", "read_file", "replace_text", "run_probe", "search_files", "stop_task"),
        "290f340e7c845ebfb8246fbd611e5a86b78860c99d2a4256aaaaf8c8323d33f3"
        if FROZEN_ARM is None else
        "b817201c9d1aa8432575b0c1b55015dc01bc08a2b002e3e2cc09ab13bfa229c6",
        id="names1-de57dc4e83f8b26994c5df5f659cc208bbd3b348233d0ad3640493ffd5b90bd3"
        if FROZEN_ARM is None else None,
    ),
    pytest.param(
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task"),
        "ed4ecf72224de5eb209e3a99d964cb84c6a2fcafb8a5fea07b4d23680699b719"
        if FROZEN_ARM is None else
        "310f8ec3dd129c93fb10c2a0589decf38eb09ce60e395ef906ac814e399e5139",
        id="names2-923a71312af5fa8d677ce72762b2f045a47ff2ebc4e084caaf1f57a2c11e7032"
        if FROZEN_ARM is None else None,
    ),
    pytest.param(
        ("read_file", "replace_text", "run_check", "run_probe", "search_files", "stop_task",
         "finish_task"),
        "ad917cf1f860db1352a5bd577f85649bfaa96762037cfd8983ac913abb2cfd1f"
        if FROZEN_ARM is None else
        "6302bc9d248be03d6e1430f0102a0e5c00ecb7883c25d453945f979f21fd3af7",
        id="names3-53d8c9ffaa20544b633c883b1e40010113b680722f23caebeb0ef991f1738caa"
        if FROZEN_ARM is None else None,
    ),
])
def test_descriptions_outside_memory_and_schema_order_are_unchanged(names, expected):
    # Pin current grounded check/test guidance; preserve IDs and historical removal arms.
    # OFF still has the prior four digests; argument shapes remain independently pinned.
    tools = dev_tool_schemas(finish_enabled="finish_task" in names, allowed_tools=names)
    tools = _legacy_compression_surface(tools)
    for tool in tools:
        if _assert_small_core(tool):
            continue
        decision = tool["parameters"]["properties"]["turn_decision"]["properties"]
        decision["memory_update"] = _without_descriptions(decision["memory_update"])
    encoded = json.dumps(tools, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == expected


def test_surrounding_action_guidance_identity():
    from repair_mechanism_expectations import JUDGMENT
    prefix, _, suffix = _memory_block()
    # Registered file batches join annotation-free actions; memory stays unchanged
    # and surrounding prose keeps the 8,000-character bound.
    # Historical J0/J1 arms retain their exact earlier surrounding-guidance identities.
    assert hashlib.sha256(canonical_json([prefix, suffix]).encode()).hexdigest() == (
        "dcc32805637450349c682ae5d2001c78ebacc937f81e00a337b202d4f98f212f"
        if FROZEN_ARM is None else
        "2d0a9063da8d508a3c1218903cae12e33aa5db97f4d5655ca645fd5d52dc1331"
        if JUDGMENT else "c6439ce32e7724ed5d4c08dc1f207186b45e34234947c2867d7a65f096ce10a3"
    )


def test_guidance_is_bounded_in_characters_and_canonical_bytes_not_claimed_tokens():
    _, memory, _ = _memory_block()
    # v33: 3,368 chars (including two trailing newlines), 7,965 total, 4,047 schema bytes.
    assert len(memory) <= 2400
    if FROZEN_ARM is None:
        # Changing the following action delimiter must not absorb or change the memory body.
        assert hashlib.sha256(memory.encode()).hexdigest() == (
            "2093928be3895d8d4656a4db099e9f0a7fb4f6f3416cef7539b30ab6f0f220c2"
        )
    # Simplification stays within the original bounded prompt contract.
    assert len(DEV_SYSTEM_PROMPT) <= 8007
    # The two-reference question object adds wire structure; final request limits stay fixed.
    assert len(canonical_json(memory_update_schema()).encode()) <= 4000
    assert hashlib.sha256(canonical_json(_without_descriptions(memory_update_schema()))
                          .encode()).hexdigest() == (
        "2b2939d1a9bb49ef05cf62e0274625cda8dfba88ef54e99f850b310945899780"
    )


def test_compact_guidance_keeps_optional_evidence_lifecycle_and_concern_boundaries():
    from repair_mechanism_expectations import JUDGMENT
    _, memory, _ = _memory_block()
    for instruction in (
        "model interpretations and untested assumptions",
        "not reasoning\ntranscripts or status copies",
        "behavior-bearing observed source/results",
        "note_id=null creates a distinct interpretation", "remove_note_ids",
        "Updates are optional",
        ("closed_by_model never certify\nbehavior" if JUDGMENT else
         "model concern resolution never certify\nbehavior"),
        "not confirmation of the note's prose", "Reconsider claims after edits",
        "first non-null", "before the batch executes",
        "pending/current-batch results", "findings=[]", "memory_update=null",
        "Null preserves notes and the question", "clears only the question",
        "working_notes.available_note_ids", "Source changes can expire notes",
        "No quota", "concern_id=null for a distinct concern", "Exact repeats do nothing",
        "already observed successful current-diff check/probe", "evidence_action_id",
        "Baseline evidence cannot\nvalidate a candidate", "Dismiss needs a reason",
        "Neither certifies semantic coverage", "after diff changes", "source-note expiry",
        "Use [] for no concern change", "do not mechanically gate actions or finish",
    ):
        assert instruction in memory
    feedback = (
        ("Tool outputs report action outcomes only", "working_notes.last_update_result",
         "working_plan.last_update_result", "is nonblocking", "last_source_lifecycle",
         "Receipts precede the batch", "Fix annotation errors on a useful later call")
        if FROZEN_ARM is None else
        ("pre-batch\nreceipt, not current availability", "working_notes_after_batch",
         "does not mean a note was stored", "without\nrereading solely to retry a note")
    )
    for instruction in feedback:
        assert instruction in memory


def test_guidance_identity_changes_without_changing_run_schema_or_limits():
    # Registered selection review and completion-source delivery change the surface;
    # argument and description identities remain independently pinned above.
    assert dev_tool_surface_hash() == (
        "sha256:ba96122e880e6d6962fb5fc9bcba696dbe1c8fabf531c59dd032ebab2a555766"
        if FROZEN_ARM is None else
        "sha256:57193859890419b79cb7f4927c37796d044bc4bf7159c51ddf17723849529e26"
    )
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (
                40, 100, 4 if FROZEN_ARM is not None else 12, 1800,
            )
