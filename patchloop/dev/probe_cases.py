"""Opt-in reusable public experiments, not task acceptance or model-authored truth."""

from __future__ import annotations

import copy
import json
import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

POLICY = "cases-v1"
MAX_CASES = 3
MAX_OBSERVATION_BYTES = 2_048
DESCRIPTION = (
    "Optional reusable cases: first run an ordinary reference experiment printing exactly "
    "one JSON value (at most 2048 UTF-8 bytes), with case_id and reference_action_id null. "
    "Then supply that completed probe's reference_action_id, a question and new python_source "
    "that explicitly calls the current public project and prints the same observation shape; "
    "case_id is null. The harness compares JSON values and saves the candidate program. "
    "To rerun that exact candidate program on a later diff, set case_id from probe_cases and "
    "set question, python_source and reference_action_id null. No reference rerun is needed. "
    "Native-only code does not test a candidate. A match means only equality to the chosen "
    "observation, not that the reference is correct or all task behavior passed. Existing "
    "ad-hoc probes remain available; cases never block finish or trigger automatic execution."
)


def contract() -> dict[str, Any]:
    return {
        "policy": POLICY, "max_cases": MAX_CASES,
        "max_observation_utf8_bytes": MAX_OBSERVATION_BYTES,
        "comparison": "canonical-json-exact-types-order-independent-objects-v1",
        "reference": "prior-healthy-public-probe-model-selected-not-an-oracle-v1",
        "replay": "exact-saved-candidate-source-current-diff-existing-probe-action-v1",
        "retention": "three-most-recently-executed-cases-action-finished-v1",
        "context": "latest-bounded-catalog-mutable-no-archive-resurrection-v1",
        "description": DESCRIPTION,
    }


def extend_schema(schema: dict[str, Any]) -> None:
    schema["description"] += " " + DESCRIPTION
    parameters = schema["parameters"]
    for field in ("question", "python_source"):
        parameters["properties"][field]["type"] = ["string", "null"]
    for field in ("case_id", "reference_action_id"):
        parameters["properties"][field] = {"type": ["string", "null"], "maxLength": 500}
        parameters["required"].append(field)


class ProbeCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str | None = Field(default=None, min_length=1, max_length=500)
    python_source: str | None = Field(default=None, min_length=1, max_length=8_000)
    case_id: str | None = Field(default=None, min_length=1, max_length=500)
    reference_action_id: str | None = Field(default=None, min_length=1, max_length=500)


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite observation")
    return number


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate observation key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("non-JSON observation constant")


def observation_json(output: dict[str, Any]) -> tuple[str | None, str | None]:
    if (output.get("status") != "passed" or type(output.get("exit_code")) is not int
            or output["exit_code"] != 0
            or any(output.get(key) for key in (
                "timed_out", "truncated", "cleanup_failed", "deadline_exhausted",
            ))):
        return None, "execution_not_healthy"
    text = output.get("stdout")
    if not isinstance(text, str):
        return None, "stdout_not_json"
    try:
        if len(text.encode("utf-8")) > MAX_OBSERVATION_BYTES:
            return None, "observation_too_large"
        value = json.loads(text, parse_float=_finite_float, parse_constant=_invalid_constant,
                           object_pairs_hook=_unique_object)
        normalized = canonical_json(value)
        if len(normalized.encode("utf-8")) > MAX_OBSERVATION_BYTES:
            return None, "observation_too_large"
        return normalized, None
    except (ValueError, RecursionError, UnicodeError):
        return None, "stdout_not_json"


def _definition_hash(definition: dict[str, Any]) -> str:
    return sha256_json({key: value for key, value in definition.items() if key != "case_id"})


def _case_id(definition: dict[str, Any]) -> str:
    return "pc_" + _definition_hash(definition).removeprefix("sha256:")[:24]


def saved_cases(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Rebuild only durable executions; no mutable allocator or lifecycle replay."""
    cases: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] != "action_finished":
            continue
        definition = event["payload"].get("probe_case")
        if definition is None:
            continue
        result = event["payload"]["result"]
        comparison = result.get("output", {}).get("case_comparison", {})
        if (result["tool"] != "run_probe" or result["status"] != "succeeded"
                or definition.get("case_id") != _case_id(definition)
                or comparison.get("definition_hash") != _definition_hash(definition)
                or comparison.get("case_id") != definition["case_id"]):
            raise RecoveryError("saved probe case identity does not match its durable result")
        key = definition["case_id"]
        cases.pop(key, None)
        cases[key] = {"definition": copy.deepcopy(definition), "last_result": {
            "action_id": result["action_id"], "input_hash": result["input_hash"],
            "diff_hash": result["workspace_diff_hash"], **copy.deepcopy(comparison),
        }}
        if len(cases) > MAX_CASES:
            del cases[next(iter(cases))]
    return cases


def prepare(arguments: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve a prior reference or case before dispatch; never invent expectations."""
    intent = ProbeCaseRequest.model_validate(arguments)
    if intent.case_id is not None:
        if any(value is not None for value in (
            intent.question, intent.python_source, intent.reference_action_id,
        )):
            raise ContractError("case replay requires question/source/reference_action_id null")
        stored = saved_cases(events).get(intent.case_id)
        if stored is None:
            raise ContractError("unknown or no longer retained probe case_id")
        definition = stored["definition"]
        return {"question": definition["question"], "python_source": definition["python_source"],
                "case": definition}
    if intent.question is None or intent.python_source is None:
        raise ContractError("a new probe requires question and python_source")
    prepared = {"question": intent.question, "python_source": intent.python_source, "case": None}
    if intent.reference_action_id is None:
        return prepared
    reference = next((
        event["payload"]["result"] for event in events
        if event["event_type"] == "action_finished"
        and event["payload"]["result"]["action_id"] == intent.reference_action_id
    ), None)
    if reference is None or reference["tool"] != "run_probe" or reference["status"] != "succeeded":
        raise ContractError("reference_action_id must name a prior completed public probe")
    output = reference["output"]
    expected, reason = observation_json(output)
    if reason is not None:
        raise ContractError(f"reference probe has no bounded healthy JSON observation: {reason}")
    if (not isinstance(output.get("source_hash"), str)
            or not isinstance(reference.get("workspace_diff_hash"), str)
            or output.get("diff_hash") != reference["workspace_diff_hash"]):
        raise RecoveryError("reference probe identity is incomplete or inconsistent")
    definition = {
        "question": intent.question, "python_source": intent.python_source,
        "reference": {
            "action_id": reference["action_id"], "input_hash": reference["input_hash"],
            "diff_hash": reference["workspace_diff_hash"], "source_hash": output["source_hash"],
            "observation_json": expected,
        },
    }
    definition["case_id"] = _case_id(definition)
    prepared["case"] = definition
    return prepared


def compare(definition: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    source_hash = sha256_bytes(definition["python_source"].encode("utf-8"))
    if output.get("source_hash") != source_hash:
        raise RecoveryError("probe case executed source differs from saved program", details=output)
    observed, reason = observation_json(output)
    expected = definition["reference"]["observation_json"]
    return {
        "case_id": definition["case_id"], "definition_hash": _definition_hash(definition),
        "status": ("not_compared" if reason
                   else "matched" if expected == observed else "mismatched"),
        "reason": reason, "expected_json": expected, "observed_json": observed,
        "reference_action_id": definition["reference"]["action_id"],
        "candidate_source_hash": source_hash,
        "interpretation": "Equality to a model-selected reference, not task acceptance or proof "
                          "that the program tested the intended project behavior.",
        "counts_toward_completion": False,
    }


def project(events: list[dict[str, Any]], diff_hash: str) -> dict[str, Any]:
    items = []
    for case_id, case in saved_cases(events).items():
        definition = case["definition"]
        result = copy.deepcopy(case["last_result"])
        result["currency"] = "current" if result["diff_hash"] == diff_hash else "historical"
        result.pop("interpretation", None)
        result.pop("expected_json", None)  # Already carried by the bound reference below.
        if result["status"] == "matched":
            result.pop("observed_json", None)
            result["observed_json_matches_reference"] = True
        items.append({
            "case_id": case_id, "question": definition["question"],
            "reference": copy.deepcopy(definition["reference"]), "last_candidate_result": result,
            "program_authorship": "model_authored_unverified",
        })
    return {
        "policy": POLICY, "items": items,
        "interpretation": "Optional exact candidate programs retained in this run. Replay with "
                          "case_id using run_probe when offered; no automatic executions. "
                          "Historical matches do not test the current diff. References and program "
                          "relevance are model-selected, not trusted task oracles. The three most "
                          "recently executed cases remain available; older records are archived.",
    }
