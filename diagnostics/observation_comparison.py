"""Prepare without provider calls; collect only with an exact funded manifest."""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_comparison import ContinuationLedger
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
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

RUBRIC = ".agent/observation-comparison.md"
ORDER = ("N1A", "N1B", "P1B", "P1A", "P2A", "P2B")
MODEL = "gpt-5.4-2026-03-05"


def normalized(request):
    value = copy.deepcopy(request)
    value.pop("timeout", None)
    view = json.loads(value["input"][-1]["content"])
    view["state"]["remaining_budget"]["active_wall_time_seconds"] = 0
    value["input"][-1]["content"] = canonical_json(view)
    return value


def controls(cases, env_file, result_root, row_cap_usd):
    require(set(cases) == {"N1", "P1", "P2"}, "exact three-case panel required")
    require(row_cap_usd.is_finite() and row_cap_usd > 0, "positive finite cap required")
    require(usd_to_nanos(row_cap_usd) > 0, "cap below accounting precision")
    rows = []
    for label in ORDER:
        case = cases[label[:2]]
        source = Source.from_record(case["source"])
        journal = DevJournal(source.root, source.run_id)
        for path, digest in (
            (journal.path, source.journal_hash),
            (journal.envelope_path, source.envelope_hash),
            (source.public_path, source.public_hash),
        ):
            require(sha256_bytes(path.read_bytes()) == digest, "source identity changed")
        old = journal.load_envelope()
        target = next(
            (
                e["payload"]["result"]
                for e in journal.events()
                if e["sequence"] < case["cut_sequence"]
                and e["event_type"] == "action_finished"
                and e["payload"]["result"]["action_id"] == case["target_action_id"]
            ),
            None,
        )
        require(
            target is not None
            and target["tool"] == "run_probe"
            and target["output"].get("status") == "failed",
            "target is not a failed probe",
        )
        require(old.split == "dev-train" and old.model == MODEL, "source model/split changed")
        require(
            sha256_bytes(str(env_file.resolve()).encode()) == old.credential_file_path_hash,
            "credential path changed",
        )
        disjoint(result_root.resolve(), (repository_root(), source.root, source.public_path.parent))
        rows.append(
            {
                "label": label,
                "arm": label[-1],
                "source": source.record(),
                "cut_sequence": case["cut_sequence"],
                "target_action_id": case["target_action_id"],
                "task": str(source.public_path),
                "new_cap_nanos": usd_to_nanos(row_cap_usd),
            }
        )
    return {
        "schema": "observation-comparison-v1",
        "official": False,
        "paid_execution_authorized": False,
        "rows": rows,
        "repeat": len(rows),
        "model": MODEL,
        "reasoning_effort": "xhigh",
        "max_output_tokens": 25000,
        "env_file": str(env_file.resolve()),
        "result_root": str(result_root.resolve()),
        "new_cap_nanos": len(rows) * usd_to_nanos(row_cap_usd),
        "runtime_hash": runner._runtime_hash(),
        "implementation_hash": exposure.implementation_hash(),
        "rubric_hash": sha256_bytes((repository_root() / RUBRIC).read_bytes()),
        "pricing": {k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()},
        "sdk_retries": 0,
        "automatic_resume": False,
    }


def clean_implementation():
    root = repository_root()
    runner._require_tracked_clean_paths(
        root,
        [
            RUBRIC,
            *sorted(p.relative_to(root).as_posix() for p in (root / "diagnostics").glob("*.py")),
        ],
    )


def check_environment(row, env_file):
    """Read-only admission; credential contents and provider construction are forbidden."""
    source = Source.from_record(row["source"])
    old = DevJournal(source.root, source.run_id).load_envelope()
    checks = {}
    try:
        clean_implementation()
        deadline = ExecutionDeadline.from_remaining(120)
        task_dir, package = runner._resolve_task_file(source.public_path)
        runner._live_task_is_admitted(task_dir, package)
        runner._live_source_preflight(task_dir, package, deadline=deadline)
        checks["task_runtime"] = "PASS"
        require(env_file.is_file(), "credential file missing")
        require(
            sha256_bytes(str(env_file.resolve()).encode()) == old.credential_file_path_hash,
            "credential path changed",
        )
        require(old.prepared_source_path is not None, "prepared source required")
        runner.load_source(
            Path(old.prepared_source_path),
            package.public.repository.url,
            package.public.repository.base_commit,
            expected_hash=old.prepared_source_hash,
            deadline=deadline,
        )
        deps = (
            runner.load_dependencies(
                Path(old.prepared_probe_dependencies_path), package.public, old.probe_dependencies
            )
            if old.prepared_probe_dependencies_path
            else None
        )
        if deps is not None:
            deps.verify(deadline=deadline)
        runner._live_sandbox_preflight(package, deadline=deadline)
        identity = runner.DockerProbeSandbox(dependencies=deps).preflight(deadline=deadline)
        require(
            identity
            == {"image_digest": old.probe_image_digest, "profile_hash": old.probe_profile_hash},
            "probe identity changed",
        )
        checks["source_images_dependencies"] = "PASS"
        return {"status": "READY", "checks": checks}
    except Exception as exc:
        return {
            "status": "PREFLIGHT_FAILED",
            "checks": checks,
            "error": f"{type(exc).__name__}: {exc}",
        }


def prepare(cases, env_file, result_root, row_cap_usd, output):
    plan = controls(cases, env_file, result_root, row_cap_usd)
    protected = [repository_root(), result_root.resolve()]
    for case in cases.values():
        source = Source.from_record(case["source"])
        protected.extend((source.root, source.public_path.parent))
    disjoint(output.resolve(), protected)
    require(not result_root.exists(), "result root already used")
    clean_implementation()
    output.mkdir()
    journal = DevJournal(output, "run_dev_observationpreparation")
    fingerprints, requests = {}, {}
    for row in plan["rows"]:
        label = row["label"]
        branch = exposure.fork(
            Source.from_record(row["source"]),
            row["cut_sequence"],
            output / label,
            row["arm"],
            synthetic_cap_usd=row_cap_usd,
        )
        client = ScriptedClient(
            [
                [
                    {
                        "name": "stop_task",
                        "action_id": "prepare_stop",
                        "arguments": {
                            "reason_code": "insufficient_public_evidence",
                            "summary": "Synthetic first-input preparation.",
                            "turn_decision": {
                                "mode": "stop",
                                "basis": "Synthetic preparation only.",
                                "evidence_goal": None,
                                "memory_update": None,
                                "plan_update": None,
                            },
                        },
                    }
                ]
            ]
        )
        receipt = exposure.rehearse(branch, client)
        require(
            len(client.counted) == len(client.created) == 1
            and receipt["result"]["terminal"] == "AGENT_STOPPED",
            "preview failed",
        )
        requests[label] = normalized(client.created[0])
        fingerprints[label] = sha256_json(requests[label])
        (output / f"{label}-first.json").write_text(
            canonical_json(requests[label]), encoding="utf-8"
        )
    for case in cases:
        require(
            requests[case + "A"] == exposure.project(requests[case + "B"], "A"),
            "pair differs beyond catalog and elapsed time",
        )
    plan["first_request_hashes"] = fingerprints
    plan["preparation_root"] = str(output.resolve())
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    preflight = {row["label"]: check_environment(row, env_file) for row in plan["rows"]}
    journal.append(
        "observation_comparison_prepared",
        {
            "manifest_hash": sha256_bytes(raw),
            "plan": plan,
            "preflight": preflight,
            "actual_provider_calls": 0,
        },
    )
    (output / "preflight.json").write_text(canonical_json(preflight), encoding="utf-8")
    return {
        "manifest": str(output / "manifest.json"),
        "manifest_hash": sha256_bytes(raw),
        "new_cap_nanos": plan["new_cap_nanos"],
        "preflight": preflight,
        "actual_provider_calls": 0,
        "paid_execution_authorized": False,
    }


def run_branch(branch, group, journal, store, label, first_hash):
    ledger = ContinuationLedger(branch, group, journal, label)
    counted, dispatched = [], []
    active = runner._run_one_active
    executing_commit = git_commit()

    def current_identity(**kwargs):
        return active(**{**kwargs, "harness_git_commit": executing_commit})

    class RecordedAdapter(OpenAIResponsesAdapter):
        def count_input_tokens_v2(self, payload, **kwargs):
            if not counted:
                require(
                    sha256_json(normalized(payload)) == first_hash,
                    "first input differs from approved preparation",
                )
            require(
                branch.arm == "B" or exposure.project(payload, "A") == payload,
                "catalog leaked into A input",
            )
            artifact = store.put_json(payload)
            journal.append(
                "actual_input_count_started",
                {"row": label, "artifact": artifact.model_dump(mode="json")},
            )
            counted.append(copy.deepcopy(payload))
            return super().count_input_tokens_v2(payload, **kwargs)

        def execute_request(self, payload, **kwargs):
            require(len(counted) == len(dispatched) + 1, "dispatch lacks immediate count")
            expected = copy.deepcopy(counted[-1])
            require(
                0 < payload["max_output_tokens"] <= expected["max_output_tokens"],
                "output ceiling grew after count",
            )
            expected["max_output_tokens"] = payload["max_output_tokens"]
            require(payload == expected, "count and dispatch input differ")
            artifact = store.put_json(payload)
            journal.append(
                "actual_dispatch_started",
                {"row": label, "artifact": artifact.model_dump(mode="json")},
            )
            dispatched.append(artifact.content_hash)
            return super().execute_request(payload, **kwargs)

    with (
        inherited_reads(branch),
        exposure.exposure(branch.arm),
        patch.object(runner, "OpenAIResponsesAdapter", RecordedAdapter),
        patch.object(runner, "_run_one_active", current_identity),
        branch.journal.execution_lock(),
    ):
        branch.journal.append(
            "executing_runtime_git_identity",
            {"harness_git_commit": executing_commit, "inherited_identity_is_historical": True},
        )
        result = runner._run_one_locked(
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
    known = runner._provider_usage_failure(branch.journal) is None
    return {
        "row": label,
        "status": "EXECUTED",
        "result": result.public,
        "billing_known": known,
        "new_cost_nanos": ledger.spent_nanos - branch.initial_spent_nanos if known else None,
        "input_counts": len(counted),
        "dispatches": len(dispatched),
        "stop_remaining": not known
        or result.public["terminal"] == "PREFLIGHT_FAILED"
        or (result.stop_remaining and result.public["terminal"] != "COST_CAP_REACHED"),
    }


def collect(manifest_path, approved_hash, approved_cap_usd):
    raw = manifest_path.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "approved manifest hash differs")
    plan = json.loads(raw)
    require(usd_to_nanos(approved_cap_usd) == plan["new_cap_nanos"], "approved cap differs")
    cases = {
        row["label"][:2]: {k: row[k] for k in ("source", "cut_sequence", "target_action_id")}
        for row in plan["rows"]
    }
    env_file, root = Path(plan["env_file"]), Path(plan["result_root"])
    expected = controls(cases, env_file, root, Decimal(plan["rows"][0]["new_cap_nanos"]) / 10**9)
    require(
        {k: v for k, v in plan.items() if k not in {"first_request_hashes", "preparation_root"}}
        == expected,
        "manifest controls changed",
    )
    disjoint(root, (Path(plan["preparation_root"]), manifest_path.parent))
    clean_implementation()
    root.mkdir()  # Single-use even after interruption or uncertain billing.
    journal, store = (
        DevJournal(root, "run_dev_observationcomparison"),
        ArtifactStore(root / "artifacts"),
    )
    group = DevCostLedger(approved_cap_usd, pricing_for_model(MODEL))
    rows = [{"row": label, "status": "NOT_RUN"} for label in ORDER]
    known, stop_reason = True, None
    with journal.execution_lock():
        journal.append("comparison_authorized", {"manifest_hash": approved_hash, "plan": plan})
        for i, row in enumerate(plan["rows"]):
            check = check_environment(row, env_file)
            journal.append("environment_checked", {"row": row["label"], **check})
            if check["status"] != "READY":
                stop_reason = "PREFLIGHT_FAILED"
                break
            branch = None
            try:
                branch = exposure._fork(
                    Source.from_record(row["source"]),
                    row["cut_sequence"],
                    root / row["label"],
                    row["arm"],
                    mode="funded-observation",
                    env_file=env_file,
                    new_cap_usd=Decimal(row["new_cap_nanos"]) / 10**9,
                )
                result = run_branch(
                    branch,
                    group,
                    journal,
                    store,
                    row["label"],
                    plan["first_request_hashes"][row["label"]],
                )
            except Exception as exc:
                result = {
                    "row": row["label"],
                    "status": "COLLECTOR_FAILED",
                    "error_type": type(exc).__name__,
                    "stop_remaining": True,
                    "billing_known": branch is None
                    or runner._provider_usage_failure(branch.journal) is None,
                }
            rows[i] = result
            known = known and result["billing_known"]
            journal.append("row_finished", result)
            if result["stop_remaining"]:
                stop_reason = result.get("result", {}).get("terminal", result["status"])
                break
        receipt = {
            "official": False,
            "manifest_hash": approved_hash,
            "rows": rows,
            "billing_known": known,
            "new_cost_nanos": group.spent_nanos if known else None,
            "recorded_new_cost_nanos": group.spent_nanos,
            "new_cap_nanos": group.cap_nanos,
            "stop_reason": stop_reason,
            "efficacy_claim": "NOT_ESTABLISHED",
        }
        journal.append("comparison_finished", receipt)
        (root / "result.json").write_text(canonical_json(receipt), encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for key in ("cases", "env-file", "result-root", "output"):
        prep.add_argument("--" + key, type=Path, required=True)
    prep.add_argument("--row-cap-usd", type=Decimal, required=True)
    run = sub.add_parser("collect")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--approved-manifest-hash", required=True)
    run.add_argument("--approved-new-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    result = (
        prepare(
            json.loads(args.cases.read_bytes()),
            args.env_file,
            args.result_root,
            args.row_cap_usd,
            args.output,
        )
        if args.command == "prepare"
        else collect(args.manifest, args.approved_manifest_hash, args.approved_new_cap_usd)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
