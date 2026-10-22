"""Four provider-free probes for the approved Astroid helper-path information gate."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from diagnostics.caller_uptake import read_ref
from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ProbeDependencyIdentity
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.prepared_probe_dependencies import load_dependencies
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SPEC = Path("C:/pt/callerevidence19-spec/specification.json")
SOURCE = Path("C:/pt/ld20p01/s/13/prepared-source.json")
DEPENDENCIES = Path("C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json")
TASK = "tasks/dev-train/current-dev20/13/public.yaml"
TRACE = Path(__file__).parent / "probes/astroid_helper_trace.py"
ORDER = ("missing-off", "missing-on", "present-off", "present-on")
QUESTION = "Does the original caller execute the proposed helper, with which path and result?"


def program(template, mode):
    require(mode in ORDER, "unknown condition")
    source = template.replace("PRESENT = False", f"PRESENT = {mode.startswith('present')}")
    require(template.count("PRESENT = False") == 1, "initializer anchor changed")
    anchor = "entry = next(e for e in md.distribution"
    require(source.count(anchor) == 1, "entry anchor changed")
    helper = ast.unparse(ast.parse(TRACE.read_text(encoding="utf-8")))
    source = source.replace(anchor, helper + "\n" + anchor)
    source = source.replace("sys.setprofile(observe)\n", "sys.setprofile(observe)\n"
                            f"sys.settrace(helper_trace if {mode.endswith('on')} else None)\n")
    source = source.replace("    sys.setprofile(None)\n",
                            "    sys.settrace(None)\n    sys.setprofile(None)\n")
    source += ('\nprint(json.dumps({"stage": "helper_path", "calls": helper_calls, '
               '"all_call_counts": helper_counts, "selected_call_counts": helper_selected, '
               '"overflow": helper_overflow}), flush=True)\n')
    require(len(source) <= 8000 and len(source.encode()) <= 32000, "probe source exceeds limits")
    compile(source, "<public-helper-path-probe>", "exec")
    return source


def parse(receipt):
    require(receipt["status"] == "passed" and receipt["exit_code"] == 0
            and not any(receipt.get(k) for k in
                        ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted")),
            "incomplete probe; stop without retry")
    require(receipt.get("setup_checks", {}).get("status") == "passed", "setup not confirmed")
    records = [json.loads(line) for line in receipt["stdout"].splitlines()]
    require([r["stage"] for r in records] == ["before_call", "result", "helper_path"],
            "unexpected public observation stages")
    require(records[1]["overflow"] == records[2]["overflow"] == 0, "observer overflow")
    require(all(row["returned"] for row in records[2]["calls"]), "incomplete helper observation")
    return records


def normalized(records):
    root = records[0]["input"]["cwd"]
    return canonical_json(records[:2]).replace(root, "<fixture-root>")


def analyze(observations):
    require(set(observations) == set(ORDER), "four assigned conditions required")
    parity = {}
    for case in ("missing", "present"):
        off, on = (observations[f"{case}-{mode}"] for mode in ("off", "on"))
        require(normalized(off) == normalized(on), "instrumentation changed caller observations")
        result = off[1]
        expected = 1 if case == "missing" else 0
        require(result["pylint_exit_code"] == expected, "base caller outcome changed")
        require(("F0010" in result["pylint_stdout"]) == (case == "missing"),
                "base error signature changed")
        child = any(c["function"] == "get_ast"
                    and c["arguments"].get("filepath") == "src/project/file.py"
                    for c in result["calls"])
        require(child == (case == "present"), "base child-analysis behavior changed")
        parity[case] = {"matched": True, "caller_exit": expected, "child_analyzed": child}
    return {"parity": parity, "information_gate": "REQUIRES_PUBLIC_EVIDENCE_REVIEW",
            "automatic_live_dispatch": False, "paid_calls": 0, "new_billed_usd": "0"}


def export_result(output, result):
    ArtifactStore(output).write_text_immutable(output / "result.json",
                                              canonical_json(result) + "\n")


def run(output):
    require(not output.exists() and not output.resolve().is_relative_to(repository_root()),
            "fresh external output root required")
    spec = json.loads(SPEC.read_bytes())
    observation = json.loads(read_ref(spec["observation"]))
    envelope = json.loads(read_ref(spec["source"]["envelope"]))
    public = load_public_task(repository_root() / TASK)
    require(public.task_id == spec["task_id"], "task identity changed")
    programs = {mode: program(observation["program_template"], mode) for mode in ORDER}
    output.mkdir(parents=True)
    journal = DevJournal(output, "run_dev_helperpathgate")
    store = ArtifactStore(output / "artifacts")
    journal.append("helper_path_gate_frozen", {
        "official": False, "claim_eligible": False, "head": git_commit(),
        "runtime_hash": runtime_content_hash(), "order": list(ORDER),
        "implementation": {str(p.relative_to(repository_root())): sha256_bytes(p.read_bytes())
                           for p in (Path(__file__).resolve(), TRACE.resolve())},
        "source": {"path": str(SOURCE), "hash": sha256_bytes(SOURCE.read_bytes())},
        "dependencies": {"path": str(DEPENDENCIES),
                         "hash": sha256_bytes(DEPENDENCIES.read_bytes())},
        "historical_observation": spec["observation"],
        "programs": {m: store.put_text(s).model_dump(mode="json") for m, s in programs.items()},
        "authorization": "User requested execution of the immediately preceding two-stage plan.",
        "provider_calls": 0, "input_count_calls": 0, "live_cap_usd_if_qualified": "3.04420380",
    })
    try:
        deadline = ExecutionDeadline.from_remaining(180)
        deps = load_dependencies(DEPENDENCIES, public,
                                 ProbeDependencyIdentity.model_validate(envelope["probe_dependencies"]))
        probe = DockerProbeSandbox(dependencies=deps)
        identity = probe.preflight(deadline=deadline)
        require(identity["image_digest"] == observation["probe_image_digest"], "image changed")
        manager = WorkspaceManager(repository_root() / "fixtures/repositories",
                                   output / "workspaces", prepared_source=SOURCE,
                                   prepared_source_hash=envelope["prepared_source_hash"])
        workspace = manager.create(journal.run_id, public.repository.url,
                                   public.repository.base_commit, deadline=deadline)
        before = manager.diff_summary(workspace)
        require(not before.changed_files and not before.untracked_files, "base source changed")
        journal.append("helper_path_environment_ready", {
            **identity, "historical_profile_hash": observation["probe_profile_hash"],
            "profile_matches_historical": (
                identity["profile_hash"] == observation["probe_profile_hash"]),
            "diff_hash": before.patch_hash})
        observations, receipts = {}, {}
        for mode in ORDER:
            execution = {"run_id": journal.run_id, "action_id": mode,
                         "input_hash": sha256_json({"source": programs[mode],
                                                   "diff": before.patch_hash})}
            journal.append("helper_path_probe_started", {"mode": mode, "execution": execution})
            receipt = probe.run_probe(workspace, QUESTION, programs[mode], deadline=deadline,
                                      execution_identity=execution)
            ref = store.put_json(receipt).model_dump(mode="json")
            journal.append("helper_path_probe_finished", {"mode": mode, "artifact": ref})
            receipts[mode] = ref
            require(receipt["source_hash"] == sha256_bytes(programs[mode].encode()),
                    "executed source identity changed")
            require(receipt["snapshot_hash"] == observation["snapshot_hash"],
                    "public source snapshot changed")
            observations[mode] = parse(receipt)
        require(manager.diff_summary(workspace) == before, "source changed during probing")
        result = {**analyze(observations), "observations": observations, "receipts": receipts,
                  "probe_identity": identity, "official": False, "claim_eligible": False}
        artifact = store.put_json(result).model_dump(mode="json")
        journal.append("helper_path_gate_completed", {"artifact": artifact})
        export_result(output, result)
        return {k: v for k, v in result.items() if k not in ("observations", "receipts")}
    except Exception as exc:
        journal.append("helper_path_gate_stopped", {"error_type": type(exc).__name__,
                                                    "reason": str(exc), "retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(canonical_json(run(args.output)))


if __name__ == "__main__":
    main()
