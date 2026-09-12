"""One frozen post-compaction count and one response; never execute sampled tools.

Preparation is provider-free. Collection needs a separate exact approval, including
the unconfirmed count-endpoint billing; the numeric cap covers generation only.
No correction, retry, recompaction, native resume, task workspace or Docker path.
"""
from __future__ import annotations

import argparse
import json
import re
import uuid
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from diagnostics import compaction_cost as prices
from diagnostics import compaction_replay as design
from diagnostics import compaction_state as compact
from diagnostics import episode_requests as transport
from diagnostics.count_collector import failure_evidence
from diagnostics.decision_sampler import model_config, read_source_artifact, require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.runner import (
    _load_provider_continuation,
    _store_provider_continuation,
    _turn_from_openai,
    _validate_continuation_action_order,
)
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import validate_tool_batch
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.runtime import runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

KIND = "compaction-single-followup-v1"
INPUT_LIMIT, OUTPUT_LIMIT = 272_000, 25_000
WAITS = {"count_seconds": 30, "response_seconds": 300, "total_seconds": 335,
         "cleanup_reserve_seconds": 5}
BOUNDARIES = {"official": False, "claim_eligible": False, "task_acceptance": "NOT_RUN",
              "safety_state": "NOT_RUN", "tool_executions": 0, "docker_operations": 0,
              "compaction_requests": 0, "correction_requests": 0,
              "automatic_retry_or_resume": False}


def source(root: Path, result_hash: str) -> tuple[dict, dict, dict]:
    """Verify completed source receipts and reconstruct input without source writes."""
    root = root.resolve()
    raw = (root / "result.json").read_bytes()
    require(sha256_bytes(raw) == result_hash, "source result hash mismatch")
    result = json.loads(raw)
    binding = json.loads((root / "execution.json").read_bytes())
    require(sha256_json(binding["plan"]) == binding["execution_plan_hash"]
            == result["execution_plan_hash"], "source execution binding mismatch")
    journal = DevJournal(root, binding["run_id"])
    events = journal.events()
    terminal = [e["payload"] for e in events if e["event_type"] == "terminal"]
    require(len(terminal) == 1 and terminal[0]["result_hash"] == result_hash
            and read_source_artifact(root, terminal[0]["result_artifact"]) == raw,
            "source terminal mismatch")
    require(result["result"] == "COMPACTION_COMPLETE" and result["cleanup"]["status"] == "CLOSED"
            and result["provider_request_attempts"] == 1 and result["official"] is False,
            "source compaction is not complete")
    packet, values, child = compact._load(root / "compact")
    receipt = json.loads((root / "compact" / "receipt.json").read_bytes())
    recorded = [e["payload"] for e in child.events()
                if e["event_type"] == "compaction_result_recorded"]
    require(receipt == result["compact_receipt"] and receipt["status"] == "READY_FOR_REVIEW"
            and recorded == [{"receipt_hash": sha256_json(receipt)}], "source receipt mismatch")
    window = json.loads(read_source_artifact(root / "compact", receipt["window_artifact"]))
    compact.validated_window({"object": "response.compaction", "output": window},
                             values["control"]["input"])
    require(sha256_json(window) == receipt["window_hash"], "source window hash mismatch")
    request, count = compact.next_requests(values, window)
    restored = []
    for key, value in (("next_request", request), ("next_count", count)):
        artifact_bytes = read_source_artifact(root / "compact", receipt[key + "_artifact"])
        require(artifact_bytes == canonical_json(value).encode(), "source next request mismatch")
        restored.append(json.loads(artifact_bytes))
    # Keep even JSON member order from the frozen next-request artifacts.
    request, count = restored
    identity = {
        "collection_root": str(root), "result_hash": result_hash,
        "execution_hash": sha256_bytes((root / "execution.json").read_bytes()),
        "journal_hash": sha256_bytes(journal.path.read_bytes()),
        "receipt_hash": sha256_json(receipt),
        "child_journal_hash": sha256_bytes(child.path.read_bytes()),
        "source_contract": packet["source_contract"], "source_run_id": packet["source_run_id"],
        "source_state_root": packet["source_root"],
        "source_packet_root": binding["plan"]["packet_root"],
        "window_hash": receipt["window_hash"], "evidence": packet["evidence"],
        "request_hash": sha256_json(request), "count_hash": sha256_json(count),
    }
    return identity, request, count


def reservation(cap: Decimal, input_tokens: int) -> dict:
    ledger = DevCostLedger(cap, prices.RATES)
    quote = ledger.admit(input_tokens, desired_output_ceiling=OUTPUT_LIMIT,
                         minimum_output_ceiling=OUTPUT_LIMIT)
    require(quote is not None, "generation budget cannot cover unchanged output ceiling")
    return {"generation_cap_nanos": ledger.cap_nanos,
            "reserved_generation_nanos": quote.reserved_cost_nanos}


def inspect(collection_root: Path, result_hash: str, output: Path, env_file: Path,
            max_generation_cost_usd: Decimal, repeat: int) -> dict:
    require(type(repeat) is int and repeat == 1, "one response only")
    identity, request, count = source(collection_root, result_hash)
    output = design.new_external_root(output, collection_root,
                                     Path(identity["source_state_root"]),
                                     Path(identity["source_packet_root"]))
    env_file = env_file.resolve()
    require(env_file.is_file() and sha256_bytes(str(env_file).encode())
            == identity["source_contract"]["credential_file_path_hash"], "credential path mismatch")
    require(request["model"] == prices.MODEL and request["reasoning"] == {"effort": "medium"}
            and request["max_output_tokens"] == OUTPUT_LIMIT and request["store"] is False
            and request["service_tier"] == "default"
            and request["include"] == ["reasoning.encrypted_content"],
            "unexpected request settings")
    quote = reservation(max_generation_cost_usd, INPUT_LIMIT)
    plan = {
        **BOUNDARIES, "kind": KIND, "source": identity, "output_root": str(output),
        "credential_file_path_hash": identity["source_contract"]["credential_file_path_hash"],
        "repeat": 1, "input_token_limit": INPUT_LIMIT, "output_token_limit": OUTPUT_LIMIT,
        "max_generation_cost_usd": format(max_generation_cost_usd.normalize(), "f"),
        "reservation": quote, "prices": {
            "input_per_million_usd": "0.75", "cached_input_per_million_usd": "0.075",
            "output_per_million_usd": "4.50", "source": "https://developers.openai.com/api/docs/pricing",
        },
        "count_billing": "UNCONFIRMED_SEPARATELY_ACKNOWLEDGED_NOT_INCLUDED_IN_GENERATION_CAP",
        "total_invoice_cost_usd": None, "maximum_count_requests": 1,
        "maximum_generation_requests": 1,
        "waits": WAITS, "sdk_retries": 0, "runtime_hash": runtime_content_hash(),
        "implementation": {p.name: sha256_bytes(p.read_bytes()) for p in (
            Path(__file__), Path(prices.__file__), Path(transport.__file__),
        )},
        "request_metrics": compact.request_metrics(request),
        "count_hash": sha256_json(count),
        "assessment": ("provider admission, response/tool contract and continuation shape only; "
                       "no task execution"),
    }
    return {"execution_plan_hash": sha256_json(plan), "plan": plan,
            "credentials_loaded": 0, "api_requests": 0, "execution_granted": False}


def _usage(response) -> dict | None:
    value = getattr(response, "usage", None)
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude_unset=True, warnings=False)
    try:
        return compact.usage_fields({"usage": value})
    except (ContractError, TypeError, ValueError):
        return None


def assess(response, request, counted, store: ArtifactStore) -> dict:
    """Reuse the runtime parser with an in-memory response, not another HTTP request."""
    parser = OpenAIResponsesAdapter(model_config("medium"), api_key="", client=SimpleNamespace(
        max_retries=0, responses=SimpleNamespace(create=lambda **_: response)))
    raw = parser.execute_request({}, requested_input_tokens=counted)
    turn = _turn_from_openai(raw)
    continuation = None
    if turn.provider_continuation is not None:
        _validate_continuation_action_order(turn.provider_continuation, turn.tool_calls)
        continuation = _store_provider_continuation(store, turn.provider_continuation)
        _load_provider_continuation(store, continuation)
    shape, contract = None, "FAIL"
    if turn.error_code is None:
        try:
            shape = validate_tool_batch(turn.tool_calls,
                                        allowed_tools={t["name"] for t in request["tools"]})
            contract = "PASS_SHAPE_ONLY"
        except ContractError:
            pass
    cipher = [i.encrypted_content for i in (turn.provider_continuation.output_order
              if turn.provider_continuation else []) if i.type == "reasoning"]
    public = {
        **BOUNDARIES, "response_status": turn.response_status, "error_code": turn.error_code,
        "incomplete_reason": turn.incomplete_reason, "tool_batch_contract": contract,
        "batch_shape": shape, "tool_calls": [c.model_dump(mode="json") for c in turn.tool_calls],
        "output_item_types": turn.output_item_types,
        "continuation_ref": continuation.model_dump(mode="json") if continuation else None,
        "encrypted_item_count": len(cipher), "encrypted_chars": sum(map(len, cipher)),
        "largest_encrypted_chars": max(map(len, cipher), default=0),
        "source_admission": "NOT_RUN", "semantic_correctness": "NOT_ASSESSED",
    }
    ref = design.put_json(store, public)
    return {k: v for k, v in public.items() if k != "tool_calls"} | {
        "tool_names": [c.name for c in turn.tool_calls], "public_artifact": ref}


def _publish(output, journal, result):
    ref = design.put_json(ArtifactStore(output / "artifacts"), result)
    journal.append("terminal", {"result_artifact": ref, "result_hash": sha256_json(result)})
    ArtifactStore(output).write_text_immutable(output / "result.json", canonical_json(result))
    return result


def collect(collection_root: Path, result_hash: str, output: Path, env_file: Path,
            max_generation_cost_usd: Decimal, repeat: int, *, execution_plan_hash: str,
            accept_unconfirmed_count_billing: bool = False, client_factory=None,
            credential_loader=None, clock=monotonic, checkpoint=lambda _: None) -> dict:
    require(accept_unconfirmed_count_billing is True,
            "exact separate approval must acknowledge count billing outside generation cap")
    admission = inspect(collection_root, result_hash, output, env_file,
                        max_generation_cost_usd, repeat)
    require(admission["execution_plan_hash"] == execution_plan_hash, "execution plan mismatch")
    plan = admission["plan"]
    _, request, count_payload = source(collection_root, result_hash)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(output, "run_dev_compactnext_" + uuid.uuid4().hex[:16])
    ArtifactStore(output).write_text_immutable(output / "execution.json", canonical_json({
        "run_id": journal.run_id, "execution_plan_hash": execution_plan_hash, "plan": plan}))
    with journal.execution_lock():
        journal.append("followup_started", {"execution_plan_hash": execution_plan_hash,
                                           "unconfirmed_count_billing_acknowledged": True})
        deadline = ExecutionDeadline.from_remaining(WAITS["total_seconds"], clock=clock)
        reserve = WAITS["cleanup_reserve_seconds"]
        client, failure, counted, usage, assessment = None, None, None, None, None
        cost, count_attempts, generation_attempts = None, 0, 0
        cleanup, phase = {"status": "NOT_CREATED"}, "client_setup"
        outcome = "STOP_ERROR"
        try:
            deadline.check(reserve_seconds=reserve)
            key = (credential_loader or load_exact_openai_api_key)(env_file.resolve())
            try:
                client = (client_factory or transport.DiagnosticClient)(api_key=key)
            finally:
                del key
            require(client.max_retries == 0, "zero SDK retries required")
            timeout = deadline.bounded_timeout(WAITS["count_seconds"], reserve_seconds=reserve)
            journal.append("input_count_started", {"request_hash": plan["count_hash"]})
            checkpoint("count_dispatch_recorded")
            timeout = deadline.bounded_timeout(timeout, reserve_seconds=reserve)
            phase, count_attempts = "count_request", 1
            response = client.responses.input_tokens.count(**count_payload, timeout=timeout)
            observed_count = getattr(response, "input_tokens", None)
            require(getattr(response, "object", None) == "response.input_tokens"
                    and type(observed_count) is int and observed_count > 0, "invalid input count")
            counted = observed_count
            journal.append("input_count_finished", {"input_tokens": counted})
            checkpoint("count_recorded")
            phase = "generation_admission"
            require(counted <= INPUT_LIMIT, "input token limit exceeded")
            quote = reservation(max_generation_cost_usd, counted)
            require(sha256_json(request) == plan["source"]["request_hash"]
                    and sha256_json(OpenAIResponsesAdapter._count_payload(request))
                    == plan["count_hash"],
                    "request changed after count")
            timeout = deadline.bounded_timeout(WAITS["response_seconds"], reserve_seconds=reserve)
            journal.append("provider_call_started", {"request_hash": plan["source"]["request_hash"],
                                                      "input_tokens": counted, **quote})
            checkpoint("generation_dispatch_recorded")
            timeout = deadline.bounded_timeout(timeout, reserve_seconds=reserve)
            phase, generation_attempts = "generation_request", 1
            response = client.responses.create(**request, timeout=timeout)
            usage = _usage(response)
            response_id = getattr(response, "id", None)
            status = getattr(response, "status", None)
            metadata = {
                "response_id": response_id if isinstance(response_id, str)
                and re.fullmatch(r"resp_[\w-]{1,240}", response_id) else None,
                "response_model": prices.MODEL if getattr(response, "model", None)
                == prices.MODEL else None,
                "response_status": status if isinstance(status, str)
                and status in {"completed", "incomplete"} else None,
            }
            # Numeric usage survives parser, continuation, public-artifact and deadline failures.
            journal.append("provider_response_usage", {"usage": usage, **metadata})
            phase = "response_processing"
            checkpoint("usage_recorded")
            require(usage is not None and metadata["response_model"] == prices.MODEL
                    and metadata["response_status"] in {"completed", "incomplete"}
                    and isinstance(metadata["response_id"], str) and metadata["response_id"]
                    and usage["input_tokens"] == counted
                    and usage["output_tokens"] <= OUTPUT_LIMIT
                    and usage["input_tokens_details"].get("cache_write_tokens", 0) == 0,
                    "generation usage/model contract mismatch")
            cost = DevCostLedger(max_generation_cost_usd, prices.RATES).settle(
                input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
                cached_input_tokens=usage["input_tokens_details"]["cached_tokens"])
            require(cost <= quote["reserved_generation_nanos"], "generation reservation exceeded")
            journal.append("generation_accounted", {"model_rate_cost_nanos": cost})
            assessment = assess(response, request, counted, ArtifactStore(output / "artifacts"))
            journal.append("response_assessed", assessment)
            checkpoint("assessment_recorded")
            deadline.check(reserve_seconds=reserve)
            outcome = "RESPONSE_COLLECTED"
        except (Exception, KeyboardInterrupt, SystemExit) as error:
            failure = {"phase": phase, **failure_evidence(error)}
        finally:
            if client is not None:
                timeout = min(reserve, deadline.remaining_seconds())
                try:
                    client.close(timeout=timeout)
                    cleanup = {"status": "CLOSED", "timeout_seconds": timeout}
                except (Exception, KeyboardInterrupt, SystemExit) as error:
                    cleanup = {"status": "UNKNOWN", "error": failure_evidence(error)}
                journal.append("client_cleanup", cleanup)
        result = {
            **BOUNDARIES, "kind": KIND, "run_id": journal.run_id,
            "execution_plan_hash": execution_plan_hash,
            "result": "STOP_CLEANUP_UNKNOWN" if cleanup["status"] == "UNKNOWN" else outcome,
            "count_attempts": count_attempts, "generation_attempts": generation_attempts,
            "input_tokens": counted, "usage": usage, "generation_model_rate_cost_nanos": cost,
            "count_billing": plan["count_billing"], "total_invoice_cost_usd": None,
            "assessment": assessment, "failure": failure, "cleanup": cleanup,
        }
        return _publish(output, journal, result)


def inspect_result(output: Path) -> dict:
    """Completed evidence or conservative interrupted status; never retry or mutate."""
    binding = json.loads((output / "execution.json").read_bytes())
    require(sha256_json(binding["plan"]) == binding["execution_plan_hash"],
            "execution binding mismatch")
    journal = DevJournal(output, binding["run_id"])
    events = journal.events()
    terminals = [e["payload"] for e in events if e["event_type"] == "terminal"]
    if terminals:
        require(len(terminals) == 1, "duplicate terminal")
        raw = read_source_artifact(output, terminals[0]["result_artifact"])
        require(sha256_bytes(raw) == terminals[0]["result_hash"], "terminal result hash mismatch")
        result = json.loads(raw)
        assessment = result.get("assessment")
        if assessment:
            read_source_artifact(output, assessment["public_artifact"])
            ref = assessment.get("continuation_ref")
            if ref:
                from patchloop.dev.contracts import ProviderContinuationRef

                _load_provider_continuation(ArtifactStore(output / "artifacts"),
                                            ProviderContinuationRef.model_validate(ref))
        return result
    return {**BOUNDARIES, "result": "INTERRUPTED_NO_RETRY", "run_id": journal.run_id,
            "admitted_counts": sum(e["event_type"] == "input_count_started" for e in events),
            "admitted_generations": sum(e["event_type"] == "provider_call_started" for e in events),
            "count_attempts": None, "generation_attempts": None, "total_invoice_cost_usd": None,
            "durable_usage": [e["payload"] for e in events
                              if e["event_type"] == "provider_response_usage"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("inspect", "collect"):
        p = modes.add_parser(mode)
        for name in ("collection-root", "output", "env-file"):
            p.add_argument("--" + name, type=Path, required=True)
        p.add_argument("--result-hash", required=True)
        p.add_argument("--max-generation-cost-usd", type=Decimal, required=True)
        p.add_argument("--repeat", type=int, choices=[1], required=True)
        if mode == "collect":
            p.add_argument("--execution-plan-hash", required=True)
            p.add_argument("--accept-unconfirmed-count-billing", action="store_true")
    modes.add_parser("result").add_argument("--output", type=Path, required=True)
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    try:
        result = {"inspect": inspect, "collect": collect, "result": inspect_result}[mode](**args)
    except (Exception, KeyboardInterrupt, SystemExit) as error:
        print(canonical_json({"result": "STOP_ERROR", "failure": failure_evidence(error)}))
        raise SystemExit(2) from None
    print(canonical_json(result))
    if mode != "inspect" and result["result"] != "RESPONSE_COLLECTED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
