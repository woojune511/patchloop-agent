"""Opt-in host comparison with a model-authored expectation frozen before a probe."""
from __future__ import annotations

from patchloop.dev.probe_cases import MAX_OBSERVATION_BYTES, observation_json
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

MODE = "frozen-json-v1"
DESCRIPTION = (
    "Optionally declare expected_json before execution and have the host compare it with "
    "the program's complete stdout. Derive this expectation from the public requirement "
    "and justify it in question; python_source should compute the actual observation from "
    "current project code. Choose concrete values that express the requirement, including "
    "relevant contents and ordering, rather than copying observed values into expectations. "
    "With an expectation, print exactly one JSON value and no extra stdout, at most 2048 "
    "UTF-8 bytes. Include setup observations in that JSON if relevant. Null leaves an "
    "ordinary probe unchanged; the string 'null' expects the JSON null value. Equality "
    "only checks your chosen expected value; it does not verify its meaning, independence, "
    "case coverage or actual project execution. You may report limitations without a probe."
)


def extend_schema(schema: dict) -> None:
    schema["description"] += " " + DESCRIPTION
    parameters = schema["parameters"]
    parameters["properties"]["expected_json"] = {
        "type": ["string", "null"], "maxLength": MAX_OBSERVATION_BYTES,
        "description": "Optional literal JSON expectation, frozen in this action before execution.",
    }
    parameters["required"].append("expected_json")


def freeze(expected_json: str | None) -> str | None:
    if expected_json is None:
        return None
    normalized, error = observation_json({
        "status": "passed", "exit_code": 0, "stdout": expected_json,
    })
    if error is not None:
        raise ContractError("invalid expected_json: " + error)
    return normalized


def compare(expected: str | None, output: dict) -> dict:
    observed, reason = (observation_json(output) if expected is not None
                        else (None, "expectation_not_supplied"))
    return {
        "mode": MODE,
        "status": ("not_compared" if reason else
                   "matched" if expected == observed else "mismatched"),
        "reason": reason,
        "expected_json": expected, "observed_json": observed,
        "expected_hash": sha256_bytes(expected.encode()) if expected is not None else None,
        "observed_hash": sha256_bytes(observed.encode()) if observed is not None else None,
        "diff_hash": output["diff_hash"], "source_hash": output["source_hash"],
        "interpretation_status": "model_authored_unverified",
        "semantic_verdict": None, "coverage_status": "not_assessed",
    }


def gateway_type(base: type[DevToolGateway]) -> type[DevToolGateway]:
    class FrozenExpectationGateway(base):
        def _run_probe(self, question, python_source, *, expected_json=None, **kwargs):
            # DevToolGateway journals the complete arguments/input_hash before dispatch.
            # Only the program goes to the sandbox; the expectation stays in the host.
            expected = freeze(expected_json)
            output = super()._run_probe(question, python_source, **kwargs)
            output["expectation_comparison"] = compare(expected, output)
            return output

    return FrozenExpectationGateway
