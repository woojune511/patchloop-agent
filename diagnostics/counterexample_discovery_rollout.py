"""One bounded fixed-candidate discovery session, with read-only interrupted inspection.

The frozen design stays unchanged. Reuse the counted diagnostic dispatcher, native
exchange builder and public gateway; do not resume a solve or run private evaluation.
"""
from __future__ import annotations

import argparse
import copy
import json
import uuid
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from time import monotonic
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from diagnostics import counterexample_discovery as design
from diagnostics import episode_requests as requests
from diagnostics import fresh_state_rollout as engine
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, validate_tool_batch
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import load_dependencies, read_descriptor
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_paths
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SCHEMA = "counterexample-discovery-rollout-v1"
RUN_ID = "run_dev_discovery"
CAP = Decimal("1.20")
INPUT_LIMIT = 60_000
TOOL_NAMES = frozenset({"read_file", "search_files", "run_probe"})
BOUNDARIES = {"official": False, "claim_eligible": False, "private_evaluation": "NOT_RUN",
              "task_acceptance": "NOT_ASSESSED", "resume_allowed": False}


class DiscoveryReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    outcome: Literal["counterexample_reported", "no_counterexample_found", "blocked"]
    requirement_excerpt: str | None = Field(max_length=600)
    justification: str = Field(min_length=1, max_length=2_000)
    probe_action_id: str | None = Field(max_length=500)
    expected: str | None = Field(max_length=2_000)
    observed: str | None = Field(max_length=2_000)
    limitations: str = Field(max_length=2_000)


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def implementation_hashes() -> dict:
    names = ("counterexample_discovery_rollout", "counterexample_discovery", "episode_requests",
             "fresh_state_rollout", "fresh_state_design", "fresh_state_sampler", "decision_sampler")
    return {f"diagnostics/{name}.py": sha256_bytes(
        (repository_root() / "diagnostics" / f"{name}.py").read_bytes()) for name in names}


def configuration() -> ModelConfig:
    return ModelConfig(provider="openai", model_id=design.MODEL, reasoning_effort="medium",
                       reasoning_continuation="encrypted-v1", transport_max_retries=0,
                       max_output_tokens=25_000)


def plan_for(design_root: Path, result_root: Path, pricing_verified_on: str) -> dict:
    packet = design.validate(design_root)
    return {
        "schema_version": SCHEMA, "status": "READY", **BOUNDARIES,
        "design_root": str(design_root.resolve()), "design_packet_hash": sha256_json(packet),
        "request_hash": packet["request_hash"],
        "request_file_hash": sha256_bytes((design_root / "request.json").read_bytes()),
        "result_root": str(result_root.resolve()), "runtime_hash": packet["runtime_hash"],
        "implementation_hashes": implementation_hashes(), "model": design.MODEL,
        "reasoning_effort": "medium", "credential_file": str(repository_root() / ".env"),
        "repeat": 1, "cap_usd": str(CAP), "cap_nanos": usd_to_nanos(CAP),
        "max_model_calls": 40, "max_tool_actions": 100, "wall_time_seconds": 1800,
        "max_input_tokens": INPUT_LIMIT, "max_output_tokens": 25_000,
        "request_waits": requests.WAITS.contract(),
        "pricing": {k: str(v) for k, v in asdict(pricing_for_model(design.MODEL)).items()},
        "pricing_source": "https://developers.openai.com/api/docs/pricing",
        "pricing_verified_on": pricing_verified_on,
        "report_is_not_a_verdict": True, "no_retry_or_replacement": True,
        "fresh_request_unchanged": True,
    }


def prepare(design_root: Path, output: Path, result_root: Path, pricing_verified_on: str) -> dict:
    design.require(pricing_verified_on == utc_now().date().isoformat(),
                   "current price review date required")
    packet = design.validate(design_root)
    protected = [design_root, *(Path(v).parent for v in packet["inputs"].values())]
    output = design.fresh_external_root(output, protected)
    result_root = design.fresh_external_root(result_root, [output, *protected])
    plan = plan_for(design_root, result_root, pricing_verified_on)
    output.mkdir(exist_ok=False)
    store = ArtifactStore(output)
    store.write_text_immutable(output / "request.json",
                               (design_root / "request.json").read_bytes().decode())
    DevJournal(output, "run_dev_discovery_executable").append("diagnostic_packet_prepared", {
        "plan_hash": sha256_json(plan), "provider_calls": 0, **BOUNDARIES,
    })
    store.write_text_immutable(output / "plan.json", design.wire(plan).decode())
    return plan


def validate(root: Path) -> dict:
    plan = read(root / "plan.json")
    expected = plan_for(Path(plan["design_root"]), Path(plan["result_root"]),
                        plan["pricing_verified_on"])
    design.require(plan == expected, "executable packet, implementation or inputs changed")
    design.require(sha256_bytes((root / "request.json").read_bytes()) == plan["request_file_hash"],
                   "initial request bytes changed")
    preparation_id = "run_dev_discovery_executable"
    design.require((root / "runs" / f"{preparation_id}.jsonl").is_file(),
                   "executable preparation journal missing")
    events = DevJournal(root, preparation_id).events()
    design.require(len(events) == 1 and events[0]["event_type"] == "diagnostic_packet_prepared"
                   and events[0]["payload"]["plan_hash"] == sha256_json(plan),
                   "preparation journal does not bind the executable packet")
    return plan


class DiscoveryLedger(DevCostLedger):
    def admit(self, input_tokens, **kwargs):
        # The shared dispatcher has an older 272K bound. This diagnostic pins 60K
        # after a successful count and before its full-ceiling cost admission.
        if input_tokens > INPUT_LIMIT:
            raise engine.AbortExperiment("INPUT_LIMIT_EXCEEDED")
        return super().admit(input_tokens, **kwargs)


def report_evidence(report: DiscoveryReport, gateway: DevToolGateway) -> dict:
    """Bind recorded evidence, never infer semantic success from a claimed mismatch."""
    events = gateway.journal.events()
    matches = [e["payload"]["result"] for e in events if e["event_type"] == "action_finished"
               and e["payload"]["result"].get("action_id") == report.probe_action_id
               and e["payload"]["result"].get("tool") == "run_probe"]
    starts = [e["payload"] for e in events if e["event_type"] == "action_started"
              and e["payload"].get("action_id") == report.probe_action_id]
    text = " ".join((gateway.public_task.issue.title + " "
                     + gateway.public_task.issue.description).split())
    excerpt = " ".join((report.requirement_excerpt or "").split())
    result = matches[0] if len(matches) == len(starts) == 1 else None
    output = result["output"] if result else {}
    source = starts[0].get("arguments", {}).get("python_source") if result else None
    bound = bool(result and result["input_hash"] == starts[0]["input_hash"]
                 and isinstance(source, str)
                 and output.get("source_hash") == sha256_bytes(source.encode())
                 and output.get("diff_hash") == gateway.current_diff_hash)
    complete = bool(bound and result["status"] == "succeeded"
                    and output.get("status") in {"passed", "failed"}
                    and type(output.get("exit_code")) is int
                    and all(output.get(flag) is False for flag in (
                        "timed_out", "truncated", "cleanup_failed", "deadline_exhausted"))
                    and output.get("execution_policy", {}).get("cleanup_status") == "confirmed")
    return {"review_status": "PUBLIC_REVIEW_REQUIRED", "semantic_verdict": None,
            "requirement_excerpt_matches_issue": bool(excerpt and excerpt in text),
            "probe_identity_bound": bound, "complete_probe_receipt": complete,
            "probe_result": result, "program": source,
            "limits": "Execution and an excerpt match do not establish the expectation, "
                      "current-code invocation, or a real behavioral contradiction."}


class Session:
    def __init__(self, request, gateway, store, *, probe_identity, clock=monotonic):
        self.seed = copy.deepcopy(request)
        self.items = copy.deepcopy(request["input"])
        self.gateway, self.journal, self.store = gateway, gateway.journal, store
        self.clock, self.started = clock, clock()
        self.counters = loop._RunCounters()
        self.new_provider_calls = self.new_cost_nanos = self.new_tools = 0
        self.fixed_diff = gateway.current_diff_hash
        self.probe_identity = probe_identity
        self.report = None

    def elapsed_ms(self):
        return int((self.clock() - self.started) * 1000)

    def verify_candidate(self):
        if self.gateway.current_diff_hash != self.fixed_diff:
            raise engine.AbortExperiment("CANDIDATE_IDENTITY_CHANGED")

    def prepare_request(self):
        self.gateway.deadline.check()
        self.verify_candidate()
        if self.new_provider_calls >= self.gateway.limits.max_model_calls:
            raise engine.AbortExperiment("MODEL_CALL_LIMIT")
        if self.new_tools >= self.gateway.limits.max_tool_actions:
            raise engine.AbortExperiment("TOOL_ACTION_LIMIT")
        request = {**copy.deepcopy(self.seed), "input": copy.deepcopy(self.items)}
        turn_id = "turn_" + uuid.uuid4().hex
        ref = self.store.put_text(canonical_json(request["input"]), "application/json")
        self.journal.append("turn_started", {
            "turn_id": turn_id, "model_input_artifact": ref.model_dump(mode="json"),
            "model_input_hash": ref.content_hash, "workflow_gate": "fixed_candidate_review",
            "available_tool_names": sorted([*TOOL_NAMES, "report_discovery"]),
            "active_elapsed_ms": self.elapsed_ms(),
        })
        return turn_id, request, None

    def accept(self, turn_id, turn, policy, checkpoint):
        self.journal.append("turn_decision_recorded", {
            "turn_id": turn_id, **turn.model_dump(mode="json", exclude={"provider_continuation"}),
        })
        checkpoint("decision_recorded")
        if turn.error_code:
            raise engine.AbortExperiment("INCOMPLETE_RESPONSE" if
                                         turn.error_code == "incomplete_response" else
                                         "PROTOCOL_VIOLATION")
        if set(turn.output_item_types) - {"reasoning", "function_call"}:
            raise engine.AbortExperiment("PROTOCOL_VIOLATION")
        calls = turn.tool_calls
        used = {c["action_id"] for e in self.journal.events()
                if e["event_type"] == "tool_batch_started" for c in e["payload"]["tool_calls"]}
        if (not calls or len({c.action_id for c in calls}) != len(calls)
                or any(c.action_id in used for c in calls)):
            raise engine.AbortExperiment("PROTOCOL_VIOLATION")
        if self.new_tools + len(calls) > self.gateway.limits.max_tool_actions:
            raise engine.AbortExperiment("TOOL_ACTION_LIMIT")
        try:
            if len(calls) == 1 and calls[0].name == "report_discovery":
                report = DiscoveryReport.model_validate(calls[0].arguments)
                design.require(calls[0].turn_decision is None, "unexpected report annotation")
            else:
                report = None
                validate_tool_batch(calls, allowed_tools=TOOL_NAMES)
        except (ContractError, ValidationError):
            raise engine.AbortExperiment("PROTOCOL_VIOLATION") from None
        self.verify_candidate()
        self.journal.append("tool_batch_started", {
            "turn_id": turn_id, "tool_calls": [c.model_dump(mode="json") for c in calls],
            "active_elapsed_ms": self.elapsed_ms(),
        })
        self.new_tools += len(calls)
        self.counters.tool_actions += len(calls)
        if report is not None:
            self.report = {"turn_id": turn_id, "action_id": calls[0].action_id,
                           "report": report.model_dump(mode="json"),
                           "evidence": report_evidence(report, self.gateway)}
            self.journal.append("discovery_report_recorded", self.report)
            checkpoint("report_recorded")
            return
        loop._record_planning_decision("brief-v1", journal=self.journal, gateway=self.gateway,
                                       calls=calls, turn_id=turn_id)
        self.gateway.record_working_notes_update(calls, turn_id=turn_id)
        results = self.gateway.execute_batch(calls)
        checkpoint("actions_finished")
        loop._record_tool_batch(journal=self.journal, gateway=self.gateway, turn_id=turn_id,
                                calls=calls, results=results, active_elapsed_ms=self.elapsed_ms())
        checkpoint("batch_finished")
        if any(r.output.get("cleanup_failed") for r in results):
            raise engine.AbortExperiment("SANDBOX_CLEANUP_UNCONFIRMED")
        if any(r.error_code in {"RECOVERY_ERROR", "RESUME_CONTRACT_MISMATCH"} for r in results):
            raise engine.AbortExperiment("TOOL_EXECUTION_UNCERTAIN")
        if any(r.output.get("deadline_exhausted") for r in results):
            raise engine.AbortExperiment("LIMIT_REACHED")
        for call, result in zip(calls, results, strict=True):
            if call.name == "run_probe" and (
                result.status != "succeeded"
                or result.output.get("source_hash") != sha256_bytes(
                    call.arguments["python_source"].encode())
                or any(result.output.get(k) != v for k, v in self.probe_identity.items())
            ):
                raise engine.AbortExperiment("TOOL_EXECUTION_UNCERTAIN")
        self.verify_candidate()
        context = canonical_json({"current_diff": {"patch_hash": self.fixed_diff},
                                  "working_notes": self.gateway.working_notes()})
        exchange = loop._build_latest_exchange(journal=self.journal, artifact_store=self.store,
                                               context=context, latest_tool_results=results)[1:-1]
        self.items.extend(exchange)
        self.journal.append("discovery_history_advanced", {
            "turn_id": turn_id, "input_hash": sha256_json(self.items),
            "exchange_hash": sha256_json(exchange),
        })
        checkpoint("history_recorded")


def uncertainty(journal: DevJournal) -> str | None:
    if journal.unresolved_provider_call() or any(
        not p.get("billing_known") for p in journal.provider_usage()
    ):
        return "PROVIDER_TIMEOUT_OR_UNKNOWN"
    if journal.unresolved_input_count():
        return "COUNT_TIMEOUT_OR_UNKNOWN"
    events = journal.events()
    finished = {e["payload"]["result"]["action_id"] for e in events
                if e["event_type"] == "action_finished"}
    if any(e["payload"]["action_id"] not in finished for e in events
           if e["event_type"] == "action_started"):
        return "TOOL_EXECUTION_UNCERTAIN"
    return None


def summary(journal: DevJournal, code: str, *, provider_free: bool) -> dict:
    events = journal.events()

    def payloads(kind):
        return [e["payload"] for e in events if e["event_type"] == kind]
    usage = journal.provider_usage()
    code = uncertainty(journal) or code
    ledger = DevCostLedger(CAP, pricing_for_model(design.MODEL))
    uncached = sum(ledger.settle(input_tokens=p["input_tokens"], cached_input_tokens=0,
                                 output_tokens=p["output_tokens"])
                   for p in usage if p.get("billing_known"))
    reports = payloads("discovery_report_recorded")
    return {**BOUNDARIES, "schema_version": SCHEMA, "run_id": journal.run_id,
            "terminal": code, "provider_free": provider_free,
            "accounting_basis": "mock_simulation" if provider_free else "recorded_provider_usage",
            "live_provider_calls": 0 if provider_free else len(payloads("provider_call_started")),
            "model_calls": len(payloads("provider_call_started")),
            "input_count_calls": len(payloads("input_count_started")),
            "tool_actions": sum(len(p["tool_calls"]) for p in payloads("tool_batch_started")),
            "recorded_cost_nanos": sum(p.get("cost_nanos") or 0 for p in usage),
            "cache_neutral_cost_nanos": uncached,
            "provider_cost_known": code != "PROVIDER_TIMEOUT_OR_UNKNOWN",
            "count_billing_and_invoice": "UNVERIFIED",
            "maximum_input_tokens": max((p["input_tokens"] for p in
                                          payloads("input_count_finished")), default=0),
            "report": reports[-1] if reports else None,
            "review_status": "PUBLIC_REVIEW_REQUIRED" if reports else "INCOMPLETE_OBSERVATION",
            "discovery_outcome": None,
            "automatic_retry_resume_or_extra_sample": False}


def run(plan_root: Path, *, plan_hash: str, adapter_factory=None, probe_factory=None,
        checkpoint=lambda _: None, clock=monotonic) -> dict:
    plan = validate(plan_root)
    design.require(plan_hash == sha256_bytes((plan_root / "plan.json").read_bytes()),
                   "exact executable plan hash required")
    design.require(plan["pricing_verified_on"] == utc_now().date().isoformat(),
                   "price review date expired")
    design.require((adapter_factory is None) == (probe_factory is None),
                   "mock requires both explicit provider and probe substitutes")
    design_root, root = Path(plan["design_root"]), Path(plan["result_root"])
    packet = design.validate(design_root)
    protected = [plan_root, design_root, *(Path(v).parent for v in packet["inputs"].values())]
    design.fresh_external_root(root, protected)
    root.mkdir(exist_ok=False)  # Consume the sole bound output, even on preflight failure.
    store, journal = ArtifactStore(root / "artifacts"), DevJournal(root, RUN_ID)
    state_store = ArtifactStore(root)
    live = adapter_factory is None
    state_store.write_text_immutable(root / "execution.json", design.wire({
        "plan": plan, "plan_hash": plan_hash, "provider_free": not live,
    }).decode())
    client, session, code = None, None, "PREFLIGHT_FAILED"
    with journal.execution_lock():
        journal.append("diagnostic_execution_started", {"plan_hash": plan_hash,
                                                        "provider_free": not live, **BOUNDARIES})
        try:
            preflight = ExecutionDeadline.from_remaining(180, clock=clock)
            public_path = Path(packet["inputs"]["public_task"])
            public = load_public_task(public_path)
            design.require(public.split == "dev-train", "dev-train public task required")
            if live:
                loop._require_tracked_clean_paths(repository_root(), [
                    *runtime_content_paths(), *plan["implementation_hashes"],
                    public_path.relative_to(repository_root()).as_posix(),
                ], deadline=preflight)
            dependencies_path = Path(packet["inputs"]["prepared_dependencies"])
            _, identity = read_descriptor(dependencies_path)
            dependencies = load_dependencies(dependencies_path, public, identity)
            dependencies.verify(deadline=preflight)
            probe = (DockerProbeSandbox(dependencies=dependencies) if live else
                     probe_factory(dependencies))
            expected_probe = {"image_digest": packet["probe_profile"]["image_digest"],
                              "profile_hash": sha256_json(packet["probe_profile"])}
            design.require(probe.preflight(deadline=preflight) == expected_probe,
                           "probe environment identity changed")
            manager = WorkspaceManager(repository_root() / "fixtures/repos", root / "workspaces",
                                       prepared_source=Path(packet["inputs"]["prepared_source"]),
                                       prepared_source_hash=packet["input_hashes"]["prepared_source"])
            workspace = manager.create("candidate", public.repository.url,
                                       public.repository.base_commit, deadline=preflight)
            manager.apply_patch(workspace, design_root / "candidate.patch", deadline=preflight)
            diff = manager.diff_summary(workspace, deadline=preflight)
            design.require(diff.patch_hash == packet["input_hashes"]["candidate_patch"]
                           and not diff.untracked_files, "candidate reconstruction mismatch")
            design.require(validate(plan_root) == plan, "inputs changed during preflight")
            journal.append("discovery_source_bound", {"candidate_hash": diff.patch_hash,
                                                       "probe": expected_probe})
            gateway = DevToolGateway(workspace=workspace, public_task=public, sandbox=None,
                                     journal=journal, limits=DevLimits(), probe_sandbox=probe,
                                     deadline=ExecutionDeadline.from_remaining(1800, clock=clock))
            session = Session(read(plan_root / "request.json"), gateway, store,
                              probe_identity=expected_probe, clock=clock)
            if live:
                key = load_exact_openai_api_key(Path(plan["credential_file"]))
                client = requests.DiagnosticClient(api_key=key)
                del key
                adapter = OpenAIResponsesAdapter(configuration(), api_key="", client=client)
            else:
                adapter = adapter_factory(configuration())
                client = adapter.client
            design.require(adapter.config == configuration() and client.max_retries == 0,
                           "provider configuration changed")
            ledger = DiscoveryLedger(CAP, pricing_for_model(design.MODEL))
            code = "INTERRUPTED"
            while session.report is None:
                engine.dispatch(session, adapter, ledger, session.prepare_request(),
                                expected_model=design.MODEL, request_waits=requests.WAITS,
                                checkpoint=checkpoint)
            code = "REPORT_RECORDED"
        except engine.AbortExperiment as exc:
            code = exc.code
        except ExecutionDeadlineExceeded:
            code = "LIMIT_REACHED"
        except (Exception, KeyboardInterrupt, SystemExit) as exc:
            code = "PREFLIGHT_FAILED" if session is None else "EXECUTION_STOPPED"
            journal.append("discovery_execution_error", requests.exception_evidence(exc))
        finally:
            if client is not None:
                try:
                    client.close(timeout=requests.WAITS.client_cleanup_seconds)
                except (Exception, KeyboardInterrupt, SystemExit):
                    journal.append("discovery_cleanup_unconfirmed", {"kind": "provider_client"})
                    code = "CLIENT_CLEANUP_UNCONFIRMED"
        result = summary(journal, code, provider_free=not live)
        journal.append("diagnostic_execution_finished", result)
        state_store.write_text_immutable(root / "result.json", design.wire(result).decode())
    return result


def inspect(root: Path) -> dict:
    """Audit closed or interrupted evidence without source, credentials or another action."""
    design.require((root / "runs" / f"{RUN_ID}.jsonl").is_file(), "execution journal missing")
    execution = read(root / "execution.json")
    journal = DevJournal(root, RUN_ID)
    events = journal.events()
    design.require(sha256_bytes(design.wire(execution["plan"])) == execution["plan_hash"],
                   "execution plan identity changed")
    starts = [e["payload"] for e in events if e["event_type"] == "diagnostic_execution_started"]
    design.require(len(starts) == 1 and starts[0]["plan_hash"] == execution["plan_hash"]
                   and starts[0]["provider_free"] == execution["provider_free"],
                   "execution identity does not match journal")
    store = engine.readonly_store(root / "artifacts")

    def verify(value):
        if isinstance(value, dict):
            if {"artifact_id", "content_hash", "path", "size_bytes"} <= value.keys():
                store.read_bytes(Artifact.model_validate(value))
            else:
                for item in value.values():
                    verify(item)
        elif isinstance(value, list):
            for item in value:
                verify(item)

    verify(events)
    final = [e["payload"] for e in events if e["event_type"] == "diagnostic_execution_finished"]
    design.require(len(final) <= 1, "multiple diagnostic terminal records")
    if final:
        result = summary(journal, final[0]["terminal"], provider_free=execution["provider_free"])
        design.require(final[0] == result, "terminal does not match recorded execution")
        if (root / "result.json").exists():
            design.require(read(root / "result.json") == result, "published result changed")
        return result
    return summary(journal, "INTERRUPTED", provider_free=execution["provider_free"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    for name in ("design-root", "output", "result-root"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--pricing-verified-on", required=True)
    for command in ("validate", "inspect"):
        commands.add_parser(command).add_argument("--root", type=Path, required=True)
    r = commands.add_parser("run")
    r.add_argument("--plan-root", type=Path, required=True)
    r.add_argument("--plan-hash", required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    result = {"prepare": prepare, "validate": validate, "run": run, "inspect": inspect}[command](
        **args)
    print(canonical_json({"status": result.get("terminal", result.get("status")),
                          "official": False, "model_calls": result.get("model_calls", 0),
                          "content_hash": sha256_json(result)}))


if __name__ == "__main__":
    main()
