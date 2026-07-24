from __future__ import annotations

import pytest
from pydantic import ValidationError

from patchloop.agent.phases import validate_transition
from patchloop.contracts import (
    ModelConfig,
    Phase,
    RegisteredCheck,
    TaskConstraints,
    TaskEnvironment,
)
from patchloop.errors import ContractError


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RegisteredCheck(id="tests", command=["python"], surprise=True)


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
