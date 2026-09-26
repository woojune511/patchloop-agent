"""An independently generated public alternative for the existing seeded repair loop."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.util import sha256_text

FIELD = "independent_candidate"
EVENT = "diagnostic_independent_candidate_attached"
INSTRUCTION = (
    "An independent attempt produced this alternative from the same base and public task. "
    "Compare its behavior with the current candidate. Identify a substantive difference in "
    "their conditions or effects, and derive the expected behavior from the public requirement. "
    "Choose a concrete public input or execution state that could distinguish that difference, "
    "and use the existing source/check/probe tools to test it when useful. A check is evidence "
    "only for the inputs and outcomes it exercises. Connect the observation to your next edit "
    "or submission decision in the ordinary turn_decision. Neither candidate is a reference "
    "answer. The alternative patch is relative to the base; it is not applied or current "
    "editable-source evidence. Probes execute the current workspace only. Use normal reads "
    "and edits to construct the candidate you choose, then verify that current diff. If the "
    "alternatives coincide or no relevant difference is supported, say so and proceed normally."
)


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    patch: str = Field(min_length=1, max_length=60_000)
    patch_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_commit: str = Field(pattern=r"^(?:[0-9a-f]{40}|sha256:[0-9a-f]{64})$")

    @model_validator(mode="after")
    def exact_hash(self):
        if sha256_text(self.patch) != self.patch_hash:
            raise ValueError("independent candidate hash mismatch")
        return self


def overlay(state: dict, candidate: Candidate) -> dict:
    return {
        "instruction": INSTRUCTION,
        "origin": "independent_model_authored_unverified",
        **candidate.model_dump(),
        "matches_current_diff": state["current_diff"]["patch_hash"] == candidate.patch_hash,
        "evaluation_or_prior_actions_supplied": False,
    }
