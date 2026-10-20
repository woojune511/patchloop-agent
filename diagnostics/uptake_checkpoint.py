"""Import the two frozen, already-paid decisions without dispatching or rebilling.

This is an experiment connector, not an ordinary resume or a runtime policy.
The original records and the frozen design remain immutable.
"""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_continuation import inherited_reads
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ModelTurn,
    RequestedTool,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import history_metadata, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.runtime import runtime_content_hash
from patchloop.util import sha256_bytes, sha256_json

DESIGN = Path("C:/pt/hypfollow01/plan.json")
DESIGN_HASH = "sha256:ebf523c24e626e4c8b184eda4f3ab9a9b764958c8e37eab8c4821298ae0e3b5a"


def read_bound(ref):
    raw = Path(ref["path"]).read_bytes()
    require(sha256_bytes(raw) == ref["content_hash"], "bound file changed: " + ref["path"])
    if "size_bytes" in ref:
        require(len(raw) == ref["size_bytes"], "bound file size changed")
    return raw


def load_design(path=DESIGN):
    plan = json.loads(read_bound({"path": str(path), "content_hash": DESIGN_HASH}))
    bindings = json.loads(read_bound(plan["bindings"]))
    for name, digest in bindings["input_hashes"].items():
        read_bound({"path": name, "content_hash": digest})
    for ref in [plan["grading"], plan["cost"]["pricing"], plan["terminal_public_oracle"]]:
        read_bound(ref)
    require(runtime_content_hash() == bindings["runtime_hash"], "frozen runtime changed")
    require(
        plan["order"] == [r["cell"] for r in plan["rows"]] == ["B1", "B2"],
        "fixed row order changed",
    )
    inherited = plan["inheritance"]
    selected = json.loads(Path(inherited["prepared_B_request"]).read_bytes())
    require(sha256_json(selected) == inherited["request_hash"], "saved B request changed")
    root, run_id = Path(inherited["parent_root"]), inherited["parent_run"]
    journal = DevJournal(root, run_id)
    source = Source(
        root,
        run_id,
        sha256_bytes(journal.path.read_bytes()),
        sha256_bytes(journal.envelope_path.read_bytes()),
        Path(plan["task_path"]),
        sha256_bytes(Path(plan["task_path"]).read_bytes()),
    )
    return plan, source, selected


def saved_turn(row, selected):
    """Rehydrate opaque items by type/order only; never interpret their contents."""
    public = json.loads(read_bound(row["public_response"]))
    ordered = json.loads(read_bound(row["opaque_output_order"]))["output_order"]
    calls = [RequestedTool(**c) for c in public["tool_calls"]]
    require(
        len(calls) == 1 and calls[0].name == "run_probe" and calls[0].action_id == row["action_id"],
        "saved action linkage changed",
    )
    require(
        sha256_json(calls[0].arguments) == row["arguments_hash"]
        and calls[0].arguments["python_source"].encode() == read_bound(row["probe"]),
        "saved probe changed",
    )
    require(
        len(ordered) == 2
        and ordered[1] == {"action_id": row["action_id"]}
        and set(ordered[0]) == {"id", "status", "encrypted_content"},
        "saved ordered output changed",
    )
    events = DevJournal(
        Path(row["public_response"]["path"]).parents[3], "run_dev_sample_f87767e6bf544a18"
    ).events()
    matches = [
        e["payload"]
        for e in events
        if e["event_type"] == "provider_call_finished"
        and e["payload"].get("sample_id") == row["sample_id"]
    ]
    require(len(matches) == 1, "saved sample usage is not unique")
    usage = matches[0]
    require(
        usage["billing_known"]
        and usage["error_code"] is None
        and usage["response_status"] == "completed"
        and usage["request_hash"] == sha256_json(selected)
        and usage["response_model"] == selected["model"],
        "saved usage identity changed",
    )
    turn = ModelTurn(
        tool_calls=calls,
        provider_continuation=(
            EncryptedReasoningContinuationItem(**ordered[0]),
            FunctionCallContinuationRef(**ordered[1]),
        ),
        requested_input_tokens=usage["input_tokens"],
        **{
            k: usage[k]
            for k in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
                "response_id",
                "response_model",
                "response_status",
                "output_shape_hash",
            )
        },
        output_item_types=tuple(usage["output_item_types"]),
        output_item_count=2,
        non_tool_output_item_count=1,
    )
    return turn, usage


@contextmanager
def instruction_slot(instruction):
    """Bind the exact wire instruction; ordinary state/history validation stays intact.

    The runtime's managed-history grammar admits JSON state records, not an extra
    developer instruction. Only this one exact trailing item is removed for its
    internal state operations, then restored on every wire request. Both hashes
    are persisted and checked. No other validation or segment boundary is bypassed.
    """
    require(
        instruction.get("role") == "developer" and isinstance(instruction["content"], str),
        "missing frozen developer instruction",
    )
    build = runner._build_model_input

    def metadata(items, **kwargs):
        require(
            items[-1] == instruction and items.count(instruction) == 1,
            "developer instruction changed or duplicated",
        )
        return {
            **history_metadata(items[:-1], **kwargs),
            "uptake_overlay": {
                "instruction_hash": sha256_json(instruction),
                "wire_hash": sha256_json(items),
            },
        }

    def validate(items, meta, **kwargs):
        if "uptake_overlay" not in meta:
            return validate_model_input(items, meta, **kwargs)  # inherited prefix
        require(meta == metadata(items, **kwargs), "wire input or overlay binding changed")
        return validate_model_input(
            items[:-1], {k: v for k, v in meta.items() if k != "uptake_overlay"}, **kwargs
        )

    def assemble(**kwargs):
        items = build(**kwargs)
        require(instruction not in items, "instruction leaked into managed state")
        return [*items, copy.deepcopy(instruction)]

    with (
        patch.object(runner, "history_metadata", metadata),
        patch.object(runner, "validate_model_input", validate),
        patch.object(runner, "_build_model_input", assemble),
    ):
        yield metadata


def restore_branch(
    source,
    cut_sequence,
    selected,
    saved,
    usage,
    row,
    output,
    *,
    provider_free=True,
    credential_file=None,
):
    """Tighten inherited counters, import one pending decision, execute nothing."""
    started = monotonic()
    parent = DevJournal(source.root, source.run_id)
    events, old = parent.events(), parent.load_envelope()
    cut = next(e for e in events if e["sequence"] == cut_sequence)
    bundle = json.loads(
        ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(cut["payload"]["artifact"])
        )
    )
    require(
        {**selected, "input": selected["input"][:-1]} == bundle["request"],
        "saved input differs beyond the frozen B instruction",
    )
    prefix = [e for e in events if e["sequence"] < cut_sequence]
    counters = runner._restore_counters(type("Prefix", (), {"events": lambda _: prefix})())
    accepted = sum(
        e["event_type"] == "action_finished"
        and e["payload"]["result"]["tool"] == "replace_text"
        and e["payload"]["result"]["status"] == "succeeded"
        and e["payload"]["result"].get("error_code") is None
        for e in prefix
    )
    base_ms = bundle["turn"]["active_elapsed_ms"] + row["recorded_sample_active_ms"]
    limits = old.limits.model_copy(
        update={
            "max_model_calls": min(
                old.limits.max_model_calls, counters.model_calls + 1 + row["new_generation_cap"]
            ),
            "max_tool_actions": min(
                old.limits.max_tool_actions,
                counters.tool_actions + row["new_tool_action_cap_including_seed_probe"],
            ),
            "max_accepted_mutations": min(old.limits.max_accepted_mutations, accepted + 1),
            "max_protocol_recoveries": 0,
            "wall_time_seconds": min(old.limits.wall_time_seconds, base_ms // 1000 + 600 + 330),
        }
    )

    def request(**kwargs):
        return DevRunRequest(
            **{
                **kwargs,
                "agent_policy": old.agent_policy,
                "limits": limits,
                "evaluation_reserve_seconds": 330,
            }
        )

    with patch.object(exposure, "DevRunRequest", request):
        branch = exposure._fork(
            source,
            cut_sequence,
            output,
            "B",
            new_cap_usd=Decimal(row["new_cost_cap_usd"]),
            mode="offline-scripted-only" if provider_free else "funded-observation",
            env_file=output / "NO_CREDENTIAL_FILE" if provider_free else credential_file,
            preserve_parent_configuration=True,
        )
    require(
        branch.envelope.probe_image_digest == old.probe_image_digest
        and branch.envelope.probe_profile_hash == old.probe_profile_hash
        and branch.envelope.probe_dependencies == old.probe_dependencies,
        "inherited probe environment changed",
    )
    converted = runner._turn_from_openai(saved, agent_policy=old.agent_policy)
    require(
        converted.error_code is None and len(converted.tool_calls) == 1,
        "saved decision is invalid under the inherited policy",
    )
    runner._validate_continuation_action_order(
        converted.provider_continuation, converted.tool_calls
    )
    continuation = runner._store_provider_continuation(
        branch.store, converted.provider_continuation
    )
    turn = copy.deepcopy(bundle["turn"])
    turn["turn_id"] = "uptake_" + row["sample_id"]
    turn["model_input_artifact"] = native_compaction.put_json(branch.store, selected["input"])
    turn["model_input_hash"] = turn["model_input_artifact"]["content_hash"]
    turn["context_request_sizes"] = segments.request_sizes(selected)
    turn["active_elapsed_ms"] = base_ms + int((monotonic() - started) * 1000)
    with instruction_slot(selected["input"][-1]) as metadata:
        turn["native_history"] = metadata(selected["input"], context_policy=old.context_policy)
    decision = {
        "turn_id": turn["turn_id"],
        "tool_calls": [c.model_dump(mode="json") for c in converted.tool_calls],
        "error_code": None,
        "incomplete_reason": None,
        "tool_contract_failure": None,
        "output_item_count": converted.output_item_count,
        "non_tool_output_item_count": converted.non_tool_output_item_count,
        "output_item_types": converted.output_item_types,
        "output_shape_hash": converted.output_shape_hash,
        "continuation_ref": continuation.model_dump(mode="json"),
        "active_elapsed_ms": turn["active_elapsed_ms"],
    }
    branch.journal.append(
        "uptake_saved_response_imported",
        {
            "cell": row["cell"],
            "sample_id": row["sample_id"],
            "historical_usage": usage,
            "historical_call_consumed": 1,
            "new_provider_calls": 0,
            "new_cost_nanos": 0,
            "saved_request": branch.store.put_json(selected).model_dump(mode="json"),
            "active_elapsed_ms": turn["active_elapsed_ms"],
        },
    )
    branch.journal.append("turn_started", turn)
    # model_call_finished is the existing no-dispatch decision/counter event.
    # Explicit provider label distinguishes this import from mock or live model work.
    branch.journal.append(
        "model_call_finished",
        {**decision, "provider": "saved-response-import", "new_provider_dispatch": False},
    )
    branch.journal.append("turn_decision_recorded", decision)
    with inherited_reads(branch), instruction_slot(selected["input"][-1]):
        runner._validate_recorded_continuations(branch.journal.events(), branch.store)
        runner._load_active_model_input(turn, branch.store, context_policy=old.context_policy)
    branch.row, branch.selected, branch.saved = row, selected, converted
    branch.seed_turn_id, branch.seed_base_ms = turn["turn_id"], base_ms
    branch.parent_actions = counters.tool_actions
    branch.provider_free = provider_free
    return branch
