"""Case intent stays bounded, advisory and separate from observed behavior."""

import pytest

from diagnostics import discovery_case_selection as cases
from patchloop.contracts import PublicTask


@pytest.fixture
def public():
    return PublicTask.model_validate({
        "schema_version": "task-public-v1", "task_id": "selection-toy", "split": "dev-train",
        "repository": {"url": "snapshot://selection-toy", "base_commit": "sha256:" + "0" * 64,
                       "language": "python"},
        "issue": {"title": "Public requirement", "description": "value() returns zero."},
        "constraints": {"allowed_paths": ["toy.py"]},
        "visible_checks": [{"id": "public-example", "command": ["python", "-c", "print(0)"]}],
    })


def selection(**changes):
    return {
        "change": {"setup": "enabled=True, input=0", "expected": "1"},
        "preserve": {"setup": "enabled=False, input=0", "expected": "0"},
        "scope_basis": "The public condition is enabled=True.", "selected": "both", **changes,
    }


@pytest.mark.parametrize("selected", ["change", "preserve", "both"])
def test_selection_records_intent_without_validating_interpretation(public, selected):
    receipt = cases.bind(selection(selected=selected), public)
    assert receipt["status"] == "recorded" and receipt["selected"] == selected
    assert receipt["coverage_status"] == "not_assessed"
    assert receipt["interpretation_status"] == "model_authored_unverified"
    assert receipt["diagnostics"] == []


def test_unknown_boundary_and_missing_selected_case_are_advisory(public):
    unknown = selection(preserve=None, scope_basis="No supported preservation boundary known.",
                        selected="change")
    assert cases.bind(unknown, public)["diagnostics"] == []
    receipt = cases.bind({**unknown, "selected": "preserve"}, public)
    assert receipt["diagnostics"] == ["selected_preservation_case_missing"]
    assert receipt["coverage_status"] == "not_assessed"


@pytest.mark.parametrize("value", [[], "bad", selection(selected="unknown"),
                                   selection(scope_basis="x" * 301),
                                   selection(change={"setup": "", "expected": "1"}),
                                   selection(extra="unsupported")])
def test_bad_annotations_return_bounded_diagnostics(public, value):
    receipt = cases.bind(value, public)
    assert receipt == {"status": "invalid", "diagnostics": ["invalid_case_selection"],
                       "interpretation_status": "model_authored_unverified"}


def trigger_contrast(relation, **changes):
    return {
        "candidate_trigger": "enabled and value == 0",
        "preserve_satisfies_trigger": relation,
        "applicability_difference": "Public applicability is unknown in this toy task.",
        **changes,
    }


@pytest.mark.parametrize("relation,feedback", [
    (False, "Your annotation says the preservation input disables"),
    (True, "Your annotation claims the whole trigger is retained"),
    (None, "Whether a preservation input retains the whole candidate trigger is unresolved"),
])
def test_trigger_relation_is_reviewed_as_an_unverified_claim(public, relation, feedback):
    # Even a plainly unsupported True claim is recorded as intent, never validated.
    value = selection(trigger_contrast=trigger_contrast(relation))
    receipt = cases.bind(value, public, with_contrast=True)
    assert receipt["status"] == "recorded" and receipt["diagnostics"] == []
    assert receipt["trigger_contrast"] == value["trigger_contrast"]
    assert receipt["interpretation_status"] == "model_authored_unverified"
    assert receipt["coverage_status"] == "not_assessed"
    assert cases.contrast_review(receipt).startswith(feedback)
    assert cases.contrast_review(receipt).endswith(cases.REVIEW)


@pytest.mark.parametrize("annotation", [{}, {"trigger_contrast": None}])
def test_absent_trigger_contrast_does_not_invent_a_relation(public, annotation):
    receipt = cases.bind(selection(**annotation), public, with_contrast=True)
    assert receipt["status"] == "recorded" and receipt["trigger_contrast"] is None
    assert "is unresolved" in cases.contrast_review(receipt)


def test_missing_preservation_case_cannot_support_a_claimed_trigger_relation(public):
    value = selection(preserve=None, trigger_contrast=trigger_contrast(True))
    receipt = cases.bind(value, public, with_contrast=True)
    assert receipt["status"] == "recorded"
    assert receipt["diagnostics"] == ["selected_preservation_case_missing",
                                       "trigger_contrast_without_preservation_case"]
    assert "is unresolved" in cases.contrast_review(receipt)


@pytest.mark.parametrize("contrast", [
    trigger_contrast("true"), trigger_contrast(1), trigger_contrast(True, unexpected="bad"),
    trigger_contrast(True, candidate_trigger="x" * 301),
    trigger_contrast(True, applicability_difference=""),
])
def test_malformed_trigger_contrast_stays_bounded_and_unresolved(public, contrast):
    receipt = cases.bind(selection(trigger_contrast=contrast), public, with_contrast=True)
    assert receipt["status"] == "invalid"
    assert "trigger_contrast" not in receipt
    assert "is unresolved" in cases.contrast_review(receipt)
