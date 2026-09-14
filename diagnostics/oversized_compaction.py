"""One standalone compact of a frozen failed input, never a native-run recovery.

prepare/inspect are provider-free. collect needs separate exact authorization and
acknowledgement of conditional model-limit reservation, not an API-enforced cap.
Only compact is called. No count, generation, task execution or window activation.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from time import monotonic

from diagnostics.compaction_replay import new_external_root, put_json
from diagnostics.compaction_state import request_metrics
from diagnostics.count_collector import failure_evidence
from diagnostics.decision_sampler import read_source_artifact
from patchloop.agent.compaction import require, usage_fields, validated_window
from patchloop.agent.request_transport import BoundedResponsesClient
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import compaction_cost as cost
from patchloop.dev.conversation import validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.runtime import runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SCHEMA = "oversized-continuation-collection-v1"
PROPOSAL_SCHEMA = "oversized-continuation-compact-proposal-v1"
RUN_ID = "run_dev_oversizedcompact"
WAITS = {"request_seconds": 300, "total_seconds": 305, "cleanup_reserve_seconds": 5}
BOUNDARY = {
    "official": False, "claim_eligible": False, "task_acceptance": "NOT_RUN",
    "safety_state": "NOT_RUN", "count_requests": 0, "generation_requests": 0,
    "tool_executions": 0, "docker_operations": 0, "hidden_evaluations": 0,
    "native_window_activation": False, "automatic_retry_or_resume": False,
    "closed_planning_grant_reused": False,
}


def identity() -> dict:
    # Runtime includes the reused validators, transport, prices, journal and CAS.
    return {"runtime_hash": runtime_content_hash(),
            "modules": {name: sha256_bytes(Path(__file__).with_name(name).read_bytes())
                        for name in (Path(__file__).name, "compaction_replay.py",
                                     "compaction_state.py", "count_collector.py",
                                     "decision_sampler.py")},
            "packages": {name: version(name) for name in ("openai", "httpx")}}


def source_request(proposal_path: Path, proposal_hash: str) -> tuple[dict, dict]:
    """Only read the exact saved public model input; never open task/private files."""
    require(proposal_path.is_file() and not proposal_path.is_symlink(), "missing proposal")
    proposal = json.loads(proposal_path.read_bytes())
    require(sha256_json(proposal) == proposal_hash and proposal["schema"] == PROPOSAL_SCHEMA,
            "proposal identity mismatch")
    source, proposed = proposal["source"], proposal["proposed_request"]
    path = Path(source["journal_path"])
    require(path.is_file() and not path.is_symlink()
            and sha256_bytes(path.read_bytes()) == source["journal_hash"], "source journal changed")
    require(path.name == source["run_id"] + ".jsonl" and path.parent.name == "runs",
            "source journal path mismatch")
    # Do not construct a writable store/journal under the immutable source root.
    journal = object.__new__(DevJournal)
    journal.path, journal.run_id = path, source["run_id"]
    events = journal.events()
    require(events and events[-1]["event_type"] == "terminal"
            and events[-1]["payload"]["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN",
            "source terminal mismatch")
    turns = [e["payload"] for e in events if e["event_type"] == "turn_started"
             and e["payload"]["turn_id"] == source["turn_id"]]
    require(len(turns) == 1, "source turn mismatch")
    turn = turns[0]
    require(not any(e["event_type"] == "provider_call_started"
                    and e["payload"].get("turn_id") == source["turn_id"] for e in events),
            "source correction was already dispatched")
    ref = turn["model_input_artifact"]
    require(ref["content_hash"] == source["input_artifact_hash"] == turn["model_input_hash"]
            and ref["size_bytes"] == source["input_artifact_bytes"]
            and Path(ref["path"]).resolve() == Path(source["input_artifact_path"]).resolve(),
            "source input binding mismatch")
    items = json.loads(read_source_artifact(path.parent.parent, ref))
    validate_model_input(items, turn["native_history"])
    for item in items:
        if item.get("type") == "reasoning":
            require(set(item) <= {"type", "id", "summary", "status", "encrypted_content"}
                    and item.get("summary", []) == []
                    and isinstance(item.get("encrypted_content"), str)
                    and bool(item["encrypted_content"]), "unsafe source reasoning")
    require(proposed["model"] == cost.MODEL and proposed["service_tier"] == "default"
            and proposed["endpoint"] == cost.CONTRACT["endpoint"], "request contract mismatch")
    request = {"model": cost.MODEL, "input": items, "service_tier": "default"}
    require(sha256_json(request) == proposed["canonical_hash"]
            and len(canonical_json(request).encode()) == proposed["canonical_utf8_bytes"],
            "exact compact request mismatch")
    envelope_path = path.with_suffix(".envelope.json")
    require(envelope_path.is_file() and not envelope_path.is_symlink(), "missing source envelope")
    envelope = json.loads(envelope_path.read_bytes())
    require(all(envelope[key] == source[key] for key in ("task_id", "task_version", "runtime_hash"))
            and envelope["model"] == cost.MODEL, "source envelope mismatch")
    # Do not copy private envelope fields into the diagnostic packet or request.
    binding = {"proposal_path": str(proposal_path.resolve()), "proposal_hash": proposal_hash,
               "source": source, "envelope_hash": sha256_bytes(envelope_path.read_bytes()),
               "credential_file_path_hash": envelope["credential_file_path_hash"],
               "credential_file": proposed["credential_file_if_authorized"]}
    return binding, request


def _packet(proposal: Path, proposal_hash: str, root: Path, env_file: Path,
            max_cost_usd: Decimal, repeat: int, pricing_verified_on: str) -> tuple[dict, dict]:
    require(type(repeat) is int and repeat == 1, "only one compact request is supported")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", pricing_verified_on), "invalid price-review date")
    binding, request = source_request(proposal, proposal_hash)
    env_file = env_file.resolve()
    require(env_file.is_file() and not env_file.is_symlink()
            and env_file == Path(binding["credential_file"]).resolve()
            and sha256_bytes(str(env_file).encode()) == binding["credential_file_path_hash"],
            "credential path mismatch")
    packet = {
        "schema": SCHEMA, "root": str(root.resolve()), "source_binding": binding,
        "implementation": identity(), "model": cost.MODEL, "service_tier": "default",
        "request_hash": sha256_json(request), "request_metrics": request_metrics(request),
        "body_keys": ["model", "input", "service_tier"], "repeat": repeat,
        "env_file": str(env_file), "max_cost_usd": format(max_cost_usd.normalize(), "f"),
        "reservation": cost.reserve(max_cost_usd), "cost_contract": cost.CONTRACT,
        "pricing_verified_on": pricing_verified_on, "waits": WAITS, "sdk_retries": 0,
        "source_rendered_input_tokens": None, "source_fits_model_context": "UNVERIFIED",
        "maximum_compaction_requests": 1,
        "next_window": "entire validated output, artifacts only; usability unverified",
        **BOUNDARY,
    }
    return packet, request


def summary(packet: dict) -> dict:
    return {"packet_hash": sha256_json(packet), "packet": packet,
            "api_requests": 0, "credentials_loaded": 0, "execution_granted": False}


def prepare(proposal: Path, proposal_hash: str, root: Path, env_file: Path,
            max_cost_usd: Decimal, repeat: int, pricing_verified_on: str) -> dict:
    packet, _ = _packet(proposal, proposal_hash, root, env_file,
                        max_cost_usd, repeat, pricing_verified_on)
    source_root = Path(packet["source_binding"]["source"]["journal_path"]).parent.parent
    root = new_external_root(root, source_root, proposal.resolve().parent)
    root.mkdir(parents=True, exist_ok=False)
    ArtifactStore(root).write_text_immutable(root / "packet.json", canonical_json(packet))
    return summary(packet)


def _load(root: Path, packet_hash: str, *, current: bool = True) -> tuple[dict, dict]:
    path = root / "packet.json"
    require(path.is_file() and not path.is_symlink(), "missing diagnostic packet")
    packet = json.loads(path.read_bytes())
    require(sha256_json(packet) == packet_hash and packet["schema"] == SCHEMA
            and Path(packet["root"]).resolve() == root.resolve(), "packet binding mismatch")
    if not current:
        return packet, {}
    source = packet["source_binding"]
    expected, request = _packet(Path(source["proposal_path"]), source["proposal_hash"], root,
                                Path(packet["env_file"]), Decimal(packet["max_cost_usd"]),
                                packet["repeat"], packet["pricing_verified_on"])
    require(packet == expected, "diagnostic execution contract changed")
    return packet, request


def inspect(root: Path, packet_hash: str) -> dict:
    return summary(_load(root, packet_hash)[0])


def _record_response(root: Path, journal: DevJournal, response, original: list[dict]) -> None:
    if hasattr(response, "model_dump"):
        response = response.model_dump(mode="json", exclude_unset=True, warnings=False)
    require(isinstance(response, dict), "invalid response object")
    try:
        usage = usage_fields(response)
    except (ContractError, TypeError, ValueError):
        usage = None
    tier = response.get("service_tier")
    response_id = response.get("id")
    # Usage is durable before output validation/storage. Never save the raw response.
    journal.append("compact_usage_recorded", {
        "usage": usage, "standard_tier": tier is None or tier == "default",
        "response_id": response_id if isinstance(response_id, str)
        and re.fullmatch(r"resp_[A-Za-z0-9_-]{1,240}", response_id) else None,
    })
    record = {"window_artifact": None, "window_hash": None, "metrics": None,
              "status": "COMPACTION_OUTPUT_CONTRACT_ERROR"}
    try:
        window = validated_window(response, original)
    except (ContractError, TypeError, ValueError):
        pass
    else:
        record.update(window_artifact=put_json(ArtifactStore(root / "artifacts"), window),
                      window_hash=sha256_json(window), metrics=request_metrics({"input": window}),
                      status="COMPACT_WINDOW_OBSERVED_ONLY")
    journal.append("compact_response_recorded", record)


def _result(packet, journal, *, failure=None, attempts=None) -> dict:
    events = journal.events()

    def single(kind):
        rows = [e["payload"] for e in events if e["event_type"] == kind]
        require(len(rows) <= 1, "duplicate diagnostic event")
        return rows[0] if rows else None

    started = single("compact_dispatch_started")
    usage = single("compact_usage_recorded")
    record = single("compact_response_recorded")
    cleanup = single("compact_client_cleanup") or {"status": "UNKNOWN"}
    failure = failure or single("compact_request_failed")
    if attempts is None and not started:
        attempts = 0
    if attempts is None and (usage is not None or record is not None):
        attempts = 1  # A recorded response, unlike intent alone, proves a call completed.
    accounting = cost.account(usage["usage"] if usage and usage["standard_tier"] else None,
                              Decimal(packet["max_cost_usd"]))
    if not started and attempts == 0:
        accounting["status"] = "NOT_DISPATCHED"
    if cleanup["status"] == "UNKNOWN":
        status = "STOP_CLEANUP_UNKNOWN"
    elif failure:
        status = ("COMPACT_ENDPOINT_REJECTED_INPUT_SIZE" if failure.get("http_status") == 400
                  and failure.get("code") == "string_above_max_length"
                  and (failure.get("param") or "").startswith("input") else "STOP_ERROR")
    elif accounting["status"] != "ACCOUNTED_AT_MODEL_RATES":
        status = "STOP_" + accounting["status"]
    else:
        status = record["status"] if record else "COMPACTION_OUTCOME_UNKNOWN"
    return {"schema": SCHEMA, "packet_hash": sha256_json(packet), "result": status,
            "request_hash": packet["request_hash"], "before": packet["request_metrics"],
            "response": record, "observed_usage": usage["usage"] if usage else None,
            "accounting": accounting, "reservation": packet["reservation"],
            "failure": failure, "cleanup": cleanup, "provider_request_attempts": attempts,
            "admitted_compaction_attempts": int(started is not None),
            "next_request_admission": "NOT_TESTED", **BOUNDARY}


def _publish(root: Path, journal: DevJournal, result: dict) -> dict:
    ref = put_json(ArtifactStore(root / "artifacts"), result)
    journal.append("terminal", {"result_artifact": ref, "result_hash": sha256_json(result)})
    ArtifactStore(root).write_text_immutable(root / "result.json", canonical_json(result))
    return result


def collect(root: Path, packet_hash: str, *, accept_model_limit_reservation: bool = False,
            client_factory=None, credential_loader=None, clock=monotonic) -> dict:
    require(accept_model_limit_reservation is True,
            "separate approval must accept conditional reservation, not an enforced dollar cap")
    packet, _ = _load(root, packet_hash)
    require(packet["pricing_verified_on"] == utc_now().date().isoformat(),
            "fresh price review required")
    execution = root / "execution"
    # One exclusive claim per exact packet; even an interrupted setup is never retried.
    execution.mkdir(exist_ok=False)
    journal = DevJournal(execution, RUN_ID)
    with journal.execution_lock():
        journal.append("collection_started", {"packet_hash": packet_hash,
                                             "conditional_reservation_acknowledged": True})
        deadline = ExecutionDeadline.from_remaining(WAITS["total_seconds"], clock=clock)
        client, failure, attempts, phase = None, None, 0, "client_setup"
        try:
            deadline.check(reserve_seconds=WAITS["cleanup_reserve_seconds"])
            key = (credential_loader or load_exact_openai_api_key)(Path(packet["env_file"]))
            try:
                client = (client_factory or BoundedResponsesClient)(api_key=key)
            finally:
                del key
            require(client.max_retries == 0, "zero retries required")
            # Recheck source/code after client setup, before durable admission.
            _, request = _load(root, packet_hash)
            phase = "pre_dispatch"
            timeout = deadline.bounded_timeout(WAITS["request_seconds"], reserve_seconds=5)
            journal.append("compact_dispatch_started", {
                "request_hash": sha256_json(request), "timeout_seconds": timeout,
                "reservation": cost.reserve(Decimal(packet["max_cost_usd"])),
            })
            timeout = deadline.bounded_timeout(timeout, reserve_seconds=5)
            phase, attempts = "compact_request", 1
            response = client.responses.compact(**request, timeout=timeout)
            phase = "response_persistence"
            _record_response(execution, journal, response, request["input"])
            phase = "post_response"
            deadline.check(reserve_seconds=5)
        except (Exception, KeyboardInterrupt, SystemExit) as error:
            failure = {"phase": phase, **failure_evidence(error)}
            journal.append("compact_request_failed", failure)
        finally:
            cleanup = {"status": "NOT_CREATED"}
            if client is not None:
                timeout = min(5, deadline.remaining_seconds())
                try:
                    client.close(timeout=timeout)
                    cleanup = {"status": "CLOSED", "timeout_seconds": timeout}
                except (Exception, KeyboardInterrupt, SystemExit) as error:
                    cleanup = {"status": "UNKNOWN", "error": failure_evidence(error)}
            journal.append("compact_client_cleanup", cleanup)
        return _publish(execution, journal, _result(packet, journal,
                                                   failure=failure, attempts=attempts))


def recover(root: Path, packet_hash: str) -> dict:
    """Read/reconcile durable evidence only. No client and no unresolved-call retry."""
    packet, _ = _load(root, packet_hash, current=False)
    execution = root / "execution"
    require(execution.is_dir() and not execution.is_symlink(), "no diagnostic execution")
    journal = DevJournal(execution, RUN_ID)
    with journal.execution_lock():
        events = journal.events()
        require(events and events[0]["event_type"] == "collection_started"
                and events[0]["payload"]["packet_hash"] == packet_hash, "collection mismatch")
        terminals = [e["payload"] for e in events if e["event_type"] == "terminal"]
        require(len(terminals) <= 1, "duplicate terminal")
        if terminals:
            terminal = terminals[0]
            result = json.loads(read_source_artifact(execution, terminal["result_artifact"]))
            require(sha256_json(result) == terminal["result_hash"]
                    and result["packet_hash"] == packet_hash, "result identity mismatch")
        else:
            _load(root, packet_hash)  # Unfinished reconciliation requires the exact contract.
            result = _result(packet, journal, failure={"phase": "recovery",
                                                     "category": "interrupted_no_retry"})
        record = result["response"]
        if record and record["window_artifact"]:
            window = json.loads(read_source_artifact(execution, record["window_artifact"]))
            require(sha256_json(window) == record["window_hash"], "window identity mismatch")
        if not terminals:
            return _publish(execution, journal, result)
        ArtifactStore(execution).write_text_immutable(execution / "result.json",
                                                     canonical_json(result))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--proposal", type=Path, required=True)
    p.add_argument("--proposal-hash", required=True)
    p.add_argument("--env-file", type=Path, required=True)
    p.add_argument("--max-cost-usd", type=Decimal, required=True)
    p.add_argument("--repeat", type=int, choices=[1], required=True)
    p.add_argument("--pricing-verified-on", required=True)
    p.add_argument("--root", type=Path, required=True)
    for mode in ("inspect", "collect", "recover"):
        p = commands.add_parser(mode)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--packet-hash", required=True)
        if mode == "collect":
            p.add_argument("--accept-model-limit-reservation", action="store_true")
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    try:
        result = {"prepare": prepare, "inspect": inspect,
                  "collect": collect, "recover": recover}[mode](**args)
    except (Exception, KeyboardInterrupt, SystemExit) as error:
        print(canonical_json({"result": "STOP_ERROR", "error": failure_evidence(error)}))
        raise SystemExit(2) from None
    print(canonical_json(result))
    if mode in {"collect", "recover"} and result["result"] != "COMPACT_WINDOW_OBSERVED_ONLY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
