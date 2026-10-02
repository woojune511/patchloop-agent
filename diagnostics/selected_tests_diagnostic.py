"""Two seeded, uncued public-test diagnostics; preparation never calls a provider."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import candidate_review_repair as seeded
from patchloop import prepared_probe_dependencies as deps
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevRunRequest, PublicTurnDecision, RequestedTool
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.environment import load_exact_openai_api_key
from patchloop.prepared_source import admission_hash
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

require = seeded.require
MODEL = "gpt-5.4-2026-03-05"
ROW_CAP, CAP = Decimal("3"), Decimal("6")
TASK = "swebench-lite-dev-sqlfluff-sqlfluff-1625"
LIVE = Path("C:/pt/stlive01")
CALIBRATION = Path("C:/pt/stcal02")
NOTE = ".agent/selected-tests-diagnostic.md"
TARGET = "test/cli/commands_test.py::test__cli__command_directed"
SEEDS = {
    "A1": (
        "run_dev_31b82ad97f904d2f",
        "sha256:a6093a3d40dff12b8f9e9307eb8d6d32ea221845af7c26268c7c25a254af1e25",
    ),
    "B1": (
        "run_dev_ae26a17d5f29413c",
        "sha256:9d36d34b3d6400666818b298267aa53baa39ecd5c93231c89786bf2d0ef54908",
    ),
}
PROGRAMS = Path("C:/pt/analyses/positive-verification-20261003-v1/public-programs.json")
SETTLED = {
    "EVALUATOR_PASS",
    "EVALUATOR_FAIL",
    "COST_CAP_REACHED",
    "LIMIT_REACHED",
    "AGENT_STOPPED",
    "INCOMPLETE_RESPONSE",
    "PROTOCOL_VIOLATION",
}


def save(root: Path, name: str, value):
    ArtifactStore(root).write_text_immutable(root / name, canonical_json(value) + "\n")


def request(state: Path) -> DevRunRequest:
    return DevRunRequest(
        provider="openai",
        model=MODEL,
        task=repository_root() / "tasks/dev-train" / TASK / "public.yaml",
        state_root=state,
        env_file=repository_root() / ".env",
        max_cost_usd=ROW_CAP,
        repeat=1,
        reasoning_effort="xhigh",
        max_output_tokens=25000,
        context_policy="segmented-v1",
        segment_boundary_policy="result-or-size-v1",
        planning_policy="brief-v1",
        enable_probes=True,
        probe_policy="none",
        repair_recheck=True,
        repair_inspection_policy="protected-v1",
        completion_cost_policy="per-call-v1",
        limits=DevLimits(),
        prepared_source=Path("C:/pt/ld20p01/s/17/prepared-source.json"),
        prepared_probe_dependencies=Path(
            "C:/pt/analyses/lite-probe-support-20261002-v1/"
            "dependencies-17/prepared-probe-dependencies.json"
        ),
    )


def bindings() -> dict:
    paths = [Path(__file__).resolve(), repository_root() / NOTE]
    paths += [
        repository_root() / f"diagnostics/{name}.py"
        for name in (
            "candidate_review_repair",
            "change_review",
            "completion_status",
            "independent_candidate",
            "paired_observation",
        )
    ]
    return {
        p.relative_to(repository_root()).as_posix(): sha256_bytes(p.read_bytes()) for p in paths
    }


def environment():
    req = request(LIVE / "unused")
    directory, package = runner._resolve_task_file(req.task)
    runner._live_task_is_admitted(directory, package)
    runner._live_source_preflight(directory, package)
    sandbox = runner._live_sandbox_preflight(package)  # Existing image only.
    dependencies = deps.load_dependencies(
        req.prepared_probe_dependencies, package.public, deps.admit(req.prepared_probe_dependencies)
    )
    dependencies.verify()
    probe = DockerProbeSandbox(dependencies=dependencies)
    profile = probe.preflight()
    return package, sandbox, probe, profile


def classify_examples(result: dict, expected: dict) -> str:
    if any(
        result.get(k) for k in ("timed_out", "truncated", "deadline_exhausted", "cleanup_failed")
    ):
        return "ERROR"
    if result.get("exit_code") != 0:
        return "ERROR"
    try:
        observed = json.loads(result["stdout"])
    except (ValueError, KeyError):
        return "ERROR"
    if (
        not isinstance(observed, dict)
        or set(observed) != {"violations"}
        or not isinstance(observed["violations"], list)
        or len(observed["violations"]) != 2
        or not all(isinstance(v, list) for v in observed["violations"])
    ):
        return "ERROR"
    return "PASS" if observed == expected else "FAIL"


def assess(root, workspace, expected_hash, package, sandbox, probe, spec):
    """Operator-only public checks, after calibration or after the solver has stopped."""
    require(not root.exists(), "assessment exists; no rerun")
    journal = DevJournal(root, "run_dev_publicassessment")
    store = ArtifactStore(root / "artifacts")
    before = WorkspaceManager.diff_summary(workspace)
    require(before.patch_hash == expected_hash and not before.untracked_files, "candidate changed")
    journal.append(
        "assessment_started",
        {"patch_hash": expected_hash, "target": TARGET, "program_hash": spec["program_hash"]},
    )
    started = monotonic()
    gateway = DevToolGateway(
        workspace=workspace,
        public_task=package.public,
        sandbox=sandbox,
        journal=journal,
        limits=DevLimits(),
        deadline=ExecutionDeadline.from_remaining(180),
    )
    selected = gateway.execute(
        RequestedTool(
            name="run_tests",
            action_id="operator-cli",
            arguments={"suite_id": "public-pytest", "targets": [TARGET]},
            turn_decision=PublicTurnDecision(mode="verify", basis="Check public CLI behavior."),
        )
    )
    test = selected.output
    require(
        selected.status == "succeeded"
        and test.get("test_status") in {"PASS", "FAIL"}
        and not any(
            test.get(k) for k in ("timed_out", "truncated", "deadline_exhausted", "cleanup_failed")
        ),
        "public CLI execution uncertain; stop",
    )
    result = probe.run_probe(
        workspace,
        "Do both public TSQL examples produce no violations?",
        spec["program"],
        deadline=ExecutionDeadline.from_remaining(120),
        execution_identity={"run_id": journal.run_id, "action_id": sha256_text(str(root))},
    )
    examples = classify_examples(result, spec["oracle"])
    journal.append(
        "examples_finished",
        {"receipt": store.put_json(result).model_dump(mode="json"), "status": examples},
    )
    require(examples != "ERROR", "public example execution uncertain; stop")
    after = WorkspaceManager.diff_summary(workspace)
    require(
        after.patch_hash == expected_hash and not after.untracked_files, "assessment mutated code"
    )
    summary = {
        "patch_hash": expected_hash,
        "cli": test["test_status"],
        "examples": examples,
        "elapsed_seconds": round(monotonic() - started, 3),
        "provider_calls": 0,
        "required_check_credit": False,
        "delivered_to_solver": False,
        "cli_receipt": store.put_json(selected.model_dump(mode="json")).model_dump(mode="json"),
    }
    save(root, "result.json", summary)
    journal.append("assessment_completed", {"result_hash": sha256_json(summary)})
    return summary


def prepare(root: Path):
    require(
        not root.exists() and not root.resolve().is_relative_to(repository_root()),
        "fresh external preparation root required",
    )
    require(not CALIBRATION.exists() and not LIVE.exists(), "workspace root already exists")
    package, sandbox, probe, profile = environment()
    spec = json.loads(PROGRAMS.read_bytes())["1625"]
    require(
        spec["issue_hash"] == sha256_text(package.public.issue.description.replace("\r", ""))
        and spec["program_hash"]
        == sha256_text(spec["program"])
        == "sha256:3183b754e203ddc234758c4fbbed0d3ff06405ceed49d5cdb927de3253c2f719"
        and spec["oracle"] == {"violations": [[], []]},
        "public assessment identity changed",
    )
    root.mkdir(parents=True)
    journal = DevJournal(root, "run_dev_testdiagnostic")
    journal.append("preparation_started", {"implementation": bindings(), "provider_calls": 0})
    save(root, "public-example.json", spec)
    req = request(LIVE / "unused")
    manager = WorkspaceManager(
        repository_root() / "fixtures/repositories",
        CALIBRATION,
        prepared_source=req.prepared_source,
        prepared_source_hash=admission_hash(req.prepared_source),
    )
    outcomes = {}
    for label in ("base", *SEEDS):
        workspace = manager.create(
            label,
            package.public.repository.url,
            package.public.repository.base_commit,
            deadline=ExecutionDeadline.from_remaining(120),
        )
        digest = sha256_text("")
        if label != "base":
            source_run, digest = SEEDS[label]
            source = Path(f"C:/pt/pv1live01/1625{label}/workspaces/{source_run}/repo")
            seed = WorkspaceManager.diff_summary(source)
            require(seed.patch_hash == digest and not seed.untracked_files, "source seed changed")
            patch_file = root / f"{label}.patch"
            ArtifactStore(root).write_text_immutable(patch_file, seed.patch)
            WorkspaceManager.apply_patch(workspace, patch_file)
        outcomes[label] = assess(
            root / f"calibration-{label}", workspace, digest, package, sandbox, probe, spec
        )
        require(
            (outcomes[label]["cli"], outcomes[label]["examples"])
            == {
                "base": ("PASS", "FAIL"),
                "A1": ("FAIL", "PASS"),
                "B1": ("PASS", "PASS"),
            }[label],
            "calibration disagrees; stop without live execution",
        )
        print(canonical_json({"calibrated": label, **outcomes[label]}), flush=True)
    receipt = {
        "rows": outcomes,
        "image": sandbox.image_identity(),
        "probe_profile": profile,
        "runtime_hash": runtime_content_hash(),
        "task_hash": package.task_content_hash,
        "source_hash": admission_hash(req.prepared_source),
        "provider_calls": 0,
        "new_hidden_evaluations": 0,
        "implementation": bindings(),
    }
    save(root, "calibration.json", receipt)
    journal.append("calibration_passed", {"receipt_hash": sha256_json(receipt)})


def identity(root: Path) -> dict:
    req = request(LIVE / "unused")
    directory, package = runner._resolve_task_file(req.task)
    runner._live_task_is_admitted(directory, package)
    runner._live_source_preflight(directory, package)
    calibration = json.loads((root / "calibration.json").read_bytes())
    require(calibration["implementation"] == bindings(), "calibrated driver changed")
    require(
        calibration["runtime_hash"] == runtime_content_hash()
        and calibration["task_hash"] == package.task_content_hash
        and calibration["source_hash"] == admission_hash(req.prepared_source),
        "calibrated runtime, task or source changed",
    )
    for label, (_, digest) in SEEDS.items():
        require(sha256_bytes((root / f"{label}.patch").read_bytes()) == digest, "seed changed")
    pricing = pricing_for_model(MODEL)
    external = [
        req.prepared_source,
        req.prepared_probe_dependencies,
        root / "calibration.json",
        root / "public-example.json",
        *(root / f"{label}.patch" for label in SEEDS),
    ]
    return {
        "schema": "selected-tests-diagnostic-v1",
        "official": False,
        "claim_eligible": False,
        "head": git_commit(),
        "runtime_hash": runtime_content_hash(),
        "implementation": bindings(),
        "task_hash": package.task_content_hash,
        "public_hash": package.public_spec_hash,
        "request": req.model_dump(mode="json"),
        "model_hash": runner._model_hash(req, pricing),
        "order": list(SEEDS),
        "seeds": {k: list(v) for k, v in SEEDS.items()},
        "cap_usd": str(CAP),
        "row_cap_usd": str(ROW_CAP),
        "live_root": str(LIVE),
        "external": {str(p): sha256_bytes(p.read_bytes()) for p in external},
        "pricing": {
            "input": str(pricing.input_per_million_usd),
            "cached_input": str(pricing.cached_input_per_million_usd),
            "output": str(pricing.output_per_million_usd),
        },
        "approval": "PENDING_EXACT_HUMAN_SCOPE",
        "resume_allowed": False,
    }


def freeze(root: Path):
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    packet = identity(root)
    save(root, "packet.json", packet)
    digest = sha256_bytes((root / "packet.json").read_bytes())
    DevJournal(root, "run_dev_testdiagnostic").append("packet_frozen", {"packet_hash": digest})
    return digest


def validate(root: Path, digest: str):
    raw = (root / "packet.json").read_bytes()
    require(sha256_bytes(raw) == digest, "packet changed")
    require(json.loads(raw) == identity(root), "frozen conditions changed")


def dispatch(req, root, label, digest, base_commit):
    source_run, seed_hash = SEEDS[label]
    return seeded.run_seeded(
        req,
        seed_patch=(root / f"{label}.patch").read_text(encoding="utf-8"),
        seed_hash=seed_hash,
        base_commit=base_commit,
        source_code=[],
        review=None,
        experiment_hash=digest,
        source_run_id=source_run,
        branch=label,
    )


def settled(result, state):
    if result.get("completed_repetitions") != 1 or len(result.get("runs", [])) != 1:
        return False
    row = result["runs"][0]
    journal = DevJournal(state, row["run_id"])
    evaluation = row.get("evaluator") or {}
    return (
        row["terminal"] in SETTLED
        # Normal terminal records omit billing_state; uncertainty alone emits UNKNOWN.
        and row.get("billing_state") != "UNKNOWN"
        and journal.unresolved_provider_call() is None
        and journal.unresolved_input_count() is None
        and evaluation.get("task_acceptance") != "ERROR"
        and evaluation.get("safety_state") != "ERROR"
    )


def run(root: Path, digest: str):
    validate(root, digest)
    authorization = root / "authorization.json"
    require(authorization.is_file(), "fresh exact two-run approval required")
    approval = json.loads(authorization.read_bytes())
    require(
        approval.get("approved") is True
        and bool(approval.get("human_message"))
        and approval.get("packet_hash") == digest,
        "approval does not bind this packet",
    )
    journal = DevJournal(root, "run_dev_testdiagnostic")
    with journal.execution_lock():
        require(
            not any(e["event_type"] == "diagnostic_started" for e in journal.events())
            and not LIVE.exists(),
            "no restart or resume",
        )
        require(
            bool(load_exact_openai_api_key(request(LIVE / "unused").env_file)),
            "credential unavailable",
        )
        package, sandbox, probe, profile = environment()
        calibration = json.loads((root / "calibration.json").read_bytes())
        require(
            calibration["image"] == sandbox.image_identity()
            and calibration["probe_profile"] == profile,
            "calibrated environment changed",
        )
        spec = json.loads((root / "public-example.json").read_bytes())
        journal.append(
            "diagnostic_started",
            {"packet_hash": digest, "authorization_hash": sha256_json(approval)},
        )
        LIVE.mkdir(parents=True)
        rows, spent = [], 0
        try:
            for label in SEEDS:
                validate(root, digest)
                require(spent + usd_to_nanos(ROW_CAP) <= usd_to_nanos(CAP), "cap exhausted")
                req = request(LIVE / label)
                journal.append(
                    "row_started", {"label": label, "request": req.model_dump(mode="json")}
                )
                started = monotonic()
                result = dispatch(req, root, label, digest, package.public.repository.base_commit)
                cost = result["cost_nanos"]
                spent += cost
                known = settled(result, req.state_root)
                row = {
                    "label": label,
                    "result": result,
                    "settled": known,
                    "solver_seconds": round(monotonic() - started, 3),
                    "assessment": "NOT_RUN",
                }
                rows.append(row)
                journal.append("solver_finished", row)
                if not known or not 0 <= cost <= usd_to_nanos(ROW_CAP):
                    break
                candidate = result["runs"][0]
                submitted = candidate.get("artifact_hashes", {}).get("submitted_patch")
                if submitted:
                    workspace = req.state_root / "workspaces" / candidate["run_id"] / "repo"
                    row["assessment"] = assess(
                        root / f"final-{label}", workspace, submitted, package, sandbox, probe, spec
                    )
                journal.append("row_completed", row)
                print(canonical_json({"finished": label, "cost_nanos": cost}), flush=True)
        except BaseException as error:
            journal.append(
                "diagnostic_interrupted",
                {
                    "error_type": type(error).__name__,
                    "allocation": "CLOSED",
                    "resume_allowed": False,
                },
            )
            raise
        summary = {
            "rows": rows,
            "not_run": list(SEEDS)[len(rows) :],
            "recorded_cost_nanos": spent,
            "total_cost_known": all(r["settled"] for r in rows),
            "allocation": "CLOSED",
            "official": False,
            "claim_eligible": False,
            "resume_allowed": False,
        }
        save(root, "result.json", summary)
        journal.append("diagnostic_closed", {"result_hash": sha256_json(summary)})
        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "freeze", "run"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-hash")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.root)
    elif args.action == "freeze":
        print(freeze(args.root))
    else:
        run(args.root, args.packet_hash)
