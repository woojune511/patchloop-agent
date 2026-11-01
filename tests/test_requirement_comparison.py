"""A changed plan cannot silently consume the helper/original-condition review."""
from __future__ import annotations

import copy

import pytest
from test_scope_review import CURRENT, OTHER, observed, review, selected
from test_semantic_review_focus import mutation

from patchloop.dev import completion_context, scope_review, working_plan
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes, sha256_json

ISSUE = {"title": "Quoted newline changes a record",
         "description": "read_rows(text) must preserve quoted newlines.\r\n"
                        "Plain unquoted input already works."}
QUOTE = "read_rows(text) must preserve quoted newlines."


def helper(journal, action="helper", *, diff=CURRENT, replay=None, partial=False):
    source = "print(read_rows(['a', 'b']))"
    question = "Does a list-input helper preserve its items?"
    arguments = ({"replay_action_id": replay, "question": None, "python_source": None}
                 if replay else {"question": question, "python_source": source,
                                 "purpose": {"kind": "helper"}})
    identity = {"action_id": action, "tool": "run_probe",
                "input_hash": sha256_json({"tool": "run_probe", "arguments": arguments})}
    start = {**identity, "arguments": arguments, "baseline_diff_hash": diff}
    if replay:
        start["probe_replay_request"] = {
            "question": question, "python_source": source,
            "replayed_from": {"action_id": replay},
        }
    journal.append("action_started", start)
    result = {**identity, "status": "succeeded", "workspace_diff_hash": diff,
              "output": {"diff_hash": diff, "question": question,
                         "source_hash": sha256_bytes(source.encode()),
                         "status": "timeout" if partial else "passed",
                         "timed_out": partial, "exit_code": None if partial else 0,
                         "stdout": "helper result, not the reported input",
                         "execution_policy": {"cleanup_status": "confirmed"}}}
    journal.append("action_finished", {"result": result})
    return result


def put(journal, turn, *, scope=None, plan=None, diff=CURRENT):
    return working_plan.record(
        journal, [selected(scope, plan=plan)], turn_id=turn,
        diff_hash=diff, gate="ready_to_submit", public_issue=ISSUE,
    )


def view(journal, *, diff=CURRENT, issue=ISSUE):
    return working_plan.project(journal.events(), diff_hash=diff, gate="ready_to_submit",
                                public_issue=issue)


def scoped(action="helper", quote=QUOTE):
    value = review(evidence=action, sources=[])
    value["cases"][0]["input"] = {
        "public_conditions": quote, "case_conditions": "read_rows(['a', 'b'])",
    }
    value["cases"][0]["interpretation"] = (
        "The helper used a list, not the reported text. Inspect the producing caller next."
    )
    return value


@pytest.fixture
def journal(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_requirementcomparison")
    put(journal, "initial", plan="Inspect the public caller and its conversion.")
    helper(journal)
    return journal


def test_null_review_and_rewritten_plan_do_not_consume_original_comparison(journal):
    before = view(journal)["review_request"]["requirement_comparison"]
    put(journal, "changed-plan", plan="Repair list-like input and finish when it works.")
    put(journal, "next-action")
    after = view(journal)
    assert after["plan"]["text"] == "Repair list-like input and finish when it works."
    assert after["review_request"]["requested"]
    assert after["review_request"]["requirement_comparison"] == before
    assert before["task_reference"] == {
        "source": "public_task.issue", "issue_hash": sha256_json(ISSUE),
    }
    assert before["status"] == "review_needed"
    reopened = DevJournal(journal.root, journal.run_id)
    assert view(reopened) == after


def test_literal_task_quote_and_execution_bind_review_without_certifying_fit(journal):
    result = put(journal, "review", scope=scoped())
    assert result["scope_review"]["status"] == "applied"
    state = view(journal)
    assert state["review_request"]["requirement_comparison"]["status"] == "review_recorded"
    assert state["review_request"]["requirement_comparison"]["requirement_fit"] == "not_certified"
    assert "recorded_review" not in state["review_request"]["requirement_comparison"]
    saved = copy.deepcopy(state["plan"]["scope_review"])
    assert saved["cases"][0]["public_condition_binding"]["source"] == (
        "public_task.issue.description")
    assert saved["cases"][0]["input"]["public_conditions"] == QUOTE
    assert saved["coverage_status"] == "not_certified"
    put(journal, "later-plan", plan="Inspect upstream conversion before selecting a target.")
    assert view(journal)["plan"]["scope_review"] == saved
    before = journal.path.read_bytes()
    assert put(journal, "review", scope=scoped()) == result
    assert journal.path.read_bytes() == before


def test_helper_paraphrase_cannot_replace_literal_public_conditions(journal):
    result = put(journal, "bad", scope=scoped(quote="read_rows accepts list-like data."),
                 plan="Explore a new hypothesis.")
    assert result["status"] == "updated"  # Annotation failure does not reject the action/plan.
    assert result["scope_review"]["diagnostics"] == [
        "scope_review_public_conditions_must_quote_public_task_issue",
    ]
    assert "scope_review" not in view(journal)["plan"]
    assert view(journal)["review_request"]["requirement_comparison"]["status"] == "review_needed"


@pytest.mark.parametrize("kind", ["legacy", "control", "wrong_execution"])
def test_unbound_or_other_case_does_not_consume_helper_comparison(journal, kind):
    helper(journal, "newest")
    raw = scoped(action="helper" if kind == "wrong_execution" else "newest")
    if kind == "legacy":
        raw["cases"][0]["input"] = "legacy model-authored case description"
    elif kind == "control":
        raw["cases"][0]["input"]["public_conditions"] = None
    assert put(journal, kind, scope=raw)["scope_review"]["status"] == "applied"
    assert view(journal)["review_request"]["requirement_comparison"]["status"] == "review_needed"


def test_line_endings_and_source_change_do_not_forge_requirement_binding(journal):
    quote = ISSUE["description"].replace("\r\n", "\n")
    assert put(journal, "line-endings", scope=scoped(quote=quote))["scope_review"]["status"] == (
        "applied")
    changed = {**ISSUE, "description": "A different public task."}
    assert view(journal, issue=changed)["review_request"]["requirement_comparison"]["status"] == (
        "review_needed")


def test_replay_keeps_base_counterevidence_and_requires_its_own_review(journal):
    put(journal, "review-base", scope=scoped())
    helper(journal, "candidate", diff=OTHER, replay="helper")
    current = view(journal, diff=OTHER)
    comparison = current["review_request"]["requirement_comparison"]
    assert comparison["observation_action_ids"] == ["helper", "candidate"]
    assert comparison["status"] == "review_needed"
    assert current["plan"]["scope_review"]["cases"][0]["execution"]["currency"] == "historical"
    assert put(journal, "review-candidate", scope=scoped("candidate"), diff=OTHER)[
        "scope_review"]["status"] == "applied"


def test_partial_execution_can_be_reviewed_but_remains_partial_not_coverage(journal):
    helper(journal, "partial", partial=True)
    assert put(journal, "partial-review", scope=scoped("partial"))["scope_review"]["status"] == (
        "applied")
    state = view(journal)
    assert state["review_request"]["requirement_comparison"]["status"] == "review_recorded"
    case = state["plan"]["scope_review"]["cases"][0]
    assert case["execution"]["observation"]["timed_out"]
    assert state["plan"]["scope_review"]["coverage_status"] == "not_certified"


def test_completion_keeps_compared_historical_result_without_changing_authority(journal):
    helper(journal, "candidate", diff=OTHER, replay="helper")
    plan = view(journal, diff=OTHER)
    state = {"workflow_gate": "ready_to_submit", "current_diff": {"patch_hash": OTHER},
             "public_task": {"issue": ISSUE}, "remaining_budget": {"model_calls": 3},
             "available_tool_names": ["finish_task", "read_file", "run_probe"],
             "working_plan": plan, "recent_probes": [
                 {"action_id": "helper", "diff_hash": CURRENT, "historical": True,
                  "stdout": "base control also failed", "program": {"python_source": "case()"}},
                 {"action_id": "candidate", "diff_hash": OTHER, "historical": False,
                  "stdout": "changed helper passed", "program": {"python_source": "case()"}},
             ]}
    actual = completion_context.project(state)
    for key in ("public_task", "remaining_budget", "available_tool_names", "workflow_gate"):
        assert actual[key] == state[key]
    assert actual["recent_probes"] == state["recent_probes"]
    assert actual["recent_probes"][0]["historical"]


def test_missing_or_unbound_helper_never_gets_invented_program(journal):
    events = journal.events()
    bad = copy.deepcopy(events)
    bad[-1]["payload"]["result"]["output"]["source_hash"] = "wrong"
    assert scope_review.helper_comparison(bad, public_issue=ISSUE, review=None) is None
    assert scope_review.helper_comparison([], public_issue=ISSUE, review=None) is None


@pytest.mark.parametrize("partial", [False, True])
def test_helper_review_after_edit_keeps_historical_execution_without_replay(journal, partial):
    if partial:
        helper(journal, "helper-partial", partial=True)
    action = "helper-partial" if partial else "helper"
    mutation(journal, baseline=CURRENT, current=OTHER)
    assert view(journal, diff=OTHER)["review_request"]["requirement_comparison"][
        "status"] == "review_needed"
    result = put(journal, "after-edit", scope=scoped(action), diff=OTHER)
    assert result["scope_review"]["status"] == "applied"
    state = view(journal, diff=OTHER)
    comparison = state["review_request"]["requirement_comparison"]
    assert comparison["status"] == "review_recorded"
    assert comparison["diff_hash"] == CURRENT
    assert comparison["requirement_fit"] == "not_certified"
    stored = state["plan"]["scope_review"]
    assert stored["diff_hash"] == OTHER  # The review was written after the edit.
    assert stored["coverage_status"] == "not_certified"
    execution = stored["cases"][0]["execution"]
    assert execution["diff_hash"] == CURRENT and execution["currency"] == "historical"
    assert execution["observation"]["timed_out"] is partial
    reopened = DevJournal(journal.root, journal.run_id)
    assert view(reopened, diff=OTHER) == state
    assert working_plan.submission_review(reopened.events(), OTHER)["plan"][
        "scope_review"]["cases"][0]["execution"] == execution


def test_replay_comparison_accepts_both_actual_diff_receipts(journal):
    helper(journal, "candidate", diff=OTHER, replay="helper")
    raw = scoped("candidate")
    raw["cases"].insert(0, scoped("helper")["cases"][0])
    assert put(journal, "compare", scope=raw, diff=OTHER)["scope_review"]["status"] == "applied"
    state = view(journal, diff=OTHER)
    assert state["review_request"]["requirement_comparison"]["status"] == "review_recorded"
    cases = state["plan"]["scope_review"]["cases"]
    assert [(c["execution"]["diff_hash"], c["execution"]["currency"]) for c in cases] == [
        (CURRENT, "historical"), (OTHER, "current"),
    ]


@pytest.mark.parametrize("kind", ["unrelated_helper", "run_check", "run_tests", "original"])
def test_historical_exception_does_not_admit_other_old_results(journal, kind):
    if kind == "unrelated_helper":
        helper(journal, "newest", diff=OTHER)
        events, action = journal.events(), "helper"
    elif kind == "original":
        events, action = journal.events(), "helper"
        events[-1]["payload"]["result"]["output"]["reproduction"] = {"status": "unverified"}
    else:
        observed(journal, kind, tool=kind)
        events, action = journal.events(), kind
    value, error = scope_review.parse(scoped(action), events=events, diff_hash=OTHER,
                                     turn_id="historical", public_issue=ISSUE)
    assert value is None and error == "scope_review_execution_not_current"


@pytest.mark.parametrize("kind", ["null_quote", "legacy", "missing_start", "bad_source"])
def test_historical_helper_requires_quote_and_bound_program(journal, kind):
    events, raw = journal.events(), scoped()
    if kind == "null_quote":
        raw["cases"][0]["input"]["public_conditions"] = None
    elif kind == "legacy":
        raw["cases"][0]["input"] = QUOTE
    elif kind == "missing_start":
        events = [e for e in events if e["event_type"] != "action_started"]
    else:
        events[-1]["payload"]["result"]["output"]["source_hash"] = "wrong"
    value, error = scope_review.parse(raw, events=events, diff_hash=OTHER, turn_id="historical",
                                     public_issue=ISSUE)
    assert value is None and error == "scope_review_execution_not_current"


def test_later_unrelated_review_does_not_reopen_recorded_helper(journal):
    assert put(journal, "helper-review", scope=scoped())["scope_review"]["status"] == "applied"
    updated = scoped()
    updated["cases"][0]["interpretation"] = "Revised interpretation: inspect the text caller next."
    assert put(journal, "revised-helper-review", scope=updated)[
        "scope_review"]["status"] == "applied"
    recorded = view(journal)["review_request"]["requirement_comparison"]
    assert recorded["status"] == "review_recorded"
    observed(journal, "public-check", tool="run_check", output={"passed": True})
    assert put(journal, "check-review", scope=scoped("public-check"))[
        "scope_review"]["status"] == "applied"
    state = view(journal)
    assert state["plan"]["scope_review"]["cases"][0]["execution"][
        "action_id"] == "public-check"
    comparison = state["review_request"]["requirement_comparison"]
    assert {k: v for k, v in comparison.items() if k != "recorded_review"} == recorded
    saved = comparison["recorded_review"]
    assert saved["turn_id"] == "revised-helper-review"
    assert saved["case"]["interpretation"] == updated["cases"][0]["interpretation"]
    assert saved["case"]["execution"]["currency"] == "current"
    completion = completion_context.project({
        "workflow_gate": "ready_to_submit", "current_diff": {"patch_hash": CURRENT},
        "working_plan": state,
    })
    assert completion["working_plan"]["review_request"]["requirement_comparison"] == comparison
    reopened = DevJournal(journal.root, journal.run_id)
    assert view(reopened) == state
    historical = view(reopened, diff=OTHER)["review_request"]["requirement_comparison"]
    assert historical["status"] == "review_recorded"
    assert historical["recorded_review"]["case"]["execution"]["currency"] == "historical"
    changed = {**ISSUE, "description": "A different public issue."}
    assert view(reopened, issue=changed)["review_request"]["requirement_comparison"][
        "status"] == "review_needed"
    helper(reopened, "new-helper")
    assert view(reopened)["review_request"]["requirement_comparison"][
        "status"] == "review_needed"


@pytest.mark.parametrize("field", ["input_hash", "diff_hash"])
def test_journal_review_cannot_acknowledge_another_execution_identity(journal, field):
    put(journal, "helper-review", scope=scoped())
    events = journal.events()
    events[-1]["payload"]["plan"]["scope_review"]["cases"][0]["execution"][field] = "wrong"
    comparison = scope_review.helper_comparison(events, public_issue=ISSUE, review=None)
    assert comparison["status"] == "review_needed"
