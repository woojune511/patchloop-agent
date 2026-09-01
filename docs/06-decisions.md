# Active decisions

## DR-1: One mutable development head

Normal iteration changes `dev-head` directly in small feature commits. Runtime
versions, Work Items, candidates, qualifications, activations, adoptions, and
rehearsals are removed from the development lane.

## DR-2: Completion before memory

Memory is disabled during the reset. Context contains only bounded current-run
public evidence. Completion and submission reliability are the immediate target.

## DR-3: Embedded mutation intent

A mutation carries a hypothesis, expected behavior, current span evidence, and an
exact edit anchor. Repeated failures require a falsified hypothesis and alternative
mechanism in the next mutation, not a separate plan phase.

## DR-4: Invocation is bounded live authority

An exact live command authorizes only its provider, task, model, credential file,
repeat count, and total positive cap. Cost is checked at the final dispatch
boundary; uncertainty ends the invocation.

## DR-5: Historical executables leave the checkout

Historical source is recoverable from checkpoint commit `b71ddeee`; immutable
results remain in Git-tracked artifact directories. Current-run compatibility with
old Rapid or claim paths is intentionally not maintained.

## DR-6: Confirmatory work is separate

If claim work returns, it must introduce its own frozen contracts and authority in
a separate change. Confirmatory rules do not slow the mutable development lane.
