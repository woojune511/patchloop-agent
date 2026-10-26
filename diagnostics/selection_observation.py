"""Prepare or run a clean-base, public-observation A/B diagnostic.

Preparation is offline. Collection needs exact manifest and monetary approval;
neither an old seeded repair nor its source packet enters either model request.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from diagnostics import exception_frame_repair as loop
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask, TaskEnvironment
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevLimits, RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.prepared_probe_dependencies import load_dependencies, read_descriptor
from patchloop.prepared_source import load_source
from patchloop.repository import WorkspaceManager
from patchloop.runtime import (
    git_commit,
    repository_root,
    runtime_content_hash,
    runtime_content_paths,
)
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, load_unique_yaml, sha256_bytes, sha256_json

SCHEMA = "selection-observation-pair-v1"
PROFILE = loop.RepairProfile(SCHEMA, ("A", "B"), 8, Decimal("1.20"),
                             reserve_opportunity=True, annotation_policy="thin")
EMPTY_DIFF = sha256_bytes(b"")
PUBLIC = repository_root() / "tasks/dev-train/current-dev20/13/public.yaml"
SOURCE = Path("C:/pt/ld20p01/s/13/prepared-source.json")
SOURCE_HASH = "sha256:16326c5cddf7f836cee378e8c47b01eded3689e3f9cfcd604e086aae6ddd6a20"
DEPENDENCIES = Path("C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json")
DEPENDENCY_HASH = "sha256:685f01a9d10d047d798a164480ab4a16482b13299debd6ef2377b88a43077450"
CALIBRATION = Path("C:/pt/exception-frame-calibration-v2/calibration.json")
CALIBRATION_HASH = "sha256:82529d87a5cc86e00d5c1ca670fc54a37ab0a4969a406b90766996109b2027fc"
PROBE_IMAGE = "sha256:dad5b29e3506c35e0fd222736f4d4ef25d21b219acdd73f7bb41d59996ca8e0d"
PROBE_PROFILE = "sha256:aabaaf472062ce66208b88c7528480a685f1ecae5699c3598f3651f1668896f9"
HELPER = Path(__file__).with_name("probes") / "selection_observation.py"
PROMPT = (
    "Repair the public task from its unchanged base source. You have at most eight normal "
    "responses, one protocol correction, twelve tool actions, one diagnostic probe and one "
    "accepted source edit. Inspect current source with registered reads before editing. "
    "The supplied records are public observations, not repair instructions; supplementary "
    "fixtures may differ from the issue. Use only the offered tools. Stop if no justified "
    "edit is available. A successful replace_text ends the model phase. The host then checks "
    "the original caller, public controls, regression and isolated task acceptance. "
    "These later results are not fed back to this conversation."
)
CASES = {
    "empty": ("namespace", ""),
    "import": ("namespace", "import os\n"),
    "syntax": ("namespace", "def broken(:\n    pass\n"),
    "direct": ("direct", "def broken(:\n    pass\n"),
    "package": ("package", "def broken(:\n    pass\n"),
}


def request_payload(common, arm, *, history=(), remaining=None, correction=None,
                    probe_used=False, profile=PROFILE, source_packet=None, opportunity=None):
    require(arm in PROFILE.order and profile == PROFILE, "unexpected comparison arm/profile")
    require(source_packet is None, "seeded source packet is not allowed")
    remaining = remaining if remaining is not None else {
        "normal_calls": PROFILE.normal_calls, "tool_actions": loop.TOOL_ACTIONS,
        "diagnostic_probes": 1, "accepted_mutations": 1,
        "cost_nanos": int(PROFILE.row_cap * 1_000_000_000)}
    opportunity = opportunity or loop.repair_opportunity(
        normal_remaining=remaining["normal_calls"], tool_remaining=remaining["tool_actions"],
        probe_used=probe_used, correction=correction is not None)
    items = [{"role": "system", "content": PROMPT},
             {"role": "user", "content": canonical_json({
                 "public_task": common["public_task"],
                 "public_observations": common["packets"][arm]})}, *copy.deepcopy(history),
             {"role": "developer", "content": canonical_json({
                 "remaining": remaining, "protocol_correction": correction,
                 "opportunity": opportunity.public()})}]
    schemas = dev_tool_schemas(finish_enabled=False, allowed_tools=opportunity.allowed,
                               probe_environment=common.get("probe_environment"),
                               agent_policy="thin")
    adapter = loop.OpenAIResponsesAdapter(loop.config(), api_key="",
                                          client=SimpleNamespace(max_retries=0))
    payload = adapter.request_payload(items, schemas, system_prompt=PROMPT)
    payload["max_output_tokens"] = (loop.CORRECTION_OUTPUT if correction else loop.NORMAL_OUTPUT)
    return payload


def verify_pair(a, b):
    expected = copy.deepcopy(b)
    data = json.loads(expected["input"][1]["content"])
    extra = data["public_observations"].pop("additional_observations")
    require(bool(extra), "B has no additional observations")
    expected["input"][1]["content"] = canonical_json(data)
    require(a == expected, "A/B differs beyond the additional public observations")


def load_inputs(packet_dir):
    public = PublicTask.model_validate(load_unique_yaml(PUBLIC.read_text("utf-8")))
    require(public.split == "dev-train", "only dev-train tasks allowed")
    environment = TaskEnvironment.model_validate(load_unique_yaml(
        PUBLIC.with_name("environment.yaml").read_text("utf-8")))
    load_source(SOURCE, public.repository.url, public.repository.base_commit,
                expected_hash=SOURCE_HASH)
    require(sha256_bytes(DEPENDENCIES.read_bytes()) == DEPENDENCY_HASH,
            "dependency descriptor changed")
    dependencies = load_dependencies(DEPENDENCIES, public, read_descriptor(DEPENDENCIES)[1])
    provenance = json.loads((packet_dir / "operator-provenance.json").read_bytes())
    evidence = [*provenance["inputs"], provenance["original"]["receipt"]]
    for row in provenance["selection"]:
        evidence.extend((row["receipt"], row["source"]))
    for row in evidence:
        require(sha256_bytes(Path(row["path"]).read_bytes()) == row["hash"],
                "observation source changed")
    packets = {arm: json.loads((packet_dir / f"model-{arm}.json").read_bytes())
               for arm in PROFILE.order}
    for arm in PROFILE.order:
        name = f"model-{arm}.json"
        require(sha256_bytes((packet_dir / name).read_bytes())
                == provenance["packets"][name]["hash"],
                "packet provenance differs")
    common = {"public_task": public.model_dump(mode="json"), "packets": packets,
              "probe_environment": dependencies.environment}
    requests = {arm: request_payload(common, arm) for arm in PROFILE.order}
    verify_pair(requests["A"], requests["B"])
    require(sha256_bytes(CALIBRATION.read_bytes()) == CALIBRATION_HASH,
            "original public program changed")
    original = json.loads(CALIBRATION.read_bytes())["original_arguments"]
    return SimpleNamespace(public=public, environment=environment, dependencies=dependencies,
                           common=common, requests=requests, original_arguments=original)


def file_binding(path):
    return {"path": str(path.resolve()), "hash": sha256_bytes(path.read_bytes())}


def scope():
    return {"model": loop.MODEL, "reasoning_effort": "xhigh", "repeat_per_arm": 1,
            "order": list(PROFILE.order), "row_cap_usd": str(PROFILE.row_cap),
            "total_cap_usd": str(PROFILE.invocation_cap), "normal_calls": 8,
            "correction_calls": 1, "tool_actions": 12, "diagnostic_probes": 1,
            "accepted_mutations": 1, "ordinary_output": 40_000, "correction_output": 25_000,
            "input_limit": 60_000, "model_seconds_per_arm": 600,
            "public_check_seconds_per_arm": 390, "acceptance_seconds_per_arm": 390,
            "annotation_policy": "thin", "starting_diff": EMPTY_DIFF,
            "prices": loop.model_prices(loop.MODEL)}


def prepare(output, result_root, credential_file):
    output, result_root = output.resolve(), result_root.resolve()
    require(output.is_dir() and all(
        not output.is_relative_to(path) and not path.is_relative_to(output)
        for path in (repository_root(), result_root)), "invalid preparation root")
    disjoint(result_root, (repository_root(), output))
    require(not result_root.exists(), "result root already exists")
    packet_dir = output / "packet-build"
    loaded = load_inputs(packet_dir)
    # Bind exact code and evidence bytes. No private task files or credentials are read.
    paths = [Path(__file__), Path(loop.__file__), HELPER,
             Path(__file__).with_name("saved_candidate_acceptance.py"), PUBLIC,
             PUBLIC.with_name("environment.yaml"), SOURCE, DEPENDENCIES, CALIBRATION]
    paths.extend(packet_dir / name for name in
                 ("model-A.json", "model-B.json", "operator-provenance.json", "extract.py"))
    manifest = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
                "runtime_hash": runtime_content_hash(), "prepared_at_commit": git_commit(),
                "scope": scope(), "packet_dir": str(packet_dir),
                "result_root": str(result_root), "credential_file": str(credential_file.resolve()),
                "bindings": [file_binding(path) for path in paths],
                "first_request_hashes": {arm: sha256_json(value)
                                         for arm, value in loaded.requests.items()},
                "interpretation": "One task, one run per arm, operator-curated baseline evidence. "
                    "Measures assisted information availability, not autonomous diagnosis, "
                    "ordinary runner completion or general success rates."}
    for arm, value in loaded.requests.items():
        with (output / f"{arm}-first.json").open("x", encoding="utf-8") as stream:
            stream.write(canonical_json(value) + "\n")
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(manifest) + "\n")
    receipt = {"manifest": str(output / "manifest.json"),
               "manifest_hash": sha256_bytes((output / "manifest.json").read_bytes()),
               "provider_calls": 0, "credential_reads": 0, "input_count_calls": 0,
               "target_executions": 0, "acceptance": "NOT_RUN"}
    DevJournal(output, "run_dev_selectionpreparation").append("prepared", receipt)
    return receipt


def validate(manifest, digest):
    require(sha256_bytes(manifest.read_bytes()) == digest, "approved manifest hash differs")
    plan = json.loads(manifest.read_bytes())
    require(plan["schema"] == SCHEMA and plan["scope"] == scope(), "comparison scope changed")
    require(plan["runtime_hash"] == runtime_content_hash(), "runtime changed")
    for row in plan["bindings"]:
        require(file_binding(Path(row["path"])) == row, "bound code or evidence changed")
    loaded = load_inputs(Path(plan["packet_dir"]))
    for arm, request in loaded.requests.items():
        require(sha256_json(request) == plan["first_request_hashes"][arm]
                and json.loads((manifest.parent / f"{arm}-first.json").read_bytes()) == request,
                "prepared request changed")
    return plan, loaded


def clean_gateway(loaded, root):
    deadline = ExecutionDeadline.from_remaining(loop.MODEL_SECONDS)
    workspace = WorkspaceManager(repository_root() / "fixtures/repositories", root / "workspaces",
        prepared_source=SOURCE, prepared_source_hash=SOURCE_HASH).create(
            "base", loaded.public.repository.url, loaded.public.repository.base_commit,
            deadline=deadline)
    diff = WorkspaceManager.diff_summary(workspace)
    require(diff.patch_hash == EMPTY_DIFF and not diff.untracked_files, "base is not clean")
    probe = DockerProbeSandbox(dependencies=loaded.dependencies)
    identity = probe.preflight(deadline=deadline)
    require(identity["image_digest"] == PROBE_IMAGE
            and identity["profile_hash"] == PROBE_PROFILE
            and identity["dependency_hash"] == DEPENDENCY_HASH, "probe identity changed")
    sandbox = DockerSandbox(loaded.environment.evaluator_image)
    require(sandbox.image_identity(deadline=deadline) == loaded.environment.image_digest,
            "public check image changed or missing")
    journal = DevJournal(root, "run_dev_selectionmodel")
    journal.append("clean_base_started", {"diff_hash": diff.patch_hash,
                   "base_commit": loaded.public.repository.base_commit,
                   "prepared_source_hash": SOURCE_HASH, "probe_identity": identity,
                   "seed_restored": False, "historical_actions_imported": False})
    return DevToolGateway(workspace=workspace, public_task=loaded.public, sandbox=sandbox,
        probe_sandbox=probe, journal=journal, agent_policy="thin",
        limits=DevLimits(max_accepted_mutations=1, max_model_calls=9, max_tool_actions=12),
        deadline=deadline)


def programs():
    template = HELPER.read_text("utf-8")
    result = {name: template.replace("__LAYOUT__", layout).replace(
        '"__CHILD_SOURCE__"', repr(content)) for name, (layout, content) in CASES.items()}
    for code in result.values():
        require(len(code) <= 8000, "host helper exceeds model-source bound")
        compile(code, "<public-selection-check>", "exec")
    return result


def observation(result):
    output = result.output
    abort, reason = loop.runner._batch_execution_abort([result])
    require(abort is None, "public execution aborted: " + str(reason))
    require(result.status == "succeeded" and output.get("status") == "passed"
            and output.get("exit_code") == 0
            and output.get("execution_policy", {}).get("cleanup_status") == "confirmed"
            and not any(output.get(k) for k in ("truncated", "timed_out", "cleanup_failed",
                                               "deadline_exhausted")),
            "incomplete public observation")
    lines = [line.removeprefix("SELECTION_DIAGNOSTIC=") for line in output["stdout"].splitlines()
             if line.startswith("SELECTION_DIAGNOSTIC=")]
    require(len(lines) == 1, "public observation missing or duplicated")
    data = json.loads(lines[0])
    require(not data["overflow"] and data["inputs_before"] == data["inputs_after"],
            "public capture overflow or mutated fixture")
    return data


def grade_case(name, data):
    text = data["stdout"] + data["stderr"]
    child_selected = any(e["function"] == "expand" and any(
        r["path"].endswith("src/project/file.py") for r in e.get("selected", []))
                         for e in data["events"])
    child_attempted = any(e["function"] == "file_build" and
                          e["input"]["filepath"].endswith("src/project/file.py")
                          for e in data["events"])
    expected = ((data["exit_code"] == 0 and not text) if name == "empty" else
                (data["exit_code"] == 20 and "C0114" in text and "W0611" in text)
                if name == "import" else (data["exit_code"] == 2 and "E0001" in text))
    return {"passed": bool(expected and child_selected and child_attempted
                            and "F0010" not in text and data["exception"] is None),
            "exit_code": data["exit_code"], "child_selected": child_selected,
            "child_parse_attempted": child_attempted,
            "F0010": "F0010" in text, "E0001": "E0001" in text}


def original_summary(base, current):
    for result in (base, current):
        output = result["output"]
        trace = loop._trace(result)
        require(result["status"] == "succeeded" and output.get("status") == "passed"
                and output.get("exit_code") == 0 and trace["incomplete"] is False
                and output.get("execution_policy", {}).get("cleanup_status") == "confirmed"
                and not any(output.get(key) for key in
                            ("truncated", "timed_out", "cleanup_failed", "deadline_exhausted")),
                "original capture incomplete")
        require(len(trace["calls"]) == 2 and all(call["capture"]["status"] == "complete"
                                                for call in trace["calls"]),
                "original calls incomplete")
    old = {row["call_id"]: row for row in loop._trace(base)["calls"]}
    new = {row["call_id"]: row for row in loop._trace(current)["calls"]}
    require(set(old) == set(new) == {"call-1", "call-2"}, "original call identities differ")
    def text(call):
        return call["capture"]["stdout"] + call["capture"]["stderr"]
    require("F0010" in text(old["call-1"]), "original failure was not reproduced")
    same = loop._same_selected(loop._trace(base), loop._trace(current))
    clean = all(call["outcome"] in {"returned", "system_exit"}
                and (not call.get("exception") or call["exception"].get("type")
                     in {"SystemExit", "builtins.SystemExit"}) for call in new.values())
    control_same = all(old["call-2"][key] == new["call-2"][key]
                       for key in ("outcome", "exit_code", "exception", "capture"))
    resolved = "F0010" not in text(new["call-1"])
    return {"supported": same and clean and control_same and resolved,
            "call1_same_conditions": same, "call1_F0010_resolved": resolved,
            "call2_same_conditions": loop._same_selected(
                loop._trace(base), loop._trace(current), "call-2"),
            "control_output_unchanged": control_same, "no_unexpected_exception": clean,
            "call2_identity_note": "Cache output inside input root can alter later call inputs; "
                "report call-2 identity separately from call-1 and control output."}


def public_checks(loaded, model_gateway, root):
    before = model_gateway.current_diff_hash
    gateway = DevToolGateway(workspace=model_gateway.workspace, public_task=loaded.public,
        sandbox=model_gateway.sandbox, probe_sandbox=model_gateway.probe_sandbox,
        journal=DevJournal(root, "run_dev_selectionpublic"), limits=DevLimits(),
        deadline=ExecutionDeadline.from_remaining(loop.CHECK_SECONDS))
    store, cases = ArtifactStore(root / "artifacts"), {}
    workspace = WorkspaceManager(repository_root() / "fixtures/repositories", root / "workspaces",
        prepared_source=SOURCE, prepared_source_hash=SOURCE_HASH).create(
            "base-control", loaded.public.repository.url, loaded.public.repository.base_commit,
            deadline=gateway.deadline)
    require(WorkspaceManager.diff_summary(workspace).patch_hash == EMPTY_DIFF,
            "host baseline is not clean")
    baseline = DevToolGateway(workspace=workspace, public_task=loaded.public,
        sandbox=gateway.sandbox, probe_sandbox=gateway.probe_sandbox,
        journal=DevJournal(root / "base", "run_dev_selectionbase"), limits=DevLimits(),
        deadline=gateway.deadline)
    original_call = RequestedTool(name="run_probe", action_id="host-original",
                                  arguments=loaded.original_arguments)
    originals = []
    for selected in (baseline, gateway):
        result = selected.execute(original_call)
        abort, reason = loop.runner._batch_execution_abort([result])
        require(abort is None, "original execution aborted: " + str(reason))
        originals.append(result.model_dump(mode="json"))
    original = {**original_summary(*originals),
                "base_receipt": store.put_json(originals[0]).model_dump(mode="json"),
                "candidate_receipt": store.put_json(originals[1]).model_dump(mode="json")}
    for name, code in programs().items():
        call = RequestedTool(name="run_probe", action_id="host-" + name,
            arguments={"question": "Observe the public caller: " + name, "python_source": code,
                       "purpose": {"kind": "helper"}, "replay_action_id": None})
        base_result = baseline.execute(call)
        base = observation(base_result)
        result = gateway.execute(call)
        receipt = store.put_json(result.model_dump(mode="json"))
        data = observation(result)
        require(gateway.current_diff_hash == before, "host probe changed candidate")
        require(baseline.current_diff_hash == EMPTY_DIFF, "host baseline changed")
        same_conditions = all(base[key] == data[key]
                              for key in ("target", "environment", "inputs_before"))
        require(same_conditions, "public caller conditions changed")
        grade = grade_case(name, data)
        control_same = None
        if name in {"direct", "package"}:
            require(grade_case(name, base)["passed"], "public control baseline invalid")
            control_same = all(base[key] == data[key] for key in
                               ("stdout", "stderr", "exit_code", "exception", "outcome"))
            grade["passed"] = grade["passed"] and control_same
        else:
            require("F0010" in base["stdout"] and base["exit_code"] == 1,
                    "original baseline failure not reproduced")
        cases[name] = {**grade, "same_conditions": same_conditions,
                       "control_unchanged": control_same,
                       "base_receipt": store.put_json(base_result.model_dump(mode="json"))
                           .model_dump(mode="json"),
                       "receipt": receipt.model_dump(mode="json")}
    regression = gateway.execute(RequestedTool(name="run_check", action_id="host-regression",
                                               arguments={"check_id": "base-regression"}))
    abort, reason = loop.runner._batch_execution_abort([regression])
    require(abort is None, "regression infrastructure failed: " + str(reason))
    require(gateway.current_diff_hash == before, "public checks changed candidate")
    summary = {"candidate_hash": before, "original_call": original, "cases": cases,
               "public_cases_passed": all(row["passed"] for row in cases.values()),
               "regression_passed": regression.status == "succeeded"
                   and regression.output.get("passed") is True,
               "regression_receipt": store.put_json(regression.model_dump(mode="json"))
                   .model_dump(mode="json")}
    gateway.journal.append("public_checks_finished", summary)
    return summary


def acceptance(gateway, root, passed):
    # The only private-loading code runs in a separate process after the model closes.
    command = [sys.executable, "-X", "utf8", "-m", "diagnostics.saved_candidate_acceptance",
               "--public-task", str(PUBLIC), "--workspace", str(gateway.workspace),
               "--expected-diff-hash", gateway.current_diff_hash,
               "--prepared-source", str(SOURCE), "--prepared-source-hash", SOURCE_HASH,
               "--output-root", str(root)]
    if passed:
        command.append("--public-checks-passed")
    environment = {key: value for key, value in os.environ.items()
                   if not any(token in key.upper() for token in ("KEY", "TOKEN", "SECRET"))}
    completed = subprocess.run(command, cwd=repository_root(), env=environment,
                               capture_output=True, timeout=420, check=False)
    require(completed.returncode == 0, "isolated acceptance execution incomplete")
    summary = json.loads((root / "summary.json").read_bytes())
    require(summary["candidate_patch_hash"] == gateway.current_diff_hash,
            "acceptance candidate identity changed")
    require(not summary.get("stop_remaining", False), "acceptance outcome uncertain")
    return summary


def collect(manifest, approved_manifest_hash, approved_cap_usd):
    require(approved_cap_usd == PROFILE.invocation_cap, "exact new cap approval required")
    plan, loaded = validate(manifest, approved_manifest_hash)
    root = Path(plan["result_root"])
    disjoint(root, (repository_root(), manifest.parent, SOURCE.parent, DEPENDENCIES.parent))
    relative = [row["path"] for row in plan["bindings"]
                if Path(row["path"]).is_relative_to(repository_root())]
    loop.runner._require_tracked_clean_paths(repository_root(), [*runtime_content_paths(),
        *(Path(path).relative_to(repository_root()).as_posix() for path in relative)])
    root.mkdir()  # Existing or interrupted runs are never restarted.
    journal = DevJournal(root, "run_dev_selectioncomparison")
    journal.append("approved_collection_started", {"manifest_hash": approved_manifest_hash,
                   "cap_usd": str(approved_cap_usd), "git_commit": git_commit()})
    group = DevCostLedger(PROFILE.invocation_cap, pricing_for_model(loop.MODEL))
    rows = []
    try:
        for arm in PROFILE.order:
            gateway = clean_gateway(loaded, root / arm)
            key = loop.load_exact_openai_api_key(Path(plan["credential_file"]))
            adapter = loop.OpenAIResponsesAdapter(loop.config(), api_key=key)
            del key
            try:
                row = loop.run_model(loaded, arm, gateway, adapter, group,
                    first_hash=plan["first_request_hashes"][arm], profile=PROFILE,
                    request_builder=request_payload)
            finally:
                adapter.client.close()
            rows.append({"arm": arm, **row})
            journal.append("model_row_finished", rows[-1])
            if row["stop_remaining"]:
                break
            if row["terminal"] == "CANDIDATE_PRODUCED":
                checks = public_checks(loaded, gateway, root / arm / "public")
                rows[-1]["public_checks"] = checks
                journal.append("candidate_ready_for_evaluation", {"arm": arm, **checks})
                rows[-1]["acceptance"] = acceptance(gateway, root / arm / "acceptance",
                                                    checks["regression_passed"])
                rows[-1]["task_acceptance"] = rows[-1]["acceptance"].get("acceptance", "not_run")
            journal.append("row_finished", rows[-1])
    except BaseException as exc:
        journal.append("collection_interrupted", {"error_type": type(exc).__name__,
                                                   "resume_allowed": False})
        raise
    result = {"official": False, "rows": rows, "cost_nanos": group.spent_nanos,
              "interpretation": plan["interpretation"], "allocation_closed": True}
    (root / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    journal.append("closed", {"artifact": ArtifactStore(root / "artifacts")
                             .put_json(result).model_dump(mode="json")})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--result-root", type=Path, required=True)
    prep.add_argument("--credential-file", type=Path, required=True)
    for name in ("validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--approved-manifest-hash", required=True)
        if name == "collect":
            command.add_argument("--approved-cap-usd", type=Decimal, required=True)
    args = vars(parser.parse_args())
    name = args.pop("command")
    if name == "validate":
        validate(args["manifest"], args["approved_manifest_hash"])
        result = {"status": "VALIDATED_OFFLINE", "provider_calls": 0}
    else:
        result = globals()[name](**args)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
