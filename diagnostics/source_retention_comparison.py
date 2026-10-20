"""Frozen eight-row retention comparison; four distinct-task waves, no restart."""

from __future__ import annotations

import argparse
import json
import math
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import current_dev20, parallel_dev_batch, portfolio_dev20
from diagnostics import probe_recheck_panel as public_runner
from diagnostics import probe_recheck_public as sql_public
from diagnostics.positive_verification_panel import require, save
from patchloop import prepared_probe_dependencies as deps
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.prepared_source import admission_hash
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json

PROPOSAL = Path("C:/pt/analyses/source-retention-option-20261006-v1/comparison-proposal-v2.json")
PROPOSAL_HASH = "sha256:6dc5dcb5af814c485916a2631165333e1cc122516c1428b6259a8a7fc548fe6a"
JOURNAL = "run_dev_source_retention"
CAP = Decimal("9.60")
ORDER = [(18, "A", 1), (2, "B", 1), (18, "B", 1), (2, "A", 1),
         (18, "B", 2), (2, "A", 2), (18, "A", 2), (2, "B", 2)]
PVLIB_PROGRAM = '''import json
import pandas as pd
from pvlib.temperature import fuentes
index = pd.date_range('2019-01-01', freq='h', periods=3)
kwargs = {'poa_global': pd.Series(1000, index), 'temp_air': pd.Series(20, index),
          'wind_speed': pd.Series(1, index), 'noct_installed': 45}
rows = []
for case in ('naive', 'aware'):
    if case == 'aware':
        kwargs['poa_global'].index = index.tz_localize('UTC')
    try:
        result = fuentes(**kwargs)
        rows.append({'case': case, 'values': result.tolist(),
                     'index_preserved': result.index.equals(kwargs['poa_global'].index),
                     'name': result.name})
    except Exception as exc:
        rows.append({'case': case, 'error': type(exc).__name__})
print(json.dumps(rows))
'''


def proposal():
    value = json.loads(PROPOSAL.read_bytes())
    require(sha256_json(value) == PROPOSAL_HASH, "prepared scope drift")
    validate_rows(value["rows"])
    return value


def validate_rows(rows):
    require([(r["task_index"], r["arm"], r["repetition"]) for r in rows] == ORDER,
            "exact frozen order required")
    requests = [DevRunRequest.model_validate(r["request"]) for r in rows]
    require(sum(r.max_cost_usd for r in requests) == CAP, "allocation changed")
    require(len({r.state_root.resolve() for r in requests}) == 8, "independent roots required")
    for n, (row, req) in enumerate(zip(rows, requests, strict=True), 1):
        require(row["row"] == n and row["wave"] == (n + 1) // 2, "wave identity changed")
        require(req.repeat == 1 and req.resume_run_id is None, "fresh rows required")
        require(req.max_cost_usd == Decimal("1.20"), "row cap changed")
        require(req.retained_source_chars == (24000 if row["arm"] == "A" else 48000),
                "treatment changed")
    for index in (18, 2):
        normalized = [{k: v for k, v in r["request"].items()
                       if k not in {"state_root", "retained_source_chars"}}
                      for r in rows if r["task_index"] == index]
        require(all(r == normalized[0] for r in normalized), "confounded comparison")


def bindings():
    names = {*current_dev20.bindings(), "diagnostics/probe_recheck_public.py",
             "diagnostics/source_retention_comparison.py", ".agent/source-retention-comparison.md"}
    return {n: sha256_bytes((repository_root() / n).read_bytes()) for n in sorted(names)}


def public_spec(index, issue):
    if index == 18:
        return sql_public.design("1733", issue)
    return {"case": "1072", "program": PVLIB_PROGRAM,
            "program_hash": sha256_bytes(PVLIB_PROGRAM.encode()),
            "issue_hash": sha256_bytes(issue.replace('\r', '').encode()),
            "expected_rounded_values": [47.85, 50.85, 50.85],
            "normalization": "issue values rounded to two decimals; aware/naive atol 1e-9"}


def classify(result, spec):
    if spec["case"] == "1733":
        return sql_public.classify(result, spec)
    if result.get("exit_code") != 0 or any(result.get(k) for k in (
        "timed_out", "cleanup_failed", "truncated", "deadline_exhausted",
    )):
        return {"status": "UNASSESSED", "reason": "execution"}
    try:
        rows = json.loads(result["stdout"])
        if [r["case"] for r in rows] != ["naive", "aware"]:
            return {"status": "UNASSESSED", "reason": "invalid observation"}
        def ordinary(row):
            values = row.get("values", [])
            return (len(values) == 3 and all(math.isfinite(v) for v in values)
                    and [round(v, 2) for v in values] == spec["expected_rounded_values"]
                    and row.get("index_preserved") is True and row.get("name") == "tmod")
        passed = all(ordinary(r) for r in rows) and all(
            math.isclose(a, b, rel_tol=0, abs_tol=1e-9)
            for a, b in zip(rows[0]["values"], rows[1]["values"], strict=True))
        return {"status": "PASS" if passed else "FAIL", "observed": rows,
                "ordinary_pass": ordinary(rows[0]), "scope": "public example only"}
    except (ValueError, KeyError, TypeError):
        return {"status": "UNASSESSED", "reason": "invalid observation"}


def execute_public(root, sandbox, workspace, spec, label):
    journal = DevJournal(root, JOURNAL)
    journal.append("public_started", {"label": label, "spec_hash": sha256_json(spec)})
    result = sandbox.run_probe(workspace, "Observe the complete public example and preservation.",
                               spec["program"], deadline=None,
                               execution_identity={"run_id": JOURNAL, "action_id": label})
    record = {"label": label, "result": result, "assessment": classify(result, spec)}
    journal.append("public_finished", {
        "label": label, "artifact": ArtifactStore(root).put_json(record).model_dump(mode="json")})
    require(record["assessment"]["status"] != "UNASSESSED", "public execution uncertainty")
    return record


def prepare(root):
    require(not root.exists() and not root.is_relative_to(repository_root()), "fresh external root")
    root.mkdir(parents=True)
    p = proposal()
    require(p["runtime_hash"] == runtime_content_hash(), "prepared runtime changed")
    entries = {e["index"]: e for e in portfolio_dev20.baseline()[0]["rows"]}
    calibration = {}
    for row in p["rows"][:2]:
        index = row["task_index"]
        req = DevRunRequest.model_validate(row["request"])
        capability = current_dev20.preflight_row(root, entries[index], req)
        package, source, sandbox, identity = public_runner.environment(req)
        spec = public_spec(index, package.public.issue.description)
        # Freeze the program before observing either calibration output.
        save(root, f"public-spec-{index}.json", spec)
        base = execute_public(root, sandbox, source, spec, f"base{index}")
        require(base["assessment"]["status"] == "FAIL", "base must expose defect")
        if index == 2:
            require(base["assessment"]["ordinary_pass"], "naive preservation control failed")
            state = Path("C:/pt/cd20live06c/2")
            paths = list((state / "workspaces").glob("run_dev_*/repo"))
            require(len(paths) == 1, "positive calibration workspace missing")
            positive = paths[0]
        else:
            positive = Path("C:/pt/pv1live01/1733B1/workspaces/run_dev_ee5f0eca9f634e7a/repo")
        patch_hash = WorkspaceManager.diff_summary(positive).patch_hash
        control = execute_public(root, sandbox, positive, spec, f"positive{index}")
        require(control["assessment"]["status"] == "PASS", "positive calibration failed")
        calibration[str(index)] = {"spec": spec, "base": base, "positive": control,
                                   "positive_workspace": str(positive), "patch_hash": patch_hash,
                                   "environment": identity, "capability": capability}
    save(root, "calibration.json", calibration)
    DevJournal(root, JOURNAL).append("calibrated", {"hash": sha256_json(calibration)})
    return {"calibrated": list(calibration), "provider_calls": 0}


def freeze(root):
    p = proposal()
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    calibration = json.loads((root / "calibration.json").read_bytes())
    native = {str(e["index"]): e for e in portfolio_dev20.baseline()[0]["rows"]
              if e["index"] in (18, 2)}
    packet = {"schema": "source-retention-comparison-v1", "head": git_commit(),
              "runtime_hash": runtime_content_hash(), "implementation": bindings(),
              "proposal_hash": PROPOSAL_HASH, "rows": p["rows"], "native_entries": native,
              "calibration_hash": sha256_json(calibration), "native_identity":
              portfolio_dev20.native_identity(), "pricing": portfolio_dev20.price(),
              "total_cap_usd": str(CAP), "workers_per_wave": 2,
              "official": False, "claim_eligible": False, "automatic_followup": False,
              "validation": json.loads((root / "validation.json").read_bytes())}
    validate_inputs(packet, root)
    save(root, "manifest.json", packet)
    digest = sha256_json(packet)
    DevJournal(root, JOURNAL).append("frozen", {"packet_hash": digest})
    return {"packet_hash": digest}


def validate_inputs(packet, root):
    require(packet["rows"] == proposal()["rows"], "scope changed")
    require(packet["head"] == git_commit() and packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation"] == bindings(), "implementation drift")
    require(packet["native_identity"] == portfolio_dev20.native_identity()
            and packet["pricing"] == portfolio_dev20.price(), "execution identity drift")
    require(packet["validation"] == json.loads((root / "validation.json").read_bytes()),
            "validation receipt drift")
    for entry in packet["native_entries"].values():
        require(sha256_bytes(Path(entry["native_row"]).read_bytes()) == entry["native_row_hash"],
                "native input drift")
    calibration = json.loads((root / "calibration.json").read_bytes())
    require(sha256_json(calibration) == packet["calibration_hash"], "calibration drift")
    for row in packet["rows"][:2]:
        req = DevRunRequest.model_validate(row["request"])
        package = load_task_package(req.task.parent)
        runner._live_source_preflight(req.task.parent, package)
        require(package.task_content_hash == row["task_hash"], "task drift")
        require(admission_hash(req.prepared_source) == row["source_manifest_hash"], "source drift")
        require(deps.admit(req.prepared_probe_dependencies).model_dump(mode="json")
                == row["dependency_identity"], "dependency drift")
        _, _, _, identity = public_runner.environment(req)
        require(identity == calibration[str(row["task_index"])]["environment"], "image drift")


def execute_waves(root, packet, journal, *, dispatch=None, assess=None):
    dispatch = dispatch or parallel_dev_batch.run_parallel_rows
    assess = assess or current_dev20.assess
    validate_rows(packet["rows"])
    results, stopped = [], False
    started = monotonic()
    journal.append("allocation_reserved", {"usd": str(CAP), "transfer": False})
    for wave in range(1, 5):
        rows = [r for r in packet["rows"] if r["wave"] == wave]
        def after_row(i, value, req, rows=rows):
            row = rows[i]
            return assess(root / "assessments" / str(row["row"]),
                          packet["native_entries"][str(row["task_index"])], value, req)
        journal.append("wave_started", {"wave": wave, "rows": [r["row"] for r in rows]})
        outcome = dispatch(rows, total_cap=Decimal("2.40"), workers=2,
                           journal=journal, after_row=after_row)
        for value in outcome["rows"]:
            row = rows[value.pop("index")]
            results.append({**{k: row[k] for k in ("row", "wave", "task_index", "arm",
                                                  "repetition", "instance_id")}, **value})
        journal.append("wave_closed", {"wave": wave, "stopped": outcome["stopped"]})
        if outcome["stopped"]:
            stopped = True
            break
    result = {"rows": results, "planned": 8, "started": len(results),
              "not_started": 8 - len(results), "stopped": stopped, "allocation": "CLOSED",
              "wall_seconds": round(monotonic() - started, 3),
              "cost_nanos": sum(r["accounting"].get("cost_nanos") or 0 for r in results),
              "billing_known": all(r["accounting"]["billing_known"] for r in results),
              "counting_known": all(r["accounting"]["counting_known"] for r in results),
              "official": False, "claim_eligible": False}
    save(root, "result.json", result)
    journal.append("panel_closed", {"result_hash": sha256_json(result)})
    return result


def run(root, digest):
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest, "packet changed")
    validate_inputs(packet, root)
    approval = json.loads((root / "authorization.json").read_bytes())
    require(approval.get("approved") is True and approval.get("packet_hash") == digest
            and approval.get("human_message") == "실험 진행해줘", "exact scope approval required")
    journal = DevJournal(root, JOURNAL)
    with journal.execution_lock():
        require(not any(e["event_type"] == "panel_started" for e in journal.events()),
                "no restart or resume")
        require(all(not Path(r["request"]["state_root"]).exists() for r in packet["rows"]),
                "fresh states required")
        journal.append("panel_started", {"packet_hash": digest,
                                         "authorization_hash": sha256_json(approval)})
        return execute_waves(root, packet, journal)


def public_candidates(root):
    packet = json.loads((root / "manifest.json").read_bytes())
    result = json.loads((root / "result.json").read_bytes())
    calibration = json.loads((root / "calibration.json").read_bytes())
    records = []
    for row in result["rows"]:
        runs = (row.get("result") or {}).get("runs", [])
        run = runs[0] if runs else {}
        patch = run.get("artifact_hashes", {}).get("submitted_patch")
        if not patch:
            records.append({"row": row["row"], "status": "NOT_RUN"})
            continue
        req = DevRunRequest.model_validate(packet["rows"][row["row"] - 1]["request"])
        workspace = req.state_root / "workspaces" / run["run_id"] / "repo"
        require(WorkspaceManager.diff_summary(workspace).patch_hash == patch, "patch drift")
        _, _, sandbox, _ = public_runner.environment(req)
        record = execute_public(root, sandbox, workspace,
                                calibration[str(row["task_index"])]["spec"], f"row{row['row']}")
        records.append({"row": row["row"], **record})
    save(root, "public-candidates.json", records)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "freeze", "run", "public"])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--packet-hash")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "run":
        value = run(root, args.packet_hash)
    else:
        operations = {"prepare": prepare, "freeze": freeze, "public": public_candidates}
        operation = operations[args.command]
        value = operation(root)
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
