# Executable caller linkage and same-condition comparisons

## Problem and decision

The closed [role comparison](2026-10-22-verification-role-results.md) produced no
accepted repairs. B2 declared `pylint.lint.Run` but executed helper calls instead.
The existing receipt already said `not_compared`, with zero observed declared
calls; the final claim still overstated coverage. This was not an old comparator
mistakenly reporting a matched original caller. The gap matters because adding a
declaration or independent verifier had not produced actual caller verification.

Two explanations remain: the model may fail to construct/use the declared path,
or disregard a correctly delivered coverage gap. This change addresses the first
mechanism and makes the gap concrete in handoffs. It cannot establish that the
model will use the mechanism or make better final judgments. If callers are still
not selected, or fully comparable evidence is later ignored, further bookkeeping
would not by itself resolve that problem.

## Implementation

Fresh original-requirement probes receive `call_target`, which resolves and calls
the declared public Python entrypoint, including exported aliases/constructors.
It captures actual arguments, cwd/sys.path, Python/platform, selected fixture
contents and selected environment variable hashes at invocation. The host adds
the observed sandbox profile/image/dependency identity. The expectation and task
mapping remain model-authored, separate from observed values and repair acceptance.

Replay retains the same program, purpose and expectation. Pairing requires equal
observed conditions, normalizing fresh scratch/input roots but preserving relative
paths, argument types and fixture contents, including absent files. Return versus
caught exception can change as a repair outcome. Changed inputs/environment cannot
turn a previous failure into same-condition success. Each bounded case now retains
its replay ID and baseline/latest execution linkage across handoffs.

Helper probes stay unbound. Old stdout and `record-observation-v1` cases retain
their exact execution bytes and recovery identities. No historical case is silently
upgraded. No task ID, package name or benchmark-specific behavior is in the runtime.

The adapter is bounded to four calls, four input roots, 16 selected environment
names, 64 snapshot entries/1 MiB per call, the existing 6,000-character observation
report and 2,048-byte result. Unsupported/oversized inputs, deferred execution,
missing calls and observations recorded before later calls remain unverified.
Implementation files should not be selected as fixtures. The observer is in-process
diagnostic feedback, not protection against a deliberately dishonest program.

## Offline evidence

Evidence root: `C:/pt/probe-call52`; starting commit
`50b91b511d5a3d64d1365bacfa3203eda3a85aad`. The external plan records original file
hashes and a hash-chained validation journal. Final validation and commit identity
are recorded in its closeout; intermediate failed runs remain preserved.

Saved-log replay uses the six immutable public audits from role51. All 149 saved
inputs reconstruct with previous classifications unchanged. All four probe results
remain unchanged: three unbound, one declared but unobserved. The latter's old
execution wrapper hash still matches exactly. Its one subsequent input gains a
237-byte review identifying `not_called` and the original replay action.

The new tool description adds 514 public wire bytes where `run_probe` is offered.
Including the one changed review, the maximum projected public wire increase is
779 bytes (JSON escaping included). No existing source, notes, native exchanges,
other state field or tool parameter schema is displaced in this projection.
Encrypted bodies are redacted; full token counts and future size-trigger behavior
are not measured. No saved model program or private evaluator was executed.

Local controls exercise exported aliases, constructors, exceptions, real patch
before/after replay, changed file contents/presence, argument type differences,
environment/profile drift, unsupported inputs, observation ordering, idempotent
recovery and handoff retention. Focused validation: **43 PASS / 88.142 s**. Quick
suite: **217 PASS**, including isolated mock evaluation. Ruff also passed. These
are local mechanism/regression checks, not repair-accuracy measurements. The full
repository suite and live model uptake were not run. Exact artifacts and final
commit identity are in the external closeout.

## Preserved limits and remaining question

Transition rules, two references, run/cost/source/context limits and the sandbox
remain unchanged. The larger adapter consumes existing source capacity: for the
saved 1,375-character declared program, the old wrapper was 4,473 characters and
the new wrapper would be 7,370. This is a size-only counterfactual, not execution
or migration of that historical program. Larger new probes may be rejected by the
same 8,000-character admission bound; it was not raised.

The feature does not certify issue-to-caller mapping, expected results, unselected
environment, arbitrary object state or actual repair success. The next unresolved
question is whether a model uses executable caller linkage and then handles the
result correctly; local controls and fixed-trajectory replay cannot answer it.
Provider calls, input-count calls and paid execution: **0**. No paid run is queued.
