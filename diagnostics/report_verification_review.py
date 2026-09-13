"""Experimental report-aware working context, not a new completion gate.

Compare report-only A with lifecycle/reminder B at the same public checkpoint.
Only the latest unsent state changes. No report resolution is inferred from a
mutation, check PASS, probe exit code, line trace or model-authored note.
"""
from __future__ import annotations

import argparse
import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from diagnostics import failure_given_repair_rollout as feedback
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import history_metadata, reconstruct_state, validate_model_input
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "report-verification-review-v1"
FIELD = "reported_issue_review"
ORDER = ("A1", "B1", "B2", "A2")
BRANCH_CAP, TOTAL_CAP = Decimal("0.50"), Decimal("2.00")
require, read, design, native = feedback.require, feedback.read, feedback.design, feedback.native


def review(state: dict) -> dict:
    """Reference already delivered public evidence; do not create a model-authored note."""
    report = state[design.FIELD]
    diff_hash = state["current_diff"]["patch_hash"]
    same_diff = diff_hash == report["observed_on_diff_hash"]
    # These references already exist in this state's bounded recent_probes projection.
    # Their actual source/output remains in native calls/results, not duplicated here.
    probes = [p for p in state.get("recent_probes", []) if p["diff_hash"] == diff_hash][-3:]
    return {
        "origin": "harness_projection_of_operator_public_report", "model_authored": False,
        "report_ref": design.FIELD, "current_diff_hash": diff_hash,
        "report_observation": "current_candidate" if same_diff else "historical_candidate",
        "state": "probe_evidence_available_for_review" if probes else (
            "reported_failure_on_current_candidate" if same_diff else "modified_unverified"),
        "current_diff_behavior_verdict": "NOT_ASSESSED",
        "probe_evidence_refs": [{"action_id": p["action_id"],
                                 "delivery": "native_function_call_and_output",
                                 "execution_status": p["observation"]["execution_status"]}
                                for p in probes],
        "question": "Does the current candidate satisfy the report's input, initial fixture, "
                    "environment and expected observables?",
        "interpretation": "An edit is not confirmation. Registered-check PASS is not this "
                          "report's verdict. The probe references are recent current-diff "
                          "observations, not automatic same-case matches. Compare their actual "
                          "input/fixture and output to the report. Exit zero, line entry or a "
                          "note marked resolved does not establish semantic repair. No automatic "
                          "PASS/FAIL or mandatory experiment is added.",
    }


def completion_guidance(state: dict, issue: dict) -> dict:
    """Advice follows real availability; leave eligibility, budget and tool policy intact."""
    guidance = copy.deepcopy(state["completion_guidance"])
    allowed = state["available_tool_names"]
    if not guidance["submission_ready"]:
        guidance["message"] += (
            " Also keep working_notes.reported_issue_review in view: repairing or passing "
            "registered checks does not by itself confirm the reported case."
        )
        return guidance
    message = (
        "Registered checks make this diff eligible for submission, separately from the "
        "reported case in working_notes.reported_issue_review. "
    )
    if issue["probe_evidence_refs"]:
        message += (
            "Review the referenced current-diff probe's actual input, fixture and output "
            "against the report before deciding whether it confirms repair. An unrelated "
            "or inconclusive probe leaves the case unverified. "
        )
        if "run_probe" in allowed:
            message += "If that evidence is insufficient, run_probe remains optional. "
    elif "run_probe" in allowed:
        guidance["next_action"] = {"tool": "run_probe"}
        message += (
            "No current-diff probe evidence is recorded in the recent view. Consider run_probe "
            "with the report's same input, initial fixture and expected observables. "
        )
    else:
        message += "No new diagnostic is offered by the current action space. "
    if "finish_task" in allowed:
        message += "finish_task remains available; keep any unverified behavior explicit. "
    guidance["message"] = message + "This is advisory, not a submission gate."
    return guidance


def add_review(request: dict) -> dict:
    """Only two declared paths in the unsent current view may differ from report-only A."""
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    require(items[-1].get("role") == "developer", "unsent current view required")
    original = reconstruct_state(items)
    require(FIELD not in original["working_notes"], "review must be projected exactly once")
    view = json.loads(items[-1]["content"])
    require(view["kind"] == design.STATE_KIND, "current view required")
    issue = review(original)
    changed = copy.deepcopy(request)
    notes = copy.deepcopy(original["working_notes"])
    notes[FIELD] = issue
    guidance = completion_guidance(original, issue)
    view["state"].update(working_notes=notes, completion_guidance=guidance)
    changed["input"][-1]["content"] = design.wire(view).decode()
    validate_model_input(changed["input"], history_metadata(changed["input"]))
    require(reconstruct_state(changed["input"]) == {
        **original, "working_notes": notes, "completion_guidance": guidance},
        "unrelated state changed")
    return changed


def load_plan() -> feedback.Plan:
    plan = feedback.load_plan()
    control = plan.arms["F"]
    return replace(plan, arms={"A": control, "B": add_review(control)})


def criteria() -> dict:
    return {
        "comparison": "Fresh report-only A versus report-lifecycle/advice B; one checkpoint, "
                      "two independent samples each, fixed A1/B1/B2/A2 order. Prior F1/F2 are "
                      "motivation only, never replacement controls.",
        "treatment_paths": ["working_notes.reported_issue_review", "completion_guidance"],
        "constant": "Same report, source, diff, task, native/opaque history, model, limits, "
                    "tools and optional note schema. No planning or memory update is required.",
        "agent_observations": ["new calls to first mutation", "mutation admission",
                               "agent-authored same-case probe versus unrelated exploration",
                               "comparison of expected and actual observables",
                               "new current-diff visible checks", "finish or explicit uncertainty"],
        "semantic_scoring": "Blind public source/probe review first. A report mention, accepted "
                            "mutation, probe execution, note resolution or finish is not a repair. "
                            "Use the frozen independent post-episode public case audit; never "
                            "feed that audit to the agent or count it as an agent action.",
        "interpretation_limit": "This jointly tests lifecycle salience and completion advice, "
                                "not which subfield caused a difference. One checkpoint and "
                                "two samples per arm cannot establish a general improvement, "
                                "hidden acceptance or default adoption.",
    }


def envelope_for(plan) -> dict:
    return {
        **feedback.envelope_for(plan), "schema_version": SCHEMA,
        "branch_order": list(ORDER), "cap_usd_total": str(TOTAL_CAP),
        "criteria_hash": sha256_bytes(design.wire(criteria())),
        "treatment": "B adds a harness-authored report review reference in working_notes and "
                     "report-aware completion advice to each unsent view. A remains report-only. "
                     "No inference of case resolution and no change to tools or eligibility.",
    }


def packet_files(plan) -> dict[str, bytes]:
    return {
        **{f"{arm}.json": design.wire(request) for arm, request in plan.arms.items()},
        "feedback.json": design.wire(plan.report),
        "verification-case.py": plan.verification_source.encode(),
        "criteria.json": design.wire(criteria()),
        "plan.json": canonical_json(envelope_for(plan)).encode(),
    }


def prepare(root: Path) -> dict:
    plan = load_plan()
    root = native.fresh_root(root, repository_root(), feedback.DESIGN,
                             Path(plan.checkpoint["source_root"]))
    store = ArtifactStore(root)
    files = packet_files(plan)
    for name, raw in files.items():
        store.write_text_immutable(root / name, raw.decode())
    return json.loads(files["plan.json"])


def validate(root: Path) -> tuple[feedback.Plan, dict]:
    plan = load_plan()
    files = packet_files(plan)
    require(all((root / name).read_bytes() == raw for name, raw in files.items()),
            "report-review packet or implementation changed")
    return plan, json.loads(files["plan.json"])


class Branch(feedback.Branch):
    diagnostic_schema = SCHEMA
    run_id_prefix = "run_dev_report_review_"

    def project_request(self, request, context):
        request, context, _, details = super().project_request(request, context)
        require(self.label in ORDER, "unknown report-review arm")
        if self.label.startswith("B"):
            base = json.loads(context)
            request = add_review(request)
            state = reconstruct_state(request["input"])
            base["working_notes"][FIELD] = state["working_notes"][FIELD]
            base["completion_guidance"] = state["completion_guidance"]
            context = canonical_json(base)
            details["review_hash"] = sha256_json(state["working_notes"][FIELD])
            details["review_state"] = state["working_notes"][FIELD]["state"]
        else:
            require(FIELD not in reconstruct_state(request["input"])["working_notes"],
                    "treatment leaked into control")
        return request, context, "report_verification_review_projected", {
            **details, "arm": self.label[0], "new_tool_execution": False,
        }


def initialize_branch(plan, label, root, sandbox, probe, deadline):
    branch = native.initialize_branch(plan, label, root, sandbox, probe, deadline,
                                      branch_class=Branch)
    # Both start from the identical report-only wire request; project_request applies
    # B exactly once, producing the frozen B packet. Raw context is not native-note
    # delivery metadata and must not replace already constructed native fields.
    branch.initial_request = plan.arms["A"]
    branch.bind_report(plan.report)
    return branch


def run(plan_root, result_root, **kwargs):
    return feedback.execute_packet(
        plan_root, result_root,
        protocol=feedback.RolloutProtocol(feedback.DESIGN, ORDER, BRANCH_CAP, TOTAL_CAP,
                                          validate, initialize_branch), **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "validate", "run"])
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path)
    parser.add_argument("--approval-packet-hash")
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--max-cost-usd", type=Decimal)
    parser.add_argument("--pricing-verified-on")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.plan_root)
    elif args.command == "validate":
        result = validate(args.plan_root)[1]
    else:
        require(all((args.result_root, args.approval_packet_hash, args.credential_file,
                     args.max_cost_usd, args.pricing_verified_on)), "exact run inputs required")
        result = run(args.plan_root, args.result_root,
                     approval_packet_hash=args.approval_packet_hash,
                     credential_file=args.credential_file, cap=args.max_cost_usd,
                     pricing_verified_on=args.pricing_verified_on,
                     progress=lambda p: print(canonical_json(p), flush=True))
    print(canonical_json(result))


if __name__ == "__main__":
    main()
