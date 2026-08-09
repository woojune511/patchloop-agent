"""D-128 Docker remediation for an already-running Linux daemon only.

This helper deliberately has no Docker Desktop launch, daemon polling, or
container/workload path.  It reuses the D-127 bounded Docker command boundary
for one readiness observation, pulls only an exact digest whose inspect result
is the exact confirmed-absence projection, and then observes readiness once
more.  A missing daemon is a terminal blocked observation, not a start trigger.
"""

from __future__ import annotations

from typing import Any

from patchloop.errors import ContractError
from patchloop.evals import d127_docker_remediation as d127

SCHEMA_VERSION = "d128-already-running-docker-remediation-observation-v1"

APPROVED_CLI_VERSION = "29.6.2"
APPROVED_CLI_BYTES = 43_095_472
APPROVED_CLI_SHA256 = "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
LOCAL_DOCKER_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"
EXACT_DOCKER_IMAGES = (
    "docker.io/swerebenchv2/getmoto-moto@"
    "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee",
    "docker.io/swerebenchv2/python-babel-babel@"
    "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a",
)

DAEMON_UNAVAILABLE_BLOCKER = "already-running-docker-desktop-linux-daemon-unavailable"
OUTPUT_BOUND_BLOCKER = "docker-command-output-bound-exceeded"
PULL_FAILED_BLOCKER = "exact-approved-image-pull-failed"
READINESS_BLOCKER = "exact-docker-readiness-not-established"

_OBSERVATION_KEYS = (
    "schema_version",
    "forced_daemon_endpoint",
    "approved_cli_binding_before",
    "approved_cli_binding_after",
    "daemon_start_attempted",
    "daemon_start_count",
    "exact_authorized_images",
    "before",
    "pull_basis",
    "after",
    "after_observation_performed",
    "pulled_images",
    "observed_blockers",
    "commands",
    "docker_cli_command_count",
    "read_only_daemon_or_image_call_count",
    "image_pull_call_count",
    "image_store_mutation_count",
    "container_create_start_run_exec_count",
    "docker_workload_call_count",
    "every_output_within_bound",
    "pull_commands_succeeded",
    "passed",
    "raw_stdout_or_stderr_persisted",
)


class D128DockerNoStartRemediationError(ContractError):
    """The D-128 already-running-daemon contract failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D128DockerNoStartRemediationError(message)


def _require_d127_low_level_contract() -> None:
    _require(
        d127.APPROVED_CLI_VERSION == APPROVED_CLI_VERSION
        and d127.APPROVED_CLI_BYTES == APPROVED_CLI_BYTES
        and d127.APPROVED_CLI_SHA256 == APPROVED_CLI_SHA256,
        "D-128 approved Docker CLI contract differs",
    )
    _require(
        d127.LOCAL_DOCKER_ENDPOINT == LOCAL_DOCKER_ENDPOINT
        and tuple(d127.DOCKER_IMAGES) == EXACT_DOCKER_IMAGES,
        "D-128 Docker endpoint or exact image contract differs",
    )
    _require(
        d127.ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE is False,
        "D-128 imported Docker helper permits daemon start",
    )


def _validate_with_d127(function: Any, value: Any, *, label: str) -> None:
    try:
        function(value)
    except ContractError as exc:
        raise D128DockerNoStartRemediationError(
            f"D-128 {label} failed D-127 bounded replay"
        ) from exc


def _readiness_rows(value: dict[str, Any], rows: list[dict[str, Any]], *, label: str) -> None:
    try:
        d127._validate_readiness_rows(value, rows)
    except ContractError as exc:
        raise D128DockerNoStartRemediationError(
            f"D-128 {label} rows failed bounded replay"
        ) from exc


def _validate_live_readiness(
    value: dict[str, Any], rows: list[dict[str, Any]], *, label: str
) -> None:
    _validate_with_d127(d127._validate_readiness, value, label=f"{label} readiness")
    _require(len(rows) == 3, f"D-128 {label} command count differs")
    for row in rows:
        _validate_with_d127(d127._validate_command_row, row, label=f"{label} command row")
    _require(
        [row["role"] for row in rows] == ["daemon-version", "image-moto", "image-babel"],
        f"D-128 {label} command order differs",
    )
    _readiness_rows(value, rows, label=label)


def _pull_roles(value: dict[str, Any]) -> list[str]:
    images = value["images"]
    return [
        f"pull-{key}" for key in ("moto", "babel") if d127._image_is_confirmed_absent(images[key])
    ]


def _successful_pulled_images(rows: list[dict[str, Any]]) -> list[str]:
    by_role = {"pull-moto": EXACT_DOCKER_IMAGES[0], "pull-babel": EXACT_DOCKER_IMAGES[1]}
    return [
        by_role[row["role"]]
        for row in rows
        if row["return_code"] == 0
        and row["timed_out"] is False
        and row["stdout_within_bound"] is True
        and row["stderr_within_bound"] is True
        and row["stderr_bytes"] == 0
    ]


def _derived_blockers(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    after_observation_performed: bool,
    within_bound: bool,
    pulls_succeeded: bool,
) -> list[str]:
    if before["daemon"] is None:
        return [DAEMON_UNAVAILABLE_BLOCKER]
    blockers: list[str] = []
    if not within_bound:
        blockers.append(OUTPUT_BOUND_BLOCKER)
    if not pulls_succeeded:
        blockers.append(PULL_FAILED_BLOCKER)
    if not after_observation_performed or after["passed"] is not True:
        blockers.append(READINESS_BLOCKER)
    return blockers


def approved_cli_binding() -> dict[str, Any]:
    """Return the exact approved CLI binding without invoking Docker."""

    _require_d127_low_level_contract()
    try:
        return d127.approved_cli_binding()
    except ContractError as exc:
        raise D128DockerNoStartRemediationError(
            "D-128 approved Docker CLI binding differs"
        ) from exc


def observe_docker_readiness() -> dict[str, Any]:
    """Observe the local daemon and exact images without mutation or daemon start."""

    _require_d127_low_level_contract()
    try:
        value = d127.observe_docker_readiness()
    except ContractError as exc:
        raise D128DockerNoStartRemediationError(
            "D-128 read-only Docker observation failed"
        ) from exc
    return validate_docker_readiness_snapshot(value)


def validate_docker_readiness_snapshot(value: Any) -> dict[str, Any]:
    """Replay the delegated D-127 read-only snapshot contract without Docker."""

    _require_d127_low_level_contract()
    try:
        return d127.validate_docker_readiness_snapshot(value)
    except ContractError as exc:
        raise D128DockerNoStartRemediationError(
            "D-128 read-only Docker snapshot failed bounded replay"
        ) from exc


def remediate_already_running_docker_environment() -> dict[str, Any]:
    """Pull exact missing images without ever starting or polling the daemon."""

    _require_d127_low_level_contract()
    with d127._isolated_docker_config():
        cli_before = approved_cli_binding()
        before, before_rows = d127._observe_readiness()
        _validate_live_readiness(before, before_rows, label="initial readiness")
        pull_rows: list[dict[str, Any]] = []
        pulled_images: list[str] = []
        after_observation_performed = False
        after = before
        after_rows: list[dict[str, Any]] = []

        if before["daemon"] is not None:
            for role, image in zip(("pull-moto", "pull-babel"), EXACT_DOCKER_IMAGES, strict=True):
                key = role.removeprefix("pull-")
                if not d127._image_is_confirmed_absent(before["images"].get(key)):
                    continue
                result = d127._docker_command(
                    "image",
                    "pull",
                    "--quiet",
                    "--platform",
                    "linux/amd64",
                    image,
                    timeout_seconds=1_200,
                )
                pull_rows.append(result.summary(role))
                if (
                    result.return_code == 0
                    and result.timed_out is False
                    and result.within_bound
                    and result.stderr_bytes == 0
                ):
                    pulled_images.append(image)
            after, after_rows = d127._observe_readiness()
            _validate_live_readiness(after, after_rows, label="final readiness")
            after_observation_performed = True

        cli_after = approved_cli_binding()

    _require(cli_before == cli_after, "D-128 Docker CLI changed during no-start remediation")
    commands = [*before_rows, *pull_rows, *after_rows]
    within_bound = all(
        row["stdout_within_bound"] and row["stderr_within_bound"] for row in commands
    )
    pulls_succeeded = all(
        row["return_code"] == 0
        and row["timed_out"] is False
        and row["stdout_within_bound"]
        and row["stderr_within_bound"]
        and row["stderr_bytes"] == 0
        for row in pull_rows
    )
    blockers = _derived_blockers(
        before=before,
        after=after,
        after_observation_performed=after_observation_performed,
        within_bound=within_bound,
        pulls_succeeded=pulls_succeeded,
    )
    passed = (
        before["daemon"] is not None
        and after_observation_performed
        and after["passed"] is True
        and within_bound
        and pulls_succeeded
        and len(pulled_images) == len(pull_rows)
        and not blockers
    )
    observation = {
        "schema_version": SCHEMA_VERSION,
        "forced_daemon_endpoint": LOCAL_DOCKER_ENDPOINT,
        "approved_cli_binding_before": cli_before,
        "approved_cli_binding_after": cli_after,
        "daemon_start_attempted": False,
        "daemon_start_count": 0,
        "exact_authorized_images": list(EXACT_DOCKER_IMAGES),
        "before": before,
        "pull_basis": before,
        "after": after,
        "after_observation_performed": after_observation_performed,
        "pulled_images": pulled_images,
        "observed_blockers": blockers,
        "commands": commands,
        "docker_cli_command_count": len(commands),
        "read_only_daemon_or_image_call_count": len(before_rows) + len(after_rows),
        "image_pull_call_count": len(pull_rows),
        "image_store_mutation_count": len(pull_rows),
        "container_create_start_run_exec_count": 0,
        "docker_workload_call_count": 0,
        "every_output_within_bound": within_bound,
        "pull_commands_succeeded": pulls_succeeded,
        "passed": passed,
        "raw_stdout_or_stderr_persisted": False,
    }
    return validate_docker_no_start_remediation_observation(observation)


def validate_docker_no_start_remediation_observation(value: Any) -> dict[str, Any]:
    """Replay a D-128 no-start remediation observation without invoking Docker."""

    _require_d127_low_level_contract()
    _require(
        isinstance(value, dict) and tuple(value) == _OBSERVATION_KEYS,
        "D-128 no-start remediation fields differ",
    )
    _require(value["schema_version"] == SCHEMA_VERSION, "D-128 schema differs")
    _require(
        value["forced_daemon_endpoint"] == LOCAL_DOCKER_ENDPOINT,
        "D-128 forced Docker endpoint differs",
    )
    try:
        d127._validate_file_binding(value["approved_cli_binding_before"], desktop=False)
        d127._validate_file_binding(value["approved_cli_binding_after"], desktop=False)
    except ContractError as exc:
        raise D128DockerNoStartRemediationError(
            "D-128 Docker CLI binding failed bounded replay"
        ) from exc
    _require(
        value["approved_cli_binding_before"] == value["approved_cli_binding_after"],
        "D-128 Docker CLI stability differs",
    )
    _require(value["daemon_start_attempted"] is False, "D-128 daemon start was attempted")
    _require(
        type(value["daemon_start_count"]) is int and value["daemon_start_count"] == 0,
        "D-128 daemon start count differs",
    )
    _require(
        value["exact_authorized_images"] == list(EXACT_DOCKER_IMAGES),
        "D-128 exact image scope differs",
    )

    for label in ("before", "pull_basis", "after"):
        _validate_with_d127(d127._validate_readiness, value[label], label=f"{label} readiness")
    _require(value["pull_basis"] == value["before"], "D-128 pull basis differs")
    _require(
        type(value["after_observation_performed"]) is bool,
        "D-128 after-observation flag differs",
    )

    rows = value["commands"]
    _require(isinstance(rows, list), "D-128 command rows are not a list")
    for row in rows:
        _validate_with_d127(d127._validate_command_row, row, label="command row")
    before_roles = ["daemon-version", "image-moto", "image-babel"]
    _require(
        [row["role"] for row in rows[:3]] == before_roles,
        "D-128 initial readiness command order differs",
    )
    _readiness_rows(value["before"], rows[:3], label="initial readiness")

    daemon_available = value["before"]["daemon"] is not None
    expected_pull_roles = _pull_roles(value["before"]) if daemon_available else []
    expected_roles = [*before_roles]
    if daemon_available:
        expected_roles.extend(expected_pull_roles)
        expected_roles.extend(before_roles)
    _require(
        [row["role"] for row in rows] == expected_roles,
        "D-128 no-start Docker argv sequence differs",
    )
    pull_rows = rows[3 : 3 + len(expected_pull_roles)]
    if daemon_available:
        _require(
            value["after_observation_performed"] is True,
            "D-128 ready-daemon path omitted final observation",
        )
        _readiness_rows(value["after"], rows[-3:], label="final readiness")
    else:
        _require(
            value["after_observation_performed"] is False and value["after"] == value["before"],
            "D-128 daemon-absent path did not stop immediately",
        )

    _require(
        isinstance(value["pulled_images"], list)
        and value["pulled_images"] == _successful_pulled_images(pull_rows),
        "D-128 successful pulled-image evidence differs",
    )
    _require(
        len(value["pulled_images"]) == len(set(value["pulled_images"]))
        and set(value["pulled_images"]).issubset(EXACT_DOCKER_IMAGES),
        "D-128 pulled image scope differs",
    )
    within_bound = all(row["stdout_within_bound"] and row["stderr_within_bound"] for row in rows)
    pulls_succeeded = all(
        row["return_code"] == 0
        and row["timed_out"] is False
        and row["stdout_within_bound"]
        and row["stderr_within_bound"]
        and row["stderr_bytes"] == 0
        for row in pull_rows
    )
    blockers = _derived_blockers(
        before=value["before"],
        after=value["after"],
        after_observation_performed=value["after_observation_performed"],
        within_bound=within_bound,
        pulls_succeeded=pulls_succeeded,
    )
    _require(
        value["observed_blockers"] == blockers,
        "D-128 no-start blocker evidence differs",
    )
    _require(
        type(value["docker_cli_command_count"]) is int
        and value["docker_cli_command_count"] == len(rows),
        "D-128 Docker CLI command count differs",
    )
    expected_read_calls = 6 if daemon_available else 3
    _require(
        type(value["read_only_daemon_or_image_call_count"]) is int
        and value["read_only_daemon_or_image_call_count"] == expected_read_calls,
        "D-128 read-only Docker call count differs",
    )
    _require(
        type(value["image_pull_call_count"]) is int
        and value["image_pull_call_count"] == len(pull_rows)
        and type(value["image_store_mutation_count"]) is int
        and value["image_store_mutation_count"] == len(pull_rows),
        "D-128 image pull count differs",
    )
    _require(
        type(value["container_create_start_run_exec_count"]) is int
        and value["container_create_start_run_exec_count"] == 0,
        "D-128 container action count differs",
    )
    _require(
        type(value["docker_workload_call_count"]) is int
        and value["docker_workload_call_count"] == 0,
        "D-128 workload count differs",
    )
    _require(
        value["every_output_within_bound"] is within_bound,
        "D-128 output-bound result differs",
    )
    _require(
        value["pull_commands_succeeded"] is pulls_succeeded,
        "D-128 pull result differs",
    )
    expected_passed = (
        daemon_available
        and value["after_observation_performed"] is True
        and value["after"]["passed"] is True
        and within_bound
        and pulls_succeeded
        and len(value["pulled_images"]) == len(pull_rows)
        and not blockers
    )
    _require(value["passed"] is expected_passed, "D-128 remediation result differs")
    _require(
        value["raw_stdout_or_stderr_persisted"] is False,
        "D-128 raw-output boundary differs",
    )
    return value


__all__ = [
    "APPROVED_CLI_BYTES",
    "APPROVED_CLI_SHA256",
    "APPROVED_CLI_VERSION",
    "DAEMON_UNAVAILABLE_BLOCKER",
    "D128DockerNoStartRemediationError",
    "EXACT_DOCKER_IMAGES",
    "LOCAL_DOCKER_ENDPOINT",
    "approved_cli_binding",
    "observe_docker_readiness",
    "remediate_already_running_docker_environment",
    "validate_docker_no_start_remediation_observation",
    "validate_docker_readiness_snapshot",
]
