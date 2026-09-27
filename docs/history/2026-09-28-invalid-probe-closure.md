# Invalid probe closure: acknowledged uncertainty replaced by completion eligibility

Date: 2026-09-28. Provider-free public-input audit of the
[selected continuation](2026-09-28-probe-followup-results.md).
No provider calls, container runs, runtime changes or candidate edits.

## Evidence chain

All five actual dispatched requests were matched to their saved native inputs and
their canonical public-state projections using `verify_turn`. The SyntaxError was
present in both subsequent inputs. Public decisions explicitly recognized that the
probe had not exercised repository behavior. This rules against delivery loss or
mistaking the invalid probe for a behavioral PASS in this trajectory.

The model changed its focus in three steps:

| Input sequence | Question before action | Action and question update |
| --- | --- | --- |
| 513 | Which numerical convention supports the repair? | Probe the repaired classical-state behavior; retain that question |
| 529 | Does repaired behavior match the classical result? | Run base-regression; replace focus with whether submission becomes available |
| 544 | Does base-regression pass? | Submit; clear the focus question |

Its plan still acknowledged the invalid probe and untested assumption. Thus the
record supports deprioritizing known uncertainty, not demonstrated forgetting.
All five structured verification-concern lists were empty. That existing mechanism
was unused; it did not incorrectly resolve a populated concern. Focus questions are
replaceable and are not the separate persistent verification-concern contract.

At both later inputs `run_probe` was available, accepted mutations were zero, and
more than 3,300 active seconds and $2 remained. Before submission specifically:
8 model calls, 56 tool actions, 3,378 seconds, $2.407754. Correcting the probe does
not consume a repository mutation. A compile-only one-parenthesis correction
verified that the selected probe syntax was repairable; it was not executed and
was not fed back to the agent.

## Instruction audit and competing explanations

The delivered completion guidance had `next_action=null`; its final message said
submission eligibility is not proof of untested behavior. The local advice-removal
overlay remained active. Tool admission also continued to allow optional probes
(`patchloop/dev/runner.py`, probe allowance in the completion policy).

However, both system sentences below appeared in every one of these five inputs:

```
Use an affordable experiment if it could change the decision, otherwise submit.
No extra review call, annotation or experiment is required.
```

The earlier B2 sampling intervention removed them only from its single frozen
request. They returned by design in later ordinary inputs; this is not evidence
that a persistent removal failed. The model's public rationale cites no remaining
mutations, submission eligibility and no required extra experiment. A plausible
mechanism is treating lack of edit capacity as lowering the value of verification,
then allowing required-check PASS to replace the unresolved targeted question.
The causal contribution of those two sentences is **not established**: model
judgment, optional-check semantics and task confidence are competing explanations.

The prompt already says zero mutations does not forbid affordable checks, and
`behavior_verdict=not_assessed` is not PASS. Adding the same warning again or
introducing a compulsory retry gate is not supported by a missing-information
diagnosis. Nor would merely generating more probes establish better repair quality.
The submitted patch passed the original valid probe in a separate operator check;
the residual pure-state error was outside that probe's scope.

## Result and next diagnostic

Observed mechanism: an acknowledged unverified behavior was replaced by a narrower
completion question and then cleared. No evidence of missing error delivery,
blocked probe tools, exhausted time/cost, or a mandatory next-action instruction.

The next smallest causal diagnostic is the existing two-sentence removal at the
post-check submission boundary, holding task/source/state/tool schema/budgets fixed.
If continued beyond one response, keep the removal active on every following input;
do not label a single-input intervention as persistent policy. Score actual valid
reverification and evidence-grounded closure separately from probe selection, and
keep correctness evidence separate. No default adoption or paid execution is
authorized by this audit; prior funds remain closed.

Evidence: `C:/pt/analyses/invalid-probe-closure-20260928-v1/audit.json`, hash-chained
journal `run_dev_invalidprobeclosure`, script `C:/pt/audit_invalid_probe_closure_0928.py`.
Source journals and stored requests remain unchanged. No private evaluator detail
or reference implementation was read for this analysis.
