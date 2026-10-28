"""Shared, stdlib-only contract for the injected public probe APIs.

These checks describe API usage, never target execution or behavior correctness.
The same source is available to prompt construction and the trusted probe launcher.
"""

from __future__ import annotations

SETUP_PARAMETERS = ("label", "actual", "expected")
OBSERVER_PARAMETERS = ("input_paths", "environment_keys", "expected_exceptions")
ORIGINAL_ONLY_APIS = frozenset({
    "reproduction_workspace", "reproduction_outputs", "observed_target", "record_observation",
})
MAX_INPUT_PATHS = 4
MAX_ENVIRONMENT_KEYS = 16
MAX_EXPECTED_EXCEPTIONS = 4
MAX_TARGET_CALLS = 4
MAX_SETUP_CHECKS = 16
MAX_SETUP_LABEL_CHARS = 120
MAX_SETUP_VALUE_CHARS = 256
MAX_SETUP_INTEGER_BITS = 256
SETUP_SIGNATURE = "check_setup(" + ", ".join(SETUP_PARAMETERS) + ")"
OBSERVER_SIGNATURE = "observed_target(*, " + ", ".join(p + "=()" for p in OBSERVER_PARAMETERS) + ")"


class HelperAPIError(ValueError):
    """A bounded API-usage diagnostic, not a target exception classification."""

    def __init__(self, api: str, parameter: str | None, code: str, **details) -> None:
        self.details = {"api": api, "parameter": parameter, "code": code, **details}
        field = api + ("." + parameter if parameter else "")
        if code == "missing_arguments":
            message = "missing required arguments: " + ", ".join(details["missing_parameters"])
        elif code in {"unexpected_arguments", "duplicate_arguments"}:
            message = code.replace("_", " ") + ": " + ", ".join(details["unexpected_parameters"])
        elif code == "max_count":
            message = f"received {details['actual_count']} items; maximum {details['maximum']}"
        else:
            message = "expected " + details.get("expected", code)
            if "actual_type" in details:
                message += "; received " + details["actual_type"]
        super().__init__(field + ": " + message)


def bind_setup(args, kwargs):
    """Bind the public signature before running the actual comparison function."""
    if len(args) > len(SETUP_PARAMETERS):
        raise HelperAPIError("check_setup", None, "max_count",
                             actual_count=len(args), maximum=len(SETUP_PARAMETERS))
    unexpected = sorted(set(kwargs) - set(SETUP_PARAMETERS))
    if unexpected:
        raise HelperAPIError("check_setup", None, "unexpected_arguments",
                             unexpected_parameters=[name[:64] for name in unexpected[:4]])
    duplicate = [name for name in SETUP_PARAMETERS[:len(args)] if name in kwargs]
    if duplicate:
        raise HelperAPIError("check_setup", None, "duplicate_arguments",
                             unexpected_parameters=duplicate)
    values = {SETUP_PARAMETERS[index]: value for index, value in enumerate(args)} | kwargs
    missing = [name for name in SETUP_PARAMETERS if name not in values]
    if missing:
        raise HelperAPIError("check_setup", None, "missing_arguments", missing_parameters=missing)
    return values


def validate_observer_settings(input_paths, environment_keys, expected_exceptions):
    """Preserve existing settings acceptance; identify the first invalid field."""
    for name, value, allowed, maximum in (
        ("input_paths", input_paths, (list, tuple), MAX_INPUT_PATHS),
        ("environment_keys", environment_keys, (list, tuple), MAX_ENVIRONMENT_KEYS),
        ("expected_exceptions", expected_exceptions, (tuple,), MAX_EXPECTED_EXCEPTIONS),
    ):
        expected = " or ".join(t.__name__ for t in allowed)
        if type(value) not in allowed:
            raise HelperAPIError("observed_target", name, "type", expected=expected,
                                 actual_type=type(value).__name__[:64])
        if len(value) > maximum:
            raise HelperAPIError("observed_target", name, "max_count",
                                 actual_count=len(value), maximum=maximum)
    if any(type(key) is not str for key in environment_keys):
        raise HelperAPIError("observed_target", "environment_keys", "item_type",
                             expected="string items")
    if any(not isinstance(item, type) or not issubclass(item, (Exception, SystemExit))
           for item in expected_exceptions):
        raise HelperAPIError("observed_target", "expected_exceptions", "item_type",
                             expected="Exception or SystemExit subclasses")


def valid_error(value):
    """Validate bounded diagnostics only; these fields confer no verification credit."""
    required = {"api", "parameter", "code"}
    optional = {"actual_count", "maximum", "missing_parameters", "unexpected_parameters",
                "expected", "actual_type"}
    if (type(value) is not dict or not required <= set(value)
            or set(value) - required - optional
            or type(value["api"]) is not str or type(value["code"]) is not str
            or value["api"] not in {"check_setup", "observed_target"}
            or value["code"] not in {"missing_arguments", "unexpected_arguments",
                                     "duplicate_arguments", "max_count", "type", "item_type"}
            or (value["parameter"] is not None
                and (type(value["parameter"]) is not str
                     or value["parameter"] not in {*SETUP_PARAMETERS, *OBSERVER_PARAMETERS}))):
        return False
    fields = {
        "missing_arguments": {"missing_parameters"},
        "unexpected_arguments": {"unexpected_parameters"},
        "duplicate_arguments": {"unexpected_parameters"},
        "max_count": {"actual_count", "maximum"},
        "type": {"expected", "actual_type"},
        "item_type": {"expected"},
    }
    if set(value) != required | fields[value["code"]]:
        return False
    for key, item in value.items():
        if key in {"actual_count", "maximum"} and (
                type(item) is not int or not 0 <= item <= 1_000_000):
            return False
        if key in {"expected", "actual_type"} and (
                type(item) is not str or not 1 <= len(item) <= 128):
            return False
        if key in {"missing_parameters", "unexpected_parameters"} and (
                type(item) is not list or not 1 <= len(item) <= 4
                or any(type(name) is not str or not 1 <= len(name) <= 64 for name in item)):
            return False
    return True


SETUP_DESCRIPTION = (
    f"Injected {SETUP_SIGNATURE}: all three arguments required; no import/redefinition. "
    "Use actual settings, e.g. check_setup('mode', settings.mode, expected_mode). "
    f"Up to {MAX_SETUP_CHECKS} type-strict scalar comparisons: None/bool/int/finite float/str; "
    f"label 1-{MAX_SETUP_LABEL_CHARS} chars, str <={MAX_SETUP_VALUE_CHARS} chars, "
    f"int <={MAX_SETUP_INTEGER_BITS} bits. Setup matches do not verify behavior. "
)
OBSERVER_DESCRIPTION = (
    f"Original-requirement mode also injects {OBSERVER_SIGNATURE}. "
    f"input_paths is a list or tuple of at most {MAX_INPUT_PATHS} fixture roots; directories "
    "include their descendants. Group related inputs under a fixture root without omitting "
    "required files; exclude generated outputs and their ancestors. Existing snapshot entry "
    "and byte limits still apply. "
    f"environment_keys is a list or tuple of at most {MAX_ENVIRONMENT_KEYS} strings. "
    "expected_exceptions follows the exception policy below. "
)
