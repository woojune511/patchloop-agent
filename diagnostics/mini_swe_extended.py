"""Requested five-task follow-up after the closed mini dev20 call-limit exits."""
from __future__ import annotations

import argparse
import json
import time
from decimal import Decimal
from pathlib import Path

from diagnostics import mini_swe_dev20 as baseline
from diagnostics import portfolio_dev20
from diagnostics.mini_swe_runtime import CountedModel, PublicContainer, command, load_upstream
from diagnostics.positive_verification_panel import require, save
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_json

BASE_PREP = Path("C:/pt/mini20prep05")
BASE_AUDIT = Path("C:/pt/mini20rerun01/audit.json")
BASE_AUDIT_HASH = "sha256:08635eb1fac9e0d2294ad5a5f087f3e49913b68be3be700b6e6725c39c16aff0"
BASE_PACKET_HASH = "sha256:680a2c6377a7267afc76354cce9d00df8c90234355c432aa60c77a1a14658b7a"
INDICES = (8, 13, 16, 17, 18)
PRIOR_NANOS = 3217100400
ROW_CAP = Decimal("3")
MAX_CALLS = 250
MAX_ACTIONS = 1000
SOLVER_SECONDS = 3600
MAX_INPUT_TOKENS = 250000
JOURNAL = "run_dev_miniextended"
CONTRACT = ".agent/mini-swe-extended.md"
LIMIT_TERMINALS = {"LimitsExceeded", "CallLimit", "CostOrContextLimit", "ActionLimit",
                   "TimeExceeded", "SolverDeadline"}


def previous_evidence():
    require(baseline.file_hash(BASE_AUDIT) == BASE_AUDIT_HASH, "previous audit drift")
    audit = json.loads(BASE_AUDIT.read_bytes())
    require(audit["aggregate"]["billing_known"], "previous billing uncertain")
    require(audit["aggregate"]["cumulative_recorded_cost_nanos"] == PRIOR_NANOS,
            "previous cost differs")
    require(tuple(r["index"] for r in audit["rows"] if not r["submitted"]) == INDICES,
            "follow-up roster differs")
    for path, digest in audit["input_hashes"].items():
        require(baseline.file_hash(path) == digest, "previous evidence drift")
    packet = json.loads((BASE_PREP / "manifest.json").read_bytes())
    require(sha256_json(packet) == BASE_PACKET_HASH, "original packet drift")
    return packet


def bindings():
    return baseline.bindings(BASE_PREP) | {
        CONTRACT: baseline.file_hash(repository_root() / CONTRACT),
    }


def prepare(root, live):
    require(not root.exists() and not live.exists(), "fresh external roots required")
    repo = repository_root().resolve()
    require(not root.is_relative_to(repo) and not live.is_relative_to(repo)
            and not root.is_relative_to(live) and not live.is_relative_to(root),
            "separate external preparation/live roots required")
    previous = previous_evidence()
    load_exact_openai_api_key(Path(previous["credential_file"]))
    load_upstream(BASE_PREP)
    config = json.loads((BASE_PREP / "config.json").read_bytes())
    config["agent"].update(step_limit=MAX_CALLS, cost_limit=float(ROW_CAP),
                           wall_time_limit_seconds=SOLVER_SECONDS)
    root.mkdir(parents=True)
    save(root, "config.json", config)
    packet = previous | {
        "schema_version": "mini-swe-extended-v1",
        "rows": [r for r in previous["rows"] if r["index"] in INDICES],
        "live_root": str(live), "row_cap_usd": str(ROW_CAP),
        "prior_cost_nanos": PRIOR_NANOS,
        "prior_cost_receipt": {"path": str(BASE_AUDIT), "hash": BASE_AUDIT_HASH},
        "new_run_cap_usd": str(ROW_CAP * len(INDICES)),
        "max_cumulative_spend_usd": str(Decimal(PRIOR_NANOS) / 10**9 + ROW_CAP * len(INDICES)),
        "max_model_calls": MAX_CALLS, "max_shell_actions": MAX_ACTIONS,
        "max_input_tokens": MAX_INPUT_TOKENS, "solver_seconds": SOLVER_SECONDS,
        "container_lifetime_seconds": SOLVER_SECONDS + 330,
        "harness_git_commit": git_commit(), "runtime_hash": runtime_content_hash(),
        "bindings": bindings(), "config_hash": baseline.file_hash(root / "config.json"),
        "prior_packet_hash": BASE_PACKET_HASH,
        "comparison": "fresh expanded-budget follow-up; original 20 outcomes remain unchanged",
        "fallback": "on a known limit, grade the tracked working diff as operator-collected",
        "authorization": "REQUESTED_BY_USER_WITH_EXISTING_USD24_AND_ISOLATED_BASH_SCOPE",
    }
    save(root, "manifest.json", packet)
    digest = sha256_json(packet)
    DevJournal(root, JOURNAL).append("external_panel_prepared",
                                    {"packet_hash": digest, "provider_calls": 0})
    return {"packet_hash": digest, "rows": len(INDICES), "provider_calls": 0}


def validate(root, digest):
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest, "packet hash mismatch")
    require(packet["bindings"] == bindings(), "implementation/dependency drift")
    require(packet["config_hash"] == baseline.file_hash(root / "config.json"), "config drift")
    require(packet["runtime_hash"] == runtime_content_hash(), "core runtime drift")
    require(packet["native_identity"] == portfolio_dev20.native_identity(), "native drift")
    require(packet["pricing"] == portfolio_dev20.price(), "pricing drift")
    previous = previous_evidence()
    require(packet["rows"] == [r for r in previous["rows"] if r["index"] in INDICES],
            "task selection or public/native input drift")
    for key in ("model", "reasoning_effort", "credential_file", "repeat", "workers",
                "revision", "max_output_tokens", "total_cap_usd"):
        require(packet[key] == previous[key], key + " drift")
    require(PRIOR_NANOS + int(ROW_CAP * 10**9) * len(INDICES) <= 24 * 10**9,
            "cumulative budget exceeds original USD 24")
    require(packet["row_cap_usd"] == str(ROW_CAP)
            and packet["new_run_cap_usd"] == str(ROW_CAP * len(INDICES))
            and packet["prior_cost_nanos"] == PRIOR_NANOS
            and packet["max_model_calls"] == MAX_CALLS
            and packet["max_shell_actions"] == MAX_ACTIONS
            and packet["max_input_tokens"] == MAX_INPUT_TOKENS
            and packet["solver_seconds"] == SOLVER_SECONDS, "resource contract drift")
    for row in packet["rows"]:
        require(load_task_package(Path(row["task"]).parent).task_content_hash
                == row["task_content_hash"], "task package drift")
        for key in ("source_archive", "task_text", "native_row"):
            require(baseline.file_hash(row[key]) == row[key + "_hash"], key + " drift")
        image = json.loads(command(["docker", "image", "inspect", row["image"]]).stdout)[0]
        require(image["Id"] == row["image_id"], "local image drift")
    return packet


def preflight(root, digest):
    packet = validate(root, digest)
    require(not (root / "preflight.json").exists(), "preflight evidence is immutable")
    rows = []
    for row in packet["rows"]:
        env = PublicContainer(row, root / "canaries" / str(row["index"]),
                              ExecutionDeadline.from_remaining(120))
        try:
            script = (
                "test ! -e /root/eval.sh && test ! -e /eval.sh && "
                "test ! -e /patch.diff && test ! -e /.patchloop-hidden && "
                "test ! -e /testbed/.patchloop-hidden && "
                'test $(git rev-list --count HEAD) = 1 && test -z "$(git remote)" && '
                f"python -c 'import {row['public_module']}; import pytest; "
                'print("PUBLIC_ENVIRONMENT_READY")\''
            )
            require(b"PUBLIC_ENVIRONMENT_READY" in env.operator_command(script).stdout,
                    "public canary failed")
            inspection = json.loads(command(["docker", "inspect", env.name]).stdout)[0]
            host = inspection["HostConfig"]
            require(not inspection["Mounts"] and host["NetworkMode"] == "none"
                    and host["ReadonlyRootfs"] and inspection["Image"] == row["image_id"],
                    "sandbox or image drift")
            rows.append({"index": row["index"], "public_environment": "PASS",
                         "inspection_hash": ArtifactStore(root / "artifacts")
                         .put_json(inspection).content_hash})
        finally:
            env.cleanup()
    receipt = {"packet_hash": digest, "rows": rows, "provider_calls": 0, "cost_usd": "0"}
    save(root, "preflight.json", receipt)
    DevJournal(root, JOURNAL).append("external_preflight_passed", {"receipt": sha256_json(receipt)})
    return receipt


def collect_working_diff(env, folder):
    """Bounded read-only capture after a settled limit; never another solver action."""
    result = command(["docker", "exec", "-w", "/testbed", env.name, "git",
                      "--no-pager", "diff", "--no-ext-diff", "--no-textconv",
                      "--binary", "HEAD", "--"], timeout=20)
    patch = folder / "operator-collected.patch"
    with patch.open("xb") as stream:
        stream.write(result.stdout)
    env.journal.append("external_operator_diff_collected",
                       {"patch_hash": baseline.file_hash(patch), "bytes": len(result.stdout),
                        "origin": "operator_final_diff", "agent_submission": False})
    return patch


def execute_row(client, config, row, folder, Agent, *, cap_usd=ROW_CAP,
                max_calls=MAX_CALLS, max_actions=MAX_ACTIONS, solver_seconds=SOLVER_SECONDS):
    start = time.monotonic()
    deadline = ExecutionDeadline.from_remaining(solver_seconds)
    model = CountedModel(client, config["model"], folder, deadline,
                         cap_usd=cap_usd, max_calls=max_calls, max_input_tokens=MAX_INPUT_TOKENS)
    env = None
    result = {"index": row["index"], "instance_id": row["instance_id"],
              "native": "NOT_RUN", "scope": "NOT_RUN", "registered": "NOT_RUN",
              "submitted": False, "candidate_available": False, "candidate_origin": "NONE",
              "stop_panel": False}
    try:
        env = PublicContainer(row, folder, deadline, max_actions=max_actions,
                              lifetime_seconds=solver_seconds + 330)
        agent = Agent(model, env, **config["agent"])
        answer = {}
        try:
            answer = agent.run(Path(row["task_text"]).read_text(encoding="utf-8"))
            result["terminal"] = answer.get("exit_status")
        except ExecutionDeadlineExceeded:
            result["terminal"] = "SolverDeadline"
        finally:
            save(folder, "trajectory.json", agent.serialize())
        require(not model.uncertain, "provider accounting uncertain")
        patch = None
        if result["terminal"] == "Submitted" and answer.get("submission", "").strip():
            patch = folder / "submitted.patch"
            with patch.open("xb") as stream:
                stream.write(answer["submission"].encode("utf-8"))
            result.update(submitted=True, candidate_origin="agent_submission")
        elif result["terminal"] in LIMIT_TERMINALS:
            patch = collect_working_diff(env, folder)
            result["candidate_origin"] = "operator_final_diff"
        elif result["terminal"] not in ("Submitted", "RepeatedFormatError"):
            result["stop_panel"] = True
        if patch is not None:
            result.update(patch_hash=baseline.file_hash(patch),
                          candidate_available=bool(patch.read_bytes().strip()))
        env.cleanup()  # Destroy the solver before any private grading.
        if result["candidate_available"]:
            result.update(baseline.assess_patch(folder, row, patch))
    except Exception as exc:
        result.setdefault("terminal", "OperationalStop")
        result.update(error_type=type(exc).__name__, stop_panel=True)
    finally:
        try:
            if env is not None:
                env.cleanup()
                result["environment_cleanup"] = "CONFIRMED"
        except Exception as exc:
            result.update(cleanup_error=type(exc).__name__, stop_panel=True)
        result.update(cost_nanos=model.ledger.spent_nanos, billing_known=not model.uncertain,
                      model_calls=model.calls, shell_actions=env.actions if env else 0,
                      elapsed_seconds=time.monotonic() - start)
        result["stop_panel"] |= model.uncertain
        save(folder, "result.json", result)
    return result


def run(root, digest):
    from openai import OpenAI

    packet = validate(root, digest)
    approval = json.loads((root / "authorization.json").read_bytes())
    require(approval.get("packet_hash") == digest
            and approval.get("live_authorized") is True
            and approval.get("isolated_bash_exception") is True,
            "human request and existing authorization must be bound to this packet")
    receipt = json.loads((root / "preflight.json").read_bytes())
    require(receipt["packet_hash"] == digest
            and tuple(r["index"] for r in receipt["rows"]) == INDICES,
            "preflight does not match packet")
    live = Path(packet["live_root"])
    live.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(live, JOURNAL)
    Agent = load_upstream(BASE_PREP)
    config = json.loads((root / "config.json").read_bytes())
    rows = []
    with (
        journal.execution_lock(),
        OpenAI(api_key=load_exact_openai_api_key(packet["credential_file"]), max_retries=0,
               base_url="https://api.openai.com/v1", timeout=180) as client,
    ):
        for row in packet["rows"]:
            result = execute_row(client, config, row, live / str(row["index"]), Agent)
            rows.append(result)
            journal.append("external_row_finished", result)
            print(canonical_json(result), flush=True)
            if result["stop_panel"]:
                break
    completed = {r["index"] for r in rows}
    rows.extend({"index": r["index"], "instance_id": r["instance_id"], "native": "NOT_RUN",
                 "terminal": "NOT_STARTED", "cost_nanos": None, "submitted": False}
                for r in packet["rows"] if r["index"] not in completed)
    spent = sum(r.get("cost_nanos") or 0 for r in rows)
    report = {"official": False, "claim_eligible": False, "packet_hash": digest,
              "rows": rows, "planned": len(INDICES),
              "resolved": sum(r["native"] == "PASS" for r in rows),
              "agent_submissions": sum(r["submitted"] for r in rows),
              "recorded_cost_nanos": spent, "prior_cost_nanos": PRIOR_NANOS,
              "cumulative_recorded_cost_nanos": PRIOR_NANOS + spent,
              "billing_known": all(r.get("billing_known", True) for r in rows),
              "automatic_followup": False,
              "original_dev20_outcomes": "UNCHANGED"}
    save(live, "summary.json", report)
    journal.append("external_panel_finished", {"summary_hash": sha256_json(report)})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "preflight", "run"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--live-root", type=Path)
    parser.add_argument("--packet-hash")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "prepare":
        require(args.live_root is not None, "--live-root required")
        result = prepare(root, args.live_root.resolve())
    else:
        require(args.packet_hash is not None, "--packet-hash required")
        result = globals()[args.command](root, args.packet_hash)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
