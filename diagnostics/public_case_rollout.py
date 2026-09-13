"""Supplied public-case A/B continuations; diagnostics only, exact approval required.

Both arms receive the same program/report. Only B sees its execution lifecycle and
advice. Reuse the existing native dispatcher/recovery and separate operator audit.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from diagnostics import current_failure_feedback_rollout as checkpoint
from diagnostics import failure_given_repair_rollout as feedback
from diagnostics import public_case_lifecycle as case_loop
from patchloop.contracts import Artifact
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "public-case-lifecycle-rollout-v1"
DESIGN = Path("C:/pt/analyses/public-case-loop-design-20260914")
SEAL_HASH = "sha256:a832c568eb1f9fb2a56726f005c26c16dba6e43d0412c69a2b62f1a8a546f996"
ORDER = ("A1", "B1", "B2", "A2")
BRANCH_CAP, TOTAL_CAP = Decimal("1.00"), Decimal("4.00")
native, require, read = feedback.native, feedback.require, feedback.read


@dataclass(frozen=True)
class Plan(feedback.Plan):
    case: dict = field(repr=False)
    seed_request: dict = field(repr=False)


def load_plan():
    require(
        sha256_bytes((DESIGN / "completion.json").read_bytes()) == SEAL_HASH,
        "public-case design seal changed",
    )
    require(
        all(
            sha256_bytes((DESIGN / name).read_bytes()) == digest
            for name, digest in read(DESIGN / "completion.json")["files"].items()
        ),
        "public-case design changed",
    )
    base = checkpoint.load_plan()  # Verified nested A2 cutoff and original task envelope.
    # Deliberately use only A + original report. The newer candidate failure is NOT input.
    case = case_loop.define_case(
        purpose="Reproduce the supplied report with the same public input and fixture.",
        inputs=base.report["input"],
        initial_state=base.report["initial_state"],
        expected_observables={
            "environment": base.report["environment"],
            "observables": base.report["observables"],
            "expected": base.report["expected"],
        },
        question="Does the current candidate match this public report's expected observables?",
        python_source=base.verification_source,
        provenance=base.report["provenance"],
        execution_context={
            **{
                k: base.envelope[k]
                for k in (
                    "task_id",
                    "task_version",
                    "task_content_hash",
                    "base_commit",
                    "probe_image_digest",
                    "probe_profile_hash",
                )
            },
            "public_task_hash": sha256_json(base.package.public.model_dump(mode="json")),
        },
    )
    seed = base.arms["A"]
    rows = case_loop.observations(case, base.prefix)
    arms = {a: case_loop.add_case(seed, case, rows, treatment=a == "B")[0] for a in ("A", "B")}
    return Plan(
        **{k: getattr(base, k) for k in feedback.Plan.__dataclass_fields__ if k != "arms"},
        arms=arms,
        case=case,
        seed_request=seed,
    )


def criteria():
    return {
        "comparison": "Fresh A1/B1/B2/A2; same supplied public program and original report. "
        "Only B adds exact-case lifecycle and completion advice as one treatment.",
        "treatment_paths": [case_loop.STATUS, "completion_guidance"],
        "shared_added_field": case_loop.DEFINITION,
        "agent_observations": [
            "exact supplied-program execution versus other probes",
            "actual versus expected output comparison",
            "current result citation",
            "mutation admission and new regressions",
            "visible checks and finish",
        ],
        "semantic_scoring": "Record masked public code observations before revealing labeled "
        "operator verdicts. Operator audits are post-episode, not agent credit. "
        "Execution completion, concern resolution and finish are not repair.",
        "interpretation_limit": "Use of a supplied case, not autonomous case generation or a "
        "subfield-isolated effect. Recognizable baseline limits blinding. "
        "One checkpoint/two samples cannot justify default adoption or "
        "hidden acceptance; bounds/uncertainty are separate from ability.",
    }


def envelope_for(plan):
    base = feedback.envelope_for(plan)
    return {
        **base,
        "schema_version": SCHEMA,
        "source_completion_hash": SEAL_HASH,
        "source_design_hash": read(DESIGN / "completion.json")["files"]["design.md"],
        "branch_order": list(ORDER),
        "cap_usd_each": str(BRANCH_CAP),
        "cap_usd_total": str(TOTAL_CAP),
        "case_definition_hash": sha256_json(plan.case),
        "criteria_hash": sha256_json(criteria()),
        "initial_context_hash": sha256_bytes(plan.initial_context.encode()),
        "treatment": criteria()["comparison"],
        "source_delivery": "One identical inline definition in both first unsent states; later "
        "verified append-v1 native references, bounded inline fallback on loss.",
        "current_result_rule": "Exact UTF-8 program + full diff + task/sandbox/action receipt. "
        "Behavior NOT_ASSESSED; no new gate, tool, allowance or action credit.",
        "pricing": {
            **base["pricing"],
            "verified_on": "2026-09-13",
            "verification_timezone": "UTC",
            "service_tier": "default",
        },
        "references": {
            "pricing": "https://developers.openai.com/api/docs/pricing",
            "continuation": "https://developers.openai.com/api/docs/guides/"
            "migrate-to-responses#4-decide-when-to-use-statefulness",
        },
    }


def packet_files(plan):
    return {
        **{f"{arm}.json": canonical_json(request).encode() for arm, request in plan.arms.items()},
        "historical-report.json": canonical_json(plan.report).encode(),
        "case-definition.json": canonical_json(plan.case).encode(),
        "verification-case.py": plan.verification_source.encode(),
        "criteria.json": canonical_json(criteria()).encode(),
        "plan.json": canonical_json(envelope_for(plan)).encode(),
    }


def prepare(root):
    plan = load_plan()
    root = native.fresh_root(
        root,
        repository_root(),
        DESIGN,
        checkpoint.design.SOURCE,
        Path(plan.checkpoint["source_root"]),
    )
    store = feedback.ArtifactStore(root)
    files = packet_files(plan)
    for name, raw in files.items():
        store.write_text_immutable(root / name, raw.decode())
    return json.loads(files["plan.json"])


def validate(root):
    plan = load_plan()
    files = packet_files(plan)
    require(
        all((root / name).read_bytes() == raw for name, raw in files.items()),
        "public-case packet or implementation changed",
    )
    return plan, json.loads(files["plan.json"])


class Branch(feedback.Branch):
    diagnostic_schema = SCHEMA
    run_id_prefix = "run_dev_public_case_"

    def bind_case(self, case):
        if self._new_events("public_case_bound"):
            require(self.case() == case, "supplied case cannot be replaced")
            return
        case_loop.validate_case(case)
        require(
            case["execution_context"]["public_task_hash"]
            == sha256_json(self.gateway.public_task.model_dump(mode="json")),
            "case belongs to another public task",
        )
        ref = self.store.put_text(canonical_json(case), "application/json")
        self.journal.append(
            "public_case_bound",
            {
                "arm": self.label[0],
                "case_id": case["case_id"],
                "definition_artifact": ref.model_dump(mode="json"),
                "new_tool_execution": False,
            },
        )

    def case(self):
        try:
            bindings = self._new_events("public_case_bound")
            require(
                len(bindings) == 1 and self.label in ORDER and bindings[0]["arm"] == self.label[0],
                "case binding mismatch",
            )
            binding = bindings[0]
            case = json.loads(
                self.store.read_bytes(Artifact.model_validate(binding["definition_artifact"]))
            )
            case_loop.validate_case(case)
            require(
                case["case_id"] == binding["case_id"]
                and case["execution_context"]["public_task_hash"]
                == sha256_json(self.gateway.public_task.model_dump(mode="json")),
                "case task identity mismatch",
            )
            return case
        except (ContractError, RecoveryError, ValueError, KeyError, TypeError, OSError) as exc:
            raise native.engine.AbortExperiment("PUBLIC_CASE_EVIDENCE_ERROR") from exc

    def case_rows(self, *, record=False):
        try:
            case = self.case()
            rows = case_loop.observations(case, self.journal.events())
            by_action = {r["reference"]["action_id"]: r for r in rows}
            bindings = self._new_events("public_case_result_bound")
            seen = set()
            for binding in bindings:
                action_id = binding["reference"]["action_id"]
                row = by_action[action_id]
                require(
                    action_id not in seen
                    and binding["case_id"] == case["case_id"]
                    and binding["reference"] == row["reference"],
                    "case result binding mismatch",
                )
                require(
                    self.store.read_bytes(Artifact.model_validate(binding["result_artifact"]))
                    == canonical_json(row["result"]).encode(),
                    "case result artifact changed",
                )
                seen.add(action_id)
            if record:
                for action_id, row in by_action.items():
                    if action_id not in seen:
                        ref = self.store.put_text(canonical_json(row["result"]), "application/json")
                        self.journal.append(
                            "public_case_result_bound",
                            {
                                "case_id": case["case_id"],
                                "reference": row["reference"],
                                "result_artifact": ref.model_dump(mode="json"),
                                "new_tool_execution": False,
                            },
                        )
            return rows
        except (ContractError, RecoveryError, ValueError, KeyError, TypeError, OSError) as exc:
            raise native.engine.AbortExperiment("PUBLIC_CASE_EVIDENCE_ERROR") from exc

    def reconcile(self):
        if self.terminal is None and not self._new_events("terminal"):
            uncertain = native.uncertainty([self])
            if uncertain:
                raise native.engine.AbortExperiment(uncertain)
            self.case_rows()  # Integrity before pending actions; no new execution here.
        super().reconcile()

    def _finish_batch(self):
        # Original cleanup/deadline uncertainty retains priority over derived case evidence.
        abort, _ = native.loop._batch_execution_abort(self.latest)
        if abort is not None:
            return super()._finish_batch()
        self.case_rows(record=True)
        return super()._finish_batch()

    def project_request(self, request, context):
        request, context, _, details = super().project_request(request, context)
        request, overlay, diagnostic = case_loop.add_case(
            request,
            self.case(),
            self.case_rows(record=True),
            treatment=self.label.startswith("B"),
            previously_projected=bool(self._new_events("public_case_projected")),
        )
        raw_context = json.loads(context)
        raw_context.update(overlay)
        return (
            request,
            canonical_json(raw_context),
            "public_case_projected",
            {
                **details,
                "arm": self.label[0],
                "case_id": self.case()["case_id"],
                "definition_delivery": overlay[case_loop.DEFINITION].get("delivery", "inline"),
                "delivery_diagnostic": diagnostic,
                "case_state": overlay.get(case_loop.STATUS, {}).get("state"),
                "new_tool_execution": False,
            },
        )


def initialize_branch(plan, label, root, sandbox, probe, deadline):
    branch = native.initialize_branch(
        plan, label, root, sandbox, probe, deadline, branch_class=Branch
    )
    branch.initial_request = plan.seed_request
    branch.bind_report(plan.report)
    branch.bind_case(plan.case)
    return branch


def run(plan_root, result_root, **kwargs):
    native.fresh_root(result_root, checkpoint.design.SOURCE)
    return feedback.execute_packet(
        plan_root,
        result_root,
        protocol=feedback.RolloutProtocol(
            DESIGN, ORDER, BRANCH_CAP, TOTAL_CAP, validate, initialize_branch
        ),
        **kwargs,
    )


def public_execution_summary(result):
    """CLI handoff hides labeled behavior verdicts; complete evidence stays on disk."""
    return {
        k: result[k]
        for k in (
            "terminal",
            "provider_free",
            "new_provider_calls",
            "new_input_count_calls",
            "recorded_cost_nanos",
            "provider_cost_known",
            "elapsed_ms",
            "count_billing_and_invoice",
            "task_acceptance",
            "safety_state",
            "official",
        )
        if k in result
    }


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
        require(
            all(
                (
                    args.result_root,
                    args.approval_packet_hash,
                    args.credential_file,
                    args.max_cost_usd,
                    args.pricing_verified_on,
                )
            ),
            "exact run inputs required",
        )
        result = public_execution_summary(
            run(
                args.plan_root,
                args.result_root,
                approval_packet_hash=args.approval_packet_hash,
                credential_file=args.credential_file,
                cap=args.max_cost_usd,
                pricing_verified_on=args.pricing_verified_on,
            )
        )
        # No per-arm outcomes or candidate bytes before masked observations are recorded.
    print(canonical_json(result))


if __name__ == "__main__":
    main()
