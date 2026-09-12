"""Opt-in collector for the frozen compacted short episode; never a native resume.

Inspect is provider-free. Collect needs a new exact execution-plan approval and
separate acknowledgement of unconfirmed count billing. Result is read-only, even
after an interrupted process. Existing packets and the native agent are unchanged.
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

from diagnostics import compaction_episode as episode
from diagnostics import compaction_followup as followup
from diagnostics import episode_requests as transport
from diagnostics.decision_sampler import read_source_artifact, require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.contracts import ProviderContinuationRef
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

KIND = "compaction-short-episode-collector-v1"
BOUNDARIES = {
    **episode.BOUNDARIES,
    "automatic_retry_or_resume": False,
    "compaction_requests": 0,
    "total_invoice_cost_usd": None,
}
PRICES = {
    "model": followup.prices.MODEL,
    "service_tier": "default",
    "input_per_million_usd": "0.75",
    "cached_input_per_million_usd": "0.075",
    "output_per_million_usd": "4.50",
    "source": "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
    "count_source": "https://developers.openai.com/api/docs/guides/token-counting",
}


def implementation():
    return {
        **episode.implementation(),
        "collector_hash": sha256_bytes(Path(__file__).read_bytes()),
        "pricing_hash": sha256_bytes(Path(followup.prices.__file__).read_bytes()),
    }


def inspect(
    packet_root: Path,
    packet_hash: str,
    output: Path,
    env_file: Path,
    max_generation_cost_usd: Decimal,
    repeat: int,
    prices_verified_on: str,
) -> dict:
    require(type(repeat) is int and repeat == 1, "one diagnostic episode only")
    require(prices_verified_on == utc_now().date().isoformat(), "current price review required")
    source, packet = episode.verify(packet_root, packet_hash)
    output = episode.compact.new_external_root(
        output, packet_root, source.source_root, source.collection_root
    )
    credential_hash = source.identity["credential_file_path_hash"]
    env_file = env_file.resolve()
    require(
        env_file.is_file() and sha256_bytes(str(env_file).encode()) == credential_hash,
        "credential path mismatch",
    )
    quote = followup.reservation(max_generation_cost_usd, followup.INPUT_LIMIT)
    request = source.request
    require(
        request["model"] == PRICES["model"]
        and request["reasoning"] == {"effort": "medium"}
        and request["service_tier"] == "default"
        and request["store"] is False
        and request["max_output_tokens"] == 25000
        and request["include"] == ["reasoning.encrypted_content"],
        "frozen model settings differ",
    )
    remaining = (
        source.state["remaining_budget"]["active_wall_time_seconds"]
        - source.identity["seed_active_seconds"]
    )
    require(remaining > transport.WAITS.client_cleanup_seconds, "no execution time remains")
    plan = {
        **BOUNDARIES,
        "kind": KIND,
        "packet_root": str(packet_root.resolve()),
        "packet_hash": packet_hash,
        "source": source.identity,
        "output_root": str(output),
        "credential_file_path_hash": credential_hash,
        "repeat": 1,
        "model": PRICES["model"],
        "reasoning": "medium",
        "output_ceiling": 25000,
        "input_limit": followup.INPUT_LIMIT,
        "global_limits": packet["global_limits"],
        "max_new_responses": packet["max_new_responses"],
        "max_new_input_counts": packet["max_new_input_counts"],
        "seed_executions": 1,
        "seed_generation_repeated": False,
        "seed_generation_charged_to_new_cap": False,
        "max_generation_cost_usd": format(max_generation_cost_usd.normalize(), "f"),
        "initial_reservation": quote,
        "reservation_policy": "shared ledger; JIT uncached input plus unchanged 25k output",
        "prices": PRICES,
        "prices_verified_on": prices_verified_on,
        "count_billing": "UNCONFIRMED_SEPARATELY_ACKNOWLEDGED_NOT_INCLUDED_IN_GENERATION_CAP",
        "waits": {
            **transport.WAITS.contract(),
            "total_seconds": remaining,
            "cleanup_reserve_inside_inherited_budget": True,
        },
        "sandbox": {
            key: source.identity[key]
            for key in ("evaluator_image_digest", "probe_image_digest", "probe_profile_hash")
        },
        "repair_recheck": source.identity["repair_recheck"],
        "docker_start_pull_build": False,
        "implementation": implementation(),
        "assessment": "short public loop behavior; no hidden acceptance or causal claim",
    }
    return {
        "execution_plan_hash": sha256_json(plan),
        "plan": plan,
        "api_requests": 0,
        "credentials_loaded": 0,
        "execution_granted": False,
    }


def source_preflight(source, *, deadline):
    task_dir = Path(source.identity["task_dir"])
    loop._live_task_is_admitted(task_dir, source.package)
    loop._live_source_preflight(task_dir, source.package, deadline=deadline)
    # Bound diagnostic code must also be tracked and HEAD-clean, not just native runtime.
    root = repository_root()
    modules = set(implementation()["modules"]) | {Path(__file__).name, "compaction_cost.py"}
    loop._require_tracked_clean_paths(
        root, ["diagnostics/" + name for name in sorted(modules)], deadline=deadline
    )


def live_backends(source, *, deadline):
    sandbox = loop._live_sandbox_preflight(source.package, deadline=deadline)
    require(
        source.package.environment.image_digest == source.identity["evaluator_image_digest"],
        "checkpoint evaluator identity differs",
    )
    probe = None
    if source.identity["probe_image_digest"] is not None:
        probe = DockerProbeSandbox()
        require(
            probe.preflight(deadline=deadline)
            == {
                "image_digest": source.identity["probe_image_digest"],
                "profile_hash": source.identity["probe_profile_hash"],
            },
            "checkpoint probe identity differs",
        )
    return sandbox, probe


class MeteredAdapter(OpenAIResponsesAdapter):
    """Record numeric usage before parsing; do not discard unknown billing components."""

    def __init__(self, client, journal):
        super().__init__(followup.model_config("medium"), api_key="", client=client)
        self.journal = journal

    def _attempt(self, kind):
        events = self.journal.events()
        event = next(e for e in reversed(events) if e["event_type"] == kind + "_started")
        payload = event["payload"]
        identity = {key: payload[key] for key in ("turn_id", "request_hash")}
        self.journal.append("collector_request_attempted", {"kind": kind, **identity})
        return identity

    def count_input_tokens_v2(self, request, *, timeout_seconds=None):
        self._attempt("input_count")
        result = self.client.responses.input_tokens.count(
            **self._count_payload(request), timeout=timeout_seconds
        )
        require(
            getattr(result, "object", None) == "response.input_tokens"
            and type(getattr(result, "input_tokens", None)) is int
            and result.input_tokens > 0,
            "invalid input count",
        )
        return result.input_tokens

    def execute_request(self, request, *, requested_input_tokens, timeout_seconds=None):
        identity = self._attempt("provider_call")
        response = self.client.responses.create(**request, timeout=timeout_seconds)
        usage = followup._usage(response)
        response_id = getattr(response, "id", None)
        status = getattr(response, "status", None)
        tier = getattr(response, "service_tier", None)
        billing_shape_known = (
            usage is not None
            and usage["input_tokens_details"].get("cache_write_tokens", 0) == 0
            and (tier is None or tier == "default")
        )
        self.journal.append(
            "collector_usage_observed",
            {
                **identity,
                "usage": usage if usage is not None else _numeric_usage(response),
                "billing_shape_known": billing_shape_known,
                "response_id": response_id
                if isinstance(response_id, str) and re.fullmatch(r"resp_[\w-]{1,240}", response_id)
                else None,
                "response_model": PRICES["model"]
                if getattr(response, "model", None) == PRICES["model"]
                else None,
                "response_status": status
                if isinstance(status, str) and status in {"completed", "incomplete"}
                else None,
            },
        )
        if not billing_shape_known:
            # Do not let the dispatcher's parser-only usage salvage settle unknown charges.
            self.client.phase = "provider_usage_validation"
            raise ValueError("unpriced response usage")
        # Parse this exact object with the existing parser; no second HTTP call.
        parser = OpenAIResponsesAdapter(
            self.config,
            api_key="",
            client=SimpleNamespace(
                max_retries=0, responses=SimpleNamespace(create=lambda **_: response)
            ),
        )
        return parser.execute_request(request, requested_input_tokens=requested_input_tokens)


def _numeric_usage(response):
    """Keep bounded counters even when their arithmetic/shape fails validation."""
    usage = getattr(response, "usage", None)

    def fields(value, keys):
        return {
            key: n if type(n := getattr(value, key, None)) is int and 0 <= n < 2**63 else None
            for key in keys
        }

    return {
        **fields(usage, ("input_tokens", "output_tokens", "total_tokens")),
        "input_tokens_details": fields(
            getattr(usage, "input_tokens_details", None), ("cached_tokens", "cache_write_tokens")
        ),
        "output_tokens_details": fields(
            getattr(usage, "output_tokens_details", None), ("reasoning_tokens",)
        ),
    }


def _journal(root: Path, run_id: str) -> DevJournal:
    """Construct a read-only view without mkdir or lock-file writes."""
    require(run_id.startswith("run_dev_") and run_id.replace("_", "").isalnum(), "invalid run ID")
    journal = object.__new__(DevJournal)
    journal.root, journal.run_id = root.resolve(), run_id
    journal.path = journal.root / "runs" / (run_id + ".jsonl")
    return journal


def _validate_artifacts(root, value):
    if isinstance(value, list):
        for item in value:
            _validate_artifacts(root, item)
    elif isinstance(value, dict):
        if {"artifact_id", "path", "content_hash", "size_bytes", "media_type"} <= value.keys():
            read_source_artifact(root, value)
        else:
            for item in value.values():
                _validate_artifacts(root, item)


def _child_evidence(output: Path, *, validate=False) -> dict:
    root = output / "episode"
    if not (root / "execution.json").is_file():
        return {
            "created": False,
            "admitted_counts": 0,
            "admitted_generations": 0,
            "known_generation_cost_nanos": 0,
            "generation_billing_complete": True,
            "terminal": None,
            "usage": [],
            "admitted_tool_actions": 0,
        }
    binding = json.loads((root / "execution.json").read_bytes())
    require(binding["packet_hash"] == sha256_json(binding["packet"]), "child binding mismatch")
    journal = _journal(root, binding["run_id"])
    events = journal.events()
    if validate:
        for event in events:
            _validate_artifacts(root, event["payload"])
            ref = event["payload"].get("continuation_ref")
            if ref is not None:
                loop._load_provider_continuation(
                    episode.engine.readonly_store(root / "artifacts"),
                    ProviderContinuationRef.model_validate(ref),
                )
    new = [e for e in events if not e["payload"].get("diagnostic_inherited")]
    starts = [e["payload"] for e in new if e["event_type"] == "provider_call_started"]
    finished = [e["payload"] for e in new if e["event_type"] == "provider_call_finished"]
    usage = [e["payload"] for e in new if e["event_type"] == "collector_usage_observed"]
    known = [u for u in finished if u.get("billing_known") and type(u.get("cost_nanos")) is int]
    terminals = [e["payload"] for e in new if e["event_type"] == "terminal"]
    require(len(terminals) <= 1, "duplicate episode terminal")
    return {
        "created": True,
        "run_id": journal.run_id,
        "packet_hash": binding["packet_hash"],
        "journal_hash": sha256_bytes(journal.path.read_bytes()) if journal.path.is_file() else None,
        "admitted_counts": sum(e["event_type"] == "input_count_started" for e in new),
        "admitted_generations": len(starts),
        "generation_billing_complete": len(known) == len(starts)
        and all(u["billing_shape_known"] for u in usage),
        "known_generation_cost_nanos": sum(u["cost_nanos"] for u in known),
        "usage": usage,
        "terminal": terminals[0] if terminals else None,
        "seed_started": any(e["event_type"] == "compacted_seed_started" for e in new),
        "seed_finished": any(e["event_type"] == "compacted_seed_finished" for e in new),
        "admitted_tool_actions": sum(
            len(e["payload"]["tool_calls"]) if e["event_type"] == "tool_batch_started" else 1
            for e in new
            if e["event_type"] in {"tool_batch_started", "repair_recheck_started"}
        ),
    }


def _publish(output, journal, result, checkpoint):
    ref = ArtifactStore(output / "artifacts").put_text(canonical_json(result), "application/json")
    journal.append(
        "terminal",
        {"result_artifact": ref.model_dump(mode="json"), "result_hash": ref.content_hash},
    )
    checkpoint("terminal_recorded")
    ArtifactStore(output).write_text_immutable(output / "result.json", canonical_json(result))
    return result


def collect(
    packet_root: Path,
    packet_hash: str,
    output: Path,
    env_file: Path,
    max_generation_cost_usd: Decimal,
    repeat: int,
    prices_verified_on: str,
    *,
    execution_plan_hash: str,
    accept_unconfirmed_count_billing: bool = False,
    client_factory=None,
    credential_loader=None,
    backend_factory=None,
    clock=monotonic,
    checkpoint=lambda _: None,
) -> dict:
    require(
        accept_unconfirmed_count_billing is True, "separate count billing acknowledgement required"
    )
    admission = inspect(
        packet_root,
        packet_hash,
        output,
        env_file,
        max_generation_cost_usd,
        repeat,
        prices_verified_on,
    )
    require(admission["execution_plan_hash"] == execution_plan_hash, "execution plan mismatch")
    source, packet = episode.verify(packet_root, packet_hash)
    plan, output = admission["plan"], output.resolve()
    started = clock()
    deadline = ExecutionDeadline.from_remaining(plan["waits"]["total_seconds"], clock=clock)
    reserve = transport.WAITS.client_cleanup_seconds
    work_deadline = ExecutionDeadline(deadline.expires_at - reserve, clock)
    output.mkdir(
        parents=True, exist_ok=False
    )  # Atomic destination claim before any live operation.
    journal = DevJournal(output, "run_dev_compactcollectloop_" + uuid.uuid4().hex[:16])
    execution_mode = (
        "injected"
        if any(f is not None for f in (client_factory, credential_loader, backend_factory))
        else "live"
    )
    binding = {
        "run_id": journal.run_id,
        "execution_plan_hash": execution_plan_hash,
        "plan": plan,
        "execution_mode": execution_mode,
    }
    ArtifactStore(output).write_text_immutable(output / "execution.json", canonical_json(binding))
    with journal.execution_lock():
        journal.append(
            "collector_started",
            {
                "execution_plan_hash": execution_plan_hash,
                "count_billing_acknowledged": True,
                "execution_mode": execution_mode,
            },
        )
        branch = client = failure = None
        cleanup, phase, outcome = {"status": "NOT_CREATED"}, "source_preflight", "EXECUTION_ERROR"
        ledger = DevCostLedger(max_generation_cost_usd, followup.prices.RATES)
        inherited_elapsed = (
            source.envelope["limits"]["wall_time_seconds"]
            - source.state["remaining_budget"]["active_wall_time_seconds"]
            + source.identity["seed_active_seconds"]
        )
        try:
            work_deadline.check()
            source_preflight(source, deadline=work_deadline)
            phase = "sandbox_preflight"
            sandbox, probe = (backend_factory or live_backends)(source, deadline=work_deadline)
            journal.append("sandbox_preflight_finished", plan["sandbox"])
            checkpoint("preflight_finished")
            phase = "checkpoint_initialization"
            branch = episode.initialize(
                source,
                packet,
                output / "episode",
                sandbox,
                probe_sandbox=probe,
                clock=clock,
                execution_deadline=work_deadline,
            )
            journal.append("episode_initialized", {"run_id": branch.journal.run_id})
            checkpoint("episode_initialized")
            phase = "seed_execution"
            branch.base_elapsed = inherited_elapsed + clock() - started - branch.clock()
            episode.execute_seed(branch, checkpoint=checkpoint)
            journal.append("seed_execution_finished", {"new_provider_calls": 0})
            checkpoint("seed_finished")
            while branch.terminal is None:
                work_deadline.check()
                branch.base_elapsed = inherited_elapsed + clock() - started - branch.clock()
                # Do not load credentials after an exhausted horizon/observation window.
                with branch.clock.active(), branch.journal.execution_lock():
                    shape_adapter = SimpleNamespace(
                        config=followup.model_config("medium"),
                        client=SimpleNamespace(max_retries=0),
                    )
                    prepared = branch.prepare_request(source.package, shape_adapter)
                if prepared is None:
                    break
                if client is None:
                    phase = "client_setup"
                    work_deadline.check()
                    key = (credential_loader or load_exact_openai_api_key)(env_file.resolve())
                    try:
                        client = (client_factory or transport.DiagnosticClient)(api_key=key)
                    finally:
                        del key
                    require(client.max_retries == 0, "zero SDK retries required")
                    checkpoint("client_created")
                phase = "provider_step"
                branch.base_elapsed = inherited_elapsed + clock() - started - branch.clock()
                with branch.clock.active(), branch.journal.execution_lock():
                    episode.engine.dispatch(
                        branch,
                        MeteredAdapter(client, branch.journal),
                        ledger,
                        prepared,
                        checkpoint=checkpoint,
                        request_waits=transport.WAITS,
                    )
                journal.append(
                    "step_finished",
                    {
                        "new_provider_calls": branch.new_provider_calls,
                        "spent_generation_nanos": ledger.spent_nanos,
                    },
                )
                checkpoint("step_finished")
            outcome = branch.terminal["terminal"]
        except (Exception, KeyboardInterrupt, SystemExit) as exc:
            failure = {"phase": phase, **transport.exception_evidence(exc)}
            if branch is not None:
                episode._abort(branch, exc)
                outcome = branch.terminal["terminal"]
            elif isinstance(exc, ExecutionDeadlineExceeded):
                outcome = "LIMIT_REACHED"
            journal.append("collector_failed", failure)
        finally:
            if client is not None:
                timeout = min(reserve, deadline.remaining_seconds())
                try:
                    client.close(timeout=timeout)
                    cleanup = {"status": "CLOSED", "timeout_seconds": timeout}
                except (Exception, KeyboardInterrupt, SystemExit) as exc:
                    cleanup = {"status": "UNKNOWN", "error": transport.exception_evidence(exc)}
                journal.append("client_cleanup", cleanup)
        evidence = _child_evidence(output)
        if not evidence["generation_billing_complete"]:
            outcome = "PROVIDER_TIMEOUT_OR_UNKNOWN"
        elif cleanup["status"] == "UNKNOWN" and outcome != "COUNT_TIMEOUT_OR_UNKNOWN":
            outcome = "STOP_CLEANUP_UNKNOWN"
        result = {
            **BOUNDARIES,
            "kind": KIND,
            "run_id": journal.run_id,
            "execution_plan_hash": execution_plan_hash,
            "result": outcome,
            "execution_mode": execution_mode,
            "episode": evidence,
            "failure": failure,
            "cleanup": cleanup,
            "active_elapsed_ms": int((clock() - started) * 1000),
            "known_generation_cost_nanos": evidence["known_generation_cost_nanos"],
            "generation_billing_complete": evidence["generation_billing_complete"],
            "count_billing": plan["count_billing"],
        }
        return _publish(output, journal, result, checkpoint)


def inspect_result(output: Path) -> dict:
    """Read completed or partial evidence; never reopen client, workspace or source run."""
    output = output.resolve()
    binding = json.loads((output / "execution.json").read_bytes())
    require(
        binding["plan"]["kind"] == KIND
        and sha256_json(binding["plan"]) == binding["execution_plan_hash"],
        "binding mismatch",
    )
    events = _journal(output, binding["run_id"]).events()
    terminals = [e["payload"] for e in events if e["event_type"] == "terminal"]
    require(len(terminals) <= 1, "duplicate collector terminal")
    evidence = _child_evidence(output, validate=True)
    if evidence["created"]:
        require(evidence["packet_hash"] == binding["plan"]["packet_hash"], "child packet mismatch")
    if terminals:
        raw = read_source_artifact(output, terminals[0]["result_artifact"])
        require(sha256_bytes(raw) == terminals[0]["result_hash"], "result hash mismatch")
        result = json.loads(raw)
        require(
            result["episode"] == evidence
            and result["execution_plan_hash"] == binding["execution_plan_hash"]
            and result["execution_mode"] == binding["execution_mode"],
            "result evidence mismatch",
        )
        if (output / "result.json").exists():
            require((output / "result.json").read_bytes() == raw, "published result differs")
        return result
    return {
        **BOUNDARIES,
        "kind": KIND,
        "run_id": binding["run_id"],
        "result": "INCOMPLETE_NO_RETRY",
        "execution_mode": binding["execution_mode"],
        "episode": evidence,
        "execution_plan_hash": binding["execution_plan_hash"],
        "cleanup": next(
            (e["payload"] for e in reversed(events) if e["event_type"] == "client_cleanup"),
            {"status": "UNKNOWN"},
        ),
        "count_billing": binding["plan"]["count_billing"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("inspect", "collect"):
        p = modes.add_parser(mode)
        for name in ("packet-root", "output", "env-file"):
            p.add_argument("--" + name, type=Path, required=True)
        p.add_argument("--packet-hash", required=True)
        p.add_argument("--max-generation-cost-usd", type=Decimal, required=True)
        p.add_argument("--repeat", type=int, choices=[1], required=True)
        p.add_argument("--prices-verified-on", required=True)
        if mode == "collect":
            p.add_argument("--execution-plan-hash", required=True)
            p.add_argument("--accept-unconfirmed-count-billing", action="store_true")
    modes.add_parser("result").add_argument("--output", type=Path, required=True)
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    try:
        result = {"inspect": inspect, "collect": collect, "result": inspect_result}[mode](**args)
    except (Exception, KeyboardInterrupt, SystemExit) as exc:
        print(
            canonical_json({"result": "STOP_ERROR", "failure": transport.exception_evidence(exc)})
        )
        raise SystemExit(2) from None
    print(canonical_json(result))
    if mode != "inspect" and result["result"] != "PUBLIC_CHECKS_SUBMITTED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
