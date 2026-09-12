"""One separately authorized count-only diagnostic; never a source-run resume.

The frozen design is not an execution grant. Invoking this collector requires
fresh approval for its exact packet, credential path and two-request ceiling,
including the explicitly unconfirmed count-endpoint billing. No generation price
or absent usage field is treated as proof of free counting or a monetary cap.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from time import monotonic

from diagnostics import count_replay as replay
from diagnostics import episode_requests as transport
from patchloop.agent.count_diagnostics import input_count_error_metadata
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def failure_evidence(error: BaseException) -> dict:
    if isinstance(error, (KeyboardInterrupt, SystemExit)):
        return {"category": "interrupted"}
    if isinstance(error, ExecutionDeadlineExceeded):
        return {"category": "execution_deadline"}
    if isinstance(error, ContractError):
        return {"category": "contract_error"}
    return input_count_error_metadata(error)


def admitted_inputs(packet_root: Path, packet_hash: str, output: Path, env_file: Path):
    """All inputs and destination checks precede credential/client creation."""
    replay.verify(packet_root, packet_hash)
    packet = json.loads((packet_root / "packet.json").read_bytes())
    replay.shared.require(sha256_json(packet) == packet_hash, "packet changed during admission")
    for protected in (repository_root().resolve(), Path(packet["source_root"]).resolve(),
                      packet_root):
        replay.shared.require(
            not output.is_relative_to(protected) and not protected.is_relative_to(output),
            "collection must be outside repository, source state and frozen packet",
        )
    replay.shared.require(not output.exists(), "collection destination must be new; no resume")
    credential_hash = sha256_bytes(str(env_file).encode("utf-8"))
    replay.shared.require(
        credential_hash == packet["source_contract"]["credential_file_path_hash"],
        "credential file path mismatch",
    )
    payloads = []
    for case, expected in zip(packet["cases"], replay.COUNT_HASHES, strict=True):
        payload = json.loads(replay.shared.read_source_artifact(
            packet_root, case["count_payload_artifact"],
        ))
        replay.shared.require(sha256_json(payload) == expected, "count payload mismatch")
        payloads.append(payload)
    return packet, payloads


def collect(
    packet_root: Path, packet_hash: str, output: Path, env_file: Path, *,
    accept_unconfirmed_count_billing: bool = False,
    client_factory=None, credential_loader=None, clock=monotonic,
) -> dict:
    """Execute once. Injected clients must implement DiagnosticClient's bounded API.

    A fresh directory is the exclusive invocation claim. Never reopen it to retry
    an admitted count, even when the process died before recording its outcome.
    Hard crashes leave the hash-chained started receipt as UNKNOWN evidence.
    """
    replay.shared.require(
        accept_unconfirmed_count_billing is True,
        "separate exact approval acknowledging unconfirmed count billing is required",
    )
    packet_root, output, env_file = packet_root.resolve(), output.resolve(), env_file.resolve()
    packet, payloads = admitted_inputs(packet_root, packet_hash, output, env_file)
    # Atomic mkdir also rejects a concurrent invocation at this same destination.
    output.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(output, "run_dev_countcollect_" + uuid.uuid4().hex[:16])
    store = ArtifactStore(output)
    protocol = packet["protocol"]
    journal.append("count_collection_started", {
        "packet_hash": packet_hash,
        "collector_hash": sha256_bytes(Path(__file__).read_bytes()),
        "transport_hash": sha256_bytes(Path(transport.__file__).read_bytes()),
        "credential_file_path_hash": packet["source_contract"]["credential_file_path_hash"],
        "protocol": protocol, "count_endpoint_pricing": "UNCONFIRMED",
        "unconfirmed_billing_acknowledged": True, "prior_grant_reused": False,
    })
    started = clock()
    deadline = ExecutionDeadline.from_remaining(
        protocol["proposed_total_timeout_seconds"], clock=clock,
    )
    reserve = protocol["proposed_cleanup_reserve_seconds"]
    receipts, client, failure = [], None, None
    cleanup = {"status": "NOT_CREATED"}
    phase = "client_setup"
    try:
        deadline.check(reserve_seconds=reserve)
        key = (credential_loader or load_exact_openai_api_key)(env_file)
        try:
            client = (client_factory or transport.DiagnosticClient)(api_key=key)
        finally:
            del key
        replay.shared.require(client.max_retries == 0, "collector requires zero SDK retries")
        for index, (case, payload) in enumerate(zip(packet["cases"], payloads, strict=True)):
            state = replay.protocol_state(receipts)
            if state["next_case"] is None:
                break
            replay.shared.require(state["next_case"] == case["case_id"], "case order mismatch")
            phase = "pre_dispatch"
            timeout = deadline.bounded_timeout(
                protocol["proposed_count_timeout_seconds"], reserve_seconds=reserve,
            )
            receipt = {
                "case_id": case["case_id"], "count_id": f"count_{journal.run_id}_{index}",
                "turn_id": case["turn_id"], "status": "started",
                "request_metadata": case["request_metadata"], "timeout_seconds": timeout,
            }
            journal.append("input_count_started", receipt)
            receipts.append(receipt)
            # Include admission I/O in the deadline; never start late network work.
            timeout = deadline.bounded_timeout(timeout, reserve_seconds=reserve)
            phase = "count_request"
            response = client.responses.input_tokens.count(**payload, timeout=timeout)
            count = getattr(response, "input_tokens", None)
            replay.shared.require(
                getattr(response, "object", None) == "response.input_tokens"
                and type(count) is int and count >= 0, "invalid input count response",
            )
            finished = {**receipt, "status": "succeeded", "input_tokens": count}
            phase = "count_outcome_persistence"
            journal.append("input_count_finished", finished)
            receipts[-1] = finished
            # Preserve the received count, but a late result never authorizes case 2.
            phase = "post_response"
            deadline.check(reserve_seconds=reserve)
    except (Exception, KeyboardInterrupt, SystemExit) as error:
        failure = {"phase": phase, **failure_evidence(error)}
        if receipts and receipts[-1]["status"] == "started":
            receipt = {**receipts[-1], "status": "failed", "error": failure}
            # If persistence itself fails, the started row remains UNKNOWN and no
            # subsequent request is made. Do not turn memory-only success durable.
            journal.append("input_count_failed", receipt)
            receipts[-1] = receipt
    finally:
        if client is not None:
            cleanup_timeout = min(reserve, deadline.remaining_seconds())
            try:
                client.close(timeout=cleanup_timeout)
                cleanup = {"status": "CLOSED", "timeout_seconds": cleanup_timeout}
            except (Exception, KeyboardInterrupt, SystemExit) as error:
                cleanup = {"status": "UNKNOWN", "timeout_seconds": cleanup_timeout,
                           "error": failure_evidence(error)}
            journal.append("count_client_cleanup", cleanup)
    state = replay.protocol_state(receipts)
    result = {
        "schema_version": "count-only-collection-v1", "run_id": journal.run_id,
        "packet_hash": packet_hash,
        "result": ("STOP_CLEANUP_UNKNOWN" if cleanup["status"] == "UNKNOWN"
                   else "STOP_ERROR" if failure else state["result"]),
        "protocol_result": state["result"], "receipts": receipts,
        "failure": failure, "cleanup": cleanup,
        "admitted_count_attempts": len(receipts),
        "elapsed_seconds": round(max(0.0, clock() - started), 6),
        "count_endpoint_pricing": "UNCONFIRMED", "observed_cost_usd": None,
        "generation_requests": 0, "task_executions": 0, "docker_operations": 0,
        "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN",
        "official": False, "claim_eligible": False, "automatic_retry_or_resume": False,
    }
    artifact = store.put_json(result)
    journal.append("terminal", {"result_artifact": artifact.model_dump(mode="json"),
                                "result_hash": sha256_json(result), "result": result["result"]})
    store.write_text_immutable(output / "result.json", canonical_json(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--packet-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--accept-unconfirmed-count-billing", action="store_true")
    args = parser.parse_args()
    try:
        result = collect(**vars(args))
    except (Exception, KeyboardInterrupt, SystemExit) as error:
        # CLI tracebacks can contain provider bodies or secrets from client setup.
        print(canonical_json({"result": "STOP_ERROR", "error": failure_evidence(error)}))
        raise SystemExit(2) from None
    print(canonical_json(result))
    if result["result"] != "NOT_REPRODUCED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
