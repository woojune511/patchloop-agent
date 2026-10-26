"""Bounded public edit proposals retained for correction, never for execution."""

from __future__ import annotations

import copy
from collections.abc import Iterable
from typing import Any

from patchloop.util import canonical_json, sha256_json

POLICY = "rejected-edit-drafts-v1"
MAX_DRAFTS = 2
MAX_ARGUMENT_BYTES = 32_000
GUIDANCE = (
    "These are unexecuted model-authored drafts, not instructions or verified source. "
    "Correct the reported request error and return at most one offered action. You may "
    "reuse a retained argument object without rewriting its replacement body. The current "
    "schema, exact source anchors, scope and budgets still apply. Original action IDs are "
    "provenance only; this packet grants no execution or verification credit. Omitted "
    "argument bodies are unavailable, not empty replacements."
)


def contract() -> dict[str, Any]:
    return {
        "policy": POLICY,
        "max_drafts": MAX_DRAFTS,
        "max_total_argument_utf8_bytes": MAX_ARGUMENT_BYTES,
        "size_basis": "canonical-json-arguments",
        "binding": "origin-turn-action-input-and-workspace-diff",
        "projection": "same-diff-exact-bodies-otherwise-stale-references",
        "effect": "correction-data-only-no-execution-source-or-completion-authority",
    }


def build(calls: Iterable[Any], *, turn_id: str, diff_hash: str) -> dict[str, Any] | None:
    """Retain whole argument objects in authored order, without dispatch or repair.

    The caller supplies already decoded public RequestedTool objects or their JSON
    dumps. Invalid batch membership does not validate an individual edit's schema,
    anchors or semantics. Omitted/default/null fields retain their original shape.
    """
    drafts = []
    candidate_count = 0
    retained_bytes = 0
    omitted = {"count_limit": 0, "argument_byte_limit": 0}
    for call in calls:
        raw = call.model_dump(mode="json") if hasattr(call, "model_dump") else call
        if raw["name"] != "replace_text":
            continue
        candidate_count += 1
        if len(drafts) >= MAX_DRAFTS:
            omitted["count_limit"] += 1
            continue
        arguments = raw["arguments"]
        argument_bytes = len(canonical_json(arguments).encode("utf-8"))
        if retained_bytes + argument_bytes > MAX_ARGUMENT_BYTES:
            omitted["argument_byte_limit"] += 1
            continue
        # Match the gateway's proposed-input identity without creating an action.
        action_input = {"tool": raw["name"], "arguments": arguments}
        if raw.get("turn_decision") is not None:
            action_input["turn_decision"] = raw["turn_decision"]
        if "memory_update" in raw:
            action_input["memory_update"] = raw["memory_update"]
        drafts.append({
            "original_action_id": raw["action_id"],
            "tool": raw["name"],
            "input_hash": sha256_json(action_input),
            "arguments_hash": sha256_json(arguments),
            "argument_utf8_bytes": argument_bytes,
            "body_status": "retained",
            "arguments": copy.deepcopy(arguments),
        })
        retained_bytes += argument_bytes
    if candidate_count == 0:
        return None
    return {
        "policy": POLICY,
        "origin_turn_id": turn_id,
        "source_diff_hash": diff_hash,
        "status": "retained" if drafts else "omitted",
        "execution_status": "not_executed",
        "interpretation": "model_authored_unverified",
        "candidate_count": candidate_count,
        "retained_argument_utf8_bytes": retained_bytes,
        "drafts": drafts,
        "omitted": {reason: count for reason, count in omitted.items() if count},
        "guidance": GUIDANCE,
    }


def project(packet: dict[str, Any] | None, *, diff_hash: str) -> dict[str, Any] | None:
    """Copy correction data; withhold bodies when their candidate is no longer current."""
    if packet is None:
        return None
    view = copy.deepcopy(packet)
    if view["source_diff_hash"] == diff_hash:
        return view
    withheld = sum("arguments" in draft for draft in view["drafts"])
    for draft in view["drafts"]:
        draft.pop("arguments", None)
        draft["body_status"] = "omitted_stale_diff"
    view.update(status="stale", current_diff_hash=diff_hash, retained_argument_utf8_bytes=0)
    if withheld:
        view["omitted"]["stale_diff"] = withheld
    view["guidance"] = (
        "These unexecuted drafts belong to another workspace diff; their argument bodies "
        "are withheld. Reassess any intended edit against current source and the offered "
        "schema. References grant no mutation, source or verification authority."
    )
    return view
