"""Typed, candidate-bound pre-count gate shared by live requests and no-call rehearsal.

The initial rehearsal uses the real public task/model and production projectors,
but a synthetic pre-action public execution prefix. It does not observe future run bytes,
provider token counts, later budget/compaction decisions or provider acceptance.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from patchloop.agent.context import build_context_with_evidence
from patchloop.agent.lean_runtime import (
    assemble_lean_harness_request,
    load_lean_harness_dependencies,
)
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.phases import diff_bound_evidence
from patchloop.agent.provider_schema_adapter import StrictOpenAIResponsesAdapter
from patchloop.agent.provider_schema_admission import validate_provider_tool_schemas
from patchloop.contracts import (
    RAPID_ANYIO_V5_PROVIDER_SCHEMA_AB_EXPERIMENT_ID,
    Checkpoint,
    EventType,
    MemoryCondition,
    Phase,
    PublicTask,
    RunEvent,
    RunManifest,
    Usage,
)
from patchloop.errors import HarnessAdmissionError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.util import sha256_bytes, sha256_json

REQUEST_POLICY = "candidate-bound-pre-count-request-admission-v1"
REQUEST_CONTRACT = {
    "policy_version": REQUEST_POLICY,
    "both_arms": True,
    "validate_final_dynamic_schema_before_count_and_create": True,
    "require_consumed_exact_row_capability": True,
    "require_zero_sdk_retries": True,
    "closed_empty_object_admission": "implicit-empty-required-v1",
    "provider_request_bytes_modified": False,
    "rehearsal_stop": "first-input-token-count-before-sdk",
    "initial_public_prefix_only": True,
    "provider_acceptance_observed": False,
}


class PreCountRehearsalStop(BaseException):
    """A bounded non-error exit which cannot be mistaken for a failed API call."""

    def __init__(self, receipt: dict[str, Any], request: dict[str, Any]) -> None:
        self.receipt = receipt
        self.request = copy.deepcopy(request)
        super().__init__("stopped before input-token-count SDK dispatch")


def request_admission_required(manifest: RunManifest, authorization: Any) -> bool:
    """The selected campaign must not bypass admission by omitting its capability."""
    return bool(
        (
            manifest.experiment is not None
            and manifest.experiment.experiment_id == RAPID_ANYIO_V5_PROVIDER_SCHEMA_AB_EXPERIMENT_ID
        )
        or getattr(authorization, "provider_request_policy", None) is not None
    )


def validate_request_schemas(request: dict[str, Any]) -> dict[str, Any]:
    """Validate both arms without changing emitted bytes or a frozen validator.

    JSON Schema defines missing required as an empty array. A closed, propertyless
    object accepts exactly {} in either form. Only the validation copy supplies
    that empty array; a missing requirement on any nonempty object still fails.
    https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.3
    """
    schemas = copy.deepcopy(request.get("tools"))
    normalized = []

    def visit(value: Any, path: str, depth: int = 0) -> None:
        if depth > 40:
            raise HarnessAdmissionError("request schema projection exceeds bounded depth")
        if type(value) is dict:
            if (
                value.get("type") == "object"
                and type(value.get("properties")) is dict
                and not value["properties"]
                and value.get("additionalProperties") is False
                and "required" not in value
            ):
                value["required"] = []
                normalized.append(path)
            for key, child in value.items():
                visit(child, f"{path}.{key}", depth + 1)
        elif type(value) is list:
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]", depth + 1)

    visit(schemas, "tools")
    strict = validate_provider_tool_schemas({"tools": schemas})
    body = {
        **{key: value for key, value in strict.items() if key != "content_hash"},
        "tool_schema_hash": sha256_json(request.get("tools")),
        "validation_projection_schema_hash": strict["tool_schema_hash"],
        "compatibility_policy": "implicit-empty-required-v1",
        "equivalent_empty_required_paths": normalized,
        "provider_request_bytes_modified": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def admit_request(
    manifest: RunManifest,
    authorization: Any,
    request: dict[str, Any],
    adapter: OpenAIResponsesAdapter,
    *,
    stop_before_count: bool,
) -> dict[str, Any]:
    from patchloop.agent.runner import (
        RowExecutionAuthorization,
        row_execution_authorization_receipt,
    )

    if type(authorization) is not RowExecutionAuthorization:
        raise HarnessAdmissionError("pre-count gate requires a typed row capability")
    row = row_execution_authorization_receipt(authorization)
    experiment = manifest.experiment
    if (
        experiment is None
        or experiment.experiment_id != RAPID_ANYIO_V5_PROVIDER_SCHEMA_AB_EXPERIMENT_ID
        or row.get("provider_request_policy") != REQUEST_POLICY
        or row["authority_kind"] != ("rehearsal" if stop_before_count else "live")
        or not row["consumed"]
        or row["provider_dispatch_rehearsed"]
        or row.get("input_count_rehearsed") is not False
        or row["run_id"] != manifest.run_id
        or row["manifest_hash"] != sha256_json(manifest.model_dump(mode="json"))
        or row["execution_hash"] != experiment.execution_hash
        or row["schedule_order"] != experiment.schedule_order
        or row["schedule_row_id"] != experiment.schedule_row_id
        or (manifest.tool_schema_version, manifest.context_policy_version)
        not in {("v26", "phase-evidence-v35"), ("v28", "phase-evidence-v37")}
    ):
        raise HarnessAdmissionError("pre-count request capability differs")
    if (
        not isinstance(adapter, OpenAIResponsesAdapter)
        or adapter.config != manifest.model
        or type(getattr(adapter.client, "max_retries", None)) is not int
        or adapter.client.max_retries != 0
        or manifest.model.transport_max_retries != 0
        or request.get("model") != manifest.model.model_id
    ):
        raise HarnessAdmissionError("pre-count adapter/model/retry binding differs")
    schema = validate_request_schemas(request)
    body = {
        "schema_version": "candidate-pre-count-request-receipt-v1",
        "policy_version": REQUEST_POLICY,
        "stage": "provider-input-token-count-boundary",
        "execution_hash": experiment.execution_hash,
        "schedule_order": experiment.schedule_order,
        "schedule_row_id": experiment.schedule_row_id,
        "run_id": manifest.run_id,
        "manifest_hash": row["manifest_hash"],
        "public_spec_hash": manifest.public_spec_hash,
        "model_contract_hash": sha256_json(manifest.model.model_dump(mode="json")),
        "request_hash": sha256_json(request),
        "tool_schema_admission": schema,
        "provider_dispatch_blocked": stop_before_count,
        "provider_acceptance_observed": False,
        "generation_started_by_gate": False,
    }
    receipt = {**body, "content_hash": sha256_json(body)}
    if stop_before_count:
        with authorization._state.lock:
            if authorization._state.input_count_rehearsed:
                raise HarnessAdmissionError("input count boundary was already rehearsed")
            authorization._state.input_count_rehearsed = True
        raise PreCountRehearsalStop(receipt, request)
    return receipt


class _NoTransport:
    max_retries = 0

    def __getattr__(self, name: str) -> Any:
        raise HarnessAdmissionError(f"no-call adapter attempted transport access: {name}")


class _EmptyArtifacts:
    """The synthetic pre-action prefix cannot read or write any artifact."""

    def __getattr__(self, name: str) -> Any:
        raise HarnessAdmissionError(f"pre-action rehearsal attempted artifact access: {name}")


def rehearse_initial_request(
    manifest: RunManifest,
    authorization: Any,
    task: PublicTask,
    *,
    repository: Path,
    image_authorization: Any,
) -> dict[str, Any]:
    """Real request construction, synthetic pre-action prefix, no provider or workspace."""
    from patchloop.agent.batch_image_authority import validate_row_batch_image
    from patchloop.agent.runner import AgentRunner, _consume_row_execution_authorization

    if (
        type(task) is not PublicTask
        or sha256_json(task.model_dump(mode="json")) != manifest.public_spec_hash
        or task.task_id != manifest.task_id
        or task.task_version != manifest.task_version
        or manifest.memory.condition != MemoryCondition.NO_MEMORY
    ):
        raise HarnessAdmissionError("initial request public task binding differs")
    _consume_row_execution_authorization(
        manifest,
        authorization,
        expected_authority_kind="rehearsal",
        live_authorization=None,
    )
    validate_row_batch_image(
        image_authorization,
        authorization,
        manifest,
        expected_kind="rehearsal",
        expected_image=image_authorization.image,
        expected_digest=manifest.evaluator_image_digest,
    )
    empty_diff = sha256_bytes(b"")
    events = [
        RunEvent(
            event_id="evt_initial_no_call",
            run_id=manifest.run_id,
            sequence=1,
            type=EventType.RUN_STARTED,
            timestamp=manifest.created_at,
            actor="runner",
            payload={"task_id": task.task_id, "synthetic_rehearsal_prefix": True},
        )
    ]
    checkpoint = Checkpoint(
        checkpoint_id="ckpt_initial_no_call",
        run_id=manifest.run_id,
        through_sequence=1,
        phase=Phase.REPRODUCE,
        task_summary=manifest.task_id,
        repository_head=manifest.base_commit,
        worktree_diff_hash=empty_diff,
        pending_checks=[check.id for check in task.visible_checks],
        remaining_budget={
            "tokens": manifest.budget.max_total_tokens,
            "model_calls": manifest.budget.max_model_calls,
            "tool_calls": manifest.budget.max_tool_calls,
        },
        created_at=manifest.created_at,
    )
    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        "",
        policy_version="phase-evidence-v5",
        budget=manifest.budget,
        artifact_store=_EmptyArtifacts(),
        max_output_tokens=manifest.model.max_output_tokens,
        model_provider=manifest.model.provider,
    )
    system_prompt, tools = AgentRunner._runtime_contract(manifest)
    adapter_class = (
        StrictOpenAIResponsesAdapter
        if manifest.context_policy_version == "phase-evidence-v37"
        else OpenAIResponsesAdapter
    )
    adapter = adapter_class(manifest.model, client=_NoTransport())

    def request_builder(context, selected_tools, max_output_tokens):
        body = adapter.request_payload(context, list(selected_tools), system_prompt=system_prompt)
        body["max_output_tokens"] = max_output_tokens
        return body

    def stop_counter(body):
        return admit_request(manifest, authorization, body, adapter, stop_before_count=True)

    memory = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=manifest.memory.max_context_tokens,
    )
    try:
        assemble_lean_harness_request(
            dependencies=load_lean_harness_dependencies(repository),
            built_context=built,
            normalized_no_memory_context=built,
            base_tool_schemas=tools,
            phase_evidence=diff_bound_evidence(
                task,
                events,
                empty_diff,
                phase=Phase.REPRODUCE,
                completion_driven=True,
            ),
            events=events,
            usage=Usage(),
            budget=manifest.budget,
            model_id=manifest.model.model_id,
            system_prompt=system_prompt,
            configured_max_output_tokens=manifest.model.max_output_tokens,
            memory_delivery_evidence_sha256=memory.evidence_sha256,
            runtime_policy_version=(
                "lean-harness-v27"
                if manifest.context_policy_version == "phase-evidence-v37"
                else "lean-harness-v25"
            ),
            task=task,
            provider_request_builder=request_builder,
            provider_input_token_counter=stop_counter,
            live_input_count_method="openai-input-token-count-v2-parallel-bound",
        )
    except PreCountRehearsalStop as stopped:
        body = {
            **{key: value for key, value in stopped.receipt.items() if key != "content_hash"},
            "initial_public_prefix_only": True,
            "future_execution_request_bytes_observed": False,
            "provider_input_tokens_observed": False,
            "post_count_budget_decisions_exercised": False,
        }
        return {**body, "content_hash": sha256_json(body)}
    raise HarnessAdmissionError("initial request did not reach the pre-count boundary")
