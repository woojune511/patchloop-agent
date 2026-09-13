"""Two bounded failure-given continuations, using the existing native branch engine.

Preparation/validation never execute a provider, credential loader or sandbox.
Run needs exact separate approval; the default agent and frozen design stay unchanged.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import counterexample_review_rollout as native
from diagnostics import failure_given_repair as design
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.errors import ContractError, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SCHEMA = "failure-given-repair-rollout-v1"
DESIGN = Path("C:/pt/analyses/failure-given-repair-20260914/ready")
DESIGN_HASH = "sha256:8a1ea07a28fa7035419445cd7634fa23fddc586a08bdac1d9604ec42e946e7b3"
ORDER = ("F1", "F2")
BRANCH_CAP, TOTAL_CAP = Decimal("0.50"), Decimal("1.00")
require, read = native.shared.require, native.read


@dataclass(frozen=True)
class Plan(native.Plan):
    report: dict = field(repr=False)
    verification_source: str = field(repr=False)


def load_plan() -> Plan:
    require(sha256_bytes((DESIGN / "packet.json").read_bytes()) == DESIGN_HASH,
            "frozen feedback design changed")
    design.validate(DESIGN)
    base = native.load_plan()
    require(base.checkpoint == read(DESIGN / "checkpoint.json")
            and design.wire(base.arms["A"]) == (DESIGN / "baseline-request.json").read_bytes(),
            "native seed differs from the feedback design")
    request, report = read(DESIGN / "feedback-request.json"), read(DESIGN / "feedback.json")
    require(design.add_report(base.arms["A"], report) == request, "feedback request drift")
    return Plan(**{**vars(base), "arms": {"F": request}}, report=report,
                verification_source=(DESIGN / "verification-case.py").read_text(encoding="utf-8"))


def envelope_for(plan: Plan) -> dict:
    envelope = native.envelope_for(plan)
    return {
        **envelope, "schema_version": SCHEMA, "source_design_hash": DESIGN_HASH,
        "branch_order": list(ORDER), "samples_per_arm": 2,
        "cap_usd_total": str(TOTAL_CAP), "cap_usd_each": str(BRANCH_CAP),
        "report_hash": sha256_bytes(design.wire(plan.report)),
        "verification_source_hash": sha256_bytes(plan.verification_source.encode()),
        "criteria_hash": sha256_bytes((DESIGN / "criteria.json").read_bytes()),
        "treatment": "One operator-public report in each current view, with diff-bound currency. "
                     "Native history, system prompt, tools and check verdicts are unchanged.",
        "operator_audit": "After normal episode completion, recheck each distinct final candidate "
                          "with the fixed public case. Never feed this back or give agent credit. "
                          "Skip all new execution on uncertainty or experiment deadline.",
        "pricing": {**envelope["pricing"], "verified_on": "2026-09-13",
                    "verification_timezone": "UTC", "service_tier": "default"},
        "references": {"pricing": "https://developers.openai.com/api/docs/pricing",
                       "continuation": "https://developers.openai.com/api/docs/guides/reasoning"},
    }


def prepare(root: Path) -> dict:
    plan = load_plan()
    root = native.fresh_root(root, repository_root(), DESIGN,
                             Path(plan.checkpoint["source_root"]))
    envelope = envelope_for(plan)
    store = ArtifactStore(root)
    for name, raw in {
        "F.json": design.wire(plan.arms["F"]), "feedback.json": design.wire(plan.report),
        "verification-case.py": plan.verification_source.encode(),
        "criteria.json": (DESIGN / "criteria.json").read_bytes(),
        "plan.json": canonical_json(envelope).encode(),
    }.items():
        store.write_text_immutable(root / name, raw.decode())
    return envelope


def validate(root: Path) -> tuple[Plan, dict]:
    plan = load_plan()
    envelope = envelope_for(plan)
    require(read(root / "plan.json") == envelope, "executable packet or implementation changed")
    require((root / "F.json").read_bytes() == design.wire(plan.arms["F"])
            and (root / "feedback.json").read_bytes() == design.wire(plan.report)
            and (root / "verification-case.py").read_bytes() == plan.verification_source.encode()
            and (root / "criteria.json").read_bytes() == (DESIGN / "criteria.json").read_bytes(),
            "executable request/report/reproduction changed")
    return plan, envelope


class Branch(native.Branch):
    diagnostic_schema = SCHEMA
    run_id_prefix = "run_dev_feedback_"

    def bind_report(self, report):
        existing = self._new_events("operator_feedback_bound")
        if existing:
            require(self.report() == report, "operator report cannot be replaced")
            return
        ref = self.store.put_text(design.wire(report).decode(), "application/json")
        self.journal.append("operator_feedback_bound", {
            "report_artifact": ref.model_dump(mode="json"),
            "observed_on_diff_hash": report["observed_on_diff_hash"],
            "origin": "operator_executed_public_diagnostic", "new_tool_execution": False,
        })

    def report(self):
        try:
            bindings = self._new_events("operator_feedback_bound")
            require(len(bindings) == 1, "exactly one durable report binding required")
            binding = bindings[0]
            report = json.loads(self.store.read_bytes(Artifact.model_validate(
                binding["report_artifact"])))
            require(report["observed_on_diff_hash"] == binding["observed_on_diff_hash"]
                    and report["origin"] == binding["origin"], "report binding mismatch")
            return report
        except (ContractError, RecoveryError, ValueError, KeyError) as exc:
            raise native.engine.AbortExperiment("OPERATOR_FEEDBACK_ERROR") from exc

    def reconcile(self):
        if self.terminal is not None or self._new_events("terminal"):
            return super().reconcile()
        # Uncertain provider/count outcomes retain precedence; no new actions precede them.
        uncertain = native.uncertainty([self])
        if uncertain:
            raise native.engine.AbortExperiment(uncertain)
        self.report()  # Integrity check before any pending tool replay.
        super().reconcile()

    def project_request(self, request, context):
        require(design.seed.PROMPT_SUFFIX not in request["input"][0]["content"],
                "voluntary-review instruction is outside this design")
        changed = design.add_report(request, self.report())
        overlay = reconstruct_state(changed["input"])[design.FIELD]
        stored_context = json.loads(context)
        require(stored_context["current_diff"]["patch_hash"]
                == reconstruct_state(changed["input"])["current_diff"]["patch_hash"],
                "context and request diff differ")
        stored_context[design.FIELD] = overlay
        return changed, canonical_json(stored_context), "operator_feedback_projected", {
            "report_hash": self._new_events("operator_feedback_bound")[0][
                "report_artifact"]["content_hash"],
            "observed_on_diff_hash": overlay["observed_on_diff_hash"],
            "current_diff_hash": stored_context["current_diff"]["patch_hash"],
            "currency": overlay["currency"], "origin": overlay["origin"],
        }


def initialize_branch(plan, label, root, sandbox, probe, deadline):
    branch = native.initialize_branch(plan, label, root, sandbox, probe, deadline,
                                      branch_class=Branch)
    branch.bind_report(plan.report)
    return branch


def drive(plan, branches, adapter_factory, **kwargs):
    return native.drive(plan, branches, adapter_factory, branch_cap=BRANCH_CAP,
                        total_cap=TOTAL_CAP, **kwargs)


def operator_audits(plan, branches, probe, observer, store, deadline):
    """One public execution per final candidate, not part of the agent episode."""
    rows, cached = [], {}
    for branch in branches:
        deadline.check()
        require(branch.terminal is not None
                and native.loop._unresolved_decision(branch.journal) is None,
                "operator audit requires a settled episode")
        summary = WorkspaceManager.diff_summary(branch.gateway.workspace, deadline=deadline)
        require(not summary.untracked_files
                and summary.patch_hash == branch.terminal["last_recorded_diff_hash"],
                "final candidate drift before operator audit")
        key = summary.patch_hash
        if key in cached:
            rows.append({"branch": branch.label, "diff_hash": key, "reused": True,
                         **cached[key]})
            continue
        identity = {"run_id": observer.run_id, "action_id": "case_" + key.split(":")[-1][:16],
                    "input_hash": sha256_json({"diff_hash": key,
                                              "source": plan.verification_source})}
        observer.append("operator_case_started", {
            "origin": "operator", "branch": branch.label, "diff_hash": key,
            "execution_identity": identity,
        })
        output = probe.run_probe(
            branch.gateway.workspace, "Does the final candidate match the supplied public case?",
            plan.verification_source, deadline=deadline, execution_identity=identity)
        artifact = store.put_json(output)
        status = "ERROR"
        try:
            require(output["status"] == "passed" and output["exit_code"] == 0
                    and not any(output.get(k, False) for k in (
                        "truncated", "timed_out", "cleanup_failed", "deadline_exhausted")),
                    "operator reproduction did not complete")
            require(output["source_hash"] == sha256_bytes(plan.verification_source.encode())
                    and output["execution_policy_hash"] == sha256_json(output["execution_policy"])
                    and output["execution_policy"]["cleanup_status"] == "confirmed"
                    and output["image_digest"] == plan.envelope["probe_image_digest"]
                    and output["profile_hash"] == plan.envelope["probe_profile_hash"],
                    "operator reproduction provenance differs")
            data = json.loads(output["stdout"])
            require({k: data[k] for k in plan.report["environment"]} == plan.report["environment"]
                    and len(data["rows"]) == 1, "operator fixture/environment changed")
            row = data["rows"][0]
            require(row["id"] == design.CASE_ID and row["real"] == plan.report["expected"]
                    and row["matches"] is (row["real"] == row["fake"]), "operator oracle changed")
            status = "PASS" if row["matches"] else "FAIL"
        except (KeyError, TypeError, ValueError, ContractError):
            pass  # Keep the actual evidence; malformed execution is not semantic failure.
        entry = {"origin": "operator", "agent_credit": False, "case_outcome": status,
                 "result_artifact": artifact.model_dump(mode="json")}
        cached[key] = entry
        rows.append({"branch": branch.label, "diff_hash": key, "reused": False, **entry})
        observer.append("operator_case_finished", rows[-1])
        if output.get("cleanup_failed"):
            raise native.engine.AbortExperiment("SANDBOX_CLEANUP_FAILED")
        if output.get("deadline_exhausted"):
            raise ExecutionDeadlineExceeded("operator audit deadline exhausted")
        if status == "ERROR":
            raise native.engine.AbortExperiment("OPERATOR_AUDIT_ERROR")
    return rows


def run(plan_root, result_root, *, approval_packet_hash, credential_file, cap,
        pricing_verified_on, adapter_factory=None, sandbox=None, probe=None,
        checkpoint=lambda _: None, progress=lambda _: None):
    return execute_packet(
        plan_root, result_root,
        protocol=RolloutProtocol(DESIGN, ORDER, BRANCH_CAP, TOTAL_CAP, validate, initialize_branch),
        approval_packet_hash=approval_packet_hash, credential_file=credential_file, cap=cap,
        pricing_verified_on=pricing_verified_on, adapter_factory=adapter_factory,
        sandbox=sandbox, probe=probe, checkpoint=checkpoint, progress=progress)


@dataclass(frozen=True)
class RolloutProtocol:
    """Only the frozen design varies; admission, execution and audit stay shared."""

    design_root: Path
    order: tuple[str, ...]
    branch_cap: Decimal
    total_cap: Decimal
    validate: Callable
    initialize: Callable


def execute_packet(plan_root, result_root, *, protocol, approval_packet_hash, credential_file, cap,
                   pricing_verified_on, adapter_factory=None, sandbox=None, probe=None,
                   checkpoint=lambda _: None, progress=lambda _: None):
    plan, envelope = protocol.validate(plan_root)
    require(approval_packet_hash == sha256_bytes((plan_root / "plan.json").read_bytes()),
            "exact executable packet approval required")
    require(cap == protocol.total_cap and credential_file.resolve() == repository_root() / ".env",
            "exact cap/credential path required")
    require(pricing_verified_on == utc_now().date().isoformat(), "price review date mismatch")
    root = native.fresh_root(result_root, repository_root(), protocol.design_root, plan_root,
                             Path(plan.checkpoint["source_root"]))
    root.mkdir()  # Exclusive one-shot; no resume, retry or replacement sample command.
    store, observer = ArtifactStore(root), DevJournal(root, "run_dev_feedback_observer")
    deadline = ExecutionDeadline.from_remaining(1800)
    client, branches, result = None, [], None
    started = monotonic()
    with observer.execution_lock():
        store.write_text_immutable(root / "envelope.json", canonical_json({
            **envelope, "paid_execution_authorized": adapter_factory is None,
            "approval_packet_hash": approval_packet_hash,
            "pricing_verified_on": pricing_verified_on,
            "provider_free": adapter_factory is not None,
        }))
        observer.append("diagnostic_execution_started", {
            "packet_hash": approval_packet_hash, "provider_free": adapter_factory is not None,
        })
        try:
            if adapter_factory is None:
                native.loop._live_source_preflight(native.TASK, plan.package, deadline=deadline)
                native.loop._require_tracked_clean_paths(repository_root(),
                    ["diagnostics/" + n for n in native.implementation_hashes()], deadline=deadline)
                sandbox = native.loop._live_sandbox_preflight(plan.package, deadline=deadline)
                probe = DockerProbeSandbox()
                identity = probe.preflight(deadline=deadline)
                require(identity["image_digest"] == plan.envelope["probe_image_digest"]
                        and identity["profile_hash"] == plan.envelope["probe_profile_hash"],
                        "probe identity mismatch")
            require(sandbox is not None and probe is not None, "registered backends required")
            for label in protocol.order:
                branches.append(protocol.initialize(plan, label, root, sandbox, probe, deadline))

            def adapter(config):
                nonlocal client
                if adapter_factory is not None:
                    return adapter_factory(config)
                if client is None:
                    key = load_exact_openai_api_key(credential_file)
                    client = native.requests.DiagnosticClient(api_key=key)
                    del key
                return OpenAIResponsesAdapter(config, api_key="", client=client)

            def report_progress(value):
                observer.append("diagnostic_branch_progress", value)
                progress(value)

            result = native.drive(
                plan, branches, adapter, branch_cap=protocol.branch_cap,
                total_cap=protocol.total_cap, checkpoint=checkpoint, progress=report_progress)
            result["operator_case_audits"] = []
            if result["terminal"] == "ROLLOUTS_COMPLETED":
                result["operator_case_audits"] = operator_audits(
                    plan, branches, probe, observer, store, deadline)
        except (Exception, KeyboardInterrupt, SystemExit) as exc:
            code = native.uncertainty(branches) or (
                exc.code if isinstance(exc, native.engine.AbortExperiment)
                else "LIMIT_REACHED" if isinstance(exc, ExecutionDeadlineExceeded)
                else "INTERRUPTED" if isinstance(exc, (KeyboardInterrupt, SystemExit))
                else "ROLLOUT_ERROR" if any(b.new_provider_calls for b in branches)
                else "PREFLIGHT_OR_INITIALIZATION_FAILED")
            for branch in branches:
                branch.finish(code, censored=True)
            result = {**(result or {}), **native.BOUNDARIES, "terminal": code,
                      "branches": [b.terminal for b in branches],
                      "recorded_cost_nanos": sum(b.new_cost_nanos for b in branches),
                      "provider_cost_known": code != "PROVIDER_TIMEOUT_OR_UNKNOWN",
                      "operator_case_audits": [e["payload"] for e in observer.events()
                                               if e["event_type"] == "operator_case_finished"]}
        finally:
            if client is not None:
                try:
                    client.close(timeout=native.requests.WAITS.client_cleanup_seconds)
                except (Exception, KeyboardInterrupt, SystemExit):
                    if result["terminal"] not in {
                        "PROVIDER_TIMEOUT_OR_UNKNOWN", "COUNT_TIMEOUT_OR_UNKNOWN",
                    }:
                        result["terminal"] = "CLIENT_CLEANUP_UNCONFIRMED"
        result.update(
            elapsed_ms=int((monotonic() - started) * 1000),
            provider_free=adapter_factory is not None,
            operator_execution_count=sum(e["event_type"] == "operator_case_started"
                                         for e in observer.events()),
            count_billing_and_invoice="UNVERIFIED",
        )
        observer.append("diagnostic_execution_finished", result)
        store.write_text_immutable(root / "result.json", canonical_json(result))
    return result


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
