"""Small syntax-only host API controls; submitted programs are never executed."""

import pytest

from patchloop.dev import helper_program
from patchloop.errors import ContractError
from patchloop.sandbox import probe_api
from patchloop.util import sha256_bytes


@pytest.mark.parametrize("mode", ["helper", "original"])
@pytest.mark.parametrize("source,missing", [
    ("check_setup()", ["label", "actual", "expected"]),
    ("check_setup(settings)", ["actual", "expected"]),
    ("check_setup('mode', actual=value)", ["expected"]),
])
def test_direct_setup_binding_error_is_structured_before_execution(mode, source, missing):
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source, mode=mode)
    error = raised.value
    assert error.details["invalid_fields"] == [{
        "path": "/python_source", "requirement": str(error)}]
    assert error.details["helper_program_error"] == {
        "kind": "invalid_api_call", "source_hash": sha256_bytes(source.encode()),
        "names": ["check_setup"], "line": 1, "api_error": {
            "api": "check_setup", "parameter": None, "code": "missing_arguments",
            "missing_parameters": missing}}
    assert probe_api.valid_error(error.details["helper_program_error"]["api_error"])


@pytest.mark.parametrize("source,code", [
    ("check_setup('x', value, expected, extra)", "max_count"),
    ("check_setup('x', actual=value, expected=other, surprise=1)", "unexpected_arguments"),
    ("check_setup('x', value, expected=other, actual=value)", "duplicate_arguments"),
])
def test_setup_positional_and_keyword_binding_uses_shared_contract(source, code):
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source)
    detail = raised.value.details["helper_program_error"]["api_error"]
    assert detail["code"] == code and probe_api.valid_error(detail)


@pytest.mark.parametrize("parameter,maximum", [
    ("input_paths", probe_api.MAX_INPUT_PATHS),
    ("environment_keys", probe_api.MAX_ENVIRONMENT_KEYS),
    ("expected_exceptions", probe_api.MAX_EXPECTED_EXCEPTIONS),
])
def test_original_literal_count_uses_the_runtime_limit(parameter, maximum):
    permitted = f"observed_target({parameter}=(" + ",".join(["value"] * maximum) + ",))"
    helper_program.validate(permitted, mode="original")
    source = f"observed_target({parameter}=(" + ",".join(["value"] * (maximum + 1)) + ",))"
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source, mode="original")
    detail = raised.value.details["helper_program_error"]["api_error"]
    assert detail == {
        "api": "observed_target", "parameter": parameter, "code": "max_count",
        "actual_count": maximum + 1, "maximum": maximum}
    assert probe_api.valid_error(detail)


def test_seven_fixture_paths_report_actual_count_and_limit():
    source = "target = observed_target(input_paths=[a, b, c, d, e, f, g])"
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source, mode="original")
    detail = raised.value.details["helper_program_error"]["api_error"]
    assert detail["actual_count"] == 7 and detail["maximum"] == 4
    assert "input_paths" in str(raised.value)


@pytest.mark.parametrize("source,code", [
    ("observed_target(paths)", "max_count"),
    ("observed_target(paths=paths)", "unexpected_arguments"),
])
def test_observer_accepts_only_its_declared_keyword_parameters(source, code):
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source, mode="original")
    assert raised.value.details["helper_program_error"]["api_error"]["code"] == code


def test_original_mode_supplies_observer_apis_but_never_executes_the_source():
    source = (
        "root = reproduction_workspace()\noutputs = reproduction_outputs()\n"
        "target = observed_target(input_paths=[root], environment_keys=['HOME'])\n"
        "check_setup(label='mode', actual=setting, expected=desired)\n"
        "record_observation(target().value)\nraise RuntimeError('must not execute')\n")
    assert helper_program.validate(source, mode="original") is None
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source)
    assert set(raised.value.details["helper_program_error"]["names"]) == (
        probe_api.ORIGINAL_ONLY_APIS)


@pytest.mark.parametrize("source", [
    "check_setup(*values)",
    "check_setup(**values)",
    "observed_target(*values)",
    "observed_target(input_paths=[a,b,c,d,e], **options)",
    "observed_target(input_paths=selected_paths)",
    "observed_target(input_paths=[*selected_paths,a,b,c,d])",
    "globals()['check_setup'] = custom\ncheck_setup()",
    "alias = check_setup\nalias()",
    "custom.check_setup()",
    "from missing_module import check_setup\ncheck_setup()",
    "def check_setup():\n    pass\ncheck_setup()",
    "def helper(check_setup):\n    check_setup()",
    "def helper():\n    check_setup = custom\n    return lambda: check_setup()",
    "class Helper:\n    check_setup = custom\n    check_setup()",
    "values = [check_setup() for check_setup in supplied]",
    "observed_target = custom\nobserved_target(input_paths=[a,b,c,d,e])",
])
def test_dynamic_calls_and_shadowed_names_are_not_rejected_as_host_api_errors(source):
    assert helper_program.validate(source, mode="original") is None


def test_original_mode_still_rejects_compile_errors():
    with pytest.raises(ContractError) as raised:
        helper_program.validate("return 1", mode="original")
    assert raised.value.details["helper_program_error"]["kind"] == "syntax_error"
