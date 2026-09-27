"""Single-use, explicitly funded live continuations of a frozen input pair.

Preparation and preflight never count input or call a model. Collection uses the
ordinary registered-action loop with one shared ledger for new usage only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from diagnostics import checkpoint_continuation as continuation
from diagnostics import mutation_advice_checkpoint as checkpoint
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

ORDER = ("A1", "B1", "B2", "A2")
IMPLEMENTATION = (
    "diagnostics/checkpoint_comparison.py",
    "diagnostics/checkpoint_continuation.py",
    ".agent/checkpoint-comparison.md",
    ".agent/checkpoint-continuation.md",
)


def source_state(packet_path, packet_hash):
    checkpoint.validate(packet_path, packet_hash)
    packet = json.loads(packet_path.read_bytes())
    source = Source.from_record(packet["source"])
    envelope = DevJournal(source.root, source.run_id).load_envelope()
    return packet, source, envelope


def controls(packet_path: Path, packet_hash: str, env_file: Path, result_root: Path):
    packet, source, envelope = source_state(packet_path, packet_hash)
    env_file, result_root = env_file.resolve(), result_root.resolve()
    require(sha256_bytes(str(env_file).encode()) == envelope.credential_file_path_hash,
            "credential path differs from the checkpoint")
    disjoint(result_root, (repository_root(), source.root, packet_path.parent,
                           source.public_path.parent))
    remaining = packet["checkpoint"]["remaining_budget"]["cost"]["remaining"]
    require(remaining > 0, "no remaining checkpoint allowance")
    pricing = pricing_for_model(envelope.model)
    return {
        "schema": "checkpoint-live-comparison-v1", "official": False,
        "packet": str(packet_path.resolve()), "packet_hash": packet_hash,
        "task": str(source.public_path.resolve()), "model": envelope.model,
        "reasoning_effort": envelope.reasoning_effort,
        "env_file": str(env_file), "credential_path_hash": envelope.credential_file_path_hash,
        "result_root": str(result_root), "order": list(ORDER), "repeat": len(ORDER),
        "row_new_cap_nanos": remaining, "new_cap_nanos": len(ORDER) * remaining,
        "historical_spent_nanos": packet["checkpoint"]["remaining_budget"]["cost"][
            "settled_usage"],
        "original_row_cap_nanos": envelope.max_cost_nanos,
        "remaining_budget": packet["checkpoint"]["remaining_budget"],
        "first_request_hashes": packet["pair"],
        "prepared_source_hash": envelope.prepared_source_hash,
        "probe_dependencies": envelope.probe_dependencies.model_dump(mode="json")
        if envelope.probe_dependencies else None,
        "runtime_hash": envelope.runtime_hash,
        "head": git_commit(),
        "implementation": {p: sha256_bytes((repository_root() / p).read_bytes())
                           for p in IMPLEMENTATION},
        "pricing": {k: str(v) for k, v in asdict(pricing).items()},
        "pricing_source": "https://developers.openai.com/api/docs/pricing",
        "sdk_retries": 0, "automatic_resume": False, "paid_execution_authorized": False,
    }


def check_environment(packet_path: Path, packet_hash: str, env_file: Path):
    """Read-only admission: no credential contents, container runs or provider calls."""
    packet, source, envelope = source_state(packet_path, packet_hash)
    deadline = ExecutionDeadline.from_remaining(120)
    task_dir, package = runner._resolve_task_file(source.public_path)
    checks = {}
    try:
        runner._live_task_is_admitted(task_dir, package)
        runner._live_source_preflight(task_dir, package, deadline=deadline)
        checks["task_and_runtime"] = "PASS"
        require(env_file.is_file(), "credential file does not exist")
        require(sha256_bytes(str(env_file.resolve()).encode())
                == envelope.credential_file_path_hash, "credential path changed")
        checks["credential_path_only"] = "PASS"
        require(envelope.prepared_source_path is not None, "prepared source required")
        runner.load_source(Path(envelope.prepared_source_path), package.public.repository.url,
                           package.public.repository.base_commit,
                           expected_hash=envelope.prepared_source_hash, deadline=deadline)
        checks["prepared_source"] = "PASS"
        dependencies = runner.load_dependencies(
            Path(envelope.prepared_probe_dependencies_path), package.public,
            envelope.probe_dependencies,
        ) if envelope.prepared_probe_dependencies_path else None
        if dependencies is not None:
            dependencies.verify(deadline=deadline)
            checks["prepared_dependencies"] = envelope.probe_dependencies.model_dump(mode="json")
        runner._live_sandbox_preflight(package, deadline=deadline)
        checks["evaluator_image"] = package.environment.image_digest
        identity = runner.DockerProbeSandbox(dependencies=dependencies).preflight(deadline=deadline)
        require(identity == {"image_digest": envelope.probe_image_digest,
                             "profile_hash": envelope.probe_profile_hash},
                "probe environment differs from checkpoint")
        checks["probe_environment"] = identity
        status, error = "READY", None
    except Exception as exc:
        status, error = "PREFLIGHT_FAILED", f"{type(exc).__name__}: {exc}"
    return {"status": status, "checks": checks, "error": error, "official": False,
            "packet_hash": packet_hash, "runtime_hash": packet["runtime_hash"],
            "model_calls": 0, "input_counts": 0, "container_runs": 0,
            "provider_acceptance": "NOT_RUN", "acceptance": "NOT_RUN", "safety": "NOT_RUN"}


def prepare(packet_path, packet_hash, env_file, result_root, output):
    plan = controls(packet_path, packet_hash, env_file, result_root)
    source = Source.from_record(json.loads(packet_path.read_bytes())["source"])
    disjoint(output.resolve(), (repository_root(), source.root, packet_path.parent,
                                result_root.resolve(), source.public_path.parent))
    require(not result_root.exists(), "result root already used")
    runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    output.mkdir()
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    journal = DevJournal(output, "run_dev_checkpointcomparisonpreparation")
    journal.append("comparison_prepared", {"manifest_hash": sha256_bytes(raw), "plan": plan})
    preflight = check_environment(packet_path, packet_hash, env_file)
    journal.append("environment_checked", preflight)
    (output / "preflight.json").write_text(canonical_json(preflight) + "\n", encoding="utf-8")
    return {"manifest": str(output / "manifest.json"), "manifest_hash": sha256_bytes(raw),
            "preflight": preflight, "new_cap_usd": str(Decimal(plan["new_cap_nanos"]) / 10**9)}


class ContinuationLedger(DevCostLedger):
    """Inherited spend affects row allowance; only new settlements affect the group."""

    def __init__(self, branch, group, journal, label):
        super().__init__(branch.request.max_cost_usd, branch.pricing)
        self.spent_nanos = branch.initial_spent_nanos
        self.group, self.journal, self.label = group, journal, label
        self.reservation = None

    def admit(self, input_tokens, **kwargs):
        row = super().admit(input_tokens, **kwargs)
        group = self.group.admit(input_tokens, **kwargs)
        if row is None or group is None:
            return None
        self.reservation = min((row, group), key=lambda a: a.output_ceiling)
        self.journal.append("new_cost_admitted", {
            "row": self.label, **asdict(self.reservation),
            "group_remaining_nanos": self.group.remaining_nanos,
            "row_remaining_nanos": self.remaining_nanos,
        })
        return self.reservation

    def settle(self, **usage):
        require(self.reservation is not None, "new settlement has no admission")
        cost = super().settle(**usage)
        require(self.group.settle(**usage) == cost, "group price mismatch")
        self.journal.append("new_usage_recorded", {"row": self.label, **usage,
                            "provisional_cost_nanos": cost})
        reservation, self.reservation = self.reservation, None
        require(cost <= reservation.reserved_cost_nanos
                and self.spent_nanos <= self.cap_nanos
                and self.group.spent_nanos <= self.group.cap_nanos,
                "usage exceeded admitted cost; stop the invocation")
        return cost


def run_branch(branch, group, journal, store, label):
    ledger = ContinuationLedger(branch, group, journal, label)
    counted, dispatched = [], []

    class RecordedAdapter(OpenAIResponsesAdapter):
        def record(self, kind, request, records):
            if not records:
                require(request == branch.selected, "first request differs from frozen input")
            artifact = store.put_json(request)
            journal.append(kind, {"row": label, "request_hash": sha256_json(request),
                                  "artifact": artifact.model_dump(mode="json")})
            records.append(artifact.content_hash)

        def count_input_tokens_v2(self, request_payload, **kwargs):
            self.record("actual_input_count_started", request_payload, counted)
            return super().count_input_tokens_v2(request_payload, **kwargs)

        def execute_request(self, request_payload, **kwargs):
            self.record("actual_dispatch_started", request_payload, dispatched)
            return super().execute_request(request_payload, **kwargs)

    with (continuation.inherited_reads(branch), continuation.first_input(branch) as first,
          patch.object(runner, "OpenAIResponsesAdapter", RecordedAdapter),
          branch.journal.execution_lock()):
        result = runner._run_one_locked(
            request=branch.request, task_dir=branch.task_dir, package=branch.package,
            state_root=branch.root, pricing=branch.pricing, cost_ledger=ledger,
            runtime_hash=branch.envelope.runtime_hash, model_hash=branch.envelope.model_hash,
            run_id=branch.journal.run_id, journal=branch.journal, envelope=branch.envelope,
            resuming=True,
        )
    billing_known = runner._provider_usage_failure(branch.journal) is None
    terminal = result.public["terminal"]
    stop = (not billing_known or terminal == "PREFLIGHT_FAILED"
            or (result.stop_remaining and terminal != "COST_CAP_REACHED"))
    return {"row": label, "status": "EXECUTED", "result": result.public,
            "first_state_restored": bool(first), "input_counts": len(counted),
            "model_dispatches": len(dispatched), "billing_known": billing_known,
            "new_cost_nanos": ledger.spent_nanos - branch.initial_spent_nanos
            if billing_known else None,
            "historical_spent_nanos": branch.initial_spent_nanos, "stop_remaining": stop}


def collect(manifest_path: Path, approved_hash: str, approved_cap_usd: Decimal):
    raw = manifest_path.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "approved manifest hash differs")
    plan = json.loads(raw)
    require(usd_to_nanos(approved_cap_usd) == plan["new_cap_nanos"], "approved cap differs")
    packet_path, env_file = Path(plan["packet"]), Path(plan["env_file"])
    root = Path(plan["result_root"])
    require(plan == controls(packet_path, plan["packet_hash"], env_file, root),
            "manifest controls or implementation changed")
    runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    # mkdir is the atomic single-use claim: never resume/retry an interrupted group.
    root.mkdir()
    journal = DevJournal(root, "run_dev_checkpointcomparison")
    store = ArtifactStore(root / "artifacts")
    group = DevCostLedger(approved_cap_usd, pricing_for_model(plan["model"]))
    rows = [{"row": label, "status": "NOT_RUN"} for label in ORDER]
    billing_known, stop_reason = True, None
    with journal.execution_lock():
        journal.append("comparison_authorized", {"manifest_hash": approved_hash,
                       "new_cap_nanos": group.cap_nanos, "plan": plan})
        preflight = check_environment(packet_path, plan["packet_hash"], env_file)
        journal.append("environment_checked", preflight)
        if preflight["status"] != "READY":
            stop_reason = "PREFLIGHT_FAILED"
        for index, label in enumerate(ORDER):
            if stop_reason is not None:
                break
            journal.append("row_started", {"row": label})
            branch = None
            try:
                branch = continuation.restore(packet_path, plan["packet_hash"], root / label,
                                              label[0], mode="live-checkpoint")
                branch.request = branch.request.model_copy(update={"env_file": env_file})
                require(runner._credential_file_path_hash(branch.request)
                        == branch.envelope.credential_file_path_hash, "credential path changed")
                row = run_branch(branch, group, journal, store, label)
            except Exception as exc:
                # The branch journal, not a guessed zero charge, determines billing certainty.
                known = branch is None or runner._provider_usage_failure(branch.journal) is None
                row = {"row": label, "status": "COLLECTOR_FAILED",
                       "error_type": type(exc).__name__, "billing_known": known,
                       "stop_remaining": True}
            rows[index] = row
            billing_known = billing_known and row["billing_known"]
            journal.append("row_finished", row)
            if row["stop_remaining"]:
                stop_reason = row.get("result", {}).get("terminal", row["status"])
        receipt = {"official": False, "manifest_hash": approved_hash, "rows": rows,
                   "stop_reason": stop_reason, "billing_known": billing_known,
                   "new_cost_nanos": group.spent_nanos if billing_known else None,
                   "recorded_new_cost_nanos": group.spent_nanos,
                   "new_cap_nanos": group.cap_nanos, "efficacy_claim": "NOT_ESTABLISHED",
                   "historical_allocations_reopened": False}
        journal.append("comparison_finished", receipt)
        (root / "result.json").write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("packet", "env-file", "result-root", "output"):
        prep.add_argument("--" + name, type=Path, required=True)
    prep.add_argument("--packet-hash", required=True)
    live = sub.add_parser("collect")
    live.add_argument("--manifest", type=Path, required=True)
    live.add_argument("--approved-manifest-hash", required=True)
    live.add_argument("--approved-new-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.packet, args.packet_hash, args.env_file, args.result_root, args.output
        )
    else:
        result = collect(args.manifest, args.approved_manifest_hash, args.approved_new_cap_usd)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
