from __future__ import annotations

import pytest
from pydantic import ValidationError

from patchloop.agent.phases import validate_transition
from patchloop.contracts import Phase, RegisteredCheck, TaskConstraints
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
