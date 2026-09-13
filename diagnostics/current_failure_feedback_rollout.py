"""Bounded current-failure A/B continuations; default agent behavior is unchanged.

Reuse the existing dispatcher, gateway, recovery and independent public-case audit.
Prepare/validate are provider-free; run requires its own exact packet approval.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from diagnostics import current_failure_feedback as design
from diagnostics import failure_given_repair_rollout as feedback
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes

SCHEMA = "current-failure-feedback-rollout-v1"
DESIGN = Path("C:/pt/analyses/current-failure-feedback-20260914")
DESIGN_HASH = "sha256:17b1b872cdd8a8ded90df17451885571f1c497d40501ba1af695edf30c8d9cf2"
SEAL_HASH = "sha256:24a8b2dcb03413c8327496931d51a1e69c34609c324d1c645a9c34d4ad5bd440"
ORDER = ("A1", "B1", "B2", "A2")
BRANCH_CAP, TOTAL_CAP = Decimal("1.00"), Decimal("4.00")
native, require, read = feedback.native, feedback.require, feedback.read


@dataclass(frozen=True)
class Plan(feedback.Plan):
    candidate_report: dict = field(repr=False)


def load_plan() -> Plan:
    require(sha256_bytes((DESIGN / "packet.json").read_bytes()) == DESIGN_HASH
            and sha256_bytes((DESIGN / "completion.json").read_bytes()) == SEAL_HASH,
            "frozen current-failure design changed")
    design.validate(DESIGN)
    ancestor = feedback.load_plan()
    checkpoint = read(DESIGN / "checkpoint.json")
    require(checkpoint["source_run_id"] == design.RUN_ID
            and checkpoint["turn_id"] == design.TURN_ID, "wrong nested checkpoint")
    source = Path(checkpoint["source_root"])
    events = DevJournal(source, checkpoint["source_run_id"]).events()
    cutoff = events[checkpoint["cutoff_event_sequence"] - 1]
    require(cutoff["event_hash"] == checkpoint["cutoff_event_hash"]
            and checkpoint["prefix_event_count"] == checkpoint["cutoff_event_sequence"] - 1,
            "nested prefix cutoff changed")
    arms = {arm: read(DESIGN / f"{arm}.json") for arm in ("A", "B")}
    state = reconstruct_state(arms["A"]["input"])
    for key in ("runtime_hash", "task_content_hash"):
        require(checkpoint[key] == ancestor.envelope[key], "ancestor/nested contract mismatch")
    require(checkpoint["tool_surface_hash"] == native.dev_tool_surface_hash(),
            "nested tool surface mismatch")
    require(ancestor.package.public.model_dump(mode="json") == state["public_task"]
            and ancestor.package.task_content_hash == checkpoint["task_content_hash"],
            "nested public task mismatch")
    candidate_report = read(DESIGN / "feedback.json")
    require(design.prior.add_report(arms["A"], ancestor.report) == arms["A"]
            and design.add_feedback(arms["A"], candidate_report) == arms["B"],
            "frozen initial overlay changed")
    case = (DESIGN / "verification-case.py").read_text(encoding="utf-8")
    require(case == ancestor.verification_source, "public reproduction changed")
    return Plan(
        checkpoint=checkpoint, envelope=ancestor.envelope,
        prefix=events[:checkpoint["prefix_event_count"]],
        initial_context=(DESIGN / "context.json").read_text(encoding="utf-8"),
        arms=arms, package=ancestor.package, state=state, report=ancestor.report,
        verification_source=case, candidate_report=candidate_report)


def envelope_for(plan) -> dict:
    base = feedback.envelope_for(plan)
    return {
        **base, "schema_version": SCHEMA,
        "source_design_hash": DESIGN_HASH, "source_completion_hash": SEAL_HASH,
        "branch_order": list(ORDER), "cap_usd_each": str(BRANCH_CAP),
        "cap_usd_total": str(TOTAL_CAP),
        "candidate_report_hash": sha256_bytes(design.wire(plan.candidate_report)),
        "initial_context_hash": sha256_bytes(plan.initial_context.encode()),
        "criteria_hash": sha256_bytes((DESIGN / "criteria.json").read_bytes()),
        "base_commit": plan.envelope["base_commit"],
        "treatment": "B adds only the sealed current-candidate observation to each latest "
                     "unsent state, with diff-bound currency. A retains the old report only. "
                     "Keep native/opaque history, notes, guidance, tools and eligibility intact.",
        "nested_replay": "Import the prefix strictly before the fixed A2 turn. All source "
                         "events are inherited evidence, not newly billed/actioned work. "
                         "Restore remaining model/tool/mutation budgets; fresh cost ledgers.",
        "pricing": {**base["pricing"], "verified_on": "2026-09-13",
                    "verification_timezone": "UTC", "service_tier": "default"},
        "references": {"pricing": "https://developers.openai.com/api/docs/pricing",
                       "continuation": design.DOC_URL},
    }


def packet_files(plan) -> dict[str, bytes]:
    return {
        **{f"{arm}.json": design.wire(request) for arm, request in plan.arms.items()},
        "historical-report.json": design.wire(plan.report),
        "current-report.json": design.wire(plan.candidate_report),
        "verification-case.py": plan.verification_source.encode(),
        "criteria.json": (DESIGN / "criteria.json").read_bytes(),
        "plan.json": canonical_json(envelope_for(plan)).encode(),
    }


def prepare(root: Path) -> dict:
    plan = load_plan()
    root = native.fresh_root(root, repository_root(), DESIGN, design.SOURCE,
                             Path(plan.checkpoint["source_root"]))
    store = ArtifactStore(root)
    files = packet_files(plan)
    for name, raw in files.items():
        store.write_text_immutable(root / name, raw.decode())
    return json.loads(files["plan.json"])


def validate(root: Path) -> tuple[Plan, dict]:
    plan = load_plan()
    files = packet_files(plan)
    require(all((root / name).read_bytes() == raw for name, raw in files.items()),
            "current-failure executable packet or implementation changed")
    return plan, json.loads(files["plan.json"])


class Branch(feedback.Branch):
    diagnostic_schema = SCHEMA
    run_id_prefix = "run_dev_current_failure_"

    def bind_candidate_report(self, report):
        require(self.label in ORDER and (report is not None) == self.label.startswith("B"),
                "current report must belong only to B")
        if self._new_events("current_candidate_feedback_bound"):
            require(self.candidate_report() == report, "current report cannot be replaced")
            return
        ref = (self.store.put_text(design.wire(report).decode(), "application/json")
               if report is not None else None)
        self.journal.append("current_candidate_feedback_bound", {
            "arm": self.label[0], "report_artifact": ref.model_dump(mode="json") if ref else None,
            "observed_on_diff_hash": report["observed_on_diff_hash"] if report else None,
            "new_tool_execution": False,
        })

    def candidate_report(self):
        try:
            bindings = self._new_events("current_candidate_feedback_bound")
            require(len(bindings) == 1 and self.label in ORDER
                    and bindings[0]["arm"] == self.label[0], "current report binding mismatch")
            bound = bindings[0]
            if self.label.startswith("A"):
                require(bound["report_artifact"] is None and bound["observed_on_diff_hash"] is None,
                        "current report leaked into A")
                return None
            report = json.loads(self.store.read_bytes(Artifact.model_validate(
                bound["report_artifact"])))
            require(report["observed_on_diff_hash"] == bound["observed_on_diff_hash"]
                    and report["origin"] == "operator_executed_public_diagnostic"
                    and report["case_definition_ref"] == design.prior.FIELD,
                    "current report identity mismatch")
            return report
        except (ContractError, RecoveryError, ValueError, KeyError, TypeError) as exc:
            raise native.engine.AbortExperiment("CURRENT_CANDIDATE_FEEDBACK_ERROR") from exc

    def reconcile(self):
        if self.terminal is None and not self._new_events("terminal"):
            # Uncertain billing/dispatch still wins; check the report before pending tools.
            uncertain = native.uncertainty([self])
            if uncertain:
                raise native.engine.AbortExperiment(uncertain)
            self.candidate_report()
        super().reconcile()

    def project_request(self, request, context):
        request, context, _, details = super().project_request(request, context)
        report = self.candidate_report()
        state = reconstruct_state(request["input"])
        raw_context = json.loads(context)
        if report is None:
            require(design.FIELD not in state and design.FIELD not in raw_context,
                    "treatment leaked into control")
        else:
            request = design.add_feedback(request, report)
            state = reconstruct_state(request["input"])
            raw_context[design.FIELD] = state[design.FIELD]
            context = canonical_json(raw_context)
        ref = self._new_events("current_candidate_feedback_bound")[0]["report_artifact"]
        return request, context, "current_candidate_feedback_projected", {
            **details, "arm": self.label[0], "new_tool_execution": False,
            "candidate_report_hash": ref["content_hash"] if ref else None,
            "candidate_report_currency": state[design.FIELD]["currency"] if report else None,
        }


def initialize_branch(plan, label, root, sandbox, probe, deadline):
    branch = native.initialize_branch(plan, label, root, sandbox, probe, deadline,
                                      branch_class=Branch)
    branch.initial_request = plan.arms["A"]  # Apply B only to the latest unsent snapshot.
    branch.bind_report(plan.report)
    branch.bind_candidate_report(plan.candidate_report if label.startswith("B") else None)
    return branch


def run(plan_root, result_root, **kwargs):
    # The checkpoint root is A2 inside an immutable completed experiment. Do not
    # let a new result be placed in one of that experiment's sibling directories.
    native.fresh_root(result_root, design.SOURCE)
    return feedback.execute_packet(
        plan_root, result_root,
        protocol=feedback.RolloutProtocol(DESIGN, ORDER, BRANCH_CAP, TOTAL_CAP,
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
