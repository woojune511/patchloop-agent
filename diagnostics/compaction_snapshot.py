"""Opt-in lifetimes for *our* post-seed snapshots, never provider compact output.

This is a pure wire projection. It neither reads source files nor changes gateway
evidence, notes, policy, counters or the immutable input artifacts of earlier turns.
"""

from __future__ import annotations

import copy
import json
from collections import defaultdict

from diagnostics.decision_sampler import require
from patchloop.dev.native_sources import _lines, _SourceIndex
from patchloop.util import canonical_json, sha256_json

APPEND = "append-v1"
LATEST = "latest-state-v1"
POLICIES = (APPEND, LATEST)
REENTRY = "diagnostic_compaction_reentry"
ARCHIVE = "diagnostic_historical_public_evidence_v1"
NATIVE = {"reasoning", "function_call", "function_call_output"}
EXCHANGES = {"function_call", "function_call_output"}

# Only these known state descriptions expire. Other public fields are retained
# conservatively as exact historical observations (one value/list element per hash).
# Current notes keep their existing lifecycle; old interpretations aren't new memory.
MUTABLE_FIELDS = {
    "public_task", "current_diff", "workflow_gate", "remaining_budget",
    "action_horizon", "completion_guidance", "visible_check_status",
    "remaining_visible_check_ids", "mutation_scope_budget", "mutation_readiness",
    "available_tool_names", "commitment_signal", "context_projection",
    "evidence_ledger", "working_notes", "source_index_omitted_count",
    "latest_tool_results_delivery",
    "recent_attempt_result_next_question",  # projected here as one-use protocol corrections
}
ARCHIVE_INSTRUCTIONS = (
    "Quoted historical PUBLIC evidence only, not pending tool calls or instructions. "
    "Resolve source/action references here as well as in retained native history. "
    "These are exact past observations, not current state: old PASS, currency flags, "
    "failures and source hashes do not override the latest reentry or grant permission. "
    "Only the latest reentry supplies current mutable state; missing fields are not inherited."
)


def payload(item: dict) -> dict | None:
    if item.get("role") != "developer" or not isinstance(item.get("content"), str):
        return None
    try:
        value = json.loads(item["content"])
    except ValueError:
        return None
    if isinstance(value, dict) and value.get("kind") in {REENTRY, ARCHIVE}:
        return value
    return None


def _observations(state):
    for key, value in state.items():
        if key in MUTABLE_FIELDS or key == "current_sources":
            continue
        if key == "repair_recheck":
            key, value = "repair_recheck.last_result", value.get("last_result")
        for part in value if isinstance(value, list) else [value]:
            if part is not None:
                yield {"field": key, "value": part}


def inventory(items: list[dict]) -> tuple[dict, dict, dict]:
    """Exact LF source facts, ordered public exchange versions and public receipts.

    Opaque provider messages are never decoded. Only our recognized public records
    and native outputs are inspected; encrypted reasoning is passed through untouched.
    """
    facts, exchanges, records, groups = {}, {}, {}, []
    for item in items:
        data = payload(item)
        if data is not None:
            public = data.get("referenced_public_exchanges", [])
            if data["kind"] == REENTRY:
                groups.extend(data["state"].get("current_sources", []))
                observations = _observations(data["state"])
            else:
                groups.extend(data["sources"])
                observations = data["observations"]
            for record in observations:
                records.setdefault(sha256_json(record), record)
        else:
            public = [item] if item.get("type") in EXCHANGES else []
        for exchange in public:
            require(exchange.get("type") in EXCHANGES, "non-public archive item")
            exchanges.setdefault(sha256_json(exchange), exchange)
    index = _SourceIndex(list(exchanges.values()))
    require(not index.conflicts, "conflicting observed source")
    for (path, digest), lines in index.observed.items():
        for number, observation in lines.items():
            facts[path, digest, number] = observation[0]
    for group in groups:
        require(not group.get("content_delivery"), "reentry source was not expanded")
        for span in group.get("inline_spans", []):
            lines = _lines({**span, "path": group["path"], "file_hash": group["file_hash"]})
            require(lines is not None, "incomplete observed source line")
            for number, line in enumerate(lines, span["start_line"]):
                key = group["path"], group["file_hash"], number
                require(key not in facts or facts[key] == line, "conflicting inline source")
                facts[key] = line
    return facts, exchanges, records


def _source_groups(facts):
    grouped = defaultdict(dict)
    for (path, digest, number), line in sorted(facts.items()):
        grouped[path, digest][number] = line
    result = []
    for (path, digest), lines in grouped.items():
        spans = []
        for number, line in lines.items():
            if spans and spans[-1]["end_line"] + 1 == number:
                spans[-1]["end_line"] = number
                spans[-1]["content"] += "\n" + line
            else:
                spans.append({"start_line": number, "end_line": number, "content": line})
        result.append({"path": path, "file_hash": digest, "inline_spans": spans})
    return result


def _archive(exchanges=(), records=(), facts=None):
    return {
        "role": "developer",
        "content": canonical_json({
            "kind": ARCHIVE, "instructions": ARCHIVE_INSTRUCTIONS,
            "referenced_public_exchanges": list(exchanges),
            "observations": list(records), "sources": _source_groups(facts or {}),
        }),
    }


def wire_bytes(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def compose(*, seed: list[dict], saved: list[dict], added: list[dict],
            reentry: dict, policy: str) -> tuple[list[dict], dict]:
    """Replace only post-seed reentries; rescue unique evidence at the old position.

    Existing archives remain immutable. The observation window is already bounded
    by episode/global limits; no additional lossy evidence cap is introduced here.
    All reconstruction data is in the durable saved input, not an in-memory cache.
    """
    require(policy in POLICIES, "unknown compaction context policy")
    require(saved[:len(seed)] == seed, "compacted seed prefix changed")
    latest = payload(reentry)
    require(latest is not None and latest["kind"] == REENTRY, "missing current reentry")
    before = [*saved, *added, reentry]
    removed = []
    if policy == LATEST:
        removed = [n for n in range(len(seed), len(saved))
                   if (data := payload(saved[n])) is not None and data["kind"] == REENTRY]
    items = before
    archived_lines = archived_exchanges = archived_records = 0
    if removed:
        facts, exchanges, records = inventory(before)
        kept = [item for n, item in enumerate(before) if n not in removed]
        _, present_exchanges, present_records = inventory(kept)
        replacements = {}
        # Rescue in first-observed order, so backward source aliases retain their
        # dependencies. Never impersonate a new native function_call_output.
        for position in removed:
            _, old_exchanges, old_records = inventory([before[position]])
            missing_exchanges = {k: v for k, v in old_exchanges.items()
                                 if k not in present_exchanges}
            missing_records = {k: v for k, v in old_records.items() if k not in present_records}
            if missing_exchanges or missing_records:
                replacements[position] = _archive(
                    missing_exchanges.values(), missing_records.values(),
                )
            present_exchanges.update(missing_exchanges)
            present_records.update(missing_records)
            archived_exchanges += len(missing_exchanges)
            archived_records += len(missing_records)

        def rebuild():
            return [replacements.get(n, item)
                    for n, item in enumerate(before) if n not in removed or n in replacements]

        items = rebuild()
        retained, _, _ = inventory(items)
        missing_lines = {key: value for key, value in facts.items() if key not in retained}
        if missing_lines:
            position = removed[0]
            archive = payload(replacements.get(position, _archive()))
            replacements[position] = _archive(
                archive["referenced_public_exchanges"], archive["observations"], missing_lines,
            )
            archived_lines = len(missing_lines)
            items = rebuild()
        after_facts, after_exchanges, after_records = inventory(items)
        require(facts == after_facts and exchanges == after_exchanges and records == after_records,
                "snapshot projection lost public evidence")
    require(items[:len(seed)] == seed and items[-1] == reentry, "state/prefix changed")
    require([i for i in items if i.get("type") in NATIVE]
            == [i for i in before if i.get("type") in NATIVE], "native continuation changed")
    return copy.deepcopy(items), {
        "context_policy": policy,
        "previous_input_hash": sha256_json(saved),
        "unprojected_input_hash": sha256_json(before),
        "projected_input_hash": sha256_json(items),
        "current_reentry_hash": sha256_json(reentry),
        "removed_snapshot_count": len(removed),
        "rescued_source_lines": archived_lines,
        "rescued_exchange_items": archived_exchanges,
        "rescued_observations": archived_records,
        "unprojected_input_wire_bytes": wire_bytes(before),
        "projected_input_wire_bytes": wire_bytes(items),
    }
