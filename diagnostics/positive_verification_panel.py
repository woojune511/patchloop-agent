"""Bounded fresh-repair A/B: positive expected behavior in existing brief planning."""
from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from patchloop import prepared_probe_dependencies as deps
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, working_plan
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError
from patchloop.prepared_source import admission_hash, load_source
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODEL = "gpt-5.4-2026-03-05"
ROW_CAP = Decimal("3")
CAP = Decimal("24")
TASKS = {"1733": 18, "1625": 17}
ORDER = (("1733", "A", 1), ("1733", "B", 1), ("1625", "B", 1), ("1625", "A", 1),
         ("1733", "B", 2), ("1733", "A", 2), ("1625", "A", 2), ("1625", "B", 2))
LIVE = Path("C:/pt/pv1live01")
NOTE = ".agent/positive-verification-experiment.md"
REPLACED = """The plan is model-authored, unverified working data, not an instruction from the
harness or proof that a behavior is correct. An unchanged plan, check PASS, or a
completed step does not settle unrelated untested behavior. Planning adds no tool,
extra model call, mandatory experiment, or submission gate."""
GUIDANCE = """For a behavior check, derive the expected observation from the public requirement,
documented contract or observed source before using the candidate's output. Check
the required positive result, not only disappearance of the original symptom:
another incorrect output can also lack that symptom. When the public issue gives
an expected example, compare its relevant complete output, including required
content and layout. Normalize only differences the contract permits. For multiple
valid outputs, assert the stated property instead of inventing one exact answer.
Use actual observed results to decide whether to repair further or submit. Missing
requirements and failed setup remain uncertainties; a normal process exit alone
does not verify behavior. Keep any untested assumption in the existing public plan
or action fields. The plan and expectations remain model-authored and unverified.
This adds no tool, extra model call, mandatory experiment or submission gate."""
SETTLED = {"EVALUATOR_PASS", "EVALUATOR_FAIL", "COST_CAP_REACHED", "LIMIT_REACHED",
           "AGENT_STOPPED", "INCOMPLETE_RESPONSE", "PROTOCOL_VIOLATION"}


def require(condition, message):
    if not condition:
        raise ContractError(message)


@contextmanager
def arm_instructions(arm: str):
    require(arm in {"A", "B"}, "unknown arm")
    original = working_plan.instructions
    require(original("brief-v1").count(REPLACED) == 1, "baseline planning text changed")

    def selected(policy="brief-v1"):
        text = original(policy)
        return text.replace(REPLACED, GUIDANCE, 1) if policy == "brief-v1" else text

    # Existing planning_contract.instructions_hash binds the actual A/B text in
    # the envelope and model identity. All count and generation paths use it.
    if arm == "A":
        yield
    else:
        with patch.object(working_plan, "instructions", selected):
            yield


def request(case: str, state_root: Path, *, mock=False) -> DevRunRequest:
    index = TASKS[case]
    root = repository_root()
    return DevRunRequest(
        provider="mock" if mock else "openai", model="mock-dev" if mock else MODEL,
        task=root / ("tasks/smoke/csv-quoted-newline/public.yaml" if mock else
                     f"tasks/dev-train/swebench-lite-dev-sqlfluff-sqlfluff-{case}/public.yaml"),
        state_root=state_root, env_file=None if mock else root / ".env",
        max_cost_usd=None if mock else ROW_CAP, repeat=1, reasoning_effort="xhigh",
        max_output_tokens=25000, context_policy="segmented-v1",
        segment_boundary_policy="result-or-size-v1", planning_policy="brief-v1",
        enable_probes=True, probe_policy="none", repair_recheck=True,
        repair_inspection_policy="protected-v1", completion_cost_policy="per-call-v1",
        prepared_source=None if mock else Path(f"C:/pt/ld20p01/s/{index}/prepared-source.json"),
        prepared_probe_dependencies=None if mock else Path(
            f"C:/pt/analyses/lite-probe-support-20261002-v1/dependencies-{index}/"
            "prepared-probe-dependencies.json"),
    )


def bindings() -> dict:
    root = repository_root()
    paths = [Path(__file__).resolve(), root / NOTE,
             root / "diagnostics/output_predicate_controls.py"]
    return {p.relative_to(root).as_posix(): sha256_bytes(p.read_bytes()) for p in paths}


def save(root: Path, name: str, value):
    ArtifactStore(root).write_text_immutable(root / name, canonical_json(value) + "\n")


def freeze(root: Path, calibration: Path) -> str:
    require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
            "fresh external panel root required")
    calibration_raw = calibration.read_bytes()
    require(json.loads(calibration_raw)["calibration_passed"] is True, "calibration failed")
    canaries_path = calibration.parent.parent / "canaries.json"
    canaries_raw = canaries_path.read_bytes()
    canaries = json.loads(canaries_raw)
    require([row["case"] for row in canaries] == list(TASKS), "canary roster changed")
    require(all(row["result"]["exit_code"] == 0 and not row["result"]["timed_out"]
                and not row["result"]["cleanup_failed"] and not row["result"]["truncated"]
                for row in canaries), "public environment canary failed")
    assessment_root = calibration.parent.parent
    assessment = {str(assessment_root / name): sha256_bytes((assessment_root / name).read_bytes())
                  for name in ("public_assessment.py", "public-programs.json", "public-base.json")}
    base_results = json.loads((assessment_root / "public-base.json").read_bytes())
    require([row["case"] for row in base_results] == list(TASKS)
            and all(row["assessment"]["status"] == "FAIL" for row in base_results),
            "public assessment must reproduce each base defect")
    pricing = pricing_for_model(MODEL)
    cases = {}
    for case in TASKS:
        req = request(case, LIVE / "unused")
        directory, package = runner._resolve_task_file(req.task)
        runner._live_task_is_admitted(directory, package)
        runner._live_source_preflight(directory, package)
        model_hashes = {}
        for arm in ("A", "B"):
            with arm_instructions(arm):
                model_hashes[arm] = runner._model_hash(req, pricing)
        cases[case] = {"request": req.model_dump(mode="json"),
                       "task_hash": package.task_content_hash,
                       "public_hash": package.public_spec_hash,
                       "model_hashes": model_hashes, "external": {
                           str(p): sha256_bytes(p.read_bytes())
                           for p in (req.prepared_source, req.prepared_probe_dependencies)}}
    packet = {"schema": "positive-verification-panel-v1", "official": False,
              "claim_eligible": False, "cases": cases, "order": ORDER,
              "cap_usd": str(CAP), "row_cap_usd": str(ROW_CAP), "model": MODEL,
              "credential": str((repository_root() / ".env").resolve()), "live_root": str(LIVE),
              "runtime_hash": runtime_content_hash(), "implementation": bindings(),
              "head": git_commit(), "guidance": GUIDANCE, "replaced": REPLACED,
              "calibration": {"path": str(calibration), "hash": sha256_bytes(calibration_raw)},
              "canaries": {"path": str(canaries_path), "hash": sha256_bytes(canaries_raw)},
              "operator_assessment": assessment,
              "pricing": {"input": str(pricing.input_per_million_usd),
                          "cached_input": str(pricing.cached_input_per_million_usd),
                          "output": str(pricing.output_per_million_usd)},
              "approval": "PENDING_EXACT_HUMAN_SCOPE", "start": "fresh base for every row"}
    root.mkdir(parents=True)
    save(root, "packet.json", packet)
    digest = sha256_bytes((root / "packet.json").read_bytes())
    DevJournal(root, "run_dev_positivepanel").append("panel_prepared", {"packet_hash": digest})
    return digest


def validate(root: Path, expected_hash: str) -> dict:
    raw = (root / "packet.json").read_bytes()
    require(sha256_bytes(raw) == expected_hash, "packet changed")
    packet = json.loads(raw)
    require(packet["head"] == git_commit() and packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation"] == bindings(), "frozen implementation changed")
    require(packet["order"] == [list(row) for row in ORDER] and packet["model"] == MODEL
            and packet["cap_usd"] == str(CAP) and packet["row_cap_usd"] == str(ROW_CAP)
            and packet["guidance"] == GUIDANCE and packet["replaced"] == REPLACED
            and packet["live_root"] == str(LIVE) and set(packet["cases"]) == set(TASKS),
            "frozen scope changed")
    calibration = packet["calibration"]
    require(sha256_bytes(Path(calibration["path"]).read_bytes()) == calibration["hash"],
            "calibration changed")
    canaries = packet["canaries"]
    require(sha256_bytes(Path(canaries["path"]).read_bytes()) == canaries["hash"],
            "canaries changed")
    for path, digest in packet["operator_assessment"].items():
        require(sha256_bytes(Path(path).read_bytes()) == digest, "public assessment changed")
    pricing = pricing_for_model(MODEL)
    require(packet["pricing"] == {"input": str(pricing.input_per_million_usd),
                                  "cached_input": str(pricing.cached_input_per_million_usd),
                                  "output": str(pricing.output_per_million_usd)}, "pricing changed")
    for case, frozen in packet["cases"].items():
        req = request(case, LIVE / "unused")
        require(req.model_dump(mode="json") == frozen["request"], "request changed")
        directory, package = runner._resolve_task_file(req.task)
        require(package.task_content_hash == frozen["task_hash"], "task changed")
        runner._live_source_preflight(directory, package)
        for path, digest in frozen["external"].items():
            require(sha256_bytes(Path(path).read_bytes()) == digest, "prepared descriptor changed")
        for arm in ("A", "B"):
            with arm_instructions(arm):
                require(runner._model_hash(req, pricing) == frozen["model_hashes"][arm],
                        "model instruction identity changed")
    return packet


def preflight(root: Path, expected_hash: str) -> dict:
    packet = validate(root, expected_hash)
    require(not LIVE.exists(), "live root exists; no restart")
    require(bool(load_exact_openai_api_key(Path(packet["credential"]))), "credential unavailable")
    canary_rows = json.loads(Path(packet["canaries"]["path"]).read_bytes())
    canaries = {row["case"]: row for row in canary_rows}
    receipts = {}
    for case in TASKS:
        req = request(case, LIVE / "unused")
        _, package = runner._resolve_task_file(req.task)
        evaluator = runner._live_sandbox_preflight(package)
        load_source(req.prepared_source, package.public.repository.url,
                    package.public.repository.base_commit,
                    expected_hash=admission_hash(req.prepared_source))
        dependencies = deps.load_dependencies(req.prepared_probe_dependencies, package.public,
                                              deps.admit(req.prepared_probe_dependencies))
        dependencies.verify()
        receipts[case] = {"evaluator_image": evaluator.image_identity(),
                          "probe": DockerProbeSandbox(dependencies=dependencies).preflight()}
        require(receipts[case]["probe"] == canaries[case]["profile"]
                and receipts[case]["evaluator_image"] == canaries[case]["evaluator_image"]
                and admission_hash(req.prepared_source) == canaries[case]["source_manifest_hash"],
                "tested public environment changed")
    save(root, "preflight.json", receipts)
    DevJournal(root, "run_dev_positivepanel").append("preflight_passed", {
        "packet_hash": expected_hash, "receipt_hash": sha256_json(receipts), "provider_calls": 0})
    return receipts


def settled(result: dict, state: Path) -> bool:
    if result.get("completed_repetitions") != 1 or len(result.get("runs", [])) != 1:
        return False
    row = result["runs"][0]
    child = DevJournal(state, row["run_id"])
    evaluation = row.get("evaluator") or {}
    return (row["terminal"] in SETTLED and row.get("billing_state") != "UNKNOWN"
            and child.unresolved_provider_call() is None and child.unresolved_input_count() is None
            and evaluation.get("task_acceptance") != "ERROR"
            and evaluation.get("safety_state") != "ERROR")


def run(root: Path, expected_hash: str) -> dict:
    validate(root, expected_hash)
    approval_path = root / "authorization.json"
    require(approval_path.is_file(), "exact task/model/credential/repeats/cap approval required")
    approval = json.loads(approval_path.read_bytes())
    require(approval.get("approved") is True and bool(approval.get("human_message"))
            and approval.get("packet_hash") == expected_hash, "approval does not bind this packet")
    journal = DevJournal(root, "run_dev_positivepanel")
    with journal.execution_lock():
        events = journal.events()
        require(not any(e["event_type"] == "panel_started" for e in events), "no restart or resume")
        receipts = json.loads((root / "preflight.json").read_bytes())
        require(any(e["event_type"] == "preflight_passed"
                    and e["payload"]["receipt_hash"] == sha256_json(receipts)
                    and e["payload"]["packet_hash"] == expected_hash for e in events),
                "frozen preflight required")
        runner._require_tracked_clean_paths(repository_root(), list(bindings()))
        require(not LIVE.exists(), "live root exists; no replacement")
        LIVE.mkdir(parents=True)
        journal.append("panel_started", {"packet_hash": expected_hash,
                                         "authorization_hash": sha256_json(approval)})
        spent, rows = 0, []
        try:
            for case, arm, repetition in ORDER:
                validate(root, expected_hash)
                require(spent + usd_to_nanos(ROW_CAP) <= usd_to_nanos(CAP), "panel cap exhausted")
                label = f"{case}{arm}{repetition}"
                req = request(case, LIVE / label)
                require(not req.state_root.exists(), "row exists; no retry")
                journal.append("row_started", {"label": label,
                                               "request": req.model_dump(mode="json")})
                started = monotonic()
                print(canonical_json({"starting": label, "cap_usd": str(ROW_CAP)}), flush=True)
                with arm_instructions(arm):
                    result = runner.run_dev(req)
                cost = result["cost_nanos"]
                spent += cost
                known = settled(result, req.state_root)
                within_cap = 0 <= cost <= usd_to_nanos(ROW_CAP) and spent <= usd_to_nanos(CAP)
                row = {"label": label, "case": case, "arm": arm, "repetition": repetition,
                       "result": result, "settled": known, "within_cap": within_cap,
                       "elapsed_seconds": round(monotonic() - started, 3)}
                rows.append(row)
                journal.append("row_finished", row)
                print(canonical_json({"finished": label, "cost_nanos": cost,
                                      "settled": known, "completed": len(rows)}), flush=True)
                if not known or not within_cap:
                    break
        except BaseException as error:
            journal.append("panel_interrupted", {"error_type": type(error).__name__,
                                                 "completed": len(rows), "resume_allowed": False})
            raise
        summary = {"rows": rows, "planned": len(ORDER), "completed": len(rows),
                   "not_run": [f"{c}{a}{n}" for c, a, n in ORDER[len(rows):]],
                   "recorded_cost_nanos": spent,
                   "total_cost_known": all(r["settled"] for r in rows),
                   "official": False, "claim_eligible": False, "resume_allowed": False,
                   "allocation": "CLOSED"}
        save(root, "result.json", summary)
        journal.append("panel_closed", {"result_hash": sha256_json(summary)})
        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "preflight", "run"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--packet-hash")
    args = parser.parse_args()
    if args.action == "freeze":
        print(freeze(args.root, args.calibration))
    elif args.action == "preflight":
        print(canonical_json(preflight(args.root, args.packet_hash)))
    else:
        run(args.root, args.packet_hash)
