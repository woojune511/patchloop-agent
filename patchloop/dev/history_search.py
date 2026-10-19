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
MAX_RESULTS = 8
MAX_RESULT_CHARS = 48_000
PASSAGE_CHARS = 1_200
PUBLIC_TOOLS = frozenset({"read_file", "search_files", "replace_text", "run_check",
                          "run_tests", "run_probe"})
INSTRUCTIONS = (
    "When search_history is supplied, you may also request exactly one search_history "
    "call with inspect mode. It searches only public evidence already delivered in this "
    "run, including earlier segments. Use identifiers or an unresolved question to "
    "recover original inputs, setup and results when summaries are insufficient. "
    "It returns up to eight historical candidates within 48,000 result characters, not "
    "direct journal/CAS access. It spends a normal action and model opportunity. "
    "Compare the original caller, environment, inputs and diff before reusing a result. "
    "An old result, supplied observation or model annotation is not proof about the "
    "current candidate. Read current source for edit anchors and use registered checks "
    "for current verification. Incomplete candidates include exact excerpts when space "
    "permits; excerpts cannot establish full execution conditions. Complete bodies have "
    "priority over previews. Metadata-only candidates can also be fetched by ID. "
    "To fetch a candidate separately, pass its exact record_id as query and offset=null. "
    "Large records return a canonical JSON page with next_offset; use that offset with "
    "the same record_id to continue. Use offset=null for keyword searches. Every search "
    "or page is another ordinary action with the same result bound."
)


def contract():
    return {"policy": POLICY, "tool": TOOL, "corpus": "dispatched-public-inputs-v1",
            "ranking": "unicode-identifier-bm25-v1", "max_query_chars": MAX_QUERY_CHARS,
            "max_results": MAX_RESULTS, "max_result_chars": MAX_RESULT_CHARS,
            "excerpt_chars": PASSAGE_CHARS,
            "oversize": "labelled-excerpts-and-exact-id-json-pages", "batch": "singleton-inspect",
            "lookup": "exact-record-id-or-bm25",
            "instructions_hash": sha256_json(INSTRUCTIONS)}


def schema():
    return {"type": "function", "name": TOOL, "strict": True,
            "description": INSTRUCTIONS,
            "parameters": {"type": "object", "additionalProperties": False,
                           "properties": {"query": {"type": "string", "minLength": 1,
                                                     "maxLength": MAX_QUERY_CHARS},
                                          "offset": {"type": ["integer", "null"], "minimum": 0}},
                           "required": ["query", "offset"]}}


def tokens(text):
    # Retain identifiers and also their components, so file paths, snake_case and
    # ordinary prose share terms. No task names, error strings or oracle vocabulary.
    whole = re.findall(r"[^\W_]+(?:[./_-][^\W_]+)*", text.casefold())
    return [part for word in whole for part in dict.fromkeys([word, *re.split(r"[./_-]", word)])
            if len(part) > 1]


def passages(value, path=""):
    """Search individual public fields; keep an exact pointer/range for each excerpt."""
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from passages(child, path + "/" + escaped)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from passages(child, path + f"/{index}")
    elif isinstance(value, str) and value:
        for start in range(0, len(value), PASSAGE_CHARS - 200):
            text = value[start:start + PASSAGE_CHARS]
            yield {"pointer": path, "start": start, "end": start + len(text), "text": text}
            if start + PASSAGE_CHARS >= len(value):
                break


class PublicHistory:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self._seen_turns: set[str] = set()
        self._seen_actions: set[str] = set()
        self._visible: set[str] = set()
        self._passages: dict[str, list] = {}

    def ingest(self, items, *, sequence, turn_id, input_hash):
        from patchloop.dev.conversation import SEGMENT_RULES, reconstruct_state

        state = reconstruct_state(items, context_policy="segmented-v1")
        self._visible = set()
        _, exchanges, observations = SEGMENT_RULES.inventory(items)
        origin = {"first_delivered_sequence": sequence, "turn_id": turn_id,
                  "model_input_hash": input_hash,
                  "delivery_diff_hash": state.get("current_diff", {}).get("patch_hash")}
        calls = {v["call_id"]: v for v in exchanges.values() if v["type"] == "function_call"}
        for value in exchanges.values():
            if value["type"] != "function_call_output":
                continue
            call = calls.get(value["call_id"])
            if not call or call.get("name") not in PUBLIC_TOOLS:
                continue
            arguments = json.loads(call["arguments"])
            # Public model annotations are not execution conditions or evidence.
            arguments = {k: v for k, v in arguments.items()
                         if k not in {"turn_decision", "memory_update"}}
            result = json.loads(value["output"])
            body = {"call": {"action_id": call["call_id"], "tool": call["name"],
                             "arguments": arguments}, "result": result}
            # A handoff may expose only a reduced view of the same action. Only an
            # exact body match makes the original full evidence currently visible.
            self._visible.add(sha256_json(body))
            if call["call_id"] in self._seen_actions:
                continue
            self._add("public_tool_exchange", body, origin, result.get("workspace_diff_hash"))
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
            self._passages[digest] = [
                (p, set(tokens(p["pointer"] + " " + p["text"]))) for p in passages(body)]
        self._visible.add(digest)
        return digest

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

    def rank(self, query):
        """Keep the measured baseline rank; passages locate exact candidate excerpts."""
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
        ranked.sort(key=lambda p: (-p[0], p[1]["origin"]["first_delivered_sequence"],
                                  p[1]["record_id"]))
        excerpts = {}
        for key, ps in self._passages.items():
            if ps:
                best = max(ps, key=lambda p: sum(
                    math.log(1 + n / (1 + frequencies[t])) for t in query_terms & p[1]))
                excerpts[key] = best[0]
        return ranked, excerpts

    def search(self, query, *, current_diff_hash, offset=None):
        if (not isinstance(query, str) or not query.strip()
                or not 1 <= len(query) <= MAX_QUERY_CHARS):
            raise ContractError("search_history query must contain 1-800 characters")
        if offset is not None and (type(offset) is not int or offset < 0
                                   or query not in self.records):
            raise ContractError("history offset requires a known record_id and nonnegative integer")
        ranked, excerpts = self.rank(query) if query not in self.records else ([], {})
        if query in self.records:
            ranked = [(1.0, self.records[query])]
        response = {"policy": POLICY, "query": query, "matched_record_count": len(ranked),
                    "returned_record_limit": MAX_RESULTS, "offset": offset, "records": [],
                    "interpretation_status": "historical_data_not_current_verification"}
        for score, record in ranked[:MAX_RESULTS]:
            row = copy.deepcopy(record)
            row["score"] = round(score, 6)
            row["already_visible"] = record["record_id"] in self._visible
            row["diff_currency"] = ("unknown" if record["observed_diff_hash"] is None else
                                    "same_diff_historical" if record["observed_diff_hash"]
                                    == current_diff_hash else "older_or_different_diff")
            row["body"] = None
            row["delivery"] = "metadata_only_result_bound"
            row["excerpt"] = None
            row["excerpt_is_complete_record"] = False
            response["records"].append(row)
        # Complete evidence has priority over previews of other candidates.
        for row in response["records"]:
            row["body"] = copy.deepcopy(self.records[row["record_id"]]["body"])
            row["delivery"] = "complete"
            if offset is not None or len(canonical_json(response)) > MAX_RESULT_CHARS:
                row["body"] = None
                row["delivery"] = "metadata_only_result_bound"
        for row in response["records"]:
            if row["body"] is None and row["record_id"] in excerpts:
                row["excerpt"] = copy.deepcopy(excerpts[row["record_id"]])
                row["delivery"] = "excerpt_only_result_bound"
                if len(canonical_json(response)) > MAX_RESULT_CHARS:
                    row["excerpt"] = None
                    row["delivery"] = "metadata_only_result_bound"
        if query in self.records and response["records"][0]["body"] is None:
            row = response["records"][0]
            text = canonical_json(self.records[query]["body"])
            start = offset or 0
            if start >= len(text):
                raise ContractError("history offset is beyond the record")
            row["delivery"] = "partial_json_page"
            row["page"] = {"start": start, "end": start, "total_chars": len(text),
                           "next_offset": None, "text": ""}
            low, high = start + 1, len(text)
            while low <= high:
                end = (low + high) // 2
                row["page"].update(end=end, text=text[start:end],
                                   next_offset=end if end < len(text) else None)
                if len(canonical_json(response)) <= MAX_RESULT_CHARS:
                    low = end + 1
                else:
                    high = end - 1
            row["page"].update(end=high, text=text[start:high],
                               next_offset=high if high < len(text) else None)
        return response
