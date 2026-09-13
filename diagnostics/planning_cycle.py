"""Bounded fresh-run planning comparison; delegates all execution to dev-head.

No checkpoint injection, planner model, hidden-feedback prompt, or provider retry.
The cycle authorization is $40 / at most 32 independent $1.20 invocations.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner, working_plan
from patchloop.dev.contracts import DevRunRequest, dev_tool_surface_hash
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SCHEMA = "planning-cycle-v1"
MODEL = "gpt-5.4-mini-2026-03-17"
CAP, RUN_CAP = Decimal("40"), Decimal("1.20")
ORDER = ("A1", "B1", "B2", "A2", "B3", "A3", "A4", "B4")
TASKS = {
    "pyfakefs": "tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2/public.yaml",
    "loguru": "tasks/dev-train/loguru-invalid-format-feedback-v3/public.yaml",
    "hf": "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
}
AXES = ("initial", "plan_instructions", "review_timing", "delivery")
PRICING = {
    "source": "https://developers.openai.com/api/docs/pricing",
    "model": MODEL,
    "service_tier": "default",
    "region": "global",
    "input_per_million": "0.75",
    "cached_input_per_million": "0.075",
    "output_per_million": "4.5",
    "reservation": "uncached-before-each-dispatch",
}


def require(ok, message):
    if not ok:
        raise RecoveryError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(root, relative, value):
    ArtifactStore(root).write_text_immutable(root / relative, canonical_json(value) + "\n")


def control(root):
    return DevJournal(root / "control", "run_dev_planningcycle")


def payloads(journal, kind):
    return [e["payload"] for e in journal.events() if e["event_type"] == kind]


def initialize(root, *, pricing_verified_on, provider="openai"):
    root = root.resolve()
    require(not root.exists(), "new planning cycle requires an unused external directory")
    require(not root.is_relative_to(repository_root()), "cycle state must be external")
    require(provider in {"openai", "mock"}, "invalid cycle provider")
    require(bool(pricing_verified_on), "record the actual official pricing verification date")
    manifest = {
        "schema": SCHEMA,
        "official": False,
        "created_at": utc_now().isoformat(),
        "provider": provider,
        "cap_nanos": usd_to_nanos(CAP),
        "run_cap_nanos": usd_to_nanos(RUN_CAP),
        "max_runs": 32,
        "pricing": {**PRICING, "verified_on": pricing_verified_on},
        "authorization": "User-approved brief planning improvement cycle; total USD 40; "
        "no repeated per-invocation approval; no Docker start/pull/build.",
        "maximum_pyfakefs_versions": 3,
        "pyfakefs_order": ORDER,
        "extension_order": ORDER[:4],
        "task_paths": TASKS,
        "extension_threshold": "B >= 2/4 acceptance PASS, B > A, no integrity failure",
        "normal_failure": "continue to the next independent planned sample",
        "uncertainty": "stop the whole cycle; never retry an unknown provider dispatch",
    }
    save(root, "cycle.json", manifest)
    journal = control(root)
    with journal.execution_lock():
        journal.append("cycle_created", {"manifest_hash": sha256_json(manifest)})
    return manifest


def load_cycle(root):
    manifest = read(root / "cycle.json")
    created = payloads(control(root), "cycle_created")
    require(
        len(created) == 1 and created[0]["manifest_hash"] == sha256_json(manifest),
        "cycle manifest integrity mismatch",
    )
    return manifest


def base_request(manifest, task, arm):
    mock = manifest["provider"] == "mock"
    return DevRunRequest(
        provider=manifest["provider"],
        model="mock-dev" if mock else MODEL,
        task=repository_root()
        / ("tasks/smoke/csv-quoted-newline/public.yaml" if mock else manifest["task_paths"][task]),
        env_file=None if mock else repository_root() / ".env",
        max_cost_usd=None if mock else RUN_CAP,
        repeat=1,
        reasoning_effort="medium",
        context_policy="append-v1",
        enable_probes=True,
        repair_recheck=True,
        planning_policy="none" if arm == "A" else "brief-v1",
    )


def freeze(manifest, task):
    requests = {a: base_request(manifest, task, a) for a in ("A", "B")}
    directory, package = runner._resolve_task_file(requests["A"].task)
    pricing = pricing_for_model(MODEL)
    require(
        (
            str(pricing.input_per_million_usd),
            str(pricing.cached_input_per_million_usd),
            str(pricing.output_per_million_usd),
        )
        == ("0.75", "0.075", "4.5"),
        "registered model price differs from the verified cycle price",
    )
    if manifest["provider"] == "openai":
        runner._live_task_is_admitted(directory, package)
        runner._live_source_preflight(directory, package)
        runner._require_tracked_clean_paths(repository_root(), ["diagnostics/planning_cycle.py"])
    # Exact starting request configuration; per-slot state paths are assigned at execution.
    configs = {a: r.model_dump(mode="json") for a, r in requests.items()}
    require(
        {k: v for k, v in configs["A"].items() if k != "planning_policy"}
        == {k: v for k, v in configs["B"].items() if k != "planning_policy"},
        "A/B differ outside the planning option",
    )
    checks = [c.id for c in package.public.visible_checks]
    schemas = {
        a: dev_tool_schemas(
            finish_enabled=True, check_ids=checks, planning_policy=r.planning_policy
        )
        for a, r in requests.items()
    }
    return {
        "runtime_hash": runner._runtime_hash(),
        "git_commit": git_commit(),
        "executor_hash": sha256_bytes(Path(__file__).read_bytes()),
        "task_content_hash": package.task_content_hash,
        "public_task_hash": sha256_json(package.public.model_dump(mode="json")),
        "base_commit": package.public.repository.base_commit,
        "sandbox_identity_hash": runner._sandbox_identity_hash(requests["A"], package),
        "requests": configs,
        "schemas": schemas,
        "system_prompts": {
            a: assemble_model_input(
                system_prompt=(
                    runner.DEV_SYSTEM_PROMPT + "\n\n" + working_plan.INSTRUCTIONS
                    if a == "B"
                    else runner.DEV_SYSTEM_PROMPT
                ),
                state={},
                history=[],
            )[0]["content"]
            for a in ("A", "B")
        },
        "tool_hashes": {
            a: dev_tool_surface_hash(planning_policy=r.planning_policy) for a, r in requests.items()
        },
        "model_hashes": {
            a: runner._model_hash(r, None if r.provider == "mock" else pricing)
            for a, r in requests.items()
        },
    }


def load_group(root, group_id):
    rows = [p for p in payloads(control(root), "group_prepared") if p["group_id"] == group_id]
    require(len(rows) == 1, "comparison group is not uniquely prepared")
    group = read(root / "groups" / f"{group_id}.json")
    require(sha256_json(group) == rows[0]["group_hash"], "frozen comparison group changed")
    return group


def slot_root(root, group_id, label):
    # Only IDs from the hash-bound group are passed here.
    return root / "state" / f"{group_id}-{label}"


def run_journal(root, group_id, label):
    state = slot_root(root, group_id, label)
    paths = list((state / "runs").glob("*.jsonl"))
    require(len(paths) <= 1, "multiple runs occupy one independent sample slot")
    return DevJournal(state, paths[0].stem) if paths else None


def settled(journal):
    if journal is None:
        return 0
    ledger = DevCostLedger(RUN_CAP, pricing_for_model(MODEL))
    ledger.restore_settled_usage(journal.provider_usage())
    require(ledger.spent_nanos <= ledger.cap_nanos, "invocation exceeded its reserved cap")
    return ledger.spent_nanos


def spent(root):
    return sum(
        settled(run_journal(root, p["group_id"], label))
        for p in payloads(control(root), "group_prepared")
        for label in load_group(root, p["group_id"])["order"]
    )


def admit_group(cap_nanos, spent_nanos, remaining_slots):
    require(
        spent_nanos + remaining_slots * usd_to_nanos(RUN_CAP) <= cap_nanos,
        "cannot reserve every remaining invocation cap in this comparison group",
    )


def prepare_group(root, *, task="pyfakefs", hypothesis, axis="initial", public_evidence=None):
    journal = control(root)
    with journal.execution_lock():
        manifest = load_cycle(root)
        require(
            not payloads(journal, "cycle_stopped") and not payloads(journal, "cycle_closed"),
            "cycle is stopped or closed",
        )
        require(task in TASKS and axis in AXES, "unapproved task or change axis")
        require(0 < len(hypothesis) <= 2000, "a bounded explicit public hypothesis is required")
        previous = payloads(journal, "group_prepared")
        finished = {p["group_id"] for p in payloads(journal, "group_finished")}
        require(all(p["group_id"] in finished for p in previous), "finish the current group first")
        groups = [load_group(root, p["group_id"]) for p in previous]
        py = [g for g in groups if g["task"] == "pyfakefs"]
        current = freeze(manifest, task)
        if task == "pyfakefs":
            require(len(py) < 3 and len(py) == len(groups), "pyfakefs revision stage is closed")
            require(
                not any(group_report(root, g)["extension_eligible"] for g in py),
                "qualified version must be frozen for extension, not retuned",
            )
            if py:
                require(
                    axis != "initial" and bool(public_evidence),
                    "revision needs one change axis and public trace evidence",
                )
                require(
                    current["runtime_hash"] != py[-1]["frozen"]["runtime_hash"],
                    "a follow-up comparison needs an actual planning revision",
                )
            else:
                require(axis == "initial", "first group must be the initial version")
            order = ORDER
        else:
            qualified = [g for g in py if group_report(root, g)["extension_eligible"]]
            require(len(qualified) == 1, "extension requires a qualifying pyfakefs version")
            require(
                current["runtime_hash"] == qualified[0]["frozen"]["runtime_hash"],
                "freeze the qualifying runtime for extension",
            )
            require(task not in [g["task"] for g in groups], "extension task already used")
            require(
                task == ("loguru" if len(groups) == len(py) else "hf"),
                "extension task order must be loguru then hf",
            )
            order = ORDER[:4]
        require(
            sum(len(g["order"]) for g in groups) + len(order) <= manifest["max_runs"],
            "cycle sample maximum reached",
        )
        admit_group(manifest["cap_nanos"], spent(root), len(order))
        group_id = f"g{len(groups) + 1:02d}-{task}"
        group = {
            "schema": SCHEMA,
            "official": False,
            "group_id": group_id,
            "task": task,
            "order": order,
            "hypothesis": hypothesis,
            "change_axis": axis,
            "public_evidence": public_evidence,
            "frozen": current,
            "created_at": utc_now().isoformat(),
            "no_call_validation": True,
        }
        save(root, f"groups/{group_id}.json", group)
        journal.append("group_prepared", {"group_id": group_id, "group_hash": sha256_json(group)})
        return group


def audit_run(journal, arm, *, frozen=None):
    if frozen is not None:
        req = DevRunRequest.model_validate(frozen["requests"][arm])
        directory, package = runner._resolve_task_file(req.task)
        envelope = journal.load_envelope()
        expected = runner._run_envelope(
            request=req,
            task_dir=directory,
            package=package,
            run_id=journal.run_id,
            runtime_hash=frozen["runtime_hash"],
            model_hash=frozen["model_hashes"][arm],
            cost_ledger=(
                DevCostLedger(RUN_CAP, pricing_for_model(MODEL))
                if req.provider == "openai"
                else None
            ),
            cost_start_nanos=0,
            created_at=envelope.created_at,
        )
        require(envelope == expected, "sample envelope differs from frozen A/B identity")
    events, terminal = journal.events(), journal.terminal()
    require(terminal is not None, "trial returned without a durable terminal")
    terminal = terminal["payload"]
    amount = settled(journal)
    require(amount == terminal["cost_nanos"], "terminal and durable usage disagree")
    store = ArtifactStore(journal.root / "artifacts")
    runner._validate_recorded_continuations(events, store)
    actions = [e["payload"]["result"] for e in events if e["event_type"] == "action_finished"]
    plans = [e["payload"] for e in events if e["event_type"] == working_plan.EVENT]
    turns = [e for e in events if e["event_type"] == "turn_started"]
    plan_views = []
    for turn in turns:
        p = turn["payload"]
        canonical = json.loads(store.read_bytes(Artifact.model_validate(p["context_artifact"])))
        inputs = runner._load_active_model_input(p, store)
        if frozen is not None:
            require(
                inputs[0]["content"] == frozen["system_prompts"][arm],
                "sample system prompt differs from its frozen arm",
            )
        active = reconstruct_state(inputs)
        require(active["public_task"] == canonical["public_task"], "public task delivery mismatch")
        require(("working_plan" in active) == (arm == "B"), "planning option delivery mismatch")
        if arm == "B":
            # Native results may own the receipt; actual latest plan/review must match exactly.
            expected = canonical["working_plan"]
            require(
                all(active["working_plan"][k] == expected[k] for k in ("plan", "review_request")),
                "planning state was not delivered",
            )
            plan_views.append(
                {
                    "turn_id": p["turn_id"],
                    "revision": (expected["plan"] or {}).get("revision", 0),
                    "review_requested": expected["review_request"]["requested"],
                }
            )
    usage = journal.provider_usage()
    normalized = DevCostLedger(CAP, pricing_for_model(MODEL))
    for row in usage:
        recompute = DevCostLedger(RUN_CAP, pricing_for_model(MODEL))
        require(
            recompute.settle(
                input_tokens=row["input_tokens"],
                cached_input_tokens=row["cached_input_tokens"],
                output_tokens=row["output_tokens"],
            )
            == row["cost_nanos"],
            "durable provider usage does not match frozen prices",
        )
        normalized.settle(
            input_tokens=row["input_tokens"],
            cached_input_tokens=0,
            output_tokens=row["output_tokens"],
        )
    first = next(
        (
            e
            for e in events
            if e["event_type"] == "action_finished"
            and e["payload"]["result"]["tool"] == "replace_text"
            and e["payload"]["result"]["status"] == "succeeded"
        ),
        None,
    )
    evaluator = terminal.get("evaluator") or {}
    submission = any(e["event_type"] == "submission_recorded" for e in events)
    unsafe = (
        terminal["terminal"]
        in {
            "COUNT_TIMEOUT_OR_UNKNOWN",
            "PROVIDER_TIMEOUT_OR_UNKNOWN",
            "PROVIDER_CONTINUATION_ERROR",
            "PREFLIGHT_FAILED",
            "EVALUATOR_ERROR",
            "TASK_FAILED",
        }
        or journal.unresolved_provider_call() is not None
        or journal.unresolved_input_count() is not None
        or any(
            a["output"].get("cleanup_failed") or a["output"].get("execution_uncertain")
            for a in actions
        )
        or evaluator.get("safety_state") in {"ERROR", "FAIL"}
        or evaluator.get("task_acceptance") == "ERROR"
    )
    return {
        "official": False,
        "arm": arm,
        "run_id": journal.run_id,
        "terminal": terminal["terminal"],
        "message": terminal.get("message"),
        "task_acceptance": evaluator.get("task_acceptance", "NOT_RUN"),
        "safety_state": evaluator.get("safety_state", "NOT_RUN"),
        "failure_class": evaluator.get("failure_class"),
        "submitted": submission,
        "call_counts": terminal["call_counts"],
        "accepted_mutations": terminal["accepted_mutations"],
        "cost_nanos": amount,
        "uncached_equivalent_cost_nanos": normalized.spent_nanos,
        "tokens": {
            k: sum(r.get(k, 0) for r in usage)
            for k in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
            )
        },
        "first_mutation_model_calls": (
            sum(e["event_type"] == "turn_decision_recorded" for e in events[: first["sequence"]])
            if first
            else None
        ),
        "action_counts": dict(Counter(a["tool"] for a in actions)),
        "zero_coverage_inspections": sum(
            a["tool"] in {"read_file", "search_files"}
            and a["output"].get("evidence_gain", {}).get("new_covered_line_count") == 0
            for a in actions
        ),
        "plan_status_counts": dict(Counter(p["receipt"]["status"] for p in plans)),
        "requested_review_decisions": sum(
            p["receipt"]["review_request"]["requested"] for p in plans
        ),
        "updated_after_review": sum(
            p["receipt"]["review_request"]["requested"]
            and p["receipt"]["status"] in {"created", "updated"}
            for p in plans
        ),
        "plan_delivery": plan_views,
        "public_action_sequence": [
            {
                "action_id": a["action_id"],
                "tool": a["tool"],
                "status": a["status"],
                "diff_hash": a["workspace_diff_hash"],
            }
            for a in actions
        ],
        "artifact_hashes": terminal.get("artifact_hashes", {}),
        "stop_cycle": unsafe,
        "journal_hash": sha256_bytes(journal.path.read_bytes()),
    }


def group_report(root, group):
    rows = []
    for label in group["order"]:
        path = root / "results" / f"{group['group_id']}-{label}.json"
        if path.exists():
            result = read(path)
            j = run_journal(root, group["group_id"], label)
            require(
                j is not None and result == audit_run(j, label[0], frozen=group["frozen"]),
                "trial receipt drift",
            )
            rows.append({"label": label, **result})
    attempted = {
        p["label"]
        for p in payloads(control(root), "trial_started")
        if p["group_id"] == group["group_id"]
    } | {r["label"] for r in rows}
    arms = {
        a: {
            "runs": sum(label[0] == a for label in attempted),
            "audited_results": sum(r["arm"] == a for r in rows),
            "acceptance_pass": sum(r["arm"] == a and r["task_acceptance"] == "PASS" for r in rows),
            "submitted": sum(r["arm"] == a and r["submitted"] for r in rows),
            "cost_nanos": sum(r["cost_nanos"] for r in rows if r["arm"] == a),
            "uncached_equivalent_cost_nanos": sum(
                r["uncached_equivalent_cost_nanos"] for r in rows if r["arm"] == a
            ),
        }
        for a in ("A", "B")
    }
    complete = len(rows) == len(group["order"])
    return {
        "official": False,
        "group_id": group["group_id"],
        "complete": complete,
        "arms": arms,
        "rows": rows,
        "unscored_labels": [
            label
            for label in group["order"]
            if label in attempted and label not in {r["label"] for r in rows}
        ],
        "cost_scope": "audited results; cycle spent additionally includes pending durable usage",
        "extension_eligible": (
            group["task"] == "pyfakefs"
            and complete
            and arms["B"]["acceptance_pass"] >= 2
            and arms["B"]["acceptance_pass"] > arms["A"]["acceptance_pass"]
            and not any(r["stop_cycle"] for r in rows)
        ),
    }


def execute_group(root, group_id):
    journal = control(root)
    with journal.execution_lock():
        manifest, group = load_cycle(root), load_group(root, group_id)
        if any(p["group_id"] == group_id for p in payloads(journal, "group_finished")):
            return group_report(root, group)  # Read-only; no runtime/provider/evaluator replay.
        require(
            not payloads(journal, "cycle_stopped") and not payloads(journal, "cycle_closed"),
            "cycle is stopped or closed",
        )
        try:
            require(freeze(manifest, group["task"]) == group["frozen"], "group contract changed")
            remaining = [
                label
                for label in group["order"]
                if not (root / "results" / f"{group_id}-{label}.json").exists()
            ]
            # Partial invocation spend is already in spent(); reserve only its unused cap.
            committed = sum(settled(run_journal(root, group_id, label)) for label in remaining)
            admit_group(manifest["cap_nanos"], spent(root) - committed, len(remaining))
            for label in group["order"]:
                path = root / "results" / f"{group_id}-{label}.json"
                j = run_journal(root, group_id, label)
                if path.exists():
                    require(
                        j is not None
                        and read(path) == audit_run(j, label[0], frozen=group["frozen"]),
                        "completed trial differs from durable run",
                    )
                    require(not read(path)["stop_cycle"], "previous trial stopped the cycle")
                    continue
                require(
                    freeze(manifest, group["task"]) == group["frozen"], "group contract changed"
                )
                if not any(
                    p["group_id"] == group_id and p["label"] == label
                    for p in payloads(journal, "trial_started")
                ):
                    journal.append("trial_started", {"group_id": group_id, "label": label})
                if j is None or j.terminal() is None:
                    req = DevRunRequest.model_validate(
                        {
                            **group["frozen"]["requests"][label[0]],
                            "state_root": str(slot_root(root, group_id, label)),
                            "resume_run_id": j.run_id if j else None,
                        }
                    )
                    # Exact-match native resume reconciles pending actions and unknown dispatch.
                    runner.run_dev(req)
                    j = run_journal(root, group_id, label)
                require(j is not None, "runner created no recoverable run journal")
                result = audit_run(j, label[0], frozen=group["frozen"])
                save(root, f"results/{group_id}-{label}.json", result)
                journal.append(
                    "trial_finished",
                    {"group_id": group_id, "label": label, "result_hash": sha256_json(result)},
                )
                print(
                    canonical_json(
                        {
                            "group_id": group_id,
                            "label": label,
                            **{
                                k: result[k]
                                for k in (
                                    "terminal",
                                    "task_acceptance",
                                    "cost_nanos",
                                    "call_counts",
                                    "stop_cycle",
                                )
                            },
                        }
                    ),
                    flush=True,
                )
                require(not result["stop_cycle"], "trial uncertainty/integrity failure stops cycle")
            report = group_report(root, group)
            save(root, f"groups/{group_id}-results.json", report)
            journal.append(
                "group_finished", {"group_id": group_id, "report_hash": sha256_json(report)}
            )
            return report
        except Exception as exc:
            journal.append(
                "cycle_stopped",
                {
                    "group_id": group_id,
                    "exception_type": type(exc).__name__,
                    "message": str(exc)[:500],
                },
            )
            raise


def status(root):
    manifest = load_cycle(root)
    journal = control(root)
    return {
        "official": False,
        "cap_nanos": manifest["cap_nanos"],
        "spent_nanos": spent(root),
        "stopped": payloads(journal, "cycle_stopped"),
        "closed": payloads(journal, "cycle_closed"),
        "groups": [
            group_report(root, load_group(root, p["group_id"]))
            for p in payloads(journal, "group_prepared")
        ],
    }


def close(root, reason):
    journal = control(root)
    with journal.execution_lock():
        load_cycle(root)
        if not payloads(journal, "cycle_closed"):
            journal.append("cycle_closed", {"reason": reason[:2000], "spent_nanos": spent(root)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "prepare", "run", "status", "close"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--provider", choices=("openai", "mock"), default="openai")
    parser.add_argument("--pricing-verified-on")
    parser.add_argument("--task", choices=tuple(TASKS), default="pyfakefs")
    parser.add_argument("--group")
    parser.add_argument("--hypothesis", default="")
    parser.add_argument("--axis", choices=AXES, default="initial")
    parser.add_argument("--public-evidence")
    parser.add_argument("--reason", default="No further justified planning change")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "init":
            result = initialize(
                root, pricing_verified_on=args.pricing_verified_on, provider=args.provider
            )
        elif args.command == "prepare":
            result = prepare_group(
                root,
                task=args.task,
                hypothesis=args.hypothesis,
                axis=args.axis,
                public_evidence=args.public_evidence,
            )
        elif args.command == "run":
            require(bool(args.group), "choose the exact prepared group")
            result = execute_group(root, args.group)
        elif args.command == "close":
            close(root, args.reason)
            result = status(root)
        else:
            result = status(root)
        print(canonical_json(result), flush=True)
    except (ContractError, RecoveryError) as exc:
        parser.exit(1, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
