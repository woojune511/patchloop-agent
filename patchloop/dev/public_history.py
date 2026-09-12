"""Pure snapshot lifetimes and exact public evidence, shared with diagnostics.

Only caller-owned snapshots expire. Native exchanges and the supplied seed stay
unchanged; all evidence comes from the supplied input, never a file or provider.
"""
from __future__ import annotations

import copy
import json
from collections import defaultdict
from dataclasses import dataclass

from patchloop.dev.native_sources import _SourceIndex, resolve_source_group
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json

NATIVE = frozenset({"reasoning", "function_call", "function_call_output"})
EXCHANGES = frozenset({"function_call", "function_call_output"})
MUTABLE_FIELDS = frozenset({
    "public_task", "current_diff", "workflow_gate", "remaining_budget",
    "action_horizon", "completion_guidance", "visible_check_status",
    "remaining_visible_check_ids", "mutation_scope_budget", "mutation_readiness",
    "available_tool_names", "commitment_signal", "context_projection",
    "evidence_ledger", "working_notes", "source_index_omitted_count",
    "latest_tool_results_delivery", "recent_attempt_result_next_question",
})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def source_groups(facts):
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


def wire_bytes(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


@dataclass(frozen=True)
class SnapshotRules:
    state_kind: str
    archive_kind: str
    instructions: str
    initial_state_index: int | None = None
    mutable_fields: frozenset[str] = MUTABLE_FIELDS

    def payload(self, item: dict) -> dict | None:
        if item.get("role") != "developer" or not isinstance(item.get("content"), str):
            return None
        try:
            value = json.loads(item["content"])
        except ValueError:
            return None
        if isinstance(value, dict) and value.get("kind") in {self.state_kind, self.archive_kind}:
            return value
        return None

    def observations(self, state):
        for key, value in state.items():
            if key in self.mutable_fields or key == "current_sources":
                continue
            if key == "repair_recheck":
                key, value = "repair_recheck.last_result", value.get("last_result")
            for part in value if isinstance(value, list) else [value]:
                if part is not None:
                    yield {"field": key, "value": part}

    def _entries(self, item, position):
        data = self.payload(item)
        if data is not None:
            public = data.get("referenced_public_exchanges", [])
            if data["kind"] == self.state_kind:
                return (data["state"].get("current_sources", []),
                        self.observations(data["state"]), public)
            return data["sources"], data["observations"], public
        if position == self.initial_state_index:
            state = json.loads(item["content"])
            return state.get("current_sources", []), self.observations(state), []
        return [], (), [item] if item.get("type") in EXCHANGES else []

    def inventory(self, items: list[dict]) -> tuple[dict, dict, dict]:
        """Resolve each view against its preceding visible history, not future deliveries."""
        facts, exchanges, records = {}, {}, {}
        index = _SourceIndex([])
        for position, item in enumerate(items):
            groups, observations, public = self._entries(item, position)
            for record in observations:
                records.setdefault(sha256_json(record), record)
            for exchange in public:
                require(isinstance(exchange, dict) and exchange.get("type") in EXCHANGES,
                        "non-public archive item")
                digest = sha256_json(exchange)
                if digest not in exchanges:
                    exchanges[digest] = exchange
                    index._add(exchange)
            for group in groups:
                try:
                    _, lines, _ = resolve_source_group(group, index)
                except ValueError as exc:
                    raise ContractError(str(exc)) from exc
                for number, line in lines.items():
                    key = group["path"], group["file_hash"], number
                    require(key not in facts or facts[key] == line, "conflicting inline source")
                    facts[key] = line
        require(not index.conflicts, "conflicting observed source")
        for (path, digest), lines in index.observed.items():
            for number, observation in lines.items():
                key, line = (path, digest, number), observation[0]
                require(key not in facts or facts[key] == line, "conflicting inline source")
                facts[key] = line
        return facts, exchanges, records

    def archive(self, exchanges=(), records=(), facts=None):
        return {"role": "developer", "content": canonical_json({
            "kind": self.archive_kind, "instructions": self.instructions,
            "referenced_public_exchanges": list(exchanges),
            "observations": list(records), "sources": source_groups(facts or {}),
        })}

    def compose(self, *, seed: list[dict], saved: list[dict], added: list[dict],
                reentry: dict, policy: str, replace: bool) -> tuple[list[dict], dict]:
        require(saved[:len(seed)] == seed, "compacted seed prefix changed")
        latest = self.payload(reentry)
        require(latest is not None and latest["kind"] == self.state_kind,
                "missing current reentry")
        before = [*saved, *added, reentry]
        removed = [n for n in range(len(seed), len(saved))
                   if replace and (data := self.payload(saved[n])) is not None
                   and data["kind"] == self.state_kind]
        items = before
        archived_lines = archived_exchanges = archived_records = 0
        if removed:
            facts, exchanges, records = self.inventory(before)
            # Gather identities before resolving source references: a retained view
            # may depend on an exchange in a snapshot that still needs rescuing.
            present_exchanges, present_records = {}, {}
            for position, item in enumerate(before):
                if position in removed:
                    continue
                _, observations, public = self._entries(item, position)
                present_exchanges.update((sha256_json(v), v) for v in public)
                present_records.update((sha256_json(v), v) for v in observations)
            replacements = {}
            for position in removed:
                data = self.payload(before[position])
                old_exchanges = {sha256_json(v): v
                                 for v in data.get("referenced_public_exchanges", [])}
                old_records = {sha256_json(v): v for v in self.observations(data["state"])}
                missing_exchanges = {k: v for k, v in old_exchanges.items()
                                     if k not in present_exchanges}
                missing_records = {k: v for k, v in old_records.items() if k not in present_records}
                if missing_exchanges or missing_records:
                    replacements[position] = self.archive(
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
            retained, _, _ = self.inventory(items)
            missing_lines = {key: value for key, value in facts.items() if key not in retained}
            if missing_lines:
                position = removed[0]
                archive = self.payload(replacements.get(position, self.archive()))
                replacements[position] = self.archive(
                    archive["referenced_public_exchanges"], archive["observations"], missing_lines,
                )
                archived_lines = len(missing_lines)
                items = rebuild()
            require((facts, exchanges, records) == self.inventory(items),
                    "snapshot projection lost public evidence")
        require(items[:len(seed)] == seed and items[-1] == reentry, "state/prefix changed")
        require([i for i in items if i.get("type") in NATIVE]
                == [i for i in before if i.get("type") in NATIVE], "native continuation changed")
        return copy.deepcopy(items), {
            "context_policy": policy, "previous_input_hash": sha256_json(saved),
            "unprojected_input_hash": sha256_json(before),
            "projected_input_hash": sha256_json(items),
            "current_reentry_hash": sha256_json(reentry), "removed_snapshot_count": len(removed),
            "rescued_source_lines": archived_lines, "rescued_exchange_items": archived_exchanges,
            "rescued_observations": archived_records,
            "unprojected_input_wire_bytes": wire_bytes(before),
            "projected_input_wire_bytes": wire_bytes(items),
        }
