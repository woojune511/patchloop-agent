# AnyIO observation comparison: process audit

Date: 2026-09-27. Read-only follow-up to the
[closed comparison](2026-09-27-anyio-observation-repair-comparison.md).
No new model, probe, task-check or evaluator execution. Earlier results remain
unchanged and `official=false`; acceptance A 2/2 and B 2/2 is not reclassified.

## Question and evidence

The user asked to analyze how the runs succeeded, including what the models did
not know, why they read code, what they learned, and how the next edits changed.
This audit read all 26 actual public inputs and 34 public tool actions, the exact
feedback, seed and incremental diffs, and the registered public checker source.
Provider reasoning and private evaluator details were not inspected.

## Shared workflow versus independent decisions

Both arms received the old candidate diff and the same model-authored question:
does ordinary cancellation end the shared runner before fixture teardown? A had
the timeout receipt; B had completed stdout. A was not a no-hypothesis control.

Actual input 1 explicitly recommended the lifecycle check. Reads, searches and
probes were also available, so the check was advised rather than the sole allowed
action. Mutation was unavailable until registered current-source evidence existed.
Input 2 recommended a read; all selected the owning TestRunner region. At input 3,
mutation and probes were available to all four. A1 edited immediately; the others
chose more investigation. Post-edit lifecycle recheck was automatic; the remaining
upstream check and submission were explicitly recommended afterward.

Thus source target selection and later repair choices remain model decisions,
while the common sequence is partly supplied by the harness. The first check
gave both arms the same failed public case, narrowing what the extra B observation
could distinguish. This limits interpretation; it does not invalidate the fixed
comparison or show that the guidance caused the tied result.

## Read-to-edit connections

| Run | Public question and evidence | Resulting edit | Limit |
| --- | --- | --- | --- |
| A1, edit call 3 | Why does per-call cancellation end the runner? Owning loop directly awaits the coroutine and re-raises CancelledError | Keep the call future cancelled while the runner survives and clears cancellation state | Direct causal connection; broader state variants were not probed |
| B1, edit call 4 | Where should cancellation and interrupt handling differ? Owning read, other run_test declarations, no interrupt-hook search hit | Repair the loop and add a separate run_test CancelledError branch | Diagnostic cited, but necessity of both changes not isolated |
| B2, edit call 6 | Must the same runner survive for later fixture use? get_runner lease code confirms reuse until the lease count reaches zero | Handle ordinary cancellation even with zero interrupt counter | Read result is explicitly used; counter strategy not independently checked |
| A2, edit call 5 | How are per-call errors delivered without ending the runner? Plugin callers and Trio result handling | Repair cancellation loop and replace future.cancel with future.set_exception | Useful analogy; necessity of the future representation change not isolated |

B1's other-backend search returned five-line declaration spans, not their complete
implementations. Its hook search returned zero hits in the specified source glob;
that does not establish absence outside the searched scope. B2's additional
read answered the stated lifetime question, so it is not merely repeated reading.

## Specific causal overreach in B1

B1's call-3 rationale attributes the ordinary-cancellation failure to routing
CancelledError through the interrupt cleanup path. Its repair bypasses
_cancel_current_call for CancelledError, in addition to fixing the runner loop.

However, the supplied probe shows runner done/cancelled, pending counter zero and
_call_future already None. Static tracing of the delivered candidate shows:
the loop re-raises at zero pending counter; the waiting call's finally clears
_call_future; run_test then reaches the helper, whose None guard returns before
calling cancel. This is a source-and-observation inference, not new branch tracing.

The loop change addresses that cause. The extra run_test branch's necessity is
not established by the combined patch passing. Likewise A2's changed future
representation was not compared independently. These are successful repairs with
incompletely isolated explanations, not newly observed task failures.

## Public-check scope

The public CASES entry for explicit_cancel is a plain fixture. The checker uses
`fixture == "plain" or (...)` for same_fixture_task, bypassing that assertion for
this case. Its recorded failure is setup_and_teardown_passed; task mismatch in the
diagnostic output is not itself the case's failing assertion.

The later PASS verifies its other assertions, including cleanup counts and
expected outcomes. It does not directly prove same-task teardown for ordinary
cancellation. Other context/taskgroup cases still assert their task identity.
Some model completion explanations claim more than this one check establishes.
No run reran the original state-observing probe on its final candidate.

B2 also uses `pending or 1` uncancel calls, whereas the others inspect actual task
cancellation state. The explicit-cancel program schedules one cancellation. There
is no separate observed comparison of multiple cancellations, and no such failure
is established here. The passing patches are not proven equivalent on all states.

## Interpretation and next question

B's observations and relevant code survived the inspected segment boundaries.
There is no demonstrated context-loss cause. B1 explicitly cites the diagnostic;
B2's public rationale mainly cites the fresh check and lease code. Absence of an
explicit field citation does not prove an observation was internally unused.

The result supports recovery of this selected seed under a guided workflow and
fresh budget. It does not establish spontaneous case choice, precise attribution
for every changed line, or complete verification of internal preservation claims.
The original NOT_RUN outcome and full-solve budget question remain separate.

The smallest concrete next check is a separately bounded replay of the existing
public probe on the saved final candidates, observing runner survival and same-task
teardown. No new model or candidate generation is required for that question.
That replay is NOT_RUN; extra-branch necessity and multiple-cancellation behavior
would require their own checks. No runtime/prompt/default change follows from this audit.

Evidence: `C:\pt\analyses\anyio-observation-process-audit-20260927-v1` contains a
Korean report, public input/action extraction and source hashes. The closed group,
prior reports and task source remain unchanged. Only this follow-up, current-status
implications and the mutable history index are added/updated.
The five documentation tests and analysis-script Ruff check passed. Runtime source
was unchanged, so product regression and mock smoke were not rerun for this audit.
