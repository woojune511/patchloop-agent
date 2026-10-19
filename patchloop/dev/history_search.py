"""Bounded search of public evidence already delivered in this one execution.

No journal text search, shell, remote retrieval or interpretation summarizer. The
index is derived from dispatched model-input artifacts and can be rebuilt after
recovery. A result is quoted historical data, never an executable call or PASS.
"""
from __future__ import annotations

import copy
import json
import math
import re
from collections import Counter
from typing import Literal

from patchloop.contracts import Artifact
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json

Policy = Literal["none", "public-v1"]
POLICY = "public-v1"
TOOL = "search_history"
MAX_QUERY_CHARS = 800
MAX_RESULTS = 2
MAX_RESULT_CHARS = 24_000
PUBLIC_TOOLS = frozenset({"read_file", "search_files", "replace_text", "run_check",
                          "run_tests", "run_probe"})
INSTRUCTIONS = (
    "When search_history is supplied, you may also request exactly one search_history "
    "call with inspect mode. It searches only public evidence already delivered in this "
    "run, including earlier segments. Use identifiers or an unresolved question to "
    "recover original inputs, setup and results when summaries are insufficient. "
    "It returns at most two quoted historical records within a bounded result, not "
    "direct journal/CAS access. It spends a normal action and model opportunity. "
    "Compare the original caller, environment, inputs and diff before reusing a result. "
    "An old result, supplied observation or model annotation is not proof about the "
    "current candidate. Read current source for edit anchors and use registered checks "
    "for current verification. Missing/oversized records are explicitly not delivered."
    " To fetch one identified record separately, pass its exact record_id as query; "
    "this is another ordinary action with the same result bound."
)


def contract():
    return {"policy": POLICY, "tool": TOOL, "corpus": "dispatched-public-inputs-v1",
            "ranking": "unicode-identifier-bm25-v1", "max_query_chars": MAX_QUERY_CHARS,
            "max_results": MAX_RESULTS, "max_result_chars": MAX_RESULT_CHARS,
            "oversize": "metadata-only-never-partial-body", "batch": "singleton-inspect",
            "lookup": "exact-record-id-or-bm25",
            "instructions_hash": sha256_json(INSTRUCTIONS)}


def schema():
    return {"type": "function", "name": TOOL, "strict": True,
            "description": INSTRUCTIONS,
            "parameters": {"type": "object", "additionalProperties": False,
                           "properties": {"query": {"type": "string", "minLength": 1,
                                                     "maxLength": MAX_QUERY_CHARS}},
                           "required": ["query"]}}


def tokens(text):
    # Retain identifiers and also their components, so file paths, snake_case and
    # ordinary prose share terms. No task names, error strings or oracle vocabulary.
    whole = re.findall(r"[^\W_]+(?:[./_-][^\W_]+)*", text.casefold())
    return [part for word in whole for part in dict.fromkeys([word, *re.split(r"[./_-]", word)])
            if len(part) > 1]


class PublicHistory:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self._seen_turns: set[str] = set()
        self._seen_actions: set[str] = set()

    def ingest(self, items, *, sequence, turn_id, input_hash):
        from patchloop.dev.conversation import SEGMENT_RULES, reconstruct_state

        state = reconstruct_state(items, context_policy="segmented-v1")
        _, exchanges, observations = SEGMENT_RULES.inventory(items)
        origin = {"first_delivered_sequence": sequence, "turn_id": turn_id,
                  "model_input_hash": input_hash,
                  "delivery_diff_hash": state.get("current_diff", {}).get("patch_hash")}
        calls = {v["call_id"]: v for v in exchanges.values() if v["type"] == "function_call"}
        for value in exchanges.values():
            if value["type"] != "function_call_output":
                continue
            call = calls.get(value["call_id"])
            if (not call or call.get("name") not in PUBLIC_TOOLS
                    or call["call_id"] in self._seen_actions):
                continue
            arguments = json.loads(call["arguments"])
            # Public model annotations are not execution conditions or evidence.
            arguments = {k: v for k, v in arguments.items()
                         if k not in {"turn_decision", "memory_update"}}
            result = json.loads(value["output"])
            body = {"call": {"action_id": call["call_id"], "tool": call["name"],
                             "arguments": arguments}, "result": result}
            self._add("public_tool_exchange", body, origin,
                      result.get("workspace_diff_hash"))
            self._seen_actions.add(call["call_id"])
        for observation in observations.values():
            # SnapshotRules excludes mutable notes/plans, budgets and status. These
            # are supplied observations, not our certification of their contents.
            self._add("supplied_public_observation", observation, origin, None)

    def _add(self, kind, body, origin, diff_hash):
        digest = sha256_json(body)
        if digest not in self.records:
            self.records[digest] = {
                "record_id": digest, "kind": kind, "origin": copy.deepcopy(origin),
                "observed_diff_hash": diff_hash, "body": copy.deepcopy(body),
            }

    def sync(self, events, store, *, before_sequence, check_deadline=lambda: None):
        from patchloop.dev.conversation import validate_model_input

        # A prepared/count-only input was never delivered. Rebuild from the same
        # durable dispatch boundary for both ordinary execution and crash recovery.
        past = [e for e in events if e["sequence"] < before_sequence]
        sent = {e["payload"]["turn_id"] for e in past
                if e["event_type"] in {"provider_call_started", "model_call_finished"}}
        for event in past:
            if event["event_type"] != "turn_started":
                continue
            turn = event["payload"]
            turn_id = turn["turn_id"]
            if turn_id not in sent or turn_id in self._seen_turns:
                continue
            check_deadline()
            artifact = Artifact.model_validate(turn["model_input_artifact"])
            if artifact.content_hash != turn["model_input_hash"]:
                raise RecoveryError("history input artifact identity mismatch")
            items = json.loads(store.read_bytes(artifact))
            validate_model_input(items, turn["native_history"], context_policy="segmented-v1")
            self.ingest(items, sequence=event["sequence"], turn_id=turn_id,
                        input_hash=turn["model_input_hash"])
            self._seen_turns.add(turn_id)

    def search(self, query, *, current_diff_hash):
        if (not isinstance(query, str) or not query.strip()
                or not 1 <= len(query) <= MAX_QUERY_CHARS):
            raise ContractError("search_history query must contain 1-800 characters")
        query_terms = set(tokens(query))
        documents = [(record, Counter(tokens(canonical_json(record["body"]))))
                     for record in self.records.values()]
        n = len(documents)
        mean_length = sum(sum(counts.values()) for _, counts in documents) / max(n, 1)
        frequencies = Counter(term for _, counts in documents for term in counts)
        ranked = []
        for record, counts in documents:
            length = sum(counts.values())
            score = sum(
                math.log(1 + (n - frequencies[term] + .5) / (frequencies[term] + .5))
                * counts[term] * 2.2
                / (counts[term] + 1.2 * (.25 + .75 * length / max(mean_length, 1)))
                for term in sorted(query_terms) if term in counts)
            if score > 0:
                ranked.append((score, record))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]["origin"]["first_delivered_sequence"],
                                     pair[1]["record_id"]))
        if query in self.records:
            ranked = [(1.0, self.records[query])]
        response = {"policy": POLICY, "query": query, "matched_record_count": len(ranked),
                    "returned_record_limit": MAX_RESULTS, "records": [],
                    "interpretation_status": "historical_data_not_current_verification"}
        for score, record in ranked[:MAX_RESULTS]:
            row = copy.deepcopy(record)
            row["score"] = round(score, 6)
            row["diff_currency"] = ("unknown" if record["observed_diff_hash"] is None else
                                    "same_diff_historical" if record["observed_diff_hash"]
                                    == current_diff_hash else "older_or_different_diff")
            row["body"] = None
            row["delivery"] = "metadata_only_result_bound"
            response["records"].append(row)
        # Reserve both records' metadata before admitting complete bodies.
        for row in response["records"]:
            row["body"] = copy.deepcopy(self.records[row["record_id"]]["body"])
            row["delivery"] = "complete"
            if len(canonical_json(response)) > MAX_RESULT_CHARS:
                row["body"] = None
                row["delivery"] = "metadata_only_result_bound"
        return response
