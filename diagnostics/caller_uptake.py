"""Frozen fresh-solve caller A/B packet. Preparation never authorizes paid work."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from diagnostics import portfolio_dev20, probe_recheck_panel
from diagnostics.positive_verification_panel import require, save
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, segments, working_plan
from patchloop.dev.contracts import DevLimits, DevRunRequest
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.working_notes import OpenQuestion
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import sha256_bytes, sha256_json

MODEL = "gpt-5.4-mini-2026-03-17"
SOURCE = Path("C:/pt/ld20p01/s/13/prepared-source.json")
TASK = "tasks/dev-train/current-dev20/13/public.yaml"
NOTE = ".agent/plans/caller-uptake-comparison.md"
ROW_CAP, ARM_CAP, CAP = Decimal("0.88"), Decimal("5.28"), Decimal("10.56")
ORDER = tuple(f"{arm}-r{rep}-t13" for rep in range(1, 7)
              for arm in ("AB" if rep % 2 else "BA"))
COMMON = ("isort==5.13.2", "lazy-object-proxy==1.12.0", "mccabe==0.6.1",
          "platformdirs==4.4.0", "setuptools==80.9.0", "toml==0.10.2",
          "typing-extensions==4.16.0", "wrapt==1.13.3")
JOURNAL = "run_dev_calleruptake"


def request(dependencies, live, label):
    require(label in ORDER, "row outside frozen order")
    return DevRunRequest(
        provider="openai", task=repository_root() / TASK, model=MODEL,
        reasoning_effort="xhigh", max_output_tokens=25000, env_file=repository_root() / ".env",
        max_cost_usd=ROW_CAP, repeat=1, state_root=live / label, prepared_source=SOURCE,
        prepared_probe_dependencies=dependencies / label[0] / "prepared-probe-dependencies.json",
        enable_probes=True, probe_policy="none", probe_recheck="none", repair_recheck=True,
        repair_inspection_policy="protected-v1", agent_policy="current", planning_policy="brief-v1",
        context_policy="segmented-v1", retained_source_chars=24000,
        segment_boundary_policy="result-or-size-v1", completion_cost_policy="per-call-v1",
        limits=DevLimits(), evaluation_reserve_seconds=330)


def invariants():
    from patchloop.dev.model import DEV_SYSTEM_PROMPT

    require(OpenQuestion.model_json_schema()["properties"]["evidence"]["maxItems"] == 2,
            "reference cap changed")
    require((segments.MAX_INPUT_TOKENS, segments.MAX_REQUEST_BYTES,
             segments.MAX_ENCRYPTED_ITEM_BYTES) == (60000, 1048576, 262144), "context caps changed")
    require(len(DEV_SYSTEM_PROMPT) == 8000
            and len(DEV_SYSTEM_PROMPT) + 2 + len(working_plan.INSTRUCTIONS) == 10809,
            "prompt budget changed")
    require(DevLimits().model_dump() == {
        "max_model_calls": 40, "max_tool_actions": 100, "max_accepted_mutations": 4,
        "wall_time_seconds": 1800, "max_protocol_recoveries": 1, "max_parallel_reads": 4,
        "max_consecutive_inspection_turns": 24, "max_failed_mutation_repair_turns": 3},
        "limits changed")
    require(ROW_CAP * 6 == ARM_CAP and ARM_CAP * 2 == CAP, "allocation changed")
    return {"segment": segments.contract(), "references": 2, "retained_source_chars": 24000,
            "limits": DevLimits().model_dump(), "evaluation_reserve_seconds": 330,
            "postrun_host_seconds": 600, "native_test_seconds": 300, "workers": 1}


def bindings():
    names = [NOTE, "diagnostics/caller_uptake.py", "diagnostics/caller_uptake_prepare.py",
        "diagnostics/caller_uptake_grading.py", "diagnostics/caller_uptake_execution.py",
        "diagnostics/parallel_dev_batch.py", "diagnostics/portfolio_dev20.py",
        "diagnostics/swebench_lite_native.py", "diagnostics/probe_recheck_panel.py",
        "diagnostics/positive_verification_panel.py", "diagnostics/legacy_probe_metadata.py",
        "tests/test_caller_uptake.py", "tests/test_prepared_probe_dependencies.py"]
    return {name: sha256_bytes((repository_root() / name).read_bytes()) for name in names}


def file_ref(path):
    return {"path": str(path.resolve()), "hash": sha256_bytes(path.read_bytes())}


def read_ref(ref):
    raw = Path(ref["path"]).read_bytes()
    require(sha256_bytes(raw) == ref["hash"], "bound file changed: " + ref["path"])
    return raw


def native_input():
    entry = next(e for e in portfolio_dev20.baseline()[0]["rows"] if e["index"] == 13)
    return {"instance_id": entry["instance_id"], "rows": file_ref(Path(entry["native_row"]))}


def environments(dependencies, live):
    records = {}
    for arm in "AB":
        req = request(dependencies, live, f"{arm}-r1-t13")
        package, _, _, identity = probe_recheck_panel.environment(req)
        runner._live_source_preflight(req.task.parent, package)
        records[arm] = {"task_hash": package.task_content_hash,
            "public_hash": package.public_spec_hash, "task_id": package.public.task_id,
            "identity": identity, "source": file_ref(SOURCE),
            "dependencies": file_ref(req.prepared_probe_dependencies),
            "model_hash": runner._model_hash(req, pricing_for_model(MODEL))}
    return records


def freeze(root, *, dependencies, live, preparation, validation):
    require(not root.exists() and not live.exists(), "fresh packet and live roots required")
    for path in (root, live):
        require(not path.resolve().is_relative_to(repository_root()), "external root required")
    require(not root.resolve().is_relative_to(live.resolve())
            and not live.resolve().is_relative_to(root.resolve()), "independent packet/live roots")
    evidence = probe_recheck_panel.validation_evidence(validation.parent)
    require(evidence["head"] == git_commit() and evidence["implementation"] == bindings(),
            "validation is not on final commit")
    require(evidence["provider_calls"] == evidence["input_count_calls"] == 0, "offline validation")
    prepared = json.loads(preparation.read_bytes())
    require(prepared["passed"] and prepared["runtime_hash"] == runtime_content_hash()
            and prepared["implementation"] == bindings(), "preparation identity changed")
    for ref in prepared["files"]:
        read_ref(ref)
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    rate = json.loads(read_ref(prepared["pricing"]))
    prices = portfolio_dev20.price()
    require(all(Decimal(rate[k]) == Decimal(v) for k, v in prices.items()), "rates changed")
    packet = {"schema": "caller-uptake-execution-v1", "paid_authorized": False,
        "official": False, "claim_eligible": False, "head": git_commit(),
        "runtime_hash": runtime_content_hash(), "implementation": bindings(),
        "dependencies_root": str(dependencies.resolve()), "live_root": str(live.resolve()),
        "credential_file": str(repository_root() / ".env"), "model": MODEL,
        "rows": [{"row_id": label, "arm": label[0], "request":
                  request(dependencies, live, label).model_dump(mode="json")} for label in ORDER],
        "row_cap_usd": str(ROW_CAP), "arm_cap_usd": str(ARM_CAP), "total_cap_usd": str(CAP),
        "invariants": invariants(), "environments": environments(dependencies, live),
        "native_identity": portfolio_dev20.native_identity(), "native_input": native_input(),
        "pricing": prices,
        "pricing_evidence": prepared["pricing"], "validation": file_ref(validation),
        "preparation": file_ref(preparation), "programs": prepared["programs"],
        "rubric": file_ref(repository_root() / NOTE),
        "no_retry_resume_transfer_replacement": True,
        "audit_before_grades": True, "uptake_judge": "public_evidence_human_annotation",
        "limitations": prepared["limitations"], "fresh_price_review_required_at_dispatch": True}
    root.mkdir(parents=True)
    save(root, "manifest.json", packet)
    DevJournal(root, JOURNAL).append("packet_frozen", {"packet_hash": sha256_json(packet),
        "artifact": ArtifactStore(root / "artifacts").put_json(packet).model_dump(mode="json"),
        "paid_authorized": False})
    return packet


def validate(root, digest):
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest and packet["paid_authorized"] is False,
            "packet identity or authorization field changed")
    require(packet["head"] == git_commit() and packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation"] == bindings() and packet["invariants"] == invariants(),
            "source or contract changed")
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    for key in ("validation", "preparation", "pricing_evidence", "rubric"):
        read_ref(packet[key])
    for ref in json.loads(read_ref(packet["preparation"]))["files"]:
        read_ref(ref)
    require(packet["pricing"] == portfolio_dev20.price(), "prices changed")
    require(packet["native_identity"] == portfolio_dev20.native_identity(),
            "native identity changed")
    require(packet["native_input"] == native_input(), "native input identity changed")
    dependencies, live = Path(packet["dependencies_root"]), Path(packet["live_root"])
    require(packet["environments"] == environments(dependencies, live), "environment changed")
    require(packet["rows"] == [{"row_id": label, "arm": label[0], "request":
            request(dependencies, live, label).model_dump(mode="json")} for label in ORDER],
            "row roster/settings changed")
    require((packet["row_cap_usd"], packet["arm_cap_usd"], packet["total_cap_usd"])
            == (str(ROW_CAP), str(ARM_CAP), str(CAP)), "cost caps changed")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "validate"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--hash")
    parser.add_argument("--dependencies", type=Path)
    parser.add_argument("--live", type=Path)
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--validation", type=Path)
    args = parser.parse_args()
    packet = (validate(args.root, args.hash) if args.mode == "validate" else freeze(
        args.root, dependencies=args.dependencies, live=args.live,
        preparation=args.preparation, validation=args.validation))
    print(json.dumps({"packet_hash": sha256_json(packet), "head": packet["head"],
                      "paid_authorized": False}))


if __name__ == "__main__":
    main()
