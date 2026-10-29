"""Bind a completion-prompt experiment without changing runtime policy or history."""
from __future__ import annotations

import copy
from contextlib import contextmanager
from unittest.mock import patch

from diagnostics.checkpoint_continuation import inherited_reads
from diagnostics.decision_sampler import require
from patchloop.dev import completion_context, runner, segments
from patchloop.util import sha256_bytes, sha256_json

SCHEMA = "completion-guidance-v1"
EVENT = "completion_guidance_installed"
BASELINE_PROMPT = completion_context.SYSTEM_PROMPT
PARAGRAPH = (
    "Submission eligibility alone does not settle whether further repair is warranted. "
    "When current public observations conflict with requested behavior, prefer a small "
    "check of the relevant caller, input, or setup before finishing. Missing changed-line "
    "coverage limits what that measurement establishes; examine how the conflicting "
    "behavior arises before deciding whether the candidate is adequate."
)
ANCHOR = "If finish_task is offered,"
require(BASELINE_PROMPT.count(ANCHOR) == 1, "completion prompt insertion anchor changed")
INVESTIGATE_PROMPT = BASELINE_PROMPT.replace(ANCHOR, PARAGRAPH + "\n" + ANCHOR, 1)


def selected_prompt(variant):
    require(variant in {"baseline", "investigate-v1"}, "unknown completion guidance variant")
    return BASELINE_PROMPT if variant == "baseline" else INVESTIGATE_PROMPT


def contract():
    return {
        "schema": SCHEMA,
        **{variant: {"prompt": selected_prompt(variant),
                     "prompt_hash": sha256_bytes(selected_prompt(variant).encode())}
           for variant in ("baseline", "investigate-v1")},
        "intervention": "Only the completion system prompt changes; task, evidence, tools, "
                        "budgets and runtime policies retain their existing contracts.",
    }


def install(branch, variant="investigate-v1"):
    """Append a replacement for an unsent completion seed before attaching feedback."""
    prompt = selected_prompt(variant)
    with branch.journal.execution_lock(), inherited_reads(branch):
        events = branch.journal.events()
        marker = events[branch.inherited_events]
        require(marker["event_type"] == "observation_exposure_fork"
                and sha256_json(marker["payload"]) == branch.marker_hash,
                "completion guidance requires the bound checkpoint fork")
        require(not any(event["event_type"] in {
            "checkpoint_helper_replay_attached", "tool_batch_started", "action_started",
            "input_count_started", "input_count_finished", "provider_call_started",
            "provider_call_finished", "model_input_prepared", "turn_started",
            "turn_decision_recorded", "terminal", EVENT,
        } for event in events[branch.inherited_events + 1:]),
                "completion guidance must precede feedback and provider work")
        binding, handoff = segments.active(
            branch.journal, branch.store,
            boundary_policy=branch.request.segment_boundary_policy,
            agent_policy=branch.request.agent_policy,
        )
        committed, _ = segments.active(branch.journal, branch.store, committed_only=True)
        require(binding is not None and binding != committed
                and segments.is_fresh(branch.journal, binding),
                "uncommitted fresh completion seed required")
        require(completion_context.active(handoff["state"]), "completion seed required")
        expected = runner.segment_seed(
            BASELINE_PROMPT, handoff["state"]["public_task"],
            agent_policy=branch.request.agent_policy, diagnosis=True,
        )
        require(handoff["base"][:3] == expected, "baseline completion seed prefix changed")
        if variant == "baseline":
            branch.completion_guidance = variant
            return {"variant": variant, "changed": False,
                    "prompt_hash": sha256_bytes(prompt.encode())}
        base = copy.deepcopy(handoff["base"])
        base[0]["content"] = prompt + base[0]["content"][len(BASELINE_PROMPT):]
        replacement = segments.start(
            branch.journal, branch.store, base=base, state=copy.deepcopy(handoff["state"]),
            reason=binding["reason"], parent_input_artifact=binding["parent_input_artifact"],
            boundary_policy=branch.request.segment_boundary_policy,
            agent_policy=branch.request.agent_policy, prepare=True, replace_pending=True,
            evidence_manifest=copy.deepcopy(handoff.get("evidence_manifest")),
        )
        require(all(replacement[key] == binding[key] for key in (
            "reason", "cursor", "previous_segment_id", "parent_input_artifact",
            "reviewed_through_sequence", "last_exchange_turn_id", "last_batch_turn_id",
        )), "completion replacement changed checkpoint lineage")
        payload = {
            "schema": SCHEMA, "variant": variant, "contract_hash": sha256_json(contract()),
            "baseline_prompt_hash": sha256_bytes(BASELINE_PROMPT.encode()),
            "prompt_hash": sha256_bytes(prompt.encode()),
            "parent_segment_id": binding["segment_id"],
            "replacement_segment_id": replacement["segment_id"],
            "parent_seed_hash": binding["seed_hash"],
            "replacement_seed_hash": replacement["seed_hash"],
            "replaced_unsent_seed_only": True, "historical_records_unchanged": True,
            "new_provider_calls": 0, "new_target_executions": 0,
        }
        branch.journal.append(EVENT, payload)
        branch.completion_guidance = variant
        return payload


@contextmanager
def activate(branch):
    """Keep later completion entries in the same variant; restore the module on exit."""
    variant = getattr(branch, "completion_guidance", "baseline")
    prompt = selected_prompt(variant)
    if variant == "baseline":
        yield
    else:
        with patch.object(completion_context, "SYSTEM_PROMPT", prompt):
            yield


def assert_pair(baseline, investigate):
    """Compare already time/segment-normalized requests, excluding one exact prompt."""
    left, right = copy.deepcopy(baseline), copy.deepcopy(investigate)
    for request, variant in ((left, "baseline"), (right, "investigate-v1")):
        first = request["input"][0]
        prompt = selected_prompt(variant)
        require(first.get("role") == "system" and isinstance(first.get("content"), str)
                and first["content"].startswith(prompt + "\n"),
                "request completion prompt differs from selected variant")
        first["content"] = BASELINE_PROMPT + first["content"][len(prompt):]
    require(left == right, "comparison differs beyond the exact completion prompt")
    return {"status": "PASS", "only_difference": "completion_system_prompt",
            "common_request_hash": sha256_json(left), "contract_hash": sha256_json(contract())}
