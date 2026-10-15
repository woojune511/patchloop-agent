"""Restore the frozen isort prefix and bind existing operator observations.

No model, diagnostic, check or evaluator is executed here. This experiment seam
does not change production policy or any historical record.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import observation_exposure as exposure
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source
from diagnostics.uptake_checkpoint import read_bound
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.util import sha256_bytes

DESIGN = Path("C:/pt/isortuptakeplan01/design-packet.json")
DESIGN_HASH = "sha256:ec67d8bc09b046ad5e6452390eab1da6cdcf7cfc132f962179f85899e6bdb186"
FIELD = "operator_public_observation"


def accepted_edits(events):
    return sum(
        e["event_type"] == "action_finished"
        and e["payload"]["result"]["tool"] == "replace_text"
        and e["payload"]["result"]["status"] == "succeeded"
        and not e["payload"]["result"].get("error_code")
        for e in events
    )


def load_design(path=DESIGN):
    packet = json.loads(read_bound({"path": str(path), "content_hash": DESIGN_HASH}))
    plan = json.loads(read_bound(packet["plan"]))
    read_bound(packet["cap_application"])
    bindings = json.loads(read_bound(plan["bindings"]))
    for name, digest in bindings["input_hashes"].items():
        read_bound({"path": name, "content_hash": digest})
    for name in ("grading", "feedback", "terminal_public_oracle"):
        read_bound(plan[name])
    require(runner._runtime_hash() == bindings["runtime_hash"], "frozen runtime changed")
    inherited = plan["inheritance"]
    parent = DevJournal(Path(inherited["root"]), inherited["run_id"])
    prefix = [e for e in parent.events() if e["sequence"] < inherited["prepared_cut_sequence"]]
    require(
        prefix[-1]["event_hash"] == inherited["prefix_hash"]
        and prefix[-1]["sequence"] == inherited["prefix_last_sequence"]
        and accepted_edits(prefix) == inherited["accepted_edits_used"],
        "frozen prefix changed",
    )
    counters = runner._restore_counters(SimpleNamespace(events=lambda: prefix))
    require(
        counters.model_calls == inherited["model_calls_used"]
        and counters.tool_actions == inherited["tool_actions_used"],
        "frozen counters changed",
    )
    source = Source(
        parent.root,
        parent.run_id,
        sha256_bytes(parent.path.read_bytes()),
        sha256_bytes(parent.envelope_path.read_bytes()),
        Path(plan["task_path"]),
        sha256_bytes(Path(plan["task_path"]).read_bytes()),
    )
    return plan, source, json.loads(read_bound(plan["feedback"]))


def verify_feedback(feedback, branch):
    """Validate currency and complete receipts, without re-running their program."""
    require(
        feedback["origin"] == "operator_executed_public_diagnostic"
        and feedback["model_authored"] is False
        and feedback["current_snapshot_label"] == "submitted"
        and sha256_bytes(feedback["python_source"].encode()) == feedback["program_hash"],
        "operator observation provenance/program changed",
    )
    require(
        WorkspaceManager.diff_summary(branch.workspace, deadline=branch.solver_deadline).patch_hash
        == feedback["observed_on_current_diff_hash"],
        "operator observation is not on the restored candidate",
    )
    snapshots = feedback["snapshots"]
    require([s["label"] for s in snapshots] == ["base", "submitted"], "both receipts required")
    require(
        snapshots[1]["observed_on_diff_hash"] == feedback["observed_on_current_diff_hash"],
        "submitted receipt currency differs",
    )
    for snapshot in snapshots:
        receipt = snapshot["receipt"]
        require(
            receipt["source_hash"] == feedback["program_hash"]
            and receipt["image_digest"] == branch.envelope.probe_image_digest
            and receipt["profile_hash"] == branch.envelope.probe_profile_hash
            and receipt["setup_checks"]["status"] == "passed"
            and receipt["status"] in {"passed", "failed"}
            and isinstance(receipt["stdout"], str)
            and isinstance(receipt["stderr"], str)
            and not any(
                receipt[k]
                for k in ("cleanup_failed", "deadline_exhausted", "timed_out", "truncated")
            ),
            "incomplete or incompatible operator receipt",
        )


def restore_branch(
    source,
    cut_sequence,
    feedback,
    output,
    *,
    provider_free=True,
    credential_file=None,
    started=None,
    clock=monotonic,
    deadline=None,
):
    started = clock() if started is None else started
    parent = DevJournal(source.root, source.run_id)
    events, old = parent.events(), parent.load_envelope()
    cut = next(e for e in events if e["sequence"] == cut_sequence)
    bundle = json.loads(
        ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(cut["payload"]["artifact"])
        )
    )
    prefix = [e for e in events if e["sequence"] < cut_sequence]
    counters = runner._restore_counters(SimpleNamespace(events=lambda: prefix))
    base_ms, edits = bundle["turn"]["active_elapsed_ms"], accepted_edits(prefix)
    solver_end = started + min(281, old.limits.wall_time_seconds - base_ms / 1000)
    require(clock() < solver_end, "inherited solver time exhausted before restoration")
    limits = old.limits.model_copy(
        update={
            "max_model_calls": min(old.limits.max_model_calls, counters.model_calls + 6),
            "max_tool_actions": min(old.limits.max_tool_actions, counters.tool_actions + 18),
            "max_accepted_mutations": min(old.limits.max_accepted_mutations, edits + 2),
            "max_protocol_recoveries": 0,
        }
    )

    def request(**kwargs):
        return DevRunRequest(
            **{
                **kwargs,
                "agent_policy": old.agent_policy,
                "limits": limits,
                # Terminal assessment has separate 30/330s phase limits inside 720s.
                # Subtracting a 330s reserve from 281s would prevent all solver work.
                "evaluation_reserve_seconds": 0,
            }
        )

    class PreparationDeadline:
        @staticmethod
        def from_remaining(seconds):
            return ExecutionDeadline(
                min(clock() + seconds, solver_end, deadline.expires_at if deadline else solver_end),
                clock,
            )

    with (
        patch.object(exposure, "DevRunRequest", request),
        patch.object(exposure, "ExecutionDeadline", PreparationDeadline),
    ):
        branch = exposure._fork(
            source,
            cut_sequence,
            output,
            "B",
            new_cap_usd=Decimal("3.50"),
            mode="offline-scripted-only" if provider_free else "funded-observation",
            env_file=output / "NO_CREDENTIAL_FILE" if provider_free else credential_file,
            preserve_parent_configuration=True,
        )
    require(
        branch.envelope.probe_image_digest == old.probe_image_digest
        and branch.envelope.probe_dependencies == old.probe_dependencies,
        "inherited image/dependencies changed",
    )
    branch.solver_deadline = ExecutionDeadline(solver_end, clock)
    branch.solver_deadline.check()
    verify_feedback(feedback, branch)  # Current profile is bound by the new operator receipts.
    branch.feedback, branch.selected = feedback, bundle["request"]
    branch.parent_actions, branch.parent_edits = counters.tool_actions, edits
    branch.row, branch.provider_free = {"cell": "I1"}, provider_free
    branch.journal.append(
        "isort_uptake_checkpoint_restored",
        {
            "row": "I1",
            "cut_sequence": cut_sequence,
            "synthetic_transport": provider_free,
            "operator_feedback": branch.store.put_json(feedback).model_dump(mode="json"),
            "candidate_hash": feedback["observed_on_current_diff_hash"],
            "active_elapsed_ms": base_ms + int((clock() - started) * 1000),
            "new_seed_executions": 0,
        },
    )
    return branch
