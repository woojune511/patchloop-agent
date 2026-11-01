"""Small acquisition description, stable schemas and shared exception contract."""

from __future__ import annotations

import pytest

from patchloop.dev import first_reproduction, probe_call_capture, reproduction
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import sha256_json


@pytest.mark.parametrize("agent_policy,probe_policy,expected", [
    ("current", "none", "5417a30b16fb2365ff44e318b480a91ed48c87eb2d524eeddc4581066808bff7"),
    ("thin", "none", "b8a4387ad679130859d7a8b76a6eb8dc27313b3c05ec02f102e8ec6f4d391ef0"),
    ("current", "cases-v1", "83ce9b6f79c39d1cb4728910153cbb9b21753669ab9933aa3c533d263f25ac61"),
    ("thin", "cases-v1", "02fa2e0de16a121d9bda31c3b87e8b9d9dd6fcad16290ec64fcbb96479609fd0"),
])
def test_original_stage_changes_description_only(agent_policy, probe_policy, expected):
    schemas = dev_tool_schemas(
        finish_enabled=False, allowed_tools={"run_probe", "stop_task"},
        agent_policy=agent_policy, probe_policy=probe_policy, original_acquisition_pending=True,
    )
    probe = next(row for row in schemas if row["name"] == "run_probe")
    assert len(probe["description"]) < 4_000
    probe["description"] = "ONLY_CHANGED_DESCRIPTION"
    # Current baseline includes the shared decision-basis description. Replacing
    # only the stage prose still pins parameters, nulls, other tools and descriptions.
    assert sha256_json(schemas) == "sha256:" + expected


@pytest.mark.parametrize("agent_policy,diagnosis,expected", [
    ("current", False, "b8d176a58e9865b3efd8e1b73c1c447b5158fd56a12e2f4b746d418420e2126b"),
    ("thin", False, "c631fb0ab43fda70f20ef48d6bcb0e58bd770732f569cfef9e2f66ae492512f3"),
    ("current", True, "9f7ea75adea8115540ee793197c00039b03672a1c91d437f277951c5faa873e0"),
    ("thin", True, "9f7ea75adea8115540ee793197c00039b03672a1c91d437f277951c5faa873e0"),
])
def test_other_probe_stages_match_current_contract(agent_policy, diagnosis, expected):
    # Current general descriptions include comparable-input guidance; diagnostic
    # stages and all argument shapes retain their existing contract.
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
