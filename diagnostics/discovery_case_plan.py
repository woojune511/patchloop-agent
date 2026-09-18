"""Freeze model-authored cases before revealing a candidate; no semantic oracle."""
from __future__ import annotations

import copy
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from patchloop.dev import runner as loop
from patchloop.dev.contracts import EncryptedReasoningContinuationItem
from patchloop.util import canonical_json, sha256_json

MODE = "task-first-v1"
TOOL = "record_case_plan"
EVENT = "discovery_case_plan_frozen"
GUIDANCE = """This review has two stages within one shared call, time and cost budget.
First, the candidate and source tools are withheld. From the complete public task alone,
record up to four concrete cases with record_case_plan. Derive applicability and expected
behavior from literal public requirements, including preservation clauses and exceptions.
Do not assume a candidate's implementation or invent an API you have not inspected.
State unresolved construction or scope in limitations; an empty case list is allowed.
These are concise public test specifications, not private reasoning or verified results.

Recording the cases freezes that initial proposal and reveals the fixed candidate and
read/search/probe tools. Then inspect source, construct and exercise useful cases, and
review actual setup/output against the public task. The initial cases may be wrong or
incomplete: correct them when evidence warrants it and explain changes in the existing
probe question or final limitations. The frozen proposal stays as provenance, not an
authority, a coverage claim, or a requirement to run every case. End with report_discovery.
The instructions below apply to that second stage.

"""


class ProposedCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    case_id: str = Field(min_length=1, max_length=40)
    purpose: Literal["change", "preserve", "boundary"]
    requirement_excerpt: str = Field(min_length=1, max_length=600)
    applicability: str = Field(min_length=1, max_length=300)
    setup: str = Field(min_length=1, max_length=600)
    expected: str = Field(min_length=1, max_length=300)


class CasePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    cases: list[ProposedCase] = Field(max_length=4)
    limitations: str = Field(max_length=600)


def schema() -> dict:
    return {"type": "function", "name": TOOL, "strict": True,
            "description": "Record an initial public-requirement case proposal before seeing "
                           "the candidate. This reveals the candidate for review; the proposal "
                           "is unverified and may be corrected in later public actions.",
            "parameters": CasePlan.model_json_schema()}


def initial_request(review_request: dict) -> dict:
    request = copy.deepcopy(review_request)
    context = json.loads(review_request["input"][1]["content"])
    request["input"] = [
        {"role": "system", "content": GUIDANCE + review_request["input"][0]["content"]},
        {"role": "user", "content": canonical_json({
            "public_task": context["public_task"], "review_limits": context["review_limits"],
            "phase": "design_cases_before_candidate",
        })},
    ]
    request["tools"] = [schema()]
    return request


def bind(plan: CasePlan, public_task) -> dict:
    text = " ".join((public_task.issue.title + " " + public_task.issue.description).split())
    ids = [case.case_id for case in plan.cases]
    return {
        "public_task_hash": sha256_json(public_task.model_dump(mode="json")),
        "requirement_bindings": [
            {"case_id": case.case_id,
             "excerpt_matches_issue": bool(
                 (excerpt := " ".join(case.requirement_excerpt.split())) and excerpt in text)}
            for case in plan.cases
        ],
        "diagnostics": ["duplicate_case_ids"] if len(set(ids)) != len(ids) else [],
        "interpretation_status": "model_authored_unverified", "coverage_status": "not_assessed",
    }


def freeze(session, turn_id, turn, plan: CasePlan, checkpoint) -> None:
    """Persist the proposal before preparing any candidate-containing model input."""
    call = turn.tool_calls[0]
    value = plan.model_dump(mode="json")
    reference = session.store.put_text(canonical_json(value), "application/json")
    receipt = {
        "turn_id": turn_id, "action_id": call.action_id,
        "input_hash": sha256_json({"tool": call.name, "arguments": call.arguments}),
        "plan_hash": sha256_json(value), "plan_artifact": reference.model_dump(mode="json"),
        **bind(plan, session.gateway.public_task),
    }
    session.journal.append(EVENT, receipt)
    checkpoint("case_plan_frozen")
    context = json.loads(session.review_request["input"][1]["content"])
    context.pop("public_task")  # Already present in the immutable first user message.
    public_result = {
        "status": "recorded", "case_plan_hash": receipt["plan_hash"],
        **bind(plan, session.gateway.public_task), "phase": "fixed_candidate_review", **context,
    }
    continuation = (loop._load_provider_continuation(session.store, turn.continuation_ref)
                    if turn.continuation_ref else None)
    function_call = {"type": "function_call", "call_id": call.action_id,
                     "name": call.name, "arguments": canonical_json(call.arguments)}
    exchange = []
    if continuation:
        loop._validate_continuation_action_order(continuation, turn.tool_calls)
        for item in continuation.output_order:
            if isinstance(item, EncryptedReasoningContinuationItem):
                exchange.append({"type": "reasoning", "id": item.id,
                                 "encrypted_content": item.encrypted_content, "summary": [],
                                 **({"status": item.status} if item.status is not None else {})})
            else:
                exchange.append(function_call)
    else:
        exchange.append(function_call)
    exchange.append({"type": "function_call_output", "call_id": call.action_id,
                     "output": canonical_json(public_result)})
    session.items.extend(exchange)
    session.seed["tools"] = copy.deepcopy(session.review_request["tools"])
    session.designing_cases = False
    session.journal.append("discovery_history_advanced", {
        "turn_id": turn_id, "input_hash": sha256_json(session.items),
        "exchange_hash": sha256_json(exchange), "case_plan_hash": receipt["plan_hash"],
    })
    checkpoint("case_plan_history_recorded")
