"""Characterize admission versus semantic review with real, public local checks.

This is a scripted CSV fixture, not a model-quality experiment or a replay of a
pyfakefs proposal. It deliberately keeps two mistakes in one sequential check.
"""

from __future__ import annotations

import json
import sys

from patchloop.contracts import RegisteredCheck
from patchloop.dev import runner
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.tools import DevToolGateway


def test_admission_is_not_semantic_review_and_feedback_repairs_need_no_reread(
    gateway_factory, smoke_package, record_property,
):
    gateway, journal, workspace = gateway_factory()
    source = MOCK_MUTATIONS["csv-quoted-newline"]
    check_source = (
        "from mini_data_utils.csvlite import parse_rows\n"
        "print('case:simple', flush=True)\n"
        "assert parse_rows('a,b\\n') == [['a', 'b']], 'simple CSV record'\n"
        "print('case:multiline', flush=True)\n"
        "assert parse_rows('\"a\\nb\",c\\n') == [['a\\nb', 'c']], 'quoted newline'\n"
        "print('case:done', flush=True)\n"
    )
    check = RegisteredCheck(
        id="two-public-behaviors", command=[sys.executable, "-c", check_source],
        timeout_seconds=10,
    )
    # Change only this test's in-memory public declaration, never a task package.
    public = smoke_package.public.model_copy(update={"visible_checks": [check]})
    package = smoke_package.model_copy(update={"public": public})
    gateway.public_task = public
    counters = runner._RunCounters()
    trace = []

    def context(latest):
        return json.loads(runner._build_context(
            package=package, gateway=gateway, journal=journal, correction=None,
            latest_tool_results=[latest], counters=counters, elapsed_seconds=0,
            limits=gateway.limits,
        ))

    def execute(name, action_id, arguments, mode):
        call = RequestedTool(
            name=name, action_id=action_id, arguments=arguments,
            turn_decision=PublicTurnDecision(
                mode=mode, basis="Scripted public workflow characterization, not model output.",
                evidence_goal="Read the exact editable parser." if mode == "inspect" else None,
            ),
        )
        result = gateway.execute(call)
        counters.tool_actions += 1
        assert result.status == "succeeded", result.message
        return result

    execute("read_file", "source", {
        "path": source.path, "start_line": 1, "end_line": 80,
    }, "inspect")
    assert gateway.working_notes()["findings"] == []

    def mutate(action_id, old, new):
        before_checks = sum(
            event["event_type"] == "action_finished"
            and event["payload"]["result"]["tool"] == "run_check"
            for event in journal.events()
        )
        result = execute("replace_text", action_id, {
            "path": source.path, "old_text": old, "new_text": new, "occurrence": 1,
            "hypothesis": "One parser should preserve simple and multiline records.",
            # Intentionally identical for wrong and correct candidates. Prose is not proof.
            "expected_behavior": "Both public CSV examples return the expected records.",
            "causal_revision": None,
        }, "mutate")
        state = context(result)
        assert state["workflow_gate"] == "needs_visible_checks"
        assert state["visible_check_status"][0]["status"] == "NOT_RUN"
        assert "run_check" in state["available_tool_names"]
        assert "finish_task" not in state["available_tool_names"]
        assert sum(
            event["event_type"] == "action_finished"
            and event["payload"]["result"]["tool"] == "run_check"
            for event in journal.events()
        ) == before_checks  # Mutation admission does not silently execute a review/check.
        assert not gateway.ready_to_submit()
        trace.append({
            "action_id": action_id, "mutation_admitted": True,
            "accepted_mutations": gateway.accepted_mutations,
            "diff_hash": result.workspace_diff_hash, "semantic_verdict": "NOT_RUN",
        })
        return result

    def run_check(action_id, *, failed_line, output):
        result = execute("run_check", action_id, {"check_id": check.id}, "verify")
        assert result.output["stdout"].splitlines() == output
        assert result.output["passed"] is (failed_line is None)
        state = context(result)
        failure = state["current_public_failure"]
        if failed_line is not None:
            assert failure["public_location"]["line"] == failed_line
            assert failure["public_location"]["statement"] == (
                check_source.splitlines()[failed_line - 1]
            )
            assert failure["evidence_currency"] == "current"
            # Do not infer generic coverage from one traceback. Markers above are
            # fixture-specific execution evidence, not a new production inference.
            assert failure["execution_boundary"]["later_source_lines_observed"] is None
            assert {"read_file", "search_files", "replace_text"}.issubset(
                state["available_tool_names"]
            )
            assert "finish_task" not in state["available_tool_names"]
            assert state["action_horizon"]["required_inspection_for_completion"] is False
        else:
            assert failure is None
            assert "finish_task" in state["available_tool_names"]
        trace.append({
            "action_id": action_id, "passed": result.output["passed"],
            "diff_hash": result.workspace_diff_hash, "stdout": output,
            "mapped_public_line": failed_line,
        })
        return result

    parser_line = "rows.extend(csv.reader([physical_line]))"
    mutate("wrong-candidate", parser_line, "pass")
    first = run_check("first-failure", failed_line=3, output=["case:simple"])
    assert "case:multiline" not in first.output["stdout"]

    # Reconstruct from the actual journal before the first repair. A failed check
    # and empty optional notes do not require a new read or a different hypothesis.
    gateway = DevToolGateway(
        workspace=workspace, public_task=public, sandbox=gateway.sandbox,
        journal=journal, limits=gateway.limits,
    )
    assert context(first)["current_public_failure"]["public_location"]["line"] == 3
    partial_line = "rows.extend(csv.reader([physical_line.strip()]))"
    mutate("partial-repair", "        pass", "        " + partial_line)
    run_check("second-failure", failed_line=5, output=["case:simple", "case:multiline"])

    # The later public assertion was always declared, but only runs after the
    # earlier defect is fixed. It does not become a newly invented requirement.
    mutate("complete-repair", source.old_text.replace(parser_line, partial_line), source.new_text)
    passed = run_check(
        "verified-repair", failed_line=None,
        output=["case:simple", "case:multiline", "case:done"],
    )
    finish = execute("finish_task", "finish", {}, "finish")
    assert finish.output["patch_hash"] == passed.output["diff_hash"]
    assert gateway.accepted_mutations == 3
    assert gateway.working_notes()["verification"]["unresolved_ids"] == []
    finished = [event["payload"]["result"] for event in journal.events()
                if event["event_type"] == "action_finished"]
    assert [result["tool"] for result in finished] == [
        "read_file", "replace_text", "run_check", "replace_text", "run_check",
        "replace_text", "run_check", "finish_task",
    ]
    record_property("public_workflow_trace", json.dumps(trace, sort_keys=True))
    record_property("evidence_boundary", "scripted local CSV; no model, pyfakefs or evaluator run")
