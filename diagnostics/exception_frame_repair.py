"""Small seeded repair comparison, not a fresh solve or ordinary submission run.

Preparation reads public evidence and constructs requests without an SDK client,
credential read, token-count request, target execution or private task loading.
Collection requires a separately approved manifest. The default pair varies only
initial exception information. The source-ready profile assesses one fixed candidate
with public source already supplied; it is not a controlled information comparison.
"""
from __future__ import annotations

import argparse
import copy
import json
from contextlib import suppress
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from diagnostics.cleanup_information_checkpoint import restore_candidate
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, SourceStore, disjoint
from diagnostics.source_ready_packet import observe_sources, validate_packet
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig, PublicTask, TaskEnvironment
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import probe_invocation, runner
from patchloop.dev.contracts import DevLimits, DevTerminal, DevToolResult, RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import load_dependencies
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox.probes import DockerProbeSandbox, probe_profile, probe_profile_hash
from patchloop.util import canonical_json, load_unique_yaml, sha256_bytes, sha256_json

SCHEMA = "exception-frame-repair-v1"
MODEL = "gpt-5.4-mini-2026-03-17"
CAP, ROW_CAP = Decimal("1.20"), Decimal("0.60")
NORMAL_OUTPUT, CORRECTION_OUTPUT, INPUT_LIMIT = 40_000, 25_000, 60_000
NORMAL_CALLS, TOOL_ACTIONS = 4, 12
MODEL_SECONDS, CHECK_SECONDS = 600, 390
TOOLS = frozenset({"read_file", "search_files", "run_probe", "replace_text", "stop_task"})
PROMPT = (
    "Repair the supplied public task from the saved candidate. You have at most four normal "
    "responses, one protocol correction, twelve tool actions, one diagnostic probe and one "
    "accepted source edit. Inspect current source with registered reads before editing. "
    "Use the observations to assess the candidate independently; they are evidence, not "
    "repair instructions. Stop if no justified edit is available. A successful replace_text "
    "ends this diagnostic. The host then checks the unchanged original program and public "
    "regression suite. There is no submission or task-acceptance verdict in this comparison. "
    "The initial observation describes the seed only. Later tool results are ordinary "
    "public observations. Use only the offered tools; no shell or dependency installation."
)


@dataclass(frozen=True)
class RepairProfile:
    name: str
    order: tuple[str, ...]
    normal_calls: int
    row_cap: Decimal


DEFAULT_PROFILE = RepairProfile("initial-information-pair-v1", ("A", "B"), NORMAL_CALLS, ROW_CAP)
SOURCE_READY_PROFILE = RepairProfile("source-ready-single-v1", ("B",), 8, CAP)
PROFILES = {profile.name: profile for profile in (DEFAULT_PROFILE, SOURCE_READY_PROFILE)}


def selected_profile(name):
    require(name in PROFILES, "unknown repair profile")
    return PROFILES[name]


def load_source_packet(loaded, profile, calibration_hash, path, digest):
    if profile == DEFAULT_PROFILE:
        require(path is None and digest is None, "paired profile does not accept a source packet")
        return None
    require(path is not None and digest is not None, "source-ready profile needs a source packet")
    raw = Path(path).read_bytes()
    require(sha256_bytes(raw) == digest, "source packet identity changed")
    packet = json.loads(raw)
    validate_packet(loaded, packet, calibration_hash)
    return packet


def anchor_reads(packet):
    return sum(row["origin"] == "workspace" for row in packet["sources"]) if packet else 0


def config():
    return ModelConfig(provider="openai", model_id=MODEL, reasoning_effort="xhigh",
                       reasoning_continuation="encrypted-v1", transport_max_retries=0,
                       max_output_tokens=NORMAL_OUTPUT, service_tier="default")


def implementation_hash():
    return sha256_bytes(Path(__file__).read_bytes())


def source_helper_hash():
    return sha256_bytes(Path(__file__).with_name("source_ready_packet.py").read_bytes())


def _trace(result):
    return result["output"]["reproduction"]["call_observation"]


def _same_selected(base, current, call_id="call-1"):
    def selected(trace):
        calls = [row for row in trace["calls"] if row["call_id"] == call_id]
        require(len(calls) == 1, "selected original call is missing or duplicated")
        value = probe_invocation.conditions({**trace, "calls": calls})
        return {key: value[key] for key in ("calls", "execution_environment")}
    return selected(base) == selected(current)


def _public_result(result):
    output = result["output"]
    observation = output["reproduction"]
    return {
        "diff_hash": result["workspace_diff_hash"],
        "helper": {key: output.get(key) for key in (
            "status", "exit_code", "stdout", "stderr", "timed_out", "truncated",
            "cleanup_failed", "deadline_exhausted", "setup_checks")},
        "observation": {key: observation.get(key) for key in (
            "observed_json", "comparison", "reason", "declared_failure_comparison")},
        "call_observation": copy.deepcopy(observation["call_observation"]),
        "exception_diagnostics": copy.deepcopy(output.get("exception_diagnostics")),
    }


def strip_frames(value):
    """The sole initial-input intervention; do not alter later tool output."""
    value = copy.deepcopy(value)
    for row in value["initial_observations"].values():
        row.pop("exception_diagnostics", None)
    return value


def load_calibration(path: Path, digest: str):
    raw = path.read_bytes()
    require(sha256_bytes(raw) == digest, "calibration identity changed")
    data = json.loads(raw)
    require(data["schema"] == "exception-frame-calibration-v1", "unknown calibration")
    require(data["current_runtime_hash"] == runtime_content_hash(), "calibration runtime changed")
    source = Source.from_record(data["source"])
    historical = DevJournal(source.root, source.run_id)
    for name, expected in ((historical.path, source.journal_hash),
                           (historical.envelope_path, source.envelope_hash),
                           (source.public_path, source.public_hash)):
        require(sha256_bytes(name.read_bytes()) == expected, "historical source changed")
    public = PublicTask.model_validate(load_unique_yaml(source.public_path.read_text("utf-8")))
    require(public.split == "dev-train", "only dev-train public tasks are admitted")
    events, old = historical.events(), historical.load_envelope()
    require(any(e["sequence"] == data["cut_sequence"]
                and e["event_type"] == "model_input_prepared" for e in events),
            "calibration cutoff is not a prepared input")
    prefix = [e for e in events if e["sequence"] < data["cut_sequence"]]
    accepted = {e["payload"]["result"]["action_id"] for e in prefix
                if e["event_type"] == "action_finished"
                and e["payload"]["result"]["tool"] == "replace_text"
                and e["payload"]["result"]["status"] == "succeeded"
                and e["payload"]["result"].get("error_code") is None}
    require(len(accepted) == 1, "the first accepted candidate is required")
    mutation = next(e["payload"] for e in prefix if e["event_type"] == "action_started"
                    and e["payload"]["action_id"] in accepted)
    require(mutation["mutation_expected_worktree_diff_hash"] == data["candidate_diff_hash"],
            "candidate identity changed")
    original = next(e["payload"] for e in prefix if e["event_type"] == "action_started"
                    and e["payload"]["action_id"] == data["original_action_id"])
    arguments = data["original_arguments"]
    require(arguments == original["arguments"] and original["tool"] == "run_probe",
            "authored original request changed")
    require(sha256_bytes(arguments["python_source"].encode()) == data["authored_program_hash"],
            "authored program changed")
    require(old.prepared_source_path and old.prepared_probe_dependencies_path,
            "local source and prepared dependencies are required")
    dependencies = load_dependencies(Path(old.prepared_probe_dependencies_path), public,
                                     old.probe_dependencies)
    identity = {"image_digest": probe_profile(old.probe_dependencies)["image_digest"],
                "profile_hash": probe_profile_hash(old.probe_dependencies)}
    require(all(data["current_probe_identity"].get(k) == v for k, v in identity.items()),
            "calibration probe profile changed")
    rows = {}
    for name, diff in (("base", sha256_bytes(b"")), ("candidate", data["candidate_diff_hash"])):
        row = data["rows"][name]
        result = json.loads(SourceStore(path.parent).read_bytes(
            Artifact.model_validate(row["receipt"])))
        DevToolResult.model_validate(result)
        output, trace = result["output"], _trace(result)
        require(set(trace) == {"calls", "incomplete", "binding_method", "execution_environment"}
                and trace["execution_environment"] == probe_invocation.environment(output)
                and all(probe_invocation.valid_call(call,
                    output["reproduction"]["binding"]["definition"]["entrypoint"],
                    channel=probe_invocation.CHANNEL) for call in trace["calls"]),
                "calibration has an invalid public call observation")
        require(result["tool"] == "run_probe" and result["status"] == "succeeded"
                and result["workspace_diff_hash"] == row["diff_hash"] == diff
                and all(output.get(k) == v for k, v in identity.items())
                and output["reproduction"]["binding"]["program_hash"]
                == data["authored_program_hash"]
                and trace["binding_method"] == probe_invocation.CHANNEL,
                "calibration receipt is not the current original program and candidate")
        rows[name] = result
    require(_same_selected(_trace(rows["base"]), _trace(rows["candidate"])),
            "selected call conditions differ in calibration")
    require(rows["base"]["output"]["reproduction"]["declared_failure_comparison"] == "matched",
            "baseline does not reproduce the declared failure")
    require(rows["candidate"]["output"].get("exception_diagnostics", {}).get("calls"),
            "candidate exception frames were not collected")
    common = {"public_task": public.model_dump(mode="json"),
              "candidate_diff_hash": data["candidate_diff_hash"],
              "candidate_patch": mutation["mutation_generated_patch"],
              "original_program": arguments["python_source"],
              "original_purpose": arguments["purpose"],
              "probe_environment": dependencies.environment,
              "initial_observations": {k: _public_result(v) for k, v in rows.items()}}
    environment_path = source.public_path.parent / "environment.yaml"
    environment = TaskEnvironment.model_validate(
        load_unique_yaml(environment_path.read_text("utf-8")))
    return SimpleNamespace(data=data, source=source, old=old, public=public, mutation=mutation,
                           dependencies=dependencies, rows=rows, common=common,
                           environment=environment,
                           environment_hash=sha256_bytes(environment_path.read_bytes()))


def request_payload(common, arm, *, history=(), remaining=None, correction=None, probe_used=False,
                    profile=DEFAULT_PROFILE, source_packet=None):
    require(arm in profile.order, "unknown arm for repair profile")
    initial = strip_frames(common) if arm == "A" else copy.deepcopy(common)
    prompt, focus = PROMPT, []
    if profile == SOURCE_READY_PROFILE:
        require(source_packet is not None, "source-ready profile needs a source packet")
        prompt = PROMPT.replace("four normal", "eight normal").replace(
            "Inspect current source with registered reads before editing.",
            "The current failure and public source excerpts are presented first. "
            "Workspace excerpts are registered current edit anchors; "
            "you may edit them or inspect further source with the offered tools. "
            "Source entries are bounded excerpts and may be partial; "
            "dependency entries are read-only.")
        focus = [{"role": "user", "content": canonical_json({
            "current_failure": initial["initial_observations"].pop("candidate"),
            "source_packet": source_packet})}]
    items = [{"role": "system", "content": prompt}, *focus,
             {"role": "user", "content": canonical_json(initial)}, *copy.deepcopy(history)]
    if remaining is not None or correction is not None:
        items.append({"role": "developer", "content": canonical_json({
            "remaining": remaining, "protocol_correction": correction})})
    allowed = TOOLS - {"run_probe"} if probe_used else TOOLS
    schemas = dev_tool_schemas(finish_enabled=False, allowed_tools=allowed,
                               probe_environment=common.get("probe_environment"))
    # A non-SDK inert client makes request construction incapable of network access.
    adapter = OpenAIResponsesAdapter(config(), api_key="", client=SimpleNamespace(max_retries=0))
    payload = adapter.request_payload(items, schemas, system_prompt=prompt)
    payload["max_output_tokens"] = CORRECTION_OUTPUT if correction else NORMAL_OUTPUT
    return payload


def verify_pair(a, b):
    expected = copy.deepcopy(b)
    expected["input"][1]["content"] = canonical_json(strip_frames(
        json.loads(expected["input"][1]["content"])))
    require(a == expected, "inputs differ beyond the initial exception details")


def prepare(calibration: Path, calibration_hash: str, output: Path, result_root: Path,
            credential_file: Path, *, profile=DEFAULT_PROFILE, source_packet: Path | None = None,
            source_packet_hash: str | None = None):
    loaded = load_calibration(calibration, calibration_hash)
    packet = load_source_packet(loaded, profile, calibration_hash,
                                source_packet, source_packet_hash)
    protected = (repository_root(), loaded.source.root, calibration.parent,
                 loaded.source.public_path.parent, result_root)
    disjoint(output, protected)
    disjoint(result_root, protected[:-1])
    requests = {arm: request_payload(loaded.common, arm, profile=profile, source_packet=packet)
                for arm in profile.order}
    if profile == DEFAULT_PROFILE:
        verify_pair(requests["A"], requests["B"])
    plan = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
            "calibration": str(calibration.resolve()), "calibration_hash": calibration_hash,
            "runtime_hash": runtime_content_hash(), "implementation_hash": implementation_hash(),
            "profile": profile.name,
            "source_packet": str(source_packet.resolve()) if source_packet is not None else None,
            "source_packet_hash": source_packet_hash,
            "source_helper_hash": source_helper_hash() if packet is not None else None,
            "host_source_reads": anchor_reads(packet),
            "task": str(loaded.source.public_path.resolve()), "model": MODEL,
            "public_environment_hash": loaded.environment_hash,
            "reasoning_effort": "xhigh", "order": list(profile.order), "repeat_per_arm": 1,
            "ordinary_output": NORMAL_OUTPUT, "correction_output": CORRECTION_OUTPUT,
            "input_limit": INPUT_LIMIT, "normal_calls": profile.normal_calls, "correction_calls": 1,
            "tool_actions": TOOL_ACTIONS, "diagnostic_probes": 1, "accepted_mutations": 1,
            "model_seconds_per_arm": MODEL_SECONDS, "host_check_seconds_per_arm": CHECK_SECONDS,
            "row_cap_usd": str(profile.row_cap), "new_cap_usd": str(CAP),
            "credential_file": str(credential_file.resolve()),
            "result_root": str(result_root.resolve()),
            "pricing": {k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()},
            "first_request_hashes": {k: sha256_json(v) for k, v in requests.items()},
            "interpretation": (
                "Source-ready conditional repair opportunity at one fixed candidate; "
                "not a controlled information comparison, fresh solve, ordinary runner completion, "
                "acceptance or generalization." if profile == SOURCE_READY_PROFILE else
                "Initial-information effect at one fixed candidate; not fresh solve, "
                "ordinary runner completion, acceptance or generalization.")}
    output.mkdir()
    for arm, value in requests.items():
        (output / f"{arm}-first.json").write_text(canonical_json(value) + "\n", encoding="utf-8")
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    receipt = {"manifest": str(output / "manifest.json"), "manifest_hash": sha256_bytes(raw),
               "provider_calls": 0, "input_count_calls": 0, "credential_reads": 0,
               "target_executions": 0, "paid_execution_authorized": False}
    DevJournal(output, "run_dev_exceptionframepreparation").append("prepared", receipt)
    return receipt


def validate(manifest: Path, digest: str):
    raw = manifest.read_bytes()
    require(sha256_bytes(raw) == digest, "approved manifest hash differs")
    plan = json.loads(raw)
    require(plan["schema"] == SCHEMA and plan["implementation_hash"] == implementation_hash()
            and plan["runtime_hash"] == runtime_content_hash(), "prepared implementation changed")
    profile = selected_profile(plan["profile"])
    require(plan["source_helper_hash"] == (
        source_helper_hash() if profile == SOURCE_READY_PROFILE else None),
        "prepared source helper changed")
    loaded = load_calibration(Path(plan["calibration"]), plan["calibration_hash"])
    packet = load_source_packet(loaded, profile, plan["calibration_hash"], plan["source_packet"],
                                plan["source_packet_hash"])
    require(plan["host_source_reads"] == anchor_reads(packet), "source read allowance changed")
    require(plan["public_environment_hash"] == loaded.environment_hash,
            "public check environment changed")
    require(plan["model"] == MODEL and plan["reasoning_effort"] == "xhigh"
            and plan["order"] == list(profile.order) and plan["repeat_per_arm"] == 1
            and Decimal(plan["row_cap_usd"]) == profile.row_cap
            and Decimal(plan["new_cap_usd"]) == CAP
            and (plan["ordinary_output"], plan["correction_output"])
            == (NORMAL_OUTPUT, CORRECTION_OUTPUT)
            and (plan["normal_calls"], plan["correction_calls"], plan["tool_actions"],
                 plan["diagnostic_probes"], plan["accepted_mutations"], plan["input_limit"])
            == (profile.normal_calls, 1, TOOL_ACTIONS, 1, 1, INPUT_LIMIT)
            and (plan["model_seconds_per_arm"], plan["host_check_seconds_per_arm"])
            == (MODEL_SECONDS, CHECK_SECONDS), "comparison scope changed")
    requests = {arm: request_payload(loaded.common, arm, profile=profile, source_packet=packet)
                for arm in profile.order}
    require(set(plan["first_request_hashes"]) == set(profile.order), "prepared arms changed")
    for arm, value in requests.items():
        require(sha256_json(value) == plan["first_request_hashes"][arm]
                and json.loads((manifest.parent / f"{arm}-first.json").read_bytes()) == value,
                "prepared input changed")
    if profile == DEFAULT_PROFILE:
        verify_pair(requests["A"], requests["B"])
    require(plan["pricing"] == {k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()},
            "registered pricing changed")
    loaded.source_packet = packet
    return plan, loaded


def _exchange(turn, results, issue=None):
    calls = {call.action_id: call for call in turn.tool_calls}
    items = []
    continuation = turn.provider_continuation
    for item in continuation.output_order if continuation else []:
        if item.type == "reasoning":
            items.append({"type": "reasoning", "id": item.id,
                          "encrypted_content": item.encrypted_content, "summary": [],
                          **({"status": item.status} if item.status else {})})
        else:
            call = calls[item.action_id]
            items.append({"type": "function_call", "call_id": call.action_id,
                          "name": call.name,
                          "arguments": canonical_json(runner._provider_tool_arguments(call))})
    if not continuation:
        items.extend({"type": "function_call", "call_id": call.action_id,
                      "name": call.name,
                      "arguments": canonical_json(runner._provider_tool_arguments(call))}
                     for call in turn.tool_calls)
    by_id = {row.action_id: row.model_dump(mode="json") for row in results}
    items.extend({"type": "function_call_output", "call_id": call.action_id,
                  "output": canonical_json(by_id.get(call.action_id, {
                      "status": "rejected", "message": issue}))} for call in turn.tool_calls)
    return items


def run_model(loaded, arm, gateway, adapter, group, *, first_hash, profile=DEFAULT_PROFILE,
              source_packet=None):
    """At most one new edit. Adapter injection supports finite offline tests."""
    journal = gateway.journal
    store = ArtifactStore(journal.root / "artifacts")
    ledger = DevCostLedger(profile.row_cap, pricing_for_model(MODEL))
    history, normal, corrections, actions, probes = [], 0, 0, 0, 0
    correction, terminal, uncertain = None, "MODEL_LIMIT", False
    execution_abort, abort_reason = None, None
    first = True
    while normal < profile.normal_calls or correction is not None:
        if actions >= TOOL_ACTIONS:
            terminal = "TOOL_LIMIT"
            break
        timeout = gateway.deadline.remaining_seconds()
        if timeout <= 0:
            terminal = "MODEL_TIME_LIMIT"
            break
        payload = request_payload(loaded.common, arm, history=history,
                                  remaining=None if first else {
                                      "normal_calls": profile.normal_calls - normal,
                                      "tool_actions": TOOL_ACTIONS - actions,
                                      "diagnostic_probes": 1 - probes, "accepted_mutations": 1,
                                      "cost_nanos": ledger.remaining_nanos},
                                  correction=correction, probe_used=bool(probes),
                                  profile=profile, source_packet=source_packet)
        if first:
            require(sha256_json(payload) == first_hash, "first input differs from preparation")
        first = False
        request_hash = sha256_json(payload)
        count_id = f"count-{normal}-{corrections}-{int(bool(correction))}"
        journal.append("input_count_started", {"count_id": count_id,
                       "request_hash": request_hash,
                       "request": store.put_json(payload).model_dump(mode="json")})
        try:
            counted = adapter.count_input_tokens_v2(payload, timeout_seconds=timeout)
        except Exception:
            terminal, uncertain = "COUNT_UNCERTAIN", True
            break
        journal.append("input_count_finished", {"count_id": count_id,
                       "request_hash": request_hash, "input_tokens": counted})
        if type(counted) is not int or counted <= 0:
            terminal, uncertain = "COUNT_UNCERTAIN", True
            break
        if counted > INPUT_LIMIT:
            terminal = "INPUT_LIMIT"
            break
        is_correction = correction is not None
        reserve = (ledger.future_call_reservation_nanos(output_ceiling=CORRECTION_OUTPUT)
                   if not is_correction and not corrections else 0)
        if not is_correction and normal + 1 < profile.normal_calls:
            reserve += ledger.future_call_reservation_nanos(output_ceiling=NORMAL_OUTPUT)
        admissions = [book.admit(counted, desired_output_ceiling=payload["max_output_tokens"],
                                 future_cost_reserve_nanos=reserve) for book in (ledger, group)]
        if any(row is None for row in admissions):
            terminal = "COST_CAP_REACHED"
            break
        timeout = gateway.deadline.remaining_seconds()
        if timeout <= 0:
            terminal = "MODEL_TIME_LIMIT"
            break
        payload["max_output_tokens"] = min(row.output_ceiling for row in admissions)
        call_id = "call-" + count_id
        journal.append("provider_call_started", {"call_id": call_id,
                        "request_hash": sha256_json(payload),
                        "request": store.put_json(payload).model_dump(mode="json"),
                        "counted_request_hash": request_hash, "input_tokens": counted,
                        "output_ceiling": payload["max_output_tokens"]})
        corrections += int(is_correction)
        normal += int(not is_correction)
        try:
            raw = adapter.execute_request(payload, requested_input_tokens=counted,
                                          timeout_seconds=timeout)
        except Exception:
            terminal, uncertain = "PROVIDER_UNCERTAIN", True
            break
        turn = runner._turn_from_openai(raw)
        if (turn.usage_evidence is None or turn.usage_evidence.get("failure_kind") is not None
                or turn.response_model != MODEL
                or turn.output_tokens > payload["max_output_tokens"]):
            journal.append("provider_usage_unknown", {"call_id": call_id,
                           "error_code": turn.error_code, "usage_evidence": turn.usage_evidence})
            terminal, uncertain = "BILLING_UNCERTAIN", True
            break
        usage = {k: getattr(turn, k)
                 for k in ("input_tokens", "cached_input_tokens", "output_tokens")}
        cost = ledger.settle(**usage)
        group.settle(**usage)
        journal.append("provider_call_finished", {"call_id": call_id, **usage, "cost_nanos": cost,
                       "response_id": turn.response_id, "error_code": turn.error_code,
                       "tool_calls": [call.model_dump(mode="json") for call in turn.tool_calls]})
        if ledger.spent_nanos > ledger.cap_nanos or group.spent_nanos > group.cap_nanos:
            terminal, uncertain = "BILLING_UNCERTAIN", True
            break
        correction = None
        issue = turn.error_code
        try:
            require(issue is None, str(issue))
            allowed = TOOLS - {"run_probe"} if probes else TOOLS
            validate_tool_batch(turn.tool_calls, allowed_tools=allowed)
            require(actions + len(turn.tool_calls) <= TOOL_ACTIONS, "tool allowance exhausted")
            if turn.provider_continuation:
                runner._validate_continuation_action_order(
                    turn.provider_continuation, turn.tool_calls)
        except ContractError as exc:
            issue = str(exc)
        if issue:
            history.extend(_exchange(turn, [], issue))
            if corrections:
                terminal = "CORRECTION_EXHAUSTED"
                break
            correction = issue
            journal.append("protocol_correction", {"turn_id": call_id, "issue": issue})
            continue
        actions += len(turn.tool_calls)
        probes += sum(call.name == "run_probe" for call in turn.tool_calls)
        try:
            results = gateway.execute_batch(turn.tool_calls)
        except ExecutionDeadlineExceeded:
            # Without a returned receipt this may follow a started external probe.
            execution_abort = DevTerminal.TASK_FAILED
            terminal = execution_abort.value
            abort_reason = "tool deadline without a settled receipt"
            break
        history.extend(_exchange(turn, results))
        execution_abort, abort_reason = runner._batch_execution_abort(results)
        if execution_abort is not None:
            terminal = execution_abort.value
            break
        if any(row.tool == "replace_text" and row.status == "succeeded" and not row.error_code
               for row in results):
            terminal = "CANDIDATE_PRODUCED"
            break
        if any(row.tool == "stop_task" for row in results):
            terminal = "AGENT_STOPPED"
            break
    result = {"terminal": terminal, "billing_known": not uncertain,
              "stop_remaining": uncertain or execution_abort == DevTerminal.TASK_FAILED,
              "execution_abort_reason": abort_reason,
              "normal_calls": normal, "correction_calls": corrections, "tool_actions": actions,
              "diagnostic_probes": probes, "new_cost_nanos": ledger.spent_nanos,
              "candidate_diff_hash": gateway.current_diff_hash,
              "new_mutations": gateway.accepted_mutations, "task_acceptance": "NOT_RUN"}
    journal.append("model_phase_finished", result)
    return result


def case_support(base, current):
    """F0010 disappearing alone cannot make an exception or changed control pass."""
    output, observation = current["output"], current["output"].get("reproduction", {})
    trace = observation.get("call_observation", {})
    complete = (current["status"] == "succeeded" and output.get("status") == "passed"
                and output.get("exit_code") == 0 and trace.get("incomplete") is False
                and not any(output.get(k) for k in (
                    "timed_out", "truncated", "cleanup_failed", "deadline_exhausted"))
                and output.get("execution_policy", {}).get("cleanup_status") == "confirmed")
    complete = complete and output.get("setup_checks", {}).get("status") != "failed"
    binding = base["output"]["reproduction"].get("binding", {})
    current_binding = observation.get("binding", {})
    program_same = bool(binding) and all(binding.get(k) == current_binding.get(k)
        for k in ("program_hash", "case_id", "definition"))
    same = False
    with suppress(KeyError, ContractError):
        same = all(_same_selected(_trace(base), trace, call_id) for call_id in ("call-1", "call-2"))
    calls = {call["call_id"]: call for call in trace.get("calls", [])}
    no_exception = all(call.get("outcome") in {"returned", "system_exit"}
                       and (not call.get("exception") or call["exception"].get("type")
                            in {"SystemExit", "builtins.SystemExit"})
                       and call.get("capture", {}).get("status") == "complete"
                       for call in calls.values())
    old_control = next((c for c in _trace(base)["calls"] if c["call_id"] == "call-2"), {})
    control = calls.get("call-2", {})
    control_same = bool(control) and all(control.get(k) == old_control.get(k)
                                        for k in ("outcome", "exception", "exit_code", "capture"))
    supported = (complete and program_same and same and no_exception and len(calls) == 2
                 and control_same and observation.get("comparison") == "matched")
    return {"supported": supported, "complete": complete, "same_call_conditions": same,
            "same_original_program_and_expectation": program_same,
            "no_unexpected_target_exception": no_exception and len(calls) == 2,
            "control_unchanged": control_same, "task_acceptance": "NOT_ASSESSED"}


def _gateway(loaded, root, *, profile=DEFAULT_PROFILE, source_packet=None):
    deadline = ExecutionDeadline.from_remaining(MODEL_SECONDS)
    workspace = WorkspaceManager(repository_root() / "fixtures/repositories", root / "workspaces",
        prepared_source=Path(loaded.old.prepared_source_path),
        prepared_source_hash=loaded.old.prepared_source_hash).create(
            "seed", loaded.public.repository.url, loaded.public.repository.base_commit,
            deadline=deadline)
    restore_candidate(workspace, loaded.mutation)
    journal = DevJournal(root, "run_dev_exceptionframerepair")
    journal.append("seed_restored", {"candidate_diff_hash": loaded.data["candidate_diff_hash"],
                   "source": loaded.source.record(), "historical_actions_imported": False})
    probe = DockerProbeSandbox(dependencies=loaded.dependencies)
    identity = probe.preflight(deadline=deadline)
    require(all(loaded.data["current_probe_identity"].get(k) == v for k, v in identity.items()),
            "executing probe differs from calibration")
    sandbox = DockerSandbox(loaded.environment.evaluator_image)
    require(sandbox.image_identity(deadline=deadline) == loaded.environment.image_digest,
            "public regression image is unavailable or changed")
    return DevToolGateway(workspace=workspace, public_task=loaded.public, sandbox=sandbox,
        probe_sandbox=probe, journal=journal, limits=DevLimits(max_accepted_mutations=1,
        max_model_calls=profile.normal_calls + 1,
        max_tool_actions=TOOL_ACTIONS + anchor_reads(source_packet)), deadline=deadline)


def verify_candidate(loaded, gateway):
    """Sequential host checks share the runtime's cleanup/recovery abort rule."""
    before = gateway.current_diff_hash
    summary = {"case_support": None, "public_regression": [], "stop_remaining": False,
               "host_terminal": "CHECKS_COMPLETED"}
    calls = [RequestedTool(name="run_probe", action_id="host-original",
                          arguments=loaded.data["original_arguments"])]
    calls.extend(RequestedTool(name="run_check", action_id="host-" + check.id,
                               arguments={"check_id": check.id})
                 for check in loaded.public.visible_checks)
    for call in calls:
        try:
            result = gateway.execute(call)
        except ExecutionDeadlineExceeded:
            summary.update(host_terminal=DevTerminal.TASK_FAILED.value, stop_remaining=True,
                           execution_abort_reason="host deadline without a settled receipt")
            break
        require(gateway.current_diff_hash == before, "host verification changed the candidate")
        abort, reason = runner._batch_execution_abort([result])
        if call.name == "run_probe":
            summary["case_support"] = case_support(
                loaded.rows["base"], result.model_dump(mode="json"))
        else:
            summary["public_regression"].append(result.model_dump(mode="json"))
        if abort is not None:
            summary.update(host_terminal=abort.value, execution_abort_reason=reason,
                           stop_remaining=abort == DevTerminal.TASK_FAILED)
            break
    return summary


def collect(manifest: Path, approved_manifest_hash: str, approved_cap_usd: Decimal):
    require(approved_cap_usd == CAP, "exact new invocation cap approval required")
    plan, loaded = validate(manifest, approved_manifest_hash)
    profile = selected_profile(plan["profile"])
    packet = loaded.source_packet
    require(loaded.source.public_path.resolve().is_relative_to(
        repository_root() / "tasks/dev-train"), "live task is outside admitted dev-train tree")
    root = Path(plan["result_root"])
    disjoint(root, (repository_root(), loaded.source.root, manifest.parent,
                    Path(plan["calibration"]).parent, loaded.source.public_path.parent))
    root.mkdir()
    group = DevCostLedger(CAP, pricing_for_model(MODEL))
    journal = DevJournal(root, "run_dev_exceptionframecomparison")
    journal.append("approved_collection_started", {"manifest_hash": approved_manifest_hash,
                                                   "new_cap_usd": str(CAP)})
    rows = []
    try:
        for arm in plan["order"]:
            gateway = _gateway(loaded, root / arm, profile=profile, source_packet=packet)
            if packet is not None:
                validate_packet(loaded, packet, plan["calibration_hash"],
                                workspace=gateway.workspace)
                observe_sources(gateway, packet)
            key = load_exact_openai_api_key(Path(plan["credential_file"]))
            adapter = OpenAIResponsesAdapter(config(), api_key=key)
            del key
            try:
                row = run_model(loaded, arm, gateway, adapter, group,
                                first_hash=plan["first_request_hashes"][arm],
                                profile=profile, source_packet=packet)
            finally:
                adapter.client.close()
            rows.append({"arm": arm, **row})
            if row["stop_remaining"]:
                break
            if row["terminal"] == "CANDIDATE_PRODUCED":
                # Public validation has a fresh journal, so model diagnostic state
                # cannot block or masquerade as this independent host execution.
                gateway = DevToolGateway(workspace=gateway.workspace, public_task=loaded.public,
                    sandbox=gateway.sandbox, probe_sandbox=gateway.probe_sandbox,
                    journal=DevJournal(root / arm / "host", "run_dev_exceptionframehost"),
                    limits=DevLimits(), deadline=ExecutionDeadline.from_remaining(CHECK_SECONDS))
                rows[-1].update(verify_candidate(loaded, gateway))
            journal.append("row_finished", rows[-1])
            if rows[-1]["stop_remaining"]:
                break
    except BaseException as exc:
        journal.append("collection_interrupted", {"error_type": type(exc).__name__,
                                                   "resume_allowed": False})
        raise
    result = {"official": False, "rows": rows, "new_cost_nanos": group.spent_nanos,
              "task_acceptance": "NOT_RUN", "resume_allowed": False,
              "interpretation": plan["interpretation"]}
    (root / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    journal.append("closed", {"completed_rows": len(rows), "unused_allowance_closed": True})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    for name in ("calibration", "output", "result-root", "credential-file"):
        prep.add_argument("--" + name, required=True, type=Path)
    prep.add_argument("--calibration-hash", required=True)
    prep.add_argument("--profile", choices=PROFILES, default=DEFAULT_PROFILE.name)
    prep.add_argument("--source-packet", type=Path)
    prep.add_argument("--source-packet-hash")
    run = commands.add_parser("collect")
    run.add_argument("--manifest", required=True, type=Path)
    run.add_argument("--approved-manifest-hash", required=True)
    run.add_argument("--approved-cap-usd", required=True, type=Decimal)
    args = parser.parse_args()
    value = (prepare(args.calibration, args.calibration_hash, args.output,
                     args.result_root, args.credential_file, profile=selected_profile(args.profile),
                     source_packet=args.source_packet, source_packet_hash=args.source_packet_hash)
             if args.command == "prepare"
             else collect(args.manifest, args.approved_manifest_hash, args.approved_cap_usd))
    print(canonical_json(value))


if __name__ == "__main__":
    main()
