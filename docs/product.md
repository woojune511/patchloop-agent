# Product and architecture

This document describes the current product and its stable design principles.
Read [current status](current-status.md) for the active problem and working baseline,
and the relevant section of the [implementation guide](../.agent/guide.md) for exact
contracts. Dated experiments and superseded descriptions belong in
[history](history/README.md); they are not current instructions.

## Product and development objective

PatchLoop is a single coding agent that understands a public software task, inspects
source, makes a correct repair, verifies changed and preserved behavior, and submits
reliably within bounded resources. The workspace manager, state journal, sandbox,
model adapter, and isolated evaluator support that agent.

Development uses short, mutable `dev-head` loops with `official=false`. Start from
an observed failure and public task/source/action/check evidence. Separate what
happened from the suspected mechanism and competing explanations; choose the
smallest useful diagnostic, correction, or simplification.

The objective is not to demonstrate memory, planning, review, or another preselected
method. These are possible responses to a diagnosed problem. Missing information,
available information that was misinterpreted, weak verification, and resource
exhaustion require different remedies. An ineffective mechanism can be removed.

Use local reproduction and regression checks for deterministic defects. Use a
bounded comparison when a causal question about model behavior needs one. Assess
correct repairs, regressions, completion, cost, and time. Notes, probes, tool counts,
and successful submission are diagnostic observations, not evidence of better task
solving by themselves. Record negative results and unresolved alternatives.

Research questions and methods can emerge during diagnosis. A reusable method claim
needs evidence that both the failure mechanism and remedy extend beyond one task.
A useful local fix does not need to become a general method claim.

## Runtime architecture

```text
public task + source
        |
        v
single dev-head model/tool loop ---> external run journal
        |
        v
submitted patch + content-bound manifest
        |                       |
        v (repair)              v (dev)
public delivery             separate private evaluator
acceptance NOT_RUN          acceptance + safety state
```

The same core prompt and registered tools apply across tasks. Public issue text,
source, dependencies, and checks are task inputs; the agent chooses its inspection,
repair, and verification actions. The model has no unrestricted shell access.

The runtime derives `needs_mutation`, `needs_visible_checks`, or `ready_to_submit`
from the current workspace and durable public check evidence. It does not require
a separate planning phase. Submission requires a non-empty diff, no non-ignored
untracked files, and all registered required checks passing against that exact diff.
A passed check on an earlier diff does not validate a later edit.

Mutation performs an exact text replacement in an allowed existing tracked file.
The gateway validates the anchor against observed current source and enforces the
complete diff's scope. Read, search, mutation, check, finish, and unsuccessful-stop
operations are constrained by the tool contract and remaining resources. Optional
public probes provide diagnostic observations and confer no submission credit.
Tasks can also register a pytest suite for bounded selection of existing public
test files or node IDs. This lets the agent reuse repository regression tests;
these optional results do not replace required checks or establish full coverage.

| Component | Responsibility |
| --- | --- |
| `patchloop/dev/runner.py` | Compose the loop, current state, and resource admission. |
| `patchloop/dev/completion_budget.py` | Forecast completion and bounded failure call counts from an immutable snapshot, without I/O. |
| `patchloop/dev/tools.py` | Enforce registered actions and current-diff evidence. |
| `patchloop/dev/model_state.py` | Present compact public state to the model. |
| `patchloop/dev/state.py` | Journal events and recover action/provider state. |
| `patchloop/dev/cost.py` | Admit provider cost immediately before dispatch. |
| `patchloop/agent/model.py` | Build model requests with zero SDK retries. |
| `patchloop/repository.py` | Manage isolated workspaces and complete diffs. |
| `patchloop/sandbox/` | Execute public checks and optional probes within their limits. |
| `patchloop/verifier/core.py` | Evaluate the submitted artifact separately. |

## Design choices and costs

| Choice | Prevents or makes observable | Tradeoff and executable evidence |
| --- | --- | --- |
| Exact replacement of observed tracked text | Edits against unobserved or stale anchors | Restricts file creation and large changes; [mutation tests](../tests/test_dev_mutation_identity_v31.py) |
| Checks bound to the complete diff | Reusing an earlier candidate's PASS | Rechecking consumes actions/time; [completion tests](../tests/test_dev_completion_v27.py) |
| Conservative pre-dispatch cost admission | Sending calls without admitted budget | May shorten output before completion; [cost tests](../tests/test_dev_completion_cost.py) |
| Durable action identity and strict recovery | Reapplying a completed mutation/check | Uncertain external state stops progress; [journal tests](../tests/test_dev_state.py) |
| Separate public delivery and acceptance | Treating public checks as a correctness certificate | Review/evaluation remains necessary; [repair implementation](../patchloop/repair.py) |
| Compare unchanged model tests before/after | Counting merely present test code as useful coverage | Limited to safe additive pytest edits; [verifier](../patchloop/repair_verification.py) |

These are implemented contracts, not evidence of better general repair accuracy.
`repair-verify` is a separate user command and supplies no solver submission credit.
See the [saved public repair](../examples/saved-repair/README.md) for observed behavior
and the [evidence map](evidence.md) for the limits of each result.

## Context, evidence, and recovery

Current working state includes the public task, candidate/check identities, remaining
resources, observed source, and bounded run-local notes. Model-authored findings,
plans, and concerns remain interpretations; their presence does not establish
correctness or semantic coverage. After a change, previous observations and check
results must be distinguished from evidence about the current candidate.

Cross-run memory retrieval is disabled. Run-local notes remain supported. The
append-only, hash-chained `dev-run-v1` journal and content-addressed artifacts live
outside the repository and preserve audit/recovery evidence; they are not a
cross-run learning system. Mutation/check recovery preserves `action_id + input_hash`
idempotency rather than executing the same action again.

The immutable run envelope binds the inputs needed for interruption recovery. A
submission manifest binds evaluator inputs after submission. Both carry hashes
without exposing private task paths or contents to the model.

Default context uses `append-v1`; optional context policies alter how much native
history is retained or transferred. Planning and probes are off by default. Exact
policy contracts and supported combinations live in the implementation guide;
[current status](current-status.md) names the selected working baseline, which may
use explicit options. These capabilities do not establish a quality or cost benefit.

## Public/private boundary and scope

Public checks exercise observable behavior promised by the public task. Their
success establishes only those observations, not full task acceptance. Private
specifications, hidden tests, reference patches, and evaluator details stay outside
the agent's context and tool surface. Isolated evaluation occurs after submission;
its acceptance result and safety state remain separate evidence.

Current scope includes source inspection, constrained repair, registered checks,
optional public diagnostics, resource enforcement, exact-envelope resume, action
recovery, and isolated evaluation. Cross-run memory, validation/held-out tuning,
and claim execution are disabled. Historical Rapid executables and their
candidate/qualification workflows are absent from the active runtime.

Live work requires an exact `dev-train` task, model, credential file, repeat count,
and positive invocation-wide cap. Count immediately before dispatch, use zero SDK
retries, and stop repetitions on count, transport, or billing uncertainty. Docker
startup and image pull/build are never automatic. See [operations](operations.md)
for execution procedures and [evidence](evidence.md) for interpreting results.

Keep implemented, locally tested, live-executed, and claim-producing evidence
separate. Documentation changes do not authorize a run or prove an improvement.
