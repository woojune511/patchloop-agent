# Timeout test readiness and final-source validation

Date: 2026-10-17. Provider calls zero; no paid execution authorized.
This follow-up preserves the [original validation failure](2026-10-17-question-support-experiment-preparation.md)
and its sealed comparison packet without changing their recorded status or bytes.

## Problem, evidence and cause

The final-source suite stopped on
`test_real_local_timeout_retains_partial_output_and_leaves_no_readers`: the child
timed out and stdout was empty, while the test expected `partial`. This prevented a
clean validation result. The test assumed a fresh Python process would start and emit
output within 0.3 seconds. The capture timeout deliberately includes process startup.
The previous investigation measured two starts above that bound during parallel tests.

A controlled reproduction kept the 0.3-second timeout, three-second total deadline
and 128-byte output limit. Three children delayed emission by 0.6 seconds: each timed
out before emitting, returned no bytes and completed cleanup. Three immediate-output
controls retained their emitted bytes. The unmodified historical test also failed its
original stdout assertion with the controlled delay; the corrected test passed with
that same delay and unchanged limits.

This identifies an invalid readiness assumption in the test and reproduces its
failure mechanism. An alternative was loss of already emitted bytes during kill or
reader teardown; the emission controls did not reproduce that loss. The historical
failed invocation has no child-start/emission timestamp, so its exact scheduling
timeline cannot be recovered. The controlled reproduction does not invent one.

## Focused correction

Only the test changes. The real-child retention test waits for a separate readiness
file written **after** actual stdout and stderr writes. It then gives that process
to capture through its existing `Popen` boundary. The test does not read, fabricate
or prefill the captured pipes. Capture still owns timeout, kill, reaping, pipe drain
and reader joins. The same three-second total assertion includes fixture startup;
capture still receives a 0.3-second timeout and the same output limit.

The test now checks both exact output streams, all 14 observed bytes, no truncation,
the timeout verdict, confirmed process exit, closed pipes and absence of new capture
reader threads. Assertions run before fallback cleanup, so that cleanup cannot hide
a leak. The fallback also prevents a failed fixture from leaving its child alive.

Two deterministic startup cases keep the other half of the contract explicit:
startup consumes 0.1 or 0.4 seconds of the same 0.3-second execution allowance.
Only the unspent execution time may be waited; startup beyond the allowance causes
immediate cancellation with legitimately empty output. Cleanup receives only the
unspent part of the original three-second deadline. No production clock, timeout,
cleanup limit, source-selection logic or resource budget changes.

## Validation and sensitivity

The focused capture suite passed all 30 cases in 1.05 seconds. Six controls matched
their preregistered outcomes:

| Control | Required and observed outcome |
| --- | --- |
| Historical test, emission delayed by 0.6 seconds | Original stdout assertion fails |
| Corrected test, same delay | Passes with unchanged 0.3/3-second limits |
| Discard captured stdout | Corrected retention assertion fails |
| Discard captured stderr | Corrected retention assertion fails |
| Restart the timeout after process startup | Both startup cases fail |
| Double the execution timeout | Both startup cases fail |

Faults were injected only in temporary test processes; tracked runtime files were
never modified. The controls reject weaker output retention and weaker time accounting.

Evidence is append-only at `C:/pt/analyses/capture-timeout-20261017-v1`:

- `diagnostic-plan.json` and `diagnostic-result.json` bind the original failure,
  current source, controlled delays and emission observations.
- `controls-plan.json`, `controls-result.json` and per-control XML/logs preserve
  expected assertion failures separately from real validation failures.
- `validation-plan.json` binds the committed checkout, raw tracked-byte inventory,
  runtime hash and exact final-suite/mock commands. The full suite uses four workers,
  file-level distribution, zero worker restarts and no fail-fast truncation.
- `full-suite-result.json` and its XML/log report the actual final-commit outcome,
  complete collection, passing/skipped/failed counts and before/after source identity.
- `validation-result.json` binds that result, Ruff, documentation checks and isolated
  mock evaluation. It can report a clean local gate only if every required check passes.
  Test output and evidence receipts remain external, so recording the result does not
  create a new source commit after the full-suite run.

## Decision and limits

Preserve the startup-inclusive runtime deadline and correct the test's precondition.
The final commit is tested without subsequent runtime, test or documentation edits.
The prior full-suite failure remains historical evidence; a new successful result is
a separate validation receipt, not a rewrite of the old failure.

The [comparison protocol](../../.agent/plans/question-support-comparison.md), task/model
roster, repeats and proposed spending cap remain unchanged. Transition rules, the
two-reference maximum, 24,000 retained-source characters and all execution budgets
remain byte-identical to the tested selector runtime. A clean local result would
remove this test-validation obstacle; live model access, human execution approval and
the comparison's other pre-dispatch conditions still apply. No provider/token-count
call, paid solve, Docker start/pull/build or quality claim is part of this correction.
