"""One durable compaction handoff, separate from policy and window activation.

Only execute() accepts an explicitly supplied, owned client factory. Preparation
and recovery cannot count, generate, load credentials or execute retained actions.
The optional runner composes locked methods inside its run-lifetime lock. Its
caller must authorize the exact run and conditional cost assumption first.
"""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal

from patchloop.agent.compaction import require, usage_fields, validated_window
from patchloop.agent.request_transport import exception_evidence
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import compaction_cost as cost
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import runtime_content_hash
from patchloop.util import canonical_json, sha256_json

REQUEST_SECONDS = 300.0
CLEANUP_SECONDS = 5.0
EVENTS = (
    "compaction_prepared",
    "compaction_started",
    "compaction_usage_recorded",
    "compaction_response_recorded",
    "compaction_request_failed",
    "compaction_cleanup_recorded",
    "compaction_finished",
)


def _elapsed(value):
    require(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        "invalid compaction active elapsed time",
    )
    return value


def _plain(value):
    # SDK union serialization warnings can contain response bodies.
    return (
        value.model_dump(mode="json", exclude_unset=True, warnings=False)
        if (hasattr(value, "model_dump"))
        else value
    )


class CompactionAdapter:
    """Run-scoped, once-only response storage with the existing execution lock."""

    def __init__(self, journal: DevJournal, *, policy_hash: str):
        require(
            isinstance(policy_hash, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", policy_hash),
            "invalid compaction policy hash",
        )
        self.journal = journal
        self.store = ArtifactStore(journal.root / "artifacts")
        self.policy_hash = policy_hash
        self.receipt_path = self.store.root / "compaction" / f"{journal.run_id}.json"

    def _read(self, ref):
        try:
            return json.loads(self.store.read_bytes(Artifact.model_validate(ref)))
        except (ValueError, TypeError) as exc:
            raise RecoveryError("invalid compaction artifact") from exc

    def _put(self, value):
        return self.store.put_text(canonical_json(value), "application/json").model_dump(
            mode="json"
        )

    def _events(self):
        result = {}
        for event in self.journal.events():
            name = event["event_type"]
            if name in EVENTS:
                if name in result:
                    raise RecoveryError("duplicate compaction event")
                result[name] = event["payload"]
        return result

    def prepare(
        self,
        *,
        source_input: Artifact,
        source_seed: Artifact,
        boundary_id: str,
        ledger: DevCostLedger,
        accept_model_limit_reservation: bool,
        active_elapsed_seconds: float,
    ) -> dict:
        """Persist source/cost identity; no client is available on this path."""
        require(
            accept_model_limit_reservation is True,
            "compaction requires acknowledgement of its conditional reservation",
        )
        require(
            isinstance(boundary_id, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", boundary_id),
            "invalid compaction boundary ID",
        )
        with self.journal.execution_lock():
            return self.prepare_locked(
                source_input=source_input,
                source_seed=source_seed,
                boundary_id=boundary_id,
                ledger=ledger,
                accept_model_limit_reservation=accept_model_limit_reservation,
                active_elapsed_seconds=active_elapsed_seconds,
            )

    def prepare_locked(
        self,
        *,
        source_input: Artifact,
        source_seed: Artifact,
        boundary_id: str,
        ledger: DevCostLedger,
        accept_model_limit_reservation: bool,
        active_elapsed_seconds: float,
    ) -> dict:
        """Persist source/cost identity; no client is available on this path."""
        require(
            accept_model_limit_reservation is True,
            "compaction requires acknowledgement of its conditional reservation",
        )
        require(
            isinstance(boundary_id, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", boundary_id),
            "invalid compaction boundary ID",
        )
        self.journal.require_execution_lock()
        require(self.journal.terminal() is None, "terminal run cannot prepare compaction")
        items, seed = self._read(source_input), self._read(source_seed)
        require(
            isinstance(items, list)
            and all(isinstance(i, dict) for i in items)
            and isinstance(seed, list)
            and bool(seed)
            and items[: len(seed)] == seed,
            "source window does not contain the exact seed",
        )
        request = {"model": cost.MODEL, "input": items, "service_tier": "default"}
        binding = {
            "kind": "native-compaction-attempt-v1",
            "run_id": self.journal.run_id,
            "boundary_id": boundary_id,
            "policy_hash": self.policy_hash,
            "runtime_hash": runtime_content_hash(),
            "source_input": source_input.model_dump(mode="json"),
            "source_seed": source_seed.model_dump(mode="json"),
            "request_hash": sha256_json(request),
            "cost_contract": cost.CONTRACT,
            "cost_contract_hash": sha256_json(cost.CONTRACT),
            "reservation": cost.reserve_from_ledger(ledger),
            "accept_model_limit_reservation": True,
            "active_elapsed_seconds": _elapsed(active_elapsed_seconds),
            "request_seconds": REQUEST_SECONDS,
            "cleanup_reserve_seconds": CLEANUP_SECONDS,
        }
        existing = self._events().get("compaction_prepared")
        if existing is not None:
            require(existing == binding, "compaction preparation contract mismatch")
            return existing
        require(
            not self._events() and not self.receipt_path.exists(),
            "compaction preparation is missing",
        )
        self.journal.append("compaction_prepared", binding)
        return binding

    def _load(self):
        events = self._events()
        binding = events.get("compaction_prepared")
        if binding is None:
            if events or self.receipt_path.exists():
                raise RecoveryError("compaction preparation is missing")
            return events, None, None
        require(
            binding["policy_hash"] == self.policy_hash
            and binding["runtime_hash"] == runtime_content_hash()
            and binding["cost_contract"] == cost.CONTRACT
            and binding["cost_contract_hash"] == sha256_json(cost.CONTRACT),
            "compaction recovery contract mismatch",
        )
        items, seed = self._read(binding["source_input"]), self._read(binding["source_seed"])
        require(
            isinstance(items, list) and bool(seed) and items[: len(seed)] == seed,
            "compaction source seed mismatch",
        )
        request = {"model": cost.MODEL, "input": items, "service_tier": "default"}
        require(sha256_json(request) == binding["request_hash"], "compaction source input mismatch")
        for name, event in events.items():
            if name not in {"compaction_prepared", "compaction_finished"}:
                require(
                    event["binding_hash"] == sha256_json(binding),
                    "compaction event binding mismatch",
                )
        return events, binding, request

    def execute(
        self,
        *,
        client_factory,
        ledger: DevCostLedger,
        deadline: ExecutionDeadline,
        active_elapsed_seconds: float,
    ) -> dict:
        """One explicitly admitted compact request; never count/create/tools/retry.

        The factory transfers ownership of exactly one zero-retry bounded client.
        A stored started event consumes the attempt even without a response.
        """
        with self.journal.execution_lock():
            return self.execute_locked(
                client_factory=client_factory,
                ledger=ledger,
                deadline=deadline,
                active_elapsed_seconds=active_elapsed_seconds,
            )

    def execute_locked(
        self,
        *,
        client_factory,
        ledger: DevCostLedger,
        deadline: ExecutionDeadline,
        active_elapsed_seconds: float,
    ) -> dict:
        """One explicitly admitted compact request; never count/create/tools/retry.

        The factory transfers ownership of exactly one zero-retry bounded client.
        A stored started event consumes the attempt even without a response.
        """
        began = deadline.clock()
        self.journal.require_execution_lock()
        events, binding, request = self._load()
        require(binding is not None, "compaction must be prepared before dispatch")
        if len(events) > 1 or self.receipt_path.exists():
            return self.recover_locked()
        require(self.journal.terminal() is None, "terminal run cannot dispatch compaction")
        require(
            cost.reserve_from_ledger(ledger) == binding["reservation"],
            "compaction remaining cost changed after preparation",
        )
        base = _elapsed(active_elapsed_seconds)
        require(base >= binding["active_elapsed_seconds"], "active elapsed time moved backwards")

        def elapsed():
            return _elapsed(base + max(0.0, deadline.clock() - began))

        def record(name, payload):
            self.journal.append(
                name,
                {
                    **payload,
                    "binding_hash": sha256_json(binding),
                    "active_elapsed_seconds": elapsed(),
                },
            )

        def failure(exc, *, attempted):
            record(
                "compaction_request_failed",
                {
                    "request_attempted": attempted,
                    "deadline_exhausted": isinstance(exc, ExecutionDeadlineExceeded),
                    "failure": exception_evidence(exc),
                },
            )

        client = None
        try:
            try:
                deadline.check(reserve_seconds=CLEANUP_SECONDS)
                client = client_factory()
                require(client.max_retries == 0, "compaction requires zero SDK retries")
                require(
                    cost.reserve_from_ledger(ledger) == binding["reservation"],
                    "compaction remaining cost changed before dispatch",
                )
                timeout = deadline.bounded_timeout(REQUEST_SECONDS, reserve_seconds=CLEANUP_SECONDS)
            except BaseException as exc:
                failure(exc, attempted=False)
            else:
                record(
                    "compaction_started",
                    {
                        "request_hash": binding["request_hash"],
                        "effective_timeout_seconds": timeout,
                        "reserved_cost_nanos": binding["reservation"]["reserved_cost_nanos"],
                    },
                )
                attempted = False
                try:
                    timeout = deadline.bounded_timeout(
                        REQUEST_SECONDS, reserve_seconds=CLEANUP_SECONDS
                    )
                    attempted = True
                    response = client.responses.compact(**request, timeout=timeout)
                except BaseException as exc:
                    failure(exc, attempted=attempted)
                else:
                    self._record_response(response, request["input"], record, binding)
        finally:
            cleanup = {"status": "NOT_CREATED", "timeout_seconds": 0.0}
            if client is not None:
                wait = min(CLEANUP_SECONDS, deadline.remaining_seconds())
                cleanup = {"status": "UNKNOWN", "timeout_seconds": wait}
                try:
                    deadline.check()
                    client.close(timeout=wait)
                    cleanup["status"] = "CLOSED"
                except BaseException as exc:
                    cleanup["failure"] = exception_evidence(exc)
            record(
                "compaction_cleanup_recorded",
                {
                    "cleanup": cleanup,
                    "deadline_exhausted": deadline.remaining_seconds() <= 0,
                },
            )
        return self.recover_locked()

    def _record_response(self, response, original, record, binding):
        # Capture usage before output serialization, validation or artifact writes.
        raw_usage = (
            response.get("usage")
            if isinstance(response, dict)
            else (getattr(response, "usage", None))
        )
        response_id = (
            response.get("id") if isinstance(response, dict) else (getattr(response, "id", None))
        )
        if not isinstance(response_id, str) or not re.fullmatch(
            r"resp_[a-zA-Z0-9_-]{1,128}", response_id
        ):
            response_id = None
        try:
            usage = usage_fields({"usage": _plain(raw_usage)})
        except (ContractError, TypeError, ValueError):
            usage = None
        accounting = cost.account(
            usage,
            Decimal(binding["reservation"]["available_nanos"]) / Decimal(1_000_000_000),
        )
        record(
            "compaction_usage_recorded",
            {
                "usage": usage,
                "response_id": response_id,
                "accounting": accounting,
                "call_id": "compact_" + binding["boundary_id"],
            },
        )
        try:
            window = validated_window(_plain(response), original)
        except (ContractError, TypeError, ValueError, AttributeError):
            result = {
                "validation": "INVALID",
                "window_artifact": None,
                "item_order_hash": None,
                "item_count": 0,
            }
        else:
            result = {
                "validation": "VALID",
                "window_artifact": self._put(window),
                "item_order_hash": sha256_json([sha256_json(i) for i in window]),
                "item_count": len(window),
            }
        record("compaction_response_recorded", result)

    def recover(self) -> dict | None:
        """Verify durable data; missing results stop, never replay a remote call."""
        with self.journal.execution_lock():
            return self.recover_locked()

    def recover_locked(self):
        self.journal.require_execution_lock()
        events, binding, request = self._load()
        if binding is None:
            return None
        if len(events) == 1 and not self.receipt_path.exists():
            return {"status": "NOT_STARTED", "binding_hash": sha256_json(binding)}
        usage = events.get("compaction_usage_recorded", {})
        response = events.get("compaction_response_recorded", {})
        cleanup = events.get("compaction_cleanup_recorded", {}).get(
            "cleanup", {"status": "UNKNOWN"}
        )
        failure = events.get("compaction_request_failed", {})
        started = "compaction_started" in events
        attempted = failure.get("request_attempted", True if usage else None) if started else False
        if response.get("validation") == "VALID":
            window = self._read(response["window_artifact"])
            validated_window({"object": "response.compaction", "output": window}, request["input"])
            require(
                response["item_count"] == len(window)
                and response["item_order_hash"] == sha256_json([sha256_json(i) for i in window]),
                "compaction output order mismatch",
            )
        accounting = cost.account(
            usage.get("usage"),
            Decimal(binding["reservation"]["available_nanos"]) / Decimal(1_000_000_000),
        )
        if usage:
            require(
                usage.get("accounting") == accounting
                and usage.get("call_id") == "compact_" + binding["boundary_id"],
                "compaction durable usage accounting mismatch",
            )
        if attempted is False:
            accounting = {"status": "NOT_RUN", "model_rate_cost_nanos": 0, "invoice_cost_usd": None}
        terminal, reason = None, "validated compaction receipt; activation not performed"
        if cleanup["status"] == "UNKNOWN":
            terminal, reason = "PROVIDER_TIMEOUT_OR_UNKNOWN", "compaction client cleanup unknown"
        elif attempted is not False and (failure or not response):
            terminal, reason = "PROVIDER_TIMEOUT_OR_UNKNOWN", "compaction outcome unknown; no retry"
        elif accounting["status"] not in {"ACCOUNTED_AT_MODEL_RATES", "NOT_RUN"}:
            terminal, reason = (
                "COST_CAP_REACHED",
                "compaction billing unknown or reservation exceeded",
            )
        elif attempted is False and not failure.get("deadline_exhausted"):
            terminal, reason = "PROVIDER_TIMEOUT_OR_UNKNOWN", "compaction setup failed; no request"
        elif response and response["validation"] != "VALID":
            terminal, reason = "PROVIDER_CONTINUATION_ERROR", "compaction output contract failed"
        elif any(e.get("deadline_exhausted") for e in events.values()):
            terminal, reason = "LIMIT_REACHED", "compaction active deadline exhausted"
        receipt = {
            "kind": "native-compaction-receipt-v1",
            "run_id": self.journal.run_id,
            "binding_hash": sha256_json(binding),
            "source_input_hash": binding["source_input"]["content_hash"],
            "source_seed_hash": binding["source_seed"]["content_hash"],
            "policy_hash": self.policy_hash,
            "request_hash": binding["request_hash"],
            "cost_contract_hash": binding["cost_contract_hash"],
            "validation": response.get("validation", "NOT_RECORDED"),
            "window_artifact": response.get("window_artifact"),
            "item_order_hash": response.get("item_order_hash"),
            "item_count": response.get("item_count", 0),
            "usage": usage.get("usage"),
            "response_id": usage.get("response_id"),
            "accounting": accounting,
            "cleanup": cleanup,
            "failure": failure.get("failure"),
            "active_elapsed_seconds": max(
                _elapsed(e.get("active_elapsed_seconds", 0)) for e in events.values()
            ),
            "admitted_compaction_attempts": int(started),
            "provider_request_attempts": None if attempted is None else int(attempted),
            "terminal": terminal,
            "message": reason,
            "ready_for_activation": terminal is None,
            "endpoint_enforced_dollar_cap": False,
            "automatic_retry": False,
            "count_requests": 0,
            "generation_requests": 0,
            "tool_executions": 0,
            "task_acceptance": "NOT_RUN",
            "safety_state": "NOT_RUN",
            "official": False,
        }
        marker = events.get("compaction_finished")
        if marker is not None and not self.receipt_path.exists():
            raise RecoveryError("committed compaction receipt is missing")
        if self.receipt_path.exists():
            require(not self.receipt_path.is_symlink(), "compaction receipt is a symlink")
            try:
                raw_receipt = self.receipt_path.read_bytes()
                saved = json.loads(raw_receipt)
            except (OSError, ValueError) as exc:
                raise RecoveryError("compaction receipt is unreadable") from exc
            require(
                saved == receipt and raw_receipt == canonical_json(receipt).encode(),
                "compaction receipt mismatch",
            )
        if marker is not None:
            require(
                marker == {"receipt_hash": sha256_json(receipt)}, "compaction receipt hash mismatch"
            )
            return receipt
        self.store.write_text_immutable(self.receipt_path, canonical_json(receipt))
        self.journal.append("compaction_finished", {"receipt_hash": sha256_json(receipt)})
        return receipt
