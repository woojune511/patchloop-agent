"""Diagnostic-only probe intent; selecting cases never establishes their coverage."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from patchloop.dev import behavior_cases
from patchloop.dev.tools import DevToolGateway

POLICY = "preservation-cases-v1"
CONTRAST_POLICY = "applicability-contrast-v1"
POLICIES = (POLICY, CONTRAST_POLICY)
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
CONTRAST_GUIDANCE = """
Distinguish the candidate's whole implementation trigger from the public requirement's
applicability. In case_selection.trigger_contrast, state that trigger and whether the
preservation input still satisfies every part of it, then identify the public condition
that differs between the two inputs. Turning off any part of the trigger tests a disabled
branch; it leaves preservation under the same trigger unresolved. When the public task
supports such a contrast, prefer keeping the whole trigger true while changing applicability.
Check actual construction, not just matching labels or attributes. Print the relevant
constructed values and observations separately for each selected case. Unknown trigger
relations or unsupported boundaries stay unknown/null; do not invent a contrast.
This annotation is an unverified hypothesis, not proof of branch execution or coverage.
"""


class CaseSelection(behavior_cases.BehaviorCases):
    selected: Literal["change", "preserve", "both"]


class TriggerContrast(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    candidate_trigger: str = Field(min_length=1, max_length=behavior_cases.MAX_TEXT_CHARS)
    preserve_satisfies_trigger: bool | None
    applicability_difference: str = Field(min_length=1, max_length=behavior_cases.MAX_TEXT_CHARS)


class ApplicabilitySelection(CaseSelection):
    trigger_contrast: TriggerContrast | None = None


def extend_schema(schema: dict, *, with_contrast: bool = False) -> None:
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
    if with_contrast:
        text = {"type": "string", "minLength": 1, "maxLength": behavior_cases.MAX_TEXT_CHARS}
        selection["properties"]["trigger_contrast"] = {
            "type": ["object", "null"],
            "description": "Optional, unverified comparison of code trigger and public scope.",
            "properties": {
                "candidate_trigger": {**text, "description": (
                    "Whole candidate condition that activates the changed behavior, "
                    "including every conjunct; derive it from the inspected patch/source.")},
                "preserve_satisfies_trigger": {"type": ["boolean", "null"], "description": (
                    "Does the preservation setup still satisfy the whole candidate trigger? "
                    "False if any conjunct is disabled; null when unknown. Intent, not evidence.")},
                "applicability_difference": {**text, "description": (
                    "Public requirement separating change/preserve applicability, and how "
                    "their actual construction differs. State unknown if unsupported.")},
            },
            "required": ["candidate_trigger", "preserve_satisfies_trigger",
                         "applicability_difference"],
            "additionalProperties": False,
        }
        selection["required"].append("trigger_contrast")
    schema["parameters"]["properties"]["case_selection"] = selection
    schema["parameters"]["required"].append("case_selection")


def bind(value, public_task, *, with_contrast: bool = False) -> dict:
    if value is None:
        return behavior_cases.bind(None, public_task)
    try:
        model = ApplicabilitySelection if with_contrast else CaseSelection
        selection = model.model_validate(value)
    except ValidationError:
        return {"status": "invalid", "diagnostics": ["invalid_case_selection"],
                "interpretation_status": "model_authored_unverified"}
    receipt = behavior_cases.bind(
        selection.model_dump(exclude={"selected", "trigger_contrast"}), public_task)
    receipt["selected"] = selection.selected
    if selection.preserve is None and selection.selected in {"preserve", "both"}:
        receipt["diagnostics"].append("selected_preservation_case_missing")
    if isinstance(selection, ApplicabilitySelection):
        contrast = selection.trigger_contrast
        receipt["trigger_contrast"] = contrast.model_dump() if contrast else None
        if contrast and selection.preserve is None:
            receipt["diagnostics"].append("trigger_contrast_without_preservation_case")
    return receipt


def contrast_review(receipt: dict) -> str:
    contrast = receipt.get("trigger_contrast")
    relation = contrast.get("preserve_satisfies_trigger") if contrast else None
    if not receipt.get("cases", {}).get("preserve"):
        relation = None
    if relation is False:
        prompt = (
            "Your annotation says the preservation input disables part of the candidate trigger. "
            "That leaves same-trigger preservation unresolved. If the public task supports it, "
            "select an input retaining the whole trigger while changing public applicability, "
            "or report that limit. ")
    elif relation is True:
        prompt = (
            "Your annotation claims the whole trigger is retained. Check that claim against "
            "each actual constructed value and output, and justify the applicability difference "
            "from the public requirement. The claim does not establish branch execution. ")
    else:
        prompt = (
            "Whether a preservation input retains the whole candidate trigger is unresolved. "
            "Use public source and actual construction to resolve it if useful, or report "
            "that limit; do not invent an applicability difference. ")
    return prompt + REVIEW


class CaseSelectionGateway(DevToolGateway):
    """Keep raw arguments in the shared action hash/journal and replay saved receipts."""

    with_contrast = False

    def _run_probe(self, question, python_source, *, execution_identity, case_selection=None):
        selection = bind(case_selection, self.public_task, with_contrast=self.with_contrast)
        output = super()._run_probe(question, python_source, execution_identity=execution_identity)
        output["case_selection"] = {
            **selection, "diff_hash": output["diff_hash"], "source_hash": output["source_hash"],
            "coverage_status": "not_assessed",
            "next_question": contrast_review(selection) if self.with_contrast else REVIEW,
        }
        return output


class ApplicabilityGateway(CaseSelectionGateway):
    with_contrast = True
