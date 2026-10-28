"""Prompt and runtime API agreement, with bounded public error records."""

import inspect

import pytest

from patchloop.dev import first_reproduction, helper_program
from patchloop.dev.tools import dev_tool_schemas
from patchloop.sandbox import probe_api, probe_setup


def test_common_setup_signature_matches_the_actual_comparison_function():
    parameters = tuple(inspect.signature(probe_setup.SetupChecks.check).parameters)
    assert parameters[1:] == probe_api.SETUP_PARAMETERS
    assert probe_api.SETUP_DESCRIPTION in helper_program.DESCRIPTION
    assert probe_api.SETUP_DESCRIPTION in first_reproduction.DESCRIPTION
    assert len(first_reproduction.DESCRIPTION) < 4_000


@pytest.mark.parametrize("original", [False, True])
@pytest.mark.parametrize("policy", ["current", "thin"])
def test_both_dispatched_probe_stages_keep_the_same_api_limits(original, policy):
    schemas = dev_tool_schemas(
        finish_enabled=False, allowed_tools={"run_probe", "stop_task"},
        agent_policy=policy, original_acquisition_pending=original,
    )
    description = next(row["description"] for row in schemas if row["name"] == "run_probe")
    assert probe_api.SETUP_DESCRIPTION in description
    assert probe_api.OBSERVER_DESCRIPTION in description
    assert "without omitting required files" in description


@pytest.mark.parametrize("change", [
    {"api": []}, {"parameter": []}, {"code": []}, {"actual_count": True},
    {"maximum": -1}, {"actual_count": 1_000_001}, {"unexpected": "field"},
])
def test_malformed_api_errors_cannot_become_valid_public_metadata(change):
    error = {"api": "observed_target", "parameter": "input_paths", "code": "max_count",
             "actual_count": 7, "maximum": 4}
    assert probe_api.valid_error(error)
    assert not probe_api.valid_error(error | change)


def test_error_code_requires_its_specific_fields():
    assert not probe_api.valid_error({"api": "observed_target", "parameter": "input_paths",
                                      "code": "max_count"})
    with pytest.raises(probe_api.HelperAPIError) as caught:
        probe_api.bind_setup(("mode",), {})
    assert caught.value.details["missing_parameters"] == ["actual", "expected"]
    assert probe_api.valid_error(caught.value.details)
