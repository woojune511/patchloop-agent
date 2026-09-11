"""Exact-grant short-episode collector; prepare/validate/inspect never call a provider.

Fresh independent starts, existing agent actions, no private evaluation or resume.
The fixed $5 proposal is not authority. Only collect with a matching explicit grant
can load a credential or preflight existing Docker/images. No start/pull/build path.
"""

from __future__ import annotations

import argparse
import json
import secrets
import uuid
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_rollout as engine
from diagnostics import model_state_episode as episode
from diagnostics import model_state_review as review
from diagnostics import model_state_sampler as design
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import PROBE_IMAGE_DIGEST, DockerProbeSandbox, probe_profile_hash
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text, utc_now

KIND = "model-state-short-episode-collector-v1"
CAP = Decimal("5.00")
SECONDS = 1800
BOUNDARIES = episode.BOUNDARIES


def implementation_hashes():
    return {
        p.name: sha256_bytes(p.read_bytes())
        for p in (
            Path(__file__),
            Path(episode.__file__),
            Path(engine.__file__),
            Path(review.__file__),
        )
    }


def proposal(frozen, preparation_path, preparation_hash, task_dir, result_root):
    """Rebuild the contract from verified public inputs and actual task bytes."""
    raw = preparation_path.read_bytes()
    shared.require(sha256_bytes(raw) == preparation_hash, "preparation hash mismatch")
    prepared = json.loads(raw)
    shared.require(
        prepared["schema_version"] == episode.PREPARATION_SCHEMA
        and prepared["input_contract_hash"] == episode.INPUT_CONTRACT_HASH
        and prepared["source_packet_hash"] == frozen.packet_hash
        and prepared["runtime_hash"] == frozen.packet["runtime_hash"]
        and prepared["prior_sample_responses_reused"] == 0
        and prepared["max_responses_per_episode"] == episode.MAX_RESPONSES,
        "preparation contract mismatch",
    )
    store = design.readonly_store(preparation_path.parent)
    shared.require(len(prepared["cells"]) == len(frozen.cells), "cell count mismatch")
    for row, cell in zip(prepared["cells"], frozen.cells, strict=True):
        request = review.read_json(store, row["request_artifact"])
        shared.require(
            (row["case_id"], row["arm"], row["repeat"])
            == (cell.case_id, cell.arm, cell.sample_number)
            and row["source_request_hash"] == cell.request_hash
            and row["request_hash"] == sha256_json(request)
            and row["ordered_request_hash"] == sha256_bytes(design.wire(request))
            and design.wire(request) == design.wire(
                episode.episode_request(json.loads(cell.request_json))),
            "prepared request mismatch",
        )
    package = load_task_package(task_dir)
    shared.require(
        package.public.split == "dev-train"
        and (package.public.task_id, package.public.task_version, package.task_content_hash)
        == (
            frozen.packet["task_id"],
            frozen.packet["task_version"],
            frozen.packet["task_content_hash"],
        ),
        "task identity mismatch",
    )
    shared.require(package.environment is not None, "declared Docker environment required")
    contract = {
        **BOUNDARIES,
        "kind": KIND,
        "status": "READY_FOR_EXACT_APPROVAL",
        "paid_execution_authorized": False,
        "actual_provider_calls": 0,
        "preparation_path": str(preparation_path.resolve()),
        "preparation_hash": preparation_hash,
        "source_packet_path": str(frozen.packet_path),
        "source_packet_hash": frozen.packet_hash,
        "source_root": str(frozen.source_root),
        "source_run_id": frozen.packet["source_run_id"],
        "source_journal_hash": frozen.packet["source_journal_hash"],
        "source_envelope_hash": frozen.packet["source_envelope_hash"],
        "runtime_hash": frozen.packet["runtime_hash"],
        "implementation_hashes": implementation_hashes(),
        "inherited_sampler_hash": design.sampler_hash(),
        "task_dir": str(task_dir.resolve()),
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "task_content_hash": package.task_content_hash,
        "evaluator_image": package.environment.evaluator_image,
        "evaluator_image_digest": package.environment.image_digest,
        "probe_image_digest": PROBE_IMAGE_DIGEST,
        "probe_profile_hash": probe_profile_hash(),
        "credential_file": str((repository_root() / ".env").resolve()),
        "credential_path_hash": sha256_text(str((repository_root() / ".env").resolve())),
        "result_root": str(result_root.resolve()),
        "models": {
            a: shared.model_config("medium", p.model_id).model_dump(mode="json")
            for a, p in design.PROFILES.items()
        },
        "prices": shared.protocol_prices(design.PROTOCOL),
        "pricing_hash": sha256_json(shared.protocol_prices(design.PROTOCOL)),
        "pricing_source": "https://developers.openai.com/api/docs/pricing",
        "pricing_review_on_execution_date_required": True,
        "proposed_total_cap_usd": str(CAP),
        "active_seconds": SECONDS,
        "read_only_metadata_tail_seconds": 10,
        "first_requests": prepared["cells"],
        "input_contract_hash": episode.INPUT_CONTRACT_HASH,
        "comparison_groups": [list(b) for b in design.BLOCKS],
        "max_responses_per_episode": episode.MAX_RESPONSES,
        "maximum_generation_calls": len(frozen.cells) * episode.MAX_RESPONSES,
        "maximum_input_count_calls": len(frozen.cells) * episode.MAX_RESPONSES,
        "input_token_limit": episode.INPUT_BOUND,
        "output_ceiling": shared.OUTPUT_CEILING,
        "four_arm_depth_reservation_nanos": sum(
            shared.full_reservation(episode.INPUT_BOUND, p.pricing())
            for p in design.PROFILES.values()
        ),
        "schedule": "group order; fixed arm order round-robin at each depth; skip terminal arms",
        "history_factor": "Inherited state only; all new native exchanges retained in all arms",
        "budget_policy": "reserve all active arms; stop whole invocation on cap/uncertainty",
        "limitations": [
            "$5 does not guarantee all 16 windows or 128 responses",
            "steps/cost/deadline censorship is not agent failure",
            "no automatic checks, judge, hidden evaluator, or agent defaults change",
        ],
    }
    return contract, package


@dataclass(frozen=True)
class Plan:
    path: Path
    packet_hash: str
    packet: dict
    frozen: shared.FrozenPlan
    package: object


def prepare(frozen, preparation_path, preparation_hash, task_dir, root, result_root):
    result_root = design.fresh_root(
        result_root,
        frozen.source_root,
        frozen.packet_path.parent,
        preparation_path.parent,
        root.resolve(),
    )
    contract, _ = proposal(frozen, preparation_path, preparation_hash, task_dir, result_root)
    root = design.fresh_root(
        root, frozen.source_root, frozen.packet_path.parent, preparation_path.parent
    )
    store = ArtifactStore(root)
    ref = store.put_json(contract)
    store.write_text_immutable(root / "packet.json", canonical_json(contract))
    DevJournal(root, "run_dev_episode_execution_design").append(
        "terminal",
        {"packet_artifact": ref.model_dump(mode="json"), "packet_hash": ref.content_hash},
    )
    return contract


def load_plan(path: Path, expected_hash: str) -> Plan:
    raw = path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "execution packet hash mismatch")
    packet = json.loads(raw)
    shared.require(packet["kind"] == KIND, "not an episode execution packet")
    frozen = design.load_plan(
        Path(packet["source_packet_path"]),
        Path(packet["source_root"]),
        packet["source_packet_hash"],
    )
    actual, package = proposal(
        frozen,
        Path(packet["preparation_path"]),
        packet["preparation_hash"],
        Path(packet["task_dir"]),
        Path(packet["result_root"]),
    )
    shared.require(packet == actual, "execution contract or implementation changed")
    return Plan(path.resolve(), expected_hash, packet, frozen, package)


def validate_grant(plan, grant):
    shared.require(
        grant.packet_hash == plan.packet_hash
        and grant.sampler_hash == sha256_json(plan.packet["implementation_hashes"]),
        "exact packet/implementation approval required",
    )
    shared.require(
        grant.max_cost_usd == CAP and grant.pricing_hash == plan.packet["pricing_hash"],
        "cap or pricing approval mismatch",
    )
    shared.require(
        grant.pricing_verified_on == utc_now().date().isoformat(),
        "pricing must be reviewed on execution UTC date",
    )
    shared.require(
        grant.credential_file.is_absolute()
        and str(grant.credential_file.resolve()) == plan.packet["credential_file"],
        "exact credential path required",
    )
    shared.require(
        grant.result_root.is_absolute()
        and str(grant.result_root.resolve()) == plan.packet["result_root"],
        "approved result root mismatch",
    )
    return design.fresh_root(
        grant.result_root,
        plan.path.parent,
        plan.frozen.source_root,
        plan.frozen.packet_path.parent,
        Path(plan.packet["preparation_path"]).parent,
    )


def _events(root, registered):
    branch_root = (root / "branches" / registered["anonymous_id"]).resolve()
    shared.require(branch_root.parent == root / "branches", "invalid branch identity")
    paths = sorted((branch_root / "runs").glob("run_dev_*.jsonl"))
    shared.require(len(paths) <= 1, "ambiguous branch journal")
    return [] if not paths else DevJournal(branch_root, paths[0].stem).events()


def evidence_totals(root, events):
    records = [e["payload"] for e in events if e["event_type"] == "branch_registered"]
    all_events = [
        e
        for record in records
        for e in _events(root, record)
        if not e["payload"].get("diagnostic_inherited")
    ]
    counts = {
        e["payload"]["count_id"] for e in all_events if e["event_type"] == "input_count_started"
    }
    counted = {
        e["payload"]["count_id"] for e in all_events if e["event_type"] == "input_count_finished"
    }
    calls = {
        e["payload"]["call_id"] for e in all_events if e["event_type"] == "provider_call_started"
    }
    finished = [e["payload"] for e in all_events if e["event_type"] == "provider_call_finished"]
    unknown = bool(calls - {e["call_id"] for e in finished}) or any(
        e.get("billing_known") is not True for e in finished
    )
    return {
        "provider_calls": len(calls),
        "input_count_calls": len(counts),
        "tool_actions_started": sum(e["event_type"] == "action_started" for e in all_events),
        "tool_actions_requested": sum(
            len(e["payload"]["tool_calls"])
            for e in all_events
            if e["event_type"] == "tool_batch_started"
        ),
        "tool_actions_finished": sum(e["event_type"] == "action_finished" for e in all_events),
        "recorded_cost_nanos": sum(e.get("cost_nanos") or 0 for e in finished),
        "total_cost_known": not unknown,
        "input_count_unknown": bool(counts - counted),
        "registered_episodes": len(records),
    }


def inspect(root: Path):
    """Read-only crash diagnosis. A durable terminal wins; never replay any action."""
    root = root.resolve()
    envelope = json.loads((root / "envelope.json").read_bytes())
    shared.require(envelope["kind"] == KIND, "not an episode collection")
    shared.require((root / "runs").is_dir(), "collection journal missing")
    journal = DevJournal(root, envelope["run_id"])
    events = journal.events()
    store = design.readonly_store(root)
    shared.require(
        review.read_json(store, events[0]["payload"]["envelope_artifact"]) == envelope,
        "envelope identity mismatch",
    )
    terminal = journal.terminal()
    if terminal is not None:
        result = terminal["payload"]
        if (root / "result.json").exists():
            shared.require(
                json.loads((root / "result.json").read_bytes()) == result,
                "terminal result mismatch",
            )
        review.read_json(store, result["review_artifact"])
        return result
    totals = evidence_totals(root, events)
    code = (
        "PROVIDER_TIMEOUT_OR_UNKNOWN"
        if not totals["total_cost_known"]
        else "COUNT_TIMEOUT_OR_UNKNOWN"
        if totals["input_count_unknown"]
        else "INTERRUPTED"
    )
    return {
        **BOUNDARIES,
        **totals,
        "terminal": code,
        "read_only": True,
        "remaining_episodes_unstarted": envelope["planned_episodes"]
        - totals["registered_episodes"],
    }


def public_receipt(registration, branch, store, code, metadata_deadline):
    """Read-only final evidence; never relax the gateway's execution deadline.

    Git metadata can still be collected after execution stops. One bounded tail
    covers all branches; if unavailable, retain the journal without inventing a
    candidate or current PASS. No task, provider, or reconciliation runs here.
    """
    snapshot_error, summary = None, None
    try:
        summary = WorkspaceManager.diff_summary(
            branch.gateway.workspace, deadline=metadata_deadline
        )
        if branch.terminal is not None and (
            branch.terminal["current_diff_hash"] != summary.patch_hash
        ):
            snapshot_error, summary = "TerminalCandidateMismatch", None
    except Exception as exc:
        snapshot_error = type(exc).__name__
    if branch.terminal is None:
        branch.terminal = {
            **BOUNDARIES,
            "branch": branch.label,
            "terminal": "DIAGNOSTIC_ABORTED",
            "message": code,
            "censored": True,
            "provider_calls": branch.new_provider_calls,
            "tool_actions": branch.new_tools,
            "cost_nanos": branch.new_cost_nanos,
            "accepted_mutations_since_checkpoint": (
                branch.gateway.accepted_mutations - branch.initial_mutations
            ),
            "current_diff_hash": summary.patch_hash if summary is not None else None,
            "visible_checks": branch.gateway.visible_check_status(diff_hash=summary.patch_hash)
            if summary is not None
            else [],
            "snapshot_error": snapshot_error,
        }
        branch.journal.append("terminal", branch.terminal)
    events = [e for e in branch.journal.events() if not e["payload"].get("diagnostic_inherited")]
    observations = [e["payload"]["result"] for e in events if e["event_type"] == "action_finished"]
    decisions = [
        {"tool_calls": e["payload"]["tool_calls"], "error_code": e["payload"].get("error_code")}
        for e in events
        if e["event_type"] == "turn_decision_recorded"
    ]
    return {
        "anonymous_id": registration["anonymous_id"],
        "case_id": registration["case_id"],
        "outcome": {
            k: branch.terminal[k]
            for k in ("terminal", "censored", "current_diff_hash", "visible_checks")
        },
        "actions": store.put_json(observations).model_dump(mode="json"),
        "decision_batches": store.put_json(decisions).model_dump(mode="json"),
        "candidate": store.put_text(summary.patch, "text/x-diff").model_dump(mode="json")
        if summary is not None
        else None,
        "snapshot_error": snapshot_error,
    }


def collect(
    plan,
    grant,
    *,
    adapter_factory=None,
    sandbox=None,
    probe=None,
    clock=monotonic,
    initializer=episode.initialize,
    checkpoint=lambda _: None,
):
    """The sole live entry: exact disk revalidation, exclusive root, lock, durable receipt."""
    root = validate_grant(plan, grant)
    plan = load_plan(plan.path, grant.packet_hash)
    root.mkdir(exist_ok=False)  # Atomic one-invocation claim, including concurrent starts.
    store = ArtifactStore(root)
    journal = DevJournal(root, "run_dev_episode_collection_" + uuid.uuid4().hex[:16])
    started = clock()
    deadline = ExecutionDeadline.from_remaining(SECONDS, clock=clock)
    ledger = shared.SharedCostLedger(grant.max_cost_usd)
    envelope = {
        **BOUNDARIES,
        "kind": KIND,
        "run_id": journal.run_id,
        "packet_hash": plan.packet_hash,
        "packet_artifact": store.put_json(plan.packet).model_dump(mode="json"),
        "result_root": str(root),
        "credential_path_hash": plan.packet["credential_path_hash"],
        "cap_nanos": ledger.cap_nanos,
        "pricing_hash": grant.pricing_hash,
        "pricing_verified_on": grant.pricing_verified_on,
        "planned_episodes": len(plan.frozen.cells),
        "provider_free": adapter_factory is not None,
    }
    envelope_ref = store.put_json(envelope)
    store.write_text_immutable(root / "envelope.json", canonical_json(envelope))
    branches, public, clients = [], [], {}
    code, failure_type = "OBSERVATION_WINDOWS_COMPLETED", None
    with journal.execution_lock(), ExitStack() as locks:
        journal.append(
            "collector_started", {"envelope_artifact": envelope_ref.model_dump(mode="json")}
        )
        try:
            deadline.check()
            if adapter_factory is None:
                loop._live_source_preflight(
                    Path(plan.packet["task_dir"]), plan.package, deadline=deadline
                )
                sandbox = loop._live_sandbox_preflight(plan.package, deadline=deadline)
                probe = DockerProbeSandbox()
                probe.preflight(deadline=deadline)
            shared.require(
                sandbox is not None and probe is not None,
                "explicit public check/probe backends required",
            )
            journal.append(
                "preflight_finished",
                {
                    "provider_free": adapter_factory is not None,
                    "task_content_hash": plan.package.task_content_hash,
                },
            )
            (root / "branches").mkdir()
            (root / "workspaces").mkdir()

            class Adapters:
                def __getitem__(self, arm):
                    config = shared.model_config("medium", design.PROFILES[arm].model_id)
                    if adapter_factory is not None:
                        adapter = adapter_factory(config)
                    else:
                        if config.model_id not in clients:
                            key = shared.load_exact_openai_api_key(grant.credential_file)
                            client = shared.create_openai_client(config, api_key=key)
                            del key
                            clients[config.model_id] = client

                            def close_client(selected=client):
                                with suppress(Exception):
                                    selected.close()

                            locks.callback(close_client)
                        adapter = OpenAIResponsesAdapter(
                            config, api_key="", client=clients[config.model_id]
                        )
                    shared.require(
                        adapter.config == config and adapter.client.max_retries == 0,
                        "adapter contract mismatch",
                    )
                    return adapter

            for case, repeat, arms in design.BLOCKS:
                deadline.check()
                if plan.packet["four_arm_depth_reservation_nanos"] > ledger.remaining_nanos:
                    code = "DIAGNOSTIC_COST_LIMIT"
                    break
                group = []
                for arm in arms:
                    cell = next(
                        c
                        for c in plan.frozen.cells
                        if (c.case_id, c.arm, c.sample_number) == (case, arm, repeat)
                    )
                    anonymous_id = "episode_" + uuid.uuid4().hex[:16]
                    registration = {
                        "anonymous_id": anonymous_id,
                        "case_id": case,
                        "arm": arm,
                        "repeat": repeat,
                    }
                    journal.append("branch_registered", registration)
                    b = initializer(
                        plan.frozen,
                        cell,
                        root / "branches" / anonymous_id,
                        root / "workspaces" / anonymous_id,
                        plan.package,
                        sandbox,
                        probe_sandbox=probe,
                        clock=clock,
                        execution_deadline=deadline,
                    )
                    branches.append((registration, b))
                    group.append(b)
                    locks.enter_context(b.journal.execution_lock())
                while any(b.terminal is None for b in group):
                    deadline.check()
                    episode.run_round(
                        group, plan.package, Adapters(), ledger, checkpoint=checkpoint
                    )
                if any(b.terminal["terminal"] == "DIAGNOSTIC_COST_LIMIT" for b in group):
                    code = "DIAGNOSTIC_COST_LIMIT"
                    break
        except engine.AbortExperiment as exc:
            code = exc.code
        except ExecutionDeadlineExceeded:
            code = "LIMIT_REACHED"
        except (KeyboardInterrupt, SystemExit):
            code = "INTERRUPTED"
        except Exception as exc:
            code, failure_type = "COLLECTOR_ERROR", type(exc).__name__
        # No call/action retry after any error. Disk journal, not in-memory counters, is authority.
        totals = evidence_totals(root, journal.events())
        if not totals["total_cost_known"]:
            code = "PROVIDER_TIMEOUT_OR_UNKNOWN"
        elif totals["input_count_unknown"]:
            code = "COUNT_TIMEOUT_OR_UNKNOWN"
        elif deadline.remaining_seconds() <= 0:
            code = "LIMIT_REACHED"
        metadata_deadline = ExecutionDeadline.from_remaining(
            plan.packet["read_only_metadata_tail_seconds"]
        )
        # Public review omits condition/model/usage. The execution deadline remains unchanged.
        for registration, b in branches:
            public.append(public_receipt(registration, b, store, code, metadata_deadline))
        secrets.SystemRandom().shuffle(public)
        review_ref = store.put_json({**BOUNDARIES, "episodes": public, "grading": "NOT_ASSESSED"})
        result = {
            **BOUNDARIES,
            **totals,
            "terminal": code,
            "failure_type": failure_type,
            "run_id": journal.run_id,
            "packet_hash": plan.packet_hash,
            "completed_episode_records": len(public),
            "candidate_snapshots_unavailable": sum(p["candidate"] is None for p in public),
            "review_state": "PARTIAL"
            if any(p["candidate"] is None for p in public)
            else "READY_FOR_BLIND_REVIEW",
            "unstarted_episodes": len(plan.frozen.cells) - totals["registered_episodes"],
            "elapsed_ms": int((clock() - started) * 1000),
            "review_artifact": review_ref.model_dump(mode="json"),
            "provider_free": adapter_factory is not None,
        }
        journal.append("terminal", result)
        store.write_text_immutable(root / "result.json", canonical_json(result))
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "validate", "collect", "inspect"])
    for name in (
        "packet",
        "preparation",
        "source-root",
        "task-dir",
        "output-root",
        "result-root",
        "credential-file",
    ):
        parser.add_argument("--" + name, type=Path)
    for name in (
        "packet-hash",
        "preparation-hash",
        "implementation-hash",
        "pricing-hash",
        "pricing-verified-on",
    ):
        parser.add_argument("--" + name)
    parser.add_argument("--max-cost-usd", type=Decimal)
    parser.add_argument("--approve-exact-episode-invocation", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "inspect":
        result = inspect(args.result_root)
    elif args.command == "prepare":
        frozen = design.load_plan(args.packet, args.source_root, args.packet_hash)
        packet = prepare(
            frozen,
            args.preparation,
            args.preparation_hash,
            args.task_dir,
            args.output_root,
            args.result_root,
        )
        result = {
            "status": packet["status"],
            "packet_hash": sha256_json(packet),
            "implementation_hash": sha256_json(packet["implementation_hashes"]),
        }
    else:
        plan = load_plan(args.packet, args.packet_hash)
        if args.command == "validate":
            result = {
                "status": "VALIDATED_NOT_EXECUTED",
                "packet_hash": plan.packet_hash,
                "implementation_hash": sha256_json(plan.packet["implementation_hashes"]),
                "pricing_hash": plan.packet["pricing_hash"],
                "cap_usd": str(CAP),
                "provider_calls": 0,
                "docker_operations": 0,
            }
        else:
            shared.require(
                args.approve_exact_episode_invocation
                and all(
                    (
                        args.implementation_hash,
                        args.result_root,
                        args.credential_file,
                        args.max_cost_usd,
                        args.pricing_hash,
                        args.pricing_verified_on,
                    )
                ),
                "an exact fresh execution grant is required",
            )
            grant = shared.Approval(
                args.packet_hash,
                args.implementation_hash,
                args.result_root,
                args.credential_file,
                args.max_cost_usd,
                args.pricing_hash,
                args.pricing_verified_on,
            )
            result = collect(plan, grant)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
