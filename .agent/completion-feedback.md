# Current failure and finalization

With `verification_policy=public-checks-v1`, original-call and diagnostic feedback
below remains evidence for model judgment, not a submission prerequisite. The
runner starts no new automatic original replay and does not force correction or
repair from that evidence. Required current-diff public checks, their failure
feedback and execution-uncertainty handling remain unchanged. The default
`reproduction-gated-v1` retains the mandatory diagnostic behavior described below.
The CLI default stays strict for compatibility and the comparison control.
Request/envelope/model identity binds the explicit policy; resume cannot switch it.
Delivery labels remain evidence labels, separate from unchanged evaluator acceptance.
The new option is locally validated, without live comparative improvement evidence.

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

Fresh invocation v5 also calls a trusted public exception collector. Frozen v1-v4
observer programs remain byte-identical. Details travel on a separate bounded
report channel, so a malformed, missing or oversized diagnostic cannot consume
the core output allowance or erase a captured exception. The sandbox profile
binds the collector and wrapper; changing it does not rebind old case baselines.

The selected negative failure may carry `exception_diagnostics`: up to three
exceptions and 16 public frames with origin, relative path, function, line and
file hash. The source scope is the exported workspace plus verified prepared
dependency members. Cause takes precedence over unsuppressed context; excluded,
limited or unsupported information is explicit. No locals or source text are
captured. An escaped exception may be secondary to an earlier context exception.
The host binds the report to action, execution source, snapshot and selected call.
Malformed diagnostic metadata cannot invalidate otherwise valid negative evidence.
Frames grant no original-case equality, success, check or submission credit.

Core owner validation: `uv run --locked pytest @tests/exception-frames.txt -n 4
--dist loadfile --max-worker-restart 0 --basetemp C:/pt/tmp/<unique>`.
Quick retains the cheap collector, legacy-byte and model-packet checks.

`completion_context` activates at host `ready_to_submit`. Segmented requests start
a compact segment on entry and after a no-action completion correction. Keep the
public task, actual current patch, required checks, original verification/outcomes,
unresolved notes/plan and budgets. Omit old source/probe bulk; retain source lookup
identities and existing retrieval tools. Latest successful `read_file`/`search_files`
results bound to the current diff retain their exact bounded output, including
repository/dependency spans and provenance, even when a fresh compact segment
omits the native exchange. Existing native-result deduplication avoids a second
delivery when that exchange remains. The latest current-diff `run_probe` also keeps
bounded stdout/stderr, the existing host observation, setup/exception/path diagnostics,
reproduction observations and completeness flags. Failed or partial probe output is
still evidence: retain failure, timeout, truncation and unknown comparison without
granting success or verification credit. Failed reads and stale/unbound results stay
summaries; older source bodies, probe programs and full execution policies remain
omitted. No retrieval permission, verdict or budget changes.
The journal is unchanged. Other context policies compact current state
but do not acquire segmented history-reset behavior.

`completion-recovery-v1` reserves role-specific output within the existing cap:
required source repair uses the ordinary output ceiling; preparation, checks and
finalization use an 8,192-token floor clipped to that ceiling. Successor inputs use
60K uncached tokens. The current required repair also keeps its full allowance;
optional exploration cannot reduce that response to the minimum accounting unit.
One physically available public-failure revision can retain read, repair, new
checks and finish funding. Immediate required completion may release speculative
recovery; per-action reservations expose that release. A closing finish has no
successor reserve and uses exact counting. The first protocol correction keeps
its independent ceiling and is never renewed. See [resources](completion-resources.md)
for time admission. These are bounded engineering allowances, not evidence that
xhigh will complete or repair. Count/transport/billing uncertainty still stops execution.

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
