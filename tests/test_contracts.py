from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.phases import validate_transition
from patchloop.contracts import (
    HiddenArtifact,
    IssueSpec,
    ModelConfig,
    Phase,
    PrivateTask,
    PublicTask,
    ReferencePatch,
    RegisteredCheck,
    RegisteredProbeProfile,
    RepositorySpec,
    TaskConstraints,
    TaskEnvironment,
    Usage,
)
from patchloop.errors import ContractError
from patchloop.runtime import calculate_model_cost
from patchloop.task_loader import load_task_package


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RegisteredCheck(id="tests", command=["python"], surprise=True)


def _public_task(**overrides) -> PublicTask:
    values = {
        "task_id": "probe-contract",
        "split": "smoke",
        "repository": RepositorySpec(
            url="snapshot://probe-contract",
            base_commit="sha256:" + ("a" * 64),
        ),
        "issue": IssueSpec(title="Probe contract", description="Exercise the contract."),
    }
    values.update(overrides)
    return PublicTask(**values)


def test_probe_profiles_are_explicit_v2_only_without_changing_v1_dump() -> None:
    v1 = _public_task()
    assert "probe_profiles" not in v1.model_dump(mode="json")

    profile = RegisteredProbeProfile(id="python-edge-cases")
    with pytest.raises(ValidationError, match="requires task-public-v2"):
        _public_task(probe_profiles=[])
    with pytest.raises(ValidationError, match="requires task-public-v2"):
        _public_task(probe_profiles=[profile])
    with pytest.raises(ValidationError, match="requires at least one"):
        _public_task(schema_version="task-public-v2")

    v2 = _public_task(
        schema_version="task-public-v2",
        probe_profiles=[profile],
    )
    assert v2.model_dump(mode="json")["probe_profiles"] == [
        {
            "id": "python-edge-cases",
            "runtime": "ephemeral-python-v1",
            "timeout_seconds": 30,
            "output_limit_bytes": 64_000,
            "source_limit_bytes": 12_000,
        }
    ]


def test_self_validation_infrastructure_fixture_is_v2_and_dataset_external() -> None:
    task_dir = (
        "fixtures/task-packages/self-validation-csv-quoted-newline"
    )
    package = load_task_package(task_dir)

    assert package.public.schema_version == "task-public-v2"
    assert package.public.task_id == "csv-quoted-newline"
    assert package.public.task_version == 2
    assert [profile.id for profile in package.public.probe_profiles] == [
        "quoted-newline-case"
    ]
    assert package.public.split == "smoke"
    assert "infrastructure-only" in package.public.tags
    assert not package.root.startswith(str(Path("tasks").resolve()))


@pytest.mark.parametrize("path", ["../secret", "/absolute", "a/../../secret"])
def test_task_paths_reject_traversal(path: str) -> None:
    with pytest.raises((ContractError, ValidationError)):
        TaskConstraints(allowed_paths=[path])


def test_invalid_phase_transition_is_rejected() -> None:
    with pytest.raises(ContractError, match="invalid phase transition"):
        validate_transition(Phase.INTAKE, Phase.DONE)


def test_replay_model_requires_content_identity() -> None:
    with pytest.raises(ValidationError, match="content hash"):
        ModelConfig(provider="replay", model_id="replay:replays/smoke/example.jsonl")

    config = ModelConfig(
        provider="replay",
        model_id="replay:replays/smoke/example.jsonl",
        replay_hash="sha256:" + ("a" * 64),
    )
    assert config.replay_hash == "sha256:" + ("a" * 64)


def test_non_replay_model_rejects_replay_hash() -> None:
    with pytest.raises(ValidationError, match="only valid"):
        ModelConfig(
            provider="mock",
            model_id="mock-v1",
            replay_hash="sha256:" + ("a" * 64),
        )


def test_model_cost_accounts_for_cache_reads_and_writes_without_double_counting() -> None:
    config = ModelConfig(
        provider="openai",
        model_id="gpt-5.6-terra",
        input_price_per_million_usd=2.50,
        cached_input_price_per_million_usd=0.25,
        cache_write_input_price_per_million_usd=3.125,
        output_price_per_million_usd=15.0,
    )
    usage = Usage(
        input_tokens=1_000_000,
        cached_input_tokens=200_000,
        cache_write_input_tokens=100_000,
        output_tokens=100_000,
    )

    assert calculate_model_cost(usage, config) == pytest.approx(3.6125)


def test_usage_rejects_cache_breakdown_larger_than_total_input() -> None:
    with pytest.raises(ValidationError, match="must not exceed input_tokens"):
        Usage(
            input_tokens=100,
            cached_input_tokens=80,
            cache_write_input_tokens=21,
        )


def test_usage_rejects_invalid_cache_breakdown_on_mutation() -> None:
    usage = Usage(input_tokens=100, cached_input_tokens=80)

    with pytest.raises(ValidationError, match="must not exceed input_tokens"):
        usage.cache_write_input_tokens = 21


def test_usage_rejects_reasoning_breakdown_larger_than_output() -> None:
    with pytest.raises(
        ValidationError,
        match="reasoning_output_tokens must not exceed output_tokens",
    ):
        Usage(output_tokens=10, reasoning_output_tokens=11)


def test_task_environment_requires_digest_pinned_image() -> None:
    digest = "sha256:" + ("a" * 64)
    with pytest.raises(ValidationError, match="immutable image digest"):
        TaskEnvironment(
            evaluator_image="example/evaluator:latest",
            image_digest=digest,
        )

    environment = TaskEnvironment(
        evaluator_image=f"example/evaluator@{digest}",
        image_digest=digest,
        source_image_tag="example/evaluator:latest",
    )
    assert environment.image_digest == digest


def test_private_v2_requires_hash_bound_hidden_artifacts() -> None:
    reference = ReferencePatch(path="reference.patch", sha256="sha256:" + ("a" * 64))

    with pytest.raises(ValidationError, match="requires at least one hidden artifact"):
        PrivateTask(
            schema_version="task-private-v2",
            task_id="hash-bound-hidden-oracle",
            reference_patch=reference,
        )

    with pytest.raises(ValidationError, match="below hidden"):
        HiddenArtifact(path="tests/oracle.py", sha256="sha256:" + ("b" * 64))
