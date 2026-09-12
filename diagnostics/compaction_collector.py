"""One separately approved compaction, then stop; no token-count or generation calls.

inspect is provider-free. collect requires the exact inspection hash, positive
budget and explicit acceptance of model-limit-based (not endpoint-enforced) cost
reservation. The previous frozen packet is evidence, never an execution grant.
"""
from __future__ import annotations

import argparse
import json
import uuid
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import compaction_cost as cost
from diagnostics import compaction_replay as design
from diagnostics import compaction_state as state
from diagnostics import episode_requests as transport
from diagnostics.count_collector import failure_evidence
from diagnostics.decision_sampler import read_source_artifact, require
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

WAITS = {"request_seconds": 300, "total_seconds": 305, "cleanup_reserve_seconds": 5}


def inspect(packet_root: Path, packet_hash: str, output: Path, env_file: Path,
            max_cost_usd: Decimal, repeat: int) -> dict:
    """Resolve exact inputs before any client, credential load or new output."""
    require(type(repeat) is int and repeat == 1, "only one compaction attempt is supported")
    packet_root, env_file = packet_root.resolve(), env_file.resolve()
    packet, values = design.verify(packet_root, packet_hash)
    output = design.new_external_root(output, packet_root, Path(packet["source_root"]))
    require(env_file.is_file() and not env_file.is_symlink(), "credential file is unavailable")
    credential_hash = sha256_bytes(str(env_file).encode())
    require(credential_hash == packet["source_contract"]["credential_file_path_hash"],
            "credential file path mismatch")
    request = values["compact"]
    require(request["model"] == cost.MODEL and request["service_tier"] == "default",
            "unpriced model or service tier")
    quote = cost.reserve(max_cost_usd)
    plan = {
        "kind": "single-compaction-collection-v1", "packet_root": str(packet_root),
        "packet_hash": packet_hash, "output_root": str(output),
        "source_contract": packet["source_contract"], "credential_file_path_hash": credential_hash,
        "request_hash": sha256_json(request), "repeat": repeat,
        "max_cost_usd": format(max_cost_usd.normalize(), "f"),
        "reservation": quote, "cost_contract": cost.CONTRACT,
        "waits": WAITS, "sdk_retries": 0,
        "implementation": {p.name: sha256_bytes(p.read_bytes()) for p in (
            Path(__file__), Path(cost.__file__), Path(transport.__file__),
        )},
        "automatic_retry_or_resume": False, "count_requests": 0, "generation_requests": 0,
        "tool_executions": 0, "docker_operations": 0, "hidden_evaluations": 0,
        "official": False, "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN",
    }
    return {"execution_plan_hash": sha256_json(plan), "plan": plan,
            "api_requests": 0, "credentials_loaded": 0, "execution_granted": False}


def _result(plan, journal, compact_receipt, cleanup, failure, attempts):
    events = journal.events()
    admitted = sum(e["event_type"] == "compaction_dispatch_started" for e in events)
    rows = [e["payload"]["usage"] for e in events
            if e["event_type"] == "compaction_response_usage"]
    require(len(rows) <= 1, "duplicate compaction usage")
    usage = compact_receipt["usage"] if compact_receipt else rows[0] if rows else None
    accounting = (cost.account(usage, Decimal(plan["max_cost_usd"]))
                  if usage is not None else {"status": "BILLING_UNKNOWN"
                                            if attempts or (admitted and attempts is None) else
                                          "NOT_DISPATCHED", "model_rate_cost_nanos": None,
                                          "invoice_cost_usd": None})
    if cleanup["status"] == "UNKNOWN":
        status = "STOP_CLEANUP_UNKNOWN"
    elif failure:
        status = "STOP_ERROR"
    elif accounting["status"] != "ACCOUNTED_AT_MODEL_RATES":
        status = "STOP_" + accounting["status"]
    elif compact_receipt is None or compact_receipt["status"] != "READY_FOR_REVIEW":
        status = "STOP_RESPONSE_CONTRACT"
    else:
        status = "COMPACTION_COMPLETE"
    return {
        "kind": plan["kind"], "run_id": journal.run_id, "execution_plan_hash": sha256_json(plan),
        "packet_hash": plan["packet_hash"], "result": status, "accounting": accounting,
        "observed_usage": usage,
        "reservation": plan["reservation"], "compact_receipt": compact_receipt,
        "cleanup": cleanup, "failure": failure, "provider_request_attempts": attempts,
        "admitted_compaction_attempts": admitted,
        "count_requests": 0, "generation_requests": 0, "tool_executions": 0,
        "docker_operations": 0, "automatic_retry_or_resume": False,
        "next_requests": "ARTIFACTS_ONLY_NOT_AUTHORIZED", "official": False,
        "claim_eligible": False, "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN",
    }


def _publish(root, journal, result):
    artifact = design.put_json(ArtifactStore(root / "artifacts"), result)
    journal.append("terminal", {"result_artifact": artifact, "result_hash": sha256_json(result)})
    ArtifactStore(root).write_text_immutable(root / "result.json", canonical_json(result))
    return result


def collect(packet_root: Path, packet_hash: str, output: Path, env_file: Path,
            max_cost_usd: Decimal, repeat: int, *, execution_plan_hash: str,
            accept_model_limit_reservation: bool = False,
            client_factory=None, credential_loader=None, clock=monotonic) -> dict:
    require(accept_model_limit_reservation is True,
            "separate approval must accept model-limit reservation, not an enforced dollar cap")
    admission = inspect(packet_root, packet_hash, output, env_file, max_cost_usd, repeat)
    require(admission["execution_plan_hash"] == execution_plan_hash, "execution plan mismatch")
    plan = admission["plan"]
    output, packet_root, env_file = output.resolve(), packet_root.resolve(), env_file.resolve()
    # Exclusive fresh-directory claim prevents retries or concurrent use of this invocation.
    output.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(output, "run_dev_compactcollect_" + uuid.uuid4().hex[:16])
    binding = {"run_id": journal.run_id, "plan": plan, "execution_plan_hash": execution_plan_hash}
    ArtifactStore(output).write_text_immutable(output / "execution.json", canonical_json(binding))
    with journal.execution_lock():
        journal.append("compaction_collection_started", {
            "execution_plan_hash": execution_plan_hash,
            "model_limit_assumption_acknowledged": True, "previous_grant_reused": False,
        })
        deadline = ExecutionDeadline.from_remaining(WAITS["total_seconds"], clock=clock)
        cleanup_reserve = WAITS["cleanup_reserve_seconds"]
        client, compact_receipt, failure, attempts = None, None, None, 0
        cleanup, phase = {"status": "NOT_CREATED"}, "client_setup"
        try:
            _, values = design.verify(packet_root, packet_hash)
            deadline.check(reserve_seconds=cleanup_reserve)
            key = (credential_loader or load_exact_openai_api_key)(env_file)
            try:
                client = (client_factory or transport.DiagnosticClient)(api_key=key)
            finally:
                del key
            require(client.max_retries == 0, "zero SDK retries required")
            state.reserve(packet_root, packet_hash, output / "compact")
            phase = "pre_dispatch"
            # Reserve the whole published model envelope, not the old native count
            # and not a smaller output ceiling that this endpoint cannot enforce.
            reservation = cost.reserve(max_cost_usd)
            timeout = deadline.bounded_timeout(WAITS["request_seconds"],
                                               reserve_seconds=cleanup_reserve)
            journal.append("compaction_dispatch_started", {
                "request_hash": plan["request_hash"], "reservation": reservation,
                "timeout_seconds": timeout,
            })
            timeout = deadline.bounded_timeout(timeout, reserve_seconds=cleanup_reserve)
            phase, attempts = "compaction_request", 1
            response = client.responses.compact(**values["compact"], timeout=timeout)
            phase = "usage_persistence"
            usage = response.get("usage") if isinstance(response, dict) else response.usage
            if hasattr(usage, "model_dump"):
                usage = usage.model_dump(mode="json", exclude_unset=True, warnings=False)
            try:
                usage = state.usage_fields({"usage": usage})
            except (ContractError, TypeError, ValueError):
                usage = None
            journal.append("compaction_response_usage", {"usage": usage})
            phase = "response_persistence"
            compact_receipt = state.record_response(output / "compact", response)
            journal.append("compaction_usage_accounted", {
                "receipt_hash": sha256_json(compact_receipt),
                "accounting": cost.account(compact_receipt["usage"], max_cost_usd),
            })
            phase = "post_response"
            deadline.check(reserve_seconds=cleanup_reserve)
        except (Exception, KeyboardInterrupt, SystemExit) as error:
            failure = {"phase": phase, **failure_evidence(error)}
        finally:
            if client is not None:
                timeout = min(cleanup_reserve, deadline.remaining_seconds())
                try:
                    client.close(timeout=timeout)
                    cleanup = {"status": "CLOSED", "timeout_seconds": timeout}
                except (Exception, KeyboardInterrupt, SystemExit) as error:
                    cleanup = {"status": "UNKNOWN", "timeout_seconds": timeout,
                               "error": failure_evidence(error)}
                journal.append("compaction_client_cleanup", cleanup)
        # Finished/invalid output is durable even if cleanup or the final publication fails.
        if compact_receipt is None and (output / "compact" / "receipt.json").is_file():
            try:
                compact_receipt = state.recover(output / "compact")
            except (Exception, KeyboardInterrupt, SystemExit) as error:
                failure = {"phase": "receipt_recovery", **failure_evidence(error)}
        result = _result(plan, journal, compact_receipt, cleanup, failure, attempts)
        return _publish(output, journal, result)


def recover(output: Path) -> dict:
    """Read/reconcile completed evidence only; never create a client or retry a call."""
    output = output.resolve()
    binding = json.loads((output / "execution.json").read_bytes())
    plan = binding["plan"]
    require(sha256_json(plan) == binding["execution_plan_hash"], "execution binding mismatch")
    journal = DevJournal(output, binding["run_id"])
    with journal.execution_lock():
        events = journal.events()
        require(events and events[0]["event_type"] == "compaction_collection_started"
                and events[0]["payload"]["execution_plan_hash"] == binding["execution_plan_hash"],
                "collection journal mismatch")
        terminals = [e["payload"] for e in events if e["event_type"] == "terminal"]
        if terminals:
            require(len(terminals) == 1, "duplicate collection terminal")
            raw = read_source_artifact(output, terminals[0]["result_artifact"])
            result = json.loads(raw)
            require(sha256_json(result) == terminals[0]["result_hash"], "result hash mismatch")
            if result["compact_receipt"]:
                require(state.recover(output / "compact") == result["compact_receipt"],
                        "compaction receipt mismatch")
            ArtifactStore(output).write_text_immutable(
                output / "result.json", canonical_json(result),
            )
            return result
        # Current exact reconstruction is required before completing an unfinished handoff.
        design.verify(Path(plan["packet_root"]), plan["packet_hash"])
        require(plan["cost_contract"] == cost.CONTRACT and plan["waits"] == WAITS,
                "recovery contract mismatch")
        for name, digest in plan["implementation"].items():
            require(name in {Path(__file__).name, Path(cost.__file__).name,
                             Path(transport.__file__).name}, "unknown recovery module")
            require(sha256_bytes(Path(__file__).with_name(name).read_bytes()) == digest,
                    "collector implementation changed")
        compact_receipt = None
        if (output / "compact" / "receipt.json").is_file():
            compact_receipt = state.recover(output / "compact")
        admitted = sum(e["event_type"] == "compaction_dispatch_started" for e in events)
        require(admitted <= 1, "duplicate compaction admission")
        # A durable intent is not proof that HTTP was reached before a hard crash.
        attempts = None if admitted else 0
        cleanup_rows = [e["payload"] for e in events
                        if e["event_type"] == "compaction_client_cleanup"]
        cleanup = cleanup_rows[-1] if cleanup_rows else {"status": "UNKNOWN"}
        failure = {"phase": "recovery", "category": "interrupted_collection_no_retry"}
        return _publish(output, journal,
                        _result(plan, journal, compact_receipt, cleanup, failure, attempts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("inspect", "collect"):
        p = commands.add_parser(mode)
        for name in ("packet-root", "output", "env-file"):
            p.add_argument("--" + name, required=True, type=Path)
        p.add_argument("--packet-hash", required=True)
        p.add_argument("--max-cost-usd", required=True, type=Decimal)
        p.add_argument("--repeat", required=True, type=int, choices=[1])
        if mode == "collect":
            p.add_argument("--execution-plan-hash", required=True)
            p.add_argument("--accept-model-limit-reservation", action="store_true")
    commands.add_parser("recover").add_argument("--output", required=True, type=Path)
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    try:
        result = {"inspect": inspect, "collect": collect, "recover": recover}[mode](**args)
    except (Exception, KeyboardInterrupt, SystemExit) as error:
        print(canonical_json({"result": "STOP_ERROR", "error": failure_evidence(error)}))
        raise SystemExit(2) from None
    print(canonical_json(result))
    if mode != "inspect" and result["result"] != "COMPACTION_COMPLETE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
