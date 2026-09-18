"""Diagnostic-only probe intent; selecting cases never establishes their coverage."""

from __future__ import annotations

from typing import Literal

from pydantic import ValidationError

from patchloop.dev import behavior_cases
from patchloop.dev.tools import DevToolGateway

POLICY = "preservation-cases-v1"
GUIDANCE = """
Before probing, select concrete inputs from the public requirement: one requiring the
change and, when supported, a nearby input that must preserve its existing behavior
despite sharing the proposed implementation trigger. Record their actual construction
and observable expectations in run_probe.case_selection. Derive the preservation input
yourself from the public task and inspected source; do not just name a category.
When that preservation input is available, prefer to exercise it in the first probe,
alone or together with the changed case. Set selected to the case(s) the program is
intended to exercise, and print separate setup/expected/observed evidence for each.
Use preserve=null with a scope_basis explanation if no supported boundary is known;
case_selection itself may also be null. This adds no mandatory probe or planning step.

After the result, compare each selected setup with the program's actual construction
and output. Selection is intent, not evidence of execution or correct interpretation.
A passing changed case does not settle the preservation case. If an untested case
could change the conclusion, choose a useful probe for it; otherwise report that limit.
Do not claim unselected or unsupported cases were verified. Use the existing report
fields to summarize the observed evidence and remaining uncertainty.
"""
REVIEW = (
    "Compare each selected setup and expectation with the actual program and output. "
    "Selection is model-authored intent, not execution or coverage evidence. A changed-case "
    "match does not settle preservation. Choose a useful probe for unresolved cases or "
    "report the limits; no further probe is required."
)


class CaseSelection(behavior_cases.BehaviorCases):
    selected: Literal["change", "preserve", "both"]


def extend_schema(schema: dict) -> None:
    selection = behavior_cases.cases_schema()
    selection["description"] = (
        "Optional concrete changed/preserved inputs and which this program intends to exercise. "
        "Select from the complete public task; unknown preservation scope stays null. "
        "Recording or selecting a case does not verify it or gate a probe/report."
    )
    selection["properties"]["selected"] = {
        "type": "string", "enum": ["change", "preserve", "both"],
        "description": "Cases this program intends to exercise, not a coverage claim.",
    }
    selection["required"].append("selected")
    schema["parameters"]["properties"]["case_selection"] = selection
    schema["parameters"]["required"].append("case_selection")


def bind(value, public_task) -> dict:
    if value is None:
        return behavior_cases.bind(None, public_task)
    try:
        selection = CaseSelection.model_validate(value)
    except ValidationError:
        return {"status": "invalid", "diagnostics": ["invalid_case_selection"],
                "interpretation_status": "model_authored_unverified"}
    receipt = behavior_cases.bind(selection.model_dump(exclude={"selected"}), public_task)
    receipt["selected"] = selection.selected
    if selection.preserve is None and selection.selected in {"preserve", "both"}:
        receipt["diagnostics"].append("selected_preservation_case_missing")
    return receipt


class CaseSelectionGateway(DevToolGateway):
    """Keep raw arguments in the shared action hash/journal and replay saved receipts."""

    def _run_probe(self, question, python_source, *, execution_identity, case_selection=None):
        selection = bind(case_selection, self.public_task)
        output = super()._run_probe(question, python_source, execution_identity=execution_identity)
        output["case_selection"] = {
            **selection, "diff_hash": output["diff_hash"], "source_hash": output["source_hash"],
            "coverage_status": "not_assessed", "next_question": REVIEW,
        }
        return output
