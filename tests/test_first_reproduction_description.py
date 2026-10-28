"""Small acquisition description, stable schemas and shared exception contract."""

from __future__ import annotations

import pytest

from patchloop.dev import first_reproduction, probe_call_capture, reproduction
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import sha256_json


@pytest.mark.parametrize("agent_policy,probe_policy,expected", [
    ("current", "none", "1d84200b820ca78834078bb54ac2ee4a37017c2c89cab4a8db81e65d82d0bec4"),
    ("thin", "none", "7f6fbbf2877c592ed2732fc53c6a02d93535758195c5f72a3edbe464fc6e6d15"),
    ("current", "cases-v1", "b8b2305fe6fdfaabe4f31903bfbba7fb606189c689b3bd00eea48f77c17c9c85"),
    ("thin", "cases-v1", "c2aee81383a8cc3087419253718a89b8a041f61b6bb9d081c1c423a39d3e6b49"),
])
def test_original_stage_changes_description_only(agent_policy, probe_policy, expected):
    schemas = dev_tool_schemas(
        finish_enabled=False, allowed_tools={"run_probe", "stop_task"},
        agent_policy=agent_policy, probe_policy=probe_policy, original_acquisition_pending=True,
    )
    probe = next(row for row in schemas if row["name"] == "run_probe")
    assert len(probe["description"]) < 4_000
    probe["description"] = "ONLY_CHANGED_DESCRIPTION"
    # Captured at 5ea221da before shortening. Includes every parameter, annotations,
    # required/null fields, other tools and their complete descriptions.
    assert sha256_json(schemas) == "sha256:" + expected


@pytest.mark.parametrize("agent_policy,diagnosis,expected", [
    ("current", False, "3f466bc3576cebaa99b691af15c192d3d73bfa32b19a41b1d65dfb55fd0ef07d"),
    ("thin", False, "05c10a05a34a2be49f76b76a34a9b990252d838ca65b11c21ed4e97c43ed1886"),
    ("current", True, "9f7ea75adea8115540ee793197c00039b03672a1c91d437f277951c5faa873e0"),
    ("thin", True, "9f7ea75adea8115540ee793197c00039b03672a1c91d437f277951c5faa873e0"),
])
def test_other_probe_stages_match_current_contract(agent_policy, diagnosis, expected):
    schemas = dev_tool_schemas(
        finish_enabled=False, allowed_tools={"run_probe", "stop_task"},
        agent_policy=agent_policy, path_diagnosis_pending=diagnosis,
    )
    assert sha256_json(schemas) == "sha256:" + expected


def test_first_description_keeps_environment_and_required_observation_apis():
    environment = "Read-only dependency and source locations with public caller availability."
    description = first_reproduction.description(environment)
    assert description.endswith(environment)
    assert probe_call_capture.EXCEPTION_DESCRIPTION in description
    assert probe_call_capture.EXCEPTION_DESCRIPTION in reproduction.DESCRIPTION
    for name in ("reproduction_workspace()", "reproduction_outputs()", "observed_target(",
                 "record_observation(value)", "diagnostic_rules", "expected_exceptions=",
                 "capture_status", "reported_failure_json", "expected_json"):
        assert name in description
    assert "TemporaryDirectory" not in description
    assert "purpose=null" not in description
    assert "At finish" not in description


@pytest.mark.parametrize("agent_policy", ["current", "thin"])
def test_optional_diagnostic_description_preserves_tool_schema(agent_policy):
    options = {"finish_enabled": False, "allowed_tools": {"run_probe", "stop_task"},
               "agent_policy": agent_policy}
    strict = dev_tool_schemas(**options)
    advisory = dev_tool_schemas(**options, verification_policy="public-checks-v1")
    probe = next(row for row in advisory if row["name"] == "run_probe")
    assert "No original replay is automatic" in probe["description"]
    assert "blocks submission" not in probe["description"]
    assert "purpose.corrects_action_id" in probe["description"]
    probe["description"] = next(row["description"] for row in strict if row["name"] == "run_probe")
    assert advisory == strict
