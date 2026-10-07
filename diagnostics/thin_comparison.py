"""Prepare and explicitly fund the frozen sixteen-row current/thin comparison."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from decimal import Decimal
from functools import partial
from pathlib import Path
from time import monotonic

from diagnostics import current_dev20, parallel_dev_batch, portfolio_dev20
from diagnostics import probe_recheck_panel as environments
from diagnostics.positive_verification_panel import require, save
from diagnostics.thin_comparison_public import classify_public
from patchloop import prepared_probe_dependencies as deps
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest, dev_tool_surface_hash
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.prepared_source import admission_hash
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

PLAN_PATH = Path("C:/pt/thplan01/plan-v4.json")
PLAN_FILE_HASH = "sha256:e71788d6a39072988e7c6541c983bd100f3c17e286839e283b61fcdeea24febb"
RUBRIC_PATH = Path("C:/pt/thrub01/packet.json")
RUBRIC_FILE_HASH = "sha256:a9f88e43ed6a735a611871b0c74bd2f2f5cea56119165dc93634d36a8df414ab"
MODEL = "gpt-5.4-2026-03-05"
ROW_CAP, CAP = Decimal("4.00"), Decimal("64.00")
JOURNAL = "run_dev_thincomparison"
ORDER = (
    (18, "A", 1), (2, "B", 1), (20, "B", 1), (9, "A", 1),
    (9, "B", 1), (20, "A", 1), (2, "A", 1), (18, "B", 1),
    (20, "A", 2), (9, "B", 2), (18, "B", 2), (2, "A", 2),
    (2, "B", 2), (18, "A", 2), (9, "A", 2), (20, "B", 2),
)


def _pinned_json(path, expected):
    raw = path.read_bytes()
    require(sha256_bytes(raw) == expected, f"frozen input changed: {path}")
    return json.loads(raw)


def proposal():
    return _pinned_json(PLAN_PATH, PLAN_FILE_HASH)


def rubric_packet():
    packet = _pinned_json(RUBRIC_PATH, RUBRIC_FILE_HASH)
    for path, expected in packet["inputs"].items():
        require(sha256_bytes(Path(path).read_bytes()) == expected, "public rubric input changed")
    return packet


def price_identity():
    pricing = pricing_for_model(MODEL)
    return {name: str(getattr(pricing, name)) for name in (
        "input_per_million_usd", "cached_input_per_million_usd", "output_per_million_usd",
    )}


def bindings():
    names = {
        *current_dev20.bindings(), "diagnostics/thin_comparison.py",
        "diagnostics/thin_comparison_public.py", "diagnostics/source_retention_comparison.py",
        "diagnostics/probe_recheck_public.py",
    }
    # Documentation may be committed after canaries; only executable bytes bind this stage.
    return {name: sha256_bytes((repository_root() / name).read_bytes())
            for name in sorted(names) if name.endswith(".py")}


def request_rows(live_root):
    rows = deepcopy(proposal()["rows"])
    for row in rows:
        row["request"]["state_root"] = str(live_root.resolve() / row["row_id"])
    validate_rows(rows)
    return rows


def validate_rows(rows):
    frozen = proposal()["rows"]
    require(len(rows) == len(frozen) == 16, "exact sixteen rows required")
    require([(r["task_index"], r["arm"], r["repetition"]) for r in rows] == list(ORDER),
            "frozen schedule changed")
    requests = []
    for number, (row, reference) in enumerate(zip(rows, frozen, strict=True), 1):
        require(all(row[key] == reference[key] for key in (
            "row", "row_id", "wave", "position_in_wave", "task_index", "instance_id",
            "arm", "repetition",
        )), "row identity changed")
        require(row["row"] == number and row["wave"] == (number - 1) // 4 + 1,
                "wave identity changed")
        req = DevRunRequest.model_validate(row["request"])
        baseline = DevRunRequest.model_validate(reference["request"])
        require(req.model_dump(exclude={"state_root"}) == baseline.model_dump(
            exclude={"state_root"}), "request differs from frozen design")
        require(req.model == MODEL and req.repeat == 1 and req.resume_run_id is None,
                "fresh single full-model rows required")
        require(req.max_cost_usd == ROW_CAP, "row cap changed")
        require(req.agent_policy == ("current" if row["arm"] == "A" else "thin")
                and req.planning_policy == ("brief-v1" if row["arm"] == "A" else "none"),
                "policy treatment changed")
        requests.append(req)
    roots = [req.state_root.resolve() for req in requests]
    require(len(set(roots)) == 16 and all(not a.is_relative_to(b)
            for a in roots for b in roots if a != b), "independent state roots required")
    require(sum(usd_to_nanos(req.max_cost_usd) for req in requests) == usd_to_nanos(CAP),
            "invocation allocation changed")
    for wave in range(4):
        require(len({req.task.resolve() for req in requests[wave * 4:wave * 4 + 4]}) == 4,
                "distinct tasks per wave required")
    return requests


def _external_roots(root, live):
    repo = repository_root().resolve()
    require(not root.is_relative_to(repo) and not live.is_relative_to(repo)
            and not root.is_relative_to(live) and not live.is_relative_to(root),
            "separate external preparation and live roots required")


def _row_identities(rows):
    result = {}
    for row in rows:
        req = DevRunRequest.model_validate(row["request"])
        result[row["row_id"]] = {
            "model_hash": runner._model_hash(req, pricing_for_model(req.model)),
            "tool_surface_hash": dev_tool_surface_hash(
                agent_policy=req.agent_policy, planning_policy=req.planning_policy,
                probe_policy=req.probe_policy, probe_recheck=req.probe_recheck,
            ),
        }
    return result


def _case_environment(req, case, rubric):
    package, source, sandbox, environment = environments.environment(req)
    runner._live_source_preflight(req.task.parent, package)
    require(package.task_content_hash == case["task_content_hash"]
            and package.public_spec_hash == case["public_spec_hash"], "task identity changed")
    require(sha256_bytes(req.task.read_bytes()) == case["public_file_hash"],
            "public task bytes changed")
    require(package.public.task_id == rubric["task_id"]
            and package.public.repository.base_commit == rubric["base_commit"],
            "public rubric task changed")
    require(admission_hash(req.prepared_source) == case["prepared_source_descriptor_hash"],
            "prepared source changed")
    require(sha256_bytes(req.prepared_probe_dependencies.read_bytes())
            == case["prepared_dependency_descriptor_hash"], "dependency descriptor changed")
    identity = deps.admit(req.prepared_probe_dependencies).model_dump(mode="json")
    require(identity == case["previous_dependency_identity"], "dependency identity changed")
    record = {"task_hash": package.task_content_hash, "public_hash": package.public_spec_hash,
              "source_hash": admission_hash(req.prepared_source), "dependencies": identity,
              "environment": environment, "probe_profile": sandbox.current_profile()}
    return record, source, sandbox


def _public_observation(root, sandbox, workspace, rubric, identity, label):
    spec = rubric["spec"]
    program = spec.get("program", spec.get("source"))
    program_hash = spec.get("program_hash", spec.get("source_hash"))
    require(sha256_bytes(program.encode()) == program_hash, "public program changed")
    require(sandbox.current_profile() == identity["probe_profile"], "probe profile changed")
    before = WorkspaceManager.diff_summary(workspace)
    journal = DevJournal(root, JOURNAL)
    journal.append("public_started", {"label": label, "program_hash": program_hash,
                                      "patch_hash": before.patch_hash})
    try:
        result = sandbox.run_probe(
            workspace, spec.get("question", "Check the public bug and preservation cases."),
            program, deadline=None, execution_identity={"run_id": JOURNAL, "action_id": label},
        )
    except Exception as exc:
        journal.append("public_failed", {"label": label, "error_type": type(exc).__name__})
        raise
    after = WorkspaceManager.diff_summary(workspace)
    assessment = classify_public(spec["case"], result, spec)
    record = {"label": label, "program_hash": program_hash, "result": result,
              "assessment": assessment, "patch_hash_before": before.patch_hash,
              "patch_hash_after": after.patch_hash}
    save(root, f"public-{label}.json", record)
    journal.append("public_finished", {"label": label, "record_hash": sha256_json(record)})
    profile = identity["probe_profile"]
    policy = result.get("execution_policy", {})
    require(result.get("source_hash") == program_hash
            and result.get("profile_hash") == sha256_json(profile)
            and policy.get("profile_hash") == sha256_json(profile)
            and all(policy.get(key) == value for key, value in profile.items())
            and result.get("execution_policy_hash") == sha256_json(policy),
            "public execution identity changed")
    require(before.patch_hash == after.patch_hash
            and before.untracked_files == after.untracked_files,
            "public check changed candidate")
    require(assessment["status"] != "UNASSESSED", "public execution uncertainty")
    return record


def prepare(root, live_root=Path("C:/pt/thlive01")):
    root, live = root.resolve(), live_root.resolve()
    _external_roots(root, live)
    require(not root.exists() and not live.exists(), "fresh preparation and live roots required")
    plan, rubrics = proposal(), rubric_packet()
    require(price_identity() == plan["price_snapshot"], "pricing differs from reviewed proposal")
    require(Path(plan["credential_file"]).is_file(), "exact credential file is missing")
    rows = request_rows(live)
    entries = {str(entry["index"]): entry for entry in portfolio_dev20.baseline()[0]["rows"]
               if entry["index"] in {18, 20, 2, 9}}
    root.mkdir(parents=True)
    journal = DevJournal(root, JOURNAL)
    with journal.execution_lock():
        implementation, runtime = bindings(), runtime_content_hash()
        journal.append("preparation_started", {"plan_hash": PLAN_FILE_HASH, "provider_calls": 0})
        cases, capabilities, public = {}, {}, {}
        for index in (18, 20, 2, 9):
            key = str(index)
            row = next(row for row in rows if row["task_index"] == index)
            req = DevRunRequest.model_validate(row["request"])
            rubric = next(r for r in rubrics["rubrics"].values() if r["task_index"] == index)
            identity, source, sandbox = _case_environment(req, plan["cases"][key], rubric)
            cases[key] = {**identity, "rubric": rubric}
            capability = current_dev20.preflight_row(root, entries[key], req)
            capabilities[key] = capability
            require(capability["environment"] == identity["environment"],
                    "canary environment drift")
            observed = _public_observation(root, sandbox, source, rubric, identity, f"base{index}")
            public[key] = observed
            require(observed["assessment"]["status"] == "FAIL", "public base must expose defect")
            after, _, _ = _case_environment(req, plan["cases"][key], rubric)
            require(after == identity, "prepared environment changed during canaries")
        preparation = {
            "schema": "thin-comparison-preparation-v1", "source_head": git_commit(),
            "runtime_hash": runtime, "implementation": implementation, "rows": rows,
            "row_identities": _row_identities(rows), "cases": cases, "native_entries": entries,
            "native_identity": portfolio_dev20.native_identity(), "live_root": str(live),
            "plan_file_hash": PLAN_FILE_HASH, "rubric_file_hash": RUBRIC_FILE_HASH,
            "pricing": price_identity(), "model": MODEL, "credential_file": plan["credential_file"],
            "total_cap_usd": str(CAP), "row_cap_usd": str(ROW_CAP), "repetitions": 2,
            "row_count": 16, "workers_per_wave": 2, "official": False, "claim_eligible": False,
        }
        require(implementation == bindings() and runtime == runtime_content_hash(),
                "implementation changed during preparation")
        save(root, "preparation.json", preparation)
        receipt = {"passed": True, "preparation_hash": sha256_json(preparation),
                   "capabilities": capabilities, "public_base": public, "provider_calls": 0,
                   "new_public_probes": 12, "selected_test_checks": 4, "evaluator_calls": 0}
        save(root, "preflight.json", receipt)
        journal.append("preflight_passed", {"preparation_hash": sha256_json(preparation),
                                            "receipt_hash": sha256_json(receipt)})
        return {"prepared": True, "preparation_hash": sha256_json(preparation),
                "provider_calls": 0, "paid_execution_authorized": False}


def validate_inputs(packet, *, require_head=False):
    plan, rubrics = proposal(), rubric_packet()
    require(packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation"] == bindings(), "implementation drift")
    if require_head:
        require(packet["head"] == git_commit(), "executing commit changed")
        runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    require(packet["pricing"] == price_identity()
            and packet["native_identity"] == portfolio_dev20.native_identity(), "identity drift")
    require(packet["plan_file_hash"] == PLAN_FILE_HASH
            and packet["rubric_file_hash"] == RUBRIC_FILE_HASH, "design binding changed")
    require(packet["model"] == MODEL and Decimal(packet["total_cap_usd"]) == CAP
            and Decimal(packet["row_cap_usd"]) == ROW_CAP and packet["workers_per_wave"] == 2
            and packet["repetitions"] == 2 and packet["row_count"] == 16
            and packet["credential_file"] == plan["credential_file"], "declared scope changed")
    validate_rows(packet["rows"])
    require(packet["row_identities"] == _row_identities(packet["rows"]), "model/tool drift")
    require(set(packet["cases"]) == set(packet["native_entries"]) == {"18", "20", "2", "9"},
            "task roster changed")
    for key, case in packet["cases"].items():
        expected_rubric = next(r for r in rubrics["rubrics"].values()
                               if str(r["task_index"]) == key)
        require(case["rubric"] == expected_rubric, "frozen public rubric changed")
        row = next(row for row in packet["rows"] if str(row["task_index"]) == key)
        req = DevRunRequest.model_validate(row["request"])
        actual, _, _ = _case_environment(req, plan["cases"][key], case["rubric"])
        require(actual == {k: v for k, v in case.items() if k != "rubric"}, "environment drift")
        entry = packet["native_entries"][key]
        require(sha256_bytes(Path(entry["native_row"]).read_bytes()) == entry["native_row_hash"],
                "native task input changed")


def _preflight_receipt(root, preparation):
    receipt = json.loads((root / "preflight.json").read_bytes())
    require(receipt["passed"] is True and receipt["provider_calls"] == 0
            and receipt["preparation_hash"] == sha256_json(preparation), "preflight changed")
    require(any(event["event_type"] == "preflight_passed" and event["payload"] == {
        "preparation_hash": sha256_json(preparation), "receipt_hash": sha256_json(receipt),
    } for event in DevJournal(root, JOURNAL).events()), "bound preflight receipt required")
    return receipt


def freeze(root, validation_path):
    root, validation_path = root.resolve(), validation_path.resolve()
    require(not (root / "manifest.json").exists(), "manifest already frozen")
    preparation = json.loads((root / "preparation.json").read_bytes())
    require(not Path(preparation["live_root"]).exists(), "fresh live root required")
    validate_inputs(preparation)
    receipt = _preflight_receipt(root, preparation)
    validation = json.loads(validation_path.read_bytes())
    require(validation["passed"] is True and validation["provider_calls"] == 0
            and validation["runtime_hash"] == runtime_content_hash()
            and validation["implementation"] == bindings(), "validation identity changed")
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    packet = {**preparation, "schema": "thin-comparison-execution-v1", "head": git_commit(),
              "preparation_hash": sha256_json(preparation), "preflight_hash": sha256_json(receipt),
              "validation": {"path": str(validation_path),
                             "file_hash": sha256_bytes(validation_path.read_bytes())},
              "approval": "PENDING_EXACT_HUMAN_SCOPE", "automatic_followup": False}
    save(root, "manifest.json", packet)
    digest = sha256_json(packet)
    DevJournal(root, JOURNAL).append("manifest_frozen", {"packet_hash": digest})
    return {"packet_hash": digest, "total_cap_usd": str(CAP), "paid_execution_authorized": False}


def validate(root, digest):
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest, "manifest changed")
    preparation = json.loads((root / "preparation.json").read_bytes())
    require(sha256_json(preparation) == packet["preparation_hash"], "preparation changed")
    require(sha256_json(_preflight_receipt(root, preparation)) == packet["preflight_hash"],
            "preflight changed")
    require(sha256_bytes(Path(packet["validation"]["path"]).read_bytes())
            == packet["validation"]["file_hash"], "validation receipt changed")
    _external_roots(root.resolve(), Path(packet["live_root"]).resolve())
    require(all(Path(row["request"]["state_root"]).resolve()
                == Path(packet["live_root"]).resolve() / row["row_id"]
                for row in packet["rows"]), "row state root changed")
    validate_inputs(packet, require_head=True)
    return packet


def validate_authorization(packet, approval, *, approved_manifest_hash, approved_cap_usd,
                           credential_file):
    require(approved_cap_usd == CAP and approved_cap_usd > 0, "exact positive USD 64 cap required")
    require(sha256_json(packet) == approved_manifest_hash, "approved manifest differs")
    require(Path(credential_file).resolve() == Path(packet["credential_file"]).resolve(),
            "credential path differs")
    require(approval.get("approved") is True
            and approval.get("packet_hash") == approved_manifest_hash
            and isinstance(approval.get("human_message"), str) and approval["human_message"].strip()
            and approval.get("model") == packet["model"] == MODEL
            and Path(approval.get("credential_file", "")).resolve()
            == Path(credential_file).resolve()
            and approval.get("repetitions") == 2 and approval.get("row_count") == 16
            and Decimal(approval.get("total_cap_usd", "0")) == CAP,
            "exact human scope approval required")


def assess_submission(root, entry, value, req, *, packet=None):
    if packet is not None:
        validate_row_binding(req, packet)
    result = current_dev20.assess(root, entry, value, req)
    run = value["result"]["runs"][0]
    patch = run.get("artifact_hashes", {}).get("submitted_patch")
    if not patch or not result["ok"]:
        result["public"] = {"status": "NOT_RUN", "reason": "unsubmitted_or_native_unavailable"}
        return result
    packet = packet or json.loads((root.parent.parent / "manifest.json").read_bytes())
    case = packet["cases"][str(entry["index"])]
    _, _, sandbox, environment = environments.environment(req)
    require(environment == case["environment"], "submitted public environment changed")
    workspace = req.state_root / "workspaces" / run["run_id"] / "repo"
    require(WorkspaceManager.diff_summary(workspace).patch_hash == patch, "submitted patch changed")
    record = _public_observation(root, sandbox, workspace, case["rubric"], case,
                                 f"{root.name}-submitted")
    result["public"] = {"status": record["assessment"]["status"],
                        "record_hash": sha256_json(record), "patch_hash": patch}
    return result


def _execution_identity(packet):
    require(packet["head"] == git_commit()
            and packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation"] == bindings(), "frozen execution identity changed")


def validate_row_binding(req, packet):
    """Re-admit only this row's immutable execution inputs, without executing checks."""
    _execution_identity(packet)
    row = next(row for row in packet["rows"]
               if Path(row["request"]["state_root"]).resolve() == req.state_root.resolve())
    frozen = DevRunRequest.model_validate(row["request"])
    require(req.model_dump() == frozen.model_dump(), "dispatched request changed")
    require(_row_identities([row])[row["row_id"]] == packet["row_identities"][row["row_id"]],
            "row model/tool identity changed")
    key = str(row["task_index"])
    case = packet["cases"][key]
    rubric = next(r for r in rubric_packet()["rubrics"].values() if str(r["task_index"]) == key)
    require(case["rubric"] == rubric, "row rubric changed")
    actual, _, _ = _case_environment(req, proposal()["cases"][key], rubric)
    require(actual == {k: v for k, v in case.items() if k != "rubric"}, "row environment drift")
    entry = packet["native_entries"][key]
    require(sha256_bytes(Path(entry["native_row"]).read_bytes()) == entry["native_row_hash"]
            and portfolio_dev20.native_identity() == packet["native_identity"],
            "row native evaluator binding changed")


def solve_frozen_row(serialized, *, expected):
    """Reject code drift at each fresh row before the shared worker admits any call."""
    try:
        validate_row_binding(DevRunRequest.model_validate(serialized), expected)
    except Exception:
        parallel_dev_batch.stop_workers()
        raise
    return parallel_dev_batch.solve_row(serialized)


def execute_waves(root, packet, journal, *, dispatch=None, assess=None):
    production = dispatch is None
    dispatch = dispatch or parallel_dev_batch.run_parallel_rows
    validate_rows(packet["rows"])
    journal.append("allocation_reserved", {"cap_nanos": usd_to_nanos(CAP), "transfer": False,
                                           "row_count": 16})
    results, stopped = [], False
    started = monotonic()
    for wave in range(1, 5):
        if production:
            try:
                validate_inputs(packet, require_head=True)
            except Exception as exc:
                journal.append("identity_stop", {"wave": wave, "phase": "before",
                                                  "error_type": type(exc).__name__})
                stopped = True
                break
        rows = [row for row in packet["rows"] if row["wave"] == wave]

        def after_row(index, value, req, selected=rows):
            row = selected[index]
            location = root / "assessments" / row["row_id"]
            entry = packet["native_entries"][str(row["task_index"])]
            if assess is not None:
                return assess(location, entry, value, req)
            return assess_submission(location, entry, value, req, packet=packet)

        journal.append("wave_started", {"wave": wave, "rows": [r["row_id"] for r in rows]})
        options = {}
        if production:
            options["execute"] = partial(solve_frozen_row, expected=packet)
        outcome = dispatch(rows, total_cap=4 * ROW_CAP, workers=2,
                           journal=journal, after_row=after_row, **options)
        for value in outcome["rows"]:
            row = rows[value["index"]]
            cost = value["accounting"]["cost_nanos"]
            require(cost is None or 0 <= cost <= usd_to_nanos(ROW_CAP), "row allocation exceeded")
            results.append({**{key: row[key] for key in (
                "row", "row_id", "wave", "task_index", "arm", "repetition", "instance_id",
            )}, **value})
        known = all(r["accounting"]["billing_known"] and r["accounting"]["counting_known"]
                    for r in results)
        stopped = outcome["stopped"] or outcome.get("not_started", 0) > 0 or not known
        journal.append("wave_closed", {"wave": wave, "stopped": stopped})
        if production:
            try:
                validate_inputs(packet, require_head=True)
            except Exception as exc:
                journal.append("identity_stop", {"wave": wave, "phase": "after",
                                                  "error_type": type(exc).__name__})
                stopped = True
        if stopped:
            break
    cost = sum(row["accounting"]["cost_nanos"] or 0 for row in results)
    require(cost <= usd_to_nanos(CAP), "invocation cap exceeded")
    result = {"rows": results, "planned": 16, "started": len(results),
              "not_started": 16 - len(results), "stopped": stopped, "allocation": "CLOSED",
              "wall_seconds": round(monotonic() - started, 3), "recorded_cost_nanos": cost,
              "billing_known": all(r["accounting"]["billing_known"] for r in results),
              "counting_known": all(r["accounting"]["counting_known"] for r in results),
              "official": False, "claim_eligible": False}
    save(root, "result.json", result)
    journal.append("panel_closed", {"result_hash": sha256_json(result)})
    return result


def execute(root, *, approved_manifest_hash, approved_cap_usd, credential_file):
    root = root.resolve()
    packet = json.loads((root / "manifest.json").read_bytes())
    approval = json.loads((root / "authorization.json").read_bytes())
    validate_authorization(packet, approval, approved_manifest_hash=approved_manifest_hash,
                           approved_cap_usd=approved_cap_usd, credential_file=credential_file)
    journal = DevJournal(root, JOURNAL)
    with journal.execution_lock():
        require(not any(e["event_type"] == "panel_started" for e in journal.events()),
                "no restart or resume")
        packet = validate(root, approved_manifest_hash)
        require(not Path(packet["live_root"]).exists()
                and all(not Path(r["request"]["state_root"]).exists() for r in packet["rows"]),
                "fresh live states required")
        Path(packet["live_root"]).mkdir(parents=True)
        journal.append("panel_started", {"packet_hash": approved_manifest_hash,
                                         "authorization_hash": sha256_json(approval)})
        return execute_waves(root, packet, journal)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--live-root", type=Path, default=Path("C:/pt/thlive01"))
    frozen = commands.add_parser("freeze")
    frozen.add_argument("--root", type=Path, required=True)
    frozen.add_argument("--validation-path", type=Path, required=True)
    live = commands.add_parser("execute")
    live.add_argument("--root", type=Path, required=True)
    live.add_argument("--approved-manifest-hash", required=True)
    live.add_argument("--approved-cap-usd", type=Decimal, required=True)
    live.add_argument("--credential-file", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.root, args.live_root)
    elif args.command == "freeze":
        result = freeze(args.root, args.validation_path)
    else:
        result = execute(args.root, approved_manifest_hash=args.approved_manifest_hash,
                         approved_cap_usd=args.approved_cap_usd,
                         credential_file=args.credential_file)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
