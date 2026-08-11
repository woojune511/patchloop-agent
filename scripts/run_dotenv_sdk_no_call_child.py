"""Isolated child for one-key dotenv membership and SDK no-transport checks."""

from __future__ import annotations

import argparse
import json
import stat
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "isolated-dotenv-sdk-no-call-observation-v1"
MAX_DOTENV_BYTES = 65_536
MAX_LINE_CHARACTERS = 16_384
SUBJECT = "OPENAI_API_KEY"


def _fixed_failure(
    code: str,
    *,
    file_present: bool,
    dotenv_file_read_count: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "dotenv": {
            "file_present": file_present,
            "exact_subject_declared": False,
            "exact_subject_nonempty": False,
            "duplicate_subject": False,
            "error_code": code,
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        "sdk_observation": None,
        "activity": {
            "dotenv_file_read_count": dotenv_file_read_count,
            "dotenv_subject_membership_check_count": 0,
            "credential_assignment_parse_count": 0,
            "credential_value_return_count": 0,
            "credential_value_hash_prefix_or_length_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
    }


def _dotenv_membership(path: Path) -> tuple[dict[str, Any], int]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return _fixed_failure("dotenv_missing", file_present=False), 0
    except OSError:
        return _fixed_failure("dotenv_stat_error", file_present=False), 0
    linklike = stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & 0x400
    )
    if linklike or not stat.S_ISREG(metadata.st_mode):
        return _fixed_failure("dotenv_not_regular_file", file_present=True), 0
    if metadata.st_size > MAX_DOTENV_BYTES:
        return _fixed_failure("dotenv_size_limit", file_present=True), 0
    try:
        raw = path.read_bytes()
        after = path.stat()
    except OSError:
        return _fixed_failure(
            "dotenv_read_error",
            file_present=True,
            dotenv_file_read_count=1,
        ), 1
    if (metadata.st_size, metadata.st_mtime_ns, metadata.st_ino) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ino,
    ):
        return _fixed_failure(
            "dotenv_changed_during_read",
            file_present=True,
            dotenv_file_read_count=1,
        ), 1
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return _fixed_failure(
            "dotenv_not_utf8",
            file_present=True,
            dotenv_file_read_count=1,
        ), 1
    declared = False
    nonempty = False
    duplicate = False
    assignment_parse_count = 0
    error_code: str | None = None
    try:
        for source_line in text.splitlines():
            if len(source_line) > MAX_LINE_CHARACTERS:
                error_code = "dotenv_line_limit"
                break
            line = source_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() != SUBJECT:
                continue
            assignment_parse_count += 1
            if declared:
                duplicate = True
                error_code = "dotenv_duplicate_subject"
                nonempty = False
                break
            declared = True
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            nonempty = bool(value)
            value = ""
            line = ""
            source_line = ""
    except Exception:
        error_code = "dotenv_parse_error"
        declared = False
        nonempty = False
    finally:
        raw = b""
        text = ""
    result = {
        "schema_version": SCHEMA_VERSION,
        "dotenv": {
            "file_present": True,
            "exact_subject_declared": declared,
            "exact_subject_nonempty": nonempty,
            "duplicate_subject": duplicate,
            "error_code": error_code,
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        "sdk_observation": None,
        "activity": {
            "dotenv_file_read_count": 1,
            "dotenv_subject_membership_check_count": 1,
            "credential_assignment_parse_count": assignment_parse_count,
            "credential_value_return_count": 0,
            "credential_value_hash_prefix_or_length_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
    }
    return result, 1


def _run(repository: Path) -> dict[str, Any]:
    root = repository.resolve(strict=True)
    dotenv = root / ".env"
    try:
        dotenv.relative_to(root)
    except ValueError:
        return _fixed_failure("dotenv_path_escape", file_present=False)
    result, _read_count = _dotenv_membership(dotenv)
    if not result["dotenv"]["exact_subject_nonempty"] or result["dotenv"]["error_code"]:
        return result

    sys.path.insert(0, str(root))
    try:
        from patchloop.evals import d137_no_call_preflight as d137

        dependencies = d137._default_sdk_dependencies()

        def environment_present(name: str) -> bool:
            if name == SUBJECT:
                return True
            if name in {"PYTHONHOME", "PYTHONPATH"}:
                return False
            raise RuntimeError("unexpected environment subject")

        isolated = replace(dependencies, environment_present=environment_present)
        sdk = d137.run_d137_sdk_no_call_preflight_observation(
            repository=root,
            dependencies=isolated,
        )
    except Exception:
        result["dotenv"]["error_code"] = "sdk_checker_error"
        return result
    result["sdk_observation"] = sdk
    result["activity"]["network_call_count"] = sdk["activity"]["network_call_count"]
    result["activity"]["provider_evaluator_agent_call_count"] = sdk["activity"][
        "provider_evaluator_or_agent_call_count"
    ]
    return result


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    try:
        result = _run(Path(args.repository))
    except Exception:
        result = _fixed_failure("isolated_checker_error", file_present=False)
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    main()
