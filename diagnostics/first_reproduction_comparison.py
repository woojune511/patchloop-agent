"""Prepare a public first-reproduction description pair; collect only exact new approval.

This diagnostic ends after the first settled run_probe batch. It preserves the
ordinary gateway, cost admission and protocol correction, and never repairs or
evaluates. Preparation uses a scripted stop and forbids network/credentials/Docker.
"""

from __future__ import annotations

import argparse
import copy
import json
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_comparison import ContinuationLedger
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.decision_sampler import read_source_artifact, require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, segments
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash, runtime_content_paths
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "first-reproduction-description-comparison-v1"
MODEL = "gpt-5.4-mini-2026-03-17"
ORDER = ("A", "B")
HOST_FILES = (
    "patchloop/dev/reproduction.py",
    "patchloop/dev/probe_invocation.py",
    "patchloop/dev/probe_judgment.py",
    "patchloop/dev/original_obligation.py",
)


def public_input(items):
    """Keep public messages and exact call/results; never project opaque reasoning."""
    result = [copy.deepcopy(item) for item in items if item.get("type") != "reasoning"]
    require(not any("encrypted_content" in item for item in result), "opaque input remains")
    return result


def probe_tool(request):
    matches = [tool for tool in request["tools"] if tool["name"] == "run_probe"]
    require(len(matches) == 1, "one original probe schema required")
    return matches[0]


def project(request, description):
    result = copy.deepcopy(request)
    probe_tool(result)["description"] = description
    return result


def verify_pair(a, b):
    require(
        a != b and project(a, probe_tool(b)["description"]) == b,
        "pair must differ only in run_probe.description",
    )
    require(a["input"] == public_input(a["input"]), "pair contains opaque reasoning")
    return {
        "changed_fields": ["tools.run_probe.description"],
        "public_input_hash": sha256_json(a["input"]),
        "parameter_schema_hash": sha256_json(probe_tool(a)["parameters"]),
        "description_chars": {
            "A": len(probe_tool(a)["description"]),
            "B": len(probe_tool(b)["description"]),
        },
        "request_hashes": {"A": sha256_json(a), "B": sha256_json(b)},
        "opaque_reasoning_items": 0,
    }


def source_record(root, run_id, public_task):
    journal = DevJournal(root, run_id)
    return Source(
        root.resolve(),
        run_id,
        sha256_bytes(journal.path.read_bytes()),
        sha256_bytes(journal.envelope_path.read_bytes()),
        public_task.resolve(),
        sha256_bytes(public_task.read_bytes()),
    )


def load_checkpoint(source, cut_sequence):
    journal = DevJournal(source.root, source.run_id)
    for path, digest in (
        (journal.path, source.journal_hash),
        (journal.envelope_path, source.envelope_hash),
        (source.public_path, source.public_hash),
    ):
        require(sha256_bytes(path.read_bytes()) == digest, "source identity changed")
    events, old = journal.events(), journal.load_envelope()
    cut = next((event for event in events if event["sequence"] == cut_sequence), None)
    require(
        cut is not None and cut["event_type"] == "model_input_prepared",
        "checkpoint must be a prepared input",
    )
    prefix = events[: cut_sequence - 1]
    view = SimpleNamespace(events=lambda: prefix)
    require(
        DevJournal.unresolved_provider_call(view) is None
        and DevJournal.unresolved_input_count(view) is None,
        "uncertain prefix",
    )
    actions = [e["payload"] for e in prefix if e["event_type"] == "action_started"]
    require(
        actions and all(a["tool"] in {"read_file", "search_files"} for a in actions),
        "checkpoint must precede any target, mutation or check execution",
    )
    bundle = json.loads(read_source_artifact(source.root, cut["payload"]["artifact"]))
    require(
        sha256_json(bundle["request"]) == cut["payload"]["request_hash"],
        "saved request hash changed",
    )
    state = json.loads(read_source_artifact(source.root, bundle["turn"]["context_artifact"]))
    require(
        state["workflow_gate"] == "needs_original_reproduction"
        and bundle["turn"]["original_acquisition_pending"] is True,
        "first original acquisition checkpoint required",
    )
    require(
        not state["current_diff"]["patch"] and not state["current_diff"]["untracked_files"],
        "unchanged public base required",
    )
    require(
        old.model == MODEL
        and old.reasoning_effort == "xhigh"
        and old.max_output_tokens == 40000
        and old.max_correction_output_tokens == 25000
        and old.split == "dev-train"
        and old.context_policy == "segmented-v1",
        "checkpoint model/limits differ",
    )
    original = bundle["request"]
    require(
        {t["name"] for t in original["tools"]} == {"run_probe", "stop_task"},
        "original-only tool availability required",
    )
    public = copy.deepcopy(original)
    public["input"] = public_input(public["input"])
    return SimpleNamespace(
        source=source,
        envelope=old,
        state=state,
        bundle=bundle,
        public=public,
        cut_sequence=cut_sequence,
        prefix_hash=prefix[-1]["event_hash"],
    )


def current_description(loaded):
    old = loaded.envelope
    _, package = runner._resolve_task_file(loaded.source.public_path)
    deps = (
        runner.load_dependencies(
            Path(old.prepared_probe_dependencies_path), package.public, old.probe_dependencies
        )
        if old.prepared_probe_dependencies_path
        else None
    )
    tools = runner.dev_tool_schemas(
        finish_enabled=False,
        allowed_tools=("run_probe", "stop_task"),
        original_acquisition_pending=True,
        planning_policy=old.planning_policy,
        agent_policy=old.agent_policy,
        probe_policy=old.probe_policy,
        probe_recheck_policy=old.probe_recheck,
        probe_environment=deps.environment if deps else None,
    )
    current = {**loaded.public, "tools": tools}
    require(
        project(current, probe_tool(loaded.public)["description"]) == loaded.public,
        "current tools changed beyond the original description",
    )
    return probe_tool(current)["description"]


def controls(source, cut_sequence, env_file, result_root):
    loaded = load_checkpoint(source, cut_sequence)
    budget, old = loaded.state["remaining_budget"], loaded.envelope
    cap = budget["cost"]["remaining"]
    require(
        cap > 0 and sha256_bytes(str(env_file.resolve()).encode()) == old.credential_file_path_hash,
        "positive allowance and exact credential path required",
    )
    requests = {"A": loaded.public, "B": project(loaded.public, current_description(loaded))}
    pair = verify_pair(**{k.lower(): v for k, v in requests.items()})
    plan = {
        "schema": SCHEMA,
        "official": False,
        "paid_execution_authorized": False,
        "source": source.record(),
        "cut_sequence": cut_sequence,
        "prefix_hash": loaded.prefix_hash,
        "model": old.model,
        "reasoning_effort": old.reasoning_effort,
        "order": list(ORDER),
        "repeats_per_arm": 1,
        "credential_file": str(env_file.resolve()),
        "result_root": str(result_root.resolve()),
        "row_new_cap_nanos": cap,
        "new_cap_nanos": cap * 2,
        "historical_spent_nanos": budget["cost"]["settled_usage"],
        "remaining_budget": budget,
        "original_limits": old.limits.model_dump(mode="json"),
        "normal_output_tokens": 40000,
        "correction_output_tokens": 25000,
        "context_tokens": 60000,
        "evaluation_reserve_seconds": old.evaluation_reserve_seconds,
        "runtime_hash": runtime_content_hash(),
        "implementation_hash": exposure.implementation_hash(),
        "host_file_hashes": {
            p: sha256_bytes((repository_root() / p).read_bytes()) for p in HOST_FILES
        },
        "executing_probe_identity": {
            "image_digest": old.probe_image_digest,
            "profile_hash": old.probe_profile_hash,
        },
        "pair": pair,
        "pricing": {k: str(v) for k, v in asdict(pricing_for_model(old.model)).items()},
        "sdk_retries": 0,
        "automatic_resume": False,
        "stop_at": "first settled run_probe batch, model stop, or ordinary terminal",
        "scope": "first reproduction only; no mutation, required checks, finish or evaluation",
        "public_reconstruction": (
            "same saved public messages and calls/results; all reasoning items removed"
        ),
        "historical_allocations_reopened": False,
    }
    loaded.requests = requests
    return plan, loaded


def restore(plan, loaded, root, arm, *, live_mode=False):
    branch = exposure._fork(
        loaded.source,
        plan["cut_sequence"],
        root,
        arm,
        new_cap_usd=Decimal(plan["row_new_cap_nanos"]) / 10**9,
        mode="funded-observation" if live_mode else "offline-scripted-only",
        env_file=Path(plan["credential_file"]) if live_mode else root / "NO_CREDENTIAL_FILE",
        preserve_parent_configuration=True,
    )
    branch.arm = arm
    branch.selected = loaded.requests[arm]
    branch.descriptions = {
        label: probe_tool(loaded.requests[label])["description"] for label in ORDER
    }
    return branch


class FirstProbeSettled(Exception):
    """Diagnostic endpoint after durable public action and batch receipts."""

    def __init__(self, result):
        self.result = result


@contextmanager
def diagnostic_hooks(branch):
    build, schemas, record = (
        runner._build_model_input,
        runner.dev_tool_schemas,
        runner._record_tool_batch,
    )
    first = []

    def model_input(**kwargs):
        actual = build(**kwargs)
        if not first:
            state = json.loads(actual[-1]["content"])["state"]
            require(
                state["workflow_gate"] == "needs_original_reproduction",
                "restored original gate differs",
            )
            frozen = copy.deepcopy(branch.selected["input"])
            segments.start(
                kwargs["journal"],
                kwargs["artifact_store"],
                base=frozen[:3],
                state={
                    **json.loads(frozen[-1]["content"])["state"],
                    "public_task": json.loads(frozen[1]["content"])["public_task"],
                },
                reason="diagnostic_public_checkpoint",
                parent_input_artifact=None,
                boundary_policy=branch.request.segment_boundary_policy,
                agent_policy=branch.request.agent_policy,
                prepare=True,
            )
            first.append(True)
            # The frozen public checkpoint is the intervention's common input.
            # Host state/counters are independently restored and validated by _fork.
            return frozen
        return actual

    def stage_schemas(**kwargs):
        require(
            kwargs.get("original_acquisition_pending") is True,
            "diagnostic cannot continue beyond original acquisition",
        )
        result = schemas(**kwargs)
        request = {"tools": result}
        probe_tool(request)["description"] = branch.descriptions[branch.arm]
        require(result == branch.selected["tools"], "schema or host tool availability changed")
        return result

    def batch(**kwargs):
        result = record(**kwargs)
        probes = [item for item in kwargs["results"] if item.tool == "run_probe"]
        if probes:
            require(len(probes) == len(kwargs["results"]) == 1, "single probe required")
            raise FirstProbeSettled(probes[0].model_dump(mode="json"))
        return result

    with (
        patch.object(runner, "_build_model_input", model_input),
        patch.object(runner, "dev_tool_schemas", stage_schemas),
        patch.object(runner, "_record_tool_batch", batch),
    ):
        yield


def forbidden(*args, **kwargs):
    raise RuntimeError("offline preparation cannot access credentials, network or targets")


def run_branch(branch, group, journal, store, *, client=None, synthetic_probe_outcomes=None):
    ledger = ContinuationLedger(branch, group, journal, branch.arm)
    counted, dispatched = [], []

    class Adapter(OpenAIResponsesAdapter):
        def count_input_tokens_v2(self, payload, **kwargs):
            self.pending = None
            if not counted:
                require(
                    payload == branch.selected,
                    "first request differs from frozen public checkpoint",
                )
                require(
                    payload["input"] == public_input(payload["input"]),
                    "historical opaque reasoning leaked",
                )
            counted.append(copy.deepcopy(payload))
            journal.append(
                "actual_input_count_started",
                {"arm": branch.arm, "request_hash": sha256_json(payload)},
            )
            result = super().count_input_tokens_v2(payload, **kwargs)
            self.pending = copy.deepcopy(payload)
            return result

        def execute_request(self, payload, **kwargs):
            expected, self.pending = self.pending, None
            require(expected is not None, "dispatch without successful count")
            require(
                0 < payload["max_output_tokens"] <= expected["max_output_tokens"],
                "output grew after count",
            )
            expected["max_output_tokens"] = payload["max_output_tokens"]
            require(payload == expected, "count and dispatch differ")
            dispatched.append(copy.deepcopy(payload))
            journal.append(
                "actual_dispatch_started", {"arm": branch.arm, "request_hash": sha256_json(payload)}
            )
            return super().execute_request(payload, **kwargs)

    def make_adapter(config, **kwargs):
        if client is not None:
            return Adapter(config, api_key="offline-unused", client=client)
        return Adapter(config, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(inherited_reads(branch))
        stack.enter_context(diagnostic_hooks(branch))
        stack.enter_context(patch.object(runner, "OpenAIResponsesAdapter", make_adapter))
        if client is not None:
            stack.enter_context(patch("socket.socket.connect", forbidden))
            stack.enter_context(
                patch.object(runner, "load_exact_openai_api_key", lambda _: "offline-unused")
            )
            stack.enter_context(
                patch.object(runner, "_live_source_preflight", lambda *a, **k: None)
            )
            stack.enter_context(
                patch.object(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox())
            )
            stack.enter_context(
                patch.object(
                    runner,
                    "DockerProbeSandbox",
                    lambda **kw: exposure.SyntheticProbe(
                        branch.envelope, synthetic_probe_outcomes or {}, **kw
                    ),
                )
            )
        stack.enter_context(branch.journal.execution_lock())
        try:
            outcome = runner._run_one_locked(
                request=branch.request,
                task_dir=branch.task_dir,
                package=branch.package,
                state_root=branch.root,
                pricing=branch.pricing,
                cost_ledger=ledger,
                runtime_hash=branch.envelope.runtime_hash,
                model_hash=branch.envelope.model_hash,
                run_id=branch.journal.run_id,
                journal=branch.journal,
                envelope=branch.envelope,
                resuming=True,
            )
            result = {"terminal": outcome.public["terminal"], "public": outcome.public}
            stop_remaining = (
                outcome.stop_remaining and outcome.public["terminal"] != "COST_CAP_REACHED"
            )
        except FirstProbeSettled as settled:
            result = {"terminal": "FIRST_PROBE_SETTLED", "probe_result": settled.result}
            abort, _ = runner._batch_execution_abort(
                [runner.DevToolResult.model_validate(settled.result)]
            )
            stop_remaining = abort is not None
        known = runner._provider_usage_failure(branch.journal) is None
        uncertain_count = branch.journal.unresolved_input_count() is not None
        receipt = {
            "arm": branch.arm,
            "result": result,
            "billing_known": known,
            "input_counts": len(counted),
            "model_dispatches": len(dispatched),
            "new_cost_nanos": ledger.spent_nanos - branch.initial_spent_nanos if known else None,
            "stop_remaining": bool(stop_remaining or not known or uncertain_count),
            "task_acceptance": "NOT_RUN",
            "repair_efficacy": "NOT_ESTABLISHED",
        }
        branch.journal.append("first_reproduction_diagnostic_finished", receipt)
    return receipt


def prepare(source, cut_sequence, env_file, result_root, output):
    plan, loaded = controls(source, cut_sequence, env_file, result_root)
    disjoint(output.resolve(), (repository_root(), source.root, result_root.resolve()))
    require(not result_root.exists(), "result root already used")
    output.mkdir()
    journal = DevJournal(output, "run_dev_firstreproductionpreparation")
    store = ArtifactStore(output / "artifacts")
    rehearsals = {}
    for arm in ORDER:
        branch = restore(plan, loaded, output / arm, arm)
        client = ScriptedClient(
            [
                [
                    {
                        "name": "stop_task",
                        "action_id": "offline_stop",
                        "arguments": {
                            "reason_code": "insufficient_public_evidence",
                            "summary": "Offline checkpoint preparation.",
                        },
                    }
                ]
            ]
        )
        group = DevCostLedger(Decimal(plan["new_cap_nanos"]) / 10**9, branch.pricing)
        receipt = run_branch(branch, group, journal, store, client=client)
        require(
            receipt["result"]["terminal"] == "AGENT_STOPPED"
            and receipt["input_counts"] == receipt["model_dispatches"] == 1,
            "offline ordinary-runner preparation failed: " + canonical_json(receipt),
        )
        rehearsals[arm] = receipt
        (output / f"{arm}-first.json").write_text(
            canonical_json(loaded.requests[arm]) + "\n", encoding="utf-8"
        )
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    receipt = {
        "manifest": str(output / "manifest.json"),
        "manifest_hash": sha256_bytes(raw),
        "rehearsals": rehearsals,
        "provider_calls": 0,
        "input_count_calls": 0,
        "credential_reads": 0,
        "target_executions": 0,
        "paid_execution_authorized": False,
    }
    journal.append("prepared", receipt)
    return receipt


def validate(manifest, digest, approved_cap_usd=None):
    raw = manifest.read_bytes()
    require(sha256_bytes(raw) == digest, "manifest hash differs")
    plan = json.loads(raw)
    current, loaded = controls(
        Source.from_record(plan["source"]),
        plan["cut_sequence"],
        Path(plan["credential_file"]),
        Path(plan["result_root"]),
    )
    require(plan == current, "prepared controls/runtime changed")
    if approved_cap_usd is not None:
        require(usd_to_nanos(approved_cap_usd) == plan["new_cap_nanos"], "approved cap differs")
    for arm in ORDER:
        require(
            json.loads((manifest.parent / f"{arm}-first.json").read_bytes())
            == loaded.requests[arm],
            "prepared request changed",
        )
    return plan, loaded


def clean_implementation():
    root = repository_root()
    runner._require_tracked_clean_paths(root, [
        *runtime_content_paths(root),
        *sorted(path.relative_to(root).as_posix()
                for path in (root / "diagnostics").glob("*.py")),
    ])


def collect(manifest, approved_manifest_hash, approved_cap_usd):
    plan, loaded = validate(manifest, approved_manifest_hash, approved_cap_usd)
    root = Path(plan["result_root"])
    disjoint(root, (repository_root(), loaded.source.root, manifest.parent))
    clean_implementation()
    root.mkdir()
    journal = DevJournal(root, "run_dev_firstreproductioncomparison")
    store = ArtifactStore(root / "artifacts")
    group = DevCostLedger(approved_cap_usd, pricing_for_model(plan["model"]))
    rows = [{"arm": arm, "status": "NOT_RUN"} for arm in ORDER]
    journal.append(
        "authorized",
        {"manifest_hash": approved_manifest_hash, "new_cap_nanos": plan["new_cap_nanos"]},
    )
    preflight = live.check_environment(
        {"source": plan["source"], "executing_probe_identity": plan["executing_probe_identity"]},
        Path(plan["credential_file"]),
    )
    journal.append("environment_checked", preflight)
    stop = None if preflight["status"] == "READY" else "PREFLIGHT_FAILED"
    for index, arm in enumerate(ORDER):
        if stop is not None:
            break
        branch = None
        try:
            branch = restore(plan, loaded, root / arm, arm, live_mode=True)
            row = run_branch(branch, group, journal, store)
        except Exception as exc:
            row = {
                "arm": arm,
                "status": "COLLECTOR_FAILED",
                "error_type": type(exc).__name__,
                "billing_known": branch is None
                or runner._provider_usage_failure(branch.journal) is None,
                "stop_remaining": True,
            }
        rows[index] = row
        journal.append("row_finished", row)
        if row["stop_remaining"]:
            stop = row.get("result", {}).get("terminal", row.get("status"))
    receipt = {
        "official": False,
        "manifest_hash": approved_manifest_hash,
        "rows": rows,
        "stop_reason": stop,
        "recorded_new_cost_nanos": group.spent_nanos,
        "billing_known": all(row.get("billing_known", True) for row in rows),
        "task_acceptance": "NOT_RUN",
        "repair_efficacy": "NOT_ESTABLISHED",
    }
    journal.append("comparison_finished", receipt)
    (root / "result.json").write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    for key in ("source-root", "public-task", "env-file", "result-root", "output"):
        prep.add_argument("--" + key, type=Path, required=True)
    prep.add_argument("--run-id", required=True)
    prep.add_argument("--cut-sequence", type=int, required=True)
    for name in ("validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--approved-manifest-hash", required=True)
        command.add_argument("--approved-cap-usd", type=Decimal, required=name == "collect")
    args = vars(parser.parse_args())
    name = args.pop("command")
    if name == "prepare":
        source = source_record(args.pop("source_root"), args.pop("run_id"), args.pop("public_task"))
        result = prepare(source=source, **args)
    elif name == "validate":
        validate(args["manifest"], args["approved_manifest_hash"], args["approved_cap_usd"])
        result = {"status": "VALID", "provider_calls": 0, "target_executions": 0}
    else:
        result = collect(**args)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
