# AnyIO: linking delivered evidence to actions and later observations

Date: 2026-09-27. Follow-up to the [process audit](2026-09-27-anyio-observation-process-audit.md)
and [final-candidate replay](2026-09-27-anyio-final-probe-scope.md).
Read-only analysis of saved public evidence; `official=false`, `claim_eligible=false`.
No model, probe, registered check or private evaluation was executed in this audit.

## Question and method

Did the available information support the repairs and the verification claims?
We linked 26 saved input projections, 34 public tool actions, incremental patches
and the later operator replay. All 31 delivered source spans matched the exact
saved seed files, including their full-file hashes. Each repair's resulting diff
matched its final-candidate replay. Public turn decisions are model assertions,
not private reasoning transcripts or proof that a specific input caused an action.

Both arms already had the prior cancellation question and probe program. A had a
timeout receipt; B had completed output. A was not a no-hypothesis control. All
four first followed the recommended lifecycle check, obtained current source
anchors, repaired once, passed automatic recheck and upstream regression, then
submitted. The automatic recheck was a harness action, not a model probe choice.

## Evidence-to-action links

Call and sequence numbers below refer to the original public action journals.

| Candidate | Information and subsequent edit | What remains unresolved |
| --- | --- | --- |
| A1 / NA1 | Call 2, seq 32 read the runner loop, caller and cancellation helper. Call 3, seq 47 removed the zero-pending re-raise and drained cancellation before continuing the runner. | The later probe supports runner survival and same-task cleanup; it does not isolate the necessity of the entire draining strategy. |
| B1 / NB1 | Call 2, seq 32 read the same mechanism. Call 3 searched for an interrupt hook and runner declarations. Call 4, seq 63 repaired the runner loop and added a separate `except CancelledError: raise` in `run_test`. | The combined patch works, but blaming the helper's additional cancellation does not fit the observed seed path. The extra exception branch's necessity was not tested. |
| B2 / NB2 | Calls 3-5 inspected runner construction and `get_runner` leases; call 5, seq 78 delivered the lease code. Call 6, seq 92 explicitly used that reading and changed cancellation clearing to `pending or 1`. | The lease source establishes instance reuse; the loop source supplies the task-lifetime connection. The replay covers one cancellation, not all possible cancellation counts. |
| A2 / NA2 | Call 4, seq 67-68 read the pytest plugin and Trio outcome transport. Call 5, seq 82 separated per-call failure from runner lifetime, changing `future.cancel(...)` to `future.set_exception(exc)` and clearing cancellation. | The backend analogy informed a coherent repair. The replay does not isolate whether changing Future exception transport was needed. |

All four later observations support cleanup completing once in the original task
for the selected single-cancellation plain-fixture program. A1 and B2 retained
`future.cancel(...)` without B1's extra exception branch. They show those changes
are not universal requirements for this observation; they are not controlled
deletions from B1 or A2 because their runner-loop implementations also differ.

## Correction to the helper interpretation

The earlier process record described a path that "bypasses" the helper. More
precisely, the saved seed replay records entry into the helper and its early return:

- Seed line 2255 enters the runner-loop re-raise. Line 2293 resets `_call_future`.
- Lines 2296 and 2298 read that field and test for `None`; line 2303 returns.
- Lines 2305-2306, which increment pending uncancellations and cancel the runner,
  are within the collector's changed-line scope and were not observed.

Together with the delivered source and probe's explicit self-cancellation, this
supports runner-loop termination as the observed failure mechanism, not another
cancel issued by that helper on this path. This is Python launch-thread line-entry
evidence, not general branch coverage. B1's added exception branch itself *was*
entered in its later replay (2355-2356); execution alone does not prove necessity.
A2's `set_exception` line 2250 was also entered, with the same limitation.

## Verification and harness implications

The public lifecycle check reports seven passing cases and upstream regression
reports 32 passed, three deselected. The lifecycle plain-fixture explicit-cancel
case short-circuits its same-task assertion. Those results did not directly prove
the same-task behavior asserted in B1's subsequent public decision. The later
operator probe supplies that specific observation after submission; it does not
retroactively become verification performed by the agent.

Every saved input offered `run_probe`; no model requested it. B's completed
observation remained delivered, becoming historical-candidate evidence after the
edit. Every final input requested segment review and explicitly said submission
eligibility was not proof of untested behavior, with an optional probe for a
concrete remaining uncertainty. The final decisions reported no remaining one.
Missing observation delivery, missing probe access and absence of a coverage
warning therefore do not explain this record. Delivery does not establish use;
the guidance/action alignment also does not establish that advice caused stopping.

No new prompt, memory mechanism, probe mandate or default change follows from
these four successful repairs. Correct behavior, imperfect causal explanation and
verification claims exceeding the agent's own checks can coexist.

The smallest next counterfactual is to remove only B1's extra exception branch
and rerun the same public observation/checks under the fixed environment. This
would test patch necessity, not a harness component. It has not been executed.
A separate harness hypothesis could test completion recommendations with gates
fixed. The existing `status-only-v1` diagnostic removes two recommendation fields,
but currently rejects supplemental `public_feedback`; directly comparing it with
these feedback-seeded runs would confound two changes. Any such comparison needs
matched feedback conditions and a separately bounded design before execution.

## Evidence and validation

Packet: `C:\pt\analyses\anyio-evidence-action-link-20260927-v2` contains the
read-only extraction script, source/input hashes, per-candidate links, selected
line-entry evidence and closure. A six-event `dev-run-v1` journal verifies. Closure
checked 63 input/source/history files unchanged before documentation updates.

The preserved `v1` attempt stopped at an extraction assertion: Python
`splitlines()` dropped a final empty delivered source line. The successor compares
the exact newline-joined source span to the delivered content and passes. This
was an audit-script error; it is not an agent or probe failure.

Extractor assertions, five documentation layout/link tests and Git whitespace
validation passed. Ruff reported seven style findings (line length and variable
naming) in the preserved external extractor; they were not runtime failures.
Product regression and mock smoke were not rerun for this documentation-only
change. Paid work, component ablations and fresh end-to-end solving remain unrun.
