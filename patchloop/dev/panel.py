"""Fresh ordered development rows sharing one admission budget; never resumes."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest, DevTerminal
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import make_run_id, repository_root


class RowCostLedger(DevCostLedger):
    """Apply the original row ceiling and shared remaining budget to every call."""

    def __init__(self, cap_usd: Decimal, parent: DevCostLedger):
        super().__init__(cap_usd, parent.pricing)
        self.parent = parent

    @property
    def remaining_nanos(self) -> int:
        return min(super().remaining_nanos, self.parent.remaining_nanos)

    def settle(self, *, input_tokens: int, cached_input_tokens: int, output_tokens: int) -> int:
        cost = super().settle(input_tokens=input_tokens, cached_input_tokens=cached_input_tokens,
                              output_tokens=output_tokens)
        self.parent.spent_nanos += cost
        return cost


def run_panel(
    requests: list[DevRunRequest], *, max_cost_usd: Decimal, state_root: Path,
) -> dict[str, Any]:
    """Run a predeclared panel once. Calling this function is execution, not approval.

    Reuse the runner's counted dispatch, zero-retry transport and stop-all signal.
    A fresh external root prevents automatic restart after uncertain interruption.
    Each row keeps its own exact envelope and public/private separation.
    """
    rows = [DevRunRequest.model_validate(r.model_dump()) for r in requests]
    if not 1 <= len(rows) <= 6:
        raise ContractError("a panel requires 1-6 fixed rows")
    if any(r.repeat != 1 or r.resume_run_id is not None for r in rows):
        raise ContractError("panel rows must be fresh, repeat=1, without resume")
    if len({(r.provider, r.model) for r in rows}) != 1:
        raise ContractError("panel rows must share provider and model")
    cap = usd_to_nanos(max_cost_usd)
    live = rows[0].provider == "openai"
    if live and sum(usd_to_nanos(r.max_cost_usd) for r in rows) > cap:
        raise ContractError("row allocations exceed the invocation-wide cap")
    pricing = pricing_for_model(rows[0].model) if live else None
    parent = DevCostLedger(max_cost_usd, pricing) if pricing else None
    resolved = [runner._resolve_task_file(r.task) for r in rows]
    if live:
        for task_dir, package in resolved:
            runner._live_task_is_admitted(task_dir, package)
    root = state_root.resolve()
    repo = repository_root().resolve()
    if root == repo or root.is_relative_to(repo):
        raise ContractError("panel state must be outside the PatchLoop repository")
    root.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(root, make_run_id("dev"))
    runtime_hash = runner._runtime_hash()
    rows = [r.model_copy(update={"state_root": root / f"row-{i + 1}"})
            for i, r in enumerate(rows)]
    outcomes: list[dict[str, Any]] = [{"status": "NOT_RUN"} for _ in rows]
    journal.append("panel_started", {
        "official": False, "runtime_hash": runtime_hash, "cost_cap_nanos": cap,
        "rows": [{"request": r.model_dump(mode="json"),
                  "task_hash": package.task_content_hash,
                  "model_hash": runner._model_hash(r, pricing)}
                 for r, (_, package) in zip(rows, resolved, strict=True)],
        "outcomes": outcomes,
    })
    for i, (request, (task_dir, package)) in enumerate(zip(rows, resolved, strict=True)):
        ledger = RowCostLedger(request.max_cost_usd, parent) if parent else None
        journal.append("panel_row_started", {
            "row": i + 1, "state_root": str(request.state_root),
            "cost_start_nanos": parent.spent_nanos if parent else 0,
        })
        try:
            one = runner._run_one(
                request=request, task_dir=task_dir, package=package,
                state_root=request.state_root, pricing=pricing, cost_ledger=ledger,
                runtime_hash=runtime_hash, model_hash=runner._model_hash(request, pricing),
            )
        except BaseException:
            # No exception recovery, retry, replacement row, or further provider dispatch.
            journal.append("panel_aborted", {"row": i + 1, "reason": "execution_uncertainty"})
            raise
        outcomes[i] = {"status": "COMPLETED", "result": one.public,
                       "cost_nanos": ledger.spent_nanos if ledger else 0}
        # A normal runner stops repetitions when its shared cap is exhausted. Here
        # that is only this row's cap; the next fixed allocation remains independent.
        normal = one.public.get("terminal") in {
            DevTerminal.EVALUATOR_PASS, DevTerminal.EVALUATOR_FAIL,
            DevTerminal.COST_CAP_REACHED, DevTerminal.LIMIT_REACHED,
            DevTerminal.AGENT_STOPPED, DevTerminal.PROTOCOL_VIOLATION,
            DevTerminal.INCOMPLETE_RESPONSE,
        }
        stop = (not normal
                or (one.stop_remaining and one.public["terminal"] != DevTerminal.COST_CAP_REACHED)
                or bool(ledger and ledger.spent_nanos > ledger.cap_nanos)
                or bool(parent and parent.spent_nanos > parent.cap_nanos))
        journal.append("panel_row_finished", {"row": i + 1, **outcomes[i], "stop_all": stop})
        if stop:
            break
    result = {"official": False, "panel_id": journal.run_id, "rows": outcomes,
              "cost_cap_nanos": cap, "cost_nanos": parent.spent_nanos if parent else 0}
    journal.append("panel_finished", result)
    return result
