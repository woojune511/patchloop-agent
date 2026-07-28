"""Create immutable fault-derived runs from an existing manifest."""

from __future__ import annotations

from patchloop.agent.runner import AgentRunner
from patchloop.contracts import FaultSpec
from patchloop.errors import ContractError
from patchloop.runtime import make_run_id
from patchloop.util import utc_now

FAULT_ALIASES = {
    "context-reset": "context-reset",
    "worker-restart": "worker-kill-after-patch",
    "worker-kill-after-patch": "worker-kill-after-patch",
    "test-timeout": "test-timeout",
}


def clone_with_fault(baseline_run_id: str, fault: str) -> dict:
    if fault not in FAULT_ALIASES:
        raise ContractError(f"unknown fault type: {fault}")
    runner = AgentRunner()
    baseline = runner.state.get_manifest(baseline_run_id)
    if baseline.model.provider == "openai":
        raise ContractError(
            "direct live fault injection is disabled; an approved reliability suite "
            "is not implemented"
        )
    fault_type = FAULT_ALIASES[fault]
    derived = baseline.model_copy(
        update={
            "run_id": make_run_id("fault"),
            "fault": FaultSpec(type=fault_type),
            "created_at": utc_now(),
        },
        deep=True,
    )
    task_dir = runner._find_task(baseline)
    model = (
        baseline.model.model_id
        if baseline.model.provider == "replay"
        else baseline.model.provider
    )
    result = runner.start(
        task_dir,
        model=model,
        memory_condition=derived.memory.condition,
        manifest=derived,
    )
    return {"derived_from_run_id": baseline_run_id, "fault": fault_type, "result": result}
