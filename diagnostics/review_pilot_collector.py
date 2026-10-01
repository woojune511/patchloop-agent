"""Collect only an exact approved manifest; preparation never loads credentials."""
import argparse
import json
from decimal import Decimal
from pathlib import Path

from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from diagnostics.review_context_offline import ReviewStopped, load
from diagnostics.review_context_rehearsal import _rehearse_locked, admitted_probe
from diagnostics.review_pilot_manifest import IMPLEMENTATION, TASKS, build
from diagnostics.review_pilot_scoring import score
from patchloop.agent.model import create_openai_client
from patchloop.contracts import ModelConfig
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.cost import usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes


def validate(path, approved_hash, approved_cap):
    raw = path.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "approved manifest hash differs")
    plan = json.loads(raw)
    require(approved_cap.is_finite() and approved_cap > 0
            and usd_to_nanos(approved_cap) == plan["new_cap_nanos"], "approved cap differs")
    cases = {}
    for row in plan["rows"]:
        cases[row["task"]] = {"source": Source.from_record(row["source"]),
            "sequence": row["sequence"], "evaluation_path": Path(row["evaluation_path"])}
    expected = build(cases, {k: Path(v["path"]) for k, v in plan["operator_only_programs"].items()},
                     env_file=Path(plan["env_file"]), result_root=Path(plan["result_root"]))
    require(plan == expected, "approved controls or implementation changed")
    root = Path(plan["result_root"])
    disjoint(root, [repository_root(), path.parent,
                   *(case["source"].root for case in cases.values()),
                   *(case["evaluation_path"] for case in cases.values())])
    runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    return plan


def environment(row, env_file):
    source = Source.from_record(row["source"])
    loaded = load(source, row["sequence"], conan_materialization=True)
    deadline = ExecutionDeadline.from_remaining(120)
    require(env_file.is_file(), "credential file missing")  # Contents are not read here.
    runner._live_task_is_admitted(source.public_path.parent, loaded.package)
    runner._live_source_preflight(source.public_path.parent, loaded.package, deadline=deadline)
    env = loaded.envelope
    runner.load_source(Path(env.prepared_source_path), loaded.package.public.repository.url,
                       loaded.package.public.repository.base_commit,
                       expected_hash=env.prepared_source_hash, deadline=deadline)
    runner._live_sandbox_preflight(loaded.package, deadline=deadline)
    admitted_probe(loaded, deadline)
    evaluation = load_task_package(Path(row["evaluation_path"]))
    require(evaluation.task_content_hash == row["evaluation_content_hash"], "evaluation changed")
    runner._live_task_is_admitted(Path(row["evaluation_path"]), evaluation)
    runner._live_source_preflight(Path(row["evaluation_path"]), evaluation, deadline=deadline)
    runner._live_sandbox_preflight(evaluation, deadline=deadline)


def execute_row(row, plan, root, client):
    panel_root = root / "panel"
    panel = DevJournal(panel_root, "run_dev_reviewpanel")
    label = row["task"] + "-" + row["arm"]
    with panel.execution_lock():
        result = _rehearse_locked(Source.from_record(row["source"]), row["sequence"],
            root / label, row["arm"], client,
            reviewer_client=None if row["arm"] == "C" else client,
            panel_root=panel_root, execute_reviewer_probes=True, current_runtime_fork=True,
            real_sandboxes=True, live=True, env_file=Path(plan["env_file"]))
    return result


def _run_panel(plan, approved_hash, *, row_executor, preflight, client_factory, scorer,
               simulated_transport=False):
    root = Path(plan["result_root"])
    root.mkdir()  # Interrupted or completed invocations can never silently restart.
    journal = DevJournal(root, "run_dev_reviewpilot")
    rows = [{"task": r["task"], "arm": r["arm"], "status": "NOT_RUN"} for r in plan["rows"]]
    total, known, stop = 0, True, None
    with journal.execution_lock():
        journal.append("pilot_rehearsed" if simulated_transport else "pilot_authorized", {
            "manifest_hash": approved_hash, "plan": plan,
            "simulated_transport": simulated_transport})
        try:
            for task in TASKS:
                row = next(r for r in plan["rows"] if r["task"] == task)
                preflight(row, Path(plan["env_file"]))
                journal.append("environment_ready", {"task": task})
        except Exception as exc:
            stop = type(exc).__name__
        if stop is None:
            for i, row in enumerate(plan["rows"]):
                client = None
                label = row["task"] + "-" + row["arm"]
                try:
                    journal.append("row_started", {"row": label})
                    rows[i]["status"] = "STARTED"
                    client = client_factory(plan)
                    receipt = row_executor(row, plan, root, client)
                    require(receipt["billing_known"], "uncertain row billing")
                    cost = receipt["new_cost_nanos"]
                    require(type(cost) is int and 0 <= cost <= row["new_cap_nanos"],
                            "row cost exceeded allowance")
                    total += cost
                    require(total <= plan["new_cap_nanos"], "panel cap exceeded")
                    rows[i] = {**rows[i], "status": "EXECUTED", "receipt": receipt}
                    journal.append("row_settled", {"row": label, "new_cost_nanos": cost})
                    closing, client = client, None
                    closing.close()
                    if receipt["stop_remaining"]:
                        stop = receipt["result"]["terminal"]
                    else:
                        scoring = scorer(row, receipt, root / label,
                                         plan["operator_only_programs"], root / (label + "-score"))
                        rows[i]["scoring"] = scoring
                    journal.append("row_finished", rows[i])
                except Exception as exc:
                    stop = type(exc).__name__
                    # Known settlement survives scoring failure; earlier uncertainty does not.
                    known = rows[i]["status"] == "EXECUTED"
                    if not known:
                        rows[i]["status"] = "PARTIAL"
                    if isinstance(exc, ReviewStopped):
                        cost = exc.settled_cost_nanos
                        total += cost
                        known = exc.billing_known
                        stop = "review: " + exc.reason
                        rows[i]["partial_usage"] = {
                            "settled_cost_nanos": cost, "billing_known": known}
                    rows[i] = {**rows[i], "failure": stop}
                    journal.append("row_failed", rows[i])
                finally:
                    if client is not None:
                        try:
                            client.close()
                        except Exception:
                            stop = "client_cleanup_uncertain"
                if stop is not None:
                    break
        result = {"official": False, "rows": rows, "billing_known": known,
                  "recorded_new_cost_nanos": total, "new_cost_nanos": total if known else None,
                  "cap_nanos": plan["new_cap_nanos"], "stop_reason": stop,
                  "automatic_retry": False, "improvement": "NOT_ESTABLISHED"}
        if simulated_transport:
            result.update(simulated_transport=True, actual_provider_calls=0)
        journal.append("pilot_finished", result)
        (root / "result.json").write_text(canonical_json(result), encoding="utf-8")
    return result


def collect(path, approved_hash, approved_cap):
    plan = validate(path, approved_hash, approved_cap)

    def client_factory(plan):
        config = ModelConfig(provider="openai", model_id=plan["model"],
            reasoning_effort=plan["reasoning_effort"], max_output_tokens=plan["max_output_tokens"],
            reasoning_continuation="encrypted-v1", transport_max_retries=0)
        key = runner.load_exact_openai_api_key(Path(plan["env_file"]))
        return create_openai_client(config, api_key=key)

    return _run_panel(plan, approved_hash, row_executor=execute_row,
                      preflight=environment, client_factory=client_factory, scorer=score)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--approved-hash", required=True)
    parser.add_argument("--approved-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    print(canonical_json(collect(args.manifest, args.approved_hash, args.approved_cap_usd)))


if __name__ == "__main__":
    main()
