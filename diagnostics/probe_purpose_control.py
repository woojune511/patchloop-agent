"""Diagnostic-only legacy probe interface; verification state stays ON in both arms."""
from __future__ import annotations

import copy
from contextlib import contextmanager
from unittest.mock import patch

from diagnostics.positive_verification_panel import require
from patchloop.dev import reproduction, runner

BASE = "5ff8654b4dab0b668986b6a2f643e0b37e5caa68"
LEGACY = "cbc779d2cc3d5db1b683bdde057c391edf55cba5"
LEGACY_REPLAY = (
    "After an edit, use replay_action_id with reproduction=null to keep the exact program, "
    "purpose and expected value."
)
LEGACY_DESCRIPTION = (
    "For a proposed original-task reproduction, set reproduction before execution: quote "
    "the public requirement, name the fully qualified Python entrypoint actually called, "
    "describe inputs/environment, and freeze expected_json. Print exactly one JSON value "
    "computed from the observed behavior. A helper experiment uses reproduction=null. "
    "The harness observes the declared Python call and compares stdout with the frozen "
    "expectation; neither proves that your chosen call represents the public requirement. "
    + LEGACY_REPLAY + " Changing them creates a different experiment, not resolution "
    "of the old one. reproduction_review separates helpers, unobserved calls, changed setup "
    "and same-reproduction comparisons. No extra probe or submission gate is imposed."
)
_ACTIVE = False


def project_tools(schemas, arm):
    require(arm in {"A", "B"}, "unknown probe-purpose arm")
    result = copy.deepcopy(schemas)
    if arm == "A":
        for tool in result:
            if tool["name"] != "run_probe":
                continue
            require(tool["description"].count(reproduction.DESCRIPTION) == 1,
                    "probe guidance changed")
            tool["description"] = tool["description"].replace(
                reproduction.DESCRIPTION, LEGACY_DESCRIPTION,
            ).replace("For helper probes, state the expected observation",
                      "State the expected observation")
            params = tool["parameters"]
            require(params["properties"]["purpose"] == reproduction.purpose_schema(),
                    "probe purpose schema changed")
            params["properties"] = {
                ("reproduction" if k == "purpose" else k):
                (reproduction.schema() if k == "purpose" else v)
                for k, v in params["properties"].items()
            }
            params["required"] = [
                "reproduction" if k == "purpose" else k for k in params["required"]]
    return result


@contextmanager
def assigned(arm):
    global _ACTIVE
    require(arm in {"A", "B"} and not _ACTIVE, "one known arm per process")
    _ACTIVE = True
    schemas, selection = runner.dev_tool_schemas, reproduction.selection

    def legacy_selection(arguments):
        require("purpose" not in arguments and "reproduction" in arguments,
                "control requires its offered reproduction input")
        return selection(arguments)

    try:
        if arm == "B":
            yield
        else:
            with (patch.object(runner, "dev_tool_schemas", lambda **kw:
                               project_tools(schemas(**kw), "A")),
                  patch.object(reproduction, "selection", legacy_selection)):
                yield
    finally:
        _ACTIVE = False


def initialize_off_worker(stop, admission):
    from diagnostics.parallel_dev_batch import initialize_worker

    initialize_worker(stop, admission)
    global _WORKER_SCOPE
    _WORKER_SCOPE = assigned("A")
    _WORKER_SCOPE.__enter__()
