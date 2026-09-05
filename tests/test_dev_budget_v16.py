from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import patchloop.dev.runner as runner
from patchloop.dev.contracts import DevLimits, DevToolResult, PublicTurnDecision, RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.tools import DevToolGateway
from patchloop.util import sha256_json


class PolicyGateway:
    def __init__(self):
        self.current_diff = SimpleNamespace(
            patch="diff --git a/source.py b/source.py\n", untracked_files=[],
            changed_files=["source.py"],
        )
        self.public_task = SimpleNamespace(
            visible_checks=[SimpleNamespace(id="first"), SimpleNamespace(id="second")],
        )
        self.accepted_mutations = 1
        self.anchor = True
        self.statuses = {"first": "PASS", "second": "PASS"}
        self.probe_sandbox = object()
        self.last_failed_mutation = None

    def has_current_mutation_evidence(self):
        return self.anchor

    def visible_check_status(self):
        return [{"check_id": check, "status": status} for check, status in self.statuses.items()]

    def remaining_visible_check_ids(self):
        return [check for check, status in self.statuses.items() if status != "PASS"]

    def unrun_visible_check_ids(self):
        return [check for check, status in self.statuses.items() if status == "NOT_RUN"]

    def ready_to_submit(self):
        return not self.remaining_visible_check_ids()


def _counters(limits, model_remaining, tool_remaining=100):
    return runner._RunCounters(
        model_calls=limits.max_model_calls - model_remaining,
        tool_actions=limits.max_tool_actions - tool_remaining,
        mutation_recovery_used=True,
    )


def _probe_result(status="failed"):
    return DevToolResult(
        action_id="diagnostic-probe", input_hash=sha256_json("diagnostic-probe"),
        tool="run_probe", status="succeeded", output={
            "status": status, "exit_code": int(status != "passed"),
            "stdout": "A public diagnostic observation.",
        },
    )


@pytest.mark.parametrize("probe_status", ["passed", "failed"])
def test_diagnostic_probe_leaves_minimum_edit_path_available(probe_status):
    gateway = PolicyGateway()
    limits = DevLimits()
    counters = _counters(limits, 9)
    before = runner._tool_policy(gateway, counters, limits)
    assert {"replace_text", "run_probe", "finish_task"} <= before.allowed_tools
    probe = _probe_result(probe_status)
    counters.model_calls += 1
    counters.tool_actions += 1
    runner._update_inspection_counters(counters, [probe])
    after = runner._tool_policy(gateway, counters, limits)
    assert after.workflow_gate == "ready_to_submit"
    assert after.minimum_completion_calls == after.completion_budget_calls == 1
    assert {"replace_text", "finish_task"} <= after.allowed_tools
    assert "run_check" not in after.allowed_tools
    assert not counters.failed_check_pending
    assert not counters.check_recovery_used_ids
    assert gateway.accepted_mutations == 1
    assert runner._mutation_completion_horizon(after) == {
        "minimum_calls": 4, "protected_calls": 12,
        "minimum_possible": True, "protected_possible": False,
        "recovery_warning": (
            "An edit, all checks, and finish fit if the edit succeeds; "
            "full failure-recovery reserves do not fit."
        ),
    }


@pytest.mark.parametrize(
    ("model_remaining", "tool_remaining", "accepted", "anchor", "untracked", "allowed"),
    [
        (4, 4, 1, True, False, True),
        (3, 4, 1, True, False, False),
        (4, 3, 1, True, False, False),
        (4, 4, 3, True, False, True),
        (4, 4, 4, True, False, False),
        (40, 100, 1, False, False, False),
        (40, 100, 1, True, True, False),
    ],
)
def test_optional_edit_uses_minimum_and_preserves_capacity_evidence_boundaries(
    model_remaining, tool_remaining, accepted, anchor, untracked, allowed,
):
    gateway = PolicyGateway()
    gateway.accepted_mutations = accepted
    gateway.anchor = anchor
    gateway.current_diff.untracked_files = ["new.py"] if untracked else []
    limits = DevLimits()
    policy = runner._tool_policy(
        gateway, _counters(limits, model_remaining, tool_remaining), limits,
    )
    assert ("replace_text" in policy.allowed_tools) is allowed
    assert policy.mutation_completion_possible is allowed
    assert policy.optional_mutation_completion_calls == 4
    if not allowed:
        assert runner._mutation_completion_horizon(policy)["recovery_warning"] is None


@pytest.mark.parametrize("remaining, protected", [(11, False), (12, True)])
def test_edit_recovery_protection_is_separate_from_current_baseline(remaining, protected):
    limits = DevLimits()
    policy = runner._tool_policy(PolicyGateway(), _counters(limits, remaining), limits)
    assert policy.protected_completion_possible is True  # Existing checked diff can finish.
    assert policy.mutation_completion_possible is True
    assert policy.mutation_protected_completion_possible is protected
    assert bool(runner._mutation_completion_horizon(policy)["recovery_warning"]) is not protected


def test_optional_inspection_and_probe_still_preserve_protected_check_path():
    gateway = PolicyGateway()
    gateway.statuses = {"first": "NOT_RUN", "second": "NOT_RUN"}
    limits = DevLimits()
    floor = runner._tool_policy(gateway, _counters(limits, 11), limits)
    assert floor.minimum_completion_calls == 3
    assert floor.completion_budget_calls == 11
    assert floor.allowed_tools == {"replace_text", "run_check", "stop_task"}
    spare = runner._tool_policy(gateway, _counters(limits, 12), limits)
    assert {"read_file", "search_files", "run_probe"} <= spare.allowed_tools
    assert spare.exploration_state == "last_opportunity"


@pytest.mark.parametrize("failure_class", ["anchor_invalid", "evidence_invalid"])
def test_anchor_attempt_feedback_does_not_require_one_targeted_read(failure_class):
    gateway = PolicyGateway()
    failure = DevToolResult(
        action_id="bad-anchor", input_hash=sha256_json("bad-anchor"), tool="replace_text",
        status="failed", output={"mutation_failure": {"class": failure_class}},
    )
    card = runner._attempt_card(failure, gateway)
    assert "already delivered exact evidence" in card["next_question"]
    assert "missing exact evidence while allowed" in card["next_question"]
    assert "targeted" not in card["next_question"]
    assert "one " not in card["next_question"]
    gateway.last_failed_mutation = failure.output
    policy = runner._tool_policy(gateway, runner._RunCounters(), DevLimits())
    assert {"replace_text", "read_file", "search_files", "finish_task"} <= policy.allowed_tools


def _replacement(action_id, old_text, new_text):
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    return RequestedTool(
        name="replace_text", action_id=action_id, arguments={
            "path": mutation.path, "old_text": old_text, "new_text": new_text,
            "occurrence": 1, "hypothesis": mutation.hypothesis,
            "expected_behavior": mutation.expected_behavior, "causal_revision": None,
        },
        turn_decision=PublicTurnDecision(mode="mutate", basis="Use observed exact source."),
    )


def test_unprotected_edit_context_restart_and_actual_check_invalidation(gateway_factory):
    gateway, journal, _ = gateway_factory()
    first_check = gateway.public_task.visible_checks[0]
    gateway.public_task = gateway.public_task.model_copy(update={
        "visible_checks": [first_check, first_check.model_copy(update={"id": "second-check"})],
    })
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    gateway.execute(RequestedTool(
        name="read_file", action_id="source", arguments={
            "path": mutation.path, "start_line": 1, "end_line": 80,
        },
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Read public source.", evidence_goal="Acquire exact source.",
        ),
    ))
    assert gateway.execute(_replacement(
        "initial-edit", mutation.old_text, mutation.new_text,
    )).status == "succeeded"
    baseline_hash = gateway.current_diff_hash
    for check in gateway.public_task.visible_checks:
        output = {"check_id": check.id, "diff_hash": baseline_hash, "passed": True}
        result = DevToolResult(
            action_id=f"check-{check.id}", input_hash=sha256_json(check.id),
            tool="run_check", status="succeeded", output=output,
        )
        journal.append("action_finished", {"result": result.model_dump(mode="json")})
        gateway._remember_check(output)
    assert gateway.ready_to_submit()
    # Count only synthetic dispatch/batch events; no provider or probe executes.
    rejection = DevToolResult(
        action_id="rejected", input_hash=sha256_json("rejected"),
        tool="replace_text", status="failed",
    )
    for result in [rejection, _probe_result()]:
        turn_id = f"turn-{result.action_id}"
        journal.append("model_call_finished", {"turn_id": turn_id})
        journal.append("tool_batch_started", {"turn_id": turn_id, "tool_calls": [{}]})
        journal.append("action_finished", {"result": result.model_dump(mode="json")})
        journal.append("tool_batch_finished", {
            "turn_id": turn_id, "action_ids": [result.action_id],
        })
    limits = DevLimits(max_model_calls=10)
    counters = runner._restore_counters(journal)
    assert counters.model_calls == counters.tool_actions == 2
    policy = runner._tool_policy(gateway, counters, limits)
    assert policy.mutation_completion_possible
    assert not policy.mutation_protected_completion_possible
    context = json.loads(runner._build_context(
        package=SimpleNamespace(public=gateway.public_task), gateway=gateway,
        journal=journal, correction=None,
        latest_tool_results=[], counters=counters, elapsed_seconds=0, limits=limits,
    ))
    horizon = context["action_horizon"]["mutation_completion_horizon"]
    journal.append("turn_started", {
        "turn_id": "turn-after-probe", "mutation_completion_horizon": horizon,
    })
    before = journal.path.read_bytes()
    restarted = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=gateway.sandbox,
        journal=journal, limits=limits,
    )
    restored_context = json.loads(runner._build_context(
        package=SimpleNamespace(public=gateway.public_task), gateway=restarted,
        journal=journal, correction=None,
        latest_tool_results=[], counters=runner._restore_counters(journal),
        elapsed_seconds=0, limits=limits,
    ))
    assert restored_context["action_horizon"]["mutation_completion_horizon"] == horizon
    assert journal.events()[-1]["payload"]["mutation_completion_horizon"] == horizon
    assert journal.path.read_bytes() == before
    old = '    return list(csv.reader(io.StringIO(text, newline="")))'
    new = old + "  # Preserve stream parsing."
    assert restarted.execute(_replacement("optional-edit", old, new)).status == "succeeded"
    assert restarted.current_diff_hash != baseline_hash
    assert restarted.accepted_mutations == 2
    assert not restarted.ready_to_submit()
    assert [row["status"] for row in restarted.visible_check_status()] == ["NOT_RUN", "NOT_RUN"]
    assert len(restarted.remaining_visible_check_ids()) == 2
