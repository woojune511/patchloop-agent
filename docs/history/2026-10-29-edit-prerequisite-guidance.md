# Preserve edit prerequisites in compact model requests

Status: IMPLEMENTED and LOCALLY_VALIDATED. Live uptake NOT_EXECUTED.
All runs remain official=false and claim-ineligible. No new paid allocation is
authorized; the preceding six-run allocation remains CLOSED.

## Problem and evidence

The [six-run policy comparison](2026-10-29-verification-policy-six-v2-results.md)
contained an immediate SQLFluff B stop: one response, one stop action and no edit.
The model reported no available edit tool before attempting a source read. This
matters because it reported inability to proceed while an offered source-acquisition
path and exploration resources remained. It is one observed failure,
not an estimated recurrence rate or proof that this mechanism caused every stop.

The actual request used thin projection and the compact repair prompt. Projection
removed `completion_guidance.next_action/message`; that prompt also omitted the
ordinary source-to-edit explanation. Read/search tools were offered, but neither
system nor retained state explained that current editable source evidence could
make the edit tool available. The existing ordinary-prompt test did not exercise
this combination. Evidence is preserved in the closed result and external
`C:/pt/verification-policy-six-run-v2/post-run-audit.json`.

## Decision and implementation

Restore the missing capability fact before comparing always-visible tool schemas.
The latter would also change invalid-action exposure and request size, so it is
unnecessary to repair the demonstrated communication loss. Model action selection
could still be the cause of a stop after the information is delivered; a live
follow-up, not deterministic tests, must distinguish that remaining explanation.

- Compute `edit_availability` only after workflow, resource and scope filtering.
  Its status agrees with the final `replace_text` schema availability. Reasons
  distinguish known hard blockers from missing current editable source.
- Supply a source prerequisite only when read/search remains offered. Describe
  reevaluation under the remaining budgets, never an unconditional edit unlock.
- Preserve the card in ordinary, thin and compact stage requests, fresh correction
  and restored requests. Fresh repair correction mentions inspection as an option;
  it does not require a read or forbid stop.
- Bind the new projection contract through `dev_tool_surface_hash`. Do not change
  schema arguments, actual admission, exact-anchor checks, budgets, submission
  policy, evaluator, public/private separation or recovery action identities.

The expected benefit is that the model can understand how to obtain an edit
opportunity. Restored delivery alone cannot establish improved repairs, fewer
premature stops or superiority of staged tools. Helper/setup defects remain a
separate unresolved mechanism.

## Local validation

The new focused suite passed nine cases in 27.03 seconds. It checks actual counted
and dispatched request equality in thin/segmented compact repair, initial source
prerequisites, source-to-edit transitions, initial protocol correction, fresh
repair correction, read interruption/recovery, no duplicate actions after terminal
resume, and local isolated mock acceptance. Model/tool/edit limits and invalid
workspace scope do not advertise a read-based unlock.

The existing availability suite passed nine cases in 22.96 seconds after fixing
its stale mock callback and prompt expectations. Reinjecting unchanged HEAD policy
functions reproduced its `AttributeError`: the callback assumed every small-schema
call had `turn_decision`. It now handles absent annotations and asserts the actual
segmented repair/completion prompts. Runtime behavior was not changed for this test.
An additional legacy selection passed 29 cases; two then-failing availability
cases were resolved as above. The two previously documented native-history
`commitment_signal` failures were deselected, not repaired or counted as passing.

Quick ran 892 cases in 125.07 seconds: 890 passed, including isolated mock smoke;
two failed solely on the intentional surface-identity change. The current identity
pins were updated; seven targeted identity tests then passed in 0.97 seconds.
That selection also exposed one stale current probe-schema pin, reproduced with
unchanged HEAD's surface function and unchanged tools. Only its expected current
value was corrected; frozen historical-arm pins remain unchanged. Quick was not
repeated for these expected-value-only changes. Documentation checks passed five
cases in 0.18 seconds. Ruff over `patchloop tests` and whitespace checks passed.
An initial attempt using
the Windows default pytest temp directory failed with Access Denied; all meaningful
tests used unique short external basetemps. Runtime evidence and JUnit summaries
are outside the repository under `C:/pt/tmp`.

The focused tests use fake provider payloads and local mock evaluation with network
calls forbidden. No credential, paid provider or Docker execution occurs. Mock
acceptance is not live repair success or Docker safety; mock safety is NOT_RUN.

## Next question and boundaries

Under the same public task/model/resource settings, does the model consume the
restored prerequisite, inspect editable source and continue to a correct repair?
An unused or misunderstood card would weaken the missing-information explanation
and motivate a separate tool-visibility comparison. No such live comparison was
prepared or executed by this implementation. Prior approvals and unused funds do
not authorize a new run. Do not treat scripted transitions as model judgment gains.
