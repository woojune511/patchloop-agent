"""No-call source gate and execution-closed runner candidate for admission.

This module binds the exact 144-row deterministic partial-admission plan to a
tracked Harbor source snapshot and a closed oracle/Docker command projection.
It does not extract packages, write task workspaces, inspect private patches,
open Docker, or execute Harbor.  A later activation must bind the candidate's
execution hash and receive explicit Docker authority before an executor exists.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_all_cross_successor import CANDIDATE_IDS
from patchloop.evals.fresh_harbor_admission import _load_observation
from patchloop.evals.fresh_harbor_partial_admission import (
    PREREGISTRATION_PATH,
    load_preregistration,
)
from patchloop.evals.fresh_harbor_partial_admission import (
    SOURCE_QUALIFICATION_PATH as GENERATOR_SOURCE_QUALIFICATION_PATH,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SOURCE_QUALIFICATION_SCHEMA = "lean-fresh-harbor-partial-runner-source-qualification-v1"
SOURCE_QUALIFICATION_ID = "lean-fresh-harbor-partial-runner-20260818-r1"
SOURCE_QUALIFICATION_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-partial-runner-source-qualification-r1.json"
)
CANDIDATE_SCHEMA = "lean-fresh-harbor-partial-runner-candidate-v1"
CANDIDATE_ID = "lean-fresh-harbor-partial-admission-runner-20260818-v1"
CANDIDATE_PATH = "experiments/lean-harness-fresh-harbor-partial-admission-runner-20260818-v1.json"

GENERATOR_SOURCE_BYTES = 5_326
GENERATOR_SOURCE_FILE_SHA256 = (
    "sha256:db9f4ad3856f339c0a53e31e5f97979a7fcae5c5855d5814083c095efccfb514"
)
GENERATOR_SOURCE_CONTENT_HASH = (
    "sha256:c4544a05e91478869a1afcf8b5abe4bf5083a362808969e748067d5f64822f96"
)
PREREGISTRATION_BYTES = 140_706
PREREGISTRATION_FILE_SHA256 = (
    "sha256:7431e4f8d9dd6274ecc0124ef40935206e02bae31c4a01ae16024f4d612a0dec"
)
PREREGISTRATION_CONTENT_HASH = (
    "sha256:02d32a43fc4697814dba503a1623d9733a4c494fa0cac47f2e5c696148054efb"
)
HARBOR_COMMIT = "f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e"
HARBOR_TREE = "ad3ff0729de33525c618fad6b60557643d1cb24c"
HARBOR_VERSION = "0.21.0"
EXPECTED_ROWS = 144

SOURCE_PATHS = (
    "patchloop/evals/fresh_harbor_partial_runner.py",
    "scripts/build_lean_fresh_harbor_partial_runner_source_qualification.py",
    "scripts/build_lean_fresh_harbor_partial_runner_candidate.py",
)
VALIDATION_PATHS = ("tests/test_fresh_harbor_partial_runner.py",)
HARBOR_AUDIT_PATHS = (
    "pyproject.toml",
    "src/harbor/cli/main.py",
    "src/harbor/cli/jobs.py",
    "src/harbor/agents/oracle.py",
    "src/harbor/models/trial/paths.py",
    "src/harbor/telemetry.py",
)
EXPECTED_ARCHIVE_MEMBERS = (
    "environment/Dockerfile",
    "instruction.md",
    "solution/solve.sh",
    "task.toml",
    "tests/config.json",
    "tests/swan_log_parsers.py",
    "tests/test.sh",
)
PARTIAL_SOLVE_SCRIPT = (
    b"#!/bin/sh\nset -eu\ncd /testbed\ngit apply --whitespace=nowarn /solution/partial.patch\n"
)


class FreshHarborPartialRunnerError(ContractError):
    """The no-call runner source or candidate identity differs."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FileBinding(FrozenModel):
    path: str
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    role: str

    @field_validator("file_bytes", mode="before")
    @classmethod
    def exact_bytes(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("file_bytes must be a JSON integer")
        return value


class HarborSourceBinding(FrozenModel):
    commit: Literal[HARBOR_COMMIT]
    tree: Literal[HARBOR_TREE]
    version: Literal[HARBOR_VERSION]
    tracked_worktree_clean: Literal[True]
    audit_files: tuple[FileBinding, ...]
    audit_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("audit_files", mode="before")
    @classmethod
    def freeze_files(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if tuple(item.path for item in self.audit_files) != HARBOR_AUDIT_PATHS:
            raise ValueError("Harbor audit-file order differs")
        if self.audit_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.audit_files]
        ):
            raise ValueError("Harbor audit inventory hash differs")
        return self


class SourceAuthority(FrozenModel):
    local_source_files_read: Literal[3]
    local_validation_files_read: Literal[1]
    harbor_git_metadata_reads: Literal[3]
    harbor_audit_source_files_read: Literal[6]
    package_archives_read: Literal[0]
    private_reference_patches_read: Literal[0]
    task_packages_materialized: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    provider_calls: Literal[0]
    agent_runs: Literal[0]
    added_cost_usd: Literal[0]
    source_qualified: Literal[True]
    candidate_creation_authorized: Literal[False]
    docker_preflight_authorized: Literal[False]
    docker_execution_authorized: Literal[False]


class CandidateAuthority(FrozenModel):
    source_qualification_files_read: Literal[1]
    preregistration_files_read: Literal[1]
    public_observation_files_read: Literal[1]
    package_archives_read: Literal[0]
    private_reference_patches_read: Literal[0]
    task_packages_materialized: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    provider_calls: Literal[0]
    agent_runs: Literal[0]
    added_cost_usd: Literal[0]
    candidate_materialized: Literal[True]
    no_call_preflight_authorized: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    admission_result_authorized: Literal[False]
    task_conversion_authorized: Literal[False]
    runtime_candidate_authorized: Literal[False]
    official_analysis_authorized: Literal[False]


class RunnerSourceQualification(FrozenModel):
    schema_version: Literal[SOURCE_QUALIFICATION_SCHEMA]
    qualification_id: Literal[SOURCE_QUALIFICATION_ID]
    status: Literal["PARTIAL_RUNNER_SOURCE_QUALIFIED_NO_DOCKER_AUTHORITY"]
    predecessor_bindings: tuple[FileBinding, ...]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    harbor_source: HarborSourceBinding
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checks: dict[str, bool]
    authority: SourceAuthority
    next_gate: Literal["materialize-execution-closed-exact-144-row-runner-candidate"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("predecessor_bindings", "source_files", "validation_files", mode="before")
    @classmethod
    def freeze_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.checks != _source_checks():
            raise ValueError("partial runner source checks differ")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("partial runner source inventory hash differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("partial runner validation inventory hash differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("partial runner source content hash differs")
        return self


class RunnerRow(FrozenModel):
    order: int = Field(ge=1, le=EXPECTED_ROWS)
    task_id: str
    repository: str
    variant_ordinal: int = Field(ge=1, le=12)
    package_archive_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reference_patch_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    generated_patch_bytes: int = Field(ge=1)
    generated_patch_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="before")
    @classmethod
    def exact_integers(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in ("order", "variant_ordinal", "generated_patch_bytes"):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"row_id"}))
        if self.row_id != expected:
            raise ValueError("partial runner row ID differs")
        return self


class RunnerCandidate(FrozenModel):
    schema_version: Literal[CANDIDATE_SCHEMA]
    candidate_id: Literal[CANDIDATE_ID]
    status: Literal["EXACT_144_ROW_RUNNER_CANDIDATE_EXECUTION_CLOSED"]
    source_qualification_binding: FileBinding
    preregistration_binding: FileBinding
    harbor_source: HarborSourceBinding
    rows: tuple[RunnerRow, ...]
    row_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    command_contract: dict[str, Any]
    task_materialization_contract: dict[str, Any]
    evidence_contract: dict[str, Any]
    stopping_contract: dict[str, Any]
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: CandidateAuthority
    next_gate: Literal[
        "obtain-explicit-read-only-docker-preflight-authority-for-this-execution-hash"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("rows", mode="before")
    @classmethod
    def freeze_rows(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_candidate(self) -> Self:
        if len(self.rows) != EXPECTED_ROWS:
            raise ValueError("partial runner row count differs")
        if tuple(item.order for item in self.rows) != tuple(range(1, EXPECTED_ROWS + 1)):
            raise ValueError("partial runner row order differs")
        expected_pairs = tuple(
            (task_id, ordinal) for task_id in CANDIDATE_IDS for ordinal in range(1, 13)
        )
        if tuple((item.task_id, item.variant_ordinal) for item in self.rows) != expected_pairs:
            raise ValueError("partial runner task/variant schedule differs")
        if self.row_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.rows]
        ):
            raise ValueError("partial runner row inventory hash differs")
        if self.command_contract != _command_contract():
            raise ValueError("partial runner command contract differs")
        if self.task_materialization_contract != _task_materialization_contract():
            raise ValueError("partial runner materialization contract differs")
        if self.evidence_contract != _evidence_contract():
            raise ValueError("partial runner evidence contract differs")
        if self.stopping_contract != _stopping_contract():
            raise ValueError("partial runner stopping contract differs")
        execution_projection = self.model_dump(
            mode="json",
            exclude={"execution_hash", "authority", "next_gate", "content_hash"},
        )
        if self.execution_hash != sha256_json(execution_projection):
            raise ValueError("partial runner execution hash differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("partial runner candidate content hash differs")
        return self


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def artifact_bytes(value: BaseModel) -> bytes:
    return (json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n").encode()


def _safe_file(root: Path, path: str) -> Path:
    selected = ensure_within(root, path)
    lexical = root / Path(path)
    if lexical.is_symlink() or selected.is_symlink() or not selected.is_file():
        raise FreshHarborPartialRunnerError(f"required runner binding is unavailable: {path}")
    return selected


def _binding(root: Path, path: str, role: str) -> FileBinding:
    raw = _safe_file(root, path).read_bytes()
    content_hash: str | None = None
    if path.endswith(".json"):
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            value = None
        if isinstance(value, dict) and isinstance(value.get("content_hash"), str):
            content_hash = value["content_hash"]
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
        role=role,
    )


def _predecessor_bindings(root: Path) -> tuple[FileBinding, ...]:
    expected = (
        FileBinding(
            path=GENERATOR_SOURCE_QUALIFICATION_PATH,
            file_bytes=GENERATOR_SOURCE_BYTES,
            file_sha256=GENERATOR_SOURCE_FILE_SHA256,
            content_hash=GENERATOR_SOURCE_CONTENT_HASH,
            role="deterministic-partial-generator-source",
        ),
        FileBinding(
            path=PREREGISTRATION_PATH,
            file_bytes=PREREGISTRATION_BYTES,
            file_sha256=PREREGISTRATION_FILE_SHA256,
            content_hash=PREREGISTRATION_CONTENT_HASH,
            role="deterministic-partial-admission-preregistration",
        ),
    )
    actual = (
        _binding(
            root,
            GENERATOR_SOURCE_QUALIFICATION_PATH,
            "deterministic-partial-generator-source",
        ),
        _binding(root, PREREGISTRATION_PATH, "deterministic-partial-admission-preregistration"),
    )
    if actual != expected:
        raise FreshHarborPartialRunnerError("partial runner predecessor differs")
    return actual


def _git_value(harbor_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(harbor_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise FreshHarborPartialRunnerError("Harbor Git identity is unavailable") from exc
    return result.stdout.strip()


def _harbor_source_binding(harbor_root: Path) -> HarborSourceBinding:
    lexical_root = harbor_root.absolute()
    if lexical_root.is_symlink() or not lexical_root.is_dir():
        raise FreshHarborPartialRunnerError("Harbor source root is unavailable or linked")
    commit = _git_value(lexical_root, "rev-parse", "HEAD")
    tree = _git_value(lexical_root, "rev-parse", "HEAD^{tree}")
    status = _git_value(lexical_root, "status", "--porcelain", "--untracked-files=no")
    if commit != HARBOR_COMMIT or tree != HARBOR_TREE or status:
        raise FreshHarborPartialRunnerError("Harbor tracked source identity differs")
    audit_files: list[FileBinding] = []
    for path in HARBOR_AUDIT_PATHS:
        selected = ensure_within(lexical_root.resolve(), path)
        lexical = lexical_root / Path(path)
        if lexical.is_symlink() or selected.is_symlink() or not selected.is_file():
            raise FreshHarborPartialRunnerError("Harbor audit source file differs")
        raw = selected.read_bytes()
        audit_files.append(
            FileBinding(
                path=path,
                file_bytes=len(raw),
                file_sha256=sha256_bytes(raw),
                content_hash=None,
                role="harbor-runner-source",
            )
        )
    frozen = tuple(audit_files)
    return HarborSourceBinding(
        commit=HARBOR_COMMIT,
        tree=HARBOR_TREE,
        version=HARBOR_VERSION,
        tracked_worktree_clean=True,
        audit_files=frozen,
        audit_inventory_hash=sha256_json([item.model_dump(mode="json") for item in frozen]),
    )


def _source_checks() -> dict[str, bool]:
    return {
        "exact-harbor-commit-and-tree-bound": True,
        "tracked-harbor-worktree-clean": True,
        "telemetry-forced-off": True,
        "oracle-agent-only": True,
        "docker-environment-only": True,
        "one-attempt-zero-retries-one-concurrent": True,
        "exact-seven-member-archive-contract": True,
        "solution-script-replaced-by-fixed-git-apply-wrapper": True,
        "private-patch-body-never-enters-candidate": True,
        "single-report-and-agent-exit-evidence-required": True,
        "no-subprocess-shell": True,
        "source-gate-makes-no-docker-or-harbor-call": True,
    }


def _source_authority() -> SourceAuthority:
    return SourceAuthority(
        local_source_files_read=3,
        local_validation_files_read=1,
        harbor_git_metadata_reads=3,
        harbor_audit_source_files_read=6,
        package_archives_read=0,
        private_reference_patches_read=0,
        task_packages_materialized=0,
        network_calls=0,
        docker_calls=0,
        evaluator_calls=0,
        provider_calls=0,
        agent_runs=0,
        added_cost_usd=0,
        source_qualified=True,
        candidate_creation_authorized=False,
        docker_preflight_authorized=False,
        docker_execution_authorized=False,
    )


def _candidate_authority() -> CandidateAuthority:
    return CandidateAuthority(
        source_qualification_files_read=1,
        preregistration_files_read=1,
        public_observation_files_read=1,
        package_archives_read=0,
        private_reference_patches_read=0,
        task_packages_materialized=0,
        network_calls=0,
        docker_calls=0,
        evaluator_calls=0,
        provider_calls=0,
        agent_runs=0,
        added_cost_usd=0,
        candidate_materialized=True,
        no_call_preflight_authorized=False,
        approval_granted=False,
        execution_authorized=False,
        admission_result_authorized=False,
        task_conversion_authorized=False,
        runtime_candidate_authorized=False,
        official_analysis_authorized=False,
    )


def _command_contract() -> dict[str, Any]:
    return {
        "shell": False,
        "stdin": "closed",
        "environment": {"HARBOR_TELEMETRY": "off"},
        "entrypoint": ["{harbor_python}", "-m", "harbor.cli.main"],
        "arguments": [
            "run",
            "--path",
            "{prepared_task_dir}",
            "--agent",
            "oracle",
            "--env",
            "docker",
            "--jobs-dir",
            "{row_job_dir}",
            "--n-attempts",
            "1",
            "--max-retries",
            "0",
            "--n-concurrent",
            "1",
            "--yes",
            "--delete",
        ],
        "model_argument_present": False,
        "credential_or_agent_env_arguments_present": False,
        "network_allowlist_arguments_present": False,
        "row_order": "strictly-serial-1-through-144",
    }


def _task_materialization_contract() -> dict[str, Any]:
    return {
        "archive_members_exact": list(EXPECTED_ARCHIVE_MEMBERS),
        "archive_regular_files_only": True,
        "absolute-parent-link-or-special-members_rejected": True,
        "archive_sha256_must_match_row": True,
        "reference-and-generated-patch_sha256_must_match-row": True,
        "solution/solve.sh_replaced": True,
        "solution/partial.patch_added": True,
        "partial_solve_script_bytes": len(PARTIAL_SOLVE_SCRIPT),
        "partial_solve_script_sha256": sha256_bytes(PARTIAL_SOLVE_SCRIPT),
        "workspace_outside-task-repository": True,
        "fresh-workspace-per-row": True,
        "task-workspace-retained_after-row": False,
        "private-patch-agent-visible": False,
    }


def _evidence_contract() -> dict[str, Any]:
    return {
        "exactly-one-verifier-report-required": True,
        "raw-report-byte-size-and-sha-required": True,
        "agent-exit-code-file-absent-means-zero": True,
        "nonzero-agent-exit-means-patch-application-failed": True,
        "resolved-false-and-zero-agent-exit-means-applied-rejection": True,
        "resolved-true-means-partial-variant-survived": True,
        "raw-test-identifiers-and-output-not-persisted": True,
        "raw-job-root-external-to-repository": True,
        "sanitized-row-evidence-append-only": True,
    }


def _stopping_contract() -> dict[str, Any]:
    return {
        "expected_rows": EXPECTED_ROWS,
        "minimum-applied-rejections-per-task": 8,
        "automatic-retry": False,
        "adaptive-replacement": False,
        "resume": False,
        "parallel-execution": False,
        "stop-before-next-row-on-source-plan-command-or-evidence-drift": True,
        "stop-before-next-row-on-docker-harbor-or-evaluator-infrastructure-error": True,
        "patch-application-failure-is-terminal-non-rejection-not-infrastructure": True,
        "partial-campaign-primary-admission-decision-authorized": False,
    }


def build_source_qualification(root: Path, harbor_root: Path) -> RunnerSourceQualification:
    root = root.resolve()
    predecessors = _predecessor_bindings(root)
    source_files = tuple(_binding(root, path, "partial-runner-source") for path in SOURCE_PATHS)
    validation_files = tuple(
        _binding(root, path, "partial-runner-validation") for path in VALIDATION_PATHS
    )
    body: dict[str, Any] = {
        "schema_version": SOURCE_QUALIFICATION_SCHEMA,
        "qualification_id": SOURCE_QUALIFICATION_ID,
        "status": "PARTIAL_RUNNER_SOURCE_QUALIFIED_NO_DOCKER_AUTHORITY",
        "predecessor_bindings": predecessors,
        "source_files": source_files,
        "validation_files": validation_files,
        "harbor_source": _harbor_source_binding(harbor_root),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "checks": _source_checks(),
        "authority": _source_authority(),
        "next_gate": "materialize-execution-closed-exact-144-row-runner-candidate",
    }
    return RunnerSourceQualification(**body, content_hash=sha256_json(_jsonable(body)))


def load_source_qualification(root: Path) -> tuple[RunnerSourceQualification, bytes]:
    root = root.resolve()
    selected = _safe_file(root, SOURCE_QUALIFICATION_PATH)
    try:
        raw = selected.read_bytes()
        value = RunnerSourceQualification.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise FreshHarborPartialRunnerError("partial runner source gate is unavailable") from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborPartialRunnerError("partial runner source bytes are noncanonical")
    if value.predecessor_bindings != _predecessor_bindings(root):
        raise FreshHarborPartialRunnerError("partial runner source predecessor drifted")
    current_source = tuple(_binding(root, path, "partial-runner-source") for path in SOURCE_PATHS)
    current_validation = tuple(
        _binding(root, path, "partial-runner-validation") for path in VALIDATION_PATHS
    )
    if value.source_files != current_source or value.validation_files != current_validation:
        raise FreshHarborPartialRunnerError("partial runner source or validation drifted")
    return value, raw


def build_candidate(root: Path) -> RunnerCandidate:
    root = root.resolve()
    qualification, qualification_raw = load_source_qualification(root)
    preregistration, preregistration_raw = load_preregistration(root)
    if not (
        len(preregistration_raw) == PREREGISTRATION_BYTES
        and sha256_bytes(preregistration_raw) == PREREGISTRATION_FILE_SHA256
        and preregistration.content_hash == PREREGISTRATION_CONTENT_HASH
    ):
        raise FreshHarborPartialRunnerError("partial runner preregistration binding differs")
    observation = _load_observation(root)
    observation_by_task = {item.instance: item for item in observation.candidates}
    rows: list[RunnerRow] = []
    order = 0
    for task_plan in preregistration.task_plans:
        candidate = observation_by_task.get(task_plan.task_id)
        if candidate is None or candidate.repository != task_plan.repository:
            raise FreshHarborPartialRunnerError("partial runner public task binding differs")
        for variant in task_plan.variants:
            order += 1
            body = {
                "order": order,
                "task_id": task_plan.task_id,
                "repository": task_plan.repository,
                "variant_ordinal": variant.ordinal,
                "package_archive_sha256": candidate.archive.sha256,
                "reference_patch_sha256": task_plan.reference_patch.file_sha256,
                "generated_patch_bytes": variant.generated_patch.file_bytes,
                "generated_patch_sha256": variant.generated_patch.file_sha256,
            }
            rows.append(RunnerRow(**body, row_id=sha256_json(body)))
    frozen_rows = tuple(rows)
    qualification_binding = FileBinding(
        path=SOURCE_QUALIFICATION_PATH,
        file_bytes=len(qualification_raw),
        file_sha256=sha256_bytes(qualification_raw),
        content_hash=qualification.content_hash,
        role="partial-runner-source-qualification",
    )
    preregistration_binding = FileBinding(
        path=PREREGISTRATION_PATH,
        file_bytes=len(preregistration_raw),
        file_sha256=sha256_bytes(preregistration_raw),
        content_hash=preregistration.content_hash,
        role="deterministic-partial-admission-preregistration",
    )
    body: dict[str, Any] = {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "status": "EXACT_144_ROW_RUNNER_CANDIDATE_EXECUTION_CLOSED",
        "source_qualification_binding": qualification_binding,
        "preregistration_binding": preregistration_binding,
        "harbor_source": qualification.harbor_source,
        "rows": frozen_rows,
        "row_inventory_hash": sha256_json([item.model_dump(mode="json") for item in frozen_rows]),
        "command_contract": _command_contract(),
        "task_materialization_contract": _task_materialization_contract(),
        "evidence_contract": _evidence_contract(),
        "stopping_contract": _stopping_contract(),
    }
    execution_hash = sha256_json(_jsonable(body))
    body["execution_hash"] = execution_hash
    body["authority"] = _candidate_authority()
    body["next_gate"] = (
        "obtain-explicit-read-only-docker-preflight-authority-for-this-execution-hash"
    )
    return RunnerCandidate(**body, content_hash=sha256_json(_jsonable(body)))


def load_candidate(root: Path) -> tuple[RunnerCandidate, bytes]:
    root = root.resolve()
    selected = _safe_file(root, CANDIDATE_PATH)
    try:
        raw = selected.read_bytes()
        value = RunnerCandidate.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise FreshHarborPartialRunnerError("partial runner candidate is unavailable") from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborPartialRunnerError("partial runner candidate bytes are noncanonical")
    if value != build_candidate(root):
        raise FreshHarborPartialRunnerError("partial runner candidate drifted")
    return value, raw


def _write_once(root: Path, path: str, value: BaseModel, role: str) -> FileBinding:
    selected = ensure_within(root, path)
    raw = artifact_bytes(value)
    if selected.exists():
        if selected.read_bytes() != raw:
            raise FreshHarborPartialRunnerError(f"append-only runner artifact differs: {path}")
    else:
        selected.parent.mkdir(parents=True, exist_ok=True)
        with selected.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=str(value.model_dump(mode="json")["content_hash"]),
        role=role,
    )


def materialize_source_qualification(root: Path, harbor_root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(
        root,
        SOURCE_QUALIFICATION_PATH,
        build_source_qualification(root, harbor_root),
        "partial-runner-source-qualification",
    )


def materialize_candidate(root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(
        root,
        CANDIDATE_PATH,
        build_candidate(root),
        "execution-closed-partial-runner-candidate",
    )
