"""Prepare one public failure-given repair diagnostic; no execution entry point.

Reuse the native checkpoint restorer. Only the unsent current-state view receives
an operator-authored report; no native action, check verdict or repair credit is
invented. This module neither imports a collector nor reads credentials.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path

from diagnostics import counterexample_review as seed
from diagnostics.probe_first_view import require, wire
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import (
    STATE_KIND,
    history_metadata,
    reconstruct_state,
    validate_model_input,
)
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import sha256_bytes, sha256_json

SCHEMA = "failure-given-repair-design-v1"
FIELD = "operator_public_feedback"
EVIDENCE = Path("C:/pt/analyses/public-counterexamples-20260913")
COMPLETION_HASH = "sha256:8c69493caa10db7257b785516712781f5d91b22aaf1f8fda307e092c3b4e16cf"
CASE_ID = "multi_parent"
PUBLIC_SPEC = (repository_root()
               / "tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2/public.yaml")
DOC_URL = "https://developers.openai.com/api/docs/guides/agent-evals"
BOUNDARIES = {
    "provider_calls": 0, "input_count_calls": 0, "credential_reads": 0,
    "tool_executions": 0, "docker_operations": 0, "candidate_execution": "NOT_RUN",
    "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN", "private_evaluation": "NOT_RUN",
    "official": False, "claim_eligible": False, "paid_execution_authorized": False,
}


def one(values: list[dict], key: str, value: str) -> dict:
    matches = [item for item in values if item.get(key) == value]
    require(len(matches) == 1, f"expected one {key}={value}")
    return matches[0]


def select_case(packet: dict, execution: dict) -> tuple[dict, dict, dict]:
    """Allowlist a single observed input/output, not neighboring operator diagnoses."""
    case = one(packet["cases"], "id", CASE_ID)
    require(case == {"id": CASE_ID, "path": "a/../b/../c",
                     "requirement": "traversal side effects"}, "selected case changed")
    require(execution["status"] == "passed" and execution["exit_code"] == 0
            and not any(execution[key] for key in (
                "timed_out", "truncated", "deadline_exhausted", "cleanup_failed")),
            "incomplete public diagnostic")
    data = json.loads(execution["stdout"])
    row = one(data["rows"], "id", CASE_ID)
    environment = {key: data[key] for key in ("platform", "python", "umask")}
    require(environment == {"platform": "Linux", "python": "3.12.13", "umask": "0o022"},
            "observed environment changed")
    # Fixed post-hoc case, not a new oracle generated from the candidate's behavior.
    expected = {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "b", "c")]}
    actual = {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "c")]}
    require(row["real"] == expected and row["fake"] == actual and row["matches"] is False,
            "selected failure differs from the frozen observation")
    return case, environment, {"expected": expected, "actual": actual}


def single_case_source(source: bytes, case: dict) -> bytes:
    """Freeze the existing public reproduction with one case; do not execute it."""
    tree = ast.parse(source)
    declarations = [n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "CASES" for t in n.targets)]
    require(len(declarations) == 1, "case declaration missing or ambiguous")
    declaration = declarations[0]
    require(one(ast.literal_eval(declaration.value), "id", CASE_ID) == case,
            "case source and packet disagree")
    declaration.value = ast.parse(repr([case]), mode="eval").body
    return (ast.unparse(ast.fix_missing_locations(tree)) + "\n").encode()


def load_report(request: dict, checkpoint: dict, root: Path) -> tuple[dict, dict, bytes]:
    completion_path = root / "completion.json"
    require(sha256_bytes(completion_path.read_bytes()) == COMPLETION_HASH,
            "public evidence completion changed")
    completion = json.loads(completion_path.read_bytes())
    verified = {str(completion_path.resolve()): COMPLETION_HASH}

    def sealed(name: str) -> bytes:
        raw = (root / name).read_bytes()
        require(sha256_bytes(raw) == completion["files"][name], "public evidence bytes changed")
        verified[str((root / name).resolve())] = sha256_bytes(raw)
        return raw

    packet_raw, execution_raw = sealed("packet.json"), sealed("A2-execution.json")
    packet, execution = json.loads(packet_raw), json.loads(execution_raw)
    source = sealed("probe.py")
    state = reconstruct_state(request["input"])
    subject = one(packet["subjects"], "subject", "A2")
    require(subject["run_id"] == checkpoint["source_run_id"] == seed.SOURCE_ID
            and subject["diff_hash"] == state["current_diff"]["patch_hash"]
            and sha256_bytes(state["current_diff"]["patch"].encode()) == subject["diff_hash"]
            and one(state["current_sources"], "path", "pyfakefs/fake_os.py")["file_hash"]
            == subject["source_hash"], "observed candidate and checkpoint differ")
    require(packet["baseline_commit"] == checkpoint["base_commit"]
            and packet["runtime_hash"] == runtime_content_hash()
            and Path(packet["public_spec_path"]).resolve() == PUBLIC_SPEC.resolve()
            and sha256_bytes(PUBLIC_SPEC.read_bytes()) == packet["public_spec_hash"],
            "public task or runtime changed")
    verified[str(PUBLIC_SPEC.resolve())] = packet["public_spec_hash"]
    require(execution["subject"] == "A2"
            and execution["source_hash"] == packet["probe_source_hash"] == sha256_bytes(source)
            and execution["execution_policy_hash"] == sha256_json(execution["execution_policy"])
            and execution["execution_policy"]["cleanup_status"] == "confirmed"
            and all(execution[k] == v for k, v in packet["sandbox_identity"].items()),
            "public execution binding mismatch")
    observer = "run_dev_public_counterexamples_20260913"
    identity = {"run_id": observer, "action_id": "panel_A2", "input_hash": sha256_json({
        "packet": sha256_bytes(packet_raw), "subject": subject})}
    require(execution["identity"] == identity, "operator execution identity mismatch")
    sealed(f"runs\\{observer}.jsonl")
    events = DevJournal(root, observer).events()
    started = one([e["payload"] for e in events if e["event_type"] == "public_panel_started"],
                  "subject", "A2")
    finished = one([e["payload"] for e in events if e["event_type"] == "public_panel_finished"],
                   "subject", "A2")
    require(started["execution_identity"] == identity
            and finished["result_hash"] == sha256_bytes(execution_raw),
            "public journal and receipt disagree")
    case, environment, observations = select_case(packet, execution)
    report = {
        "kind": "operator_public_bug_report_v1", "origin": "operator_executed_public_diagnostic",
        "notice": "An external public bug report, not an agent tool result or registered check. "
                  "Investigate it within the current task using the available tools and budgets.",
        "observed_on_diff_hash": subject["diff_hash"],
        "environment": environment,
        "initial_state": "An empty existing current working directory, mode 0o700, in each "
                         "of the real and fake filesystems. Fake filesystem mode is Linux.",
        "input": {"operation": "os.makedirs", "path": case["path"], "path_type": "str",
                  "mode": "0o777", "exist_ok": False},
        "observables": "Exception type/errno and all relative entries with type and mode.",
        **observations,
        "oracle": "Real Linux os.makedirs executed with the same initial fixture and umask.",
        "provenance": {"public_packet_hash": sha256_bytes(packet_raw),
                       "public_execution_receipt_hash": sha256_bytes(execution_raw),
                       "case_id": CASE_ID},
    }
    provenance = {"verified_source_files": verified, "operator_execution_identity": identity,
                  "observed_source_hash": subject["source_hash"],
                  "snapshot_hash": execution["snapshot_hash"],
                  "sandbox_identity": packet["sandbox_identity"]}
    return report, provenance, single_case_source(source, case)


def add_report(request: dict, report: dict) -> dict:
    """Overlay only the latest unsent snapshot; safely label older-diff evidence.

    A future diagnostic adapter must call this after native request construction on
    each turn. It is deliberately not wired into the default agent or a paid command.
    """
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    require(items[-1].get("role") == "developer", "latest state must end the request")
    view = json.loads(items[-1]["content"])
    require(view["kind"] == STATE_KIND, "latest current-state snapshot required")
    original = reconstruct_state(items)
    overlay = {**copy.deepcopy(report), "currency": (
        "current_candidate" if original["current_diff"]["patch_hash"]
        == report["observed_on_diff_hash"] else "historical_candidate"),
        "currency_rule": "This report describes only observed_on_diff_hash. After an edit it "
                         "does not establish whether the new candidate passes or fails this case."}
    require(FIELD not in view["state"] or {
        **view["state"][FIELD], "currency": overlay["currency"]} == overlay,
            "conflicting operator feedback already present")
    view["state"][FIELD] = overlay
    changed = copy.deepcopy(request)
    changed["input"][-1]["content"] = wire(view).decode()
    validate_model_input(changed["input"], history_metadata(changed["input"]))
    expected = {**original, FIELD: overlay}
    require(reconstruct_state(changed["input"]) == expected, "unrelated current state changed")
    return changed


def criteria() -> dict:
    return {
        "evidence_rule": "Cite actual public decision/action/result and diff identities. "
                         "Do not inspect reasoning plaintext or infer understanding from silence.",
        "axes": {
            "recognition": "Explicit public acknowledgment of the missing b directory; "
                           "mark unobserved rather than assuming a silent model understood it.",
            "repair_attempt": "Separate proposed, gateway-rejected and accepted replacements. "
                              "An admitted edit or persuasive explanation is not correctness.",
            "agent_same_case_recheck": "Record agent-initiated run_probe on the changed diff, "
                                       "same str input/fixture and expected observables. Different "
                                       "cases or existence-only prints are partial evidence, "
                                       "not PASS.",
            "operator_same_case_audit": "After the episode, execute verification-case.py on each "
                                        "distinct final candidate in the public sandbox. Compare "
                                        "complete real/fake output. This is operator execution, "
                                        "never agent credit or feedback to the finished episode.",
            "registered_checks": "Separate inherited PASS from newly executed checks. Both "
                                 "visible checks must PASS on the final diff after an edit.",
            "submission": "Record finish and patch hash; compare it with the tested candidate. "
                          "Finish alone can occur without fixing the supplied bug.",
            "resources": "Report model/tool/mutation counts, input/cached/output/reasoning token "
                         "counts and costs. Limits/uncertainty censor observations, not ability.",
        },
        "interpretation": {
            "repair_and_recheck_pass": "Local evidence that repair is possible given this report; "
                                       "investigate autonomous discovery; do not claim causality.",
            "recognized_but_wrong_repair": "Causal understanding or repair remains a candidate.",
            "unchanged_submission": "Feedback use/completion judgment remains a candidate; "
                                    "do not automatically score inability to implement a repair.",
            "operator_pass_without_agent_recheck": "Separate correct candidate from unverified "
                                                    "agent completion behavior.",
            "missing_or_censored": "Cause remains unseparated; no automatic extra sample.",
        },
        "limits": ["One selected case/checkpoint; not generalization or an autonomous discovery.",
                   "Earlier no-feedback runs are descriptive, not new randomized controls.",
                   "No hidden evaluation, paid judge, default adoption or broad correctness claim.",
                   ],
        "initial_scores": "NOT_RUN", "task_acceptance": "NOT_RUN", "official": False,
    }


def compile_packet(source_root: Path, evidence_root: Path) -> tuple[dict, dict[str, bytes]]:
    request, checkpoint = seed.restore(source_root)
    _, eligibility = seed.add_review(request)  # Reuse eligibility checks, never the suffix.
    eligibility = {k: v for k, v in eligibility.items() if k not in {
        "control_request_bytes", "treatment_request_bytes", "changed_field"}}
    report, provenance, verification_source = load_report(request, checkpoint, evidence_root)
    changed = add_report(request, report)
    protocol = {
        "schema_version": SCHEMA, "status": "PREPARED_INPUTS_ONLY", "collector_implemented": False,
        "model": seed.MODEL, "reasoning_effort": "medium", "max_output_tokens": 25000,
        "context_policy": "append-v1", "compaction": False, "encrypted_continuation": "retained",
        "branch_order": ["F1", "F2"], "schedule": "independent continuations, round-robin",
        "planning_cap_usd_each": "0.50", "planning_cap_usd_total": "1.00", "new_calls_each": 8,
        "budget_transfer": False, "automatic_retry_resume_or_extra_sample": False,
        "pricing": "Reverify official model rates and exact counting before any live grant. "
                   "Reserve uncached input plus full 25000 output; never reduce the ceiling. "
                   "Planning caps do not guarantee eight funded calls; count billing unverified.",
        "baseline_request": "Identity reference only, not another paid arm or historical control.",
        "treatment": f"Only state.{FIELD} in the latest unsent developer snapshot is added. "
                     "The original system prompt is unchanged; no voluntary-review suffix.",
        "lifecycle": "Overlay the same report once in each latest snapshot; retain already-sent "
                     "native items. Bind currency to the current diff, never carry failure to an "
                     "edited candidate as current. Do not increment tool/check/allowance counters.",
        "policy": "Existing tools, notes, exact replacement and normal finish remain voluntary. "
                  "No new gate, mandatory read/probe, registered check or repair credit.",
        "next_required_work": "Adapt the existing bounded collector, mock feedback lifecycle "
                              "and fault recovery, then seal an executable packet for separate "
                              "exact paid approval. This design has no run command.",
        "sandbox": "Future agent probes and post-episode same-case audit need prepared Docker "
                   "and pinned images. Never automatically start, pull or build.",
        "references": {"evaluation": DOC_URL, "pricing": seed.REFERENCES["pricing"]},
        "boundaries": BOUNDARIES,
    }
    files = {
        "baseline-request.json": wire(request), "feedback-request.json": wire(changed),
        "feedback.json": wire(report), "checkpoint.json": wire(checkpoint),
        "evidence-provenance.json": wire(provenance), "verification-case.py": verification_source,
        "protocol.json": wire(protocol), "criteria.json": wire(criteria()),
        "candidate.patch": reconstruct_state(request["input"])["current_diff"]["patch"].encode(),
    }
    return {
        "schema_version": SCHEMA, "status": "PREPARED_INPUTS_ONLY",
        "source_root": str(source_root.resolve()), "evidence_root": str(evidence_root.resolve()),
        "runtime_hash": runtime_content_hash(), "implementation_hashes": {
            **seed.implementation_hashes(),
            "diagnostics/failure_given_repair.py": sha256_bytes(Path(__file__).read_bytes())},
        "file_hashes": {name: sha256_bytes(body) for name, body in files.items()},
        "metrics": {"eligibility": eligibility, "request_bytes_before": len(wire(request)),
                    "request_bytes_after": len(wire(changed)),
                    "added_bytes": len(wire(changed)) - len(wire(request)),
                    "reasoning_item_count": history_metadata(
                        changed["input"])["reasoning_item_count"],
                    "unchanged_native_prefix_hash": sha256_bytes(wire(request["input"][:-1])),
                    "unchanged_tools_hash": sha256_bytes(wire(request["tools"]))},
        "boundaries": BOUNDARIES,
    }, files


def prepare(source_root: Path, output_root: Path, evidence_root: Path = EVIDENCE) -> dict:
    require(source_root.is_absolute() and output_root.is_absolute(), "absolute roots required")
    root = output_root.resolve()
    require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    require(all(not root.is_relative_to(p.resolve()) and not p.resolve().is_relative_to(root)
                for p in (repository_root(), source_root, evidence_root)), "protected root overlap")
    packet, files = compile_packet(source_root, evidence_root)
    store = ArtifactStore(root)
    for name, body in {**files, "packet.json": wire(packet)}.items():
        store.write_text_immutable(root / name, body.decode())
    return packet


def validate(root: Path) -> dict:
    packet = json.loads((root / "packet.json").read_bytes())
    expected, files = compile_packet(Path(packet["source_root"]), Path(packet["evidence_root"]))
    require(packet == expected, "packet/source/runtime/implementation changed")
    require(all((root / name).read_bytes() == body for name, body in files.items()),
            "frozen diagnostic file changed")
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    v = commands.add_parser("validate")
    v.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    packet = (prepare(args.source_root, args.output_root) if args.command == "prepare"
              else validate(args.root))
    # Do not print native input, opaque reasoning or source observations to terminal logs.
    print(wire({"status": packet["status"], "file_hashes": packet["file_hashes"],
                "metrics": packet["metrics"], "boundaries": packet["boundaries"]}).decode())


if __name__ == "__main__":
    main()
