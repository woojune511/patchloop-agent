"""Durable standalone-compaction result handoff, with no network or task executor.

A future, separately approved collector can reserve an attempt, call compact once,
then record its response. Recovery only consumes durable data; an unresolved attempt
is UNKNOWN, never permission to retry. This module does not grant cost admission.
"""
from __future__ import annotations

import copy
import json
import re
import uuid
from pathlib import Path

from diagnostics import compaction_replay as design
from diagnostics.decision_sampler import read_source_artifact, require
from patchloop.agent.compaction import (
    usage_fields as usage_fields,
)
from patchloop.agent.compaction import (
    validated_window as validated_window,
)
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


def request_metrics(request: dict) -> dict:
    items = request["input"]
    ciphertext = [i["encrypted_content"] for i in items if "encrypted_content" in i]
    return {
        "canonical_request_bytes": len(canonical_json(request).encode()),
        "input_item_count": len(items),
        "reasoning_item_count": sum(i.get("type") == "reasoning" for i in items),
        "compaction_item_count": sum(i.get("type") == "compaction" for i in items),
        "encrypted_chars": sum(map(len, ciphertext)),
        "encrypted_utf8_bytes": sum(len(s.encode()) for s in ciphertext),
        "largest_encrypted_chars": max(map(len, ciphertext), default=0),
    }


def next_requests(values: dict, window: list[dict]) -> tuple[dict, dict]:
    request = copy.deepcopy(values["control"])
    request["input"] = [*copy.deepcopy(window), *copy.deepcopy(values["reentry"])]
    require(request["input"][:len(window)] == window, "compacted output changed")
    return request, OpenAIResponsesAdapter._count_payload(request)


def reserve(packet_root: Path, packet_hash: str, output: Path) -> dict:
    """Persist intent only. No credential, client, cost admission or dispatch occurs."""
    packet, _ = design.verify(packet_root, packet_hash)
    output = design.new_external_root(output, packet_root, Path(packet["source_root"]))
    output.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(output, "run_dev_compaction_" + uuid.uuid4().hex[:16])
    binding = {"schema_version": design.SCHEMA, "packet_root": str(packet_root.resolve()),
               "packet_hash": packet_hash, "run_id": journal.run_id}
    ArtifactStore(output).write_text_immutable(output / "trial.json", canonical_json(binding))
    journal.append("compaction_attempt_reserved", {
        "packet_hash": packet_hash, "request_artifact": packet["artifacts"]["compact"],
        "cost_admission": "NOT_GRANTED_BY_THIS_MODULE",
    })
    return binding


def _load(root: Path):
    binding = json.loads((root / "trial.json").read_bytes())
    require(binding["schema_version"] == design.SCHEMA, "trial schema mismatch")
    packet, values = design.verify(Path(binding["packet_root"]), binding["packet_hash"])
    journal = DevJournal(root, binding["run_id"])
    events = journal.events()
    require(events and events[0]["event_type"] == "compaction_attempt_reserved"
            and events[0]["payload"]["packet_hash"] == binding["packet_hash"]
            and events[0]["payload"]["request_artifact"] == packet["artifacts"]["compact"],
            "trial reservation mismatch")
    return packet, values, journal


def record_response(root: Path, response) -> dict:
    """Validate before persistence; retain usage even when the output is rejected."""
    _, values, journal = _load(root)
    with journal.execution_lock():
        require(len(journal.events()) == 1 and not (root / "receipt.json").exists(),
                "attempt already resolved; use recover, not a second response")
        if hasattr(response, "model_dump"):
            # SDK union-serialization warnings may contain response text. Validation
            # below is authoritative; do not emit those warnings into logs/traces.
            response = response.model_dump(mode="json", exclude_unset=True, warnings=False)
        require(isinstance(response, dict), "invalid compaction response object")
        usage, error, window = None, None, None
        try:
            usage = usage_fields(response)
        except (ContractError, TypeError, ValueError):
            error = "COMPACTION_USAGE_ERROR"
        if error is None:
            try:
                window = validated_window(response, values["control"]["input"])
            except (ContractError, TypeError, ValueError):
                error = "COMPACTION_OUTPUT_CONTRACT_ERROR"
        receipt = {
            "status": error or "READY_FOR_REVIEW", "usage": usage,
            "response_id": (response.get("id") if isinstance(response.get("id"), str)
                            and re.fullmatch(r"resp_[A-Za-z0-9_-]{1,240}", response["id"])
                            else None),
            "compaction_cost_usd": None, "next_input_tokens": None,
            "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN", "official": False,
            "automatic_generation_requests": 0, "tool_executions": 0,
        }
        if error is None:
            store = ArtifactStore(root / "artifacts")
            request, count = next_requests(values, window)
            receipt.update(
                window_artifact=design.put_json(store, window),
                next_request_artifact=design.put_json(store, request),
                next_count_artifact=design.put_json(store, count),
                window_hash=sha256_json(window),
                before=request_metrics(values["control"]), after=request_metrics(request),
            )
        # The receipt is the durable completion boundary. A crash before it is
        # UNKNOWN, even if an orphan CAS object exists. A crash after it is replayable.
        ArtifactStore(root).write_text_immutable(root / "receipt.json", canonical_json(receipt))
        journal.append("compaction_result_recorded", {"receipt_hash": sha256_json(receipt)})
        return receipt


def recover(root: Path) -> dict:
    """Idempotent durable recovery, never compaction/count/generation/tool dispatch."""
    _, values, journal = _load(root)
    with journal.execution_lock():
        events = journal.events()
        terminal = [e["payload"] for e in events if e["event_type"] == "terminal"]
        if terminal:
            return terminal[0]
        path = root / "receipt.json"
        if not path.exists():
            require(len(events) == 1, "durable compaction receipt is missing")
            result = {"status": "COMPACTION_OUTCOME_UNKNOWN", "usage": None,
                      "compaction_cost_usd": None, "official": False,
                      "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN"}
            journal.append("terminal", result)
            return result
        require(not path.is_symlink(), "invalid receipt path")
        receipt = json.loads(path.read_bytes())
        base_keys = {"status", "usage", "response_id", "compaction_cost_usd", "next_input_tokens",
                     "task_acceptance", "safety_state", "official", "automatic_generation_requests",
                     "tool_executions"}
        result_keys = {"window_artifact", "next_request_artifact", "next_count_artifact",
                       "window_hash", "before", "after"}
        require(set(receipt) == (base_keys | result_keys if receipt.get("status")
                                == "READY_FOR_REVIEW" else base_keys), "invalid receipt fields")
        require(receipt.get("official") is False
                and receipt.get("compaction_cost_usd") is None
                and receipt.get("next_input_tokens") is None
                and receipt.get("task_acceptance") == receipt.get("safety_state") == "NOT_RUN"
                and receipt.get("automatic_generation_requests") == receipt.get("tool_executions")
                == 0, "invalid diagnostic receipt boundary")
        require((receipt["usage"] is None) == (receipt["status"] == "COMPACTION_USAGE_ERROR"),
                "receipt usage status mismatch")
        if receipt.get("usage") is not None:
            require(usage_fields(receipt) == receipt["usage"], "invalid receipt usage")
        recorded = [e for e in events if e["event_type"] == "compaction_result_recorded"]
        require(len(recorded) <= 1 and (not recorded or recorded[0]["payload"] == {
            "receipt_hash": sha256_json(receipt),
        }), "receipt identity mismatch")
        if receipt["status"] == "READY_FOR_REVIEW":
            window = json.loads(read_source_artifact(root, receipt["window_artifact"]))
            validated_window({"object": "response.compaction", "output": window},
                             values["control"]["input"])
            require(sha256_json(window) == receipt["window_hash"], "window hash mismatch")
            request, count = next_requests(values, window)
            for key, value in (("next_request", request), ("next_count", count)):
                require(read_source_artifact(root, receipt[key + "_artifact"])
                        == canonical_json(value).encode(), "replayed request mismatch")
            require(receipt["before"] == request_metrics(values["control"])
                    and receipt["after"] == request_metrics(request), "size metrics mismatch")
        require(receipt["status"] in {"READY_FOR_REVIEW", "COMPACTION_USAGE_ERROR",
                                     "COMPACTION_OUTPUT_CONTRACT_ERROR"}, "invalid receipt status")
        if not recorded:
            journal.append("compaction_result_recorded", {"receipt_hash": sha256_json(receipt)})
        return receipt
