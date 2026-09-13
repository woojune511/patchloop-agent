"""Compaction response validation shared by runtime handoff and diagnostics.

Only already-public retained messages/actions and opaque encrypted state may be
persisted. Validation rejects the entire window; it never strips provider output.
"""
from __future__ import annotations

import copy
import re
from collections import Counter

from patchloop.errors import ContractError


def require(condition, message):
    if not condition:
        raise ContractError(message)


def message_identity(item: dict) -> tuple[str, str]:
    require(set(item) <= {"id", "type", "role", "content", "status", "phase"}
            and item.get("role") in {"system", "developer", "user", "assistant"},
            "unsupported retained message")
    require(item.get("phase") in (None, "commentary", "final"),
            "unsupported retained phase")
    content = item.get("content")
    require(isinstance(content, (str, list)), "unsupported message content")
    if isinstance(content, list):
        for part in content:
            require(isinstance(part, dict)
                    and set(part) <= {"type", "text", "annotations", "logprobs"}
                    and part.get("type") in {"input_text", "output_text"}
                    and isinstance(part.get("text"), str)
                    and not part.get("annotations") and not part.get("logprobs"),
                    "unsupported retained content")
        content = "".join(part["text"] for part in content)
    return item["role"], content


def usage_fields(response: dict) -> dict:
    raw = response.get("usage")
    require(isinstance(raw, dict), "missing compaction usage")
    keys = ("input_tokens", "output_tokens", "total_tokens")
    usage = {k: raw.get(k) for k in keys}
    for section, fields in (
        ("input_tokens_details", ("cached_tokens", "cache_write_tokens")),
        ("output_tokens_details", ("reasoning_tokens",)),
    ):
        details = raw.get(section)
        require(isinstance(details, dict), "missing usage details")
        # cache_write_tokens is absent in older SDK responses, not assumed zero.
        usage[section] = {k: details[k] for k in fields if k in details}
    numbers = [usage[k] for k in keys]
    numbers += [n for k in ("input_tokens_details", "output_tokens_details")
                for n in usage[k].values()]
    require(all(type(n) is int and n >= 0 for n in numbers), "invalid token usage")
    require(usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"],
            "inconsistent total usage")
    require(0 <= usage["input_tokens_details"].get("cached_tokens", -1) <= usage["input_tokens"]
            and 0 <= usage["output_tokens_details"].get("reasoning_tokens", -1)
            <= usage["output_tokens"], "inconsistent detailed usage")
    return usage


def validated_window(response: dict, original: list[dict]) -> list[dict]:
    require(response.get("object") == "response.compaction", "not a compaction response")
    output = response.get("output")
    require(isinstance(output, list) and output, "missing compacted window")
    originals = {(i.get("type"), i.get("call_id")): i for i in original
                 if i.get("type") in {"function_call", "function_call_output"}}
    messages = Counter(message_identity(i) for i in original
                       if i.get("type", "message" if "role" in i else None) == "message")
    ids, calls, results = set(), [], []
    compactions = 0
    for item in output:
        require(isinstance(item, dict), "invalid output item")
        if "id" in item:
            identifier = item["id"]
            require(isinstance(identifier, str) and re.fullmatch(r"[\w-]{1,256}", identifier)
                    and identifier not in ids, "invalid or duplicate output identity")
            ids.add(identifier)
        require(item.get("status") in (None, "in_progress", "completed", "incomplete"),
                "unsupported retained status")
        kind = item.get("type", "message" if "role" in item else None)
        if kind in {"compaction", "reasoning"}:
            allowed = {"id", "type", "encrypted_content"}
            if kind == "reasoning":
                allowed |= {"status", "summary"}
            require(set(item) <= allowed and item.get("summary", []) == [],
                    "plaintext reasoning or unknown opaque fields")
            require("id" in item and isinstance(item.get("encrypted_content"), str)
                    and bool(item["encrypted_content"]), "missing encrypted content")
            compactions += kind == "compaction"
        elif kind in {"function_call", "function_call_output"}:
            previous = originals.get((kind, item.get("call_id")))
            fields = ("call_id", "name", "arguments") if kind == "function_call" else (
                "call_id", "output",
            )
            require(previous is not None and set(item) <= {*fields, "id", "type", "status"}
                    and all(item.get(k) == previous.get(k) for k in fields),
                    "compaction changed or invented a public action")
            (calls if kind == "function_call" else results).append(item["call_id"])
            require(kind != "function_call_output" or item["call_id"] in calls,
                    "retained result precedes its call")
        elif kind == "message":
            key = message_identity(item)
            require(messages[key] > 0, "compaction changed or invented a public message")
            messages[key] -= 1
        else:
            raise ContractError("unsupported compaction output item")
    require(compactions > 0, "no compaction item returned")
    require(calls == results and len(set(calls)) == len(calls),
            "retained public actions are not complete ordered pairs")
    # Never salvage by stripping summaries or dropping unfamiliar items.
    return copy.deepcopy(output)
