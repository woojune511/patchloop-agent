# Continue confirmed interrupted state under a new time and cost allocation

Investigation started: 2026-11-01 KST; local validation completed 2026-11-02 KST.
Lane: dev-head, official=false.
Preparation only; no new paid authorization or execution is recorded here.

## Selected problem and decision

The [eight-worker batch](2026-11-01-parallel429-dev20-results.md) stopped after
task18 reached its solver deadline while awaiting a generation. Four peers had
settled their requests and actions before the shared stop prevented the next count;
task6 had not started. The user asked to allow more time under parallel execution
and continue saved progress with increased time and cost limits.

The 26m23s batch duration is not a completed full20 time. Task18 spent about 87.7%
of its active duration in generation dispatch/wait intervals, and its public
regression still failed. Five distinct probe questions and one required check do
not support identical-check repetition as the main delay. Parallel contention and
large inputs were not isolated as causal explanations. More time can enable further
work; it does not demonstrate that the selected repair hypothesis is correct.

Normal resume binds time/cost in the exact envelope and retains consumed time.
Changing those settings fails its identity check. Four peers could technically
resume with unchanged limits, but that would not implement the user's request for
a larger allowance. The external fresh-row scheduler also rejects resume requests.
Task18 cannot retrieve its lost generation: there is no saved server response ID
for that call and the request used store=false. Its old terminal/UNKNOWN remains.

Use a new explicitly funded branch from each confirmed public checkpoint, preserving
the original runs. Reuse the existing fork/runner and shared parallel admission
mechanisms rather than rewriting old envelopes, reexecuting old effects, or starting
every task from an empty context. Ordinary exact-envelope recovery is unchanged.

## Proposed exact scope

- Five state continuations: dev-train tasks18,9,10,7,14; one fresh task6.
- One new attempt per row, maximum six concurrent processes.
- Same gpt-5.4-2026-03-05/xhigh, 25,000 output tokens, credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Cumulative 3,600 seconds per task, including the existing 330-second evaluation
  reserve. The normal fresh 1,800-second baseline is not changed.
- New funds: USD4 per row, USD24 invocation-wide; no transfer or reopening of old
  allocations. Parent settled usage and UNKNOWN reservations remain separate.
- Preserve cumulative 40 model calls, 100 actions and 12 accepted edits. No slot or
  elapsed time is refunded by selecting an earlier confirmed checkpoint.
- Keep the existing bounded temporary-429 policy, zero SDK retries and shared stop
  on any new count/transport/billing/continuation/cleanup uncertainty. No automatic
  repeat, continuation after a new interruption, or extra independent evaluation.

Task18's selected prepared-input event is seq533, retaining the settled prefix
through seq532. The full parent consumed 1,470.036 seconds and 27 generation slots,
although only 26 responses settled. The child retains those 26 receipts and uses
a 39-call envelope, leaving 13 new slots. Its separate historical lost call remains
UNKNOWN with a USD0.524015 conservative reservation. It is not resent, recovered,
zero-billed or counted as a completed response. The new input contains the confirmed
patch, failed public check, observations and planning state, with the extended budget.

The other four parents stop before their next input count and have no unresolved
provider/count/action. They preserve their full-parent elapsed time as well. No
independent evaluator output, later operator diagnosis or additional repair hint
is introduced. Finished tasks from the original batch are excluded.

## Implementation and defects found during preparation

`diagnostics/funded_continuation.py` selects and binds the latest unevaluated public
decision boundary, validates the full parent, and runs rows with separate new-cost
accounting. Every worker verifies the approved manifest bytes before loading its
row. The ordinary shared admission lock covers count, generation and physical
429 attempts. A new unknown call remains unknown and stops new peer admissions.

The existing observation-exposure restoration primitive now accepts an explicit
validated larger total wall limit. Its marker binds the whole parent journal,
excluded generation IDs/request hashes/reservations, parent elapsed time and child
call ceiling. The outer panel separately fixes 3,600 seconds. Default fork and
ordinary resume behavior are unchanged.

The audit found two concrete incompatibilities with these saved runs: restoration
only reapplied/counted replace_text even though the agent used edit_files, and the
configuration-copy list omitted rate_limit_policy. Restoration now applies accepted
file transactions from verified CAS pre/post bytes, checks their complete diff, and
preserves the retry policy. Rejected transactions stay unapplied.

An actual task18 offline rehearsal then exposed a third incompatibility: the normal
runner constructed its managed HTTP client before the scripted adapter substitution.
The network-denying rehearsal correctly stopped at adapter initialization instead
of reaching the scripted response. The helper now supplies an inert closeable
transport and retains the network ban. Review also closed its omitted run_tests
guard; remote edits/checks/submissions remain forbidden during offline rehearsal.
Actual transport wiring is exercised separately with a mocked HTTP 429 then success.

The initial failed offline receipt is preserved. After correction, task18 restored
its exact candidate and reached one scripted count/generation and AGENT_STOPPED,
with zero real API, probe or evaluation executions. The corrected rehearsal does
not establish the model's subsequent choices or successful repair.

A public-context comparison of the corrected task18 rehearsal retained all 30
top-level fields; 28 were exactly equal. Only remaining_budget and action_horizon
differed. Candidate diff, plan revision7, open question, the public check
(1 FAIL / 507 PASS), latest source read and source index/spans were identical. The
parent's existing 24K source-retention omissions remained unchanged. This establishes
public projection continuity, not full provider-wire delivery or model utilization.

## Validation and evidence boundaries

Integrated focused coverage: **62 PASS, 83.065 seconds**, including existing fork
and cost-cap owners plus new state/resource/worker tests. Cases cover accepted and
rejected multi-file edits, full-parent tail consumption, UNKNOWN provenance, fresh
funds without historical double counting, shared admission stop, manifest drift,
default compatibility, offline transport/check boundaries and actual mocked retry
wiring. Quick coverage is **1,608 PASS / one host skip, 1,286.731 seconds**, including
isolated mock evaluation. Ruff passes. The full repository test matrix was not run.
The exact committed implementation and these results are bound by the local
validation receipt before paid authorization.

The provider-free preparation rebuilds all five continuation inputs, binds their
normalized first-request fingerprints, rechecks task/source/dependency/image
identities, and reuses already passing public canaries only under those same
identities. The external collector has 14 passing offline cases and Ruff PASS; it
separates inherited/new costs, preserves UNKNOWN and validates the durable start
manifest binding before finalization. Preparation does not rerun target checks.
New preparation/execution directories
are external and single-use; the execution root remains absent before approval.

Success criteria for a later authorized run are task correctness and regression
recovery, continuity of confirmed public evidence, completion, new cost and time.
Restoration, more elapsed time or successful submission alone is not repair gain.
These continuations plus one fresh solve must not be presented as twenty fresh
latest-code attempts or a controlled causal comparison. The original partial panel
and all old UNKNOWN usage remain unchanged regardless of the new outcomes.

External evidence:

- Closed parent: `C:/pt/parallel429-dev20-run-20261101-v1/` and its closure audit.
- Initial/corrected task18 offline checks:
  `C:/pt/funded-continuation-inspection-20261101-v1/` and `-v2/`.
- Local validation: `C:/pt/funded-continuation-local-20261101-v1/`.
- Frozen preparation and authorization boundary:
  `C:/pt/funded-continuation-20261101-v1/`.
- Proposed new execution root: `C:/pt/funded-continuation-run-20261101-v1/`.

The manifest, first-request bindings and exact new allocation require current
authorization after provider-free preparation. No old approval or unused balance
is carried forward. See the [implementation contract](../../.agent/funded-continuation.md).
