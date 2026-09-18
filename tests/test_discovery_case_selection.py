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
