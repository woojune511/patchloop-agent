# Public-check submission with advisory original-call diagnostics

Status: IMPLEMENTED and LOCALLY_VALIDATED; live comparison NOT_EXECUTED.
All runs remain official=false and claim-ineligible. No new paid allocation is
authorized. Prior allocations remain CLOSED.

## Problem, evidence and decision

The [preceding panel](2026-10-29-helper-transfer-three-results.md) returned one
isolated acceptance PASS, one FAIL and one NOT_RUN. Its additional complete
reproduction-to-delivery criterion was 0/3, which is not zero benchmark successes.
The user asked why a repair needed diagnostic milestones beyond the benchmark's
public/hidden checks and approved separating those criteria.

This matters because pvlib passed all 31 public tests and later valid original
observations, but an earlier malformed JSON observation remained REFUTED and
blocked submission. Further code repair could not satisfy that schema mistake.
Pydicom already passed independent evaluation with unverified_delivery; SQLFluff
failed independent evaluation despite 506 public passes. These observations support
separating outcome scoring from diagnostic confidence, while preserving the need
for independent acceptance. They do not show that optional reproduction improves
repair accuracy. The unevaluated pvlib candidate might still be incorrect, and
mandatory diagnosis might prevent premature submission on other tasks.

Rather than adding another compulsory observation-correction stage, introduce a
single explicit comparison policy. The suspected mechanism is that coupled
diagnostic gates and their reservations can spend repair resources or strand a
candidate. The expected benefit is fewer such stalls; the opposing risk is that
the model submits more insufficiently investigated repairs. Acceptance and
regressions, not submission count alone, distinguish those explanations.

## Implementation

`verification_policy=public-checks-v1` is bound to RunRequest, RunEnvelope and model
identity. CLI `--verification-policy` selects it. Default/omitted
`reproduction-gated-v1` preserves old wire identity and remains the comparison
control. Resume cannot change the policy.

- A nonempty scoped candidate requires fresh PASS on all required public checks.
  Public failures still reach subsequent requests and can lead to another edit.
- Original acquisition, observation correction, path diagnosis and discriminating
  test stages become advisory. Their raw outcomes remain in the journal/model
  view, with an explicit statement that they do not block submission.
- No new automatic original replay runs after edits or at finish. Optional
  diagnostic stages/replays no longer reserve completion resources. Required
  public rechecks and the necessary edit/check/finish path remain reserved.
- Already-started physical work still reconciles. Unknown execution, scope/source
  restrictions, check freshness, action_id/input_hash idempotency, total limits
  and pre-dispatch cost accounting are unchanged.
- `unverified_delivery` remains honest about missing/refuted original evidence;
  it does not override independent acceptance. A valid explicit original replay
  can still produce cases_verified_delivery. No helper API, evaluator, hidden
  test, task package or historical result is modified.

Generic, thin and compact repair context explain this policy. The compact
completion view preserves it beside the actual observations. Optional probes
remain available within the same resources; they are not extra budget.

## Local evidence

Focused validation: 13 tests PASS in 39.256 seconds, plus two diagnostic-gate cases
PASS in 3.317 seconds; 15 cases total. Deterministic tests cover malformed and
valid-refuted observations, required public failures,
stale check results, original acquisition without a forced probe, optional
diagnostic reservations, finish idempotency, uncertain physical dispatch, and
policy identity/resume rejection. A full mock run tests isolated PASS and FAIL
independently of the delivery label. Mock evidence does not demonstrate real-model
repair gains or Docker safety.

Quick collected 870 cases: 869 passed and one documentation-size check failed.
After shortening the guide without changing runtime, all five documentation
checks passed in 0.18 seconds. Quick includes isolated mock smoke; it was not
repeated separately. Ruff over `patchloop tests` and whitespace checks passed.
The external six-row executor passed 19 offline accounting/order/cap cases in
0.096 seconds, with no provider, target, Docker or credential access.

Additional legacy resource tests passed 17 cases. Two unrelated native-context
tests in `test_thin_policy_runner.py` still fail on missing `commitment_signal`;
both were reproduced with HEAD's unchanged runner/thin/repair modules loaded in
memory. They are outside quick and were not modified or counted as passing.

## Prepared comparison

External plan: `C:/pt/verification-policy-six-plan-v1`; new output root:
`C:/pt/verification-policy-six-run-v1`. Runtime/hash and actual first-request
audits are sealed after the implementation commit. The command is `run.ps1` in
that plan directory; preparation alone never authorizes its paid execution.

| Order | Exact dev-train task | A / B |
| --- | --- | --- |
| 5-A, 5-B | swebench-lite-dev-pvlib-pvlib-python-1707 | reproduction-gated-v1 / public-checks-v1 |
| 9-A, 9-B | swebench-lite-dev-pydicom-pydicom-1694 | reproduction-gated-v1 / public-checks-v1 |
| 18-A, 18-B | swebench-lite-dev-sqlfluff-sqlfluff-1733 | reproduction-gated-v1 / public-checks-v1 |

- Same public tasks, clean prepared originals, dependency wheels, evaluator and
  gpt-5.4-2026-03-05(xhigh). Credential file:
  `C:/Users/geonj/Documents/PatchLoop/.env`; preparation does not read it.
- One run per arm/task, USD4.50 each, proposed invocation-wide **USD27.00** cap,
  no transfer/retry. Fixed A-before-B order, no runtime changes between tasks.
- Per run: 20 responses including at most one protocol correction, 40 tools,
  three accepted edits, input 60K, output 40K/correction 25K, 2400 seconds total
  including 390 seconds for isolated evaluation. These are ceilings within the
  monetary cap, not guaranteed simultaneously affordable maxima.
- Within each pair, only verification_policy and state_root differ. Thin,
  segmented-v1, result-or-size-v1, protected-v1, completion-recovery-v1, enabled
  probes/policy none, repair_recheck and bounded-v1 acquisition remain configured.
  The intervention makes acquisition advisory in B. No prior patch, checkpoint,
  observations, operator counterexamples or private evaluator contents are input.
- Primary outcome: unchanged isolated task acceptance, including registered hidden
  checks, public regressions and scope policy. Record FAIL, ERROR and NOT_RUN
  separately. Secondary: safety, submission/delivery, diagnostic evidence, actions,
  failures/revisions, cost and time. More submissions without better acceptance
  do not establish a better repair agent.
- Stop the entire batch on count, transport, billing, physical execution, cleanup
  or bound-input uncertainty; no automatic retry or image pull/build.

These are the same exposed development tasks, not held-out cases. Pydicom's public
report includes a repair suggestion. One draw per arm/task and fixed order cannot
establish a general success rate or separate stochastic model variation. A mixed
result is inconclusive; another run needs a specific evidence-based question.
Worse acceptance despite fewer stalls would weaken the simplification hypothesis.
Even a favorable result would support only a development decision under these
conditions, not a broad accuracy or safety claim.
