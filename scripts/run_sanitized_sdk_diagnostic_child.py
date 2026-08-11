"""Isolated child for the versioned, sanitized SDK diagnostic successor.

Importing this module performs no dotenv, SDK, environment, transport, or
provider action.  The CLI is source-only in v6 and is not connected to an
approval, attempt, or terminal runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "isolated-dotenv-sanitized-sdk-diagnostic-v1"
SUBJECT = "OPENAI_API_KEY"


def _empty_dotenv(code: str) -> dict[str, Any]:
    return {
        "file_present": False,
        "exact_subject_declared": False,
        "exact_subject_nonempty": False,
        "duplicate_subject": False,
        "error_code": code,
        "raw_value_returned": False,
        "value_hash_prefix_or_length_returned": False,
    }


def _activity(dotenv_activity: dict[str, Any], diagnostic: dict[str, Any] | None) -> dict[str, Any]:
    diagnostic_activity = {} if diagnostic is None else diagnostic["activity"]
    return {
        "dotenv_file_read_count": int(dotenv_activity.get("dotenv_file_read_count", 0)),
        "dotenv_subject_membership_check_count": int(
            dotenv_activity.get("dotenv_subject_membership_check_count", 0)
        ),
        "credential_assignment_parse_count": int(
            dotenv_activity.get("credential_assignment_parse_count", 0)
        ),
        "credential_value_return_count": 0,
        "credential_value_hash_prefix_or_length_count": 0,
        "exception_message_type_repr_or_traceback_return_count": 0,
        "transport_dispatch_count": int(diagnostic_activity.get("transport_dispatch_count", 0)),
        "network_call_count": 0,
        "provider_evaluator_agent_call_count": 0,
    }


def _result(
    *,
    dotenv: dict[str, Any],
    dotenv_activity: dict[str, Any],
    diagnostic: dict[str, Any] | None,
    state: str,
    error_code: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "dotenv": dotenv,
        "diagnostic": diagnostic,
        "error_code": error_code,
        "activity": _activity(dotenv_activity, diagnostic),
        "raw_credential_value_returned": False,
        "credential_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def _top_level_failure(code: str) -> dict[str, Any]:
    return _result(
        dotenv=_empty_dotenv(code),
        dotenv_activity={},
        diagnostic=None,
        state="error",
        error_code=code,
    )


def _run(repository: Path) -> dict[str, Any]:
    root = repository.resolve(strict=True)
    sys.path.insert(0, str(root))
    try:
        from scripts.run_dotenv_sdk_no_call_child import _dotenv_membership
    except Exception:
        return _top_level_failure("dotenv_parser_import_error")

    dotenv_result, _read_count = _dotenv_membership(root / ".env")
    dotenv = dotenv_result["dotenv"]
    dotenv_activity = dotenv_result["activity"]
    if not dotenv["exact_subject_nonempty"] or dotenv["error_code"] is not None:
        return _result(
            dotenv=dotenv,
            dotenv_activity=dotenv_activity,
            diagnostic=None,
            state="blocked",
            error_code=dotenv["error_code"] or "dotenv_subject_empty",
        )

    try:
        from patchloop.evals import d137_no_call_preflight as d137
        from patchloop.evals import sanitized_sdk_diagnostic_successor as successor
    except Exception:
        return _result(
            dotenv=dotenv,
            dotenv_activity=dotenv_activity,
            diagnostic=None,
            state="error",
            error_code="diagnostic_runtime_import_error",
        )

    def dependency_factory() -> d137.SDKObservationDependencies:
        dependencies = d137._default_sdk_dependencies()

        def environment_present(name: str) -> bool:
            if name == SUBJECT:
                return True
            if name in {"PYTHONHOME", "PYTHONPATH"}:
                return False
            raise RuntimeError("unexpected environment subject")

        return replace(dependencies, environment_present=environment_present)

    diagnostic = successor.run_sanitized_sdk_diagnostic(
        repository=root,
        dependency_factory=dependency_factory,
    ).model_dump(mode="json")
    return _result(
        dotenv=dotenv,
        dotenv_activity=dotenv_activity,
        diagnostic=diagnostic,
        state=diagnostic["state"],
        error_code=(None if diagnostic["state"] == "ready" else diagnostic["code"]),
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    try:
        result = _run(Path(args.repository))
    except Exception:
        result = _top_level_failure("isolated_diagnostic_error")
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    main()
