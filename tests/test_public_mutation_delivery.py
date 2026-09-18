"""Segment handoffs retain exact public receipts without native provider items."""
from __future__ import annotations

import copy
import json

import pytest

from diagnostics.public_mutation_delivery import delivered_mutation
from patchloop.dev.conversation import SEGMENT_RULES
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def example():
    mutation = {"diff_hash": "sha256:" + "1" * 64,
                "expected_behavior": "Keep ordinary field-mode profiles unchanged.",
                "behavior_cases": {"status": "recorded", "coverage_status": "not_assessed"}}
    state = {"last_successful_mutation": {
        "action_id": "edit-2", "delivery": "preceding_function_call_output"}}
    output = {"type": "function_call_output", "call_id": "edit-2", "output": canonical_json({
        "action_id": "edit-2", "tool": "replace_text", "status": "succeeded",
        "output": {"mutation": mutation, "worktree_diff_hash": mutation["diff_hash"]},
    })}
    return mutation, state, output


@pytest.mark.parametrize("archived", [False, True])
def test_exact_native_and_segment_archive_deliver_the_same_mutation(archived):
    mutation, state, output = example()
    native = [SEGMENT_RULES.archive(exchanges=[output])] if archived else [output]
    before = copy.deepcopy((state, native))
    actual, mode = delivered_mutation(state, native)
    assert actual == mutation
    assert mode == ("quoted_public_exchange" if archived else "preceding_function_call_output")
    assert (state, native) == before


@pytest.mark.parametrize("kind", ["missing", "duplicate", "ordinary_prose", "wrong_archive"])
def test_missing_or_ambiguous_delivery_cannot_borrow_an_unseen_receipt(kind):
    _, state, output = example()
    if kind == "missing":
        native = []
    elif kind == "duplicate":
        native = [output, SEGMENT_RULES.archive(exchanges=[output])]
    else:
        record = {"kind": "unrelated", "referenced_public_exchanges": [output]}
        native = [{"role": "user" if kind == "ordinary_prose" else "developer",
                   "content": canonical_json(record)}]
    with pytest.raises(ContractError, match="missing or ambiguous"):
        delivered_mutation(state, native)


@pytest.mark.parametrize("defect", ["action_id", "tool", "status", "diff", "missing_mutation"])
def test_archived_receipt_still_requires_exact_mutation_identity(defect):
    _, state, output = example()
    result = json.loads(output["output"])
    if defect == "diff":
        result["output"]["worktree_diff_hash"] = "different"
    elif defect == "missing_mutation":
        result["output"].pop("mutation")
    else:
        result[defect] = "wrong"
    output["output"] = canonical_json(result)
    with pytest.raises(ContractError, match="mutation delivery"):
        delivered_mutation(state, [SEGMENT_RULES.archive(exchanges=[output])])


def test_inline_current_record_and_empty_state_need_no_exchange():
    mutation, _, _ = example()
    assert delivered_mutation({"last_successful_mutation": mutation}, []) == (
        mutation, "inline_current_state")
    assert delivered_mutation({}, []) == ({}, None)
