"""Fresh, sequential boundary-example A/B panel using the unchanged dev-head loop."""
from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from patchloop import prepared_probe_dependencies as deps
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, working_plan
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.prepared_source import admission_hash, load_source
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODEL = "gpt-5.4-2026-03-05"
RUN_CAP = Decimal("2")
CAP = Decimal("48")
TASKS = {
    "P": "pydantic-ai-synthetic-tool-reasoning",
    "H": "hf-hub-xet-endpoint-propagation-v5",
    "F": "fromager-recursive-orphan-removal",
    "L": "loguru-invalid-format-feedback-v3",
    "D": "pdm-ignore-active-venv-resolution-v2",
    "G": "pgmpy-stable-skeleton-order",
}
PREPARED = {
    "P": ("pydantic-ai-registration-20260917-v1/source/prepared-source.json",
          "prepared-probe-dependencies-20260918-v1/dependencies-metadata/"
          "prepared-probe-dependencies.json"),
    "H": ("fixed-config-two-task-20260916-v1/sources/H/prepared-source.json",
          "hf-probe-dependencies-20260926-v1/prepared-probe-dependencies.json"),
    "F": ("fromager-registration-20260917-v1/source/prepared-source.json",
          "mini-xhigh-fixed-harness-panel-20260921-v1/dependencies/F/"
          "prepared-probe-dependencies.json"),
}
TREATMENT = """Before choosing a repair, select a concrete case where the public task
requires changed behavior and a nearby case where existing behavior must be preserved.
Derive their expected outcomes independently from the public requirement, not from
the proposed patch. Trace the source values and conditions that distinguish the cases,
including where those values are created or transformed. If this distinction remains
uncertain, use a small allowed public check or probe that could falsify the proposed
condition. Use the observed result to choose or revise the repair. Record the cases,
distinguishing condition, evidence and unresolved uncertainty briefly in the existing
public plan or action fields. A plausible explanation or a passing unrelated check
does not establish that the two cases are distinguished. Do not invent a boundary
unsupported by the task, add a separate ceremony, or repeat already decisive evidence.
Work within the existing tools, submission rules and total resource budget."""
ORDER = tuple((case, arm, n) for n in (1, 2) for i, case in enumerate(TASKS)
              for arm in (("A", "B") if (i + n) % 2 else ("B", "A")))


def require(ok, message):
    if not ok:
        raise ContractError(message)


@contextmanager
def arm_instructions(arm):
    require(arm in {"A", "B"}, "unknown arm")
    original = working_plan.instructions

    def selected(policy="brief-v1"):
        text = original(policy)
        return text + "\n\n" + TREATMENT if arm == "B" and policy == "brief-v1" else text

    # The existing planning contract hashes these actual instructions into model identity.
    # A keeps the ordinary function. The context is restored even after failures.
    if arm == "A":
        yield
    else:
        with patch.object(working_plan, "instructions", selected):
            yield


def request(case, state_root, *, mock=False):
    root = repository_root()
    prepared = PREPARED.get(case)
    return DevRunRequest(
        provider="mock" if mock else "openai", model="mock-dev" if mock else MODEL,
        task=root / ("tasks/smoke/csv-quoted-newline/public.yaml" if mock else
                     f"tasks/dev-train/{TASKS[case]}/public.yaml"),
        state_root=state_root, env_file=None if mock else root / ".env",
        max_cost_usd=None if mock else RUN_CAP, reasoning_effort="xhigh",
        context_policy="segmented-v1", planning_policy="brief-v1",
        enable_probes=True, repair_recheck=True,
        prepared_source=(Path("C:/pt/analyses/boundarypair-sources-20260928-v1")
                         / case / "prepared-source.json" if not mock else None),
        prepared_probe_dependencies=(Path("C:/pt/analyses") / prepared[1]
                                     if prepared and not mock else None),
    )


def bindings():
    return {str(p): sha256_bytes(p.read_bytes()) for p in
            (Path(__file__).resolve(), repository_root() / ".agent/boundary-pair-panel.md")}


def save(root, name, value):
    ArtifactStore(root).write_text_immutable(root / name, canonical_json(value) + "\n")


def freeze(root):
    require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
            "fresh external root required")
    pricing = pricing_for_model(MODEL)
    require((pricing.input_per_million_usd, pricing.cached_input_per_million_usd,
             pricing.output_per_million_usd) == (Decimal("2.50"), Decimal("0.25"), Decimal("15")),
            "price differs from official reviewed rates")
    cases = {}
    for case in TASKS:
        req = request(case, root / "unused")
        directory, package = runner._resolve_task_file(req.task)
        runner._live_task_is_admitted(directory, package)
        runner._live_source_preflight(directory, package)
        external = {str(p): sha256_bytes(p.read_bytes()) for p in
                    (req.prepared_source, req.prepared_probe_dependencies) if p}
        cases[case] = {"task_hash": package.task_content_hash,
                       "public_hash": package.public_spec_hash, "external": external,
                       "request": req.model_dump(mode="json"), "model_hashes": {}}
        for arm in ("A", "B"):
            with arm_instructions(arm):
                cases[case]["model_hashes"][arm] = runner._model_hash(req, pricing)
    packet = {"schema": "boundary-pair-panel-v1", "official": False,
              "cases": cases, "order": ORDER, "cap_usd": str(CAP),
              "run_cap_usd": str(RUN_CAP), "runtime_hash": runtime_content_hash(),
              "implementation": bindings(), "treatment": TREATMENT,
              "start": "fresh base; no prior agent state",
              "pricing_source": "https://developers.openai.com/api/docs/models/gpt-5.4",
              "pricing_verified_on": "2026-09-28"}
    root.mkdir(parents=True)
    save(root, "packet.json", packet)
    digest = sha256_bytes((root / "packet.json").read_bytes())
    DevJournal(root, "run_dev_boundarypanel").append("panel_prepared", {"packet_hash": digest})
    return digest


def validate(root, expected):
    raw = (root / "packet.json").read_bytes()
    require(sha256_bytes(raw) == expected, "packet changed")
    p = json.loads(raw)
    require(p["implementation"] == bindings() and p["runtime_hash"] == runtime_content_hash()
            and p["order"] == [list(x) for x in ORDER] and p["treatment"] == TREATMENT
            and p["cap_usd"] == str(CAP), "frozen implementation changed")
    for case, data in p["cases"].items():
        req = request(case, Path(data["request"]["state_root"]))
        require(req.model_dump(mode="json") == data["request"], "request changed")
        directory, package = runner._resolve_task_file(req.task)
        require(package.task_content_hash == data["task_hash"], "task changed")
        runner._live_source_preflight(directory, package)
        for path, digest in data["external"].items():
            require(sha256_bytes(Path(path).read_bytes()) == digest, "prepared descriptor changed")
    return p


def preflight(root, expected):
    p = validate(root, expected)
    receipts = {}
    for case in TASKS:
        req = request(case, root / "unused")
        _, package = runner._resolve_task_file(req.task)
        sandbox = runner._live_sandbox_preflight(package)
        if req.prepared_source:
            load_source(req.prepared_source, package.public.repository.url,
                        package.public.repository.base_commit,
                        expected_hash=admission_hash(req.prepared_source))
        dependency = (deps.load_dependencies(req.prepared_probe_dependencies, package.public,
                                            deps.admit(req.prepared_probe_dependencies))
                      if req.prepared_probe_dependencies else None)
        if dependency:
            dependency.verify()
        probe = DockerProbeSandbox(dependencies=dependency)
        receipts[case] = {"evaluator_image": sandbox.image_identity(),
                          "probe": probe.preflight(),
                          "probe_dependencies": "prepared" if dependency else "stdlib-only",
                          "task_hash": p["cases"][case]["task_hash"]}
    save(root, "preflight.json", receipts)
    DevJournal(root, "run_dev_boundarypanel").append("preflight_passed", {
        "receipt_hash": sha256_json(receipts), "provider_calls": 0})
    return receipts


def run(root, expected):
    packet = validate(root, expected)
    control = DevJournal(root, "run_dev_boundarypanel")
    with control.execution_lock():
        events = control.events()
        require(any(e["event_type"] == "preflight_passed" for e in events), "preflight required")
        require(not any(e["event_type"] == "panel_started" for e in events),
                "no restart, resume or replacement runs")
        runner._require_tracked_clean_paths(repository_root(), [
            "diagnostics/boundary_pair_panel.py", ".agent/boundary-pair-panel.md"])
        control.append("panel_started", {"packet_hash": expected, "cap_usd": str(CAP)})
        spent, results = 0, []
        try:
            for case, arm, n in ORDER:
                require(spent + int(RUN_CAP * 10**9) <= int(CAP * 10**9), "panel cap exhausted")
                label = f"{case}{arm}{n}"
                state = root / "state" / label
                require(not state.exists(), "sample root already exists")
                req = request(case, state)
                directory, package = runner._resolve_task_file(req.task)
                pricing = pricing_for_model(MODEL)
                ledger = DevCostLedger(RUN_CAP, pricing)
                control.append("sample_started", {"label": label, "case": case,
                                                   "arm": arm, "repetition": n})
                with arm_instructions(arm):
                    model_hash = runner._model_hash(req, pricing)
                    require(model_hash == packet["cases"][case]["model_hashes"][arm],
                            "arm model identity changed")
                    one = runner._run_one(request=req, task_dir=directory, package=package,
                                          state_root=state, pricing=pricing, cost_ledger=ledger,
                                          runtime_hash=packet["runtime_hash"],
                                          model_hash=model_hash)
                spent += ledger.spent_nanos
                row = {"label": label, "case": case, "arm": arm, "repetition": n,
                       "result": one.public, "stop_remaining": one.stop_remaining}
                results.append(row)
                control.append("sample_finished", row)
                print(canonical_json({"completed": len(results), "label": label,
                                      "terminal": one.public["terminal"],
                                      "cost_nanos": spent}), flush=True)
                if one.stop_remaining:
                    break
        except BaseException as exc:
            control.append("panel_interrupted", {"error_type": type(exc).__name__,
                                                  "resume_allowed": False})
            raise
        known = all(r["result"]["terminal"] != "PROVIDER_TIMEOUT_OR_UNKNOWN"
                    and r["result"].get("billing_state") != "UNKNOWN" for r in results)
        summary = {"results": results, "cost_nanos": spent, "total_cost_known": known,
                   "planned": 24,
                   "completed": len(results), "official": False, "resume_allowed": False,
                   "unused_allowance_closed_nanos": int(CAP * 10**9) - spent}
        save(root, "result.json", summary)
        control.append("panel_closed", {"result_hash": sha256_json(summary)})
        return summary


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=["freeze", "preflight", "run"])
    cli.add_argument("--root", type=Path, required=True)
    cli.add_argument("--packet-hash")
    args = cli.parse_args()
    if args.action == "freeze":
        print(freeze(args.root))
    elif args.action == "preflight":
        print(canonical_json(preflight(args.root, args.packet_hash)))
    else:
        run(args.root, args.packet_hash)
