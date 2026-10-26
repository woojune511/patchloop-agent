# Current failure and finalization

`target_outcome` projects bounded per-call outcome/capture/exception/exit-code
summaries. An unexpected raised exception can be a positive current failure even
when whole-case comparison is UNKNOWN. Qualification requires an acquired healthy
unchanged-base failure, identical frozen binding/program, current candidate diff,
one unique call ID, valid complete selected-call capture, and canonical equality
of that call's normalized inputs and execution environment. Expected exceptions,
SystemExit, changed conditions, failed setup and uncertain cleanup/timeout/output
are excluded. Other missing calls do not erase this positive selected-call evidence.

The surrounding helper may exit zero or nonzero: its settled receipt must have
consistent passed/zero or failed/nonzero status and an integer exit code. A helper
failure after a complete target exception preserves that negative evidence. Failure
before a target call, or after a normal target return, is not a target exception.
Unknown execution, incomplete selected capture and changed identity remain excluded.

The packet retains global incomplete and the original comparison; it supplies no
whole-case equality, verification or task-correctness credit. The original outer
status, exit code and helper error remain in the receipt. Existing observer
bytes, `_healthy()` and automatic replay identities remain unchanged. A later PASS
on the same candidate cannot erase the exception. A new diff requires new evidence.
`target_failure_count` blocks finish in both runner and gateway and exposes the
exception through `current_public_failure`. It uses the existing per-candidate
preparation/probe opportunity, without renewed retries on replay or restart.

`completion_context` activates at host `ready_to_submit`. Segmented requests start
a compact segment on entry and after a no-action completion correction. Keep the
public task, actual current patch, required checks, original verification/outcomes,
unresolved notes/plan and budgets. Omit old source/probe bulk; retain source lookup
identities and existing retrieval tools. Explicit new reads still deliver native
results. The journal is unchanged. Other context policies compact current state
but do not acquire segmented history-reset behavior.

`completion-recovery-v1` additionally reserves an 8,192-output-token finalization
floor, clipped to the configured ordinary ceiling. Ordinary non-final successors
still reserve 60K uncached input + 128 output. One future finalization premium is
reserved within the existing invocation cap; an optional action from ready state
must fund both its current allowance and the subsequent finalization. A closing
finish has no future reserve and uses exact input counting. The first pending
protocol correction retains its separate requested ceiling; it is never renewed.
The floor is a bounded engineering choice, not evidence that xhigh will complete
or repair successfully. Count/transport/billing uncertainty still stops execution.

`inspection_focus` is advisory after a complete current first observation. It
connects the observation to delivered current source ranges, up to three recent
zero-new-coverage inspections, and the actual last inspection question or existing
open question. These questions remain model-authored/unverified. Zero coverage
does not mean zero information; no inspection ban, new mandatory note or extra
action budget is introduced. Stale/unknown observations do not activate it.

Core validation: `uv run --locked pytest @tests/completion-feedback.txt -n 4
--dist loadfile --max-worker-restart 0 --basetemp C:/pt/tmp/<unique>`.
Quick includes the cheap projection/budget checks and real local target-exception
fixtures with zero/nonzero helper exits, plus isolated mock evaluation. The focused
`tests/test_target_outcome.py` suite also covers helper-only failures and rejected
receipts. No provider or Docker execution is required.
