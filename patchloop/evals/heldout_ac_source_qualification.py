"""Offline source qualification for the execution-closed held-out A/C contract.

This gate binds only metadata, contract code, deterministic completion/analysis
code, and their offline validation.  It intentionally does not load task
packages or private markers and cannot create task/evaluator bindings, a live
candidate, approval, reservation, or any runtime authority.

R1 is retained byte-for-byte as a zero-authority predecessor invalidated by a
concurrent pre-seal source extraction.  R2 validates those immutable bytes and
replays only the current dedicated held-out contract source.
"""

from __future__ import annotations

import ast
import json
import os
import stat
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.util import resolve_name
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.runtime import repository_root
from patchloop.util import (
    load_unique_yaml,
    safe_relative_path,
    sha256_bytes,
    sha256_json,
)

SCHEMA_VERSION = "heldout-ac-contract-source-qualification-v2"
QUALIFICATION_ID = "core-ac-fixed-bundle-heldout-contract-source-qualification-20260814-r2"
STATUS = "OFFLINE_CONTRACT_SOURCE_QUALIFIED_TASK_EVALUATOR_BINDING_CLOSED"

PREREGISTRATION_PATH = Path("experiments/heldout-ac-preregistration-20260814-v1.yaml")
SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
PLAN_PATH = Path("experiments/heldout-ac-suite-20260814-v1.plan.yaml")
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r2.json")
R1_PREDECESSOR_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r1.json"
)
R1_PREDECESSOR_FILE_BYTES = 18_750
R1_PREDECESSOR_FILE_SHA256 = (
    "sha256:1c42aecbbe4c9e3f39215658fb3ffba87930f94385b526c13287a0d09448fa22"
)
R1_PREDECESSOR_CONTENT_HASH = (
    "sha256:f024e04fd3a01b98f8fb469f2f0d0a11f4faf8372ed57cc7986e163bdecc5042"
)

CONTRACT_IMPORT_ENTRYPOINTS = tuple(
    sorted(
        (
            Path("patchloop/evals/heldout_ac_analysis.py"),
            Path("patchloop/evals/heldout_ac_completion.py"),
            Path("patchloop/evals/heldout_ac_contracts.py"),
            Path("patchloop/evals/heldout_ac_preregistration.py"),
            Path("patchloop/evals/heldout_ac_source_qualification.py"),
            Path("patchloop/evals/heldout_ac_suite.py"),
        ),
        key=lambda item: item.as_posix(),
    )
)

VALIDATION_PATHS = tuple(
    sorted(
        (
            Path("pyproject.toml"),
            Path("scripts/build_heldout_ac_source_qualification.py"),
            Path("tests/test_heldout_ac_analysis.py"),
            Path("tests/test_heldout_ac_completion.py"),
            Path("tests/test_heldout_ac_preregistration.py"),
            Path("tests/test_heldout_ac_source_qualification.py"),
            Path("tests/test_heldout_ac_suite.py"),
            Path("uv.lock"),
        ),
        key=lambda item: item.as_posix(),
    )
)

NEXT_GATE = "separate-task-evaluator-binding-and-refreshed-pricing-before-candidate"


class HeldoutACSourceQualificationError(ContractError):
    """Raised when the offline held-out contract source gate drifts."""


class QualificationFileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="qualification file path")


class InvalidatedPredecessorBinding(HeldoutACFrozenModel):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r1.json"]
    schema_version: Literal["heldout-ac-contract-source-qualification-v1"]
    qualification_id: Literal[
        "core-ac-fixed-bundle-heldout-contract-source-qualification-20260814-r1"
    ]
    original_status: Literal["OFFLINE_CONTRACT_SOURCE_QUALIFIED_TASK_EVALUATOR_BINDING_CLOSED"]
    disposition: Literal["invalidated-by-pre-seal-source-race"]
    source_qualification_hash: Literal[R1_PREDECESSOR_CONTENT_HASH]
    file_bytes: Literal[R1_PREDECESSOR_FILE_BYTES]
    file_sha256: Literal[R1_PREDECESSOR_FILE_SHA256]
    current_source_replay_valid: Literal[False]
    task_package_bindings: Literal[0]
    evaluator_v2_task_contract_bindings: Literal[0]
    authoritative_persisted_producer_adapter_bindings: Literal[0]
    execution_authorized: Literal[False]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    docker_calls_made: Literal[0]
    sdk_calls_made: Literal[0]
    agent_runs_made: Literal[0]
    added_model_cost_usd: Literal[0.0]


class PreregistrationSectionHashes(HeldoutACFrozenModel):
    dataset: Literal["sha256:effac6a9e9a26b21db52e6377a078746819d95dfd6607e7db11ca5bc8dcbdfc2"]
    treatment: Literal["sha256:f3a7256fe2201d0d43c4739c973a180ba0fd4d5bfe5de4f472b21589068982b3"]
    schedule_design: Literal[
        "sha256:52f58401c3626e5d788719ff0932f3f2a2abf1dd1cb092570ad0be461ff68a72"
    ]
    schedule: Literal["sha256:e999650448975f7382d69734ff52fa8c95d912bdb01dbdf82e17d8098d3f6206"]
    runtime: Literal["sha256:907b109b07606e78ed9eacd09b91e09b49fe46d6b4a1dc7bae2b79baf772fd03"]
    cost: Literal["sha256:c1034d283fed13ddb6af0f5462d06add2df5004730d3466ae73ef2cce8d0c2bb"]
    outcomes: Literal["sha256:03ea217e0092c84b02bedd1b896c3e7c5aabd174d6147bf83ab1af6934f54bc5"]
    analysis: Literal["sha256:a044262a830b4615bf0ee9394879a22e46acce184a0894696baff2193b216a3a"]
    exclusions: Literal["sha256:055316274c9dc14bb0b0e9e67735047ba8104db275a77ef2f8edf5e055ee3ed7"]
    stopping: Literal["sha256:d8c723fd38e592c81859b7ed298c407cef3d4682077f5e96807ccd0977388c20"]
    authority: Literal["sha256:c3b416c3f1a9d039713964ba4f4b1f62dfd33c44201c1787c25048e2088ac855"]


class HeldoutACContractProjection(HeldoutACFrozenModel):
    suite_schema_version: Literal["heldout-ac-suite-v1"]
    suite_status: Literal["execution-closed"]
    scheduled_task_count: Literal[12]
    scheduled_run_count: Literal[48]
    task_condition_pair_count: Literal[24]
    schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    treatment_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    planning_cost_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    completion_fixture_schema: Literal["heldout-ac-completion-contract-fixture-v1"]
    completion_contract_projection_schema: Literal["heldout-ac-completion-contract-projection-v1"]
    qualification_fixture_schema: Literal["heldout-ac-trace-qualification-contract-fixture-v1"]
    future_qualification_source_schema: Literal["heldout-ac-trace-qualification-v1"]
    analysis_schema: Literal["heldout-ac-analysis-v1"]
    outcome_projection_schema: Literal["heldout-ac-outcome-projection-v1"]
    completion_surface_status: Literal["offline-untrusted-contract-fixture"]
    analysis_surface_status: Literal["unofficial-preview-only"]
    complete_panel_required: Literal[True]
    evaluator_fail_is_eligible_zero: Literal[True]
    typed_pre_evaluator_agent_terminal_is_eligible_zero: Literal[True]
    infrastructure_or_qualification_confound_is_inconclusive: Literal[True]
    role_strata_count: Literal[2]
    verdict_distribution_count: Literal[4]
    pre_reservation_inconclusive_requires_zero_reserved_runs: Literal[True]
    post_reservation_inconclusive_requires_full_48_run_reservation: Literal[True]
    retry_replacement_or_resume_allowed: Literal[False]
    planning_full_schedule_reserve_usd: Literal[252.0]
    planning_hard_cap_usd: Literal[275.0]
    fresh_pricing_binding_present: Literal[False]
    authoritative_persisted_producer_adapter_present: Literal[False]
    trace_qualification_v2_persisted_adapter_bound: Literal[False]
    persisted_evidence_authenticated: Literal[False]
    official: Literal[False]
    official_analysis_ready: Literal[False]


class HeldoutACBindingBoundary(HeldoutACFrozenModel):
    qualification_scope: Literal["metadata-suite-completion-analysis-contract-only"] = (
        "metadata-suite-completion-analysis-contract-only"
    )
    task_package_binding_status: Literal["closed-not-inspected"] = "closed-not-inspected"
    task_package_binding_count: Literal[0] = 0
    task_private_marker_binding_count: Literal[0] = 0
    evaluator_v2_task_contract_binding_status: Literal["closed-not-materialized"] = (
        "closed-not-materialized"
    )
    evaluator_v2_task_contract_binding_count: Literal[0] = 0
    authoritative_persisted_producer_adapter_binding_status: Literal["closed-not-materialized"] = (
        "closed-not-materialized"
    )
    authoritative_persisted_producer_adapter_binding_count: Literal[0] = 0
    heldout_task_specs_opened: Literal[False] = False
    heldout_task_outcomes_opened: Literal[False] = False


class HeldoutACQualificationAuthority(HeldoutACFrozenModel):
    heldout_task_spec_or_outcome_access_authorized: Literal[False] = False
    unblinding_authorized: Literal[False] = False
    credential_or_environment_observation_authorized: Literal[False] = False
    docker_observation_authorized: Literal[False] = False
    sdk_observation_authorized: Literal[False] = False
    provider_execution_authorized: Literal[False] = False
    evaluator_execution_authorized: Literal[False] = False
    agent_execution_authorized: Literal[False] = False
    runtime_memory_injection_authorized: Literal[False] = False
    authoritative_persisted_producer_adapter_authorized: Literal[False] = False
    pricing_refresh_authorized: Literal[False] = False
    exact_execution_hash_authorized: Literal[False] = False
    execution_candidate_authorized: Literal[False] = False
    approval_creation_or_transfer_authorized: Literal[False] = False
    cost_reservation_authorized: Literal[False] = False
    spend_authorized: Literal[False] = False
    automatic_retry_replacement_or_resume_authorized: Literal[False] = False
    memory_benefit_claim_authorized: Literal[False] = False
    broad_generalization_claim_authorized: Literal[False] = False
    official_analysis_authorized: Literal[False] = False
    analysis_claim_authorized: Literal[False] = False
    authorized_provider_calls: Literal[0] = 0
    authorized_evaluator_calls: Literal[0] = 0
    authorized_agent_runs: Literal[0] = 0
    authorized_docker_calls: Literal[0] = 0
    authorized_sdk_calls: Literal[0] = 0
    authorized_cost_usd: Literal[0.0] = 0.0
    provider_calls_made: Literal[0] = 0
    evaluator_calls_made: Literal[0] = 0
    agent_runs_made: Literal[0] = 0
    docker_calls_made: Literal[0] = 0
    sdk_calls_made: Literal[0] = 0
    retrieval_calls_made: Literal[0] = 0
    added_model_cost_usd: Literal[0.0] = 0.0


class HeldoutACContractSourceQualification(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    qualification_id: Literal[QUALIFICATION_ID] = QUALIFICATION_ID
    status: Literal[STATUS] = STATUS
    recorded_at: datetime
    predecessor: InvalidatedPredecessorBinding
    preregistration: QualificationFileBinding
    preregistration_content_hash: Literal[
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    ]
    preregistration_section_hashes: PreregistrationSectionHashes
    suite: QualificationFileBinding
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    plan: QualificationFileBinding
    plan_content_hash: Literal[
        "sha256:b2058c48de3f2b4d13df872d7fd19a325c3a76ffb5ef24974310409100cb8885"
    ]
    contract_import_entrypoints: tuple[str, ...] = Field(min_length=1)
    contract_import_closure: tuple[str, ...] = Field(min_length=1)
    contract_import_closure_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_source_files: tuple[QualificationFileBinding, ...] = Field(min_length=1)
    contract_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    completion_contract_fixture_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    analysis_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_files: tuple[QualificationFileBinding, ...] = Field(min_length=1)
    validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_projection: HeldoutACContractProjection
    binding_boundary: HeldoutACBindingBoundary
    authority: HeldoutACQualificationAuthority
    next_gate: Literal[NEXT_GATE] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("recorded_at must be timezone-aware UTC")
        return value

    @model_validator(mode="after")
    def validate_hashes_and_inventories(self) -> HeldoutACContractSourceQualification:
        entrypoints = self.contract_import_entrypoints
        closure = self.contract_import_closure
        source_paths = tuple(item.path for item in self.contract_source_files)
        validation_paths = tuple(item.path for item in self.validation_files)
        if entrypoints != tuple(sorted(entrypoints)) or len(entrypoints) != len(set(entrypoints)):
            raise ValueError("contract import entrypoints are not canonical")
        if closure != tuple(sorted(closure)) or len(closure) != len(set(closure)):
            raise ValueError("contract import closure is not canonical")
        if source_paths != closure:
            raise ValueError("contract source inventory differs from import closure")
        if validation_paths != tuple(sorted(validation_paths)) or len(validation_paths) != len(
            set(validation_paths)
        ):
            raise ValueError("validation inventory is not canonical")
        if self.contract_import_closure_hash != sha256_json(list(closure)):
            raise ValueError("contract import closure hash mismatch")
        source_projection = [item.model_dump(mode="json") for item in self.contract_source_files]
        if self.contract_source_hash != sha256_json(source_projection):
            raise ValueError("contract source hash mismatch")
        validation_projection = [item.model_dump(mode="json") for item in self.validation_files]
        if self.validation_hash != sha256_json(validation_projection):
            raise ValueError("validation hash mismatch")
        by_path = {item.path: item.file_sha256 for item in self.contract_source_files}
        if self.completion_contract_fixture_source_hash != by_path.get(
            "patchloop/evals/heldout_ac_completion.py"
        ):
            raise ValueError("completion contract fixture source hash differs")
        if self.analysis_source_hash != by_path.get("patchloop/evals/heldout_ac_analysis.py"):
            raise ValueError("analysis source hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out source qualification content hash mismatch")
        return self


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HeldoutACSourceQualificationError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise HeldoutACSourceQualificationError(
            "held-out source qualification repository is unavailable"
        ) from exc
    _require(root.is_dir(), "held-out source qualification root is not a directory")
    return root


def _is_linklike(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = Path(safe_relative_path(relative.as_posix(), field_name="qualification path"))
    candidate = root / safe
    current = root
    for part in safe.parts:
        current = current / part
        if current.exists() and _is_linklike(current):
            raise HeldoutACSourceQualificationError(
                f"qualification path is link-like: {relative.as_posix()}"
            )
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise HeldoutACSourceQualificationError(
            f"qualification path is unavailable: {relative.as_posix()}"
        ) from exc
    _require(
        resolved.is_relative_to(root),
        f"qualification path escapes repository: {relative.as_posix()}",
    )
    if must_exist:
        _require(resolved.is_file(), f"qualification source is not a file: {relative}")
    return resolved


def _module_name(relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _internal_module_path(
    root: Path,
    module_name: str,
    *,
    required: bool,
) -> Path | None:
    if module_name != "patchloop" and not module_name.startswith("patchloop."):
        return None
    stem = Path(*module_name.split("."))
    candidates = (stem.with_suffix(".py"), stem / "__init__.py")
    existing = [item for item in candidates if (root / item).is_file()]
    if len(existing) > 1:
        raise HeldoutACSourceQualificationError(f"ambiguous internal import module: {module_name}")
    if not existing:
        if required:
            raise HeldoutACSourceQualificationError(
                f"unresolved internal import module: {module_name}"
            )
        return None
    return existing[0]


def _contract_import_closure(
    root: Path,
    *,
    entrypoints: Sequence[Path] = CONTRACT_IMPORT_ENTRYPOINTS,
) -> tuple[Path, ...]:
    """Resolve the internal Python import closure of the bound contract entrypoints."""

    queued: list[Path] = []
    closure: set[Path] = set()

    def add(relative: Path) -> None:
        relative = Path(safe_relative_path(relative.as_posix(), field_name="import path"))
        _logical_path(root, relative, must_exist=True)
        if relative.suffix != ".py" or not relative.parts or relative.parts[0] != "patchloop":
            raise HeldoutACSourceQualificationError(
                f"contract import is not a patchloop Python module: {relative.as_posix()}"
            )
        candidates = [relative]
        parent = relative.parent
        while parent.parts and parent.parts[0] == "patchloop":
            initializer = parent / "__init__.py"
            if (root / initializer).is_file():
                candidates.append(initializer)
            parent = parent.parent
        for candidate in candidates:
            if candidate not in closure:
                closure.add(candidate)
                queued.append(candidate)

    for entrypoint in entrypoints:
        add(entrypoint)
    while queued:
        relative = queued.pop()
        selected = _logical_path(root, relative, must_exist=True)
        try:
            tree = ast.parse(selected.read_text(encoding="utf-8"), filename=relative.as_posix())
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise HeldoutACSourceQualificationError(
                f"contract import source cannot be parsed: {relative.as_posix()}"
            ) from exc
        current_module = _module_name(relative)
        current_package = (
            current_module if relative.name == "__init__.py" else current_module.rpartition(".")[0]
        )
        for node in ast.walk(tree):
            imported_modules: list[tuple[str, bool]] = []
            if isinstance(node, ast.Import):
                imported_modules.extend((alias.name, True) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    try:
                        base = resolve_name(
                            f"{'.' * node.level}{node.module or ''}",
                            current_package,
                        )
                    except (ImportError, ValueError) as exc:
                        raise HeldoutACSourceQualificationError(
                            f"invalid relative import in {relative.as_posix()}"
                        ) from exc
                else:
                    base = node.module or ""
                imported_modules.append((base, True))
                imported_modules.extend(
                    (f"{base}.{alias.name}", False) for alias in node.names if alias.name != "*"
                )
            for module_name, required in imported_modules:
                if module_name != "patchloop" and not module_name.startswith("patchloop."):
                    continue
                imported_path = _internal_module_path(root, module_name, required=required)
                if imported_path is not None:
                    add(imported_path)
    return tuple(sorted(closure, key=lambda item: item.as_posix()))


def _file_binding(root: Path, relative: Path) -> QualificationFileBinding:
    selected = _logical_path(root, relative, must_exist=True)
    try:
        content = selected.read_bytes()
    except OSError as exc:
        raise HeldoutACSourceQualificationError(
            f"qualification source cannot be read: {relative.as_posix()}"
        ) from exc
    return QualificationFileBinding(
        path=relative.as_posix(),
        file_bytes=len(content),
        file_sha256=sha256_bytes(content),
    )


def _bindings(root: Path, paths: Sequence[Path]) -> tuple[QualificationFileBinding, ...]:
    values = tuple(_file_binding(root, item) for item in paths)
    _require(
        tuple(item.path for item in values) == tuple(sorted(item.path for item in values)),
        "qualification inventory is not ordered",
    )
    return values


def _read_mapping(root: Path, relative: Path, *, label: str) -> dict[str, Any]:
    selected = _logical_path(root, relative, must_exist=True)
    try:
        value = load_unique_yaml(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise HeldoutACSourceQualificationError(f"{label} is unreadable") from exc
    _require(isinstance(value, dict), f"{label} is not a mapping")
    return value


def _invalidated_r1_predecessor(root: Path) -> InvalidatedPredecessorBinding:
    """Validate the immutable race-invalidated R1 bytes without replaying them."""

    selected = _logical_path(root, R1_PREDECESSOR_PATH, must_exist=True)
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACSourceQualificationError(
            "held-out R1 predecessor artifact is invalid"
        ) from exc
    _require(isinstance(payload, dict), "held-out R1 predecessor is not a mapping")
    _require(
        len(raw) == R1_PREDECESSOR_FILE_BYTES and sha256_bytes(raw) == R1_PREDECESSOR_FILE_SHA256,
        "held-out R1 predecessor bytes drifted",
    )
    canonical = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _require(raw == canonical, "held-out R1 predecessor bytes are noncanonical")
    _require(
        payload.get("schema_version") == "heldout-ac-contract-source-qualification-v1"
        and payload.get("qualification_id")
        == "core-ac-fixed-bundle-heldout-contract-source-qualification-20260814-r1"
        and payload.get("status") == STATUS
        and payload.get("content_hash") == R1_PREDECESSOR_CONTENT_HASH
        and sha256_json({key: value for key, value in payload.items() if key != "content_hash"})
        == R1_PREDECESSOR_CONTENT_HASH,
        "held-out R1 predecessor identity or content hash differs",
    )
    boundary = payload.get("binding_boundary")
    authority = payload.get("authority")
    projection = payload.get("contract_projection")
    _require(
        isinstance(boundary, dict)
        and boundary.get("task_package_binding_count") == 0
        and type(boundary.get("task_package_binding_count")) is int
        and boundary.get("task_private_marker_binding_count") == 0
        and type(boundary.get("task_private_marker_binding_count")) is int
        and boundary.get("evaluator_v2_task_contract_binding_count") == 0
        and type(boundary.get("evaluator_v2_task_contract_binding_count")) is int
        and boundary.get("authoritative_persisted_producer_adapter_binding_count") == 0
        and type(boundary.get("authoritative_persisted_producer_adapter_binding_count")) is int
        and boundary.get("heldout_task_specs_opened") is False
        and boundary.get("heldout_task_outcomes_opened") is False,
        "held-out R1 predecessor binding boundary differs",
    )
    _require(
        isinstance(projection, dict)
        and projection.get("authoritative_persisted_producer_adapter_present") is False
        and projection.get("trace_qualification_v2_persisted_adapter_bound") is False
        and projection.get("persisted_evidence_authenticated") is False
        and projection.get("official") is False
        and projection.get("official_analysis_ready") is False,
        "held-out R1 predecessor projection authority differs",
    )
    _require(isinstance(authority, dict), "held-out R1 predecessor authority is absent")
    _require(
        all(value is False for key, value in authority.items() if key.endswith("authorized")),
        "held-out R1 predecessor contains runtime authority",
    )
    _require(
        all(
            type(value) is int and value == 0
            for key, value in authority.items()
            if (key.startswith("authorized_") and key.endswith(("_calls", "_runs")))
            or key.endswith(("_calls_made", "_runs_made"))
        ),
        "held-out R1 predecessor contains nonzero runtime observations",
    )
    _require(
        type(authority.get("authorized_cost_usd")) is float
        and authority["authorized_cost_usd"] == 0.0
        and type(authority.get("added_model_cost_usd")) is float
        and authority["added_model_cost_usd"] == 0.0,
        "held-out R1 predecessor contains cost authority or spend",
    )
    _require(
        b'"task_bindings"' not in raw and b'"private_spec_hash"' not in raw,
        "held-out R1 predecessor contains a forbidden task binding",
    )
    return InvalidatedPredecessorBinding(
        path=R1_PREDECESSOR_PATH.as_posix(),
        schema_version="heldout-ac-contract-source-qualification-v1",
        qualification_id=("core-ac-fixed-bundle-heldout-contract-source-qualification-20260814-r1"),
        original_status=STATUS,
        disposition="invalidated-by-pre-seal-source-race",
        source_qualification_hash=R1_PREDECESSOR_CONTENT_HASH,
        file_bytes=R1_PREDECESSOR_FILE_BYTES,
        file_sha256=R1_PREDECESSOR_FILE_SHA256,
        current_source_replay_valid=False,
        task_package_bindings=0,
        evaluator_v2_task_contract_bindings=0,
        authoritative_persisted_producer_adapter_bindings=0,
        execution_authorized=False,
        provider_calls_made=0,
        evaluator_calls_made=0,
        docker_calls_made=0,
        sdk_calls_made=0,
        agent_runs_made=0,
        added_model_cost_usd=0.0,
    )


def _build_candidate(
    root: Path,
    *,
    recorded_at: datetime,
) -> HeldoutACContractSourceQualification:
    # Local imports make the source boundary explicit without widening module import into
    # any runtime operation.  Both loaders are metadata-only and are guarded by tests.
    from patchloop.evals.heldout_ac_analysis import (
        ANALYSIS_SCHEMA_VERSION,
    )
    from patchloop.evals.heldout_ac_analysis import (
        SCHEMA_VERSION as OUTCOME_SCHEMA_VERSION,
    )
    from patchloop.evals.heldout_ac_completion import (
        COMPLETION_SCHEMA_VERSION,
    )
    from patchloop.evals.heldout_ac_completion import (
        SCHEMA_VERSION as COMPLETION_INPUT_SCHEMA_VERSION,
    )
    from patchloop.evals.heldout_ac_preregistration import (
        load_heldout_ac_preregistration,
    )
    from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite_plan

    predecessor = _invalidated_r1_predecessor(root)
    preregistration_summary = load_heldout_ac_preregistration(repository=root)
    plan, suite = load_heldout_ac_suite_plan(PLAN_PATH, repository=root)
    preregistration_raw = _read_mapping(
        root, PREREGISTRATION_PATH, label="held-out preregistration"
    )
    suite_raw = _read_mapping(root, SUITE_PATH, label="held-out suite")
    plan_raw = _read_mapping(root, PLAN_PATH, label="held-out plan")
    section_hashes = suite.preregistration.section_hashes.model_dump(mode="json")
    _require(
        preregistration_summary["content_hash"] == suite.preregistration.content_hash
        and preregistration_summary["file_sha256"] == suite.preregistration.file_sha256
        and suite_raw["content_hash"] == suite.content_hash
        and plan_raw["content_hash"] == plan.content_hash,
        "held-out preregistration, suite, or plan identity differs",
    )
    for section, expected_hash in section_hashes.items():
        _require(
            sha256_json(preregistration_raw[section]) == expected_hash,
            f"held-out preregistration {section} section drifted",
        )

    closure = _contract_import_closure(root)
    source_files = _bindings(root, closure)
    validation_files = _bindings(root, VALIDATION_PATHS)
    source_hashes = {item.path: item.file_sha256 for item in source_files}
    projection = HeldoutACContractProjection(
        suite_schema_version=suite.schema_version,
        suite_status=suite.status,
        scheduled_task_count=len(suite.tasks),
        scheduled_run_count=len(suite.schedule),
        task_condition_pair_count=suite.schedule_binding.task_condition_pairs,
        schedule_hash=sha256_json([item.model_dump(mode="json") for item in suite.schedule]),
        treatment_hash=sha256_json(suite.treatment.model_dump(mode="json")),
        runtime_tuple_hash=sha256_json(suite.runtime.model_dump(mode="json")),
        planning_cost_hash=sha256_json(suite.cost.model_dump(mode="json")),
        completion_fixture_schema=COMPLETION_INPUT_SCHEMA_VERSION,
        completion_contract_projection_schema=COMPLETION_SCHEMA_VERSION,
        qualification_fixture_schema="heldout-ac-trace-qualification-contract-fixture-v1",
        future_qualification_source_schema="heldout-ac-trace-qualification-v1",
        analysis_schema=ANALYSIS_SCHEMA_VERSION,
        outcome_projection_schema=OUTCOME_SCHEMA_VERSION,
        completion_surface_status="offline-untrusted-contract-fixture",
        analysis_surface_status="unofficial-preview-only",
        complete_panel_required=True,
        evaluator_fail_is_eligible_zero=True,
        typed_pre_evaluator_agent_terminal_is_eligible_zero=True,
        infrastructure_or_qualification_confound_is_inconclusive=True,
        role_strata_count=2,
        verdict_distribution_count=4,
        pre_reservation_inconclusive_requires_zero_reserved_runs=True,
        post_reservation_inconclusive_requires_full_48_run_reservation=True,
        retry_replacement_or_resume_allowed=False,
        planning_full_schedule_reserve_usd=suite.cost.full_schedule_reserve_usd,
        planning_hard_cap_usd=suite.cost.hard_cap_usd,
        fresh_pricing_binding_present=False,
        authoritative_persisted_producer_adapter_present=False,
        trace_qualification_v2_persisted_adapter_bound=False,
        persisted_evidence_authenticated=False,
        official=False,
        official_analysis_ready=False,
    )
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": STATUS,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
        "predecessor": predecessor.model_dump(mode="json"),
        "preregistration": _file_binding(root, PREREGISTRATION_PATH).model_dump(mode="json"),
        "preregistration_content_hash": preregistration_summary["content_hash"],
        "preregistration_section_hashes": section_hashes,
        "suite": _file_binding(root, SUITE_PATH).model_dump(mode="json"),
        "suite_content_hash": suite.content_hash,
        "plan": _file_binding(root, PLAN_PATH).model_dump(mode="json"),
        "plan_content_hash": plan.content_hash,
        "contract_import_entrypoints": [item.as_posix() for item in CONTRACT_IMPORT_ENTRYPOINTS],
        "contract_import_closure": [item.as_posix() for item in closure],
        "contract_import_closure_hash": sha256_json([item.as_posix() for item in closure]),
        "contract_source_files": [item.model_dump(mode="json") for item in source_files],
        "contract_source_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "completion_contract_fixture_source_hash": source_hashes[
            "patchloop/evals/heldout_ac_completion.py"
        ],
        "analysis_source_hash": source_hashes["patchloop/evals/heldout_ac_analysis.py"],
        "validation_files": [item.model_dump(mode="json") for item in validation_files],
        "validation_hash": sha256_json([item.model_dump(mode="json") for item in validation_files]),
        "contract_projection": projection.model_dump(mode="json"),
        "binding_boundary": HeldoutACBindingBoundary().model_dump(mode="json"),
        "authority": HeldoutACQualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return HeldoutACContractSourceQualification.model_validate_json(
        json.dumps(
            {**body, "content_hash": sha256_json(body)},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def _canonical_bytes(payload: HeldoutACContractSourceQualification) -> bytes:
    return (payload.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_validated(
    root: Path,
) -> tuple[HeldoutACContractSourceQualification, bytes]:
    selected = _logical_path(root, OUTPUT_PATH, must_exist=True)
    try:
        raw = selected.read_bytes()
        payload = HeldoutACContractSourceQualification.model_validate_json(raw)
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        raise HeldoutACSourceQualificationError(
            "held-out contract source qualification artifact is invalid"
        ) from exc
    _require(raw == _canonical_bytes(payload), "source qualification bytes are not canonical")
    expected = _build_candidate(root, recorded_at=payload.recorded_at)
    _require(payload == expected, "held-out contract source qualification has drifted")
    return payload, raw


def _summary(
    payload: HeldoutACContractSourceQualification,
    raw: bytes,
) -> dict[str, Any]:
    return {
        "status": payload.status,
        "qualification_id": payload.qualification_id,
        "source_qualification_hash": payload.content_hash,
        "predecessor_disposition": payload.predecessor.disposition,
        "predecessor_file_sha256": payload.predecessor.file_sha256,
        "contract_source_hash": payload.contract_source_hash,
        "suite_content_hash": payload.suite_content_hash,
        "completion_contract_fixture_source_hash": (
            payload.completion_contract_fixture_source_hash
        ),
        "analysis_source_hash": payload.analysis_source_hash,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "task_package_bindings": 0,
        "evaluator_v2_task_contract_bindings": 0,
        "authoritative_persisted_producer_adapter_bindings": 0,
        "execution_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "agent_runs_made": 0,
        "added_model_cost_usd": 0.0,
    }


def validate_heldout_ac_source_qualification(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Validate canonical artifact bytes and replay every bound local source identity."""

    root = _repo_root(repository)
    payload, raw = _load_validated(root)
    return _summary(payload, raw)


def _write_new(
    root: Path,
    payload: HeldoutACContractSourceQualification,
) -> bytes:
    selected = _logical_path(root, OUTPUT_PATH, must_exist=False)
    _require(not selected.exists(), "held-out contract source qualification already exists")
    try:
        selected.parent.mkdir(parents=True, exist_ok=True)
        content = _canonical_bytes(payload)
        with selected.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        observed = selected.read_bytes()
    except OSError as exc:
        raise HeldoutACSourceQualificationError(
            "held-out contract source qualification cannot be created"
        ) from exc
    _require(observed == content, "source qualification changed after creation")
    return observed


def run_heldout_ac_source_qualification(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Materialize once, or validate the exact append-only offline artifact."""

    root = _repo_root(repository)
    output = _logical_path(root, OUTPUT_PATH, must_exist=False)
    if output.exists():
        return validate_heldout_ac_source_qualification(repository=root)
    payload = _build_candidate(root, recorded_at=datetime.now(UTC))
    raw = _write_new(root, payload)
    validated, observed = _load_validated(root)
    _require(raw == observed and payload == validated, "source qualification reread differs")
    return _summary(validated, observed)


__all__ = [
    "CONTRACT_IMPORT_ENTRYPOINTS",
    "NEXT_GATE",
    "OUTPUT_PATH",
    "PLAN_PATH",
    "PREREGISTRATION_PATH",
    "QUALIFICATION_ID",
    "R1_PREDECESSOR_CONTENT_HASH",
    "R1_PREDECESSOR_FILE_BYTES",
    "R1_PREDECESSOR_FILE_SHA256",
    "R1_PREDECESSOR_PATH",
    "SCHEMA_VERSION",
    "STATUS",
    "SUITE_PATH",
    "VALIDATION_PATHS",
    "HeldoutACContractSourceQualification",
    "HeldoutACSourceQualificationError",
    "run_heldout_ac_source_qualification",
    "validate_heldout_ac_source_qualification",
]
