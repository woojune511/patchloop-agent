"""Offline v6 successor for sanitized SDK checker diagnostics.

Importing this module performs no Docker, dotenv, SDK, environment, network,
provider, evaluator, or agent observation.  The diagnostic runner is fully
injectable and has no CLI/approval/attempt integration in this source slice.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import d137_no_call_preflight as d137
from patchloop.evals import no_start_executable_preflight as v5
from patchloop.util import sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-diagnostic-successor-contract-v6"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-diagnostic-v6"
CONTRACT_PATH = Path("experiments/evaluator-v2-sanitized-sdk-diagnostic-v6.contract.json")

PREDECESSOR_TERMINAL_COMMIT = "3374e3452af2a615b5c3eb00e493354baabe9b09"
PREDECESSOR_PRESERVATION_COMMIT = "edb79b24221285a2bbaeeb02ca674d692c5edbac"
PREDECESSOR_TERMINAL_ID = (
    "ncpterminal_a7e12f36e75259ae00fe657ea0a96fde0a9826f58d77ffb1a7f091fff6902089"
)

RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_diagnostic_successor.py")
CHILD_PATH = Path("scripts/run_sanitized_sdk_diagnostic_child.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_diagnostic_successor.py")
TEST_PATH = Path("tests/test_sanitized_sdk_diagnostic_successor.py")
V5_RUNTIME_PATH = v5.RUNTIME_PATH
V5_TERMINAL_PATH = v5.TERMINAL_PATH
V5_APPROVAL_PATH = v5.APPROVAL_BINDING_PATH
OLD_CHILD_PATH = v5.CHILD_PATH
D137_PATH = v5.D137_PATH

QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-diagnostic-source-qualification-v6"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-diagnostic-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_SANITIZED_SDK_DIAGNOSTIC_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-diagnostic-v6-source-qualification.json"
)
NEXT_GATE = "diagnostic-runtime-integration-successor"

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (
            CONTRACT_PATH,
            RUNTIME_PATH,
            CHILD_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
        )
    )
)
SOURCE_FILES = tuple(
    sorted(
        (
            CONTRACT_PATH,
            RUNTIME_PATH,
            CHILD_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            V5_RUNTIME_PATH,
            V5_TERMINAL_PATH,
            V5_APPROVAL_PATH,
            OLD_CHILD_PATH,
            D137_PATH,
        ),
        key=lambda item: item.as_posix(),
    )
)


class SanitizedSDKDiagnosticError(ContractError):
    """The offline v6 diagnostic contract failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SanitizedSDKDiagnosticError(message)


def _repo_root(repository: str | Path | None) -> Path:
    return v5._repo_root(repository)


def _read_bytes(root: Path, relative: Path) -> bytes:
    return v5._read_bytes(root, relative)


def _canonical_bytes(value: FrozenStrictModel) -> bytes:
    return v5._canonical_bytes(value)


def _derived_id(prefix: str, content_hash: str) -> str:
    return v5._derived_id(prefix, content_hash)


def _semantic_hash(body: dict[str, Any]) -> str:
    return v5._semantic_hash(body)


class SDKDiagnosticStage(StrEnum):
    DEPENDENCY_BUILD = "dependency_build"
    PRESENCE = "presence"
    PYTHON_RESOLUTION = "python_resolution"
    PYTHON_BINDING = "python_binding"
    HTTPX_ORIGIN = "httpx_origin"
    OPENAI_ORIGIN = "openai_origin"
    HTTPX_PREIMPORT = "httpx_preimport"
    OPENAI_PREIMPORT = "openai_preimport"
    HTTPX_IMPORT = "httpx_import"
    OPENAI_IMPORT = "openai_import"
    HTTPX_LOADED_PROVENANCE = "httpx_loaded_provenance"
    OPENAI_LOADED_PROVENANCE = "openai_loaded_provenance"
    FACTORY_CONTRACT = "factory_contract"
    HTTPX_CLIENT = "httpx_client"
    OPENAI_CLIENT = "openai_client"
    PROBE_ASSERTIONS = "probe_assertions"
    CLIENT_CLOSE = "client_close"
    POST_PROBE_BINDINGS = "post_probe_bindings"
    AGGREGATE_VALIDATION = "aggregate_validation"
    INTERNAL_SANITIZER = "internal_sanitizer"
    COMPLETE = "complete"


STAGE_ORDER = tuple(SDKDiagnosticStage)


class SDKDiagnosticCode(StrEnum):
    READY = "ready"
    SDK_BLOCKED = "sdk_blocked"
    DEPENDENCY_BUILD_ERROR = "dependency_build_error"
    PRESENCE_ERROR = "presence_error"
    PYTHON_RESOLUTION_ERROR = "python_resolution_error"
    PYTHON_BINDING_ERROR = "python_binding_error"
    HTTPX_ORIGIN_ERROR = "httpx_origin_error"
    OPENAI_ORIGIN_ERROR = "openai_origin_error"
    HTTPX_PREIMPORT_ERROR = "httpx_preimport_error"
    OPENAI_PREIMPORT_ERROR = "openai_preimport_error"
    HTTPX_IMPORT_ERROR = "httpx_import_error"
    OPENAI_IMPORT_ERROR = "openai_import_error"
    HTTPX_LOADED_PROVENANCE_ERROR = "httpx_loaded_provenance_error"
    OPENAI_LOADED_PROVENANCE_ERROR = "openai_loaded_provenance_error"
    FACTORY_CONTRACT_ERROR = "factory_contract_error"
    HTTPX_CLIENT_ERROR = "httpx_client_error"
    OPENAI_CLIENT_ERROR = "openai_client_error"
    TRANSPORT_DISPATCH_REJECTED = "transport_dispatch_rejected"
    PROBE_ASSERTIONS_ERROR = "probe_assertions_error"
    CLIENT_CLOSE_ERROR = "client_close_error"
    POST_PROBE_BINDINGS_ERROR = "post_probe_bindings_error"
    AGGREGATE_VALIDATION_ERROR = "aggregate_validation_error"
    INTERNAL_SANITIZER_ERROR = "internal_sanitizer_error"


ERROR_CODE_BY_STAGE = {
    SDKDiagnosticStage.DEPENDENCY_BUILD: SDKDiagnosticCode.DEPENDENCY_BUILD_ERROR,
    SDKDiagnosticStage.PRESENCE: SDKDiagnosticCode.PRESENCE_ERROR,
    SDKDiagnosticStage.PYTHON_RESOLUTION: SDKDiagnosticCode.PYTHON_RESOLUTION_ERROR,
    SDKDiagnosticStage.PYTHON_BINDING: SDKDiagnosticCode.PYTHON_BINDING_ERROR,
    SDKDiagnosticStage.HTTPX_ORIGIN: SDKDiagnosticCode.HTTPX_ORIGIN_ERROR,
    SDKDiagnosticStage.OPENAI_ORIGIN: SDKDiagnosticCode.OPENAI_ORIGIN_ERROR,
    SDKDiagnosticStage.HTTPX_PREIMPORT: SDKDiagnosticCode.HTTPX_PREIMPORT_ERROR,
    SDKDiagnosticStage.OPENAI_PREIMPORT: SDKDiagnosticCode.OPENAI_PREIMPORT_ERROR,
    SDKDiagnosticStage.HTTPX_IMPORT: SDKDiagnosticCode.HTTPX_IMPORT_ERROR,
    SDKDiagnosticStage.OPENAI_IMPORT: SDKDiagnosticCode.OPENAI_IMPORT_ERROR,
    SDKDiagnosticStage.HTTPX_LOADED_PROVENANCE: (SDKDiagnosticCode.HTTPX_LOADED_PROVENANCE_ERROR),
    SDKDiagnosticStage.OPENAI_LOADED_PROVENANCE: (SDKDiagnosticCode.OPENAI_LOADED_PROVENANCE_ERROR),
    SDKDiagnosticStage.FACTORY_CONTRACT: SDKDiagnosticCode.FACTORY_CONTRACT_ERROR,
    SDKDiagnosticStage.HTTPX_CLIENT: SDKDiagnosticCode.HTTPX_CLIENT_ERROR,
    SDKDiagnosticStage.OPENAI_CLIENT: SDKDiagnosticCode.OPENAI_CLIENT_ERROR,
    SDKDiagnosticStage.PROBE_ASSERTIONS: SDKDiagnosticCode.PROBE_ASSERTIONS_ERROR,
    SDKDiagnosticStage.CLIENT_CLOSE: SDKDiagnosticCode.CLIENT_CLOSE_ERROR,
    SDKDiagnosticStage.POST_PROBE_BINDINGS: (SDKDiagnosticCode.POST_PROBE_BINDINGS_ERROR),
    SDKDiagnosticStage.AGGREGATE_VALIDATION: (SDKDiagnosticCode.AGGREGATE_VALIDATION_ERROR),
    SDKDiagnosticStage.INTERNAL_SANITIZER: SDKDiagnosticCode.INTERNAL_SANITIZER_ERROR,
}


class DiagnosticActivity(FrozenStrictModel):
    attempted_stages: tuple[SDKDiagnosticStage, ...]
    completed_stages: tuple[SDKDiagnosticStage, ...]
    credential_value_return_count: Literal[0] = 0
    credential_value_hash_prefix_or_length_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    transport_dispatch_count: int = Field(ge=0, le=1)
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0

    @model_validator(mode="after")
    def validate_stage_prefix(self) -> DiagnosticActivity:
        attempted = self.attempted_stages
        completed = self.completed_stages
        if len(set(attempted)) != len(attempted):
            raise ValueError("diagnostic attempted stages repeat")
        if tuple(stage for stage in STAGE_ORDER if stage in attempted) != attempted:
            raise ValueError("diagnostic attempted stages are not canonical")
        if completed != attempted[: len(completed)]:
            raise ValueError("diagnostic completed stages are not an attempted prefix")
        if len(completed) not in {len(attempted), max(0, len(attempted) - 1)}:
            raise ValueError("diagnostic stage completion differs")
        return self


class SanitizedSDKDiagnostic(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-diagnostic-v1"] = "sanitized-sdk-diagnostic-v1"
    state: Literal["ready", "blocked", "error"]
    stage: SDKDiagnosticStage
    code: SDKDiagnosticCode
    sdk_observation: dict[str, Any] | None = None
    activity: DiagnosticActivity
    raw_credential_value_returned: Literal[False] = False
    credential_hash_prefix_or_length_returned: Literal[False] = False
    exception_message_type_repr_or_traceback_returned: Literal[False] = False

    @model_validator(mode="after")
    def validate_semantics(self) -> SanitizedSDKDiagnostic:
        if not self.activity.attempted_stages:
            raise ValueError("diagnostic has no attempted stage")
        if self.stage != self.activity.attempted_stages[-1]:
            raise ValueError("diagnostic final stage differs")
        if self.sdk_observation is not None:
            try:
                d137.validate_d137_sdk_no_call_preflight_observation(self.sdk_observation)
            except ContractError as exc:
                raise ValueError("diagnostic SDK observation is invalid") from exc
        if self.state == "error":
            expected = ERROR_CODE_BY_STAGE.get(self.stage)
            if (
                self.sdk_observation is not None
                or expected is None
                or self.code not in {expected, SDKDiagnosticCode.TRANSPORT_DISPATCH_REJECTED}
                or len(self.activity.completed_stages) != len(self.activity.attempted_stages) - 1
            ):
                raise ValueError("diagnostic error state differs")
        else:
            if (
                self.stage != SDKDiagnosticStage.COMPLETE
                or self.sdk_observation is None
                or self.activity.completed_stages != self.activity.attempted_stages
            ):
                raise ValueError("diagnostic terminal state differs")
            passed = self.sdk_observation["passed"] is True
            if self.state == "ready" and (not passed or self.code != SDKDiagnosticCode.READY):
                raise ValueError("diagnostic ready state differs")
            if self.state == "blocked" and (passed or self.code != SDKDiagnosticCode.SDK_BLOCKED):
                raise ValueError("diagnostic blocked state differs")
        return self


class _StageFailure(Exception):
    def __init__(self, stage: SDKDiagnosticStage) -> None:
        self.stage = stage
        super().__init__(stage.value)


@dataclass
class _StageTracker:
    attempted: list[SDKDiagnosticStage]
    completed: list[SDKDiagnosticStage]

    @classmethod
    def create(cls) -> _StageTracker:
        return cls([], [])

    def call(self, stage: SDKDiagnosticStage, function: Any) -> Any:
        self.attempted.append(stage)
        try:
            value = function()
        except Exception:
            raise _StageFailure(stage) from None
        self.completed.append(stage)
        return value

    def extend(
        self,
        attempted: tuple[SDKDiagnosticStage, ...],
        completed: tuple[SDKDiagnosticStage, ...],
    ) -> None:
        self.attempted.extend(attempted)
        self.completed.extend(completed)


@dataclass(frozen=True)
class _ProbeOutcome:
    probe: dict[str, Any] | None
    attempted: tuple[SDKDiagnosticStage, ...]
    completed: tuple[SDKDiagnosticStage, ...]
    failure_stage: SDKDiagnosticStage | None
    failure_code: SDKDiagnosticCode | None
    transport_dispatch_count: int


def _safe_close(client: Any) -> bool:
    try:
        client.close()
    except Exception:
        return False
    return True


def _sanitized_probe(*, openai_module: ModuleType, httpx_module: ModuleType) -> _ProbeOutcome:
    attempted: list[SDKDiagnosticStage] = []
    completed: list[SDKDiagnosticStage] = []
    dispatch_count = 0

    def reject_dispatch(_request: Any) -> Any:
        nonlocal dispatch_count
        dispatch_count = 1
        raise SanitizedSDKDiagnosticError("synthetic transport dispatch rejected")

    attempted.append(SDKDiagnosticStage.HTTPX_CLIENT)
    try:
        transport = httpx_module.MockTransport(reject_dispatch)
        http_client = httpx_module.Client(transport=transport, trust_env=False)
    except Exception:
        return _ProbeOutcome(
            None,
            tuple(attempted),
            tuple(completed),
            SDKDiagnosticStage.HTTPX_CLIENT,
            SDKDiagnosticCode.HTTPX_CLIENT_ERROR,
            dispatch_count,
        )
    completed.append(SDKDiagnosticStage.HTTPX_CLIENT)

    openai_client: Any = None
    attempted.append(SDKDiagnosticStage.OPENAI_CLIENT)
    try:
        openai_client = openai_module.OpenAI(
            api_key="v6-fixed-nonsecret-placeholder",
            organization="v6-none",
            project="v6-none",
            webhook_secret="v6-none",
            base_url=d137.OFFICIAL_API_BASE_URL,
            max_retries=0,
            http_client=http_client,
        )
    except Exception:
        _safe_close(http_client)
        # Preserve the first failed stage.  Cleanup is best effort here because
        # reporting it as a second failed stage would violate the single-fault
        # prefix contract and obscure the constructor failure we are diagnosing.
        code = (
            SDKDiagnosticCode.TRANSPORT_DISPATCH_REJECTED
            if dispatch_count
            else SDKDiagnosticCode.OPENAI_CLIENT_ERROR
        )
        return _ProbeOutcome(
            None,
            tuple(attempted),
            tuple(completed),
            SDKDiagnosticStage.OPENAI_CLIENT,
            code,
            dispatch_count,
        )
    if dispatch_count:
        _safe_close(openai_client)
        return _ProbeOutcome(
            None,
            tuple(attempted),
            tuple(completed),
            SDKDiagnosticStage.OPENAI_CLIENT,
            SDKDiagnosticCode.TRANSPORT_DISPATCH_REJECTED,
            dispatch_count,
        )
    completed.append(SDKDiagnosticStage.OPENAI_CLIENT)

    attempted.append(SDKDiagnosticStage.PROBE_ASSERTIONS)
    try:
        base_url_exact = str(openai_client.base_url).rstrip("/") == d137.OFFICIAL_API_BASE_URL
        max_retries_zero = openai_client.max_retries == 0
    except Exception:
        _safe_close(openai_client)
        return _ProbeOutcome(
            None,
            tuple(attempted),
            tuple(completed),
            SDKDiagnosticStage.PROBE_ASSERTIONS,
            SDKDiagnosticCode.PROBE_ASSERTIONS_ERROR,
            dispatch_count,
        )
    completed.append(SDKDiagnosticStage.PROBE_ASSERTIONS)

    attempted.append(SDKDiagnosticStage.CLIENT_CLOSE)
    if not _safe_close(openai_client):
        return _ProbeOutcome(
            None,
            tuple(attempted),
            tuple(completed),
            SDKDiagnosticStage.CLIENT_CLOSE,
            SDKDiagnosticCode.CLIENT_CLOSE_ERROR,
            dispatch_count,
        )
    completed.append(SDKDiagnosticStage.CLIENT_CLOSE)
    http_client_closed = bool(http_client.is_closed)
    probe = {
        "transport_kind": "httpx.MockTransport-reject-dispatch",
        "fixed_nonsecret_placeholder_used": True,
        "ambient_credential_value_used": False,
        "official_base_url": d137.OFFICIAL_API_BASE_URL,
        "base_url_exact": base_url_exact,
        "trust_env": False,
        "max_retries": 0,
        "observed_max_retries_zero": max_retries_zero,
        "transport_dispatch_count": dispatch_count,
        "openai_client_close_call_count": 1,
        "http_client_fallback_close_call_count": 0,
        "http_client_closed": http_client_closed,
        "passed": bool(
            base_url_exact and max_retries_zero and dispatch_count == 0 and http_client_closed
        ),
    }
    return _ProbeOutcome(
        probe,
        tuple(attempted),
        tuple(completed),
        None,
        None,
        dispatch_count,
    )


def _diagnostic_activity(
    tracker: _StageTracker, *, transport_dispatch_count: int = 0
) -> DiagnosticActivity:
    return DiagnosticActivity(
        attempted_stages=tuple(tracker.attempted),
        completed_stages=tuple(tracker.completed),
        transport_dispatch_count=transport_dispatch_count,
    )


def _error_result(
    tracker: _StageTracker,
    failure: _StageFailure,
    *,
    code: SDKDiagnosticCode | None = None,
    transport_dispatch_count: int = 0,
) -> SanitizedSDKDiagnostic:
    return SanitizedSDKDiagnostic(
        state="error",
        stage=failure.stage,
        code=code or ERROR_CODE_BY_STAGE[failure.stage],
        activity=_diagnostic_activity(tracker, transport_dispatch_count=transport_dispatch_count),
    )


def _completed_result(
    tracker: _StageTracker, observation: dict[str, Any], *, transport_dispatch_count: int
) -> SanitizedSDKDiagnostic:
    tracker.call(SDKDiagnosticStage.COMPLETE, lambda: True)
    passed = observation["passed"] is True
    return SanitizedSDKDiagnostic(
        state="ready" if passed else "blocked",
        stage=SDKDiagnosticStage.COMPLETE,
        code=SDKDiagnosticCode.READY if passed else SDKDiagnosticCode.SDK_BLOCKED,
        sdk_observation=observation,
        activity=_diagnostic_activity(tracker, transport_dispatch_count=transport_dispatch_count),
    )


def _run_sanitized_sdk_diagnostic(
    *,
    repository: str | Path,
    dependency_factory: Callable[[], d137.SDKObservationDependencies],
) -> SanitizedSDKDiagnostic:
    """Run a fully injected, staged SDK diagnostic without exception text."""

    root = Path(repository).resolve(strict=True)
    tracker = _StageTracker.create()
    transport_dispatch_count = 0
    try:
        dependencies = tracker.call(
            SDKDiagnosticStage.DEPENDENCY_BUILD,
            dependency_factory,
        )
        presence = tracker.call(
            SDKDiagnosticStage.PRESENCE,
            lambda: {
                name: dependencies.environment_present(name) for name in d137.SDK_ENVIRONMENT_NAMES
            },
        )
        if not presence["OPENAI_API_KEY"] or presence["PYTHONHOME"] or presence["PYTHONPATH"]:
            observation = d137._presence_suppressed_sdk_result(presence)
            return _completed_result(
                tracker, observation, transport_dispatch_count=transport_dispatch_count
            )

        python_observation = tracker.call(
            SDKDiagnosticStage.PYTHON_RESOLUTION,
            lambda: d137._resolve_python_executable(root, dependencies),
        )
        if not python_observation["executable_under_repository_venv"]:
            observation = d137._python_suppressed_sdk_result(presence, python_observation)
            return _completed_result(
                tracker, observation, transport_dispatch_count=transport_dispatch_count
            )
        tracker.call(
            SDKDiagnosticStage.PYTHON_BINDING,
            lambda: d137._bind_python_executable(root, dependencies, python_observation),
        )

        httpx_origin = tracker.call(
            SDKDiagnosticStage.HTTPX_ORIGIN,
            lambda: d137._resolve_module_origin(root, name="httpx", dependencies=dependencies),
        )
        openai_origin = tracker.call(
            SDKDiagnosticStage.OPENAI_ORIGIN,
            lambda: d137._resolve_module_origin(root, name="openai", dependencies=dependencies),
        )
        origins = {"openai": openai_origin, "httpx": httpx_origin}
        if not d137._module_origins_ready(origins):
            observation = d137._module_origin_suppressed_sdk_result(
                presence, python_observation, origins
            )
            return _completed_result(
                tracker, observation, transport_dispatch_count=transport_dispatch_count
            )

        httpx_preimport = tracker.call(
            SDKDiagnosticStage.HTTPX_PREIMPORT,
            lambda: d137._bind_preimport_module(
                root, origin=origins["httpx"], dependencies=dependencies
            ),
        )
        openai_preimport = tracker.call(
            SDKDiagnosticStage.OPENAI_PREIMPORT,
            lambda: d137._bind_preimport_module(
                root, origin=origins["openai"], dependencies=dependencies
            ),
        )
        preimport = {"openai": openai_preimport, "httpx": httpx_preimport}
        if not d137._preimport_modules_ready(preimport):
            observation = d137._module_preimport_suppressed_sdk_result(
                presence, python_observation, preimport
            )
            return _completed_result(
                tracker, observation, transport_dispatch_count=transport_dispatch_count
            )

        httpx_module = tracker.call(
            SDKDiagnosticStage.HTTPX_IMPORT,
            lambda: dependencies.import_module("httpx"),
        )
        openai_module = tracker.call(
            SDKDiagnosticStage.OPENAI_IMPORT,
            lambda: dependencies.import_module("openai"),
        )
        httpx_provenance = tracker.call(
            SDKDiagnosticStage.HTTPX_LOADED_PROVENANCE,
            lambda: d137._loaded_module_provenance(
                root,
                name="httpx",
                module=httpx_module,
                preimport=preimport["httpx"],
            ),
        )
        openai_provenance = tracker.call(
            SDKDiagnosticStage.OPENAI_LOADED_PROVENANCE,
            lambda: d137._loaded_module_provenance(
                root,
                name="openai",
                module=openai_module,
                preimport=preimport["openai"],
            ),
        )
        modules = {"openai": openai_provenance, "httpx": httpx_provenance}
        production_factory = tracker.call(
            SDKDiagnosticStage.FACTORY_CONTRACT,
            lambda: d137._checked_in_openai_factory_contract(root),
        )
        probe_outcome = _sanitized_probe(openai_module=openai_module, httpx_module=httpx_module)
        tracker.extend(probe_outcome.attempted, probe_outcome.completed)
        transport_dispatch_count = probe_outcome.transport_dispatch_count
        if probe_outcome.failure_stage is not None:
            failure = _StageFailure(probe_outcome.failure_stage)
            return _error_result(
                tracker,
                failure,
                code=probe_outcome.failure_code,
                transport_dispatch_count=transport_dispatch_count,
            )
        _require(probe_outcome.probe is not None, "sanitized probe lacks result")

        def bind_after() -> None:
            python_after = dependencies.file_binding(dependencies.python_executable)
            d137._generic_file_binding(
                python_after, label="Python executable after diagnostic probe"
            )
            python_observation["executable_file_binding_after"] = python_after
            python_observation["executable_binding_stable"] = (
                python_observation["executable_file_binding_before"] == python_after
            )
            for name in ("openai", "httpx"):
                relative = modules[name]["repository_relative_path"]
                _require(isinstance(relative, str), "module path unavailable")
                binding = dependencies.file_binding(root / Path(relative))
                d137._generic_file_binding(binding, label=f"{name} module after probe")
                modules[name]["module_file_binding_after"] = binding
                modules[name]["module_binding_stable"] = (
                    modules[name]["module_file_binding_before"] == binding
                )

        tracker.call(SDKDiagnosticStage.POST_PROBE_BINDINGS, bind_after)

        def aggregate() -> dict[str, Any]:
            observation = {
                "environment_presence_bits": presence,
                "python": python_observation,
                "modules": modules,
                "production_client_factory": production_factory,
                "synthetic_probe": probe_outcome.probe,
            }
            checks = d137._sdk_checks(observation)
            blockers = d137._sdk_blockers(checks)
            result = {
                "schema_version": d137.SDK_OBSERVATION_SCHEMA,
                "phase": d137.SDK_PHASE,
                "status": (d137.SDK_READY_STATUS if not blockers else d137.SDK_BLOCKED_STATUS),
                "observer_contract": d137._sdk_observer_contract(),
                "observation": {**observation, "checks": checks},
                "blockers": blockers,
                "activity": {
                    "dynamic_module_import_count": 2,
                    "find_module_spec_count": 2,
                    "python_executable_file_binding_count": 2,
                    "sdk_module_file_binding_count": 4,
                    "distribution_version_observation_count": 2,
                    "locked_version_source_read_count": 2,
                    "checked_in_factory_source_read_count": 1,
                    "environment_presence_check_count": 3,
                    "environment_value_read_count": 0,
                    "dotenv_read_count": 0,
                    "synthetic_transport_dispatch_count": transport_dispatch_count,
                    "network_call_count": 0,
                    "provider_evaluator_or_agent_call_count": 0,
                    "openai_client_close_call_count": probe_outcome.probe[
                        "openai_client_close_call_count"
                    ],
                    "http_client_fallback_close_call_count": probe_outcome.probe[
                        "http_client_fallback_close_call_count"
                    ],
                    "http_client_closed": probe_outcome.probe["http_client_closed"],
                },
                "passed": not blockers,
            }
            return d137.validate_d137_sdk_no_call_preflight_observation(result)

        observation = tracker.call(SDKDiagnosticStage.AGGREGATE_VALIDATION, aggregate)
        return _completed_result(
            tracker, observation, transport_dispatch_count=transport_dispatch_count
        )
    except _StageFailure as failure:
        return _error_result(
            tracker,
            failure,
            transport_dispatch_count=transport_dispatch_count,
        )


def run_sanitized_sdk_diagnostic(
    *,
    repository: str | Path,
    dependency_factory: Callable[[], d137.SDKObservationDependencies],
) -> SanitizedSDKDiagnostic:
    """Return a fixed diagnostic even if an unclassified checker fault escapes."""

    try:
        return _run_sanitized_sdk_diagnostic(
            repository=repository,
            dependency_factory=dependency_factory,
        )
    except Exception:
        return SanitizedSDKDiagnostic(
            state="error",
            stage=SDKDiagnosticStage.INTERNAL_SANITIZER,
            code=SDKDiagnosticCode.INTERNAL_SANITIZER_ERROR,
            activity=DiagnosticActivity(
                attempted_stages=(SDKDiagnosticStage.INTERNAL_SANITIZER,),
                completed_stages=(),
                transport_dispatch_count=0,
            ),
        )


class V5TerminalBinding(FrozenStrictModel):
    terminal_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    preservation_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    terminal_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    outcome: Literal["error"] = "error"
    reason: Literal["checker_error"] = "checker_error"
    docker_ready: Literal[True] = True
    docker_cli_command_count: Literal[8] = 8
    dotenv_exact_subject_declared: Literal[True] = True
    dotenv_exact_subject_nonempty: Literal[True] = True
    dotenv_error_code: Literal["sdk_checker_error"] = "sdk_checker_error"
    credential_value_return_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    activity_accounting_complete: Literal[False] = False
    unknown_post_marker_activity_possible: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_commits(self) -> V5TerminalBinding:
        if (
            self.terminal_commit != PREDECESSOR_TERMINAL_COMMIT
            or self.preservation_commit != PREDECESSOR_PRESERVATION_COMMIT
            or self.terminal_id != PREDECESSOR_TERMINAL_ID
        ):
            raise ValueError("v6 predecessor identity drifted")
        return self


class DiagnosticProfile(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-diagnostic-profile-v1"] = (
        "sanitized-sdk-diagnostic-profile-v1"
    )
    child_path: Literal["scripts/run_sanitized_sdk_diagnostic_child.py"] = CHILD_PATH.as_posix()
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    old_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    d137_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v5_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exact_stages: tuple[str, ...] = tuple(stage.value for stage in STAGE_ORDER)
    exact_codes: tuple[str, ...] = tuple(code.value for code in SDKDiagnosticCode)
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_limit: Literal[0] = 0
    synthetic_transport_dispatch_limit: Literal[0] = 0
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    diagnostic_runtime_integration_implemented: Literal[False] = False
    approval_or_attempt_entrypoint_implemented: Literal[False] = False

    @model_validator(mode="after")
    def validate_enums(self) -> DiagnosticProfile:
        if self.exact_stages != tuple(stage.value for stage in STAGE_ORDER):
            raise ValueError("diagnostic stage profile drifted")
        if self.exact_codes != tuple(code.value for code in SDKDiagnosticCode):
            raise ValueError("diagnostic code profile drifted")
        return self


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    diagnostic_runtime_integration_authorized: Literal[False] = False
    state_binding_or_approval_authorized: Literal[False] = False
    docker_sdk_or_dotenv_observation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False


class SanitizedDiagnosticContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-diagnostic-successor-contract-v6"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-diagnostic-v6"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V5TerminalBinding
    profile: DiagnosticProfile
    source_authority: SourceAuthority
    next_gate: Literal["diagnostic-runtime-integration-successor"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> SanitizedDiagnosticContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v6 contract hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected):
            raise ValueError("v6 contract id mismatch")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (PREDECESSOR_PRESERVATION_COMMIT,):
            raise ValueError("v6 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v6 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    runtime_integration_or_approval_created: Literal[False] = False
    docker_sdk_dotenv_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-diagnostic-source-qualification-v6"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-sanitized-sdk-diagnostic-source-20260812-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_SANITIZED_SDK_DIAGNOSTIC_SOURCE_QUALIFIED_LIVE_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v5.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: v5.CommittedFileBinding
    runtime_file: v5.CommittedFileBinding
    child_file: v5.CommittedFileBinding
    predecessor_terminal_file: v5.CommittedFileBinding
    authority: QualificationAuthority
    next_gate: Literal["diagnostic-runtime-integration-successor"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v6 qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v6 qualification inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        projections = (
            (self.contract_file, CONTRACT_PATH),
            (self.runtime_file, RUNTIME_PATH),
            (self.child_file, CHILD_PATH),
            (self.predecessor_terminal_file, V5_TERMINAL_PATH),
        )
        if any(item != by_path.get(path.as_posix()) for item, path in projections):
            raise ValueError("v6 qualification projection differs")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("v6 qualification hash mismatch")
        return self


def _load_v5_chain(
    root: Path,
) -> tuple[
    v5.NoStartExecutableContract,
    v5.ApprovalBinding,
    v5.AttemptIntent,
    v5.ActionStarted,
    v5.TerminalTransition,
]:
    artifacts: tuple[tuple[str, Path, type[FrozenStrictModel]], ...] = (
        ("contract", v5.CONTRACT_PATH, v5.NoStartExecutableContract),
        ("approval", V5_APPROVAL_PATH, v5.ApprovalBinding),
        ("attempt", v5.ATTEMPT_PATH, v5.AttemptIntent),
        ("action", v5.ACTION_STARTED_PATH, v5.ActionStarted),
        ("terminal", V5_TERMINAL_PATH, v5.TerminalTransition),
    )
    values: dict[str, FrozenStrictModel] = {}
    raws: dict[str, bytes] = {}
    for label, path, model in artifacts:
        raw = _read_bytes(root, path)
        try:
            value = model.model_validate_json(raw)
        except (ValidationError, UnicodeDecodeError) as exc:
            raise SanitizedSDKDiagnosticError(f"v6 predecessor {label} is invalid") from exc
        _require(raw == _canonical_bytes(value), f"v6 predecessor {label} is not canonical")
        values[label] = value
        raws[label] = raw

    contract = values["contract"]
    approval = values["approval"]
    attempt = values["attempt"]
    action = values["action"]
    terminal = values["terminal"]
    _require(isinstance(contract, v5.NoStartExecutableContract), "v5 contract type differs")
    _require(isinstance(approval, v5.ApprovalBinding), "v5 approval type differs")
    _require(isinstance(attempt, v5.AttemptIntent), "v5 attempt type differs")
    _require(isinstance(action, v5.ActionStarted), "v5 action type differs")
    _require(isinstance(terminal, v5.TerminalTransition), "v5 terminal type differs")
    _require(approval.contract_id == contract.contract_id, "v5 approval contract differs")
    _require(attempt.contract_id == contract.contract_id, "v5 attempt contract differs")
    _require(attempt.approval_id == approval.approval_id, "v5 attempt approval differs")
    _require(action.attempt_id == attempt.attempt_id, "v5 action attempt differs")
    _require(
        terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id
        and terminal.previous_content_hash == action.content_hash,
        "v5 terminal chain differs",
    )
    _require(
        terminal.recorded_at >= action.recorded_at >= attempt.created_at,
        "v5 predecessor chronology differs",
    )
    committed_terminal = _git(
        root, "show", f"{PREDECESSOR_TERMINAL_COMMIT}:{V5_TERMINAL_PATH.as_posix()}"
    )
    _require(committed_terminal == raws["terminal"], "v5 committed terminal differs")
    preservation_row = (
        _git(root, "rev-list", "--parents", "-n", "1", PREDECESSOR_PRESERVATION_COMMIT)
        .decode("ascii")
        .split()
    )
    _require(
        preservation_row == [PREDECESSOR_PRESERVATION_COMMIT, PREDECESSOR_TERMINAL_COMMIT],
        "v5 preservation commit does not directly follow terminal",
    )
    return contract, approval, attempt, action, terminal


def _predecessor_binding(root: Path) -> V5TerminalBinding:
    contract, approval, attempt, action, terminal = _load_v5_chain(root)
    _require(terminal.docker_observation is not None, "v5 Docker observation missing")
    _require(terminal.sdk_observation is not None, "v5 SDK observation missing")
    _require(terminal.sdk_observation.child is not None, "v5 child observation missing")
    child = terminal.sdk_observation.child
    return V5TerminalBinding(
        terminal_commit=PREDECESSOR_TERMINAL_COMMIT,
        preservation_commit=PREDECESSOR_PRESERVATION_COMMIT,
        contract_id=contract.contract_id,
        approval_id=approval.approval_id,
        attempt_id=attempt.attempt_id,
        action_started_id=action.marker_id,
        terminal_id=terminal.terminal_id,
        terminal_content_hash=terminal.content_hash,
        docker_ready=terminal.docker_observation["passed"],
        docker_cli_command_count=terminal.docker_observation["activity"][
            "docker_cli_command_count"
        ],
        dotenv_exact_subject_declared=child.dotenv.exact_subject_declared,
        dotenv_exact_subject_nonempty=child.dotenv.exact_subject_nonempty,
        dotenv_error_code=child.dotenv.error_code,
        credential_value_return_count=child.activity.credential_value_return_count,
        network_call_count=child.activity.network_call_count,
        activity_accounting_complete=terminal.activity_accounting_complete,
        unknown_post_marker_activity_possible=terminal.unknown_post_marker_activity_possible,
        retry_or_resume_allowed=False,
    )


def _build_contract(root: Path) -> SanitizedDiagnosticContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "profile": DiagnosticProfile(
            child_file_sha256=sha256_bytes(_read_bytes(root, CHILD_PATH)),
            old_child_file_sha256=sha256_bytes(_read_bytes(root, OLD_CHILD_PATH)),
            d137_file_sha256=sha256_bytes(_read_bytes(root, D137_PATH)),
            v5_runtime_file_sha256=sha256_bytes(_read_bytes(root, V5_RUNTIME_PATH)),
        ).model_dump(mode="json"),
        "source_authority": SourceAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    content_hash = _semantic_hash(body)
    return SanitizedDiagnosticContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> SanitizedDiagnosticContract:
    root = _repo_root(repository)
    raw = _read_bytes(root, CONTRACT_PATH)
    try:
        contract = SanitizedDiagnosticContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKDiagnosticError("v6 contract artifact is invalid") from exc
    _require(raw == _canonical_bytes(contract), "v6 contract bytes are not canonical")
    _require(contract == _build_contract(root), "v6 contract has drifted")
    return contract


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    target = v5._logical_path(root, CONTRACT_PATH, must_exist=False)
    if target.exists():
        contract = load_contract(repository=root)
        raw = _read_bytes(root, CONTRACT_PATH)
    else:
        contract = _build_contract(root)
        raw = _canonical_bytes(contract)
        v5._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_SANITIZED_SDK_DIAGNOSTIC_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


def _git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SanitizedSDKDiagnosticError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v6 source parent binding failed")
    lines = (
        _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v6 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v5._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(item[0] for item in pairs)
    by_path = {item.path: item for item in files}
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(
        pairs[contract_index][1] == _canonical_bytes(contract),
        "committed v6 contract differs",
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "child_file": by_path[CHILD_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_terminal_file": by_path[V5_TERMINAL_PATH.as_posix()].model_dump(mode="json"),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=_semantic_hash(body))


def qualify_source(
    *, source_commit: str = "HEAD", repository: str | Path | None = None
) -> dict[str, Any]:
    root = _repo_root(repository)
    target = v5._logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if target.exists():
        return validate_source_qualification(repository=root)
    value = _build_qualification(root, source_commit=source_commit, recorded_at=datetime.now(UTC))
    v5._write_once(root, QUALIFICATION_PATH, _canonical_bytes(value))
    return validate_source_qualification(repository=root)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    raw = _read_bytes(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKDiagnosticError("v6 source qualification is invalid") from exc
    _require(raw == _canonical_bytes(value), "v6 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v6 source qualification has drifted")
    return {
        "status": value.status,
        "qualification_id": value.qualification_id,
        "source_commit": value.source_commit.commit,
        "source_tree": value.source_commit.tree,
        "contract_id": value.contract_id,
        "contract_content_hash": value.contract_content_hash,
        "source_qualification_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


__all__ = [
    "CHILD_PATH",
    "CONTRACT_PATH",
    "DiagnosticActivity",
    "DiagnosticProfile",
    "NEXT_GATE",
    "PREDECESSOR_PRESERVATION_COMMIT",
    "QUALIFICATION_PATH",
    "SDKDiagnosticCode",
    "SDKDiagnosticStage",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "SanitizedDiagnosticContract",
    "SanitizedSDKDiagnostic",
    "SanitizedSDKDiagnosticError",
    "SourceQualification",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "run_sanitized_sdk_diagnostic",
    "validate_source_qualification",
]
