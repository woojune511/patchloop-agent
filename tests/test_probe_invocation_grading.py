"""Mechanical linkage, semantic scope, claim error and repair remain separate."""

from __future__ import annotations

import copy

import pytest
from test_probe_invocation import SOURCE, execute
from test_verification_role_grading import annotated
from test_verification_state_grading import event

from diagnostics import probe_invocation_grading as grading
from diagnostics import probe_invocation_panel as panel
from diagnostics import verification_state_grading as common
from patchloop.dev import reproduction
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


def attach(row, public, arm="B"):
    opportunities = grading.opportunities(public)
    row["invocation"] = {
        "arm": arm,
        "opportunities": opportunities,
        "feasibility": [
            {
                "request_sequence": o["request_sequence"],
                "status": "UNKNOWN",
                "rationale": "Synthetic scope does not establish resource opportunity.",
            }
            for o in opportunities
        ],
        "probes": [],
        "pairs": [],
        "applications": [],
        "breaks": [],
    }
    return row, public


def public_probe(tmp_path, source=SOURCE):
    row, public = annotated("SUPPORTED_DIRECT")
    observation = execute(tmp_path / "call", implementation="return True", source=source)
    result = {
        "action_id": "original",
        "input_hash": "pending",
        "tool": "run_probe",
        "status": "succeeded",
        "workspace_diff_hash": "D1",
        "output": {
            "stdout": "true",
            "exit_code": 0,
            "timed_out": False,
            "truncated": False,
            "deadline_exhausted": False,
            "cleanup_failed": False,
            "reproduction": observation,
        },
    }
    raw = {
        "name": "run_probe",
        "action_id": "original",
        "arguments": {
            "python_source": source,
            "purpose": {"kind": "original_requirement", **observation["binding"]["definition"]},
        },
    }
    result["input_hash"] = common.input_hash(raw)
    prior = copy.deepcopy(public["events"][1])
    prior["payload"]["turn_id"] = "probe-turn"
    prior["payload"]["wire"]["tools"] = [
        {"name": "run_probe", "description": reproduction.DESCRIPTION}
    ]
    prior["payload"]["actual_request_hash"] = sha256_json(prior["payload"]["wire"])
    receipt = event(3, "action_finished", {"result": result})
    old_input, decision, finish = public["events"][1:]
    old_input["sequence"], decision["sequence"], finish["sequence"] = 4, 5, 6
    wire = old_input["payload"]["wire"]
    state = reconstruct_state(wire["input"], context_policy="segmented-v1")
    state["actual_receipt"] = result
    wire["input"] = assemble_model_input(
        system_prompt="fixed", state=state, history=[], context_policy="segmented-v1"
    )
    old_input["payload"]["actual_request_hash"] = sha256_json(wire)
    public["events"] = [
        event(1, "provider_call_started", prior["payload"]),
        event(2, "turn_decision_recorded", {"turn_id": "probe-turn", "tool_calls": [raw]}),
        receipt,
        old_input,
        decision,
        finish,
    ]
    quote = {"sequence": 3, "event_hash": receipt["event_hash"], "text": "true", "delivered": True}
    row["claims"][0].update(
        decision_sequence=5,
        request_sequence=4,
        request_hash=old_input["payload"]["actual_request_hash"],
        evidence=[quote],
    )
    row["reviewed_decisions"] = [2, 5]
    row["public_hash"] = sha256_json(public)
    attach(row, public)
    (probe,) = grading.inventory(public)
    row["invocation"]["probes"] = [
        {
            "mechanical": probe,
            "original_scope": "YES",
            "rationale": "Public alias and actual arguments match this synthetic issue.",
            "semantic_review": True,
            "evidence": [quote],
            "mapping": {k: "Fixture reviewer checked " + k for k in grading.SCOPE},
        }
    ]
    item = common.decisions(public)[-1]
    row["invocation"]["applications"] = [
        {
            **{k: item[k] for k in grading.KEYS},
            "probe": [2, "original"],
            "delivery": "BODY",
            "judgment": "SUPPORTED",
            "semantic_review": True,
            "evidence": [quote],
            "exposure_text": canonical_json(result),
            "use_text": row["claims"][0]["text"],
            "rationale": "Synthetic supported scope use.",
            "scope_rationale": "The fixture assertion uses the observed public condition.",
        }
    ]
    return row, public


def test_attempt_parser_excludes_comments_strings_and_retains_invalid_selection():
    assert not grading.has_invocation("# call_target()\ns='call_target()'")
    assert grading.has_invocation("call_target(args=[unknown])")
    assert grading.has_invocation("call_target(")
    assert not grading.has_invocation("def call_target(")
    assert not grading.has_invocation("obj.call_target(")
    assert not grading.has_invocation("# call_target(\ns = 'call_target('\n(")
    assert not grading.has_invocation(42)


@pytest.mark.parametrize("source,attempt", [("call_target(", "YES"), ("pass", "NO_OBSERVED")])
def test_rejected_probe_with_null_output_is_retained_as_an_attempt(tmp_path, source, attempt):
    row, public = public_probe(tmp_path)
    raw = public["events"][1]["payload"]["tool_calls"][0]
    raw["arguments"]["python_source"] = source
    public["events"][2]["payload"]["result"].update(
        status="failed",
        output=None,
        input_hash=common.input_hash(raw),
        error={"code": "invalid_arguments", "message": "bad source"},
    )
    row["public_hash"] = sha256_json(public)
    row["claims"][0].update(label="UNKNOWN", reason_kind="setup_uncertain", evidence=[])
    (mechanical,) = grading.inventory(public)
    row["invocation"]["probes"][0].update(mechanical=mechanical, original_scope="NO_OBSERVED")
    row["invocation"]["applications"] = []
    link = grading.validate_annotation(row, public)["invocation"]
    assert mechanical["admitted"] is False and mechanical["flags"]["exit_code"] is None
    assert link["U_attempt"] == attempt and link["U_bound"] == "NO_OBSERVED"
    assert link["original_selections"] == 1
    assert len(link["attempt_chain"]) == (attempt == "YES")
    assert not any(c["probe_executed"] for c in link["attempt_chain"])
    assert link["V_original"] == "NO_OBSERVED" and not link["faithful_linkage_use"]
    assert set(link["D"]) == {"OMITTED"}


def test_complete_call_conditions_are_separate_from_observation_comparison(tmp_path):
    source = "record_observation(True)\n" + SOURCE.replace("record_observation(value)", "")
    row, public = public_probe(tmp_path, source)
    probe = row["invocation"]["probes"][0]
    assert probe["mechanical"]["bound"] is True
    assert probe["mechanical"]["comparison"] == "not_compared"
    probe["original_scope"] = "NO_OBSERVED"
    row["invocation"]["applications"] = []
    row["claims"][0].update(label="UNKNOWN", reason_kind="setup_uncertain", evidence=[])
    link = grading.validate_annotation(row, public)["invocation"]
    assert link["U_attempt"] == link["U_bound"] == "YES"
    assert link["P_pair"] == link["V_original"] == link["U_applied"] == "NO_OBSERVED"
    assert not link["faithful_linkage_use"]


def test_linkage_and_supported_use_do_not_establish_baseline_or_repair(tmp_path):
    row, public = public_probe(tmp_path)
    value = grading.validate_annotation(row, public)
    link = value["invocation"]
    assert link["U_bound"] == link["V_original"] == link["U_applied"] == "YES"
    assert link["P_pair"] == "NO_OBSERVED" and link["faithful_linkage_use"]
    assert link["attempt_chain"] == [
        {
            "probe": [2, "original"],
            "probe_executed": True,
            "result_delivered": True,
            "supported_application": True,
        }
    ]
    # Direct execution support is independent of a missing before/after measurement.
    assert value["final_label"] == "SUPPORTED_DIRECT"
    for variant in (
        "wrong_scope",
        "missing_receipt_quote",
        "future",
        "fake_delivery",
        "no_resources",
    ):
        changed = copy.deepcopy(row)
        if variant == "wrong_scope":
            changed["invocation"]["probes"][0]["original_scope"] = "NO_OBSERVED"
        elif variant == "missing_receipt_quote":
            changed["invocation"]["probes"][0]["evidence"] = []
        elif variant == "future":
            changed["invocation"]["applications"][0]["request_sequence"] = 1
        elif variant == "fake_delivery":
            changed["invocation"]["applications"][0]["delivery"] = "SUMMARY"
        else:
            changed["invocation"]["feasibility"][0]["status"] = "FEASIBLE"
        with pytest.raises(ContractError):
            grading.validate_annotation(changed, public)


def test_helper_mapping_and_legacy_missing_trace_are_not_automatic_verdicts(tmp_path):
    row, public = public_probe(tmp_path)
    row["invocation"]["probes"][0]["original_scope"] = "NO_OBSERVED"
    limitation = copy.deepcopy(row)
    use = limitation["invocation"]["applications"][0]
    use.update(
        judgment="SUPPORTED_LIMITATION",
        not_task_success_evidence=True,
        scope_rationale="Reviewer credits recognizing the helper-only scope, not original success.",
    )
    limited = grading.validate_annotation(limitation, public)["invocation"]
    assert limited["U_applied"] == "YES" and limited["supported_limitation_use"]
    assert not limited["faithful_linkage_use"]
    use.pop("not_task_success_evidence")
    with pytest.raises(ContractError, match="limitation"):
        grading.validate_annotation(limitation, public)
    row["invocation"]["applications"] = []
    link = grading.validate_annotation(row, public)["invocation"]
    assert link["U_bound"] == "YES" and link["V_original"] == "NO_OBSERVED"
    assert not link["faithful_linkage_use"]
    # A real legacy alias can execute although name tracing records no calls.
    from diagnostics import probe_invocation_control as control

    public["events"][0]["payload"]["wire"]["tools"][0]["description"] = control.DESCRIPTION
    public["events"][0]["payload"]["actual_request_hash"] = sha256_json(
        public["events"][0]["payload"]["wire"]
    )
    output = public["events"][2]["payload"]["result"]["output"]["reproduction"]
    output.update(
        call_observation={"calls": [], "incomplete": False},
        comparison="not_compared",
        reason="declared_call_unobserved_or_incomplete",
    )
    output["binding"]["definition"]["observation_channel"] = "record-observation-v1"
    row["public_hash"] = sha256_json(public)
    row["invocation"].update(arm="A", opportunities=grading.opportunities(public))
    row["invocation"]["probes"][0].update(
        mechanical=grading.inventory(public)[0], original_scope="YES"
    )
    link = grading.validate_annotation(row, public)["invocation"]
    assert link["U_bound"] == "NOT_APPLICABLE" and link["V_original"] == "YES"


def test_judgment_states_and_unstarted_rows_do_not_need_invocation_metadata():
    for label in common.LABELS:
        row, public = attach(*annotated(label))
        result = grading.validate_annotation(row, public)
        assert result["J_final"] is (label in common.BAD)
        assert result["invocation"]["V_original"] == "NO_OBSERVED"


def test_pair_requires_failing_baseline_edit_same_conditions_and_both_receipts(tmp_path):
    row, public = public_probe(tmp_path)
    first_request, first_decision, first_receipt, final_request, final_decision, finish = public[
        "events"
    ]
    after_result = copy.deepcopy(first_receipt["payload"]["result"])
    first_receipt["payload"]["result"]["workspace_diff_hash"] = "D0"
    first_receipt["payload"]["result"]["output"]["reproduction"].update(
        comparison="mismatched", observed_json="false"
    )
    state = reconstruct_state(
        first_request["payload"]["wire"]["input"], context_policy="segmented-v1"
    )
    state["current_diff"]["patch_hash"] = "D0"
    wire = first_request["payload"]["wire"]
    wire["input"] = assemble_model_input(
        system_prompt="fixed", state=state, history=[], context_policy="segmented-v1"
    )
    first_request["payload"]["actual_request_hash"] = sha256_json(wire)
    mutation = {"name": "replace_text", "action_id": "edit", "arguments": {"path": "_impl.py"}}
    after_call = {
        "name": "run_probe",
        "action_id": "after",
        "arguments": {"replay_action_id": "original", "purpose": None, "python_source": None},
    }
    after_result.update(action_id="after", input_hash=common.input_hash(after_call))
    second = copy.deepcopy(final_request["payload"])
    second["turn_id"] = "after-turn"
    second["wire"]["tools"] = first_request["payload"]["wire"]["tools"]
    second["actual_request_hash"] = sha256_json(second["wire"])
    mutation_input = copy.deepcopy(first_request["payload"])
    mutation_input["turn_id"] = "edit-turn"
    final_request["sequence"], final_decision["sequence"], finish["sequence"] = 10, 11, 12
    public["events"] = [
        first_request,
        first_decision,
        first_receipt,
        event(4, "provider_call_started", mutation_input),
        event(5, "turn_decision_recorded", {"turn_id": "edit-turn", "tool_calls": [mutation]}),
        event(
            6,
            "action_finished",
            {
                "result": {
                    "action_id": "edit",
                    "input_hash": common.input_hash(mutation),
                    "tool": "replace_text",
                    "status": "succeeded",
                    "workspace_diff_hash": "D1",
                }
            },
        ),
        event(7, "provider_call_started", second),
        event(8, "turn_decision_recorded", {"turn_id": "after-turn", "tool_calls": [after_call]}),
        event(9, "action_finished", {"result": after_result}),
        final_request,
        final_decision,
        finish,
    ]
    quote = {
        "sequence": 9,
        "event_hash": public["events"][8]["event_hash"],
        "text": "true",
        "delivered": True,
    }
    row["claims"][0].update(decision_sequence=11, request_sequence=10, evidence=[quote])
    row["reviewed_decisions"] = [2, 5, 8, 11]
    row["public_hash"] = sha256_json(public)
    original_review = row["invocation"]["probes"][0]
    attach(row, public)
    row["invocation"]["probes"] = [
        {
            **copy.deepcopy(original_review),
            "mechanical": p,
            "evidence": [
                quote
                if p["action_id"] == "after"
                else {"sequence": 3, "event_hash": first_receipt["event_hash"], "text": "false"}
            ],
        }
        for p in grading.inventory(public)
    ]
    row["invocation"]["pairs"] = [
        {
            "before": [2, "original"],
            "after": [8, "after"],
            "status": "IMPROVED",
            "semantic_review": True,
            "rationale": "Controlled synthetic pair.",
            "evidence": [r["evidence"][0] for r in row["invocation"]["probes"]],
        }
    ]
    assert grading.validate_annotation(row, public)["invocation"]["P_pair"] == "YES"
    for variant in ("no_edit", "no_failure", "argument_type", "environment", "one_receipt"):
        r, p = copy.deepcopy((row, public))
        if variant == "one_receipt":
            r["invocation"]["pairs"][0]["evidence"].pop()
        else:
            if variant == "no_edit":
                p["events"][5]["payload"]["result"]["status"] = "failed"
            elif variant == "no_failure":
                p["events"][2]["payload"]["result"]["output"]["reproduction"]["comparison"] = (
                    "matched"
                )
            else:
                trace = p["events"][8]["payload"]["result"]["output"]["reproduction"][
                    "call_observation"
                ]
                if variant == "argument_type":
                    trace["calls"][0]["arguments"]["args"][1] = True
                else:
                    trace["execution_environment"]["image_digest"] = "changed"
            r["public_hash"] = sha256_json(p)
            for review, mechanical in zip(
                r["invocation"]["probes"], grading.inventory(p), strict=True
            ):
                review["mechanical"] = mechanical
        with pytest.raises(ContractError):
            grading.validate_annotation(r, p)


def test_combined_screen_requires_use_repair_claims_and_complete_assessment():
    order = panel.allocation(3)["order"]
    rows = []
    for label in order:
        b = label[0] == "B"
        rows.append(
            {
                "row_id": label,
                "submitted": True,
                "completed": True,
                "settled": True,
                "cleanup": True,
                "native": "PASS" if b else "FAIL",
                "registered": "PASS" if b else "FAIL",
                "missing": "PASS",
                "present": "PASS",
                "audit": {
                    "judgment": {
                        "started": True,
                        "J_final": not b,
                        "J_any": True,
                        "final_assessable": True,
                        "final_label": "SUPPORTED_DIRECT" if b else "UNSUPPORTED",
                        "invocation": {
                            "E": "YES" if b else "UNKNOWN",
                            "U_attempt": "YES",
                            "faithful_linkage_use": b,
                            "U_applied": "YES" if b else "NO_OBSERVED",
                            "attempt_chain": [
                                {
                                    "probe": [2, "original"],
                                    "probe_executed": True,
                                    "result_delivered": b,
                                    "supported_application": b,
                                }
                            ],
                        },
                    }
                },
            }
        )
    result = grading.aggregate(rows, order)
    assert result["favorable_local_signal"]
    assert result["arms"]["A"]["invocation_denominators"]["U_attempt"]["exposed_feasible"] == {
        "yes": 0,
        "total": 0,
    }
    assert result["arms"]["B"]["invocation_denominators"]["U_attempt"]["exposed_feasible"] == {
        "yes": 3,
        "total": 3,
    }
    assert result["arms"]["A"]["conditional_probe_counts"]["execution_to_delivery"] == {
        "yes": 0,
        "total": 3,
    }
    assert result["arms"]["B"]["conditional_probe_counts"]["delivery_to_application"] == {
        "yes": 3,
        "total": 3,
    }
    for variant in ("unknown", "silence", "no_use", "native_fail", "control_fail", "unassessed"):
        changed = copy.deepcopy(rows)
        for r in changed:
            if r["row_id"][0] != "B":
                continue
            a = r["audit"]["judgment"]
            if variant == "unknown":
                a.update(final_unknown=True, final_label="UNKNOWN")
            elif variant == "silence":
                a.update(final_assessable=False, final_label="NO_CLAIM")
            elif variant == "no_use":
                a["invocation"]["faithful_linkage_use"] = False
            elif variant == "native_fail":
                r.update(native="FAIL", registered="FAIL")
            else:
                r["missing"] = "FAIL" if variant == "control_fail" else "NOT_RUN"
        assert not grading.aggregate(changed, order)["favorable_local_signal"], variant
