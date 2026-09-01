"""Zero-call qualification for role-aware recent-event descriptor compaction."""

from __future__ import annotations

import gc
import json
import tempfile
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext, build_context_with_evidence
from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors,
    project_lean_context_event_descriptors_v2,
    restore_lean_context_event_descriptors,
)
from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V6,
    LeanHarnessRequestEvidenceV6,
    assemble_lean_harness_request,
    load_lean_harness_dependencies,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.phases import diff_bound_evidence
from patchloop.agent.tools import TOOL_SCHEMAS_V10, ToolGateway
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Budget, MemoryCondition, Phase, Usage
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

QUALIFICATION_PATH = Path(
    "experiments/lean-harness-event-descriptor-role-public-qualification-20260823-v1.json"
)
R6_DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-mechanical-20260823-r6-public-infrastructure-diagnosis-v1.json"
)
R6_DIAGNOSIS_BYTES = 2_254
R6_DIAGNOSIS_SHA256 = "sha256:4e2049be86ed831331c355e7058531b1439f97dbed922cfa6c76f790372e82f2"
R6_DIAGNOSIS_CONTENT_HASH = (
    "sha256:66705021543c2b45535a184389e2194cf99ab9a61f9c98c4b3386f8c5f1c3445"
)
R6_EXECUTION_HASH = "sha256:d977b523f672e6b2d2d01674ad7909197ad797b109f39b69cdc39ab9b02c3c66"

SOURCE_FILES = (
    "patchloop/agent/context_event_compaction.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
)


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class QualificationScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    scenario_id: str = Field(min_length=1)
    observed: dict[str, Any]
    observation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        if self.observation_hash != sha256_json(self.observed):
            raise ValueError("descriptor-role qualification observation hash differs")
        return self


class EventDescriptorRoleQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-event-descriptor-role-qualification-v1"]
    qualification_id: Literal[
        "lean-harness-event-descriptor-role-public-20260823-v1"
    ]
    status: Literal["PUBLIC_OFFLINE_DESCRIPTOR_ROLE_QUALIFIED_PROVIDER_CLOSED"]
    official: Literal[False]
    source_diagnosis: FileBinding
    source_files: tuple[FileBinding, ...]
    source_execution_hash: Literal[
        "sha256:d977b523f672e6b2d2d01674ad7909197ad797b109f39b69cdc39ab9b02c3c66"
    ]
    runtime_policy_version: Literal["lean-harness-v6"]
    tool_schema_version: Literal["v10"]
    context_policy_version: Literal["phase-evidence-v16"]
    compaction_schema_version: Literal["lean-harness-context-event-compaction-v2"]
    event_descriptor_role_policy_version: Literal["typed-distinct-input-role-v1"]
    scenarios: tuple[QualificationScenario, ...] = Field(min_length=5)
    scenario_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    production_gateway_actions: Literal[2]
    task_repository_mutated: Literal[False]
    historical_runtime_bytes_mutated: Literal[False]
    hidden_or_private_data_read: Literal[False]
    provider_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_cost_usd: Literal["0"]
    runtime_activation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    r6_retry_authorized: Literal[False]
    quality_improvement_established: Literal[False]
    production_composition_offline_qualified: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if (
            self.source_diagnosis.path != R6_DIAGNOSIS_PATH.as_posix()
            or self.source_diagnosis.bytes != R6_DIAGNOSIS_BYTES
            or self.source_diagnosis.file_sha256 != R6_DIAGNOSIS_SHA256
        ):
            raise ValueError("descriptor-role qualification diagnosis binding differs")
        if tuple(item.path for item in self.source_files) != SOURCE_FILES:
            raise ValueError("descriptor-role qualification source inventory differs")
        scenario_ids = tuple(item.scenario_id for item in self.scenarios)
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("descriptor-role qualification scenarios repeat")
        if scenario_ids != (
            "legacy-composition-rejected",
            "production-role-distinct-inputs-preserved",
            "redundant-admission-result-compacted",
            "production-context-exact-roundtrip",
            "alternate-binding-tamper-rejected",
            "v16-persisted-next-request",
        ):
            raise ValueError("descriptor-role qualification scenario inventory differs")
        observed = {item.scenario_id: item.observed for item in self.scenarios}
        if observed["legacy-composition-rejected"] != {
            "error": "recent-event artifact binding differs"
        } or observed["alternate-binding-tamper-rejected"] != {
            "error": "recent-event alternate artifact binding differs"
        }:
            raise ValueError("descriptor-role qualification rejection class differs")
        if observed["production-role-distinct-inputs-preserved"] != {
            "mutation_status": "succeeded",
            "blocked_status": "rejected",
            "preserved_descriptor_count": 2,
            "preserved_roles": [
                {
                    "event_type": "ToolCalled",
                    "tool": "apply_structured_edit",
                    "binding_field": "patch_artifact",
                },
                {
                    "event_type": "ToolAdmissionBlocked",
                    "tool": "run_check",
                    "binding_field": "result_artifact",
                },
            ],
        }:
            raise ValueError("descriptor-role qualification preserved roles differ")
        if observed["redundant-admission-result-compacted"] != {
            "removed_descriptor_count": 1,
            "removed_fields": ["result_artifact"],
        }:
            raise ValueError("descriptor-role qualification compacted role differs")
        if observed["production-context-exact-roundtrip"].get("exact_roundtrip") is not True:
            raise ValueError("descriptor-role qualification roundtrip differs")
        if observed["v16-persisted-next-request"] != {
            "schema_version": "lean-harness-request-evidence-v6",
            "runtime_policy_version": "lean-harness-v6",
            "tool_schema_version": "v10",
            "context_policy_version": "phase-evidence-v16",
            "event_descriptor_role_policy_version": "typed-distinct-input-role-v1",
            "provider_authority_granted": False,
        }:
            raise ValueError("descriptor-role qualification persisted request differs")
        if self.scenario_set_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.scenarios]
        ):
            raise ValueError("descriptor-role qualification scenario set differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("descriptor-role qualification content hash differs")
        return self


def _binding(root: Path, relative: str | Path) -> FileBinding:
    relative_path = Path(relative)
    raw = (root / relative_path).read_bytes()
    return FileBinding(
        path=relative_path.as_posix(),
        bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _budget() -> Budget:
    return Budget(
        max_model_calls=240,
        max_tool_calls=400,
        max_total_tokens=1_100_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
    )


def _scenario(scenario_id: str, observed: dict[str, Any]) -> QualificationScenario:
    return QualificationScenario(
        scenario_id=scenario_id,
        observed=observed,
        observation_hash=sha256_json(observed),
    )


def _tampered_context(source: BuiltContext) -> BuiltContext:
    payload = json.loads(source.rendered)
    call = next(item for item in payload["recent_events"] if item["type"] == "ToolCalled")
    call["payload"]["patch_artifact"]["path"] = "objects/forged-patch"
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            **source.evidence,
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def _exercise_production_composition(root: Path) -> tuple[QualificationScenario, ...]:
    package = load_task_package(root / "tasks/smoke/csv-quoted-newline")
    budget = _budget()
    with tempfile.TemporaryDirectory(prefix="patchloop-v16-role-") as temporary:
        scratch = Path(temporary)
        manifest = build_manifest(
            package,
            run_id="run_descriptor_role_qualification",
            provider="mock",
            sandbox_backend="local",
            budget=budget,
            max_output_tokens=25_000,
        )
        state = StateStore(scratch / "state.sqlite3")
        state.create_run(manifest)
        manager = WorkspaceManager(root / "fixtures/repositories", scratch / "workspaces")
        workspace = manager.create(
            manifest.run_id,
            package.public.repository.url,
            package.public.repository.base_commit,
        )
        gateway = ToolGateway(
            run_id=manifest.run_id,
            workspace=workspace,
            task=package.public,
            state=state,
            artifacts=ArtifactStore(scratch / "artifacts"),
            sandbox=LocalSandbox(),
            tool_schema_version="v10",
            context_policy_version="phase-evidence-v16",
        )
        mutation = gateway.execute(
            "apply_structured_edit",
            "qualification-structured-edit",
            {
                "schema_version": "structured-edit-arguments-v2",
                "files": [
                    {
                        "path": "mini_data_utils/csvlite.py",
                        "replacements": [
                            {
                                "expected_text": "one audited defect",
                                "replacement_text": "one documented defect",
                            }
                        ],
                    }
                ],
            },
        )
        blocked = gateway.block_same_turn_action(
            "run_check",
            "qualification-blocked-check",
            {"check_id": package.public.visible_checks[0].id},
            source_action_id="qualification-structured-edit",
            source_result_status=mutation.status,
            source_model_event_id="qualification-model-event",
            source_call_index=0,
            blocked_call_index=1,
        )
        events = state.list_events(manifest.run_id)
        built = build_context_with_evidence(
            package.public,
            events,
            None,
            policy_version="phase-evidence-v5",
            artifact_store=gateway.artifacts,
            budget=budget,
            max_output_tokens=25_000,
        )
        try:
            project_lean_context_event_descriptors(built)
        except ValueError as exc:
            legacy_error = str(exc)
        else:
            raise ContractError("legacy descriptor compactor unexpectedly accepted R6 composition")
        if legacy_error != "recent-event artifact binding differs":
            raise ContractError("legacy descriptor compactor failure class differs")

        projected = project_lean_context_event_descriptors_v2(built)
        if restore_lean_context_event_descriptors(projected) != built.rendered:
            raise ContractError("descriptor-role projection does not restore production context")
        try:
            project_lean_context_event_descriptors_v2(_tampered_context(built))
        except ValueError as exc:
            tamper_error = str(exc)
        else:
            raise ContractError("descriptor-role alternate binding tamper was accepted")
        if tamper_error != "recent-event alternate artifact binding differs":
            raise ContractError("descriptor-role alternate binding failure class differs")

        current_diff_hash = WorkspaceManager.diff_summary(workspace).patch_hash
        phase = diff_bound_evidence(
            package.public,
            events,
            current_diff_hash,
            presented_tool_results=built.evidence["tool_results"],
            phase=Phase.IMPLEMENT,
            completion_driven=True,
        )
        delivery = build_fixed_memory_delivery(
            condition=MemoryCondition.NO_MEMORY,
            token_budget=2_000,
        )
        request = assemble_lean_harness_request(
            dependencies=load_lean_harness_dependencies(root),
            built_context=built,
            normalized_no_memory_context=built,
            base_tool_schemas=TOOL_SCHEMAS_V10,
            phase_evidence=phase,
            events=events,
            usage=Usage(),
            budget=budget,
            model_id="patchloop-public-calibration-mock-v1",
            system_prompt="public qualification prompt",
            configured_max_output_tokens=25_000,
            memory_delivery_evidence_sha256=delivery.evidence_sha256,
            runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V6,
        )
        persisted = validate_persisted_lean_harness_request(
            {
                "request_body": request.request_body,
                "request_body_hash": request.evidence.request_body_hash,
                "lean_harness_request": request.evidence.model_dump(mode="json"),
            }
        )
        if not isinstance(persisted, LeanHarnessRequestEvidenceV6):
            raise ContractError("descriptor-role persisted request type differs")

        preserved = projected.evidence.preserved_distinct_descriptors
        preserved_roles = [
            {
                "event_type": item.event_type,
                "tool": item.tool,
                "binding_field": item.binding_field,
            }
            for item in preserved
        ]
        scenarios = (
            _scenario("legacy-composition-rejected", {"error": legacy_error}),
            _scenario(
                "production-role-distinct-inputs-preserved",
                {
                    "mutation_status": mutation.status,
                    "blocked_status": blocked.status,
                    "preserved_descriptor_count": len(preserved),
                    "preserved_roles": preserved_roles,
                },
            ),
            _scenario(
                "redundant-admission-result-compacted",
                {
                    "removed_descriptor_count": projected.evidence.removed_descriptor_count,
                    "removed_fields": [
                        item.payload_field for item in projected.evidence.descriptors
                    ],
                },
            ),
            _scenario(
                "production-context-exact-roundtrip",
                {
                    "exact_roundtrip": True,
                    "source_recent_event_count": len(json.loads(built.rendered)["recent_events"]),
                },
            ),
            _scenario("alternate-binding-tamper-rejected", {"error": tamper_error}),
            _scenario(
                "v16-persisted-next-request",
                {
                    "schema_version": persisted.schema_version,
                    "runtime_policy_version": persisted.runtime_policy_version,
                    "tool_schema_version": persisted.tool_schema_version,
                    "context_policy_version": persisted.context_policy_version,
                    "event_descriptor_role_policy_version": (
                        persisted.event_descriptor_role_policy_version
                    ),
                    "provider_authority_granted": persisted.provider_authority_granted,
                },
            ),
        )
        # StateStore uses short-lived SQLite connections. Repeated Windows
        # qualification builds can otherwise defer their finalizers past the
        # TemporaryDirectory cleanup boundary.
        gc.collect()
        return scenarios


def build_event_descriptor_role_qualification(
    repository: str | Path = ".",
) -> EventDescriptorRoleQualification:
    root = Path(repository).resolve()
    diagnosis_binding = _binding(root, R6_DIAGNOSIS_PATH)
    if (
        diagnosis_binding.bytes != R6_DIAGNOSIS_BYTES
        or diagnosis_binding.file_sha256 != R6_DIAGNOSIS_SHA256
    ):
        raise ContractError("R6 public infrastructure diagnosis bytes differ")
    diagnosis = json.loads((root / R6_DIAGNOSIS_PATH).read_text(encoding="utf-8"))
    if (
        diagnosis.get("content_hash") != R6_DIAGNOSIS_CONTENT_HASH
        or diagnosis.get("content_hash")
        != sha256_json({key: value for key, value in diagnosis.items() if key != "content_hash"})
        or diagnosis.get("source_bundle", {}).get("execution_hash") != R6_EXECUTION_HASH
        or diagnosis.get("observed_failure", {}).get("terminal_error_message")
        != "recent-event artifact binding differs"
        or diagnosis.get("disposition", {}).get("r6_retry_authorized") is not False
    ):
        raise ContractError("R6 public infrastructure diagnosis content differs")
    source_bundle = diagnosis["source_bundle"]
    bundle_binding = _binding(root, source_bundle["path"])
    if (
        bundle_binding.bytes != source_bundle["bytes"]
        or bundle_binding.file_sha256 != source_bundle["file_sha256"]
    ):
        raise ContractError("R6 consumed result bundle differs from its diagnosis")
    bundle_events = [
        json.loads(line)
        for line in (root / source_bundle["path"]).read_text(encoding="utf-8").splitlines()
    ]
    if (
        not bundle_events
        or bundle_events[-1].get("event") != "batch-completed"
        or bundle_events[-1].get("content_hash") != source_bundle["terminal_content_hash"]
        or bundle_events[-1].get("execution_hash") != R6_EXECUTION_HASH
    ):
        raise ContractError("R6 consumed result bundle terminal differs")

    scenarios = _exercise_production_composition(root)
    body: dict[str, Any] = {
        "schema_version": "lean-harness-event-descriptor-role-qualification-v1",
        "qualification_id": "lean-harness-event-descriptor-role-public-20260823-v1",
        "status": "PUBLIC_OFFLINE_DESCRIPTOR_ROLE_QUALIFIED_PROVIDER_CLOSED",
        "official": False,
        "source_diagnosis": diagnosis_binding.model_dump(mode="python"),
        "source_files": tuple(
            _binding(root, relative).model_dump(mode="python") for relative in SOURCE_FILES
        ),
        "source_execution_hash": R6_EXECUTION_HASH,
        "runtime_policy_version": "lean-harness-v6",
        "tool_schema_version": "v10",
        "context_policy_version": "phase-evidence-v16",
        "compaction_schema_version": "lean-harness-context-event-compaction-v2",
        "event_descriptor_role_policy_version": "typed-distinct-input-role-v1",
        "scenarios": tuple(item.model_dump(mode="python") for item in scenarios),
        "scenario_set_hash": sha256_json(
            [item.model_dump(mode="json") for item in scenarios]
        ),
        "production_gateway_actions": 2,
        "task_repository_mutated": False,
        "historical_runtime_bytes_mutated": False,
        "hidden_or_private_data_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_cost_usd": "0",
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "r6_retry_authorized": False,
        "quality_improvement_established": False,
        "production_composition_offline_qualified": True,
    }
    return EventDescriptorRoleQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(qualification: EventDescriptorRoleQualification) -> bytes:
    return (canonical_json(qualification.model_dump(mode="json")) + "\n").encode("utf-8")


def load_event_descriptor_role_qualification(
    repository: str | Path = ".",
) -> EventDescriptorRoleQualification:
    raw = (Path(repository).resolve() / QUALIFICATION_PATH).read_bytes()
    try:
        qualification = EventDescriptorRoleQualification.model_validate_json(raw)
    except ValueError as exc:
        raise ContractError("event descriptor role qualification is invalid") from exc
    if qualification_bytes(qualification) != raw:
        raise ContractError("event descriptor role qualification bytes are not canonical")
    return qualification
