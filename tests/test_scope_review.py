"""Scope annotations bind public observations without certifying case coverage."""

from __future__ import annotations

import copy
import json

import pytest

from patchloop.dev import scope_review
from patchloop.dev import working_plan as plans
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import validate_tool_batch
from patchloop.util import sha256_json

CURRENT = "sha256:" + "a" * 64
OTHER = "sha256:" + "b" * 64
ABSENT = object()


def selected(review=ABSENT, *, action="inspect", plan=None, tool="read_file"):
    fields = dict(mode="inspect" if tool == "read_file" else "verify",
                  basis="Review the public mode registry and observed caller output.",
                  evidence_goal=("Identify an uncovered public mode."
                                 if tool == "read_file" else None),
                  plan_update=plan, plan_update_reason="Keep unresolved mode checks in scope.")
    if review is not ABSENT:
        fields["scope_review"] = review
    return RequestedTool(name=tool, action_id=action, arguments={},
                         turn_decision=PublicTurnDecision(**fields))


def record(journal, review=ABSENT, *, turn="review", plan=None, diff=CURRENT, calls=None):
    return plans.record(journal, calls or [selected(review, plan=plan)], turn_id=turn,
                        diff_hash=diff, gate="ready_to_submit")


def view(journal, diff=CURRENT):
    return plans.project(journal.events(), diff_hash=diff, gate="ready_to_submit")


def retained(journal, diff=CURRENT):
    return view(journal, diff)["plan"]["scope_review"]


def observed(journal, action="source", *, tool="read_file", diff=CURRENT,
             output_diff=None, status="succeeded", output=None, finish=True, input_hash=True):
    identity = {"action_id": action, "input_hash": sha256_json(action) if input_hash else "",
                "tool": tool}
    journal.append("action_started", {**identity, "arguments": {}, "baseline_diff_hash": diff})
    if finish:
        journal.append("action_finished", {"result": {
            **identity, "status": status, "workspace_diff_hash": diff,
            "output": {"diff_hash": output_diff or diff, **(output or {})},
        }})
    return identity


def review(*, disposition="executed", evidence="check", sources=None, scope="Public modes"):
    return {"scope": scope, "source_action_ids": ["source"] if sources is None else sources,
            "cases": [{"input": "public_call(mode='strict', item='valid')",
                       "expected_observation": "Returned identifier equals the input identifier.",
                       "disposition": disposition, "evidence_action_id": evidence,
                       "interpretation": "One member observed; other modes remain open."}]}


@pytest.fixture
def journal(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_scopereview")
    record(journal, turn="initial", plan="Inspect public modes and test the original caller.")
    observed(journal, output={"spans": [
        {"path": "public.py", "content": "MODES = ('strict', 'fast')"},
    ]})
    return journal


@pytest.mark.parametrize("tool", ["run_check", "run_tests", "run_probe"])
@pytest.mark.parametrize("outcome", ["pass", "fail", "partial"])
def test_execution_retains_observed_outcome_without_certifying_scope(journal, tool, outcome):
    facts = {"passed": outcome == "pass", "status": "passed" if outcome == "pass" else
             "failed" if outcome == "fail" else "timeout",
             "exit_code": 0 if outcome == "pass" else 1 if outcome == "fail" else None,
             "timed_out": outcome == "partial", "truncated": outcome == "partial"}
    identity = observed(journal, "check", tool=tool, output=facts)
    raw = review()
    before = copy.deepcopy(raw)
    receipt = record(journal, raw)
    assert receipt["scope_review"]["status"] == "applied"
    scope = retained(journal)
    case = scope["cases"][0]
    assert {key: case[key] for key in before["cases"][0]} == before["cases"][0]
    assert case["execution"] == {**identity, "diff_hash": CURRENT,
                                 "observation": facts, "currency": "current"}
    assert scope["interpretation_status"] == "model_authored_unverified"
    assert scope["coverage_status"] == "not_certified"
    assert scope["diff_currency"] == "current"
    assert raw == before
    authority = {"workflow_gate": "ready_to_submit", "remaining_budget": {"tool_actions": 3},
                 "available_tool_names": ["run_probe", "finish_task"],
                 "working_plan": view(journal)}
    projected = compact_model_state(authority, history=[])
    assert projected["working_plan"]["plan"]["scope_review"] == scope
    for key in ("workflow_gate", "remaining_budget", "available_tool_names"):
        assert projected[key] == authority[key]


@pytest.mark.parametrize("defect", ["missing", "pending", "stale", "wrong_output_diff",
                                  "wrong_tool", "tool_failed", "missing_input_hash"])
def test_invalid_execution_reference_preserves_prior_review_and_valid_action(journal, defect):
    observed(journal, "check", tool="run_check", output={"passed": True})
    record(journal, review(), turn="saved")
    previous = retained(journal)
    kwargs = {
        "pending": {"finish": False}, "stale": {"diff": OTHER},
        "wrong_output_diff": {"output_diff": OTHER}, "wrong_tool": {"tool": "read_file"},
        "tool_failed": {"status": "failed"}, "missing_input_hash": {"input_hash": False},
    }.get(defect, {})
    if defect != "missing":
        observed(journal, "invalid", **({"tool": "run_probe"} | kwargs))
    call = selected(review(evidence="invalid"))
    receipt = record(journal, calls=[call])
    assert receipt["scope_review"]["status"] == "rejected"
    assert receipt["scope_review"]["diagnostics"]
    assert retained(journal) == previous
    assert validate_tool_batch([call]) == "parallel_read"
    assert not any(e["event_type"] == "protocol_correction" for e in journal.events())


@pytest.mark.parametrize("defect", ["missing", "pending", "wrong_tool", "tool_failed",
                                  "missing_input_hash"])
def test_invalid_public_source_reference_is_nonblocking(journal, defect):
    kwargs = {"pending": {"finish": False}, "wrong_tool": {"tool": "run_probe"},
              "tool_failed": {"status": "failed"}, "missing_input_hash": {"input_hash": False}}
    if defect != "missing":
        observed(journal, "invalid-source", **kwargs.get(defect, {}))
    call = selected(review(disposition="source_inferred", evidence=None,
                           sources=["invalid-source"]))
    receipt = record(journal, calls=[call])
    assert receipt["scope_review"]["status"] == "rejected"
    assert "scope_review" not in view(journal)["plan"]
    assert view(journal)["plan"]["text"] == "Inspect public modes and test the original caller."
    assert validate_tool_batch([call]) == "parallel_read"


@pytest.mark.parametrize("disposition,sources", [("source_inferred", ["source"]), ("untested", [])])
def test_nonexecution_cases_are_retained_without_execution_credit(journal, disposition, sources):
    record(journal, review(disposition=disposition, evidence=None, sources=sources))
    scope = retained(journal)
    assert scope["cases"][0]["disposition"] == disposition
    assert scope["cases"][0]["execution"] is None
    assert scope["coverage_status"] == "not_certified"


@pytest.mark.parametrize("substituted", [False, True],
                         ids=["same-conditions", "helper-substitution"])
def test_input_comparison_binds_execution_without_certifying_equivalence(journal, substituted):
    public = "parse_record receives one quoted CSV field containing an embedded newline."
    supplied = "parse_record receives a flat CSV row without a newline." if substituted else public
    inputs = {"public_conditions": public, "case_conditions": supplied}
    interpretation = (
        "The flat-row helper does not exercise the reported embedded newline; that remains open."
        if substituted else
        "The authored construction preserves the reported newline; receipt identity alone "
        "does not establish that the assertion checked it."
    )
    facts = {"status": "passed", "exit_code": 0}
    identity = observed(journal, "csv-helper", tool="run_probe", output=facts)
    raw = review(evidence="csv-helper", scope="Quoted-field newline preservation")
    raw["cases"][0].update(input=inputs, expected_observation="The field retains its newline.",
                            interpretation=interpretation)
    before = copy.deepcopy(raw)
    assert record(journal, raw)["scope_review"]["status"] == "applied"
    delivered = compact_model_state({"working_plan": view(journal)}, [])
    saved = delivered["working_plan"]["plan"]["scope_review"]
    case = saved["cases"][0]
    assert {key: case[key] for key in raw["cases"][0]} == raw["cases"][0]
    assert case["execution"] == {**identity, "diff_hash": CURRENT, "currency": "current",
                                 "observation": facts}
    assert saved["coverage_status"] == "not_certified"
    assert saved["interpretation_status"] == "model_authored_unverified"
    assert raw == before
    observed(journal, "stale-helper", tool="run_probe", diff=OTHER, output=facts)
    stale = copy.deepcopy(raw)
    stale["cases"][0]["evidence_action_id"] = "stale-helper"
    receipt = record(journal, stale, turn="stale-reference")
    assert receipt["scope_review"]["diagnostics"] == ["scope_review_execution_not_current"]
    assert retained(journal) == saved


def test_unknown_public_conditions_and_extra_control_remain_explicitly_unmapped(journal):
    observed(journal, "control", tool="run_probe", output={"status": "passed", "exit_code": 0})
    raw = review(disposition="untested", evidence=None)
    raw["cases"] = [{
        "input": {"public_conditions": None,
                  "case_conditions": "Proposed parse_record call with a constructed quoted row."},
        "expected_observation": "One complete field is returned.",
        "disposition": "untested", "evidence_action_id": None,
        "interpretation": "The public input construction is unspecified; this is an assumption.",
    }, {
        "input": {"public_conditions": None,
                  "case_conditions": "Additional normal control: parse_record('left,right')."},
        "expected_observation": "Two ordinary fields are returned.",
        "disposition": "executed", "evidence_action_id": "control",
        "interpretation": "This extra control is not a reconstruction of the public example.",
    }]
    assert record(journal, raw)["scope_review"]["status"] == "applied"
    saved = retained(journal)
    for requested, case in zip(raw["cases"], saved["cases"], strict=True):
        assert case["input"] == requested["input"]
        assert case["interpretation"] == requested["interpretation"]
    assert saved["cases"][0]["execution"] is None
    assert saved["cases"][1]["execution"]["action_id"] == "control"
    assert saved["coverage_status"] == "not_certified"


@pytest.mark.parametrize("field,value", [
    ("public_conditions", " \n"), ("case_conditions", " \n"), ("case_conditions", "x" * 501),
], ids=["blank-public", "blank-case", "oversized-case"])
def test_invalid_input_comparison_preserves_review_without_rejecting_action(journal, field, value):
    record(journal, review(disposition="untested", evidence=None), turn="saved-legacy")
    before = retained(journal)
    raw = review(disposition="untested", evidence=None)
    raw["cases"][0]["input"] = {
        "public_conditions": "One quoted CSV field contains a newline.",
        "case_conditions": "The helper constructs a quoted CSV field containing a newline.",
        field: value,
    }
    call = selected(raw)
    assert record(journal, calls=[call])["scope_review"]["status"] == "rejected"
    assert retained(journal) == before
    assert isinstance(retained(journal)["cases"][0]["input"], str)
    assert validate_tool_batch([call]) == "parallel_read"


@pytest.mark.parametrize("defect", ["scope_too_long", "too_many_cases", "too_many_sources",
                                  "blank_interpretation", "no_source_for_inference",
                                  "execution_id_on_untested", "unknown_disposition"])
def test_invalid_annotation_shape_does_not_erase_plan(journal, defect):
    raw = review(disposition="untested", evidence=None)
    if defect == "scope_too_long":
        raw["scope"] = "s" * 501
    elif defect == "too_many_cases":
        raw["cases"] *= 5
    elif defect == "too_many_sources":
        raw["source_action_ids"] *= 5
    elif defect == "blank_interpretation":
        raw["cases"][0]["interpretation"] = "  "
    elif defect == "no_source_for_inference":
        raw["cases"][0]["disposition"] = "source_inferred"
        raw["source_action_ids"] = []
    elif defect == "execution_id_on_untested":
        raw["cases"][0]["evidence_action_id"] = "check"
    else:
        raw["cases"][0]["disposition"] = "verified"
    before = view(journal)["plan"]
    assert record(journal, raw)["scope_review"]["status"] == "rejected"
    assert view(journal)["plan"] == before


@pytest.mark.parametrize("paired_input", [False, True], ids=["legacy-string", "compared-input"])
def test_plan_rewrite_null_new_diff_and_restart_preserve_review(journal, tmp_path, paired_input):
    observed(journal, "check", tool="run_probe", output={"status": "failed", "exit_code": 1})
    raw = review()
    if paired_input:
        raw["cases"][0]["input"] = {
            "public_conditions": "public_call(mode='strict', item='valid')",
            "case_conditions": "public_call(mode='fast', item='valid') as a sibling control",
        }
    record(journal, raw, turn="saved")
    original = retained(journal)
    assert original["cases"][0]["input"] == raw["cases"][0]["input"]
    receipt = record(journal, None, turn="rewrite", plan="Inspect the next untested public mode.")
    assert receipt["status"] == "updated" and "scope_review" not in receipt
    assert retained(journal) == original
    null_receipt = record(journal, None, turn="null")
    assert "scope_review" not in null_receipt and retained(journal) == original
    restarted = DevJournal(tmp_path, journal.run_id)
    assert retained(restarted) == original
    before = restarted.path.read_bytes()
    assert record(restarted, review(scope="Do not replace on replay"), turn="saved") == (
        next(e["payload"]["receipt"] for e in restarted.events()
             if e["event_type"] == plans.EVENT and e["payload"]["turn_id"] == "saved")
    )
    assert restarted.path.read_bytes() == before
    historical = retained(restarted, OTHER)
    assert historical["diff_currency"] == "historical"
    assert historical["source_evidence"][0]["currency"] == "historical"
    assert historical["cases"][0]["execution"]["currency"] == "historical"
    assert historical["cases"][0]["input"] == raw["cases"][0]["input"]
    assert historical["cases"][0]["interpretation"] == original["cases"][0]["interpretation"]
    assert historical["coverage_status"] == "not_certified"


def test_prior_diff_source_is_labelled_historical_without_new_source_authority(journal):
    observed(journal, "old-source", tool="search_files", diff=OTHER)
    record(journal, review(disposition="source_inferred", evidence=None, sources=["old-source"]))
    scope = retained(journal)
    assert scope["diff_currency"] == "current"
    assert scope["source_evidence"][0]["currency"] == "historical"
    assert scope["cases"][0]["execution"] is None


def test_same_batch_future_evidence_stays_rejected_on_idempotent_restart(journal, tmp_path):
    raw = review(evidence="future")
    call = selected(raw, action="future", tool="run_probe")
    receipt = record(journal, calls=[call], turn="future-turn")
    assert receipt["scope_review"]["status"] == "rejected"
    observed(journal, "future", tool="run_probe", output={"status": "passed", "exit_code": 0})
    restarted = DevJournal(tmp_path, journal.run_id)
    before = restarted.path.read_bytes()
    assert record(restarted, calls=[call], turn="future-turn") == receipt
    assert restarted.path.read_bytes() == before
    assert "scope_review" not in view(restarted)["plan"]
    assert record(restarted, raw, turn="later-turn")["scope_review"]["status"] == "applied"


@pytest.mark.parametrize("first_valid", [False, True])
def test_first_nonnull_annotation_owns_batch_without_fallback(journal, first_valid):
    first = (review(disposition="untested", evidence=None, scope="First scope")
             if first_valid else {})
    second = review(disposition="untested", evidence=None, scope="Second scope")
    calls = [selected(None, action="null"), selected(first, action="first"),
             selected(second, action="second")]
    receipt = record(journal, calls=calls)["scope_review"]
    assert receipt["action_id"] == "first"
    assert receipt["status"] == ("applied" if first_valid else "rejected")
    assert "ignored_additional_scope_reviews" in receipt["diagnostics"]
    assert validate_tool_batch(calls) == "parallel_read"
    if first_valid:
        assert retained(journal)["scope"] == "First scope"
    else:
        assert "scope_review" not in view(journal)["plan"]


@pytest.mark.parametrize("create_plan", [False, True])
def test_review_requires_valid_plan_but_can_accompany_initial_plan(tmp_path, create_plan):
    journal = DevJournal(tmp_path, "run_dev_scopeinitial")
    raw = review(disposition="untested", evidence=None, sources=[])
    receipt = record(journal, raw, plan="Inspect public scope." if create_plan else None)
    assert receipt["scope_review"]["status"] == ("applied" if create_plan else "rejected")
    if create_plan:
        assert retained(journal)["scope"] == raw["scope"]
    else:
        assert view(journal)["plan"] is None


def test_absent_and_explicit_null_serialization_remain_distinct_and_add_no_review(journal):
    absent = selected().turn_decision
    explicit = selected(None).turn_decision
    assert "scope_review" not in absent.model_dump(mode="json")
    assert explicit.model_dump(mode="json")["scope_review"] is None
    assert "scope_review" not in PublicTurnDecision.model_validate(
        absent.model_dump(mode="json"),
    ).model_dump(mode="json")
    for turn, raw in (("absent", ABSENT), ("explicit", None)):
        assert "scope_review" not in record(journal, raw, turn=turn)
        assert "scope_review" not in view(journal)["plan"]


@pytest.mark.parametrize("public_basis", [None, "Public API promises unchanged valid records."])
def test_expectation_basis_survives_receipt_projection_and_restart(journal, public_basis):
    observed(journal, "check", tool="run_probe", output={"status": "passed", "exit_code": 0})
    raw = review()
    expectation = {"outcome": "Valid records retain their fields.", "public_basis": public_basis}
    raw["cases"][0]["expected_observation"] = expectation
    assert record(journal, raw)["scope_review"]["status"] == "applied"
    restarted = DevJournal(journal.root, journal.run_id)
    projected = retained(restarted)
    assert projected["cases"][0]["expected_observation"] == expectation
    assert projected["cases"][0]["execution"]["observation"]["status"] == "passed"
    assert projected["coverage_status"] == "not_certified"
    assert projected["interpretation_status"] == "model_authored_unverified"
    assert retained(restarted, OTHER)["cases"][0]["expected_observation"] == expectation


@pytest.mark.parametrize("bad", [
    {"outcome": "value", "public_basis": " "},
    {"outcome": "a" * 301, "public_basis": None},
    {"outcome": "value", "public_basis": "b" * 201},
    {"outcome": "value"},
])
def test_bad_expectation_preserves_prior_review_and_does_not_block_action(journal, bad):
    observed(journal, "check", tool="run_probe", output={"status": "passed"})
    record(journal, review(), turn="legacy-review")
    original = retained(journal)
    raw = review()
    raw["cases"][0]["expected_observation"] = bad
    call = selected(raw)
    assert record(journal, calls=[call])["scope_review"]["status"] == "rejected"
    assert retained(journal) == original
    assert validate_tool_batch([call]) == "parallel_read"


def test_rejected_scope_annotation_does_not_reject_valid_plan_revision(journal):
    record(journal, review(disposition="untested", evidence=None), turn="saved")
    previous = retained(journal)
    receipt = record(journal, {}, plan="Test the remaining mode with the original caller.")
    assert receipt["status"] == "updated"
    assert receipt["scope_review"]["status"] == "rejected"
    assert view(journal)["plan"]["text"] == "Test the remaining mode with the original caller."
    assert retained(journal) == previous


def test_external_public_prefix_supplies_evidence_not_plan_lifecycle(journal, tmp_path):
    external = DevJournal(tmp_path / "external", "run_dev_scopeevidence")
    record(external, turn="initial", plan="This external plan must not replace the current plan.")
    observed(external, "external-source", tool="search_files")
    observed(external, "external-check", tool="run_check", output={"passed": False, "exit_code": 1})
    original_external = external.path.read_bytes()
    raw = review(evidence="external-check", sources=["external-source"])
    kwargs = dict(turn_id="external-review", diff_hash=CURRENT, gate="ready_to_submit")
    receipt = plans.record(journal, [selected(raw)], evidence_events=external.events(), **kwargs)
    assert receipt["scope_review"]["status"] == "applied"
    assert view(journal)["plan"]["text"] == "Inspect public modes and test the original caller."
    execution = retained(journal)["cases"][0]["execution"]
    assert execution["action_id"] == "external-check"
    assert execution["observation"] == {"passed": False, "exit_code": 1}
    assert external.path.read_bytes() == original_external
    before = journal.path.read_bytes()
    assert plans.record(journal, [selected({})], evidence_events=[], **kwargs) == receipt
    assert journal.path.read_bytes() == before


def catalog_span(start=1, end=10, *, scope="repository", path="public.py", file_hash=CURRENT):
    return {"source_scope": scope, "path": path, "file_hash": file_hash,
            "start_line": start, "end_line": end}


def source_receipt(journal, action="read", *, spans=None, tool="read_file", **kwargs):
    selected_spans = spans if spans is not None else [catalog_span()]
    output = {"spans": [{**span, "content": "PUBLIC_SOURCE_BODY_SENTINEL"}
                         for span in selected_spans]}
    return observed(journal, action, tool=tool, output=output, **kwargs)


@pytest.mark.parametrize("mismatch", ["stale_file_hash", "other_scope", "other_path", "disjoint",
                                    "non_source_tool", "failed_read", "pending_read"])
def test_source_catalog_excludes_nonmatching_or_unfinished_receipts(tmp_path, mismatch):
    journal = DevJournal(tmp_path, "run_dev_scopecatalog")
    spans = [catalog_span()]
    kwargs = {}
    if mismatch == "stale_file_hash":
        spans[0]["file_hash"] = OTHER
    elif mismatch == "other_scope":
        spans[0]["source_scope"] = "dependency:publiclib"
    elif mismatch == "other_path":
        spans[0]["path"] = "other.py"
    elif mismatch == "disjoint":
        spans = [catalog_span(11, 20)]
    elif mismatch == "non_source_tool":
        kwargs["tool"] = "run_probe"
    elif mismatch == "failed_read":
        kwargs["status"] = "failed"
    else:
        kwargs["finish"] = False
    source_receipt(journal, spans=spans, **kwargs)
    catalog = scope_review.source_catalog(journal.events(), [catalog_span()])
    assert catalog["items"] == []
    assert catalog["omitted_action_count"] == 0


@pytest.mark.parametrize("tool,field,scope", [
    ("read_file", "spans", None),
    ("read_file", "spans", "dependency:publiclib"),
    ("search_files", "dependency_spans", "dependency:publiclib"),
])
def test_source_catalog_intersects_selected_range_without_delivering_source_text(
    tmp_path, tool, field, scope,
):
    journal = DevJournal(tmp_path, "run_dev_scopecatalog")
    source = catalog_span(1, 50, scope=scope or "repository")
    selected_spans = [catalog_span(7, 9, scope=scope or "repository")]
    expected_range = copy.deepcopy(selected_spans[0])
    if scope is None:
        source.pop("source_scope")
        selected_spans[0].pop("source_scope")
    identity = observed(journal, tool=tool, diff=OTHER, output={
        field: [{**source, "content": "PUBLIC_SOURCE_BODY_SENTINEL"}],
    })
    events = journal.events()
    before = copy.deepcopy((events, selected_spans))
    catalog = scope_review.source_catalog(events, selected_spans)
    assert catalog["items"] == [{**identity, "diff_hash": OTHER,
                                  "ranges": [expected_range], "omitted_range_count": 0}]
    assert catalog["omitted_action_count"] == 0
    assert "PUBLIC_SOURCE_BODY_SENTINEL" not in json.dumps(catalog)
    assert (events, selected_spans) == before
    # Matching file bytes may originate on an older diff; the index keeps that
    # original identity and does not manufacture a new current-diff observation.
    assert catalog["items"][0]["diff_hash"] == OTHER


def test_source_catalog_merges_overlaps_and_adjacency_but_never_fills_gaps(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_scopecatalog")
    spans = [catalog_span(1, 10), catalog_span(5, 15), catalog_span(30, 40)]
    source_receipt(journal, "older", spans=spans)
    source_receipt(journal, "newer", spans=spans)
    selected_spans = [catalog_span(8, 12), catalog_span(12, 15), catalog_span(33, 34),
                      catalog_span(35, 35), catalog_span(37, 37), catalog_span(8, 12)]
    events = journal.events()
    # A repeated completed receipt cannot create a second catalog action.
    events.append(copy.deepcopy(events[-1]))
    catalog = scope_review.source_catalog(events, selected_spans)
    assert [item["action_id"] for item in catalog["items"]] == ["newer", "older"]
    for item in catalog["items"]:
        assert item["ranges"] == [catalog_span(8, 15), catalog_span(33, 35),
                                  catalog_span(37, 37)]
        assert item["omitted_range_count"] == 0
    assert scope_review.source_catalog(events, list(reversed(selected_spans))) == catalog


def test_source_catalog_reports_action_and_range_limits_on_matching_receipts(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_scopecatalog")
    spans = [catalog_span(1 + n * 3, 1 + n * 3) for n in range(10)]
    for n in range(10):
        source_receipt(journal, f"read-{n}", spans=spans)
    catalog = scope_review.source_catalog(journal.events(), spans)
    assert [item["action_id"] for item in catalog["items"]] == [
        f"read-{n}" for n in range(9, 1, -1)
    ]
    assert catalog["omitted_action_count"] == 2
    for item in catalog["items"]:
        assert item["ranges"] == spans[:8]
        assert item["omitted_range_count"] == 2


def test_source_catalog_without_selected_spans_does_not_expand_source_selection(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_scopecatalog")
    source_receipt(journal)
    catalog = scope_review.source_catalog(journal.events(), [])
    assert catalog["items"] == []
    assert catalog["omitted_action_count"] == 0
