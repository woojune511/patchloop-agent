"""Stage-specific instructions with the shared injected helper API contract."""

from patchloop.dev.probe_call_capture import EXCEPTION_DESCRIPTION
from patchloop.sandbox import probe_api

DESCRIPTION = (
    "Reproduce the public caller on the unchanged base before editing. "
    "Set purpose.kind=original_requirement; the host binds the public issue. "
    "Declare a dotted Python entrypoint, input_conditions, environment_conditions and distinct "
    "strict-JSON reported_failure_json and expected_json for the reported bug and desired "
    "behavior. An arbitrary mismatch is not reproduction. "
    "Run the real entrypoint in this process; no child processes. "
    + probe_api.SETUP_DESCRIPTION + probe_api.OBSERVER_DESCRIPTION +
    "Also injected: reproduction_workspace(), reproduction_outputs(), record_observation(value). "
    "Build fixtures under reproduction_workspace(); generated files and HOME/cache children "
    "under reproduction_outputs(). Explicitly create directories/environment; a deliberately "
    "read cache is an input fixture. Avoid random paths. "
    "Create target=observed_target(input_paths=[fixture_root]); inspect target.signature(). "
    "Use its actual signature in target(*args, **kwargs); None means unavailable, not zero "
    "arguments. Pass list arguments directly. For CLI argv, replace initial "
    "sys.argv=['<patchloop-reproduction>']; a zero-parameter CLI then uses target(), "
    "without also passing argv. Calls are call-1 through call-4. "
    "Compare failing and normal-control inputs using error absence AND intended-input "
    "processing evidence; empty output can hide skipped work. For diagnostic_rules, each "
    "call needs field/call_id/stable public code/role entries pairing failure expected false "
    "with processing expected true. Both JSON objects contain exactly these boolean fields. "
    "The host derives them from complete per-call stdout AND stderr; execute calls only, "
    "without an extractor or record_observation. With null rules, derive actual returned/output "
    "data for failure and processing, then record_observation(value) once (2048 UTF-8 bytes max). "
    "call exposes value/stdout/stderr/capture_status/exception/outcome/exit_code. "
    "Incomplete capture or unexpected setup/invocation/parse errors remain incomplete, never "
    "false/no-error. "
    + EXCEPTION_DESCRIPTION + " Returned is not task success; null exit_code is not zero. "
    "Record the bug as a value, not a failing assertion. Keep raw logs separate."
)


def description(environment_description: str) -> str:
    """Retain the exact public environment facts alongside first-call instructions."""
    return DESCRIPTION + " " + environment_description
