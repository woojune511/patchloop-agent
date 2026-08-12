"""Value-free staged import diagnostic for the v8 SDK bootstrap successor.

The module itself has a stdlib-only import surface.  It does not read ``.env``
or construct/probe an SDK client.  Its staged project imports may recursively
load the OpenAI package, which is counted as 0/1.  A future parent must supply
``SYSTEMROOT`` inside an isolated child environment; this diagnostic returns
only presence booleans and fixed stage codes, never the value or an exception
representation.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

SCHEMA_VERSION = "sanitized-sdk-import-bootstrap-observation-v1"
SUBJECT = "SYSTEMROOT"

IMPORT_STAGES = (
    ("dotenv_parser", "scripts.run_dotenv_sdk_no_call_child"),
    ("d137_runtime", "patchloop.evals.d137_no_call_preflight"),
    ("versioned_preflight", "patchloop.evals.versioned_no_call_preflight"),
    ("executable_preflight", "patchloop.evals.executable_no_call_preflight"),
    ("manual_start_preflight", "patchloop.evals.manual_docker_start_state_successor"),
    ("no_start_preflight", "patchloop.evals.no_start_executable_preflight"),
    ("sanitized_diagnostic", "patchloop.evals.sanitized_sdk_diagnostic_successor"),
)
STAGE_ORDER = ("systemroot_presence", *(stage for stage, _module in IMPORT_STAGES), "complete")
ERROR_CODE_BY_STAGE = {
    "systemroot_presence": "systemroot_presence_error",
    **{stage: f"{stage}_import_error" for stage, _module in IMPORT_STAGES},
}
EXACT_CODES = (
    "ready",
    "systemroot_presence_error",
    "systemroot_missing",
    "systemroot_empty",
    *(ERROR_CODE_BY_STAGE[stage] for stage, _module in IMPORT_STAGES),
    "internal_sanitizer_error",
)

EnvironmentValue = Callable[[str], str | None]
ModuleImporter = Callable[[str], ModuleType]
PackagePresence = Callable[[], bool]


def _observation(
    *,
    state: str,
    stage: str,
    code: str,
    attempted_stages: tuple[str, ...],
    completed_stages: tuple[str, ...],
    systemroot_present: bool,
    systemroot_nonempty: bool,
    sdk_package_import_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "stage": stage,
        "code": code,
        "attempted_stages": attempted_stages,
        "completed_stages": completed_stages,
        "systemroot_present": systemroot_present,
        "systemroot_nonempty": systemroot_nonempty,
        "systemroot_value_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "activity": {
            "systemroot_membership_check_count": 1,
            "systemroot_nonempty_check_count": int(systemroot_present),
            "import_attempt_count": sum(
                stage_name not in {"systemroot_presence", "complete"}
                for stage_name in attempted_stages
            ),
            "import_completed_count": sum(
                stage_name not in {"systemroot_presence", "complete"}
                for stage_name in completed_stages
            ),
            "environment_value_return_count": 0,
            "exception_message_type_repr_or_traceback_return_count": 0,
            "dotenv_file_read_count": 0,
            "sdk_package_import_count": sdk_package_import_count,
            "sdk_client_or_probe_count": 0,
            "transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
    }


def diagnose_import_bootstrap(
    *,
    environment_value: EnvironmentValue,
    import_module: ModuleImporter,
    sdk_package_present: PackagePresence = lambda: "openai" in sys.modules,
) -> dict[str, Any]:
    """Diagnose only the fixed pre-SDK import chain with sanitized output."""

    attempted = ["systemroot_presence"]
    completed: list[str] = []
    try:
        systemroot = environment_value(SUBJECT)
    except BaseException:
        return _observation(
            state="error",
            stage="systemroot_presence",
            code="systemroot_presence_error",
            attempted_stages=tuple(attempted),
            completed_stages=tuple(completed),
            systemroot_present=False,
            systemroot_nonempty=False,
            sdk_package_import_count=int(sdk_package_present()),
        )
    present = systemroot is not None
    nonempty = bool(systemroot) if present else False
    del systemroot
    completed.append("systemroot_presence")
    if not present or not nonempty:
        return _observation(
            state="blocked",
            stage="systemroot_presence",
            code="systemroot_missing" if not present else "systemroot_empty",
            attempted_stages=tuple(attempted),
            completed_stages=tuple(completed),
            systemroot_present=present,
            systemroot_nonempty=nonempty,
            sdk_package_import_count=int(sdk_package_present()),
        )

    for stage, module_name in IMPORT_STAGES:
        attempted.append(stage)
        try:
            import_module(module_name)
        except BaseException:
            return _observation(
                state="error",
                stage=stage,
                code=ERROR_CODE_BY_STAGE[stage],
                attempted_stages=tuple(attempted),
                completed_stages=tuple(completed),
                systemroot_present=True,
                systemroot_nonempty=True,
                sdk_package_import_count=int(sdk_package_present()),
            )
        completed.append(stage)

    attempted.append("complete")
    completed.append("complete")
    return _observation(
        state="ready",
        stage="complete",
        code="ready",
        attempted_stages=tuple(attempted),
        completed_stages=tuple(completed),
        systemroot_present=True,
        systemroot_nonempty=True,
        sdk_package_import_count=int(sdk_package_present()),
    )


def _internal_error() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "error",
        "stage": "systemroot_presence",
        "code": "internal_sanitizer_error",
        "attempted_stages": ("systemroot_presence",),
        "completed_stages": (),
        "systemroot_present": False,
        "systemroot_nonempty": False,
        "systemroot_value_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "activity": {
            "systemroot_membership_check_count": 0,
            "systemroot_nonempty_check_count": 0,
            "import_attempt_count": 0,
            "import_completed_count": 0,
            "environment_value_return_count": 0,
            "exception_message_type_repr_or_traceback_return_count": 0,
            "dotenv_file_read_count": 0,
            "sdk_package_import_count": 0,
            "sdk_client_or_probe_count": 0,
            "transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    try:
        root = Path(args.repository).resolve(strict=True)
        sys.path.insert(0, str(root))
        result = diagnose_import_bootstrap(
            environment_value=os.environ.get,
            import_module=importlib.import_module,
        )
    except BaseException:
        result = _internal_error()
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    main()
